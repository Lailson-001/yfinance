#%%
import argparse
import logging
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
 
import pandas as pd
import yfinance as yf

DEFAULT_INTERVAL = "1d"
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
 
TICKER_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}\.SA$")
PRICE_COLUMNS = ["open", "high", "low", "close", "adj_close"]
OHLC_COLUMNS = ["open", "high", "low", "close"]
ACTION_COLUMNS = ["dividends", "stock_splits"]
 
LOGGER_NAME = "b3_pipeline"
logger = logging.getLogger(LOGGER_NAME)

#%%
class DownloadError(Exception):
    """ Falha ao baixar os dados"""
    
class NoDataError(Exception):
    """ O yahoo Finance não retornou nenhum registro para o ativo/periodo"""
    
@dataclass(frozen=True)
class ProjectPaths:
    """Caminhos absolutos do projeto."""
 
    root: Path
    raw: Path
    processed: Path
    logs: Path

@dataclass
class TickerResult:
    """Resultado do processamento de um ativo."""
 
    ticker: str
    success: bool
    records: int = 0
    raw_file: Path | None = None
    processed_file: Path | None = None
    error: str | None = None


def get_project_path() -> ProjectPaths:
    root = Path(__file__).resolve().parents[1]
    return ProjectPaths(
        root=root,
        raw=root,
        raw=root / "data" /"processed",
        logs= root / "logs",
    )
    
