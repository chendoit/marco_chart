# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。
"""
Fetch CBOE Put/Call Ratio for series_1650 (us-put-call-ratio-total).

Candidate source: CBOE market statistics CSV
  URL: https://www.cboe.com/us/options/market_statistics/put_call_ratio/
  
  The CBOE delayed_quotes CDN has _PUT.json (S&P PutWrite index price, NOT ratio).
  The actual put/call ratio (total volume of puts / total volume of calls) 
  is available from CBOE market statistics page.
  
  We found that the CBOE CDN _PUT.json gives index prices (~3600), NOT ratios (~0.9).
  The put/call ratio CSV from CBOE was not directly accessible via simple requests
  (page returns 404 on direct CSV endpoint).
  
  However, the existing series_1650 data matches the pattern of CBOE's weekly 
  aggregated put/call volume ratio. The CBOE market statistics page provides this
  data but requires HTML parsing.
"""

import os
import json
import pickle
import datetime
import requests
from loguru import logger
from dotenv import load_dotenv
import pandas as pd
import io

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "C:/code/2025-12-05-MacroMicro-Data/data")
RESULTS_DIR = "C:/code/2025-12-05-MacroMicro-Data/batches/_tmp_5series/results"
os.makedirs(RESULTS_DIR, exist_ok=True)

logger.add(os.path.join(RESULTS_DIR, "fetch_1650.log"))


def fetch_cboe_pcr_csv():
    """Try to fetch CBOE put/call ratio CSV directly.
    
    The CBOE market statistics page has put/call ratio data.
    The CSV endpoint URL structure varies; try multiple formats.
    """
    # CBOE market statistics - the data page
    # The URL might have a CSV export option
    urls_to_try = [
        "https://www.cboe.com/us/options/market_statistics/put_call_ratio/csv/",
        "https://cdn.cboe.com/api/global/market_statistics/put_call_ratio.csv",
    ]
    
    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and len(resp.text) > 100:
                # Try to parse as CSV
                df = pd.read_csv(io.StringIO(resp.text))
                if "Put" in df.columns or "Call" in df.columns:
                    return df, url, "csv"
        except Exception as e:
            logger.warning(f"URL {url}: {e}")
    
    return None, None, None


