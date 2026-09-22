# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import io
import os
import pickle
from datetime import datetime

import pandas as pd
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

NFCI_CSV_URL = "https://api.data.chicagofed.org/NFCI/nfci-data-series-csv.csv"
OFR_FSI_CSV_URL = "https://www.financialresearch.gov/financial-stress-index/data/fsi.csv"

SERIES = {
    "chicagofed_NFCI": {
        "url": NFCI_CSV_URL,
        "title": "芝加哥聯儲 NFCI (National Financial Conditions Index)",
        "date_col": "Friday_of_Week",
        "value_col": "NFCI",
        "date_format": "%m/%d/%Y",
    },
    "ofr_FSI_US": {
        "url": OFR_FSI_CSV_URL,
        "title": "OFR FSI 美國 (United States)",
        "date_col": "Date",
        "value_col": "United States",
        "date_format": "%Y-%m-%d",
    },
}


def _save_series(series_id, title, series_data):
    pkl_path = os.path.join(DATA_DIR, f"{series_id}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": title, "data": series_data}, f)
    logger.info(f"Saved {len(series_data)} records -> {pkl_path}")


def _fetch_csv_series(series_id, cfg):
    logger.info(f"Downloading {series_id}: {cfg['url']}")
    resp = requests.get(cfg["url"], timeout=120)
    resp.raise_for_status()
    logger.info(f"Downloaded {len(resp.content)} bytes")

    df = pd.read_csv(io.StringIO(resp.text))
    if cfg["date_col"] not in df.columns or cfg["value_col"] not in df.columns:
        raise ValueError(
            f"{series_id}: missing columns. got {list(df.columns)}"
        )

    series_data = []
    for _, row in df.iterrows():
        val = row[cfg["value_col"]]
        if pd.isna(val):
            continue
        dt = pd.to_datetime(row[cfg["date_col"]], format=cfg["date_format"])
        series_data.append([dt.to_pydatetime().replace(hour=8), float(val)])

    series_data.sort(key=lambda x: x[0])
    _save_series(series_id, cfg["title"], series_data)
    if series_data:
        logger.info(
            f"{series_id}: {series_data[0][0].date()} ~ {series_data[-1][0].date()}"
        )


def fetch_financial_stress():
    """Download Chicago Fed NFCI and OFR FSI (US) CSV, save as pkl."""
    for series_id, cfg in SERIES.items():
        _fetch_csv_series(series_id, cfg)


if __name__ == "__main__":
    fetch_financial_stress()
