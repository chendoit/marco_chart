"""美元水管流動性：只抓日層規則需要的序列，增量寫入 cache/<name>.csv（date,value）。

來源（全部免金鑰）：
  NY Fed  sofr、tgcr（%）             rates/secured/<x>/search.json
          srf_bn、rrp_bn（十億美元）   rp/results/search.json（當天各場次承作額加總）
  FRED    iorb、dgs10、dgs1mo、dtb3（%） fredgraph.csv
  Yahoo   spy、qqq、gld、smh、rsp、dxy（收盤價） v8/finance/chart

第一次（cache 沒有檔案）從 BOOTSTRAP_START 抓起；之後只抓最近 LOOKBACK_DAYS 天再合併
（NY Fed、FRED 偶爾會修正最近幾天的值，所以重疊的日期以新抓的為準）。

用法：venv\\Scripts\\python.exe alerts\\liq_pipe\\liq_fetch.py [--groups nyfed_rates,nyfed_ops,fred,yahoo] [--full]
"""
import argparse
import csv
import io
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
BOOTSTRAP_START = date(2024, 1, 1)    # 250 日分位數 + 20 日波動率，兩年足夠
LOOKBACK_DAYS = 21
UA = {"User-Agent": "Mozilla/5.0 (liq-pipe daily monitor)"}
NYF = "https://markets.newyorkfed.org/api"

GROUPS = {
    "nyfed_rates": ["sofr", "tgcr"],
    "nyfed_ops": ["srf_bn", "rrp_bn"],
    "fred": ["iorb", "dgs10", "dgs1mo", "dtb3"],
    "yahoo": ["spy", "qqq", "gld", "smh", "rsp", "dxy"],
}
FRED_ID = {"iorb": "IORB", "dgs10": "DGS10", "dgs1mo": "DGS1MO", "dtb3": "DTB3"}
YAHOO_ID = {"spy": "SPY", "qqq": "QQQ", "gld": "GLD", "smh": "SMH", "rsp": "RSP", "dxy": "DX-Y.NYB"}


def http_json_or_text(url, params=None, as_json=True, tries=3):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=45)
            r.raise_for_status()
            return r.json() if as_json else r.text
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep((0, 10, 30)[i] if i < 3 else 30)
    raise RuntimeError(f"抓取失敗 {url}: {last}")


# ---------- cache ----------

def cache_path(name):
    return os.path.join(CACHE, f"{name}.csv")


def load(name):
    p = cache_path(name)
    if not os.path.exists(p):
        return pd.Series(dtype=float, name=name)
    d = pd.read_csv(p, parse_dates=["date"])
    return d.set_index("date")["value"].rename(name)


def merge_save(name, new):
    """new：{date: value}。重疊日期以新值為準。回傳（新增筆數, 最新日期）。"""
    old = load(name)
    s = pd.Series(new, dtype=float)
    s.index = pd.to_datetime(s.index)
    added = len(s.index.difference(old.index))
    keep = old[~old.index.isin(s.index)]
    allv = (pd.concat([keep, s]) if len(keep) else s).sort_index()
    os.makedirs(CACHE, exist_ok=True)
    tmp = cache_path(name) + ".tmp"
    allv.rename_axis("date").rename("value").to_csv(tmp, date_format="%Y-%m-%d")
    os.replace(tmp, cache_path(name))
    return added, (allv.index.max().date() if len(allv) else None)


def start_for(names, full):
    if full or any(load(n).empty for n in names):
        return BOOTSTRAP_START
    return date.today() - timedelta(days=LOOKBACK_DAYS)


# ---------- 各來源 ----------

def fetch_nyfed_rates(start, end):
    out = {}
    for name in GROUPS["nyfed_rates"]:
        j = http_json_or_text(f"{NYF}/rates/secured/{name}/search.json",
                              {"startDate": start.isoformat(), "endDate": end.isoformat()})
        rows = {x["effectiveDate"]: float(x["percentRate"]) for x in j.get("refRates", [])
                if x.get("percentRate") is not None}
        if not rows and start == BOOTSTRAP_START:
            raise RuntimeError(f"NY Fed {name} 回傳 0 筆")
        out[name] = rows
    return out


