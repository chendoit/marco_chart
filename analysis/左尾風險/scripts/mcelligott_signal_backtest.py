"""WN-2026-10-28 野村 McElligott 報告 §3/§2/§6/§8 訊號的本地資料回測。

用本地序列重算報告引述的野村回測，看結論在我們的資料上是否成立：
  A. 恐慌極值（Insight 2）：VVIX 單日 ≥ +24%、VVIX 相對 SPX 的超額單日漲幅 ≥ 99／99.9 百分位、VIX 單日 ≤ −20.4%
  B. skew 從極平變陡（Insight 1）：以 CBOE SKEW 指數為代理（gex／lieta 的 SPX skew 只有 2024-08 以後）
  C. 日圓套息平倉（Insight 5）：USDJPY 21 日變動 z 分數
  D. 日曆（Insight 7）：月度 OpEx 之後一週、各月份

執行（在 flask_highcharts 目錄下，route 用相對 import）：
    cd flask_highcharts && ../venv/Scripts/python.exe ../analysis/左尾風險/scripts/mcelligott_signal_backtest.py

方法：
- 前瞻報酬 = 事件日收盤到 +5／+21／+63 個交易日收盤的 SPX（series 2）報酬；基準 = 同期間所有日子。
- 事件去群聚：同一次事件 21 個交易日內的後續觸發不重複計（野村也是以「次」計）。
- 百分位一律用「到當日為止的 expanding 窗口」，不看未來。
"""
import os
import sys

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "flask_highcharts")))

import importlib  # noqa: E402

lt = importlib.import_module("app.routes.左尾風險監控")

FWD = {"+1w": 5, "+1m": 21, "+3m": 63}
GAP = 21


def S(sid):
    s = lt._series(sid)
    s.index = pd.DatetimeIndex(s.index).normalize()
    return s[~s.index.duplicated(keep="last")]


def decluster(mask, gap=GAP):
    """布林 Series → 去群聚後的事件日索引。"""
    out, last = [], -10**9
    for i, (d, v) in enumerate(mask.items()):
        if v and i - last > gap:
            out.append(d)
            last = i
    return pd.DatetimeIndex(out)


def fwd_table(spx, dates, label, base=None):
    """事件日 → 前瞻報酬中位數／平均／上漲機率；base 給基準列。"""
    fw = {k: spx.shift(-n) / spx - 1 for k, n in FWD.items()}
    rows = []
    for k, f in fw.items():
        x = f.reindex(dates).dropna()
        rows.append((k, len(x), x.median(), x.mean(), (x > 0).mean()))
    line = f"| {label} | {len(dates)} |"
    for k, n, med, mean, hit in rows:
        line += f" {med*100:+.1f}%／{hit*100:.0f}%（n={n}）|"
    return line


def header():
    return "| 訊號 | 事件數 | " + " | ".join(f"SPX {k} 中位數／上漲機率" for k in FWD) + " |\n|---|---|---|---|---|"


def expanding_pct(s, min_n=500):
    """到當日（含）為止的 expanding 百分位，樣本 < min_n 為 NaN。"""
    r = s.expanding(min_periods=min_n).apply(lambda a: (a[:-1] < a[-1]).mean() * 100 + 50 * (a[:-1] == a[-1]).mean(),
                                             raw=True)
    return r


