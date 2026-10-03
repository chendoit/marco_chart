# -*- coding: utf-8 -*-
"""冬季取暖季極端路徑案例：用 data/*.csv 驗證付鵬傳導鏈的每一環（輸出純文字，給 WN 筆記引用）

先跑 fetch_data.py。熱值與排放係數：
- ULSD/取暖油 0.1374 MMBtu/gal（EIA 熱值表 137,381 Btu/gal）→ $/gal × 7.28 = $/MMBtu
- 1 MWh = 3.412 MMBtu → TTF(EUR/MWh) × EURUSD / 3.412 = $/MMBtu
- IPCC 預設排放：天然氣 56.1、柴油 74.1 tCO2/TJ；1 MMBtu = 1.055 GJ
"""
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent.parent / "data"
w = pd.read_csv(D / "eia_weekly.csv", index_col=0, parse_dates=True)
ed = pd.read_csv(D / "eia_daily.csv", index_col=0, parse_dates=True)
y = pd.read_csv(D / "yahoo_daily.csv", index_col=0, parse_dates=True)

HO_MMBTU = 1 / 0.137381           # gal per MMBtu
MWH = 3.412
EUA = 85.0                         # EUR/t，2026-09 上旬 ICE Dec26（gmk.center）
CO2_GAP = (74.1 - 56.1) * 1.055e-3  # t CO2/MMBtu，柴油比天然氣多排的量


def pct_rank(s, v):
    return (s.dropna() < v).mean() * 100


def seasonal(col, years=range(2021, 2026), frame=w):
    """同一週次（ISO week）在過去 5 年的 min/avg/max，與全歷史同週百分位。"""
    s = frame[col].dropna()
    last_d, last_v = s.index[-1], s.iloc[-1]
    wk = last_d.isocalendar().week
    same = s[s.index.isocalendar().week == wk]
    five = same[same.index.year.isin(list(years))]
    return last_d.date(), last_v, five.min(), five.mean(), five.max(), pct_rank(same, last_v), same.index.year.min()


print("=" * 80, "\n§A 最新週資料 vs 同週次 5 年（2021–2025）區間與全歷史百分位\n")
for col in ["dist_stk_padd1", "dist_stk_padd1a", "dist_stk_padd1b", "dist_stk_padd1c",
            "dist_stk_padd3", "dist_stk_us", "util_us", "util_padd1", "util_padd3",
            "dist_exp_us", "dist_imp_padd1", "dist_supplied_us", "ng_storage_l48_bcf"]:
    d, v, mn, av, mx, pr, y0 = seasonal(col)
    print(f"{col:20s} {d} {v:>9.1f} | 5y min {mn:>8.1f} avg {av:>8.1f} max {mx:>8.1f} | 自{y0}同週百分位 {pr:5.1f}%")

# 4 週平均較穩：出口、PADD1 進口
for col in ["dist_exp_us", "dist_imp_padd1", "util_us"]:
    s = w[col].dropna().rolling(4).mean()
    print(f"{col:20s} 4 週均 {s.iloc[-1]:.1f}（去年同期 {s[s.index <= s.index[-1] - pd.Timedelta(days=364)].iloc[-1]:.1f}）")

