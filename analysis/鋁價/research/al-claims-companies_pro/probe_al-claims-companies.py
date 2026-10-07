import yfinance as yf
import requests
import pandas as pd
from pathlib import Path
import time
import json

def fetch_yahoo(ticker, output_file):
    print(f"Fetching Yahoo Finance data for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="10y", interval="1d")
        if df.empty:
            print(f"No Yahoo data for {ticker}")
            return
        df.reset_index(inplace=True)
        # Convert Date to string
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')
        df.rename(columns={'Date': 'date'}, inplace=True)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {ticker} data to {output_file}")
    except Exception as e:
        print(f"Error fetching Yahoo data for {ticker}: {e}")

def fetch_sec(cik, output_file):
    print(f"Fetching SEC EDGAR data for CIK {cik}...")
    headers = {
        "User-Agent": "aluminum-research chunpin.chen@gmail.com"
    }
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # We need to extract Revenue, Net Income, EBITDA proxies, and maybe shipments
        us_gaap = data.get("facts", {}).get("us-gaap", {})
        
        rows = []
        for concept, details in us_gaap.items():
            if "units" in details and "USD" in details["units"]:
                for item in details["units"]["USD"]:
                    if "frame" in item and len(item["frame"]) == 6: # e.g. CY2021Q1
                        rows.append({
                            "concept": concept,
                            "end_date": item.get("end"),
                            "val": item.get("val"),
                            "frame": item.get("frame")
                        })
        
        if not rows:
            print(f"No USD frame data found for CIK {cik}")
            return
            
        df = pd.DataFrame(rows)
        # Pivot to have frame as index, concepts as columns
        # To handle duplicates, we can group by frame and concept and take the latest end_date or max value
        df = df.groupby(["frame", "concept", "end_date"])["val"].max().reset_index()
        df = df.groupby(["frame", "concept"])["val"].max().unstack()
        df.reset_index(inplace=True)
        df.rename(columns={'frame': 'date'}, inplace=True)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved SEC data to {output_file}")
    except Exception as e:
        print(f"Error fetching SEC data for CIK {cik}: {e}")

if __name__ == "__main__":
    out_dir = Path(__file__).parent / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    fetch_yahoo("AA", out_dir / "aa_daily.csv")
    fetch_yahoo("CENX", out_dir / "cenx_daily.csv")
    
    fetch_sec("0001675149", out_dir / "aa_quarterly.csv")
    fetch_sec("0000949157", out_dir / "cenx_quarterly.csv")
