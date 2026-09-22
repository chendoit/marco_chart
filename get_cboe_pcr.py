# -*- coding: utf-8 -*-
"""CBOE Put/Call Ratio (總量, sid 1650) — 雙源供料管線

來源:
  ① CBOE CDN totalpc.csv  (2006-11-01 ~ 2019-10-04 歷史段)
  ② cboe.com/markets/us/options/market-statistics/daily/?dt=YYYY-MM-DD (2019-10-07 起每日)

設計:
  - fetch_pcr_historical(): 一次性歷史回補。讀現有 pkl 找 max(datetime)，
    從 max(2019-10-07, max_pkl_date+1) 開始逐日打 daily page，
    限速 sleep 0.3~0.5s，結果 append 進 pkl。
    若舊 pkl 最後日早於 2019-10-07，先用 totalpc.csv 把 2019-10 前的歷史段補齊。
  - fetch_pcr_daily(): 每日增量。只抓最近 10 個自然日，append 進 pkl。
  - _save_pcr(): merge 舊 pkl + append 新點 → 整檔排序覆寫。嚴禁無腦覆寫。

驗證: 82 天 overlap 樣本 0% diff (series_1650.json)。
"""
import os
import re
import pickle
import time
import datetime
from pathlib import Path

import log_config  # noqa: F401
from loguru import logger
from curl_cffi import requests

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# CBOE 端點
TOTALPC_URL = (
    "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/totalpc.csv"
)
DAILY_URL_TEMPLATE = (
    "https://www.cboe.com/markets/us/options/market-statistics/daily/?dt={date}"
)

# CBOE minDate = 2019-10-07
CBOE_MIN_DATE = datetime.date(2019, 10, 7)
# totalpc.csv 結束日 = 2019-10-04
TOTALPC_END_DATE = datetime.date(2019, 10, 4)

# 正則: 從 SSR HTML payload 抽取 selectedDate 和 TOTAL PUT/CALL RATIO
# 實測 HTML 結構: optionsData\":{\"ratios\":[{\"name\":\"TOTAL PUT/CALL RATIO\",\"value\":\"0.95\"},...
#                 ...\"selectedDate\":\"2026-08-18\",...
SEL_RE = re.compile(r'selectedDate\\":\\"([0-9-]+)')
PCR_RE = re.compile(r'TOTAL PUT/CALL RATIO\\",\\"value\\":\\"([0-9.]+)')

TITLE = "us-put-call-ratio-total"


def _load_pkl() -> dict:
    """讀現有 pkl，無則回傳空結構。"""
    p = Path(folder) / "series_1650.pkl"
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    return {"title": TITLE, "data": []}


def _save_pkl(data: dict):
    """排序後覆寫 pkl。
    防呆: 新點數 < 舊 pkl 點數 50% 時拒寫(避免 API 異常清空歷史)。
    """
    out_path = Path(folder) / "series_1650.pkl"
    old_n = len(data.get("data", []))
    # 檢查是否需要防呆
    if out_path.exists():
        with open(out_path, "rb") as f:
            old = pickle.load(f)
        old_n = len(old.get("data", []))
        if old_n > 0 and len(data["data"]) < old_n * 0.5:
            raise RuntimeError(
                f"series_1650: new n={len(data['data'])} < 50% of old n={old_n}, skip write"
            )
    # 排序: 按 datetime 升冪
    data["data"] = sorted(data["data"], key=lambda x: x[0])
    with open(out_path, "wb") as f:
        pickle.dump(data, f)
    logger.info(
        f"series_1650.pkl saved: n={len(data['data'])}, "
        f"last={data['data'][-1][0]:%Y-%m-%d 08:00:00}"
    )


def _fetch_totalpc() -> dict:
    """從 totalpc.csv 抓 2006-11-01 ~ 2019-10-04 歷史段。回傳 {date: ratio}。"""
    out = {}
    try:
        resp = requests.get(TOTALPC_URL, impersonate="chrome", timeout=30)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                line = line.strip()
                if "/" not in line or "," not in line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) < 5:
                    continue
                try:
                    m, d, y = parts[0].split("/")
                    dt = datetime.date(int(y), int(m), int(d))
                    v = float(parts[4])
                except (ValueError, IndexError):
                    continue
                if datetime.date(2006, 11, 1) <= dt <= TOTALPC_END_DATE:
                    out[dt] = v
        logger.info(f"totalpc.csv loaded: {len(out)} points ({min(out)} ~ {max(out)})")
    except Exception as e:
        logger.warning(f"totalpc.csv fetch failed: {e}")
    return out


def _fetch_daily(dt: datetime.date) -> float | None:
    """從 CBOE Daily Market Statistics 頁抓單日 PCR。
    若該日無資料(selectedDate 被 reset 或 optionsData 為 null)，回傳 None。
    """
    try:
        url = DAILY_URL_TEMPLATE.format(date=dt.isoformat())
        resp = requests.get(url, impersonate="chrome", timeout=30)
        if resp.status_code != 200:
            return None
        text = resp.text
        # 驗 selectedDate == 要求日期(若被 reset 代表無資料)
        sel = SEL_RE.search(text)
        if not sel or sel.group(1) != dt.isoformat():
            return None
        # 驗 optionsData 不是 null(有比率資料)
        # 若 optionsData 為 null, TOTAL PUT/CALL RATIO 不會出現
        tot = PCR_RE.search(text)
        if not tot:
            return None
        return float(tot.group(1))
    except Exception:
        return None


