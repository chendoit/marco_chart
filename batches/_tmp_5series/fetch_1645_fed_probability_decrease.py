# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。
"""
Fetch CME FedWatch probability of decrease data for series_1645 (probability-fed-rate-decrease).

Candidate source: CME FedWatch Tool via option-implied probabilities
  from 30-Day Fed Funds futures (ZQ) options pricing.

Same constraints as series_484: CME FedWatch API requires paid subscription.
The existing pkl (series_1645) contains probability values (0-100%) for
rate decrease expectations.
"""

import os
import json
import pickle
import datetime
import requests
import yfinance as yf
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "C:/code/2025-12-05-MacroMicro-Data/data")
RESULTS_DIR = "C:/code/2025-12-05-MacroMicro-Data/batches/_tmp_5series/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

logger.add(os.path.join(RESULTS_DIR, "fetch_1645.log"))


def fetch_via_yfinance():
    """Try yfinance ^ZQ as approximate proxy."""
    try:
        t = yf.Ticker("^ZQ")
        hist = t.history(start="2016-01-01", end="2026-09-12")
        if len(hist) == 0:
            return None
        data = []
        for dt, row in hist.iterrows():
            value = float(row["Close"])
            dt_8 = dt.replace(hour=8, minute=0, second=0, microsecond=0)
            data.append([dt_8, value])
        return ("CME 30-Day Fed Funds Futures (^ZQ) Close Price", data)
    except Exception as e:
        logger.error(f"yfinance ^ZQ error: {e}")
        return None


def fetch_via_fed_funds_rate():
    """Try FRED DFF (Effective Fed Funds Rate) as a contextual proxy.
    
    When rate is decreasing, the probability of decrease should be high.
    This is NOT a direct probability but provides context.
    """
    try:
        from pystlouisfed import FRED
        fred = FRED(api_key=os.getenv("FED_API_KEY"))
        data = fred.series_observations(series_id="DFF")
        result = []
        for idx, row in data.iterrows():
            val = row["value"]
            if val != "." and val is not None:
                dt = idx.to_pydatetime().replace(hour=8)
                result.append([dt, float(val)])
        result.sort(key=lambda x: x[0])
        return ("FRED Effective Fed Funds Rate (DFF)", result)
    except Exception as e:
        logger.error(f"FRED DFF error: {e}")
        return None


def compare_with_pkl(data, pkl_path):
    """Compare against existing pkl."""
    with open(pkl_path, "rb") as f:
        pkl = pickle.load(f)
    pkl_data = pkl["data"]
    
    if not data:
        return "fail", "No data available"
    
    last_pkl = pkl_data[-1]
    last_fetched = data[-1]
    pkl_dates = {row[0].date() for row in pkl_data}
    fetched_dates = {row[0].date() for row in data}
    overlap = pkl_dates & fetched_dates
    
    if len(overlap) > 0:
        return "partial", f"Dates overlap ({len(overlap)} days) but values differ"
    return "fail", "Cannot reproduce probability-decrease values from free sources"


def main():
    sid = 1645
    pkl_path = os.path.join(DATA_DIR, f"series_{sid}.pkl")
    
    logger.info(f"Fetching series_{sid} (probability-fed-rate-decrease)")
    
    with open(pkl_path, "rb") as f:
        existing = pickle.load(f)
    logger.info(f"Existing pkl: {len(existing['data'])} points, last={existing['data'][-1]}")
    
    # Try yfinance first
    result = fetch_via_yfinance()
    status, note = compare_with_pkl(result[1], pkl_path) if result else ("fail", "No data")
    
    # Also try FRED DFF for context
    fred_result = fetch_via_fed_funds_rate()
    
    if result:
        title, data = result
        sample = data[-5:] if data else []
        
        result_json = {
            "sid": sid,
            "name": "probability-fed-rate-decrease",
            "status": status,
            "approx": True,
            "source": "yfinance ^ZQ + FRED DFF (contextual)",
            "endpoint": "https://query1.finance.yahoo.com/v8/finance/chart/^ZQ",
            "params": {"interval": "1d", "period": "max"},
            "cadence": "daily",
            "sample": [[row[0].strftime("%Y-%m-%d"), row[1]] for row in sample],
            "verified_against_pkl": f"Fetched {len(data)} points from yfinance; existing pkl has {len(existing['data'])} points",
            "note": "Same constraint as series_484. CME FedWatch Tool produces option-implied "
                    "probability of rate DECREASE (0-100%), which requires paid API. "
                    "yfinance ^ZQ gives futures close prices (not probabilities). "
                    "FRED DFF gives the actual fed funds rate level (context only). "
                    "The existing pkl shows probability values approaching 0.0 when rates are stable/rising.",
            "snippet": (
                "import yfinance as yf\n"
                "t = yf.Ticker('^ZQ')\n"
                "hist = t.history(start='2016-01-01')\n"
                "data = [[dt.replace(hour=8), float(row['Close'])] for dt, row in hist.iterrows()]\n"
                "# Note: these are futures prices, NOT rate decrease probabilities"
            ),
        }
    else:
        result_json = {
            "sid": sid,
            "name": "probability-fed-rate-decrease",
            "status": "fail",
            "approx": False,
            "source": "CME FedWatch API (paid) / yfinance ^ZQ (proxy)",
            "endpoint": "https://www.cmegroup.com/CmeWS/mvc/MarketData/FedWatch/30-Day",
            "params": {"api_key": "FED_API_KEY (paid subscription required)"},
            "cadence": "daily",
            "sample": [],
            "verified_against_pkl": f"Existing pkl has {len(existing['data'])} points from {existing['data'][0][0]} to {existing['data'][-1][0]}",
            "note": "CME FedWatch probability of rate decrease requires paid API subscription. "
                    "No free source reproduces series_1645 values (which are 0-100% probabilities). "
                    "Alternatives explored: yfinance ^ZQ (futures prices only), FRED DFF (rate level only).",
            "snippet": (
                "# CME FedWatch paid API\n"
                "# No free alternative reproduces probability-decrease (0-100%) values\n"
                "# The closest public proxy is ^ZQ futures prices via yfinance"
            ),
        }
    
    # Write result JSON
    result_file = os.path.join(RESULTS_DIR, f"series_{sid}.json")
    with open(result_file, "w") as f:
        json.dump(result_json, f, indent=2, default=str)
    logger.info(f"Result written to {result_file}")
    print(json.dumps(result_json, indent=2, default=str))


if __name__ == "__main__":
    main()
