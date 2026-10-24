"""抓港股四大龍頭每日成交額（港幣）。

主來源：東方財富 push2his kline API 的成交額欄位（fqt=0 不復權）。
備援／比對：Yahoo Finance 日 K，close × volume 近似。

用法：
    python fetch.py                  # 抓全部歷史（2018-01-01 起）
    python fetch.py --start 2026-10-01   # 增量
"""

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).resolve().parent

# 代號：(yahoo 代號, 東方財富 secid)
STOCKS = {
    "t0700": ("0700.HK", "116.00700"),
    "t9988": ("9988.HK", "116.09988"),
    "t3690": ("3690.HK", "116.03690"),
    "t0941": ("0941.HK", "116.00941"),
}

EM_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
SLEEP = 1.1


def fetch_eastmoney(secid, start, end):
    """回傳 Series(index=date, 成交額 HKD)；欄位 kline 格式：日期,開,收,高,低,量,額。"""
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
        "klt": 101,
        "fqt": 0,
        "beg": start.replace("-", ""),
        "end": end.replace("-", ""),
        "lmt": 100000,
    }
    r = requests.get(EM_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json().get("data") or {}
    rows = [k.split(",") for k in data.get("klines", [])]
    if not rows:
        return pd.Series(dtype="float64")
    df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "volume", "amount"])
    df["date"] = pd.to_datetime(df["date"])
    return pd.Series(df["amount"].astype(float).values, index=df["date"].values, name="amount")


def fetch_yahoo(ticker, start, end):
    """回傳 Series(index=date, close×volume)；Yahoo 的 volume 為未調整股數。"""
    d = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if d.empty:
        return pd.Series(dtype="float64")
    close = d[("Close", ticker)] if isinstance(d.columns, pd.MultiIndex) else d["Close"]
    vol = d[("Volume", ticker)] if isinstance(d.columns, pd.MultiIndex) else d["Volume"]
    s = (close * vol).astype(float)
    s.index = pd.to_datetime(s.index).tz_localize(None)
    s.name = "yahoo_approx"
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=pd.Timestamp.today().strftime("%Y-%m-%d"))
    ap.add_argument("--out", default=str(HERE / "giants_turnover.csv"))
    args = ap.parse_args()

    em = {}
    yh = {}
    for col, (ytk, secid) in STOCKS.items():
        print(f"[{col}] eastmoney ...", flush=True)
        em[col] = fetch_eastmoney(secid, args.start, args.end)
        time.sleep(SLEEP)
        print(f"[{col}] yahoo ...", flush=True)
        yh[col] = fetch_yahoo(ytk, args.start, args.end)
        time.sleep(SLEEP)
        print(f"  em={len(em[col])} rows, yahoo={len(yh[col])} rows", flush=True)

    # 主來源 eastmoney；缺值（或 eastmoney 無資料）回退 yahoo 近似
    out = pd.DataFrame()
    for col in STOCKS:
        main_s = em[col]
        fallback = yh[col].reindex(main_s.index.union(yh[col].index))
        merged = main_s.reindex(fallback.index).fillna(fallback)
        out[col] = merged
    out = out.sort_index()
    out = out[out.index >= pd.Timestamp(args.start)]
    # 排除尚未收盤的當日（香港 16:30 收盤後才視為完整交易日）
    hk_now = pd.Timestamp.now(tz="Asia/Hong_Kong")
    if hk_now.hour < 17:
        out = out[out.index < pd.Timestamp(hk_now.date())]
    out.index.name = "date"
    out["giants_total"] = out.sum(axis=1, min_count=1)
    out = out.round(0)
    out.index = out.index.strftime("%Y-%m-%d")
    out.to_csv(args.out, encoding="utf-8", na_rep="")
    print(f"wrote {args.out}: {len(out)} rows, {out.index.min()} ~ {out.index.max()}")

    # 比對：同日 eastmoney 與 yahoo 近似的差距（抽樣 5 個日期，並輸出完整差距檔）
    cmp_rows = []
    for col in STOCKS:
        both = pd.concat([em[col].rename("em"), yh[col].rename("yahoo")], axis=1).dropna()
        # Yahoo 偶有 volume=0 的壞資料（多為半日市），比對時排除
        both = both[both["yahoo"] > 0]
        both["diff_pct"] = (both["yahoo"] / both["em"] - 1) * 100
        both["stock"] = col
        cmp_rows.append(both.reset_index().rename(columns={"index": "date"}))
    cmp = pd.concat(cmp_rows)
    cmp.to_csv(HERE / "compare_em_vs_yahoo.csv", index=False, encoding="utf-8")
    print("compare rows:", len(cmp))


if __name__ == "__main__":
    sys.exit(main())