print("\n" + "=" * 80, "\n§B 價格快照與換算（$/MMBtu）\n")
last = y.ffill().iloc[-1]
ttf_usd = last.ttf * last.eurusd / MWH
ho_usd = last.ho * HO_MMBTU
print(f"日期 {y.index[-1].date()}  TTF {last.ttf:.2f} EUR/MWh × EURUSD {last.eurusd:.4f} = {ttf_usd:.2f} $/MMBtu")
print(f"HH(NG=F) {last.ng:.3f} → TTF−HH {ttf_usd - last.ng:.2f} $/MMBtu")
print(f"HO {last.ho:.4f} $/gal = {ho_usd:.2f} $/MMBtu；HO/TTF 能量比 {ho_usd / ttf_usd:.2f}")
print(f"CL {last.cl:.2f}  BZ {last.bz:.2f}  HO×42−BZ = {last.ho * 42 - last.bz:.2f} $/bbl（期貨裂解）")
carbon = CO2_GAP * EUA * last.eurusd
# 改燒油的條件：HO + 油的碳成本 < TTF + 氣的碳成本 → TTF > HO + 碳成本差，所以碳價是「提高」門檻
be_ets = (ho_usd + carbon) * MWH / last.eurusd
be_non = ho_usd * MWH / last.eurusd
print(f"氣改油平價：柴油每 MMBtu 多排 {CO2_GAP:.4f} t CO2 × EUA €{EUA} = +{carbon:.2f} $/MMBtu")
print(f"  → 受 EU ETS 管制的工業：TTF 需 ≥ {be_ets:.0f} EUR/MWh；不在 ETS 內（住宅/小型鍋爐）：≥ {be_non:.0f} EUR/MWh")
print(f"  （未計設備效率與切換成本；EUA 每 +€10 門檻提高 {CO2_GAP * 10 * MWH:.2f} EUR/MWh）")

print("\n歷史上 TTF(能量當量) 高於 HO 的日子：")
z = y[["ttf", "ho", "eurusd"]].dropna()
ratio = (z.ho * HO_MMBTU) / (z.ttf * z.eurusd / MWH)
above = ratio[ratio < 1]
print(f"  共 {len(above)} 天；區間 {above.index.min().date()} ～ {above.index.max().date()}")
for yr, g in above.groupby(above.index.year):
    print(f"   {yr}: {len(g)} 天，最低比值 {g.min():.2f}（{g.idxmin().date()}）")
r26 = ratio["2026"]
print(f"  2026 年 HO/TTF 比值：最低 {r26.min():.2f}（{r26.idxmin().date()}），最新 {ratio.iloc[-1]:.2f}")

print("\n" + "=" * 80, "\n§C 現貨：Colonial 套利（NYH−USGC ULSD）與柴油裂解\n")
e = ed.dropna(subset=["ulsd_nyh", "ulsd_usgc"])
spr = (e.ulsd_nyh - e.ulsd_usgc) * 100
print(f"NYH−USGC 最新 {spr.index[-1].date()} {spr.iloc[-1]:.1f} ¢/gal；近 60 日均 {spr.iloc[-60:].mean():.1f}；2006 起中位數 {spr.median():.1f}，95 分位 {spr.quantile(.95):.1f}")
crack = e.ulsd_nyh * 42 - ed.brent.reindex(e.index)
print(f"NYH ULSD − Dated Brent 最新 {crack.dropna().iloc[-1]:.2f} $/bbl；2026 年最高 {crack['2026'].max():.2f}（{crack['2026'].idxmax().date()}）；2022 年最高 {crack['2022'].max():.2f}")
bw = (ed.brent - ed.wti).dropna()
print(f"Dated Brent − WTI 現貨 最新 {bw.iloc[-1]:.2f} $/bbl")

print("\n" + "=" * 80, "\n§D PADD 1 餾分油：冬季去庫推演（9 月第 3 週 → 次年 2 月底/3 月初的最低點）\n")
s = w.dist_stk_padd1.dropna()
rows = []
for yr in range(2004, 2026):
    try:
        start = s[(s.index >= f"{yr}-09-12") & (s.index <= f"{yr}-09-24")].iloc[0]
        trough = s[f"{yr}-10-01":f"{yr + 1}-03-31"]
        rows.append((yr, start, trough.min(), trough.idxmin().date(), trough.min() - start))
    except IndexError:
        pass
t = pd.DataFrame(rows, columns=["winter", "sep", "trough", "trough_date", "chg"]).set_index("winter")
print(t.to_string())
cur = s.iloc[-1]
print(f"\n目前 {s.index[-1].date()} PADD1 {cur:,.0f} kbbl")
for q, lab in [(0.5, "中位數冬季"), (0.1, "偏冷 10 分位"), (0.0, "最劇烈")]:
    chg = t.chg.quantile(q)
    print(f"  套用{lab}變化 {chg:+,.0f} → 谷底 {cur + chg:,.0f} kbbl")
