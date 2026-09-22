# -*- coding: utf-8 -*-
"""CFTC COT 原油 Managed Money long/short/net，取代 M² sid 8297/8298/8296 (WN-2026-09-22-A批 WP-A5)。

評估：`get_ctfc_series.py` 既有的 `get_cot_data()`/`COTReportCache` 基礎設施是接 `pycot-reports`
套件的 `legacy_fut`／`traders_in_financial_futures_fut` 報告類型，這兩種報告只拆
Commercial/Non-Commercial/Non-Reportable，**沒有 Managed Money 欄位**（Managed Money 是
Disaggregated COT 報告特有的分類，2009 年才引入，供大宗商品用）。接不上既有基礎設施，
故照 WN 計畫退回 `fetch_mapped.py` 的 `fetch_cftc()` 簡化版：直接打 CFTC Socrata Disaggregated
COT API（`kh3c-gbw2` = Crude Oil Disaggregated Futures Only），免 key。
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

CFTC_URL = (
    "https://publicreporting.cftc.gov/resource/kh3c-gbw2.json?"
    "$select=report_date_as_yyyy_mm_dd,m_money_positions_long_all,m_money_positions_short_all"
    "&cftc_contract_market_code=067651"
    "&$order=report_date_as_yyyy_mm_dd DESC&$limit=600"
)

# (sid, title, field): field="long"/"short"/None(=long-short net 自算)
CRUDE_MM_SERIES = [
    (8297, "crude-oil-futures-and-options-manage-money-long-position", "long"),
    (8298, "crude-oil-futures-and-options-manage-money-short-position", "short"),
    (8296, "crude-oil-futures-and-options-manage-money-net-position", None),
]


def _fetch_crude_mm_raw() -> list:
    """單次打 API，回傳 [(date, long, short), ...] 供三條 series 共用，不重打 3 次。"""
    r = requests.get(CFTC_URL, timeout=30)
    r.raise_for_status()
    out = []
    for x in r.json():
        d = datetime.strptime(x["report_date_as_yyyy_mm_dd"][:10], "%Y-%m-%d").replace(hour=8)
        lo = x.get("m_money_positions_long_all")
        sh = x.get("m_money_positions_short_all")
        lo = float(lo) if lo not in (None, "") else None
        sh = float(sh) if sh not in (None, "") else None
        out.append((d, lo, sh))
    return out


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


def fetch_cftc_crude_mm():
    """供 get_all_series_data.py 呼叫的入口。任一 series 失敗會彙整後 raise。"""
    raw = _fetch_crude_mm_raw()
    failures = []
    for sid, title, field in CRUDE_MM_SERIES:
        name = f"CFTC crude MM {field or 'net'} (sid {sid})"
        try:
            logger.info(f"Starting: {name}")
            if field == "long":
                obs = [(d, lo) for d, lo, sh in raw if lo is not None]
            elif field == "short":
                obs = [(d, sh) for d, lo, sh in raw if sh is not None]
            else:
                obs = [(d, lo - sh) for d, lo, sh in raw if lo is not None and sh is not None]
            _save_series(sid, title, obs)
            logger.info(f"Completed: {name} (n={len(obs)})")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"CFTC crude MM 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    fetch_cftc_crude_mm()
