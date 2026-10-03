# -*- coding: utf-8 -*-
"""冬季取暖季極端路徑案例：一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/石油/data/：
- eia_weekly.csv   EIA WPSR 週資料（週五期末）：餾分油庫存（PADD 1/1A/1B/1C/3/US）、
                   煉廠開工率（US/PADD1/PADD3）、餾分油進出口、表觀需求、
                   美國天然氣地下庫存、美東/新英格蘭住宅取暖油價、美國零售柴油價
- eia_daily.csv    EIA 現貨日資料：NYH ULSD、USGC ULSD、WTI、Brent、Henry Hub
- yahoo_daily.csv  Yahoo 連續近月：TTF（EUR/MWh）、NG、HO、CL、BZ、EURUSD
- fred_monthly.csv FRED/IMF 歐洲天然氣月均價（PNGASEUUSDM，$/MMBtu），補 TTF=F 2017 年以前的歷史

來源：
- EIA:   https://api.eia.gov/v2/seriesid/<ID>?api_key=...（需 .env 的 EIA_API_KEY）
- Yahoo: https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>
- FRED:  https://api.stlouisfed.org/fred/series/observations（需 .env 的 FED_API_KEY）

抓不到的（付費或需 key）：GIE AGSI+（需 x-key）、ICE Low Sulphur Gasoil、Spark25/Spark30、
Baltic BLNG2。這幾項在 WN 筆記裡用新聞與報告數字代替，並註明來源。
"""
import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}

# (欄名, EIA series id)
EIA_WEEKLY = [
    ("dist_stk_padd1", "PET.WDISTP11.W"),
    ("dist_stk_padd1a", "PET.WDIST1A1.W"),
    ("dist_stk_padd1b", "PET.WDIST1B1.W"),
    ("dist_stk_padd1c", "PET.WDIST1C1.W"),
    ("dist_stk_padd3", "PET.WDISTP31.W"),
    ("dist_stk_us", "PET.WDISTUS1.W"),
    ("util_us", "PET.WPULEUS3.W"),
    ("util_padd1", "PET.W_NA_YUP_R10_PER.W"),
    ("util_padd3", "PET.W_NA_YUP_R30_PER.W"),
    ("dist_exp_us", "PET.WDIEXUS2.W"),
    ("dist_imp_us", "PET.WDIIMUS2.W"),
    ("dist_imp_padd1", "PET.WDIIM_R10-Z00_2.W"),
    ("dist_supplied_us", "PET.WDIUPUS2.W"),
    ("ng_storage_l48_bcf", "NG.NW2_EPG0_SWO_R48_BCF.W"),
    ("ho_resi_padd1", "PET.W_EPD2F_PRS_R10_DPG.W"),
    ("ho_resi_padd1a", "PET.W_EPD2F_PRS_R1X_DPG.W"),
    ("diesel_retail_us", "PET.EMD_EPD2D_PTE_NUS_DPG.W"),
]
EIA_DAILY = [
    ("ulsd_nyh", "PET.EER_EPD2DXL0_PF4_Y35NY_DPG.D"),
    ("ulsd_usgc", "PET.EER_EPD2DXL0_PF4_RGC_DPG.D"),
    ("wti", "PET.RWTC.D"),
    ("brent", "PET.RBRTE.D"),
    ("henry_hub", "NG.RNGWHHD.D"),
]
YAHOO = [("ttf", "TTF=F"), ("ng", "NG=F"), ("ho", "HO=F"), ("cl", "CL=F"),
         ("bz", "BZ=F"), ("eurusd", "EURUSD=X")]


def fetch_eia(series_id):
    key = os.getenv("EIA_API_KEY")
    r = requests.get(f"https://api.eia.gov/v2/seriesid/{series_id}",
                     params={"api_key": key}, timeout=60)
    r.raise_for_status()
    d = pd.DataFrame(r.json()["response"]["data"])
    s = pd.Series(pd.to_numeric(d["value"], errors="coerce").values,
                  index=pd.to_datetime(d["period"]))
    return s.sort_index()


def fetch_yahoo(ticker):
    # range=max 會被 Yahoo 自動降成較粗的頻率，改用 period1/period2 強制日線
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                     params={"period1": 0, "period2": 9999999999, "interval": "1d"},
                     headers=UA, timeout=60)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    idx = pd.to_datetime(res["timestamp"], unit="s").normalize()
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=idx, dtype=float)
    return s[~s.index.duplicated(keep="last")].dropna()


def fetch_fred(sid):
    # fredgraph.csv 常逾時，改走官方 API（.env 的 FED_API_KEY）
    r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                     params={"series_id": sid, "api_key": os.getenv("FED_API_KEY"),
                             "file_type": "json"}, timeout=60)
    r.raise_for_status()
    d = pd.DataFrame(r.json()["observations"])
    return pd.Series(pd.to_numeric(d["value"], errors="coerce").values,
                     index=pd.to_datetime(d["date"]))


def build(jobs, fn, name):
    cols = {}
    for col, sid in jobs:
        try:
            cols[col] = fn(sid)
            print(f"  {col:22s} {sid:34s} n={len(cols[col]):5d} last={cols[col].index[-1].date()} {cols[col].iloc[-1]}")
        except Exception as e:  # 單一序列失敗不擋其他
            print(f"  {col:22s} {sid:34s} FAILED {e}")
    df = pd.DataFrame(cols)
    df.index.name = "date"
    df.to_csv(OUT / name)
    print(f"-> {name} {df.shape}")


if __name__ == "__main__":
    build(EIA_WEEKLY, fetch_eia, "eia_weekly.csv")
    build(EIA_DAILY, fetch_eia, "eia_daily.csv")
    build(YAHOO, fetch_yahoo, "yahoo_daily.csv")
    build([("ngas_eu_imf", "PNGASEUUSDM")], fetch_fred, "fred_monthly.csv")
