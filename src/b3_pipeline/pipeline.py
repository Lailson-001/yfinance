"""Orquestra coleta, transformação, persistência e resumo da execução."""

import time
from collections.abc import Sequence
from datetime import date, datetime
from uuid import uuid4

import pandas as pd

from .config import (
    COVERAGE_TOLERANCE_DAYS,
    DEFAULT_INTERVAL,
    DEFAULT_TICKERS,
    MIN_YEAR,
    normalize_ticker,
)
from .download import download_data
from .environment import logger, setup_environment
from .models import NoDataError, ProjectPaths, TickerResult
from .storage import save_parquet, save_raw_data
from .transform import transform_data


def resolve_tickers(requested: Sequence[str] | None) -> list[str]:
    """Retorna os tickers a processar, sem duplicatas e preservando a ordem.

    Se nenhum ticker for informado, usa DEFAULT_TICKERS.
    """
    source = requested if requested else DEFAULT_TICKERS
    return list(dict.fromkeys(normalize_ticker(ticker) for ticker in source))


def process_ticker(
    ticker: str,
    history: pd.DataFrame,
    paths: ProjectPaths,
    interval: str,
    run_id: str,
) -> TickerResult:
    """Persiste o bruto, transforma e grava o Parquet de um ativo."""
    raw_file = None
    try:
        raw_file = save_raw_data(history, ticker, interval, paths.raw, run_id)
        processed = transform_data(history, ticker)
        # Uma transformação vazia não deve substituir um Parquet válido.
        if processed.empty:
            raise NoDataError(f"{ticker}: nenhum registro válido após a transformação")
        processed_file = save_parquet(processed, ticker, interval, paths.processed)
    except (OSError, ValueError, KeyError, TypeError, ImportError, NoDataError) as exc:
        logger.error("%s: erro no processamento: %s", ticker, exc, exc_info=True)
        # O CSV pode ter sido gravado antes da falha. Inclua-o no resumo.
        return TickerResult(ticker, success=False, raw_file=raw_file, error=str(exc))

    return TickerResult(
        ticker, success=True, records=len(processed),
        raw_file=raw_file, processed_file=processed_file,
    )


def log_summary(requested: int, results: list[TickerResult], elapsed: float) -> None:
    """Registra o resumo final da execução."""
    succeeded = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    files = [f for r in results for f in (r.raw_file, r.processed_file) if f]

    logger.info("=" * 60)
    logger.info("RESUMO DA EXECUÇÃO")
    logger.info("Ativos solicitados : %d", requested)
    logger.info("Coletados com êxito: %d", len(succeeded))
    logger.info("Com falha          : %d %s", len(failed), [r.ticker for r in failed] or "")
    logger.info("Total de registros : %d", sum(r.records for r in succeeded))
    logger.info("Arquivos gerados   : %d", len(files))
    for file in files:
        logger.info("  - %s", file)
    logger.info("Tempo total        : %.2fs", elapsed)
    logger.info("=" * 60)


def year_range_to_dates(start_year: int, end_year: int) -> tuple[str, str]:
    """Converte anos em datas ISO para o yfinance.

    O `end` do yfinance é exclusivo; por isso o ano final entra como 1º de
    janeiro do ano seguinte, para que o último ano seja contemplado por inteiro.
    """
    current_year = date.today().year
    if not MIN_YEAR <= start_year <= end_year <= current_year:
        raise ValueError(f"anos devem estar em ordem e entre {MIN_YEAR} e {current_year}")
    start = date(start_year, 1, 1).isoformat()
    end = date(end_year + 1, 1, 1).isoformat()
    return start, end


def run_pipeline(
    start_year: int,
    end_year: int,
    interval: str = DEFAULT_INTERVAL,
    requested_tickers: Sequence[str] | None = None,
) -> int:
    """Executa o pipeline completo. Retorna 0 se tudo deu certo, 1 se houve falhas."""
    started = time.perf_counter()
    # Valida também chamadas diretas para evitar rede e arquivos com parâmetros inválidos.
    if interval not in COVERAGE_TOLERANCE_DAYS:
        raise ValueError(f"intervalo inválido: {interval}")
    tickers = resolve_tickers(requested_tickers)
    start, end = year_range_to_dates(start_year, end_year)

    paths = setup_environment()
    # O sufixo exclusivo mantém coletas simultâneas em CSVs separados.
    run_id = f"{datetime.now():%Y%m%dT%H%M%S}_{uuid4().hex}"

    logger.info("Início da execução %s | %d ativos | %s a %s | intervalo %s",
                run_id, len(tickers), start, end, interval)

    data, failures = download_data(tickers, start, end, interval)

    results = [TickerResult(t, success=False, error=msg) for t, msg in failures.items()]
    results += [
        process_ticker(ticker, history, paths, interval, run_id)
        for ticker, history in data.items()
    ]

    elapsed = time.perf_counter() - started
    log_summary(len(tickers), results, elapsed)
    logger.info("Fim da execução %s", run_id)

    if not any(r.success for r in results):
        logger.critical("Nenhum ativo foi coletado com sucesso.")
        return 1
    return 0 if all(r.success for r in results) else 1
