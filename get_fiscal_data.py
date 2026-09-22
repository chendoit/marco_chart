# -*- coding: utf-8 -*-
"""Fiscal Data API (財政部一般帳戶 TGA)，取代 M² sid 29123 (WN-2026-09-22-A批 WP-A4)。

抓法沿用 `C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py` 的 `fetch_tga()`
（已用 verify_mapped.py 驗證過），免 key。
"""
import os
import pickle
from datetime import datetime

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

TGA_SID = 29123
TGA_TITLE = "us-treasury-general-account-daily"
TGA_URL = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/"
    "operating_cash_balance"
    "?filter=account_type:eq:Treasury%20General%20Account%20(TGA)%20Closing%20Balance"
    "&sort=-record_date&page%5Bsize%5D=10000"
)


def _fetch_tga() -> list:
    r = requests.get(TGA_URL, timeout=30)
    r.raise_for_status()
    rows = r.json()["data"]
    return [
        (datetime.strptime(x["record_date"], "%Y-%m-%d").replace(hour=8), float(x["open_today_bal"]))
        for x in rows
        if x.get("open_today_bal")
    ]


def _save_series(sid: int, title: str, obs: list):
    """逐日期 merge 存檔（同 get_yfinance_series.py／get_fred_csv.py 的防呆邏輯）。"""
    out_file = os.path.join(DATA_DIR, f"series_{sid}.pkl")
    old_data = []
    if os.path.exists(out_file):
        try:
            with open(out_file, "rb") as f:
                old = pickle.load(f)
            old_data = old.get("data", []) if isinstance(old, dict) else []
        except Exception:
            old_data = []
    merged = {d.date(): (d, v) for d, v in old_data}
    merged.update({d.date(): (d, v) for d, v in obs})
    lost = set(d.date() for d, v in old_data) - set(merged)
    assert not lost, f"series_{sid}: 資料倒退！遺失 {len(lost)} 個舊日期: {sorted(lost)[:5]}"
    rows = sorted(merged.values(), key=lambda x: x[0])
    with open(out_file, "wb") as f:
        pickle.dump({"title": title, "data": [[d, v] for d, v in rows]}, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(rows)} (old n={len(old_data)}, new n={len(obs)})"
    )


def fetch_fiscal_data():
    """供 get_all_series_data.py 呼叫的入口。"""
    logger.info("Starting: Fiscal Data TGA (sid 29123)")
    obs = _fetch_tga()
    _save_series(TGA_SID, TGA_TITLE, obs)
    logger.info(f"Completed: Fiscal Data TGA (n={len(obs)})")


if __name__ == "__main__":
    fetch_fiscal_data()
