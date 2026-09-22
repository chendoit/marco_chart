# -*- coding: utf-8 -*-
"""FRED fredgraph.csv 免 key 端點，接管 3 條 M² series (sid 261/4/7249)

來源: migration/reference_fetchers/04_fred_csv.py 已驗證函式
- sid=261 Case-Shiller 20城(SA) → FRED SPCS20RSA, 月頻, ok
- sid=4 美國實質 GDP 年增 → FRED GDPC1 自算 YoY, 季頻, ok
- sid=7249 NY Fed WEI → FRED WEI, 日頻(週六), approx(early revision)

備份: C:/Users/chendoit/AppData/Local/Temp/pkl_backup_04/
"""

import csv
import io
import os
import pickle
from datetime import datetime

from loguru import logger

import log_config  # noqa: F401

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# title 對照表:沿用舊 pkl 顯示名稱(儀表板圖例/軸標題用),一字不改
TITLE_MAP = {
    261: "sp-case-shillar-20-home-price",
    4: "realgdp-yoy",
    7249: "fereral-reserve-bank-of-new-york-weekly-economic-index",
}


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


# ============================================================================
# sid=261  Case-Shiller 20城(SA)  [ok]
# 來源: FRED SPCS20RSA, fredgraph.csv 免 key, 月頻
# ============================================================================
import requests


def fetch_sp_case_shiller_20_sa():
    """FRED SPCS20RSA: S&P Cotality Case-Shiller 20-City Composite Home Price Index
    (SA, Index Jan 2000=100). 月頻, 回傳 [(datetime 08:00, float), ...]
    備註: 舊 pkl 停在 2024-11(n=299),新源接上後歷史補滿至 2000-01 起(全期約 318 點)。
    與舊 pkl 最大絕對差 0.135%,屬 S&P revision,同口徑。"""
    r = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SPCS20RSA", timeout=120
    )
    r.raise_for_status()
    lines = r.text.strip().splitlines()
    out = []
    for line in lines[1:]:  # 第一行是 header 'SPCS20RSA' 或 'date,SPCS20RSA'
        parts = line.split(",")
        d, v = parts[0], parts[-1]
        if v in (".", ""):
            continue
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=8)
            out.append((dt, float(v)))
        except ValueError:
            continue
    return out


# ============================================================================
# sid=4  美國實質 GDP 年增  [ok]
# 來源: FRED GDPC1 (Real GDP SAAR, 2017=100), 自算 YoY
# ============================================================================


def fetch_realgdp_yoy():
    """sid=4 realgdp-yoy: FRED GDPC1 季頻 SAAR 指數, YoY = 本季/前四季-1。
    回傳 [(datetime, float), ...] (08:00, 當季首日)。
    備註: 需前四季,故輸出從 1948-01 起算(GDPC1 原始 1947-01 起),
    與舊 pkl 起點一致(108 點,1948-01~2026-04)。"""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(r.text)))
    vals = [(x["observation_date"], float(x["GDPC1"])) for x in rows]
    out = []
    for i in range(4, len(vals)):
        d, v = vals[i]
        d0, v0 = vals[i - 4]
        if d[5:7] != d0[5:7]:  # 缺季防護
            continue
        y = (v / v0 - 1) * 100
        dt = datetime(int(d[:4]), int(d[5:7]), 1, 8, 0)
        out.append((dt, round(y, 2)))
    return out


# ============================================================================
# sid=7249  NY Fed WEI  [approx]
# 來源: FRED WEI (Weekly Economic Index, 原 NY Fed, 2023-12 起改由 Dallas Fed 維護)
# ============================================================================


def fetch_series_7249():
    """sid=7249 NY Fed WEI: FRED fredgraph.csv, 免 key、週頻(週六)、單位=四季GDP成長率年化%。
    ⚠️ approx: M² 存的是「當時抓取未 revise 的快照」,FRED current 值在 2008~2024 早期
    與舊 pkl 最大差 125%,但 2024-06 之後尾端完全吻合。
    寫 pkl 時整條以 FRED current 值為準(新歷史比舊快照正確),此差異已標記 approx。"""
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WEI"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    data = []
    for row in csv.DictReader(io.StringIO(r.text)):
        d = datetime.strptime(row["observation_date"], "%Y-%m-%d")
        data.append((d.replace(hour=8, minute=0), float(row["WEI"])))
    return data


JOBS = [
    ("FRED SPCS20RSA (sid 261, Case-Shiller 20城 SA)", 261, fetch_sp_case_shiller_20_sa),
    ("FRED GDPC1 YoY (sid 4, 美國實質 GDP 年增)", 4, fetch_realgdp_yoy),
    ("FRED WEI (sid 7249, NY Fed WEI)", 7249, fetch_series_7249),
]


def fetch_fred_csv():
    """供 get_all_series_data.py 呼叫的入口。任一 series 失敗會彙整後 raise,
    交由 orchestrator 記入 error_history(不再像舊腳本吞錯)。"""
    failures = []
    for name, sid, fn in JOBS:
        try:
            logger.info(f"Starting: {name}")
            obs = fn()
            _save_series(sid, obs)
            logger.info(f"Completed: {name}")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            "FRED csv 抓取失敗 %d 項:\n%s" % (len(failures), "\n".join(failures))
        )


if __name__ == "__main__":
    fetch_fred_csv()
