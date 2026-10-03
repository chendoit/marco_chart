# -*- coding: utf-8 -*-
"""把 data/*.csv 整理成頁面用的 data/chart_data.js（window.AUD = {...}）

用 .js 而不是 .json：aud_case.html 直接用 file:// 開啟時 fetch() 會被瀏覽器擋，<script src> 不會。
先跑 fetch_data.py，再跑本檔。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
START = "2000-01-01"


def third_wednesday(y, m):
    first = pd.Timestamp(y, m, 1)
    return first + pd.Timedelta(days=(2 - first.weekday()) % 7 + 14)


def is_roll_window(d):
    """IMM 季月（3/6/9/12）換月週：週二報告日在第三個週三之前約 8 天，舊合約未平、新合約已建立，OI 雙計。
    實測 AUD 2010–2026：gap=8 那週 OI 平均 +10.0%，下一週（gap=1）平均 −20.2%，非季月週約 +1.6%。"""
    if d.month not in (3, 6, 9, 12):
        return False
    gap = (third_wednesday(d.year, d.month) - d).days
    return 6 <= gap <= 9


def legacy(ccy):
    L = pd.read_csv(D / "cot_legacy.csv", parse_dates=["date"])
    return L[L.ccy == ccy].set_index("date").drop(columns="ccy")


def weekly(fx):
    a = legacy("AUD")
    T = pd.read_csv(D / "cot_tff.csv", parse_dates=["date"])
    t = T[T.ccy == "AUD"].set_index("date").drop(columns=["ccy", "oi"])
    w = a.join(t, how="left").loc[START:]
    w["fx"] = fx.audusd.reindex(w.index, method="ffill")
    w["roll"] = [is_roll_window(d) for d in w.index]
    # 交割週假訊號：2025-12 起每個季月的「第三個週三前一天」那週，非報告部位（小戶）多空同時暴增 4–10 倍，
    # 下一週就回到原位（AUD、NZD 都有，CAD 沒有）。2026-09-15 多空各多出約 17 萬口，就是付鵬說的「歷史天量」
    nonrep = w.nonrep_long + w.nonrep_short
    w["anom"] = nonrep > 3 * nonrep.rolling(26, min_periods=8).median().shift(1)
    for k in ["dealer", "am", "lev"]:
        w[k + "_net"] = w[k + "_long"] - w[k + "_short"]
    w["minside"] = np.minimum(w.nc_long, w.nc_short)  # 多空雙高：較小的那一邊有多大
    for c in ["AUD", "NZD", "CAD"]:
        x = legacy(c)
        w[c.lower() + "_net_pct"] = ((x.nc_long - x.nc_short) / x.oi * 100).reindex(w.index)
    dp, doi = w.fx.diff(), w.oi.diff()
    reg = np.select([(dp < 0) & (doi > 0), (dp < 0) & (doi <= 0), (dp >= 0) & (doi <= 0), (dp >= 0) & (doi > 0)],
                    ["new_short", "long_liq", "short_cover", "new_long"], default="")
    skip = w.roll | w.roll.shift(1, fill_value=False) | w.anom | w.anom.shift(1, fill_value=False)
    w["regime"] = np.where(skip, "roll", reg)
    w.loc[w.index[0], "regime"] = ""
    return w


def vol_weekly(fx):
    """63 個交易日實現波動率（年化 %），週五取樣；pct = 2000 年以來的百分位（只用當時已知的歷史）。"""
    lr = np.log(fx.audusd.dropna()).diff()
    rv = (lr.rolling(63).std() * np.sqrt(252) * 100).dropna()
    v = rv.groupby(rv.index.to_period("W-FRI")).tail(1).loc[START:]  # 每週最後一個交易日，不用未來的週五當標籤
    pct = v.expanding(52).apply(lambda s: (s[:-1] < s[-1]).mean() * 100, raw=True)
    return pd.DataFrame({"rv": v, "rv_pct": pct})


def monthly():
    p = pd.read_csv(D / "policy_rates.csv", parse_dates=["date"]).set_index("date")
    r = pd.read_csv(D / "rates_monthly.csv", parse_dates=["date"]).set_index("date")
    out = pd.DataFrame({
        "rba": p.AU, "fed": p.US, "rbnz": p.NZ, "boc": p.CA,
        "au_us": p.AU - p.US, "au_nz": p.AU - p.NZ, "au_ca": p.AU - p.CA,
        "sp3m": r.au3m - r.us3m, "sp10": r.au10 - r.us10,  # 澳減美：正 = 澳元利率較高
        "au_exp": r.au3m - p.AU, "us_exp": r.us3m - p.US,  # 3M − 政策利率，代替 OIS
    })
    return out.loc[START:].dropna(subset=["rba"])


def china(fx):
    c = pd.read_csv(D / "china.csv", parse_dates=["date"]).set_index("date")
    p = pd.read_csv(D / "policy_rates.csv", parse_dates=["date"]).set_index("date")
    aud = fx.audusd.resample("MS").mean()
    yoy = lambda s: (s / s.shift(12) - 1) * 100
    z = lambda s: (s - s.loc[START:].mean()) / s.loc[START:].std()
    out = pd.DataFrame({
        "iron": c.iron_ore, "copper": c.copper, "ppi": c.cn_ppi,
        "aud_yoy": yoy(aud), "iron_yoy": yoy(c.iron_ore), "cu_yoy": yoy(c.copper),
        # 付鵬賽馬（上）的「劈叉」：商品價格與澳洲利率本該同向（需求推動），2021 起高商品價格配低利率
        "iron_z": z(c.iron_ore), "rba_z": z(p.AU),
    })
    return out.loc[START:]


def quarterly_bop():
    b = pd.read_csv(D / "bop_quarterly.csv")
    b["date"] = pd.PeriodIndex(b.quarter.str.replace("-", ""), freq="Q").to_timestamp(how="end").normalize()
    b = b.set_index("date")
    r4 = lambda s: s.rolling(4).sum() / 1000
    out = pd.DataFrame({
        "ca4": r4(b.ca), "inflow4": -r4(b.fa), "eo4": r4(b.eo),
        "goods4": r4(b.goods), "serv4": r4(b.services), "pi4": r4(b.primary_income),
        "port4": -r4(b.fa_portfolio), "fdi4": -r4(b.fa_direct), "oth4": -r4(b.fa_other),
    })
    return out.loc[START:]


def race_table():
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
                if v:
                    rec[c] = True
            elif isinstance(v, str):
                if v:
                    rec[c] = v
            elif pd.notna(v):
                rec[c] = round(float(v), nd)
        out.append(rec)
    return out


if __name__ == "__main__":
    fx = pd.read_csv(D / "fx_daily.csv", parse_dates=["date"]).set_index("date")
    fxd = fx.loc[START:].copy()
    fxd["audnzd"] = fxd.audusd / fxd.nzdusd
    fxd["usd_inv"] = 100 / fxd.usd_broad  # 取倒數：上 = 美元走弱，和 AUD/USD 同向比較
    fxd = fxd.dropna(subset=["audusd"])
    w = weekly(fx)
    payload = {
        "asof": w.index[-1].strftime("%Y-%m-%d"),
        "fx": rows(fxd, ["audusd", "audnzd", "usd_inv", "us10"]),
        "vol": rows(vol_weekly(fx), ["rv", "rv_pct"], 2),
        "wk": rows(w, ["fx", "oi", "roll", "anom", "regime", "nc_long", "nc_short", "comm_long", "comm_short",
                       "nonrep_long", "nonrep_short", "am_long", "am_short", "lev_long", "lev_short",
                       "dealer_long", "dealer_short", "dealer_net", "am_net", "lev_net", "minside",
                       "aud_net_pct", "nzd_net_pct", "cad_net_pct"], 2),
        "m": rows(monthly(), ["rba", "fed", "rbnz", "boc", "au_us", "au_nz", "au_ca", "sp3m", "sp10",
                              "au_exp", "us_exp"], 3),
        "cn": rows(china(fx), ["iron", "copper", "ppi", "aud_yoy", "iron_yoy", "cu_yoy", "iron_z", "rba_z"], 2),
        "bop": rows(quarterly_bop(), ["ca4", "inflow4", "eo4", "goods4", "serv4", "pi4", "port4", "fdi4", "oth4"], 2),
        "raceTable": race_table(),
    }
    js = "window.AUD = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (D / "chart_data.js").write_text(js, encoding="utf-8")
    print(f"chart_data.js {len(js)/1024:.0f} KB; weeks={len(payload['wk'])} roll={int(w.roll.sum())} "
          f"anom={list(w.index[w.anom].strftime('%Y-%m-%d'))}")
