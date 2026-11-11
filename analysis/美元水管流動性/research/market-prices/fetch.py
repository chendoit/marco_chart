# -*- coding: utf-8 -*-
"""抓跨資產日線 OHLCV（market-prices）。

來源：Yahoo Finance chart API（query1.finance.yahoo.com/v8/finance/chart），
請求方式同 get_yfinance_series.py 的 _yf_chart（interval=1d、period1 起算）。

Yahoo 回傳的 OHLC/volume 已做拆股回溯調整（split-adjusted），adjclose 另做股息+拆股調整。
本腳本把拆股調整還原成「未還原」口徑：對每個拆股事件，拆股日前的 open/high/low/close
乘上 numerator/denominator，volume 乘上 denominator/numerator（數字全來自 Yahoo 的 split events，
不做插補）。還原前後的跳空檢查會印在 log 裡。

用法（在任務資料夾執行）：
    PYTHONUTF8=1 C:/code/2025-12-05-MacroMicro-Data/venv/Scripts/python.exe fetch.py [--start YYYY-MM-DD]

輸出：
    market_prices.csv     長表，主鍵 (ticker, date)
    raw/<ticker>.json     來源原始回應（未經任何還原）
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "raw"
OUT_CSV = HERE / "market_prices.csv"
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TICKERS = ["^GSPC", "^DJI", "^SOX", "^NDX", "QQQ", "SPY", "RSP", "INTC", "GLD",
           "GC=F", "SI=F", "DX-Y.NYB", "BTC-USD"]
COLUMNS = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]

LAST_CLOSED = date(2026, 11, 6)   # 最新已收盤交易日（2026-11-07/08 為週末）
BTC_LAST = date(2026, 11, 8)      # BTC-USD 例外：24 小時交易，可收到 2026-11-08
# 指數、期貨在來源沒有還原價 → adj_close 留空（以 Yahoo meta.instrumentType 判斷）
NO_ADJ_TYPES = {"INDEX", "FUTURE"}


def safe_name(ticker):
    return re.sub(r"[^A-Za-z0-9.-]", "_", ticker)


def fetch_chart(ticker, start_epoch, retries=3):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(ticker, safe="")
    params = {"interval": "1d", "period1": start_epoch, "period2": int(time.time()), "events": "div,split"}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=HDRS, timeout=30)
            r.raise_for_status()
            body = r.json()
            if body["chart"].get("error"):
                raise RuntimeError(f"Yahoo error: {body['chart']['error']}")
            return body
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  retry {attempt}/{retries} {ticker}: {e}", file=sys.stderr)
            time.sleep(2 * attempt)
    raise RuntimeError(f"{ticker} 抓取失敗: {last_err}")


def utc_date(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc).date()


def fmt_num(x, nd=6):
    if x is None:
        return ""
    return repr(round(float(x), nd))


def parse_ticker(ticker, body, start_d, end_d):
    res = body["chart"]["result"][0]
    meta = res.get("meta", {})
    itype = meta.get("instrumentType", "")
    ts = res.get("timestamp") or []
    q = res["indicators"]["quote"][0]
    adj_block = res["indicators"].get("adjclose") or [{}]
    adj = adj_block[0].get("adjclose") or []

    split_events = []
    for v in (res.get("events", {}).get("splits") or {}).values():
        split_events.append((utc_date(v["date"]), float(v["numerator"]), float(v["denominator"]), v.get("splitRatio", "")))
    split_events.sort()

    def price_factor(d):
        f = 1.0
        for sd, n, dn, _ in split_events:
            if d < sd:
                f *= n / dn
        return f

    def volume_factor(d):
        f = 1.0
        for sd, n, dn, _ in split_events:
            if d < sd:
                f *= dn / n
        return f

    rows = []
    adjusted_bars = 0
    for i, t in enumerate(ts):
        close_raw = q["close"][i] if i < len(q.get("close") or []) else None
        if close_raw is None:
            continue  # 假日/無成交的空白 bar
        d = utc_date(t)
        if d < start_d or d > end_d:
            continue
        pf = price_factor(d)
        vf = volume_factor(d)
        if pf != 1.0:
            adjusted_bars += 1

        def px(key):
            v = (q.get(key) or [None] * len(ts))[i]
            return None if v is None else float(v) * pf

        vol = (q.get("volume") or [None] * len(ts))[i]
        vol_out = "" if vol is None else str(int(round(float(vol) * vf)))

        if itype in NO_ADJ_TYPES:
            adj_out = ""
        else:
            av = adj[i] if i < len(adj) else None
            adj_out = fmt_num(av)

        rows.append({
            "date": d.isoformat(),
            "ticker": ticker,
            "open": fmt_num(px("open")),
            "high": fmt_num(px("high")),
            "low": fmt_num(px("low")),
            "close": fmt_num(float(close_raw) * pf),
            "adj_close": adj_out,
            "volume": vol_out,
        })

    rows = [r for r in rows if r["date"] <= (BTC_LAST if ticker == "BTC-USD" else LAST_CLOSED).isoformat()]

    # 拆股還原的跳空檢查：Yahoo 原始 close 在拆股日應無跳空，還原後應跳出拆股比例
    split_checks = []
    by_date = {r["date"]: r for r in rows}
    for sd, n, dn, ratio in split_events:
        prev = [r for r in rows if r["date"] < sd.isoformat()]
        cur = by_date.get(sd.isoformat())
        if not prev or not cur:
            continue
        p = prev[-1]
        if not p["close"] or not cur["close"]:
            continue
        jump_restored = float(p["close"]) / float(cur["close"])
        # Yahoo 原始（已拆股調整）close 的跳空 = 還原後跳空 / 拆股倍數
        jump_yahoo = jump_restored / (n / dn)
        split_checks.append((sd.isoformat(), ratio, round(jump_yahoo, 4), round(jump_restored, 4)))

    info = {
        "instrumentType": itype,
        "exchangeTimezoneName": meta.get("exchangeTimezoneName", ""),
        "currency": meta.get("currency", ""),
        "splits": [(sd.isoformat(), ratio) for sd, _, _, ratio in split_events],
        "split_checks": split_checks,
        "adjusted_bars": adjusted_bars,
        "adj_blank": itype in NO_ADJ_TYPES,
    }
    return rows, info


def main():
    ap = argparse.ArgumentParser(description="抓 market-prices 日線 OHLCV（Yahoo chart API）")
    ap.add_argument("--start", default="1900-01-01", help="最早日期（YYYY-MM-DD），預設抓 Yahoo 全部歷史")
    args = ap.parse_args()
    start_d = date.fromisoformat(args.start)
    start_epoch = max(0, int(datetime(start_d.year, start_d.month, start_d.day, tzinfo=timezone.utc).timestamp()))

    RAW_DIR.mkdir(exist_ok=True)
    all_rows = []
    for ticker in TICKERS:
        end_d = BTC_LAST if ticker == "BTC-USD" else LAST_CLOSED
        print(f"fetch {ticker} ...", flush=True)
        body = fetch_chart(ticker, start_epoch)
        with open(RAW_DIR / f"{safe_name(ticker)}.json", "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
        rows, info = parse_ticker(ticker, body, start_d, end_d)
        if not rows:
            raise RuntimeError(f"{ticker} 沒有任何列")
        all_rows.extend(rows)
        print(f"  n={len(rows)} range={rows[0]['date']}~{rows[-1]['date']} "
              f"type={info['instrumentType']} tz={info['exchangeTimezoneName']} "
              f"adj_blank={info['adj_blank']} split_adjusted_bars={info['adjusted_bars']}", flush=True)
        for sd, ratio in info["splits"]:
            print(f"  split {sd} {ratio}", flush=True)
        for sd, ratio, jy, jr in info["split_checks"]:
            print(f"  split-check {sd} {ratio}: yahoo_close_jump={jy} restored_close_jump={jr}", flush=True)
        time.sleep(0.5)

    all_rows.sort(key=lambda r: (r["ticker"], r["date"]))
    keys = [(r["ticker"], r["date"]) for r in all_rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("主鍵 (ticker, date) 重複")

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(all_rows)
    print(f"wrote {OUT_CSV} rows={len(all_rows)}", flush=True)


if __name__ == "__main__":
    main()
