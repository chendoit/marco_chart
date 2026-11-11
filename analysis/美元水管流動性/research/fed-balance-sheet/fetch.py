"""抓 Fed 準備金與短債持有量（H.4.1 週資料，經 FRED 免 key fredgraph.csv 端點）。

用法：
    PYTHONUTF8=1 python fetch.py [--start YYYY-MM-DD]

輸出：fed_balance.csv（主鍵 date，週三，單位百萬美元）
快取：raw/<SERIES>.csv（原始回應）、raw/<SERIES>.series_page.html（系列頁，確認標題用）

欄位對應（FRED 代碼；FRED 單位為百萬美元，不需換算）：
    reserves_wed      WRBWFRBL  Reserve Balances with Federal Reserve Banks: Wednesday Level
    reserves_wavg     WRESBAL   Reserve Balances with Federal Reserve Banks: Week Average
    bills_wed         WSHOBL    Securities Held Outright: U.S. Treasury Securities: Bills: Wednesday Level
    treasuries_wed    TREAST    Securities Held Outright: U.S. Treasury Securities: All: Wednesday Level
"""

import argparse
import csv
import io
import os
import time
import urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "fed_balance.csv")
UA = "Mozilla/5.0 (research-fetch; fed-balance-sheet)"
TIMEOUT = 60
PAUSE = 1.0  # 請求間隔（秒），控制頻率

COLUMNS = [
    ("reserves_wed", "WRBWFRBL"),
    ("reserves_wavg", "WRESBAL"),
    ("bills_wed", "WSHOBL"),
    ("treasuries_wed", "TREAST"),
]


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read().decode("utf-8")


def fetch_one(series_id):
    os.makedirs(RAW, exist_ok=True)
    csv_text = http_get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}")
    with open(os.path.join(RAW, f"{series_id}.csv"), "w", encoding="utf-8") as f:
        f.write(csv_text)
    time.sleep(PAUSE)
    page = http_get(f"https://fred.stlouisfed.org/series/{series_id}")
    with open(os.path.join(RAW, f"{series_id}.series_page.html"), "w", encoding="utf-8") as f:
        f.write(page)
    time.sleep(PAUSE)
    out = {}
    for row in csv.DictReader(io.StringIO(csv_text)):
        v = row.get(series_id)
        if v in (None, ".", ""):
            continue
        out[row["observation_date"]] = v
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2015-01-01", help="輸出起始日（含）")
    args = ap.parse_args()
    start = datetime.strptime(args.start, "%Y-%m-%d").date()

    data = {}
    for col, sid in COLUMNS:
        data[col] = fetch_one(sid)

    dates = set()
    for col, _ in COLUMNS:
        dates.update(data[col].keys())
    rows = []
    for d in sorted(dates):
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        if dt < start or dt.weekday() != 2:  # 2 = 週三
            continue
        rows.append([d] + [data[col].get(d, "") for col, _ in COLUMNS])

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date"] + [col for col, _ in COLUMNS])
        w.writerows(rows)
    print(f"wrote {OUT} rows={len(rows)} first={rows[0][0]} last={rows[-1][0]}")


if __name__ == "__main__":
    main()
