"""抓取港股每日成交額（代理序列：東方財富 恒生指數 secid=100.HSI 的成交額欄位）。

用法：
    venv\\Scripts\\python.exe -I fetch.py                 # 抓全部歷史（2018-01-01 起）
    venv\\Scripts\\python.exe -I fetch.py --start 2024-10-01  # 增量 / 指定起日

注意：此欄位為恒生指數成分股的成交額，未經 HKEX 官方全市場數字核對，
不等於 HKEX 主板＋GEM 全市場成交額。詳見 report.md。
"""
import argparse
import csv
import json
import time
from datetime import datetime
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "market_turnover.csv"
URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
SOURCE = "eastmoney_HSI_f6_constituent_proxy"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}


def fetch_klines(start: str, end: str = "20500101") -> list[str]:
    """回傳 'YYYY-MM-DD,open,close,high,low,volume,turnover,...' 字串列表。"""
    CACHE.mkdir(exist_ok=True)
    cache_file = CACHE / f"hsi_{start}_{end}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))
    params = {
        "secid": "100.HSI",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "0",
        "beg": start,
        "end": end,
        "lmt": "100000",
    }
    r = requests.get(URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    klines = r.json()["data"]["klines"]
    cache_file.write_text(json.dumps(klines, ensure_ascii=False), encoding="utf-8")
    time.sleep(1.0)
    return klines


def load_existing() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8", newline="") as f:
        return {row["date"]: row for row in csv.DictReader(f)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01", help="起始日 YYYY-MM-DD（預設 2018-01-01）")
    args = ap.parse_args()

    start_compact = args.start.replace("-", "")
    klines = fetch_klines(start_compact)

    # 當日盤中的數字不完整（只有上午場或部分時段），不寫入
    today = datetime.now().strftime("%Y-%m-%d")
    rows = {d: r for d, r in load_existing().items() if d < today}
    for line in klines:
        parts = line.split(",")
        date, turnover = parts[0], parts[6]
        if date >= today:
            continue
        rows[date] = {"date": date, "market_turnover": turnover, "source": SOURCE}

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "market_turnover", "source"])
        w.writeheader()
        for d in sorted(rows):
            w.writerow(rows[d])
    print(f"wrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
