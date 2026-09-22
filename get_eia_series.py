# -*- coding: utf-8 -*-
"""EIA API (原油庫存/戰略儲備)，取代 M² sid 854/19080 (WN-2026-09-22-A批 WP-A7)。

抓法沿用 `C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py` 的 `fetch_eia()`
（已用 verify_mapped.py 驗證過，含 period 解析、正確 series id 兩個 bug 修正）。
需要 `EIA_API_KEY`（.env 已提供，2026-09-15 gate G0）。
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

# (sid, EIA series id, title)
EIA_SERIES = [
    (854, "PET.WCESTUS1.W", "us-oil-inventory"),
    (19080, "PET.MCSSTUS1.M", "us-strategic-petroleum-reserve"),
]


def _fetch_eia(series_id: str) -> list:
    key = os.getenv("EIA_API_KEY", "")
    if not key:
        raise RuntimeError("EIA_API_KEY not found in .env")
    url = f"https://api.eia.gov/v2/seriesid/{series_id}?api_key={key}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data_list = r.json().get("response", {}).get("data", [])
    # EIA v2 period 格式:YYYY / YYYY-MM / YYYY-MM-DD(ISO,非緊湊)
    out = []
    for x in data_list:
        period = x.get("period", "").strip()
        try:
            if len(period) == 4:  # yearly
                dt = datetime(int(period), 1, 1, 8)
            elif len(period) == 7:  # monthly YYYY-MM
                dt = datetime.strptime(period, "%Y-%m").replace(day=1, hour=8)
            elif len(period) == 10:  # weekly/daily YYYY-MM-DD
                dt = datetime.strptime(period, "%Y-%m-%d").replace(hour=8)
            else:
                continue
            out.append((dt, float(x["value"])))
        except Exception:
            continue
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


def fetch_eia_series():
    """供 get_all_series_data.py 呼叫的入口。任一抓取失敗會彙整後 raise。"""
    failures = []
    for sid, series_id, title in EIA_SERIES:
        name = f"EIA {series_id} (sid {sid})"
        try:
            logger.info(f"Starting: {name}")
            obs = _fetch_eia(series_id)
            _save_series(sid, title, obs)
            logger.info(f"Completed: {name} (n={len(obs)})")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"EIA 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    fetch_eia_series()
