import logging
from pathlib import Path


def setup_logging(out_dir: str, log_level: str) -> None:
    """
    Configura el logging para la aplicación.

    Args:
        out_dir: Directorio base para logs.
        log_level: Nivel de logging (ej: 'DEBUG', 'INFO').
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    # Handler de archivo para errores
    error_log_file = Path(out_dir) / "log_error.txt"
    error_log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(error_log_file, mode="w")
    file_handler.setLevel(logging.ERROR)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logging.getLogger().addHandler(file_handler)
