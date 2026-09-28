# -*- coding: utf-8 -*-
"""FRED fredgraph.csv 免 key 端點，接管 M² series (sid 261/4/7249 + WN-2026-09-22-A批 WP-A1/A1b)

來源: migration/reference_fetchers/04_fred_csv.py 已驗證函式
- sid=261 Case-Shiller 20城(SA) → FRED SPCS20RSA, 月頻, ok
- sid=4 美國實質 GDP 年增 → FRED GDPC1 自算 YoY, 季頻, ok
- sid=7249 NY Fed WEI → FRED WEI, 日頻(週六), approx(early revision)

WP-A1（11 條直接對應）+ WP-A1b（1 條拼接）：抓法沿用
`C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py` 的 `fetch_fred()`/`fetch_246_splice()`
（已用 verify_mapped.py 驗證過），改走本檔既有的免 key fredgraph.csv 端點。

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
    36: "continuedclaims",
    34: "initialclaims",
    37: "unemployment-rate",
    22910: "sahm-rule-recession-indicator",
    255: "price-new-houses",
    755: "delinquency-rate-on-business-loans",
    634: "bofa-merrill-lynch-us-corporate-ccc",
    319: "durable-goods",
    7449: "us-fed-excess-reserves-weekly",
    348: "pce-core-price-yoy",
    560: "real-disposable-personal-income-yoy",
    246: "existing-home-sales-yoy",
    8219: "us-wti-crude-oil-spot-price-daily",
    3612: "us-credit-spread",
    93001: "us-bbb-credit-spread",
    93002: "us-aaa-credit-spread",
}


def _save_series(sid, obs):
    """逐日期 merge 存檔:新舊資料以日期 union,同日期新值覆蓋,其餘舊點全保留。
    `lost`(union 後仍缺失的舊日期)理論上必為空集合,用 assert 當防呆而非事後檢查。
    (2026-09-22 由整批覆寫+筆數防呆改為逐日期 merge:WP-A2 實測發現某些新來源可回溯的
    歷史範圍比舊 pkl 短,筆數防呆抓不到「新資料筆數變多但早期歷史被默默丟掉」這種情況。)"""
    out_file = os.path.join(folder, f"series_{sid}.pkl")
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
    data = {"title": TITLE_MAP.get(sid, str(sid)), "data": [[d, v] for d, v in rows]}
    with open(out_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(rows)} (old n={len(old_data)}, new n={len(obs)}) "
        f"range={rows[0][0]:%Y-%m-%d}~{rows[-1][0]:%Y-%m-%d}"
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


# ============================================================================
# WP-A1: 11 條直接對應 FRED series (raw,免轉換)
# ============================================================================


def _fetch_fred_direct(series_id: str) -> list:
    """單一 FRED series 的 fredgraph.csv 直接取值,不做任何轉換。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        v = row.get(series_id)
        if v in (None, ".", ""):
            continue
        d = datetime.strptime(row["observation_date"], "%Y-%m-%d").replace(hour=8)
        out.append((d, float(v)))
    return out


def _fetch_fred_yoy(series_id: str) -> list:
    """單一 FRED series 的 fredgraph.csv,自算月頻 YoY(本月/去年同月-1)。"""
    pts = _fetch_fred_direct(series_id)
    by_month = {d.strftime("%Y-%m"): v for d, v in pts}
    keys = sorted(by_month)
    out = []
    for i, k in enumerate(keys):
        if i < 12:
            continue
        prev = by_month[keys[i - 12]]
        if prev:
            y, m = int(k[:4]), int(k[5:7])
            out.append((datetime(y, m, 1, 8), round((by_month[k] / prev - 1) * 100, 4)))
    return out


# ============================================================================
# WP-A1b: sid=246 成屋銷售 YoY 拼接
# FRED EXHOSLUSM495S 是 2025-08 才建立的新 series(舊 EXHOSLUS 已下架),
# 重疊段(2025-08~)以 FRED 自算 YoY 為準,之前沿用舊 pkl 既有值(M² 計算的 YoY)。
# ============================================================================


def fetch_246_splice() -> list:
    fred_yoy = {d.strftime("%Y-%m"): v for d, v in _fetch_fred_yoy("EXHOSLUSM495S")}
    old_file = os.path.join(folder, "series_246.pkl")
    old_by_month = {}
    if os.path.exists(old_file):
        with open(old_file, "rb") as f:
            old = pickle.load(f)
        old_by_month = {d.strftime("%Y-%m"): v for d, v in old.get("data", [])}
    out = []
    for m in sorted(set(old_by_month) | set(fred_yoy)):
        v = fred_yoy.get(m, old_by_month.get(m))
        if v is not None:
            y, mo = int(m[:4]), int(m[5:7])
            out.append((datetime(y, mo, 1, 8), v))
    return out


