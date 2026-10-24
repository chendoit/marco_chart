"""抓恒生指數 (HSI) 與恒生綜合中小型 / 中型 / 小型指數的日收盤。

來源：東方財富 push2his kline API（主來源）；Yahoo ^HSI 作為 HSI 交叉驗證。
用法：
    venv\\Scripts\\python.exe fetch.py                 # 全部歷史（2018-01-01 起）
    venv\\Scripts\\python.exe fetch.py --start 2026-01-01   # 增量：只重抓該日起，合併進既有 CSV
"""

import argparse
import csv
import datetime as dt
import os
import sys
import time
from zoneinfo import ZoneInfo

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "hk_indexes.csv")

# 東方財富 secid：124 = 恒生指數公司指數（HSCI 系列）；100 = 恒生指數
SERIES = {
    "hsi": "100.HSI",          # 恒生指數
    "hs_midsmall": "124.HSMSI",  # 恒生綜合中小型股指數（Hang Seng Composite MidCap & SmallCap）
    "hs_small": "124.HSSI",      # 恒生綜合小型股指數（Hang Seng Composite SmallCap）
    "hs_mid": "124.HSMI",        # 恒生綜合中型股指數（Hang Seng Composite MidCap）
}
COLUMNS = ["date", "hsi", "hs_midsmall", "hs_small", "hs_mid", "ratio_midsmall_hsi"]
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
HKT = ZoneInfo("Asia/Hong_Kong")


def get_json(url, params, retries=4):
    """東財偶爾斷線，逐次退避重試。"""
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if i == retries - 1:
                raise
            print(f"[retry] {e}", file=sys.stderr, flush=True)
            time.sleep(2 ** i * 2)


def fetch_kline(secid, start, end):
    """回傳 {date: close}。日線、不還原（指數無還原概念）。"""
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",  # 日期,開,收,高,低,量,額
        "klt": "101",
        "fqt": "0",
        "beg": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
    }
    payload = get_json(KLINE_URL, params)
    data = payload.get("data")
    if not data or not data.get("klines"):
        raise RuntimeError(f"{secid} 無資料 rc={payload.get('rc')}")
    closes = {}
    for line in data["klines"]:
        parts = line.split(",")
        closes[parts[0]] = float(parts[2])  # 第 3 欄 = 收盤
    print(f"[ok] {secid} {data.get('name')}: {len(closes)} 筆 {min(closes)} ~ {max(closes)}", flush=True)
    return closes


def fetch_yahoo_hsi(start):
    """Yahoo ^HSI 收盤，只用來交叉驗證。失敗不影響主流程。"""
    try:
        import yfinance as yf

        d = yf.download("^HSI", start=start.isoformat(), progress=False, auto_adjust=False)
        return {idx.strftime("%Y-%m-%d"): float(row["Close"].iloc[0]) if hasattr(row["Close"], "iloc") else float(row["Close"])
                for idx, row in d.iterrows()}
    except Exception as e:  # noqa: BLE001
        print(f"[warn] Yahoo ^HSI 交叉驗證失敗：{e}", file=sys.stderr)
        return {}


def load_existing():
    if not os.path.exists(OUT_CSV):
        return {}
    rows = {}
    with open(OUT_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows[row["date"]] = row
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01", help="起始日 YYYY-MM-DD（增量時用）")
    args = ap.parse_args()
    start = dt.date.fromisoformat(args.start)
    today = dt.datetime.now(HKT).date()
    now_hkt = dt.datetime.now(HKT)
    # 收盤後（16:30 HKT 之後）才視為今日已完整；否則今日那根 K 線可能還是盤中值，丟掉
    end = today if now_hkt.hour * 60 + now_hkt.minute >= 16 * 60 + 30 else today - dt.timedelta(days=1)

    series = {}
    for key, secid in SERIES.items():
        series[key] = fetch_kline(secid, start, end)
        time.sleep(1.2)

    # 截掉盤中未完成的 K 線（以 HKT 收盤時間為準）
    cutoff = end.isoformat()
    for key in series:
        series[key] = {d: v for d, v in series[key].items() if d <= cutoff}

    # HSI 交叉驗證（Yahoo），差異記在 stderr 供 report 引用
    yh = fetch_yahoo_hsi(start)
    common = [d for d in series["hsi"] if d in yh]
    if common:
        diffs = [abs(series["hsi"][d] / yh[d] - 1) for d in common]
        print(f"[check] HSI 東財 vs Yahoo 共同日 {len(common)}，最大相對差 {max(diffs):.4%}，中位 {sorted(diffs)[len(diffs)//2]:.4%}", flush=True)

    fresh = {}
    for d in sorted(set().union(*[set(s) for s in series.values()])):
        row = {"date": d}
        for key in ["hsi", "hs_midsmall", "hs_small", "hs_mid"]:
            v = series[key].get(d)
            row[key] = "" if v is None else f"{v:.2f}"
        h, m = series["hsi"].get(d), series["hs_midsmall"].get(d)
        row["ratio_midsmall_hsi"] = f"{m / h:.6f}" if h and m else ""
        fresh[d] = row

    merged = load_existing()
    merged.update(fresh)  # 新抓的覆蓋重疊日

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for d in sorted(merged):
            w.writerow({c: merged[d].get(c, "") for c in COLUMNS})
    print(f"[done] {OUT_CSV}：共 {len(merged)} 列，最新 {max(merged)}", flush=True)


if __name__ == "__main__":
    main()
