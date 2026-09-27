# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。
"""
Fetch CME FedWatch probability data for series_484 (probability-fed-rate).

Candidate source: CME FedWatch Tool via option-implied probabilities
  from 30-Day Fed Funds futures (ZQ) options pricing.
  
  CME FedWatch API requires a paid subscription key.
  Alternative: yfinance ^ZQ (30-Day Fed Funds futures) but does NOT
  provide option-implied probabilities, only futures prices.
  
  Since the CME FedWatch API is paid and ^ZQ only gives futures prices
  (not probabilities), we fall back to yfinance ^ZQ as an approximate
  proxy. The actual probability series (0-100%) is NOT available from
  free sources, so status = 'fail'.

Endpoint: https://query1.finance.yahoo.com/v8/finance/chart/^ZQ
Params: period=1mo (test), interval=1d
Note: CME FedWatch API (paid) is the only true source for probabilities.
"""

import os
import sys
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

logger.add(os.path.join(RESULTS_DIR, "fetch_484.log"))


def fetch_via_yfinance():
    """Try yfinance ^ZQ as an approximate proxy.
    
    Returns (title, data) or None if unavailable.
    """
    try:
        t = yf.Ticker("^ZQ")
        # Get full history to match existing pkl
        hist = t.history(start="2015-01-01", end="2026-09-12")
        if len(hist) == 0:
            return None
        # Convert to [datetime, value] format (08:00 UTC+8)
        data = []
        for dt, row in hist.iterrows():
            value = float(row["Close"])
            dt_8 = dt.replace(hour=8, minute=0, second=0, microsecond=0)
            data.append([dt_8, value])
        return ("CME 30-Day Fed Funds Futures (^ZQ) Close Price", data)
    except Exception as e:
        logger.error(f"yfinance ^ZQ error: {e}")
        return None


def fetch_via_cme_fedwatch():
    """Attempt CME FedWatch API (paid - will likely fail)."""
    api_key = os.getenv("FED_API_KEY")
    # CME FedWatch API requires a paid key; there's no free public endpoint
    # This is documented as "candidate" but not freely accessible
    logger.info("CME FedWatch API requires paid subscription - skipping")
    return None


def compare_with_pkl(data, pkl_path):
    """Compare fetched data against existing pkl to determine status."""
    with open(pkl_path, "rb") as f:
        pkl = pickle.load(f)
    pkl_data = pkl["data"]
    
    if not data:
        return "fail", "No data available"
    
    # Check if data matches existing pkl values
    # The ^ZQ gives futures prices, not probability (0-100%)
    # So even if we match dates, values will be different
    # This means the source is NOT the same as the original
    last_pkl = pkl_data[-1]
    last_fetched = data[-1]
    
    # Check date overlap
    pkl_dates = {row[0].date() for row in pkl_data}
    fetched_dates = {row[0].date() for row in data}
    overlap = pkl_dates & fetched_dates
    
    if len(overlap) > 0:
        # Dates match but values are different (futures price vs probability)
        return "partial", f"Dates overlap ({len(overlap)} days) but values differ (futures price ≠ probability)"
    return "fail", "Cannot access CME FedWatch probability data from free sources"


def main():
    sid = 484
    pkl_path = os.path.join(DATA_DIR, f"series_{sid}.pkl")
    
    logger.info(f"Fetching series_{sid} (probability-fed-rate)")
    
    # Check existing pkl
    with open(pkl_path, "rb") as f:
        existing = pickle.load(f)
    logger.info(f"Existing pkl: {len(existing['data'])} points, last={existing['data'][-1]}")
    
    # Try yfinance as approximate source
    result = fetch_via_yfinance()
    
    if result:
        title, data = result
        status, note = compare_with_pkl(data, pkl_path)
        
        # Build result JSON
        sample = data[-5:] if data else []
        verified = f"Fetched {len(data)} points vs pkl {len(existing['data'])} points"
        
        result_json = {
            "sid": sid,
            "name": "probability-fed-rate",
            "status": status,
            "approx": True,
            "source": "yfinance ^ZQ (CME 30-Day Fed Funds futures)",
            "endpoint": "https://query1.finance.yahoo.com/v8/finance/chart/^ZQ",
            "params": {"interval": "1d", "period": "max"},
            "cadence": "daily",
            "sample": [[row[0].strftime("%Y-%m-%d"), row[1]] for row in sample],
            "verified_against_pkl": verified,
            "note": "yfinance ^ZQ gives futures close PRICES, not option-implied PROBABILITIES (0-100%). "
                    "The actual MacroMicro series_484 is derived from CME FedWatch tool which requires paid API. "
                    "Futures price direction loosely correlates with rate hike probability but is NOT the same metric. "
                    "CME FedWatch API requires paid subscription key; no free endpoint exists.",
            "snippet": (
                "import yfinance as yf\n"
                "t = yf.Ticker('^ZQ')\n"
                "hist = t.history(start='2015-01-01')\n"
                "data = [[dt.replace(hour=8), float(row['Close'])] for dt, row in hist.iterrows()]"
            ),
        }
    else:
        result_json = {
            "sid": sid,
            "name": "probability-fed-rate",
            "status": "fail",
            "approx": False,
            "source": "CME FedWatch API (paid)",
            "endpoint": "https://www.cmegroup.com/CmeWS/mvc/MarketData/FedWatch/30-Day",
            "params": {"api_key": "FED_API_KEY (paid subscription required)"},
            "cadence": "daily",
            "sample": [],
            "verified_against_pkl": f"Existing pkl has {len(existing['data'])} points from {existing['data'][0][0]} to {existing['data'][-1][0]}",
            "note": "CME FedWatch Tool (option-implied probabilities from ZQ options) requires paid API subscription. "
                    "yfinance ^ZQ only provides futures prices, not probabilities. No free source reproduces series_484.",
            "snippet": (
                "# Requires paid CME FedWatch API key\n"
                "# https://www.cmegroup.com/CmeWS/mvc/MarketData/FedWatch/30-Day\n"
                "# import requests\n"
                "# url = 'https://www.cmegroup.com/CmeWS/mvc/MarketData/FedWatch/30-Day'\n"
                "# resp = requests.get(url, headers={'x-apitoken': API_KEY})\n"
                "# data = resp.json()['settlements']"
            ),
        }
    
    # Write result JSON
    result_file = os.path.join(RESULTS_DIR, f"series_{sid}.json")
    with open(result_file, "w") as f:
        json.dump(result_json, f, indent=2, default=str)
    logger.info(f"Result written to {result_file}")
    print(json.dumps(result_json, indent=2, default=str))
    
    # Optionally save pkl if we got data
    if result and result_json["status"] in ("ok", "partial"):
        output_path = os.path.join(DATA_DIR, f"series_{sid}_approx.pkl")
        with open(output_path, "wb") as f:
            pickle.dump({"title": result_json["source"], "data": data}, f)
        logger.info(f"Approximate pkl saved to {output_path}")


if __name__ == "__main__":
    main()
