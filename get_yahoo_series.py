# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
"""M² 系列改用 Yahoo Finance 免費源的替代 fetcher。

評估背景見 C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/
01_yahoo_finance_work_note.md（2026-09-16 決策：僅 17581 MOVE 指數執行替換，
sid 0/18331/22718/3776 維持原 M² 抓法）。
"""
import os
import pickle
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 日期檔日誌已集中設定於 log_config.py，本檔「禁止」再呼叫 logger.add()，
# 否則多個 sink 指向同一 log 檔，每筆訊息會重複寫入 N 次（2026-09 已踩過此坑）。

DATA_DIR = os.getenv("DATA_DIR")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

MOVE_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5EMOVE"


def fetch_move_index():
    """sid=17581 us-treasury-move-index。改用 Yahoo Finance ^MOVE chart API v8（免 key、
    免 M² 登入/Playwright）。與舊 M² pkl 全期重疊日期驗證 0 誤差（見 work note）。"""
    logger.info(f"Downloading MOVE index: {MOVE_CHART_URL}")
    resp = requests.get(
        MOVE_CHART_URL,
        params={"period1": 0, "period2": int(time.time()), "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]

    series_data = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        d = datetime.fromtimestamp(ts, tz=timezone.utc)
        dt = datetime(d.year, d.month, d.day, 8, 0)
        series_data.append([dt, round(float(close), 2)])

    series_data.sort(key=lambda x: x[0])

    pkl_path = os.path.join(DATA_DIR, "series_17581.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": "us-treasury-move-index", "data": series_data}, f)
    logger.info(f"Saved {len(series_data)} records -> {pkl_path}")
    if series_data:
        logger.info(f"series_17581: {series_data[0][0].date()} ~ {series_data[-1][0].date()}")


if __name__ == "__main__":
    fetch_move_index()
