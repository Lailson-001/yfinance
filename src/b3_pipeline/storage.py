"""Persistência dos CSVs brutos e dos Parquets processados."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd

from .config import DEFAULT_INTERVAL
from .environment import logger


def _ticker_slug(ticker: str) -> str:
    """Converte 'PETR4.SA' em 'PETR4_SA' para uso em nomes de arquivo."""
    return ticker.replace(".", "_")


@contextmanager
def _atomic_output(path: Path) -> Iterator[Path]:
    """Publica o arquivo somente depois que o conteúdo foi gravado."""
    # Temporários exclusivos evitam colisões entre execuções. Usar a mesma
    # pasta permite substituir o destino atomicamente no mesmo filesystem.
    with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        yield temp_path
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def save_raw_data(
    history: pd.DataFrame, ticker: str, interval: str, raw_dir: Path, run_id: str
) -> Path:
    """Salva os dados originais (sem alterações) em CSV.

    Estratégia anti-sobrescrita: o nome inclui o identificador da execução,
    então cada coleta gera um arquivo novo e nada é perdido.
    """
    filename = f"{_ticker_slug(ticker)}_{interval}_{run_id}.csv"
    path = raw_dir / filename
    with _atomic_output(path) as temp_path:
        history.to_csv(temp_path)
    logger.info("%s: dados brutos salvos em %s", ticker, path)
    return path


def save_parquet(df: pd.DataFrame, ticker: str, interval: str, processed_dir: Path) -> Path:
    """Salva o DataFrame em Parquet de forma atômica.

    Estratégia de nomes: `PETR4_SA.parquet` para o intervalo padrão (1d) e
    `PETR4_SA_1wk.parquet` para os demais. O arquivo processado é
    determinístico e sobrescrito de propósito (o bruto mantém o histórico);
    a escrita usa arquivo temporário para nunca deixar um Parquet corrompido.
    """
    suffix = "" if interval == DEFAULT_INTERVAL else f"_{interval}"
    path = processed_dir / f"{_ticker_slug(ticker)}{suffix}.parquet"
    if path.exists():
        logger.warning("%s: arquivo existente será substituído: %s", ticker, path)

    with _atomic_output(path) as temp_path:
        df.to_parquet(temp_path, engine="pyarrow", index=False)
    logger.info("%s: Parquet salvo em %s (%d registros)", ticker, path, len(df))
    return path
