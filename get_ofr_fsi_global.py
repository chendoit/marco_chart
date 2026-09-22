# -*- coding: utf-8 -*-
# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 取代 get_m_square_series.py 中的 sid 4869(全球 OFR FSI)。
# 資料源:OFR(Office of Financial Research)官方 CSV
#   https://www.financialresearch.gov/financial-stress-index/data/fsi.csv
# 欄位:Date + "OFR FSI"(World 版本)
# 備注:同 sid 4869(get_financial_stress.py 抓的是 ofr_FSI_US 美國版,並存不衝突)
#
# 覆蓋範圍(1 條 pkl):
#   sid 4869 全球 OFR FSI → series_4869.pkl

import os
import pickle
from datetime import datetime

import requests
from loguru import logger

import log_config  # noqa: F401  # [日誌規範] 統一由 log_config 設定,本檔禁止再呼叫 logger.add()

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# title 對照表:沿用舊 pkl 顯示名稱(儀表板圖例/軸標題用),不要留空
TITLE_MAP = {
    4869: "global-ofr-fsi",
}

OFR_FSI_GLOBAL_URL = (
    "https://www.financialresearch.gov/financial-stress-index/data/fsi.csv"
)


def _save_series(sid, obs):
    """寫出 {'title', 'data': [[datetime(08:00), float], ...]} 格式 pkl,同舊格式。
    防呆:新點數少於既有 pkl 的一半時不覆寫(避免 API 異常清空歷史)。"""
    out_file = os.path.join(folder, f"series_{sid}.pkl")
    old = None
    if os.path.exists(out_file):
        with open(out_file, "rb") as f:
            old = pickle.load(f)
    old_n = len(old.get("data", [])) if isinstance(old, dict) else 0
    if old and len(obs) < old_n * 0.5:
        raise RuntimeError(
            f"series_{sid}: new data n={len(obs)} < 50% of existing n={old_n}, skip write"
        )
    data = {"title": TITLE_MAP.get(sid, str(sid)), "data": [[d, v] for d, v in obs]}
    with open(out_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(obs)} last={obs[-1][0]:%Y-%m-%d} (old n={old_n})"
    )


def fetch_ofr_fsi_global():
    """Fetch OFR Financial Stress Index (global/World) daily CSV, save as series_4869.pkl.

    DictReader 取 Date + 'OFR FSI' 欄位(World 版本),datetime 統一 08:00。
    """
    resp = requests.get(OFR_FSI_GLOBAL_URL, timeout=30)
    resp.raise_for_status()

    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(resp.text))
    obs = []
    for row in reader:
        date_str = row["Date"]
        val = float(row["OFR FSI"])
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=8)
        obs.append((dt, val))

    obs.sort(key=lambda x: x[0])
    _save_series(4869, obs)
    logger.info(f"fetch_ofr_fsi_global: {len(obs)} records, last={obs[-1][0]:%Y-%m-%d}")
    return obs


JOBS = [
    ("OFR FSI global (sid 4869)", fetch_ofr_fsi_global),
]


def fetch_ofr_fsi_global_main():
    """供 get_all_series_data.py 呼叫的入口。任一失敗彙整後 raise。"""
    failures = []
    for name, fn in JOBS:
        try:
            logger.info(f"Starting: {name}")
            fn()
            logger.info(f"Completed: {name}")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            "OFR FSI global 抓取失敗 %d 項:\n%s" % (len(failures), "\n".join(failures))
        )


if __name__ == "__main__":
    fetch_ofr_fsi_global_main()