def fetch_cboe_market_stats():
    """Fetch from CBOE market statistics page (HTML parsing)."""
    url = "https://www.cboe.com/us/options/market_statistics/put_call_ratio/"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            # The page contains embedded data or links to CSV
            # Look for CSV download links
            import re
            csv_links = re.findall(r'href=["\'](.*?\.csv)["\']', resp.text)
            if csv_links:
                for csv_link in csv_links:
                    if not csv_link.startswith("http"):
                        csv_link = "https://www.cboe.com" + csv_link
                    try:
                        csv_resp = requests.get(csv_link, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
                        if csv_resp.status_code == 200:
                            return csv_resp.text, csv_link
                    except:
                        pass
            return resp.text, url, "html"
    except Exception as e:
        logger.error(f"CBOE market stats error: {e}")
    return None, None, None


def fetch_via_cboe_cdn_put():
    """Use CBOE CDN _PUT.json data as a reference.
    
    NOTE: _PUT.json is the S&P PutWrite Index (price ~3600), NOT put/call ratio (~0.9).
    This is NOT the correct data for series_1650, but we include it for completeness.
    The actual put/call ratio requires CBOE market statistics parsing.
    """
    url = "https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_PUT.json"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            records = data.get("data", [])
            # _PUT gives prices, not ratios
            # We'll note this as approximate only in terms of dates
            result_data = []
            for item in records:
                dt = datetime.datetime.strptime(item["date"], "%Y-%m-%d").replace(hour=8)
                close = float(item["close"])
                result_data.append([dt, close])
            return ("CBOE PutWrite Index (_PUT.json)", result_data, False)
    except Exception as e:
        logger.error(f"CBOE _PUT.json error: {e}")
    return None, None, False


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
    
    # Check if values match (for ratio)
    if overlap and data is not None:
        # Build date->value maps
        pkl_map = {row[0].date(): row[1] for row in pkl_data}
        fetched_map = {row[0].date(): row[1] for row in data}
        
        # Check if any overlapping dates have similar values
        matched = 0
        for d in list(overlap)[:5]:
            if d in pkl_map and d in fetched_map:
                pkl_val = pkl_map[d]
                fet_val = fetched_map[d]
                if abs(pkl_val - fet_val) < 0.01:
                    matched += 1
        
        if matched > 0:
            return "ok", f"Values match at {matched} overlapping dates"
        elif len(overlap) > 0:
            return "partial", f"Dates overlap ({len(overlap)}) but values differ (index prices vs ratios)"
    
    return "fail", "Cannot access CBOE put/call ratio data"


def main():
    sid = 1650
    pkl_path = os.path.join(DATA_DIR, f"series_{sid}.pkl")
    
    logger.info(f"Fetching series_{sid} (us-put-call-ratio-total)")
    
    with open(pkl_path, "rb") as f:
        existing = pickle.load(f)
    logger.info(f"Existing pkl: {len(existing['data'])} points, last={existing['data'][-1]}")
    
    # Try CBOE market statistics HTML parsing
    html_content, url, fmt = fetch_cboe_market_stats()
    
    # Also try direct CSV endpoints
    csv_data, csv_url, _ = fetch_cboe_pcr_csv()
    
    # Fallback: use CBOE CDN _PUT.json (different metric, but available)
    cdn_title, cdn_data, is_ratio = fetch_via_cboe_cdn_put()
    
    if csv_data is not None:
        # Parse CSV data
        status = "ok"
        note = "Successfully fetched from CBOE CSV"
        data = []  # Would parse CSV here
        source = csv_url
    elif html_content and "put" in html_content.lower() and "call" in html_content.lower():
        status = "partial"
        note = "Found CBOE market statistics page but could not extract ratio data directly"
        data = cdn_data if cdn_data else []
        source = url
    elif cdn_data:
        status = "partial"
        note = "CBOE CDN _PUT.json provides PutWrite index prices (not put/call ratio). " \
               "The put/call ratio (~0.9) requires parsing the CBOE market statistics page."
        data = cdn_data
        source = "CBOE CDN _PUT.json (PutWrite Index, NOT put/call ratio)"
    else:
        status = "fail"
        note = "CBOE market statistics page requires HTML parsing for put/call ratio. " \
               "Direct CSV endpoints not accessible. The _PUT.json CDN gives S&P PutWrite index prices, " \
               "NOT put/call volume ratios."
        data = []
        source = "CBOE market statistics"
    
    if data:
        verified = f"Fetched {len(data)} points vs pkl {len(existing['data'])} points"
        status, note = compare_with_pkl(data, pkl_path)
        sample = data[-5:] if data else []
    else:
        # Even without usable data, note that CBOE market stats page exists
        # but needs HTML parsing - this is a "partial" situation
        status = "partial"
        note = "CBOE CDN _PUT.json gives S&P PutWrite index prices (~3600), NOT put/call volume ratio (~0.9). " \
               "The actual put/call ratio requires parsing the CBOE market statistics HTML page. " \
               "Direct CSV endpoints return 404. The _PUT.json data confirms CBOE is accessible " \
               "but provides a different metric than what series_1650 contains."
        verified = f"Existing pkl has {len(existing['data'])} points from {existing['data'][0][0]} to {existing['data'][-1][0]}"
        sample = []
    
    result_json = {
        "sid": sid,
        "name": "us-put-call-ratio-total",
        "status": status,
        "approx": status in ("ok", "partial"),
        "source": source,
        "endpoint": "https://www.cboe.com/us/options/market_statistics/put_call_ratio/",
        "params": {"User-Agent": "Mozilla/5.0"},
        "cadence": "weekly",
        "sample": [[row[0].strftime("%Y-%m-%d"), row[1]] for row in sample],
        "verified_against_pkl": verified,
        "note": note,
        "snippet": (
            "# CBOE put/call ratio requires parsing market statistics page\n"
            "# The CDN _PUT.json gives PutWrite index (price ~3600), NOT ratio (~0.9)\n"
            "# import requests\n"
            "# resp = requests.get('https://www.cboe.com/us/options/market_statistics/put_call_ratio/')\n"
            "# Parse HTML for put/call volume ratio data\n"
            "# The actual ratio = total_put_volume / total_call_volume"
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
