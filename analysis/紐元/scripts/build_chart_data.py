# -*- coding: utf-8 -*-
"""把 data/*.csv 整理成頁面用的 data/chart_data.js（window.NZD = {...}）

用 .js 而不是 .json：nzd_case.html 直接用 file:// 開啟時 fetch() 會被瀏覽器擋，<script src> 不會。
先跑 fetch_data.py，再跑本檔。dairy_index.csv / nz_migration.csv 存在才會納入（由子代理另抓）。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
START = "2004-01-01"


def third_wednesday(y, m):
    first = pd.Timestamp(y, m, 1)
    return first + pd.Timedelta(days=(2 - first.weekday()) % 7 + 14)


def is_roll_window(d):
    """IMM 季月（3/6/9/12）換月週：週二報告日在第三個週三之前約 8 天，
    舊合約還沒平、新合約已建立，總持倉與各類多空被雙計而暴衝。
    實測 NZD 2010–2026：gap=8 那週 OI 平均 +12.1%，下一週（gap=1）平均 −23.6%，其他週約 +2%。"""
    if d.month not in (3, 6, 9, 12):
        return False
    gap = (third_wednesday(d.year, d.month) - d).days
    return 6 <= gap <= 9


def weekly():
    fx = pd.read_csv(D / "fx_daily.csv", parse_dates=["date"]).set_index("date")
    L = pd.read_csv(D / "cot_legacy.csv", parse_dates=["date"])
    T = pd.read_csv(D / "cot_tff.csv", parse_dates=["date"])
    n = L[L.ccy == "NZD"].set_index("date").drop(columns="ccy")
    a = L[L.ccy == "AUD"].set_index("date")
    t = T[T.ccy == "NZD"].set_index("date").drop(columns=["ccy", "oi"])
    w = n.join(t, how="left").loc[START:]
    w["fx"] = fx.nzdusd.reindex(w.index, method="ffill")
    w["roll"] = [is_roll_window(d) for d in w.index]
    w["nzd_net_pct"] = (w.nc_long - w.nc_short) / w.oi * 100
    w["aud_net_pct"] = ((a.nc_long - a.nc_short) / a.oi * 100).reindex(w.index)
    # 價格 × 持倉 四象限（換月週不判讀）
    dp, doi = w.fx.diff(), w.oi.diff()
    reg = np.select([(dp < 0) & (doi > 0), (dp < 0) & (doi <= 0), (dp >= 0) & (doi <= 0), (dp >= 0) & (doi > 0)],
                    ["new_short", "long_liq", "short_cover", "new_long"], default="")
    w["regime"] = np.where(w.roll | w.roll.shift(1, fill_value=False), "roll", reg)
    w.loc[w.index[0], "regime"] = ""
    return w


def monthly_rates():
    r = pd.read_csv(D / "rates_monthly.csv", parse_dates=["date"]).set_index("date").loc[START:]
    return pd.DataFrame({"sp10": r.us10 - r.nz10, "sp3m": r.us3m - r.nz3m}).dropna()


def quarterly_bop():
    b = pd.read_csv(D / "bop_quarterly.csv")
    b["date"] = pd.PeriodIndex(b.quarter.str.replace("-", ""), freq="Q").to_timestamp(how="end").normalize()
    b = b.set_index("date")
    r4 = lambda s: s.rolling(4).sum() / 1000
    out = pd.DataFrame({
        "ca_q": b.ca / 1000, "inflow_q": -b.fa / 1000,          # −FA = 資本淨流入，十億紐元
        "ca4": r4(b.ca), "inflow4": -r4(b.fa), "eo4": r4(b.eo),
        # 付鵬 4.1：投資收益記在經常帳（初級收入）。紐西蘭逆差的主體是付給外資的利息與利潤
        "gs4": r4(b.goods + b.services), "pi4": r4(b.primary_income),
        "port_in4": -r4(b.fa_portfolio), "other_in4": -r4(b.fa_other),
    })
    return out.loc[START:]


def monthly_race():
    """賽馬：對手央行 − 紐西蘭的政策利率差，以及「3M 市場利率 − 政策利率」當短端預期代理。
    3M − 政策利率 2004 年以來中位數約 0.21pp（期限與信用溢價），明顯高於中位數 ≈ 市場在定價升息。"""
    p = pd.read_csv(D / "policy_rates.csv", parse_dates=["date"]).set_index("date")
    r = pd.read_csv(D / "rates_monthly.csv", parse_dates=["date"]).set_index("date")
    out = pd.DataFrame({
        "ocr": p.NZ, "fed": p.US, "rba": p.AU,
        "us_nz": p.US - p.NZ, "au_nz": p.AU - p.NZ,
        "nz_exp": r.nz3m - p.NZ, "us_exp": r.us3m - p.US,
    })
    return out.loc[START:].dropna(subset=["ocr"])


def race_table():
    """最新月份：各央行政策利率、12/24 個月變化，與同期對美元匯率變化（%）。"""
    p = pd.read_csv(D / "policy_rates.csv", parse_dates=["date"]).set_index("date").dropna(how="all")
    fx = pd.read_csv(D / "g10_fx.csv", parse_dates=["date"]).set_index("date").ffill()
    t, names = p.index[-1], {"US": "美國", "NZ": "紐西蘭", "AU": "澳洲", "CA": "加拿大", "GB": "英國",
                             "XM": "歐元區", "JP": "日本", "CH": "瑞士"}
    out = []
    for c in p.columns:
        rec = {"c": names[c], "rate": p[c].iloc[-1],
               "ch12": p[c].iloc[-1] - p[c].asof(t - pd.DateOffset(months=12)),
               "ch24": p[c].iloc[-1] - p[c].asof(t - pd.DateOffset(months=24))}
        if c in fx:
            rec["fx12"] = (fx[c].asof(t) / fx[c].asof(t - pd.DateOffset(months=12)) - 1) * 100
            rec["fx24"] = (fx[c].asof(t) / fx[c].asof(t - pd.DateOffset(months=24)) - 1) * 100
        out.append({k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in rec.items()})
    return {"asof": t.strftime("%Y-%m"), "rows": sorted(out, key=lambda r: -r["ch12"])}


def rows(df, cols, nd=4):
    out = []
    for d, r in df[cols].iterrows():
        rec = {"d": d.strftime("%Y-%m-%d")}
        for c in cols:
            v = r[c]
            if isinstance(v, (bool, np.bool_)):
                rec[c] = bool(v)
            elif isinstance(v, str):
                rec[c] = v
            elif pd.notna(v):
                rec[c] = round(float(v), nd)
        out.append(rec)
    return out


def optional_csv(name, cols):
    f = D / name
    if not f.exists():
        return None
    df = pd.read_csv(f, parse_dates=["date"]).set_index("date").loc[START:]
    return rows(df, [c for c in cols if c in df.columns], 1)


if __name__ == "__main__":
    fx = pd.read_csv(D / "fx_daily.csv", parse_dates=["date"]).set_index("date").loc[START:]
    fx["audnzd"] = fx.audusd / fx.nzdusd
    w = weekly()
    payload = {
        "asof": w.index[-1].strftime("%Y-%m-%d"),
        "fx": rows(fx, ["nzdusd", "audusd", "audnzd"]),
        "wk": rows(w, ["fx", "oi", "roll", "regime", "nc_long", "nc_short", "comm_long", "comm_short",
                       "am_long", "am_short", "lev_long", "lev_short", "dealer_long", "dealer_short",
                       "nzd_net_pct", "aud_net_pct"], 2),
        "rates": rows(monthly_rates(), ["sp10", "sp3m"], 2),
        "bop": rows(quarterly_bop(), ["ca_q", "inflow_q", "ca4", "inflow4", "eo4", "gs4", "pi4",
                                      "port_in4", "other_in4"], 2),
        "race": rows(monthly_race(), ["ocr", "fed", "rba", "us_nz", "au_nz", "nz_exp", "us_exp"], 3),
        "raceTable": race_table(),
        "dairy": optional_csv("dairy_index.csv", ["value"]),
        "migr": optional_csv("nz_migration.csv", ["net_total", "net_nz_citizens", "net_non_nz"]),
    }
    js = "window.NZD = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (D / "chart_data.js").write_text(js, encoding="utf-8")
    print(f"chart_data.js {len(js)/1024:.0f} KB; weeks={len(payload['wk'])} roll={int(w.roll.sum())} "
          f"dairy={'yes' if payload['dairy'] else 'no'} migr={'yes' if payload['migr'] else 'no'}")