# ============================================================================
# 美國信用風險利差(M² chart 930)= ICE BofA 各評級實際殖利率 - DGS10(不是 OAS)
# sid 3612 = CCC;BBB / AAA 在 M² 沒有 sid,自編 93001 / 93002(chart 930 series[1]/[2])
# FRED 的 ICE BofA 序列只給近 3 年,更早的歷史靠 _save_series 按日期 merge 保留舊 pkl
# (3612 舊 pkl、93001/93002 初始值皆來自 M² chart 930,2026-09-28 一次性回填)。
# 與 M² 重疊 749 日最大差 0.075:M² 的 10Y 有 3 位小數,DGS10 只有 2 位。
# ============================================================================


def _fetch_credit_spread(ey_id: str) -> list:
    ey = dict(_fetch_fred_direct(ey_id))
    t10 = dict(_fetch_fred_direct("DGS10"))
    return [(d, round(ey[d] - t10[d], 4)) for d in sorted(ey) if d in t10]


JOBS = [
    ("FRED SPCS20RSA (sid 261, Case-Shiller 20城 SA)", 261, fetch_sp_case_shiller_20_sa),
    ("FRED GDPC1 YoY (sid 4, 美國實質 GDP 年增)", 4, fetch_realgdp_yoy),
    ("FRED WEI (sid 7249, NY Fed WEI)", 7249, fetch_series_7249),
    # WP-A1 (WN-2026-09-22-A批)
    ("FRED CCSA (sid 36, 連續申請失業金)", 36, lambda: _fetch_fred_direct("CCSA")),
    ("FRED ICSA (sid 34, 初次申請失業金)", 34, lambda: _fetch_fred_direct("ICSA")),
    ("FRED UNRATE (sid 37, 失業率)", 37, lambda: _fetch_fred_direct("UNRATE")),
    ("FRED SAHMREALTIME (sid 22910, 薩姆規則)", 22910, lambda: _fetch_fred_direct("SAHMREALTIME")),
    ("FRED MSPUS (sid 255, 新屋售價中位數)", 255, lambda: _fetch_fred_direct("MSPUS")),
    ("FRED DRBLACBS (sid 755, 商銀企業貸款拖欠率)", 755, lambda: _fetch_fred_direct("DRBLACBS")),
    ("FRED BAMLH0A3HYCEY (sid 634, CCC 有效殖利率)", 634, lambda: _fetch_fred_direct("BAMLH0A3HYCEY")),
    ("FRED DGORDER (sid 319, 耐久財新訂單)", 319, lambda: _fetch_fred_direct("DGORDER")),
    ("FRED WLODLL (sid 7449, 超額準備金週頻)", 7449, lambda: _fetch_fred_direct("WLODLL")),
    ("FRED PCEPILFE YoY (sid 348, 核心 PCE 年增自算)", 348, lambda: _fetch_fred_yoy("PCEPILFE")),
    ("FRED DSPIC96 YoY (sid 560, 實質可支配所得年增自算)", 560, lambda: _fetch_fred_yoy("DSPIC96")),
    # WP-A1b
    ("FRED EXHOSLUSM495S 拼接 (sid 246, 成屋銷售 YoY)", 246, fetch_246_splice),
    # [2026-09-27] sid 8219: EIA Cushing 現貨,與舊 pkl 243 個重疊日 0 誤差(同源);
    # FRED 有 16 個早期日期為空值,舊點由 _save_series merge 保留
    ("FRED DCOILWTICO (sid 8219, WTI 現貨日頻)", 8219, lambda: _fetch_fred_direct("DCOILWTICO")),
    # [2026-09-28] 信用風險利差,脫離 M²(見上方 _fetch_credit_spread 說明)
    ("FRED BAMLH0A3HYCEY-DGS10 (sid 3612, CCC 信用風險利差)", 3612, lambda: _fetch_credit_spread("BAMLH0A3HYCEY")),
    ("FRED BAMLC0A4CBBBEY-DGS10 (sid 93001, BBB 信用風險利差)", 93001, lambda: _fetch_credit_spread("BAMLC0A4CBBBEY")),
    ("FRED BAMLC0A1CAAAEY-DGS10 (sid 93002, AAA 信用風險利差)", 93002, lambda: _fetch_credit_spread("BAMLC0A1CAAAEY")),
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
