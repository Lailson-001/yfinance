"""Interface de linha de comando, executada com python -m src.collect."""

import argparse
import sys
from collections.abc import Sequence
from datetime import datetime

from .config import COVERAGE_TOLERANCE_DAYS, DEFAULT_INTERVAL, MIN_YEAR, normalize_ticker
from .environment import logger
from .pipeline import run_pipeline


def _year_type(value: str) -> int:
    """Valida um ano informado na CLI."""
    try:
        year = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{value}' não é um ano válido") from None
    current_year = datetime.now().year
    if not MIN_YEAR <= year <= current_year:
        raise argparse.ArgumentTypeError(f"ano deve estar entre {MIN_YEAR} e {current_year}")
    return year


def _ticker_type(value: str) -> str:
    """Valida e normaliza um ticker da B3 no formato do Yahoo (ex.: PETR4.SA)."""
    try:
        return normalize_ticker(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m src.collect",
        description="Coleta histórica de dados de ativos da B3 via yfinance.",
    )
    parser.add_argument("--start", type=_year_type, required=True,
                        help="ano inicial da coleta (ex.: 2015)")
    parser.add_argument("--end", type=_year_type, default=datetime.now().year,
                        help="ano final, inclusive (padrão: ano atual)")
    parser.add_argument("--interval", choices=list(COVERAGE_TOLERANCE_DAYS),
                        default=DEFAULT_INTERVAL, help="intervalo dos dados (padrão: 1d)")
    parser.add_argument("--tickers", nargs="+", type=_ticker_type, default=None,
                        metavar="TICKER",
                        help="tickers específicos (ex.: PETR4.SA VALE3.SA); "
                             "padrão: lista DEFAULT_TICKERS")
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Interpreta e valida os argumentos da linha de comando."""
    parser = build_parser()
    args = parser.parse_args(argv)
    # O fim é inclusivo em anos, então o mesmo ano representa um período válido.
    if args.start > args.end:
        parser.error("--start deve ser menor ou igual a --end")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada: interpreta argumentos e executa o pipeline."""
    args = parse_args(argv)
    try:
        # O núcleo recebe valores comuns e pode ser reutilizado fora da CLI.
        return run_pipeline(args.start, args.end, args.interval, args.tickers)
    except Exception:  # noqa: BLE001 - última barreira: registra e sai com erro
        logger.critical("Erro inesperado durante a execução.", exc_info=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
