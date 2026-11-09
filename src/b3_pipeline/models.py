"""Tipos compartilhados entre as etapas do pipeline."""

from dataclasses import dataclass
from pathlib import Path


class DownloadError(Exception):
    """Falha ao baixar dados após esgotar as tentativas."""


class NoDataError(Exception):
    """O Yahoo Finance não retornou nenhum registro para o ativo/período."""


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
