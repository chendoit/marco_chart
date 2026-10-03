#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fetch_dairy.py — 抓取「紐西蘭乳製品價格」歷史月資料,輸出 data/dairy_index.csv

來源 (source = GDT_price_index):
  Global Dairy Trade (GDT) Price Index,雙週拍賣事件(每檔 2 次),轉成月資料
  = 每個月「最後一次」Trading Event 的 Price Index。

  1) 先讀 latest.json 取得最新一場事件的 GUID:
     https://s3.amazonaws.com/www-production.globaldairytrade.info/results/latest.json
  2) 再讀該場事件的十年價格指數明細(每場事件的 EventDate / PriceIndex):
     https://s3.amazonaws.com/www-production.globaldairytrade.info/results/<GUID>/price_indices_ten_years.json

  註:resultsPath 這個 S3 前綴是 globaldairytrade.info 官網 HTML 內的
      `var resultsPath` 變數(見 /en/gdt-events/ 與 /en/product-results/ 頁面),
      網站本身的圖表就是讀這支 JSON。S3 bucket 不開放 list,故只能由
      latest.json 取得 GUID 進入。目前該檔涵蓋最近 10 年(約 2016-09 起)。

輸出:
  data/dairy_index.csv,欄位固定 date,value,source
  date = YYYY-MM-01,由舊到新排序;value = GDT Price Index(點數);source = GDT_price_index

用法:
  python scripts/fetch_dairy.py
可重複執行,每次重新抓取最新資料。
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

TIMEOUT = 60  # 秒
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

RESULTS_S3 = "https://s3.amazonaws.com/www-production.globaldairytrade.info/results/"
URL_LATEST = RESULTS_S3 + "latest.json"
URL_TEN_YEARS = RESULTS_S3 + "{guid}/price_indices_ten_years.json"

ROOT = Path(__file__).resolve().parent.parent
OUT_CSV = ROOT / "data" / "dairy_index.csv"
SOURCE = "GDT_price_index"


def fetch_json(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_session():
    return requests.Session()


def main():
    s = get_session()

    # 1) 最新事件 GUID
    latest = fetch_json(URL_LATEST)
    guid = latest["latestEvent"]
    print(f"[info] latest event GUID = {guid}")

    # 2) 十年價格指數明細
    data = fetch_json(URL_TEN_YEARS.format(guid=guid))
    events = data["PriceIndicesTenYears"]["Events"]["EventDetails"]
    print(f"[info] 取得 {len(events)} 場 Trading Event")

    # 3) 轉月:每個月取「最後一次」事件(以 EventDate 排序後取該月最後一筆)
    rows = []
    for e in events:
        dt = datetime.strptime(e["EventDate"], "%B %d, %Y %H:%M:%S")
        rows.append(
            {
                "date": dt,
                "value": float(e["PriceIndex"]),
                "event_number": float(e["EventNumber"]),
            }
        )

    df = pd.DataFrame(rows)
    df = df.sort_values("date").reset_index(drop=True)
    # date 轉為月初
    df["date"] = df["date"].dt.to_period("M").dt.to_timestamp()
    # 每個 Period 取最後一筆(當月最後一次拍賣)
    monthly = df.groupby(df["date"], as_index=False).last()
    monthly = monthly.sort_values("date").reset_index(drop=True)
    monthly["source"] = SOURCE

    out = monthly[["date", "value", "source"]].copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    out["value"] = out["value"].map(lambda v: int(v) if float(v).is_integer() else v)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    print(f"[ok] 寫入 {OUT_CSV}  ({len(out)} 筆)")
    print(
        f"[ok] date 範圍 {out['date'].iloc[0]} ~ {out['date'].iloc[-1]}, "
        f"最新 value = {out['value'].iloc[-1]}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # 失敗時如實回報,不捏造資料
        print(f"[error] 抓取失敗: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
