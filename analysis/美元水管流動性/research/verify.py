"""機械驗收：verify.py market-prices | fed-balance-sheet | cftc-treasury | nyfed-srf | fima-repo | treasury-qra | treasury-ops | tv-gld-1m | dealer-funding"""
import os
import pickle
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data"))
errors = []


def check(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        errors.append(msg)


def load_csv(task, name, cols, key):
    path = os.path.join(HERE, task, name)
    if not os.path.exists(path):
        check(False, f"{name} 不存在")
        return None
    df = pd.read_csv(path)
    check(list(df.columns[: len(cols)]) == cols, f"欄位前段為 {cols}（實際 {list(df.columns)}）")
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    check(not df.duplicated(key).any(), f"主鍵 {key} 不重複")
    check(df.equals(df.sort_values(key)) or df[key].equals(df.sort_values(key)[key]), f"依 {key} 升冪")
    return df


def local_series(name):
    with open(os.path.join(DATA, name + ".pkl"), "rb") as f:
        o = pickle.load(f)
    s = pd.Series({pd.Timestamp(d).normalize(): v for d, v in o["data"]}, dtype=float)
    return s.sort_index()


def market_prices():
    df = load_csv(
        "market-prices",
        "market_prices.csv",
        ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"],
        ["ticker", "date"],
    )
    if df is None:
        return
    need = ["^GSPC", "^DJI", "^SOX", "^NDX", "QQQ", "SPY", "RSP", "INTC", "GLD", "GC=F", "SI=F", "DX-Y.NYB", "BTC-USD"]
    for t in need:
        d = df[df.ticker == t]
        check(len(d) > 0, f"{t} 有資料")
        if d.empty:
            continue
        check(d.date.min() <= pd.Timestamp("2018-01-02"), f"{t} 起始 <= 2018-01-02（{d.date.min().date()}）")
        check(d.date.max() == pd.Timestamp("2026-11-06") or (t in ("BTC-USD",) and d.date.max() >= pd.Timestamp("2026-11-06")),
              f"{t} 最新為已收盤交易日 2026-11-06（{d.date.max().date()}）")
        if t != "BTC-USD":
            check(not (d.date.dt.dayofweek >= 5).any(), f"{t} 沒有週末日期")
        d18 = d[d.date >= "2018-01-02"]  # 只驗後續分析用到的 2018 起；GC/SI 2001–2011 低量列 high/low 是 Yahoo 來源本身的問題
        bad = d18[(d18.high < d18[["open", "close"]].max(axis=1) - 1e-6) | (d18.low > d18[["open", "close"]].min(axis=1) + 1e-6)]
        check(len(bad) <= len(d18) * 0.01, f"{t} high/low 合理（2018 起異常 {len(bad)} 筆）")
        check(d[d.date >= "2026-10-20"]["close"].notna().all(), f"{t} 近期 close 無缺值")
    for t, local in [("^GSPC", "series_2"), ("QQQ", "series_etf_QQQ_close"), ("GC=F", "series_485"),
                     ("DX-Y.NYB", "series_483"), ("BTC-USD", "series_4249")]:
        a = df[df.ticker == t].set_index("date")["close"]
        b = local_series(local)
        j = pd.concat([a, b], axis=1, join="inner").dropna().tail(60)
        diff = ((j.iloc[:, 0] / j.iloc[:, 1] - 1).abs()).median() if len(j) else 1
        check(len(j) >= 30 and diff < 0.005, f"{t} 與本地 {local} 近 60 筆差異中位數 {diff:.5f}")


def fed_balance_sheet():
    df = load_csv(
        "fed-balance-sheet",
        "fed_balance.csv",
        ["date", "reserves_wed", "reserves_wavg", "bills_wed", "treasuries_wed"],
        ["date"],
    )
    if df is None:
        return
    check((df.date.dt.dayofweek == 2).all(), "日期都是週三")
    check(df.date.max() >= pd.Timestamp("2026-11-04"), f"最新 >= 2026-11-04（{df.date.max().date()}）")
    check(df.date.min() <= pd.Timestamp("2018-01-03"), f"起始 <= 2018-01-03（{df.date.min().date()}）")
    for c in ["reserves_wed", "reserves_wavg", "bills_wed", "treasuries_wed"]:
        recent = df[df.date >= "2026-09-01"][c]
        check(recent.notna().all() and (recent > 0).all(), f"{c} 近期完整且為正")
    recent = df[df.date >= "2026-09-01"]
    check((recent.reserves_wed.between(2e6, 5e6)).all(), "reserves_wed 單位為百萬美元")
    b = local_series("series_7449")
    a = df.set_index("date")
    for c in ["reserves_wed", "reserves_wavg"]:
        j = pd.concat([a[c], b], axis=1, join="inner").dropna().tail(20)
        print(f"info {c} vs series_7449 近 20 筆差異中位數 {(j.iloc[:, 0] - j.iloc[:, 1]).abs().median():.0f}（百萬美元）")
    print("info 近期：")
    print(df[df.date >= "2026-10-01"].to_string(index=False))


def cftc_treasury():
    cols = ["date", "contract", "open_interest", "lev_long", "lev_short", "lev_net",
            "asset_mgr_long", "asset_mgr_short", "dealer_long", "dealer_short"]
    df = load_csv("cftc-treasury", "cftc_treasury_tff.csv", cols, ["contract", "date"])
    if df is None:
        return
    for c in ["2Y", "5Y", "10Y", "ULTRA10Y", "TBOND", "ULTRABOND"]:
        d = df[df.contract == c]
        check(len(d) > 0, f"{c} 有資料")
        if d.empty:
            continue
        check(d.date.max() == pd.Timestamp("2026-11-03"), f"{c} 最新為 2026-11-03（{d.date.max().date()}）")
        check(d.date.min() <= pd.Timestamp("2018-01-02"), f"{c} 起始 <= 2018-01-02（{d.date.min().date()}）")
        check((d.lev_long - d.lev_short == d.lev_net).all(), f"{c} lev_net = lev_long - lev_short")
    check((df.date.dt.dayofweek == 1).mean() > 0.97, "報告日絕大多數為週二")


def nyfed_srf():
    cols = ["date", "ops_count", "submitted_bn", "accepted_bn", "accepted_treasury_bn", "accepted_agency_bn", "accepted_mbs_bn", "min_bid_rate"]
    df = load_csv("nyfed-srf", "srf_usage.csv", cols, ["date"])
    if df is not None:
        check(df.date.min() <= pd.Timestamp("2021-08-31"), f"srf_usage 起始 <= 2021-08-31（{df.date.min().date()}）")
        check(df.date.max() >= pd.Timestamp("2026-11-05"), f"srf_usage 最新 >= 2026-11-05（{df.date.max().date()}）")
        check((df.accepted_bn.dropna() >= 0).all() and df.accepted_bn.notna().mean() > 0.99, "accepted_bn 非負且幾乎無空值")
        check((df.date.dt.dayofweek < 5).all(), "日期都是工作日")
        r = df[(df.date >= "2026-10-26") & (df.date <= "2026-11-05")]
        check(len(r) >= 8, f"2026-10-26~11-05 至少 8 個營業日有列（{len(r)}）")
        print("info 近期："); print(df.tail(8).to_string(index=False))
        print(f"info accepted_bn 最大 {df.accepted_bn.max()}（{df.loc[df.accepted_bn.idxmax(),'date'].date()}）；>0 的天數 {(df.accepted_bn>0).sum()}")
    d2 = load_csv("nyfed-srf", "srf_rate.csv", ["date", "target_upper", "srf_min_bid_rate"], ["date"])
    if d2 is not None:
        check(d2.date.min() <= pd.Timestamp("2018-01-03"), f"srf_rate 起始 <= 2018-01-03（{d2.date.min().date()}）")
        check(d2.date.max() >= pd.Timestamp("2026-11-05"), f"srf_rate 最新 >= 2026-11-05（{d2.date.max().date()}）")
        check(d2.target_upper.notna().all(), "target_upper 無空值")


def fima_repo():
    df = load_csv("fima-repo", "fima_repo.csv", ["date", "fima_repo_wed", "fima_repo_wavg"], ["date"])
    if df is None:
        return
    check((df.date.dt.dayofweek == 2).all(), "日期都是週三")
    check(df.date.min() <= pd.Timestamp("2018-01-03"), f"起始 <= 2018-01-03（{df.date.min().date()}）")
    check(df.date.max() >= pd.Timestamp("2026-11-04"), f"最新 >= 2026-11-04（{df.date.max().date()}）")
    check(df.fima_repo_wed.notna().all() and (df.fima_repo_wed >= 0).all(), "fima_repo_wed 無空值且非負")
    check(df.fima_repo_wavg.notna().all() and (df.fima_repo_wavg >= 0).all(), "fima_repo_wavg 無空值且非負")
    check(df.date.diff().dropna().dt.days.max() <= 7, "每週都有列")
    print("info 近期："); print(df.tail(8).to_string(index=False))


def treasury_qra():
    df = load_csv("treasury-qra", "qra_tga_targets.csv", ["date", "quarter_end", "tga_assumption_bn", "source_url"], ["date", "quarter_end"])
    if df is None:
        return
    df["quarter_end"] = pd.to_datetime(df["quarter_end"])
    check(df.date.min() <= pd.Timestamp("2019-01-31"), f"起始 <= 2019-01-31（{df.date.min().date()}）")
    check(df.date.max() >= pd.Timestamp("2026-10-26"), f"最新公告 >= 2026-10-26（{df.date.max().date()}）")
    check((df.quarter_end == pd.Timestamp("2026-12-31")).any(), "含 2026-12-31 年底目標")
    check(df.tga_assumption_bn.between(50, 2000).all(), "tga_assumption_bn 在 50~2000（十億美元；2019-09-30 來源值為 85）")
    check(df.source_url.notna().all(), "每列都有 source_url")
    print("info 近期："); print(df.tail(8).to_string(index=False))


def treasury_ops():
    d1 = load_csv("treasury-ops", "treasury_buybacks.csv", ["date", "settle_date", "bucket", "par_submitted_bn", "par_accepted_bn"], ["date", "bucket"])
    if d1 is not None:
        check(d1.date.min() <= pd.Timestamp("2024-06-30"), f"buybacks 起始 <= 2024-06-30（{d1.date.min().date()}）")
        check(d1.date.max() >= pd.Timestamp("2026-10-01"), f"buybacks 最新 >= 2026-10-01（{d1.date.max().date()}）")
        check((d1.par_accepted_bn.dropna() >= 0).all(), "par_accepted_bn 非負")
        print("info buybacks 近期："); print(d1.tail(6).to_string(index=False))
    d2 = load_csv("treasury-ops", "auction_settlements.csv", ["date", "auction_date", "security_type", "security_term", "cusip", "offering_amount_bn"], ["date", "cusip"])
    if d2 is not None:
        check(d2.date.min() <= pd.Timestamp("2023-01-31"), f"auctions 起始 <= 2023-01-31（{d2.date.min().date()}）")
        check(d2.date.max() >= pd.Timestamp("2026-11-03"), f"auctions 最新 issue >= 2026-11-03（{d2.date.max().date()}）")
        types = set(d2.security_type.dropna().unique())
        check({"Bill", "Note", "Bond"} <= types, f"含 Bill/Note/Bond（{sorted(types)}）")
        n2 = d2[(d2.security_type == "Note") & (d2.security_term.astype(str).str.contains("2-Year"))]
        check(len(n2) >= 30, f"2-Year Note 至少 30 筆（{len(n2)}）")
        print("info auctions 近期："); print(d2.tail(6).to_string(index=False))



def tv_gld_1m():
    df = load_csv("tv-gld-1m", "gld_5m.csv", ["date", "time_et", "open", "high", "low", "close", "volume"], ["date", "time_et"])
    if df is None:
        return
    check(df.date.min() <= pd.Timestamp("2026-10-29"), f"起始 <= 2026-10-29（{df.date.min().date()}）")
    check(df.date.max() >= pd.Timestamp("2026-11-06"), f"最新 >= 2026-11-06（{df.date.max().date()}）")
    d = df[df.date == "2026-10-30"]
    rth = d[(d.time_et >= "09:30") & (d.time_et <= "15:59")]
    check(len(rth) >= 75, f"2026-10-30 正常時段（09:30–15:59）至少 75 根 5 分鐘線（{len(rth)}）")
    check(len(rth) > 0 and 360 < rth.iloc[0].open < 375, f"10/30 開盤價約 368（{rth.iloc[0].open if len(rth) else None}）")
    check((df.high >= df[["open", "close"]].max(axis=1) - 1e-6).all() and (df.low <= df[["open", "close"]].min(axis=1) + 1e-6).all(), "high/low 合理")
    y = pd.read_csv(os.path.join(HERE, "market-prices", "market_prices.csv"), parse_dates=["date"])
    y = y[y.ticker == "GLD"].set_index("date").close
    diffs = []
    for day, g in df[(df.time_et >= "09:30") & (df.time_et <= "15:59")].groupby("date"):
        if day in y.index:
            diffs.append(abs(g.iloc[-1].close / y[day] - 1))
    check(len(diffs) >= 5 and max(diffs) < 0.003, f"各日最後一根 close 與 Yahoo 日線收盤差異（日數 {len(diffs)}，最大 {max(diffs) if diffs else None}）")



def dealer_funding():
    spec = [("pd_financing.csv", "2018-01-31", "2026-10-14"), ("repo_haircuts.csv", "2022-12-31", "2026-06-30"),
            ("hedge_fund_leverage.csv", "2018-12-31", "2025-06-30")]
    for name, start, last in spec:
        df = load_csv("dealer-funding", name, ["date", "series_key", "description", "value", "unit"], ["date", "series_key"])
        if df is None:
            continue
        check(df.date.min() <= pd.Timestamp(start), f"{name} 起始 <= {start}（{df.date.min().date()}）")
        check(df.date.max() >= pd.Timestamp(last), f"{name} 最新 >= {last}（{df.date.max().date()}）")
        check(df.series_key.nunique() >= 2, f"{name} 至少 2 個系列（{df.series_key.nunique()}）")
        check(df.value.notna().mean() > 0.95, f"{name} value 非空比例 > 95%")
        print(f"info {name}: {len(df)} 列、系列 {df.series_key.nunique()} 個")
        print(df.groupby("series_key").agg(最新=("date", "max"), 值=("value", "last")).head(12).to_string())


TASKS = {"dealer-funding": dealer_funding, "tv-gld-1m": tv_gld_1m, "nyfed-srf": nyfed_srf, "fima-repo": fima_repo, "treasury-qra": treasury_qra, "treasury-ops": treasury_ops, "market-prices": market_prices, "fed-balance-sheet": fed_balance_sheet, "cftc-treasury": cftc_treasury}
name = sys.argv[1] if len(sys.argv) > 1 else ""
if name not in TASKS:
    sys.exit(f"用法：verify.py {'|'.join(TASKS)}")
TASKS[name]()
print(f"FAIL {name}: {len(errors)} 項" if errors else f"PASS {name}")
sys.exit(1 if errors else 0)
