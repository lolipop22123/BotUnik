import os
import sys
import logging

from pathlib import Path
from loguru import logger


LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot_{time:YYYY-MM-DD}.log")
ROTATION = os.getenv("LOG_ROTATION", "10 MB")
RETENTION = os.getenv("LOG_RETENTION", "14 days")
COMPRESSION = os.getenv("LOG_COMPRESSION", "gzip")


class InterceptHandler(logging.Handler):
    """Перехватывает стандартный logging и прокидывает в loguru."""


def emit(self, record: logging.LogRecord) -> None:
    try:
        level = logger.level(record.levelname).name
    except ValueError:
        level = record.levelno
        
    frame, depth = logging.currentframe(), 2
    
    # Пропускаем внутренние фреймы logging
    while frame and frame.f_code.co_filename == logging.__file__:
        frame = frame.f_back
        depth += 1
        
    logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <7}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging() -> None:
    # Создаём папку для логов
    log_path = Path(LOG_FILE).expanduser().resolve().parent
    log_path.mkdir(parents=True, exist_ok=True)

    # Перехватываем stdlib logging
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(LEVEL)
    
    for noisy in ("aiogram", "asyncio", "sqlalchemy", "aiohttp"):
        logging.getLogger(noisy).setLevel(LEVEL)
        logging.getLogger(noisy).handlers = [InterceptHandler()]
    
    # 2) Настройки loguru: консоль + файл
    logger.remove()
    logger.add(sys.stdout, level=LEVEL, format=FORMAT, enqueue=True, backtrace=False, diagnose=False)
    logger.add(
        LOG_FILE,
        level=LEVEL,
        format=FORMAT,
        rotation=ROTATION,
        retention=RETENTION,
        compression=COMPRESSION,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )
    
    # Хук необработанных исключений → в лог
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            
            return
        
        logger.opt(exception=(exc_type, exc_value, exc_traceback)).error("Uncaught exception")

    sys.excepthook = handle_exception