# -*- coding: utf-8 -*-
"""賽馬補充：各央行政策利率（BIS）＋ G10 對美元匯率（FRED），一次性抓取

輸出到 analysis/紐元/data/：
- policy_rates.csv  BIS WS_CBPOL 月底政策利率：US NZ AU CA GB XM(歐元區) JP CH，2004 起
- g10_fx.csv        月底匯率，統一成「1 單位外幣 = ? 美元」（上 = 外幣升值）

來源：
- BIS:  https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.<areas>
- FRED: DEXUSNZ DEXUSAL DEXCAUS DEXUSUK DEXUSEU DEXJPUS DEXSZUS（CAD/JPY/CHF 取倒數）

付鵬「賽馬」：美國是錨，各國央行相對美國的收緊/放鬆速率決定交叉強弱。
市場利率（3M）減政策利率 ≈ 短端對下一步動作的定價，當作 OIS 的替代（RBNZ OIS 無免費來源）。
"""
import io
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent.parent / "data"
AREAS = ["US", "NZ", "AU", "CA", "GB", "XM", "JP", "CH"]
FX = {"NZ": ("DEXUSNZ", False), "AU": ("DEXUSAL", False), "CA": ("DEXCAUS", True), "GB": ("DEXUSUK", False),
      "XM": ("DEXUSEU", False), "JP": ("DEXJPUS", True), "CH": ("DEXSZUS", True)}


def bis_policy():
    u = (f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{'+'.join(AREAS)}"
         "?startPeriod=2004-01&format=csv")
    d = pd.read_csv(io.StringIO(requests.get(u, headers={"Accept": "text/csv"}, timeout=120).text))
    d["date"] = pd.to_datetime(d.TIME_PERIOD)
    return d.pivot_table(index="date", columns="REF_AREA", values="OBS_VALUE")[AREAS]


def fred(series):
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", timeout=60)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"])
    return pd.to_numeric(d.set_index("date").v, errors="coerce").dropna()


def g10_fx():
    out = {}
    for c, (sid, inv) in FX.items():
        s = fred(sid).loc["2003-12":]
        out[c] = 1 / s if inv else s
    m = pd.DataFrame(out).resample("ME").last()
    m.index = m.index.to_period("M").to_timestamp()
    return m.round(5)


if __name__ == "__main__":
    pol = bis_policy()
    pol.to_csv(OUT / "policy_rates.csv", index_label="date", date_format="%Y-%m-%d")
    fx = g10_fx()
    fx.to_csv(OUT / "g10_fx.csv", index_label="date", date_format="%Y-%m-%d")
    print(f"policy_rates rows={len(pol)} {pol.index[0]:%Y-%m} → {pol.index[-1]:%Y-%m}")
    print(f"g10_fx       rows={len(fx)} {fx.index[0]:%Y-%m} → {fx.index[-1]:%Y-%m}")