def main():
    spx = S(2)
    vix, vvix = S("cboe_VIX"), S("cboe_VVIX")
    df = pd.concat({"spx": spx, "vix": vix, "vvix": vvix}, axis=1).dropna()
    df = df[df.index >= "2006-03-06"]
    spx = df["spx"]
    ret = spx.pct_change()
    print(f"# 回測區間 {df.index.min().date()} ~ {df.index.max().date()}，{len(df)} 個交易日\n")

    # 基準
    allday = pd.DatetimeIndex(df.index[:-FWD['+3m']])
    print("## 基準（所有交易日）\n")
    print(header())
    print(fwd_table(spx, allday, "全部日子"))

    # ---------------- A ----------------
    print("\n## A. 恐慌極值（野村 §3：1 個月後 SPX 更高、機率 76–100%）\n")
    print(header())
    vvix_d1 = vvix.reindex(df.index).pct_change()
    vix_d1 = df["vix"].pct_change()
    ev = {}
    ev["VVIX 單日 ≥ +24%"] = decluster(vvix_d1 >= 0.24)
    ev["VVIX 單日 ≥ +24%（不去群聚）"] = vvix_d1.index[vvix_d1 >= 0.24]
    # VVIX 相對 SPX 的超額單日漲幅：對 SPX 單日報酬回歸的殘差，再取 expanding 百分位
    x = pd.concat([vvix_d1, ret], axis=1, keys=["v", "r"]).dropna()
    beta = np.polyfit(x["r"], x["v"], 1)
    resid = x["v"] - np.polyval(beta, x["r"])
    rp = expanding_pct(resid)
    ev["VVIX 相對 SPX 超額 ≥ 99 百分位"] = decluster(rp >= 99)
    ev["VVIX 相對 SPX 超額 ≥ 99.5 百分位"] = decluster(rp >= 99.5)
    ev["VVIX 相對 SPX 超額 ≥ 99.9 百分位"] = decluster(rp >= 99.9)
    # VIX 對 SPX 超額
    x2 = pd.concat([vix_d1, ret], axis=1, keys=["v", "r"]).dropna()
    b2 = np.polyfit(x2["r"], x2["v"], 1)
    res2 = x2["v"] - np.polyval(b2, x2["r"])
    rp2 = expanding_pct(res2)
    ev["VIX 相對 SPX 超額 ≥ 99 百分位"] = decluster(rp2 >= 99)
    ev["VIX 單日 ≤ −20.4%（vol smash）"] = decluster(vix_d1 <= -0.204)
    ev["VIX 單日 ≥ +50%"] = decluster(vix_d1 >= 0.50)
    for k, d in ev.items():
        d = pd.DatetimeIndex([t for t in d if t in spx.index and spx.index.get_loc(t) + 63 < len(spx)])
        print(fwd_table(spx, d, k))
    print("\n事件日（VVIX ≥ +24% 去群聚）：",
          ", ".join(str(d.date()) for d in ev["VVIX 單日 ≥ +24%"]))
    print("事件日（VVIX 超額 ≥ 99.5 百分位）：",
          ", ".join(str(d.date()) for d in ev["VVIX 相對 SPX 超額 ≥ 99.5 百分位"]))

    # 2024 三個案例當天狀況
    print("\n2024 案例當日：")
    for d in ["2024-04-19", "2024-08-05", "2024-09-03"]:
        t = pd.Timestamp(d)
        if t in vvix_d1.index:
            print(f"- {d}：VVIX 單日 {vvix_d1[t]*100:+.1f}%、超額百分位 {rp.get(t, np.nan):.1f}、"
                  f"VIX 單日 {vix_d1[t]*100:+.1f}%、SPX 單日 {ret[t]*100:+.1f}%")

    # ---------------- B ----------------
    print("\n## B. skew 從極平變陡（野村 §2：+1w 中位 −1.7%、上漲機率 22%，n=10）\n")
    print("代理：CBOE SKEW 指數（90 天尾部風險定價，非 3M 25Δ skew；高 = 尾部貴）。"
          "gex／lieta 的 SPX skew 只有 2024-08 以後，不足以回測。\n")
    skew = S("cboe_SKEW").reindex(df.index).ffill()
    sp = skew.expanding(min_periods=500).apply(lambda a: (a[:-1] < a[-1]).mean() * 100, raw=True)
    print(header())
    for lo, hi, w in [(10, 25, 20), (5, 25, 20), (10, 25, 40), (10, 50, 20)]:
        low = sp.rolling(w).min()
        m = (low <= lo) & (sp >= hi) & (sp.shift(1) < hi)
        d = decluster(m)
        d = pd.DatetimeIndex([t for t in d if spx.index.get_loc(t) + 63 < len(spx)])
        print(fwd_table(spx, d, f"過去{w}日最低≤{lo}百分位 且 首次升破{hi}"))
    # 反向：skew 已高再創高
    print()
    print("對照：SKEW 指數 ≥ 90 百分位（尾部已貴）")
    d = decluster(sp >= 90)
    d = pd.DatetimeIndex([t for t in d if spx.index.get_loc(t) + 63 < len(spx)])
    print(header())
    print(fwd_table(spx, d, "SKEW ≥ 90 百分位"))

    # ---------------- C ----------------
    print("\n## C. 日圓套息平倉（野村 §6：8 月前 3–4 週先動）\n")
    jp = S("ccy_usdfx_jp")
    usdjpy = (1 / jp).reindex(df.index).ffill()
    chg = usdjpy.pct_change(21)
    z = (chg - chg.expanding(min_periods=500).mean()) / chg.expanding(min_periods=500).std()
    print(header())
    for thr in (-1.5, -2.0, -2.5):
        d = decluster(z <= thr)
        d = pd.DatetimeIndex([t for t in d if spx.index.get_loc(t) + 63 < len(spx)])
        print(fwd_table(spx, d, f"USDJPY 21日變動 z ≤ {thr}"))
    t = pd.Timestamp("2024-08-05")
    first = z[(z.index >= "2024-06-01") & (z.index <= t)]
    print(f"\n2024：z 首次 ≤ −1.5 = {first[first <= -1.5].index.min()}；8/5 當日 z = {z.get(t, np.nan):.2f}；"
          f"SPX 8/5 前 15 日內最大回撤起點 = {spx['2024-07-10':'2024-08-05'].idxmax().date()}")
    # 領先性：z ≤ -1.5 首次觸發 → 之後 21 日內 SPX 最大回撤 < −5% 的比例
    d = decluster(z <= -1.5)
    d = pd.DatetimeIndex([t for t in d if spx.index.get_loc(t) + 63 < len(spx)])
    dd = []
    for t in d:
        i = spx.index.get_loc(t)
        w = spx.iloc[i:i + 22]
        dd.append(w.min() / w.iloc[0] - 1)
    dd = pd.Series(dd, index=d)
    allw = [spx.iloc[i:i + 22].min() / spx.iloc[i] - 1 for i in range(len(spx) - 63)]
    print(f"事件後 21 日內最大回撤：中位 {dd.median()*100:.1f}%、< −5% 比例 {(dd < -0.05).mean()*100:.0f}%"
          f"（基準：中位 {np.median(allw)*100:.1f}%、< −5% 比例 {(np.array(allw) < -0.05).mean()*100:.0f}%）")

    # ---------------- D ----------------
    print("\n## D. 日曆（野村 §8）\n")
    full = S(2)
    full = full[full.index >= "1990-01-01"]
    r1 = full.pct_change()
    # 月度 OpEx = 每月第三個週五（若休市則前一交易日）
    opex = []
    for (y, m), g in full.groupby([full.index.year, full.index.month]):
        fr = [d for d in g.index if d.weekday() == 4]
        if len(fr) >= 3:
            opex.append(fr[2])
        elif len(g):
            pass
    opex = pd.DatetimeIndex(opex)
    pos = full.index.get_indexer(opex)
    wk = pd.Series({d: full.iloc[p + 5] / full.iloc[p] - 1 for d, p in zip(opex, pos) if p + 5 < len(full)})
    wk_all = (full.shift(-5) / full - 1).dropna()
    print(f"OpEx 後一週（OpEx 收盤→+5 交易日，1990 起，n={len(wk)}）：中位 {wk.median()*100:+.2f}%、"
          f"上漲機率 {(wk > 0).mean()*100:.0f}%｜全部 5 日窗口：中位 {wk_all.median()*100:+.2f}%、上漲 {(wk_all > 0).mean()*100:.0f}%")
    sept = wk[wk.index.month == 9]
    print(f"其中 9 月 OpEx 後一週（n={len(sept)}）：中位 {sept.median()*100:+.2f}%、上漲 {(sept > 0).mean()*100:.0f}%")
    # 日曆暴露：VIX 到期（OpEx 前的週三）後
    # 月份
    mret = full.resample("ME").last().pct_change().dropna()
    mret = mret[mret.index >= "1990-01-01"]
    g = mret.groupby(mret.index.month)
    print("\n各月 SPX 月報酬（1990 起）：\n\n| 月 | 中位數 | 上漲機率 | 平均 |\n|---|---|---|---|")
    for m, x in g:
        print(f"| {m} | {x.median()*100:+.2f}% | {(x > 0).mean()*100:.0f}% | {x.mean()*100:+.2f}% |")
    mret_long = S(2).resample("ME").last().pct_change().dropna()
    print(f"\n9 月全樣本（1928 起，n={(mret_long.index.month == 9).sum()}）："
          f"中位 {mret_long[mret_long.index.month == 9].median()*100:+.2f}%，"
          f"月份排名（中位數由低到高）= "
          f"{mret_long.groupby(mret_long.index.month).median().rank().get(9)} / 12")
    # 9 月前兩週
    first2 = []
    for y in range(1990, 2026):
        a = full[(full.index.year == y) & (full.index.month == 8)].iloc[-1]
        s9 = full[(full.index.year == y) & (full.index.month == 9)]
        first2.append(s9.iloc[min(9, len(s9) - 1)] / a - 1)
    print(f"9 月前兩週（8 月底→9 月第 10 個交易日，1990–2025，n={len(first2)}）：中位 {np.median(first2)*100:+.2f}%、"
          f"上漲 {np.mean(np.array(first2) > 0)*100:.0f}%")


if __name__ == "__main__":
    main()
