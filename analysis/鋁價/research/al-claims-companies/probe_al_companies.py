# -*- coding: utf-8 -*-
"""Probe script for Alcoa (AA) and Century Aluminum (CENX) financial and stock data.
Fetches 10-year quarterly financial data from SEC EDGAR XBRL companyfacts API,
and 10-year daily stock prices from Yahoo Finance.
Outputs to Path(__file__).parent / "samples"
"""

import sys
import json
import urllib.request
from datetime import datetime
from pathlib import Path
import pandas as pd
import yfinance as yf

# Configure stdout encoding
sys.stdout.reconfigure(encoding="utf-8")

OUT_SAMPLES = Path(__file__).parent / "samples"
OUT_SAMPLES.mkdir(parents=True, exist_ok=True)

HEADERS = {'User-Agent': 'aluminum-research chunpin.chen@gmail.com'}

def fetch_edgar_facts(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik.zfill(10)}.json"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8'))

def parse_quarterly(facts: dict, ticker: str) -> pd.DataFrame:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    def extract_series(concept_list):
        records = []
        for cname in concept_list:
            if cname in us_gaap:
                for r in us_gaap[cname].get("units", {}).get("USD", []):
                    start = r.get("start")
                    end = r.get("end")
                    val = r.get("val")
                    form = r.get("form")
                    fp = r.get("fp")
                    fy = r.get("fy")
                    filed = r.get("filed")
                    if start and end and form in ["10-Q", "10-K"]:
                        d1 = datetime.strptime(start, "%Y-%m-%d")
                        d2 = datetime.strptime(end, "%Y-%m-%d")
                        days = (d2 - d1).days
                        records.append({
                            "start": start, "end": end, "days": days,
                            "val": val, "form": form, "fp": fp, "fy": fy,
                            "filed": filed, "concept": cname
                        })
        if not records:
            return pd.DataFrame()
        return pd.DataFrame(records)

    def get_3month_data(concept_list):
        df = extract_series(concept_list)
        if df.empty:
            return pd.Series(dtype=float)
        df3 = df[(df["days"] >= 75) & (df["days"] <= 105)].copy()
        if df3.empty:
            return pd.Series(dtype=float)
        df3 = df3.sort_values("filed").groupby("end").last()
        return df3["val"]

    def get_ytd_or_3month_da(concept_list):
        df = extract_series(concept_list)
        if df.empty:
            return pd.Series(dtype=float)
        
        df3 = df[(df["days"] >= 75) & (df["days"] <= 105)].copy()
        res = {}
        if not df3.empty:
            grouped = df3.sort_values("filed").groupby("end").last()
            for end, row in grouped.iterrows():
                res[end] = row["val"]
        
        ytd_df = df[df["form"].isin(["10-Q", "10-K"])].sort_values("filed").groupby(["fy", "fp"]).last().reset_index()
        for yr, group in ytd_df.groupby("fy"):
            q1_val = group[group["fp"] == "Q1"]["val"].values
            q2_val = group[group["fp"] == "Q2"]["val"].values
            q3_val = group[group["fp"] == "Q3"]["val"].values
            fy_val = group[group["fp"] == "FY"]["val"].values

            q1_end = group[group["fp"] == "Q1"]["end"].values
            if len(q1_val) > 0 and len(q1_end) > 0 and q1_end[0] not in res:
                res[q1_end[0]] = q1_val[0]

            q2_end = group[group["fp"] == "Q2"]["end"].values
            if len(q2_val) > 0 and len(q1_val) > 0 and len(q2_end) > 0 and q2_end[0] not in res:
                res[q2_end[0]] = q2_val[0] - q1_val[0]

            q3_end = group[group["fp"] == "Q3"]["end"].values
            if len(q3_val) > 0 and len(q2_val) > 0 and len(q3_end) > 0 and q3_end[0] not in res:
                res[q3_end[0]] = q3_val[0] - q2_val[0]

            fy_end = group[group["fp"] == "FY"]["end"].values
            if len(fy_val) > 0 and len(q3_val) > 0 and len(fy_end) > 0 and fy_end[0] not in res:
                res[fy_end[0]] = fy_val[0] - q3_val[0]

        return pd.Series(res).sort_index()

    rev_s = get_3month_data(["SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"])
    ni_s = get_3month_data(["NetIncomeLoss", "ProfitLoss"])
    op_s = get_3month_data(["OperatingIncomeLoss"])
    ebt_s = get_3month_data(["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest"])
    da_s = get_ytd_or_3month_da(["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "Depreciation"])

    all_dates = sorted(set(rev_s.index) | set(ni_s.index) | set(op_s.index) | set(ebt_s.index) | set(da_s.index))
    df_out = pd.DataFrame({"date": all_dates})
    df_out["ticker"] = ticker
    df_out["revenue"] = df_out["date"].map(rev_s)
    df_out["net_income"] = df_out["date"].map(ni_s)
    df_out["operating_income"] = df_out["date"].map(op_s) if not op_s.empty else df_out["date"].map(ebt_s)
    df_out["depreciation_amortization"] = df_out["date"].map(da_s)
    df_out["ebitda"] = df_out["operating_income"].fillna(0) + df_out["depreciation_amortization"].fillna(0)
    df_out["shipments_kt"] = None

    df_out = df_out[df_out["date"] >= "2015-01-01"].sort_values("date").reset_index(drop=True)
    return df_out

def run_probes():
    companies = [
        ("AA", "0001675149", "aa_quarterly.csv", "aa_daily.csv"),
        ("CENX", "0000949157", "cenx_quarterly.csv", "cenx_daily.csv")
    ]

    for ticker, cik, q_file, d_file in companies:
        print(f"\n--- Processing {ticker} ---")
        # 1. SEC EDGAR Quarterly
        try:
            print(f"Fetching SEC EDGAR facts for {ticker} (CIK {cik})...")
            facts = fetch_edgar_facts(cik)
            q_df = parse_quarterly(facts, ticker)
            out_p = OUT_SAMPLES / q_file
            q_df.to_csv(out_p, index=False, encoding="utf-8-sig")
            print(f"Saved {q_file} ({len(q_df)} rows, latest: {q_df['date'].max()})")
        except Exception as e:
            print(f"Error fetching SEC facts for {ticker}: {e}")

        # 2. Yahoo Finance Daily
        try:
            print(f"Fetching Yahoo Finance daily stock prices for {ticker}...")
            tk = yf.Ticker(ticker)
            hist = tk.history(period="10y", timeout=60)
            if not hist.empty:
                hist = hist.reset_index()
                hist["date"] = hist["Date"].dt.strftime("%Y-%m-%d")
                out_df = hist[["date", "Open", "High", "Low", "Close", "Volume"]]
                out_df.columns = ["date", "open", "high", "low", "close", "volume"]
                out_p = OUT_SAMPLES / d_file
                out_df.to_csv(out_p, index=False, encoding="utf-8-sig")
                print(f"Saved {d_file} ({len(out_df)} rows, latest: {out_df['date'].max()})")
            else:
                print(f"No history returned for {ticker}")
        except Exception as e:
            print(f"Error fetching Yahoo Finance daily for {ticker}: {e}")

if __name__ == "__main__":
    run_probes()