print(f"  1990 年以來 PADD1 週資料最低 {s.min():,.0f}（{s.idxmin().date()}）")

print("\n" + "=" * 80, "\n§E 冬季（12–2 月）美國煉廠開工率分布\n")
u = w.util_us.dropna()
wu = u[u.index.month.isin([12, 1, 2])]
print(f"2010 起冬季週資料：均值 {wu['2010':].mean():.1f}%、90 分位 {wu['2010':].quantile(.9):.1f}%、最高 {wu['2010':].max():.1f}%（{wu['2010':].idxmax().date()}）")
for yr in range(2021, 2027):
    g = wu[(wu.index >= f"{yr - 1}-12-01") & (wu.index < f"{yr}-03-01")]
    if len(g):
        print(f"  {yr - 1}/{str(yr)[-2:]} 冬季均 {g.mean():.1f}%  最低 {g.min():.1f}%（{g.idxmin().date()}）")

print("\n" + "=" * 80, "\n§F 事件研究：寒流前後（t−10 → t+10 交易日）價格變化\n")
EVENTS = {
    "2018-01 Bomb cyclone（美東）": "2018-01-02",
    "2018-03 Beast from the East（歐洲）": "2018-02-26",
    "2021-02 Uri（美南）": "2021-02-12",
    "2022-12 Elliott（美東）": "2022-12-22",
    "2025-01 美東寒流": "2025-01-20",
    "2026-01 Fern（美東/全美）": "2026-01-23",
}
z = y.join(ed[["henry_hub", "ulsd_nyh", "ulsd_usgc", "brent"]], how="outer").ffill()
for name, dt in EVENTS.items():
    i = z.index.searchsorted(pd.Timestamp(dt))
    a, b = z.iloc[max(i - 10, 0)], z.iloc[min(i + 10, len(z) - 1)]
    hh_max = z.henry_hub.iloc[i - 5:i + 10].max()
    crack_a = a.ulsd_nyh * 42 - a.brent
    crack_b = b.ulsd_nyh * 42 - b.brent
    sp_a = (a.ulsd_nyh - a.ulsd_usgc) * 100
    sp_b = (b.ulsd_nyh - b.ulsd_usgc) * 100
    print(f"{name}\n   TTF {a.ttf:6.1f}→{b.ttf:6.1f}  HH現貨峰值 {hh_max:6.2f}  NG=F {a.ng:5.2f}→{b.ng:5.2f}  "
          f"HO {a.ho:5.3f}→{b.ho:5.3f}  NYH裂解 {crack_a:5.1f}→{crack_b:5.1f}  NYH−USGC {sp_a:5.1f}→{sp_b:5.1f}¢  WTI {a.cl:5.1f}→{b.cl:5.1f}")

print("\n" + "=" * 80, "\n§G 傳導強度：TTF 週變動 vs 柴油裂解週變動（11–3 月）\n")
wk = z[["ttf", "eurusd", "ulsd_nyh", "brent", "ho", "cl", "ng"]].resample("W-FRI").last().dropna()
wk["ttf_usd"] = wk.ttf * wk.eurusd / MWH
wk["crack"] = wk.ulsd_nyh * 42 - wk.brent
wk["ho_cl"] = wk.ho * 42 - wk.cl
dd = wk.diff().dropna()
winter = dd[dd.index.month.isin([11, 12, 1, 2, 3])]
for lab, g in [("2017–2020", winter["2017":"2020"]), ("2021–2023", winter["2021":"2023"]),
               ("2024–2026", winter["2024":])]:
    print(f"{lab}: corr(ΔTTF, ΔNYH裂解) = {g.ttf_usd.corr(g.crack):+.2f}   corr(ΔTTF, ΔHO−CL) = {g.ttf_usd.corr(g.ho_cl):+.2f}   "
          f"corr(ΔHO−CL, ΔWTI) = {g.ho_cl.corr(g.cl):+.2f}   n={len(g)}")
