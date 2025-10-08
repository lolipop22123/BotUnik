# services/logger.py
import logging
import os
import sys
from pathlib import Path
from loguru import logger

LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot_{time:YYYY-MM-DD}.log")
ROTATION = os.getenv("LOG_ROTATION", "10 MB")
RETENTION = os.getenv("LOG_RETENTION", "14 days")
COMPRESSION = os.getenv("LOG_COMPRESSION", "gz")

FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <7}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

def _normalize_compression(value: str | None):
    if not value:
        return None
    m = value.strip().lower()
    if m in ("none", "off", "false", "0"):  # отключить компрессию
        return None
    mapping = {
        "gzip": "gz", "gz": "gz",
        "bzip2": "bz2", "bz2": "bz2",
        "xz": "xz",
        "zip": "zip",
        "tar": "tar",
        "tar.gz": "tar.gz", "tgz": "tar.gz",
        "tar.bz2": "tar.bz2", "tbz2": "tar.bz2",
        "tar.xz": "tar.xz", "txz": "tar.xz",
    }
    return mapping.get(m, m)

class InterceptHandler(logging.Handler):
    """Прокидываем stdlib logging в loguru."""
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # чуть глубже стека, чтобы правильно показать место вызова
        logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

def setup_logging() -> None:
    # 0) Создать папку для логов
    Path(LOG_FILE).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)

    # 1) Настроить loguru (консоль + файл)
    logger.remove()
    logger.add(sys.stdout, level=LEVEL, format=FORMAT, enqueue=True, backtrace=False, diagnose=False)
    logger.add(
        LOG_FILE,
        level=LEVEL,
        format=FORMAT,
        rotation=ROTATION,
        retention=RETENTION,
        compression=_normalize_compression(COMPRESSION),
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    # 2) Жёстко перехватить stdlib logging
    #    force=True сбрасывает все обработчики root-логгера
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 3) Пройтись по всем логгерам и убрать их хендлеры, включить propagate
    #    (чтобы они шли вверх в root → наш InterceptHandler → loguru)
    for name, obj in logging.Logger.manager.loggerDict.items():
        if isinstance(obj, logging.Logger):
            obj.handlers.clear()
            obj.propagate = True

    # 4) Хук необработанных исключений → в loguru
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Uncaught exception")
    sys.excepthook = handle_exception
