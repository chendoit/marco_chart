"""集中式 loguru 設定。

所有抓取腳本不要再各自呼叫 logger.add()（loguru 的 add 是「再加一個 sink」，
多個模組各 add 一次指向同一檔案會導致每筆訊息重複寫入 N 次）。
統一在模組頂層 `import log_config` 即可：本模組以模組層旗標保證只掛一次 sink。

日誌檔：<專案根>/logs/{time:YYYY-MM-DD}.log，保留 1 個月，gz 壓縮。
"""
import os

from loguru import logger

_SINK_REGISTERED = False

if not _SINK_REGISTERED:
    _LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(_LOG_DIR, exist_ok=True)
    logger.add(
        os.path.join(_LOG_DIR, "{time:YYYY-MM-DD}.log"),
        enqueue=True,
        retention="1 month",
        compression="gz",
    )
    _SINK_REGISTERED = True
