# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import pickle
import os
from datetime import datetime

import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

folder = os.getenv("DATA_DIR")
if not os.path.exists(folder):
    os.makedirs(folder)

CBOE_INDICES = [
    # 現有
    "LONGVOL", "SHORTVOL", "VIX", "SPX", "VVIX",
    # VIX 期限結構 (McElligott 02)
    "VIX1D", "VIX9D", "VIX3M", "VIX6M", "VIX1Y",
    # 跨指數波動率 (McElligott 06)
    "RVX", "VXN",
    # 市場結構 (McElligott 01, 02)
    "SKEW", "GAMMA", "SMILE",
    # 隱含相關性 (McElligott 06)
    "COR1M", "COR3M", "COR6M", "COR1Y",
    # VRP 策略基準 (McElligott 03)
    "BXM", "PUT", "VPD", "CNDR",
    # 集中度 (McElligott 06)
    "MGTN",
    # 殖利率 (McElligott 07)
    "TNX", "TYX", "FVX", "IRX",
    # 利率波動率 (McElligott 07)
    "VXTLT",
]

CBOE_OHLC_INDICES = ["SPX", "VIX", "VVIX"]

API_URL = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_{symbol}.json"


def fetch_cboe_index(symbol):
    """Fetch CBOE index historical data from CDN JSON endpoint."""
    url = API_URL.format(symbol=symbol)
    logger.info(f"Fetching CBOE index: {url}")

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = resp.json()

    records = raw.get("data", [])
    logger.info(f"{symbol}: {len(records)} total records")

    close_data = []
    for item in records:
        dt = datetime.strptime(item["date"], "%Y-%m-%d").replace(hour=8)
        if item["close"] is not None:
            close_data.append([dt, float(item["close"])])

    pkl_path = os.path.join(folder, f"series_cboe_{symbol}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": f"CBOE {symbol}", "data": close_data}, f)
    logger.info(f"Saved {len(close_data)} records -> {pkl_path}")

    return True


def fetch_cboe_ohlc(symbol):
    """Fetch CBOE index OHLC data and save as [datetime, open, high, low, close]."""
    url = API_URL.format(symbol=symbol)
    logger.info(f"Fetching CBOE OHLC: {url}")

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    raw = resp.json()

    records = raw.get("data", [])
    logger.info(f"{symbol} OHLC: {len(records)} total records")

    ohlc_data = []
    for item in records:
        if item["close"] is None:
            continue
        dt = datetime.strptime(item["date"], "%Y-%m-%d").replace(hour=8)
        ohlc_data.append([
            dt,
            float(item["open"]),
            float(item["high"]),
            float(item["low"]),
            float(item["close"]),
        ])

    pkl_path = os.path.join(folder, f"series_cboe_{symbol}_ohlc.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": f"CBOE {symbol}", "data": ohlc_data, "ohlc": True}, f)
    logger.info(f"Saved {len(ohlc_data)} OHLC records -> {pkl_path}")

    return True


def fetch_cboe_indices():
    """Fetch all CBOE indices (close-only + OHLC)."""
    for symbol in CBOE_INDICES:
        try:
            fetch_cboe_index(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")

    for symbol in CBOE_OHLC_INDICES:
        try:
            fetch_cboe_ohlc(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch OHLC {symbol}: {e}")


if __name__ == "__main__":
    fetch_cboe_indices()