def fetch_nyfed_ops(start, end):
    """SRF（operationType = Repo）和 ON RRP（Reverse Repo）每天的承作額，十億美元。
    分段查詢：一次查太長的區間 API 會很慢。"""
    srf, rrp = {}, {}
    seen = 0
    a = start
    while a <= end:
        b = min(a + timedelta(days=120), end)
        j = http_json_or_text(f"{NYF}/rp/results/search.json",
                              {"startDate": a.isoformat(), "endDate": b.isoformat()})
        for o in j.get("repo", {}).get("operations", []):
            if o.get("auctionStatus") != "Results":
                continue
            seen += 1
            d, amt = o["operationDate"], int(o.get("totalAmtAccepted") or 0) / 1e9
            if o.get("operationType") == "Repo":
                srf[d] = srf.get(d, 0.0) + amt
            elif o.get("operationType") == "Reverse Repo" and o.get("term") == "Overnight":
                rrp[d] = rrp.get(d, 0.0) + amt
        a = b + timedelta(days=1)
    if seen == 0 and (end - start).days > 7:
        raise RuntimeError("NY Fed 公開市場操作回傳 0 筆")
    return {"srf_bn": srf, "rrp_bn": rrp}


def fetch_fred(start, end):
    out = {}
    for name, sid in FRED_ID.items():
        text = http_json_or_text("https://fred.stlouisfed.org/graph/fredgraph.csv",
                                 {"id": sid, "cosd": start.isoformat()}, as_json=False)
        rows = {}
        for r in csv.DictReader(io.StringIO(text)):
            v = r.get(sid)
            if v not in (None, "", "."):
                rows[r["observation_date"]] = float(v)
        if not rows:
            raise RuntimeError(f"FRED {sid} 回傳 0 筆（格式可能改了）")
        out[name] = rows
    return out


def fetch_yahoo(start, end):
    out = {}
    p1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    for name, tk in YAHOO_ID.items():
        j = http_json_or_text(f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}",
                              {"interval": "1d", "period1": p1, "period2": int(time.time())})
        res = (j.get("chart", {}).get("result") or [None])[0]
        if not res or not res.get("timestamp"):
            raise RuntimeError(f"Yahoo {tk} 沒有資料")
        tz = res["meta"].get("exchangeTimezoneName", "America/New_York")
        closes = res["indicators"]["quote"][0]["close"]
        rows = {}
        for ts, c in zip(res["timestamp"], closes):
            if c is None:
                continue
            d = pd.Timestamp(ts, unit="s", tz="UTC").tz_convert(tz).date()
            rows[d.isoformat()] = float(c)
        # 盤中（還沒收盤）的最後一根不能用：只留收盤後的日線
        now_ny = pd.Timestamp.now(tz="America/New_York")
        today = now_ny.date().isoformat()
        if today in rows and (now_ny.hour, now_ny.minute) < (16, 15):
            rows.pop(today)
        out[name] = rows
        time.sleep(0.5)
    return out


FETCHERS = {"nyfed_rates": fetch_nyfed_rates, "nyfed_ops": fetch_nyfed_ops, "fred": fetch_fred, "yahoo": fetch_yahoo}


def run(groups, full=False):
    """回傳 {name: {"added": n, "last": date}}；任何來源失敗就 raise（讓 cron 記錯誤）。"""
    report = {}
    end = date.today() + timedelta(days=1)
    for g in groups:
        start = start_for(GROUPS[g], full)
        data = FETCHERS[g](start, end)
        for name, rows in data.items():
            added, last = merge_save(name, rows)
            report[name] = {"added": added, "last": str(last)}
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", default=",".join(GROUPS))
    ap.add_argument("--full", action="store_true", help="從 BOOTSTRAP_START 重抓")
    a = ap.parse_args()
    rep = run([g for g in a.groups.split(",") if g], a.full)
    for k, v in rep.items():
        print(f"{k:8s} +{v['added']:<4d} last={v['last']}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
