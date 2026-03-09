import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from rich.logging import RichHandler


class LoguruFormatter(logging.Formatter):
    """仿 loguru 的日誌格式"""

    def format(self, record):
        log_time = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        level = f"{record.levelname:<8}"
        return f"{log_time} | {level} | {record.filename}:{record.funcName}:{record.lineno} - {record.getMessage()}"


def setup_logger(name="app", log_dir="./logs", level=logging.INFO):
    """設置日誌記錄器，輸出到文件與終端"""
    os.makedirs(log_dir, exist_ok=True)

    # 構建日誌文件路徑
    log_file = os.path.join(log_dir, f"{datetime.now():%Y-%m-%d}.log")

    # 日誌格式化
    formatter = LoguruFormatter()

    # 文件處理器（每天新文件，保留 7 天）
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=7, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # 終端輸出處理器
    console_handler = RichHandler()
    console_handler.setFormatter(formatter)

    # 創建 Logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 創建全局 logger
logger = setup_logger()
