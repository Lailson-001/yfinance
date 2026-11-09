"""Normalização e limpeza dos dados recebidos do Yahoo."""

import re

import pandas as pd

from .config import ACTION_COLUMNS, OHLC_COLUMNS, PRICE_COLUMNS
from .environment import logger


def _standardize_column(name: object) -> str:
    """Converte nomes como 'Adj Close' para snake_case ('adj_close')."""
    return re.sub(r"\W+", "_", str(name).strip().lower()).strip("_")


def transform_data(history: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Padroniza colunas, tipos e datas, preservando as informações válidas.

    - Colunas em snake_case; coluna `ticker` na primeira posição.
    - `date` sem fuso horário (data de negociação).
    - Preços em float64, volume em Int64 (aceita nulos), NaN mantidos.
    - Remove linhas sem preço OHLC e mantém o último registro válido por data.
    - Colunas extras fornecidas pelo Yahoo são preservadas.
    """
    records_before = len(history)

    df = history.reset_index()
    df.columns = [_standardize_column(col) for col in df.columns]
    df = df.rename(columns={"datetime": "date"})
    # Falha explícita se o provedor passar a enviar nomes que colidem.
    if not df.columns.is_unique:
        raise ValueError(f"{ticker}: colunas duplicadas após padronização")
    if "date" not in df.columns:
        raise ValueError(f"{ticker}: coluna de data não encontrada")

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()

    if df["date"].isna().any():
        raise ValueError(f"{ticker}: histórico contém datas inválidas")

    for column in [*PRICE_COLUMNS, "volume", *ACTION_COLUMNS]:
        if column not in df.columns:
            logger.warning("%s: coluna '%s' indisponível; preenchida com nulos.", ticker, column)
            df[column] = float("nan")

    for column in [*PRICE_COLUMNS, *ACTION_COLUMNS]:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("float64")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").round().astype("Int64")
    df["ticker"] = ticker

    # Filtra linhas vazias primeiro para uma duplicata sem preço
    # não apagar uma observação válida do mesmo pregão.
    empty_rows = df[OHLC_COLUMNS].isna().all(axis=1)
    df = df.loc[~empty_rows]
    duplicated = int(df.duplicated(subset="date").sum())
    df = df.drop_duplicates(subset="date", keep="last")
    df = df.sort_values("date").reset_index(drop=True)

    base = ["ticker", "date", *PRICE_COLUMNS, "volume", *ACTION_COLUMNS]
    extras = [col for col in df.columns if col not in base]
    df = df[[*base, *extras]]

    logger.debug("%s: nulos por coluna: %s", ticker, df.isna().sum().to_dict())
    logger.info(
        "%s: transformação concluída | antes=%d depois=%d (duplicadas=%d, sem preço=%d)",
        ticker, records_before, len(df), duplicated, int(empty_rows.sum()),
    )
    return df
