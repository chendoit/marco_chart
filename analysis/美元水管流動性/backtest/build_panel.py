"""組回測用的日頻面板 panel.csv（以 SOFR 公布日為列），並計算 R1/R3/R4a/R6 的初版觸發。

資料來源（全部本地）：
- SOFR/TGCR：research/dealer-funding/daily/daily_repo.csv（2018-04 起），之後用 data/sofr_rate、tgcr_rate 補到最新
- IORB：raw/IOER.csv（~2021-07-28）+ data/fed_IORB
- EFFR：data/fed_DFF；OBFR：data/fed_OBFR
- SOFR P99：data/sofr_percent99（2021-08 起）
- SRF：research/nyfed-srf/srf_usage.csv、srf_rate.csv
- RRP：data/fed_RRPONTSYD；準備金：research/fed-balance-sheet；TGA：raw/WTREGEN.csv
- 市場：research/market-prices/market_prices.csv（SPY、QQQ、GLD、DX-Y.NYB）+ data/fed_DGS*、DTB3
- 標售結算：research/treasury-ops/auction_settlements.csv（毛額，2023 起）

分位門檻一律用「前 250 個交易日」（shift 1，不含當日），min_periods=120。
"""
import os
import pickle

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(ROOT, "data")
RES = os.path.join(HERE, "..", "research")


def pkl(name):
    with open(os.path.join(DATA, name + ".pkl"), "rb") as f:
        o = pickle.load(f)
    s = pd.Series({pd.Timestamp(d).normalize(): v for d, v in o["data"]}, dtype=float)
    return s[~s.index.duplicated(keep="last")].sort_index()


def raw(sid):
    d = pd.read_csv(os.path.join(HERE, "raw", f"{sid}.csv"), parse_dates=["date"])
    return d.set_index("date")[sid]


def build():
    rp = pd.read_csv(os.path.join(RES, "dealer-funding", "daily", "daily_repo.csv"), parse_dates=["date"])
    rp = rp.pivot_table(index="date", columns="series_key", values="value")
    sofr = rp["NYF-SOFR-RATE"].dropna().combine_first(pkl("sofr_rate"))
    tgcr = rp["NYF-TGCR-RATE"].dropna().combine_first(pkl("tgcr_rate"))
    df = pd.DataFrame({"sofr": sofr, "tgcr": tgcr})

    iorb = pd.concat([raw("IOER"), pkl("fed_IORB")])
    iorb = iorb[~iorb.index.duplicated(keep="last")].sort_index()
    df["iorb"] = iorb.reindex(df.index, method="ffill")
    df["effr"] = pkl("fed_DFF").reindex(df.index)
    df["obfr"] = pkl("fed_OBFR").reindex(df.index)
    df["sofr_p99"] = pkl("sofr_percent99").reindex(df.index)

    srf = pd.read_csv(os.path.join(RES, "nyfed-srf", "srf_usage.csv"), parse_dates=["date"]).set_index("date")
    df["srf_bn"] = srf["accepted_bn"].reindex(df.index)
    srate = pd.read_csv(os.path.join(RES, "nyfed-srf", "srf_rate.csv"), parse_dates=["date"]).set_index("date")
    df["srf_rate"] = srate["srf_min_bid_rate"].reindex(df.index, method="ffill")
    df.loc[df.index < "2021-07-28", "srf_rate"] = np.nan
    df["rrp_bn"] = pkl("fed_RRPONTSYD").reindex(df.index)

    fb = pd.read_csv(os.path.join(RES, "fed-balance-sheet", "fed_balance.csv"), parse_dates=["date"]).set_index("date")
    df["reserves_tn"] = (fb["reserves_wed"] / 1e6).reindex(df.index, method="ffill")
    df["tga_bn"] = (raw("WTREGEN") / 1e3).reindex(df.index, method="ffill")

    mp = pd.read_csv(os.path.join(RES, "market-prices", "market_prices.csv"), parse_dates=["date"])
    px = mp.pivot_table(index="date", columns="ticker", values="close")
    for t, col in [("SPY", "spy"), ("QQQ", "qqq"), ("GLD", "gld"), ("DX-Y.NYB", "dxy")]:
        df[col] = px[t].reindex(df.index)
    for t, col in [("SMH", "smh"), ("RSP", "rsp")]:
        df[col] = pkl(f"series_etf_{t}_close").reindex(df.index)
    for t in ["DGS10", "DGS1MO", "DGS30", "DTB3"]:
        df[t.lower()] = pkl(f"fed_{t}").reindex(df.index)

    st = pd.read_csv(os.path.join(RES, "treasury-ops", "auction_settlements.csv"), parse_dates=["date"])
    df["settle_bn"] = st.groupby("date")["offering_amount_bn"].sum().reindex(df.index)

    return df.sort_index()


