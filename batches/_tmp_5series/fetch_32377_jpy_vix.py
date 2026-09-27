# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。
"""
Fetch JVIX (Japan Volatility Index) for series_32377 (jpy-vix).

Candidate source: Japan Volatility Index (JVIX) from Osaka University
  URL: https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/
  DNS resolution fails for wwws.econ.osaka-u.ac.jp in this environment.
  
  Alternatives explored:
  - yfinance ^JVIX: NOT available (404)
  - FRED: No Japan VIX series found
  - CBOE IRVX/TYVX: US interest rate vol, NOT Japanese
  - CBOE VXN: Nasdaq volatility, NOT Japanese

  The JVIX data from MacroMicro starts from 1995 with ~201 data points
  (mostly monthly, some weekly). No free public source reproduces this.
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

logger.add(os.path.join(RESULTS_DIR, "fetch_32377.log"))


def fetch_via_yfinance():
    """Try yfinance for Japanese VIX proxies."""
    # Try various Japanese volatility tickers
    tickers = ["^JVIX", "^JPVIX", "^NKY", "^N225"]
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1mo")
            if len(hist) > 0:
                logger.info(f"{ticker}: {len(hist)} records available")
        except:
            pass
    
    # ^NKY (Nikkei 225) exists but is the index price, not volatility
    # No Japanese VIX equivalent on yfinance
    logger.info("No Japanese VIX equivalent found on yfinance")
    return None


def fetch_via_osaka_csv():
    """Try Osaka University JVIX CSV.
    
    Note: DNS resolution fails in this environment.
    This would be the primary source in a normal environment.
    """
    urls = [
        "https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/jvix.csv",
        "https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/data.csv",
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                # Parse CSV
                import pandas as pd
                import io
                df = pd.read_csv(io.StringIO(resp.text))
                # Format: date, value
                data = []
                for _, row in df.iterrows():
                    dt = pd.to_datetime(row.iloc[0]).replace(hour=8)
                    val = float(row.iloc[1])
                    data.append([dt, val])
                return data
        except Exception as e:
            logger.warning(f"Osaka URL {url}: {str(e)[:60]}")
    
    return None


def fetch_via_cboe_alternatives():
    """Check if CBOE has any Japan volatility proxy."""
    # IRVX, TYVX are US interest rate volatility
    # VXN is Nasdaq - not Japan
    # No CBOE symbol covers Japanese volatility
    logger.info("No CBOE Japan volatility proxy available")
    return None


def compare_with_pkl(data, pkl_path):
    """Compare against existing pkl."""
    with open(pkl_path, "rb") as f:
        pkl = pickle.load(f)
    pkl_data = pkl["data"]
    
    if not data:
        return "fail", "No data available"
    
    pkl_dates = {row[0].date() for row in pkl_data}
    fetched_dates = {row[0].date() for row in data}
    overlap = pkl_dates & fetched_dates
    
    if len(overlap) > 0:
        return "partial", f"Dates overlap ({len(overlap)}) but may differ"
    return "fail", "Cannot access JVIX data from free sources"


def main():
    sid = 32377
    pkl_path = os.path.join(DATA_DIR, f"series_{sid}.pkl")
    
    logger.info(f"Fetching series_{sid} (jpy-vix)")
    
    with open(pkl_path, "rb") as f:
        existing = pickle.load(f)
    logger.info(f"Existing pkl: {len(existing['data'])} points, {existing['data'][0][0]} to {existing['data'][-1][0]}")
    
    # Try Osaka CSV (will likely fail due to DNS)
    osaka_data = fetch_via_osaka_csv()
    
    # Try yfinance
    yfinance_data = fetch_via_yfinance()
    
    if osaka_data:
        status, note = compare_with_pkl(osaka_data, pkl_path)
        data = osaka_data
        source = "Osaka University JVIX CSV"
        endpoint = "https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/jvix.csv"
    elif yfinance_data:
        status, note = compare_with_pkl(yfinance_data, pkl_path)
        data = yfinance_data
        source = "yfinance"
        endpoint = "yfinance"
    else:
        status = "fail"
        note = "JVIX (Japan Volatility Index) data source unavailable. " + \
               "Osaka University site (wwws.econ.osaka-u.ac.jp) has DNS resolution issues. " + \
               "No free public source (yfinance, FRED, CBOE) provides Japanese VIX data. " + \
               "yfinance ^JVIX, ^JPVIX, ^NKY all either don't exist or provide different data. " + \
               "CBOE IRVX/TYVX/VXN are US-based interest rate/equity volatility, NOT Japanese."
        data = []
        source = "Osaka University JVIX (unavailable)"
        endpoint = "https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/"
        # Save the note about alternatives
        alternatives = [
            "CBOE IRVX (30-day implied vol on 5Y Treasury) - US, NOT Japan",
            "CBOE TYVX (30-day implied vol on 30Y Treasury) - US, NOT Japan", 
            "CBOE VXN (Nasdaq VIX) - US tech vol, NOT Japan",
            "yfinance ^NKY (Nikkei 225 price) - price index, NOT volatility",
        ]
        note += " Alternatives explored: " + "; ".join(alternatives)
    
    if data:
        verified = f"Fetched {len(data)} points vs pkl {len(existing['data'])} points"
        sample = data[-5:] if data else []
    else:
        verified = f"Existing pkl has {len(existing['data'])} points from {existing['data'][0][0]} to {existing['data'][-1][0]}"
        sample = []
    
    result_json = {
        "sid": sid,
        "name": "jpy-vix",
        "status": status,
        "approx": status in ("ok", "partial"),
        "source": source,
        "endpoint": endpoint,
        "params": {},
        "cadence": "weekly/monthly",
        "sample": [[row[0].strftime("%Y-%m-%d"), row[1]] for row in sample],
        "verified_against_pkl": verified,
        "note": note,
        "snippet": (
            "# JVIX (Japan VIX) - no free public source available\n"
            "# Primary source: Osaka University\n"
            "# https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/\n"
            "# URL format: https://wwws.econ.osaka-u.ac.jp/~kawahara/jvix/jvix.csv\n"
            "#\n"
            "# No yfinance, FRED, or CBOE equivalent exists for Japanese VIX.\n"
            "# The only known free source is the Osaka University CSV download."
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
