# backend/app/utils/logger.py
"""统一日志配置：控制台彩色输出 + 文件滚动持久化"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def get_logger(name: str) -> logging.Logger:
    """获取带统一配置的 logger，按模块名区分"""
    global _configured
    logger = logging.getLogger(name)

    if not _configured:
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(_FMT, _DATE_FMT))
        root.addHandler(console)

        file_handler = RotatingFileHandler(
            LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(_FMT, _DATE_FMT))
        root.addHandler(file_handler)

        _configured = True

    return logger