def roll_q(s, q, n=250, minp=120):
    return s.rolling(n, min_periods=minp).quantile(q).shift(1)


def calendar_flags(idx):
    idx = pd.DatetimeIndex(idx)
    s = pd.Series(idx, index=idx)
    ym = idx.to_period("M")
    month_end = s.groupby(ym).transform("max") == s
    # 資料最後一個月還沒結束時，最後一列不是月底
    last = idx.max()
    if last < last + pd.offsets.BMonthEnd(0):
        month_end[last] = False
    quarter_end = month_end & idx.month.isin([3, 6, 9, 12])
    year_end = month_end & (idx.month == 12)
    tax = pd.Series(False, index=idx)
    for y in range(idx.year.min(), idx.year.max() + 1):
        for m in [1, 4, 6, 9, 12]:
            d = pd.Timestamp(y, m, 15)
            nxt = idx[idx >= d]
            if len(nxt) and (nxt[0] - d).days <= 4:
                tax[nxt[0]] = True
    return pd.DataFrame({"month_end": month_end.values, "quarter_end": quarter_end.values,
                         "year_end": year_end.values, "tax_day": tax.values}, index=idx)


def rules(df):
    o = pd.DataFrame(index=df.index)
    o["s_iorb"] = ((df.sofr - df.iorb) * 100).round(1)
    o["s_tgcr"] = ((df.sofr - df.tgcr) * 100).round(1)
    o["o_effr"] = ((df.obfr - df.effr) * 100).round(1)
    o["p99_srf"] = ((df.sofr_p99 - df.srf_rate) * 100).round(1)

    s = o.s_iorb
    p90, p95, p99 = roll_q(s, .90), roll_q(s, .95), roll_q(s, .99)
    o["r1_p95"] = p95
    l1 = (s >= np.maximum(p90, 3)) & (s.shift(1) >= np.maximum(p90.shift(1), 3))
    l2 = s.rolling(5).mean() >= np.maximum(p95, 4.5)
    l3 = s >= np.maximum(p99, 8)
    o["R1"] = np.select([l3, l2, l1], [3, 2, 1], 0)

    t = o.s_tgcr
    o["R3"] = np.select([t >= roll_q(t, .99), t >= roll_q(t, .95)], [2, 1], 0)

    cal = calendar_flags(df.index)
    o = o.join(cal)
    srf = df.srf_bn.fillna(0)
    o["srf_bn"] = df.srf_bn
    o["R4a"] = np.select([srf > 10, (srf > 2) & ~cal.quarter_end], [2, 1], 0)
    o["R2"] = np.select([o.p99_srf > 10, o.p99_srf > 5, o.p99_srf > 0], [3, 2, 1], 0)

    def z(col):
        r = np.log(df[col]).diff() * 100
        return (r / r.rolling(20, min_periods=15).std().shift(1)).round(2), r.round(2)

    for c in ["spy", "qqq", "gld", "dxy"]:
        o[f"z_{c}"], o[f"r_{c}"] = z(c)
    o["sector"] = ((np.log(df.smh).diff() - np.log(df.rsp).diff()) * 100).round(2)
    o["d10"] = (df.dgs10.diff() * 100).round(0)
    o["d1m"] = (df.dgs1mo.diff() * 100).round(0)
    o["d3m"] = (df.dtb3.diff() * 100).round(0)
    pre = (np.minimum(o.z_spy, o.z_qqq) < -1.5) & (o.z_gld < -1.5)
    t2 = pre & (o.d10 >= 5) & ((o.d1m <= 0) | (o.d3m <= 0))
    o["R6"] = np.select([t2, pre], [2, 1], 0)
    for c in ["rrp_bn", "reserves_tn", "tga_bn", "settle_bn"]:
        o[c] = df[c]
    return o


if __name__ == "__main__":
    df = build()
    o = rules(df)
    out = os.path.join(HERE, "panel.csv")
    o.rename_axis("date").to_csv(out, float_format="%.6g")
    print(out, o.index[0].date(), o.index[-1].date(), len(o))
