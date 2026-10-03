# -*- coding: utf-8 -*-
"""澳元學習案例：一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/澳元/data/：
- cot_legacy.csv    CFTC Legacy Futures-only，AUD(232741) + NZD(112741) + CAD(090741)，週(週二)
- cot_tff.csv       CFTC TFF Futures-only，同上三幣，2006-06 起
- fx_daily.csv      AUDUSD / NZDUSD / CADUSD 日資料 + 美 10Y（DGS10）+ 廣義美元指數（DTWEXBGS）：FRED，尾端用 Yahoo 補
- rates_monthly.csv 美/澳 10Y 與 3M 利率（FRED/OECD MEI），月
- bop_quarterly.csv 澳洲國際收支（OECD SDMX DF_BOP），季，百萬澳元，未季調
- policy_rates.csv  BIS WS_CBPOL 月底政策利率：US AU NZ CA GB XM JP CH，2000 起
- g10_fx.csv        月底匯率，統一成「1 單位外幣 = ? 美元」
- china.csv         月：鐵礦石、銅（IMF，經 FRED）、中國 PPI 年增率（FRED/OECD 到 2022-12，
                    之後用 DBnomics 轉載的國家統計局資料；NBS API 只給最近 13 個月，中間有缺口）

來源：
- CFTC Socrata: https://publicreporting.cftc.gov/resource/6dca-aqww.json (legacy) / gpe5-46if.json (TFF)
- FRED:  https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>
- Yahoo: https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>
- OECD:  https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_BOP@DF_BOP,/AUS..........
- BIS:   https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.<areas>
- DBnomics: https://api.db.nomics.world/v22/series/NBS/M_A010801/A01080101

RBA 官網的 F1 表（含真正的 AUD OIS）被 Akamai 擋掉（403），所以短端預期仍用「3M 銀行票據 − 現金利率」代替。

BoP 符號慣例（BPM6）：FA > 0 = 淨對外放款 = 資本淨流出；恆等式 CA + KA − FA + EO = 0。
"""
import io
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0"}
COT_CODES = [("AUD", "232741"), ("NZD", "112741"), ("CAD", "090741")]


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
    for ccy, code in COT_CODES:
        d = fetch_cot(dataset, code)
        miss = [c for c in cols if c not in d.columns]
        if miss:
            raise KeyError(f"{dataset} {ccy} 缺欄位 {miss}")
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
    for name, fid, yid, inv in [("audusd", "DEXUSAL", "AUDUSD=X", False), ("nzdusd", "DEXUSNZ", "NZDUSD=X", False),
                                ("cadusd", "DEXCAUS", "CADUSD=X", True)]:
        s = fred(fid)
        s = 1 / s if inv else s
        tail = yahoo(yid)
        s = pd.concat([s, tail[tail.index > s.index.max()]])  # FRED 延遲約一週，用 Yahoo 補尾端
        out[name] = s[~s.index.duplicated()]
    out["us10"] = fred("DGS10")
    out["usd_broad"] = fred("DTWEXBGS")  # 廣義美元指數（2006 起）：拆出「美元因素」
    return pd.DataFrame(out).sort_index().loc["1999":].round(4)


def build_rates():
    m = {"au10": "IRLTLT01AUM156N", "us10": "IRLTLT01USM156N",
         "au3m": "IR3TIB01AUM156N", "us3m": "IR3TIB01USM156N"}
    return pd.DataFrame({k: fred(v) for k, v in m.items()}).loc["1990":]


def build_bop():
    u = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_BOP@DF_BOP,/AUS.........."
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


AREAS = ["US", "AU", "NZ", "CA", "GB", "XM", "JP", "CH"]
G10 = {"AU": ("DEXUSAL", False), "NZ": ("DEXUSNZ", False), "CA": ("DEXCAUS", True), "GB": ("DEXUSUK", False),
       "XM": ("DEXUSEU", False), "JP": ("DEXJPUS", True), "CH": ("DEXSZUS", True)}


def bis_policy():
    u = (f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{'+'.join(AREAS)}"
         "?startPeriod=2000-01&format=csv")
    d = pd.read_csv(io.StringIO(requests.get(u, headers={"Accept": "text/csv"}, timeout=120).text))
    d["date"] = pd.to_datetime(d.TIME_PERIOD)
    return d.pivot_table(index="date", columns="REF_AREA", values="OBS_VALUE")[AREAS]


def g10_fx():
    out = {}
    for c, (sid, inv) in G10.items():
        s = fred(sid).loc["1999-12":]
        out[c] = 1 / s if inv else s
    m = pd.DataFrame(out).resample("ME").last()
    m.index = m.index.to_period("M").to_timestamp()
    return m.round(5)


def build_china():
    iron, cu = fred("PIORECRUSDM"), fred("PCOPPUSDM")
    ppi = fred("CHNPIEATI01GYM")  # OECD MEI，年增率 %，到 2022-12
    r = requests.get("https://api.db.nomics.world/v22/series/NBS/M_A010801/A01080101?observations=1", timeout=60)
    s = r.json()["series"]["docs"][0]
    nbs = pd.Series([v - 100 if v not in (None, "NA") else None for v in s["value"]],
                    index=pd.to_datetime(s["period"]), dtype=float).dropna()  # 上年同月=100 → 年增率
    ppi = pd.concat([ppi, nbs[nbs.index > ppi.index.max()]])
    return pd.DataFrame({"iron_ore": iron, "copper": cu, "cn_ppi": ppi}).loc["1999":].round(2)


if __name__ == "__main__":
    jobs = [
        ("cot_legacy", lambda: build_cot("6dca-aqww", LEGACY_COLS), False),
        ("cot_tff", lambda: build_cot("gpe5-46if", TFF_COLS), False),
        ("fx_daily", build_fx, True), ("rates_monthly", build_rates, True),
        ("bop_quarterly", build_bop, "quarter"), ("policy_rates", bis_policy, True),
        ("g10_fx", g10_fx, True), ("china", build_china, True),
    ]
    for name, fn, idx in jobs:
        df = fn()
        if idx == "quarter":
            df.to_csv(OUT / f"{name}.csv")
        elif idx:
            df.to_csv(OUT / f"{name}.csv", index_label="date", date_format="%Y-%m-%d")
        else:
            df.to_csv(OUT / f"{name}.csv", index=False)
        first, last = (df.iloc[0, 0], df.iloc[-1, 0]) if not idx else (df.index[0], df.index[-1])
        print(f"{name:14s} rows={len(df):6d}  {first} → {last}")