def _collect_obs(pcr_dict: dict) -> list:
    """把 {date: ratio} 轉成 [[datetime(08:00), float], ...] 格式。"""
    obs = []
    for d, v in pcr_dict.items():
        obs.append([datetime.datetime(d.year, d.month, d.day, 8, 0), v])
    return obs


def fetch_pcr_historical(sleep_min: float = 0.3, sleep_max: float = 0.5):
    """一次性歷史回補(約 2500 請求, 15-20 分鐘)。
    
    邏輯:
    1. 讀舊 pkl, 合併 totalpc.csv 完整歷史段(2006-11~2019-10-04)
    2. 從 2019-10-07(minDate) 開始, 逐日打 daily page 到昨天
    3. merge 全部 → 排序覆寫 pkl
    """
    import random
    data = _load_pkl()
    old_n = len(data.get("data", []))
    logger.info(f"Starting historical backfill. Old pkl n={old_n}")

    # 找出舊 pkl 已有的日期集合
    existing_dates = set()
    for pt in data.get("data", []):
        existing_dates.add(pt[0].date())

    # 步驟 A: 用 totalpc.csv 補齊 2006-11~2019-10-04 段(不管舊 pkl 有沒有)
    logger.info("Merging totalpc.csv historical segment (2006-11 ~ 2019-10-04)...")
    tc = _fetch_totalpc()
    new_from_csv = 0
    for d, v in tc.items():
        if d not in existing_dates:
            data.setdefault("data", []).append(
                [datetime.datetime(d.year, d.month, d.day, 8, 0), v]
            )
            existing_dates.add(d)
            new_from_csv += 1
    logger.info(f"totalpc.csv: {new_from_csv} new points added")
    _save_pkl(data)

    # 步驟 B: 從 2019-10-07(minDate) 開始逐日打 daily page 到昨天
    start_date = CBOE_MIN_DATE
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    if start_date > end_date:
        logger.info(f"No dates to backfill ({start_date} > {end_date}). Already up to date.")
        return

    logger.info(f"Backfilling daily page: {start_date} ~ {end_date}")
    d = start_date
    new_count = 0
    skip_count = 0
    while d <= end_date:
        # 檢查是否已有這天
        if d in existing_dates:
            d += datetime.timedelta(days=1)
            continue
        v = _fetch_daily(d)
        if v is not None:
            data.setdefault("data", []).append([datetime.datetime(d.year, d.month, d.day, 8, 0), v])
            existing_dates.add(d)
            new_count += 1
        else:
            # 可能是假日/無資料
            skip_count += 1
        # 限速
        time.sleep(random.uniform(sleep_min, sleep_max))
        d += datetime.timedelta(days=1)

        # 每 100 筆 log 一次進度
        if (new_count + skip_count) % 100 == 0:
            logger.info(f"Progress: {new_count} new, {skip_count} skipped, ~{d}")

    _save_pkl(data)
    logger.info(
        f"Historical backfill done. New: {new_count}, Skipped: {skip_count}, "
        f"Total now: {len(data['data'])}"
    )


def fetch_pcr_daily(days: int = 10):
    """每日增量: 抓最近 `days` 個自然日, append 進 pkl。
    
    只打未有的日期, skip 已有/假日。
    """
    data = _load_pkl()
    existing_dates = {pt[0].date() for pt in data.get("data", [])}
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=days)

    new_count = 0
    for d in [start_date + datetime.timedelta(days=i) for i in range(days + 1)]:
        if d in existing_dates or d > end_date:
            continue
        v = _fetch_daily(d)
        if v is not None:
            data.setdefault("data", []).append([datetime.datetime(d.year, d.month, d.day, 8, 0), v])
            new_count += 1
        time.sleep(0.3)

    _save_pkl(data)
    logger.info(f"Daily incremental: {new_count} new points added. Total: {len(data['data'])}")


# ============================================================================
# JOBS + 入口
# ============================================================================
JOBS = [
    ("PCR historical backfill", fetch_pcr_historical),
]


def fetch_cboe_pcr_main():
    """供 get_all_series_data.py 呼叫的入口。
    預設跑每日增量; 若要歷史回補, 直接呼叫 fetch_pcr_historical()。
    """
    failures = []
    # 每日增量 (排程用)
    for name, fn in [("PCR daily increment", fetch_pcr_daily)]:
        try:
            logger.info(f"Starting: {name}")
            fn()
            logger.info(f"Completed: {name}")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(f"PCR fetch failures:\n" + "\n".join(failures))


if __name__ == "__main__":
    # python get_cboe_pcr.py  → 跑每日增量
    # python get_cboe_pcr.py historical  → 跑歷史回補
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "historical":
        fetch_pcr_historical()
    else:
        fetch_pcr_daily()
