"""Diretórios do projeto e configuração de logging."""

import logging
from datetime import datetime
from pathlib import Path

from .config import LOGGER_NAME
from .models import ProjectPaths

logger = logging.getLogger(LOGGER_NAME)


def get_project_paths() -> ProjectPaths:
        # environment.py está em src/b3_pipeline/. A raiz fica dois níveis acima.
    root = Path(__file__).resolve().parents[2]
    return ProjectPaths(
        root=root,
        raw=root / "data" / "raw",
        processed=root / "data" / "processed",
        logs=root / "logs",
    )
    


def configure_logging(logs_dir: Path) -> None:
    """Configura logging em arquivo (DEBUG+) e terminal (INFO+).

    É idempotente: se o logger já possui handlers, nada é adicionado,
    evitando mensagens duplicadas.
    """
    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")

    log_file = logs_dir / f"collect_{datetime.now():%Y%m%d}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def setup_environment() -> ProjectPaths:
    """Cria as pastas necessárias (se não existirem) e configura o logging."""
    paths = get_project_paths()
    for directory in (paths.raw, paths.processed, paths.logs):
        directory.mkdir(parents=True, exist_ok=True)
    configure_logging(paths.logs)
    return paths
