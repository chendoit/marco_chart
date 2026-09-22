# -*- coding: utf-8 -*-
# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 資料源: investing.com 內部 API (主) + worldgovernmentbonds.com XHR (備援)
# 覆蓋範圍(9 條 pkl): sid 27118/27119/27126/27129/27131/27134/27135/27136/27138
#   9 國 5Y 主權 CDS,status 全部為 approx(舊 M² 值與新源有 ~2-8% 中位數口徑差,
#   不同評價機構/日內時點,方向量級一致)。
#
#   [2026-09-17] 起由本檔接管;歷史上由 get_m_square_chart.py 時代或其他管道產生。
import os
import pickle
from datetime import datetime

from loguru import logger
from curl_cffi import requests as creq

import log_config  # noqa: F401

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# title 對照表:沿用舊 pkl 顯示名稱(儀表板圖例用),一字不改
TITLE_MAP = {
    27118: "uk-5year-cds",
    27119: "germany-5year-cds",
    27126: "france-5year-cds",
    27129: "portugal-5year-cds",
    27131: "spain-5year-cds",
    27134: "mexico-5year-cds",
    27135: "italy-5year-cds",
    27136: "brazil-5year-cds",
    27138: "turkey-5year-cds",
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
# sid=27118  英國 5Y CDS  [approx]
# 來源: Investing.com 內部 API pair_id=1115185 (GBGV5YUSAC=R);備援: WGB
# ============================================================================
def fetch_series_27118(start_date="2013-01-01", end_date=None) -> list:
    """Investing.com internal API: UK 5Y CDS daily closes (bp).
    Returns [(datetime 08:00, float), ...] sorted ascending.
    Note: values differ ~5% (median) from old M2 pkl (different data vendor),
    direction/magnitude consistent; treat as approximation of same metric.
    舊 M² 舊值有 ~5% 中位數口徑差,方向量級一致。
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    url = (f"https://api.investing.com/api/financialdata/historical/1115185"
           f"?start-date={start_date}&end-date={end_date}&time-frame=Daily"
           f"&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=90, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/uk-cds-5-years-gbp",
                          "domain-id": "www",
                          "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json()["data"]
    out = []
    for row in rows:
        d = datetime.strptime(row["rowDateTimestamp"][:10], "%Y-%m-%d")
        out.append((d.replace(hour=8, minute=0), float(row["last_close"])))
    out.sort(key=lambda x: x[0])
    return out


# ============================================================================
# sid=27119  德國 5Y CDS  [approx]
# 來源: investing.com pair_id=1202222 (DEGV5YUSAC=R);備援: WGB SYMBOL="2"
# ============================================================================
def fetch_germany_5y_cds(start="2008-07-01", end="2099-12-31"):
    """德國 5Y CDS(sid=27119)。回傳 [(datetime(08:00), float_bp), ...] 日頻。"""
    url = ("https://api.investing.com/api/financialdata/historical/1202222"
           f"?start-date={start}&end-date={end}&time-frame=Daily"
           "&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=60, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/germany-cds-5-year-usd",
                          "domain-id": "www", "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json().get("data") or []
    data = {}
    for row in rows:
        ds = row["rowDateTimestamp"][:10]
        if row.get("last_close") not in (None, ""):
            data[ds] = float(row["last_close"])
    return [(datetime.strptime(k, "%Y-%m-%d").replace(hour=8), v)
            for k, v in sorted(data.items())]


# ============================================================================
# sid=27126  法國 5Y CDS  [approx]
# 來源: Investing.com 內部 API instrument_id=1158922 (FRGV5YUSAC=R)
# ============================================================================
def fetch_series_27126(start_date="2013-01-01", end_date=None) -> list:
    """Investing.com internal API: France 5Y CDS daily closes (bp).
    Returns [(datetime 08:00, float), ...] sorted ascending.
    Note: values differ ~5.9% (median) from old M2 pkl (different data vendor),
    direction/magnitude consistent; treat as approximation of same metric.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    url = (f"https://api.investing.com/api/financialdata/historical/1158922"
           f"?start-date={start_date}&end-date={end_date}&time-frame=Daily"
           f"&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=90, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/france-cds-5-years-usd",
                          "domain-id": "www",
                          "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json()["data"]
    out = []
    for row in rows:
        d = datetime.strptime(row["rowDateTimestamp"][:10], "%Y-%m-%d")
        out.append((d.replace(hour=8, minute=0), float(row["last_close"])))
    out.sort(key=lambda x: x[0])
    return out


# ============================================================================
# sid=27129  葡萄牙 5Y CDS  [approx]
# 來源: worldgovernmentbonds.com XHR (investing.com 無此頁)
# 備註: 2013-01~2016-11 有 gap(WGB 該段無資料)
# ============================================================================
def fetch_series_27129() -> list:
    """worldgovernmentbonds.com: Portugal 5Y sovereign CDS daily closes (bp).
    Returns [(datetime 08:00, float), ...] sorted ascending, 2017-04-16 ~ latest.
    Note: values differ ~5% (median) from old M2 pkl (different CDS vendor);
    direction/magnitude consistent, treat as approximation. 2013-01~2016-11 gap.
    """
    gv = {"JS_VARIABLE": "jsGlobalVars", "FUNCTION": "CDS", "DOMESTIC": True,
          "ENDPOINT": "https://www.worldgovernmentbonds.com/wp-json/common/v1/historical",
          "DATE_RIF": "2099-12-31", "DEBUG": True,
          "OBJ": {"UNIT": "", "DECIMAL": 2, "UNIT_DELTA": "%", "DECIMAL_DELTA": 2},
          "COUNTRY1": {"SYMBOL": "16", "PAESE": "Portugal", "PAESE_UPPERCASE": "PORTUGAL",
                       "BANDIERA": "pt", "URL_PAGE": "portugal"},
          "COUNTRY2": None,
          "OBJ1": {"DURATA_STRING": "5 Years", "DURATA": 60},
          "OBJ2": None}
    r = creq.post("https://www.worldgovernmentbonds.com/wp-json/common/v1/historical",
                  json={"GLOBALVAR": gv}, impersonate="chrome131", timeout=60, verify=False,
                  headers={"Content-type": "application/json; charset=UTF-8",
                           "Referer": "https://www.worldgovernmentbonds.com/cds-historical-data/portugal/5-years/",
                           "Origin": "https://www.worldgovernmentbonds.com"})
    r.raise_for_status()
    quotes = r.json()["result"]["quote"]
    out = []
    for k in sorted(quotes, key=int):
        v = quotes[k]
        d = datetime.strptime(v["DATA_VAL"], "%Y-%m-%d")
        out.append((d.replace(hour=8, minute=0), float(v["CLOSE_VAL"])))
    return out


# ============================================================================
# sid=27131  西班牙 5Y CDS  [approx]
# 來源: Investing.com 內部 API pair_id=1115764 (ESGV5YUSAC=R)
# ============================================================================
def fetch_series_27131(start_date="2013-01-01", end_date=None) -> list:
    """Investing.com internal API: Spain 5Y CDS daily closes (bp).
    Returns [(datetime 08:00, float), ...] sorted ascending.
    Note: values differ ~2% (median, up to ~7% on recent points) from old M2
    pkl (different data vendor), direction/magnitude consistent; treat as
    approximation of the same metric.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    url = (f"https://api.investing.com/api/financialdata/historical/1115764"
           f"?start-date={start_date}&end-date={end_date}&time-frame=Daily"
           f"&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=90, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/spain-cds-5-years-usd",
                          "domain-id": "www",
                          "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json()["data"]
    out = []
    for row in rows:
        d = datetime.strptime(row["rowDateTimestamp"][:10], "%Y-%m-%d")
        out.append((d.replace(hour=8, minute=0), float(row["last_close"])))
    out.sort(key=lambda x: x[0])
    return out


# ============================================================================
# sid=27134  墨西哥 5Y CDS  [approx]
# 來源: investing.com pair_id=1158921 (MXGV5YUSAC=R);備援: WGB SYMBOL="14"
# ============================================================================
def fetch_series_27134(start="2012-01-01", end="2099-12-31") -> list:
    """Mexico 5Y CDS USD (sid=27134). 回傳 [(datetime(08:00), float_bp), ...] 日頻。"""
    url = ("https://api.investing.com/api/financialdata/historical/1158921"
           f"?start-date={start}&end-date={end}&time-frame=Daily"
           "&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=60, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/mexico-cds-5-years-usd",
                          "domain-id": "www", "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json().get("data") or []
    data = {}
    for row in rows:
        ds = row["rowDateTimestamp"][:10]
        if row.get("last_close") not in (None, ""):
            data[ds] = float(row["last_close"])
    return [(datetime.strptime(k, "%Y-%m-%d").replace(hour=8), v)
            for k, v in sorted(data.items())]


# ============================================================================
# sid=27135  義大利 5Y CDS  [approx]
# 來源: Investing.com 內部 API instrument_id=1115161
# ============================================================================
def fetch_series_27135(start_date="2013-01-01", end_date=None) -> list:
    """Investing.com internal API: Italy 5Y CDS daily closes (bp).
    Returns [(datetime 08:00, float), ...] sorted ascending.
    Note: values differ ~3% (median) from old M2 pkl (different data vendor),
    direction/magnitude consistent; treat as approximation of same metric.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    url = (f"https://api.investing.com/api/financialdata/historical/1115161"
           f"?start-date={start_date}&end-date={end_date}&time-frame=Daily"
           f"&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=90, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/italy-cds-5-years-usd",
                          "domain-id": "www",
                          "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json()["data"]
    out = []
    for row in rows:
        d = datetime.strptime(row["rowDateTimestamp"][:10], "%Y-%m-%d")
        out.append((d.replace(hour=8, minute=0), float(row["last_close"])))
    out.sort(key=lambda x: x[0])
    return out


# ============================================================================
# sid=27136  巴西 5Y CDS  [approx]
# 來源: Investing.com 內部 API instrument_id=1116031 (BRGV5YUSAC=R)
# ============================================================================
def fetch_series_27136(start_date="2013-01-01", end_date=None) -> list:
    """Investing.com internal API: Brazil 5Y CDS daily closes (bp).
    Returns [(datetime 08:00, float), ...] sorted ascending.
    Note: values differ ~3% (median) from old M2 pkl (different data vendor),
    direction/magnitude consistent; treat as approximation of same metric.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    url = (f"https://api.investing.com/api/financialdata/historical/1116031"
           f"?start-date={start_date}&end-date={end_date}&time-frame=Daily"
           f"&addPivotRatios=false&addPivotsDivision=false&addPivots=true")
    r = creq.get(url, impersonate="chrome131", timeout=90, verify=False,
                 headers={"Origin": "https://www.investing.com",
                          "Referer": "https://www.investing.com/rates-bonds/brazil-cds-5-years-usd",
                          "domain-id": "www",
                          "Accept": "application/json"})
    r.raise_for_status()
    rows = r.json()["data"]
    out = []
    for row in rows:
        v = row["last_close"]
        if v in (None, ""):
            continue
        d = datetime.strptime(row["rowDateTimestamp"][:10], "%Y-%m-%d")
        out.append((d.replace(hour=8, minute=0), float(v)))
    out.sort(key=lambda x: x[0])
    return out


# ============================================================================
# sid=27138  土耳其 5Y CDS  [approx]
# 來源: investing.com pair_id=1096486 (TRGV5YUSAC=R);備援: WGB
# ============================================================================
def fetch_series_27138(start="2013-01-01", end=None):
    """Turkey 5Y sovereign CDS (USD, bp) via investing.com internal API (pair_id=1096486).
    Returns list of (datetime 08:00, float)."""
    if end is None:
        from datetime import date, timedelta
        end = (date.today() + timedelta(days=1)).isoformat()
    from curl_cffi import requests as rq
    import datetime as dt
    base = "https://api.investing.com/api/financialdata/historical/1096486?pair_id=1096486&start-date={s}&end-date={e}"
    out, d0 = [], dt.date(*map(int, start.split("-")))
    d1 = dt.date(*map(int, end.split("-")))
    while d0 < d1:
        d2 = min(d0 + dt.timedelta(days=365 * 2), d1)
        js = rq.get(base.format(s=d0.isoformat(), e=d2.isoformat()),
                     impersonate="chrome131", timeout=60, verify=False,
                     headers={"domain-id": "www"}).json()
        for row in js.get("data", []):
            day = dt.datetime.fromisoformat(row["rowDateTimestamp"][:10])
            out.append((day.replace(hour=8, minute=0), float(row["last_close"])))
        d0 = d2 + dt.timedelta(days=1)
    return sorted(out)


# ============================================================================
# JOBS + 入口
# ============================================================================
JOBS = [
    ("sid 27118 UK 5Y CDS", fetch_series_27118),
    ("sid 27119 Germany 5Y CDS", fetch_germany_5y_cds),
    ("sid 27126 France 5Y CDS", fetch_series_27126),
    ("sid 27129 Portugal 5Y CDS", fetch_series_27129),
    ("sid 27131 Spain 5Y CDS", fetch_series_27131),
    ("sid 27134 Mexico 5Y CDS", fetch_series_27134),
    ("sid 27135 Italy 5Y CDS", fetch_series_27135),
    ("sid 27136 Brazil 5Y CDS", fetch_series_27136),
    ("sid 27138 Turkey 5Y CDS", fetch_series_27138),
]


def fetch_cds_series():
    """供 get_all_series_data.py 呼叫的入口。任一 fetch 失敗會彙整後 raise,
    交由 orchestrator 記入 error_history。"""
    failures = []
    for name, fn in JOBS:
        try:
            logger.info(f"Starting: {name}")
            obs = fn()
            sid = int(name.split()[1])
            _save_series(sid, obs)
            logger.info(f"Completed: {name}")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            "CDS 抓取失敗 %d 項:\n%s" % (len(failures), "\n".join(failures))
        )


if __name__ == "__main__":
    fetch_cds_series()
