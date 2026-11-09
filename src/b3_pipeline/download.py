"""Integração com o Yahoo Finance, tentativas e verificação de cobertura."""

import time
from collections.abc import Sequence

import pandas as pd
import yfinance as yf
from yfinance.exceptions import YFPricesMissingError

from .config import COVERAGE_TOLERANCE_DAYS, DEFAULT_INTERVAL, MAX_RETRIES, RETRY_DELAY_SECONDS
from .environment import logger
from .models import DownloadError, NoDataError


def fetch_ticker_history(
    ticker: str,
    start: str,
    end: str,
    interval: str,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY_SECONDS,
) -> pd.DataFrame:
    """Baixa o histórico de um ativo com retry e espera linear entre tentativas.

    Levanta:
        NoDataError: o Yahoo respondeu, mas sem registros (sem retry).
        DownloadError: todas as tentativas falharam.
    """
    if max_retries < 1:
        raise DownloadError(f"{ticker}: max_retries deve ser >= 1")

    # Nas versões recentes a opção é global. Restaurá-la após a chamada
    # evita alterar o comportamento de outros usos do yfinance no processo.
    # A coleta deste pipeline é sequencial.
    debug = getattr(getattr(yf, "config", None), "debug", None)
    legacy_options = {}
    uses_global_setting = hasattr(debug, "hide_exceptions")
    if not uses_global_setting:
        legacy_options["raise_errors"] = True

    for attempt in range(1, max_retries + 1):
        try:
            if uses_global_setting:
                previous_setting = debug.hide_exceptions
                debug.hide_exceptions = False
            try:
                history = yf.Ticker(ticker).history(
                    start=start,
                    end=end,
                    interval=interval,
                    auto_adjust=False,  # mantém Close e Adj Close separados
                    actions=True,  # inclui Dividends e Stock Splits
                    **legacy_options,
                )
            finally:
                if uses_global_setting:
                    debug.hide_exceptions = previous_setting
        except YFPricesMissingError as exc:
            # Resposta sem preços tem o mesmo tratamento de um DataFrame vazio.
            raise NoDataError(f"{ticker}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - yfinance lança tipos variados
            if attempt == max_retries:
                raise DownloadError(
                    f"{ticker}: falha após {max_retries} tentativas ({exc})"
                ) from exc
            wait = retry_delay * attempt
            logger.warning(
                "%s: tentativa %d/%d falhou (%s). Nova tentativa em %.1fs.",
                ticker, attempt, max_retries, exc, wait,
            )
            time.sleep(wait)
            continue

        if history.empty:
            raise NoDataError(f"{ticker}: nenhum registro retornado para {start} a {end}")
        return history


def check_coverage(
    ticker: str, history: pd.DataFrame, start: str, end: str, interval: str
) -> None:
    """Registra em log se o histórico disponível não cobre todo o período pedido."""
    index = history.index
    if not isinstance(index, pd.DatetimeIndex) or index.hasnans:
        raise ValueError(f"{ticker}: índice de datas inválido no histórico")
    if index.tz is not None:
        index = index.tz_localize(None)

    first, last = index.min(), index.max()
    tolerance = pd.Timedelta(days=COVERAGE_TOLERANCE_DAYS.get(interval, 10))
    requested_start = pd.Timestamp(start)
    requested_end = pd.Timestamp(end) - pd.Timedelta(days=1)  # end é exclusivo

    if first - requested_start > tolerance:
        logger.warning(
            "%s: histórico PARCIAL - solicitado desde %s, disponível desde %s.",
            ticker, requested_start.date(), first.date(),
        )
    if requested_end < pd.Timestamp.now() and requested_end - last > tolerance:
        logger.warning(
            "%s: dados terminam em %s, antes do fim solicitado (%s). "
            "Possível deslistagem ou mudança de ticker.",
            ticker, last.date(), requested_end.date(),
        )
    logger.info(
        "%s: %d registros coletados (%s a %s).",
        ticker, len(history), first.date(), last.date(),
    )


def download_data(
    tickers: Sequence[str],
    start: str,
    end: str,
    interval: str = DEFAULT_INTERVAL,
    max_retries: int = MAX_RETRIES,
    retry_delay: float = RETRY_DELAY_SECONDS,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Baixa o histórico de cada ticker sem interromper a coleta em caso de erro.

    Retorna:
        (dados, falhas): dicionários {ticker: DataFrame} e {ticker: mensagem}.
    """
    data: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}

    for ticker in tickers:
        logger.info("Processando %s | período %s a %s | intervalo %s", ticker, start, end, interval)
        try:
            history = fetch_ticker_history(
                ticker, start, end, interval, max_retries, retry_delay
            )
            # A validação da resposta também precisa ficar isolada por ativo.
            check_coverage(ticker, history, start, end, interval)
        except (DownloadError, NoDataError, ValueError) as exc:
            logger.error("%s", exc)
            failures[ticker] = str(exc)
            continue

        data[ticker] = history

    return data, failures
