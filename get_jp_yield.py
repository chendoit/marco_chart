# -*- coding: utf-8 -*-
"""日本10Y殖利率 + 美日10Y利差，取代 M² sid 2018/4456 (WN-2026-09-22-A批 WP-A6)。

抓法沿用 `C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py` 的
`fetch_jpy10y()`/`fetch_jp_spread()`（已用 verify_mapped.py 驗證過）。

- sid=2018 日本10Y:財務省 jgbcme_all.csv(免key,日頻)
- sid=4456 美日10Y利差:DGS10 - sid=2018 已存的 pkl
  依賴順序:2018 必須先抓完、寫檔,4456 才能讀到當次最新的 2018 pkl,故本檔用同一個
  入口函式依序呼叫,不交給 get_all_series_data.py 的 tasks 各自獨立排程。
  DGS10 直接讀本專案 get_fed_series.py 每次排程已維護的 fed_DGS10.pkl(keyed FRED API,
  比免 key 的 fredgraph.csv 端點穩定,且不必重打一次 API);tasks 順序上
  「FRED Treasury Yields」已排在本檔之前,故執行時 fed_DGS10.pkl 一定是當次新鮮資料。
"""
import csv
import io
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

JP10Y_SID = 2018
JP10Y_TITLE = "japan-bond-10-year"
SPREAD_SID = 4456
SPREAD_TITLE = "jp-10-year-yield-spread-japan-us"

MOF_CSV_URL = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"


def _fetch_jpy10y() -> list:
    """財務省 interest rate CSV(日頻,免key)。CSV 有兩列 header:
    [Interest Rate,...] + [Date,1Y,2Y,...,10Y,...]"""
    r = requests.get(MOF_CSV_URL, timeout=60)
    r.raise_for_status()
    rows = list(csv.reader(io.StringIO(r.text)))
    header = rows[1]
    ten_idx = header.index("10Y") if "10Y" in header else 2
    out = []
    for row in rows[2:]:
        try:
            d = datetime.strptime(row[0].strip(), "%Y/%m/%d").replace(hour=8)
            v = row[ten_idx]
            if v not in (".", "", "NA", "N/A"):
                out.append((d, float(v)))
        except Exception:
            continue
    return out


def _fetch_dgs10() -> dict:
    """讀 get_fed_series.py 維護的 fed_DGS10.pkl(keyed FRED API,已由 tasks 順序保證新鮮),
    回傳 {YYYY-MM-DD: float}。"""
    path = os.path.join(DATA_DIR, "fed_DGS10.pkl")
    with open(path, "rb") as f:
        d = pickle.load(f)
    return {dt.strftime("%Y-%m-%d"): v for dt, v in d.get("data", []) if v is not None}


def _fetch_jp_spread() -> list:
    """DGS10(日頻) - 剛存好的 series_2018.pkl(日頻) → 日頻利差。"""
    dgs10 = _fetch_dgs10()
    with open(os.path.join(DATA_DIR, "series_2018.pkl"), "rb") as f:
        jp = pickle.load(f)
    jp_by_date = {d.strftime("%Y-%m-%d"): v for d, v in jp.get("data", [])}
    common = sorted(set(dgs10) & set(jp_by_date))
    return [
        (datetime.strptime(d, "%Y-%m-%d").replace(hour=8), round(dgs10[d] - jp_by_date[d], 4))
        for d in common
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


def fetch_jp_yield_and_spread():
    """供 get_all_series_data.py 呼叫的入口。2018 必須先於 4456，故不拆兩個獨立 task。"""
    logger.info("Starting: 日本10Y殖利率 (sid 2018)")
    jp10y = _fetch_jpy10y()
    _save_series(JP10Y_SID, JP10Y_TITLE, jp10y)
    logger.info(f"Completed: 日本10Y殖利率 (n={len(jp10y)})")

    logger.info("Starting: 美日10Y利差 (sid 4456)")
    spread = _fetch_jp_spread()
    _save_series(SPREAD_SID, SPREAD_TITLE, spread)
    logger.info(f"Completed: 美日10Y利差 (n={len(spread)})")


if __name__ == "__main__":
    fetch_jp_yield_and_spread()
