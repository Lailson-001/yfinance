"""Parâmetros de coleta e esquema padrão das saídas."""

import re


# Lista inicial de ativos da base original, sem pretensão de ranking.
DEFAULT_TICKERS: tuple[str, ...] = (
    "PETR4.SA",
    "VALE3.SA",
    "ITUB4.SA",
    "BBDC4.SA",
    "BBAS3.SA",
    "ABEV3.SA",
    "WEGE3.SA",
    "B3SA3.SA",
    "ITSA4.SA",
    "SUZB3.SA",
)

DEFAULT_INTERVAL = "1d"
# Apenas intervalos >= 1 dia: intradiários no Yahoo têm janela máxima curta
# (~60 dias) e não servem para coleta histórica longa.
# Valor do dict = tolerância (dias) para detectar histórico incompleto.
COVERAGE_TOLERANCE_DAYS: dict[str, int] = {
    "1d": 10,
    "5d": 14,
    "1wk": 14,
    "1mo": 45,
    "3mo": 100,
}
MIN_YEAR = 1970
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2.0

# O prefixo pode conter dígitos, como em B3SA3.SA.
TICKER_PATTERN = re.compile(r"[A-Z][A-Z0-9]{3}[0-9]{1,2}\.SA")
PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]
OHLC_COLUMNS = ["open", "high", "low", "close"]
ACTION_COLUMNS = ["dividends", "stock_splits"]

LOGGER_NAME = "b3_pipeline"



def normalize_ticker(value: str) -> str:
    """Valida um ticker da B3 e devolve o formato esperado pelo Yahoo."""
    # A mesma regra atende a CLI e as chamadas Python do pipeline.
    ticker = value.strip().upper()
    if not TICKER_PATTERN.fullmatch(ticker):
        raise ValueError(f"ticker inválido '{value}' (esperado formato como PETR4.SA)")
    return ticker
