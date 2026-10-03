# -*- coding: utf-8 -*-
"""紐元學習案例：一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/紐元/data/：
- cot_legacy.csv   CFTC Legacy Futures-only，NZD(112741) + AUD(232741)，1999 起，週(週二)
- cot_tff.csv      CFTC TFF Futures-only，NZD + AUD，2006-06 起，週
- fx_daily.csv     NZDUSD / AUDUSD 日資料：FRED DEXUSNZ/DEXUSAL，尾端用 Yahoo chart API 補到最新
- rates_monthly.csv 美/紐 10Y 與 3M 利率（FRED/OECD MEI），月
- bop_quarterly.csv 紐西蘭國際收支（OECD SDMX DF_BOP），季，百萬紐元，未季調

來源：
- CFTC Socrata: https://publicreporting.cftc.gov/resource/6dca-aqww.json (legacy) / gpe5-46if.json (TFF)
- FRED:  https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>
- Yahoo: https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>
- OECD:  https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_BOP@DF_BOP,/NZL..........

BoP 符號慣例（BPM6）：FA = 資產淨取得 − 負債淨發生。FA > 0 = 淨對外放款 = 資本淨流出。
恆等式 CA + KA − FA + EO = 0。畫圖時用 net_inflow = −FA，讓「流入」在 0 軸上方（對應付鵬圖的橙色柱）。
"""
import io
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}


def fetch_cot(dataset, code):
    r = requests.get(
        f"https://publicreporting.cftc.gov/resource/{dataset}.json",
        params={"cftc_contract_market_code": code, "$limit": 50000,
                "$order": "report_date_as_yyyy_mm_dd"},
        timeout=60,
    )
    r.raise_for_status()
    d = pd.DataFrame(r.json())
    d["date"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]).dt.date
    return d


LEGACY_COLS = {
    "open_interest_all": "oi",
    "noncomm_positions_long_all": "nc_long",
    "noncomm_positions_short_all": "nc_short",
    "noncomm_postions_spread_all": "nc_spread",  # CFTC 原欄名就拼錯 postions
    "comm_positions_long_all": "comm_long",
    "comm_positions_short_all": "comm_short",
    "nonrept_positions_long_all": "nonrep_long",
    "nonrept_positions_short_all": "nonrep_short",
}
TFF_COLS = {
    "open_interest_all": "oi",
    "dealer_positions_long_all": "dealer_long",
    "dealer_positions_short_all": "dealer_short",
    "asset_mgr_positions_long": "am_long",
    "asset_mgr_positions_short": "am_short",
    "lev_money_positions_long": "lev_long",
    "lev_money_positions_short": "lev_short",
    "other_rept_positions_long": "other_long",
    "other_rept_positions_short": "other_short",
}


def build_cot(dataset, cols):
    frames = []
    for ccy, code in [("NZD", "112741"), ("AUD", "232741")]:
        d = fetch_cot(dataset, code)
        miss = [c for c in cols if c not in d.columns]
        if miss:
            raise KeyError(f"{dataset} 缺欄位 {miss}")
        f = d[["date"] + list(cols)].rename(columns=cols)
        for c in cols.values():
            f[c] = pd.to_numeric(f[c])
        f.insert(1, "ccy", ccy)
        frames.append(f)
    return pd.concat(frames).sort_values(["ccy", "date"])


def fred(series):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", timeout=60)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["date", series]
    d["date"] = pd.to_datetime(d["date"])
    d[series] = pd.to_numeric(d[series], errors="coerce")
    return d.dropna().set_index("date")[series]


def yahoo(ticker, rng="3mo"):
    r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
                     params={"range": rng, "interval": "1d"}, headers=UA, timeout=60)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(res["timestamp"], unit="s").normalize())
    return s.dropna()


def build_fx():
    out = {}
    for name, fid, yid in [("nzdusd", "DEXUSNZ", "NZDUSD=X"), ("audusd", "DEXUSAL", "AUDUSD=X")]:
        s = fred(fid)
        tail = yahoo(yid)
        s = pd.concat([s, tail[tail.index > s.index.max()]])  # FRED 延遲約一週，用 Yahoo 補尾端
        out[name] = s[~s.index.duplicated()]
    return pd.DataFrame(out).sort_index().round(4)


def build_rates():
    m = {"nz10": "IRLTLT01NZM156N", "us10": "IRLTLT01USM156N",
         "nz3m": "IR3TIB01NZM156N", "us3m": "IR3TIB01USM156N"}
    return pd.DataFrame({k: fred(v) for k, v in m.items()}).loc["1990":]


def build_bop():
    u = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_BOP@DF_BOP,/NZL.........."
         "?startPeriod=1990-Q1&format=csvfile")
    d = pd.read_csv(io.StringIO(requests.get(u, timeout=180).text))
    q = d[(d.FREQ == "Q") & (d.UNIT_MEASURE == "XDC") & (d.ADJUSTMENT == "N")
          & d.ACCOUNTING_ENTRY.isin(["B", "N"])]
    p = q.pivot_table(index="TIME_PERIOD", columns="MEASURE", values="OBS_VALUE")
    keep = {"CA": "ca", "G": "goods", "S": "services", "IN1": "primary_income", "KA": "ka",
            "FA": "fa", "FA_D_F": "fa_direct", "FA_P_F": "fa_portfolio", "FA_O_F": "fa_other",
            "FA_F_F7": "fa_deriv", "FA_R_F_S121": "fa_reserves", "EO": "eo"}
    p = p[[c for c in keep if c in p.columns]].rename(columns=keep)
    p.index.name = "quarter"
    return p.round(0)


if __name__ == "__main__":
    legacy = build_cot("6dca-aqww", LEGACY_COLS)
    legacy.to_csv(OUT / "cot_legacy.csv", index=False)
    tff = build_cot("gpe5-46if", TFF_COLS)
    tff.to_csv(OUT / "cot_tff.csv", index=False)
    fx = build_fx()
    fx.to_csv(OUT / "fx_daily.csv", index_label="date", date_format="%Y-%m-%d")
    rates = build_rates()
    rates.to_csv(OUT / "rates_monthly.csv", index_label="date", date_format="%Y-%m-%d")
    bop = build_bop()
    bop.to_csv(OUT / "bop_quarterly.csv")
    for name, df in [("cot_legacy", legacy), ("cot_tff", tff), ("fx", fx), ("rates", rates), ("bop", bop)]:
        print(f"{name:10s} rows={len(df):6d}  {df.iloc[0, 0] if 'date' in df else df.index[0]} → "
              f"{df.iloc[-1, 0] if 'date' in df else df.index[-1]}")
