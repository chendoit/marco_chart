"""Download ETF NAV CSV from ProShares, compute daily fund flow, save as pkl.

Fund flow formula: (shares_today - shares_prev) * 1000 * nav_today
  - shares in CSV is in thousands (000)
  - skip split dates where shares change dramatically due to split/consolidation

Sources:
  ProShares (UVXY, VIXY, SVXY, TQQQ, SQQQ): direct CSV download
"""
# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import csv
import io
import os
import pickle
from datetime import datetime

import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

folder = os.getenv("DATA_DIR")
if not os.path.exists(folder):
    os.makedirs(folder)

PROSHARES_TICKERS = {
    "UVXY": "https://accounts.profunds.com/etfdata/ByFund/UVXY-historical_nav.csv",
    "VIXY": "https://accounts.profunds.com/etfdata/ByFund/VIXY-historical_nav.csv",
    "SVXY": "https://accounts.profunds.com/etfdata/ByFund/SVXY-historical_nav.csv",
    "TQQQ": "https://accounts.profunds.com/etfdata/ByFund/TQQQ-historical_nav.csv",
    "SQQQ": "https://accounts.profunds.com/etfdata/ByFund/SQQQ-historical_nav.csv",
}

SPLITS = {
    "UVXY": [
        datetime(2012, 3, 8), datetime(2012, 9, 7), datetime(2013, 6, 10),
        datetime(2014, 1, 24), datetime(2015, 5, 20), datetime(2016, 7, 25),
        datetime(2017, 1, 12), datetime(2017, 7, 17), datetime(2018, 9, 18),
        datetime(2021, 5, 26), datetime(2023, 6, 23), datetime(2024, 4, 11),
        datetime(2025, 11, 20),
    ],
    "VIXY": [
        datetime(2023, 6, 23),
    ],
    "SVXY": [
        datetime(2018, 9, 18),
    ],
    "TQQQ": [
        datetime(2011, 2, 25), datetime(2012, 5, 11), datetime(2014, 1, 24),
        datetime(2017, 1, 12), datetime(2018, 5, 24), datetime(2021, 1, 21),
        datetime(2022, 1, 13), datetime(2025, 11, 20),
    ],
    "SQQQ": [
        datetime(2012, 5, 11), datetime(2014, 1, 24), datetime(2017, 1, 12),
        datetime(2019, 5, 24), datetime(2020, 8, 18), datetime(2022, 1, 13),
        datetime(2024, 11, 7), datetime(2025, 11, 20),
    ],
}

SPLIT_WINDOW_DAYS = 3


def _is_split_day(dt, ticker):
    """Check if dt falls within SPLIT_WINDOW_DAYS of any known split."""
    from datetime import timedelta
    for split_dt in SPLITS.get(ticker, []):
        if abs((dt - split_dt).days) <= SPLIT_WINDOW_DAYS:
            return True
    return False


def _compute_fundflow(rows, ticker):
    """Compute daily fund flow from sorted rows [(date, nav, shares_k)].

    Returns list of [datetime, float] pairs.
    """
    rows.sort(key=lambda r: r[0])
    fundflow = []
    for i in range(1, len(rows)):
        dt, nav, shares_k = rows[i]
        _, _, prev_shares_k = rows[i - 1]
        if nav is None or shares_k is None or prev_shares_k is None:
            continue
        if _is_split_day(dt, ticker):
            logger.info(f"{ticker} skipping split day: {dt.strftime('%Y-%m-%d')}")
            continue
        delta_shares = shares_k - prev_shares_k
        flow = delta_shares * 1000 * nav
        fundflow.append([dt, flow])
    return fundflow


def fetch_proshares_csv(ticker, url):
    """Download ProShares CSV and compute daily fund flow."""
    logger.info(f"Downloading ProShares CSV for {ticker}: {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    text = resp.text
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        try:
            dt = datetime.strptime(row['Date'].strip(), '%m/%d/%Y').replace(hour=8)
            nav = float(row['NAV']) if row.get('NAV') else None
            shares_str = row.get('Shares Outstanding (000)', '').replace(',', '').strip()
            shares_k = float(shares_str) if shares_str else None
            rows.append((dt, nav, shares_k))
        except (ValueError, KeyError) as e:
            logger.warning(f"{ticker} skipping row: {e}")
            continue

    logger.info(f"{ticker}: {len(rows)} rows from CSV")
    fundflow = _compute_fundflow(rows, ticker)
    logger.info(f"{ticker}: {len(fundflow)} fund flow data points")

    pkl_path = os.path.join(folder, f"series_etf_{ticker}_fundflow.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": f"{ticker}-fundflow", "data": fundflow}, f)
    logger.info(f"Saved -> {pkl_path}")
    return True


def fetch_all():
    """Fetch all ETF fund flow data."""
    for ticker, url in PROSHARES_TICKERS.items():
        try:
            fetch_proshares_csv(ticker, url)
        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")


if __name__ == "__main__":
    fetch_all()
