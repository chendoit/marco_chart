"""左尾風險 9 條判斷的 2024 案例重播（不是正式回測）。

用 flask_highcharts/app/routes/左尾風險監控.py 現行的門檻與序列 id，逐日回放三段 2024 行情：
每個交易日 D 只用「序列日期 ≤ D」的點，依 route 的規則判斷 ✅／⬜／❓，再依
WN-2026-10-28-左尾風險-9指標判斷邏輯與讀法 §0 合成 A／B／C／D 四站與站級結論；
另依 §7 #1、#2、#4 算修正版並列。SPX 後續報酬取 series_2 收盤 +5／+21／+63 個交易日。

執行（在 flask_highcharts 目錄下，route 用相對 import）：
    cd flask_highcharts && ../venv/Scripts/python.exe ../analysis/左尾風險/scripts/case_replay_2024.py [輸出目錄]

與 route 的差異（route 只判「各序列最後一點」，這裡改成判「≤ D 的最後一點」）：
- 缺資料：D 之前沒有任何點 → ❓（route：檔案不存在 → ❓）。
- 延遲：≤ D 的最後一點落後 D 超過容忍天數（FRED／lieta 落後組 1，其他 0）→ ❓，與 route 相同口徑。
- ② 的「前 20 日高點」在 gex 序列不足 21 個觀測前是 NaN；route 此時會退回整條序列最後一個高點（會看到未來），
  這裡改標 ❓。
- 百分位（VXN、MOVE）沿用 route 的 _rolling_pctl（252 觀測含當日、樣本 <126 為 NaN），只用到 D 以前的值。
"""
import os
import sys

import numpy as np
import pandas as pd

# Windows 主控台／重導向預設 cp950，印 ✅⬜❓ 會出錯
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FLASK_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "..", "flask_highcharts"))
sys.path.insert(0, FLASK_DIR)

import importlib  # noqa: E402

lt = importlib.import_module("app.routes.左尾風險監控")

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else (
    "C:/Users/chendoit/AppData/Local/Temp/claude/C--code-2025-12-05-MacroMicro-Data/"
    "71fc259d-06c0-470d-96e0-65846807f1f5/scratchpad/orca-sub/replay")

PERIODS = {
    "P1_2024-04_伊朗": ("2024-04-01", "2024-05-10"),
    "P2_2024-08_日圓套利": ("2024-07-10", "2024-09-15"),
    "P3_2024-11_選後融漲": ("2024-11-01", "2024-12-31"),
}
FWD = {"fwd_1w": 5, "fwd_1m": 21, "fwd_3m": 63}

# ---- 修正版門檻（WN §7）----
HY_WIDEN_FIX, CCC_WIDEN_FIX = 0.5, 1.5     # §7 #2 分開門檻
CREDIT_CHG_PCTL = 90                       # §7 #2 另一案：20 日變化的 1Y 百分位
EXCESS_DROP = -0.5                         # §7 #4 SMH−SPX、XLE−SPX 同日都 < −0.5%

OK, NO, UNK = lt.OK, lt.NO, lt.UNK


# ============================================================
# 序列（整條算好，逐日再切 ≤ D）
# ============================================================

def norm(s):
    """pkl 的時間戳有 08:00 與 00:00 兩種，一律對齊到日期（同日重複取最後一筆）。"""
    s = s.copy()
    s.index = pd.DatetimeIndex(s.index).normalize()
    return s[~s.index.duplicated(keep="last")]


def S(sid):
    try:
        return norm(lt._series(sid))
    except FileNotFoundError:
        return pd.Series(dtype=float)


def build():
    s = {}
    for sid in ("cboe_VXN", "cboe_VIX", "cboe_VVIX", "gex_spx_put_skew_1m", "lieta_spx_flip_dist_pct",
                "lieta_qqq_flip_dist_pct", 17581, "cboe_TNX", 2, 95001, 3612, 93001, "etf_SMH_close",
                "etf_XLE_close", "lieta_xsd_ivpct", "lieta_xop_ivpct", "lieta_vx1_vx2_spread",
                "lieta_vx1_vix_basis", "lieta_vx_contango_30d", "lieta_qqq_put_skew3m_pctl1y"):
        s[sid] = S(sid)
    for sid in ("lt_vxn_pctl1y", "lt_move_pctl1y", "lt_vvix_d1", "lt_putskew1m_prior_high20",
                "lt_hy_oas_chg20", "lt_ccc_spread_chg20", "lt_bbb_spread_chg20", "lt_smh_ret1d", "lt_xle_ret1d"):
        s[sid] = S(sid)
    # lt_qqq_spx_* 需要 lieta_qqq_p25_p50_1m；缺檔時 route 的衍生函式會丟 FileNotFoundError
    for sid in ("lt_qqq_spx_p25_p50_spread", "lt_qqq_spx_p25_p50_spread_pctl1y"):
        s[sid] = S(sid)
    s["gap"] = S(("cboe_VXN", "-", "cboe_VIX"))
    for w in (20, 60):
        s[f"corr{w}"] = S(f"2:ret~cboe_TNX.CORR{w}")
    s["spx_ret"] = s[2].pct_change() * 100
    s["hy_chg_pctl"] = lt._rolling_pctl(s["lt_hy_oas_chg20"].dropna())
    s["ccc_chg_pctl"] = lt._rolling_pctl(s["lt_ccc_spread_chg20"].dropna())
    return s


REF = None


def lag_td(last, D):
    """last 之後到 D（含）基準序列多幾個交易日。"""
    return int(((REF > last) & (REF <= D)).sum())


def asof(s, D, sid_for_tol):
    """回 (日期, 值) 或 None（缺）；第三個回傳值為是否延遲。"""
    sub = s[s.index <= D].dropna()
    if sub.empty:
        return None, None, False
    t = sub.index[-1]
    return t, float(sub.iloc[-1]), lag_td(t, D) > lt._lag_tol(sid_for_tol)


def check(D, items, s):
    """items: [(label, key_in_s, tol_sid)] → (missing, delayed, {label:(t,v)})。"""
    missing, delayed, vals = [], [], {}
    for label, key, tol_sid in items:
        t, v, late = asof(s[key], D, tol_sid)
        if t is None or v is None or np.isnan(v):
            missing.append(label)
            continue
        vals[label] = (t, v)
        if late:
            delayed.append(label)
    return missing, delayed, vals


def status(missing, delayed, triggered):
    if missing or delayed:
        return UNK
    return OK if triggered else NO


# ============================================================
# 逐日判斷
# ============================================================

def day_row(D, s):
    r = {"date": D.strftime("%Y-%m-%d")}

    # ① VXN−VIX > 7 且 VXN 1Y 百分位 > 85
    m, dl, v = check(D, [("gap", "gap", "cboe_VXN"), ("pct", "lt_vxn_pctl1y", "cboe_VXN"),
                         ("VXN", "cboe_VXN", "cboe_VXN"), ("VIX", "cboe_VIX", "cboe_VIX")], s)
    trig = (not m) and v["gap"][1] > lt.VXN_VIX_GAP and v["pct"][1] > lt.VXN_PCTL
    r["c1"] = status(m, dl, trig)
    r["vxn_vix_gap"] = v.get("gap", (None, np.nan))[1]
    r["vxn_pctl"] = v.get("pct", (None, np.nan))[1]

    # ② VVIX 單日 ≥ +10 或 SPX 1M put skew 創 20 日新高
    m, dl, v = check(D, [("d1", "lt_vvix_d1", "cboe_VVIX"), ("sk", "gex_spx_put_skew_1m", "gex_spx_put_skew_1m")], s)
    vvix_leg = v["d1"][1] >= lt.VVIX_JUMP if "d1" in v else None
    r["vvix_d1"] = v.get("d1", (None, np.nan))[1]
    hv = np.nan
    if "sk" in v:
        hi = s["lt_putskew1m_prior_high20"]
        st = v["sk"][0]
        hv = float(hi.loc[st]) if st in hi.index and not np.isnan(hi.loc[st]) else np.nan
        if np.isnan(hv):
            m = m + ["前20日高點(樣本不足)"]
    r["putskew1m"] = v.get("sk", (None, np.nan))[1]
    r["putskew1m_prior_high20"] = hv
    trig = (not m) and (vvix_leg or v["sk"][1] > hv)
    r["c2"] = status(m, dl, trig)
    r["c2_vvix_leg"] = "" if vvix_leg is None else (OK if vvix_leg else NO)

    # ③ SPX、QQQ 都跌破 gamma flip
    m, dl, v = check(D, [("sp", "lieta_spx_flip_dist_pct", "lieta_spx_flip_dist_pct"),
                         ("qq", "lieta_qqq_flip_dist_pct", "lieta_qqq_flip_dist_pct")], s)
    r["c3"] = status(m, dl, (not m) and v["sp"][1] < 0 and v["qq"][1] < 0)

    # ④ MOVE 1Y 百分位 > 90
    m, dl, v = check(D, [("pct", "lt_move_pctl1y", 17581), ("MOVE", 17581, 17581)], s)
    r["c4"] = status(m, dl, (not m) and v["pct"][1] > lt.MOVE_PCTL)
    r["move"] = v.get("MOVE", (None, np.nan))[1]
    r["move_pctl"] = v.get("pct", (None, np.nan))[1]

    # ⑤ corr(SPX 報酬, ΔTNX) 20 日 > 0
    m, dl, v = check(D, [("c20", "corr20", 2), ("c60", "corr60", 2), ("SPX", 2, 2), ("TNX", "cboe_TNX", "cboe_TNX")], s)
    r["c5"] = status(m, dl, (not m) and v["c20"][1] > 0)
    r["corr20"] = v.get("c20", (None, np.nan))[1]
    r["corr60"] = v.get("c60", (None, np.nan))[1]
    r["c5_fix"] = status(m, dl, (not m) and v["c60"][1] <= 0 and v["c20"][1] > 0)   # §7 #1

    # ⑥ HY 或 CCC 20 日擴大 > 1pp
    m, dl, v = check(D, [("hy", "lt_hy_oas_chg20", 95001), ("ccc", "lt_ccc_spread_chg20", 3612),
                         ("bbb", "lt_bbb_spread_chg20", 93001)], s)
    m = [x for x in m if x != "bbb"]
    dl = [x for x in dl if x != "bbb"]
    hy, ccc = v.get("hy", (None, np.nan))[1], v.get("ccc", (None, np.nan))[1]
    r["hy_chg20"], r["ccc_chg20"], r["bbb_chg20"] = hy, ccc, v.get("bbb", (None, np.nan))[1]
    r["c6"] = status(m, dl, (not m) and (hy > lt.CREDIT_WIDEN or ccc > lt.CREDIT_WIDEN))
    r["c6_fix"] = status(m, dl, (not m) and (hy > HY_WIDEN_FIX or ccc > CCC_WIDEN_FIX))   # §7 #2 分開門檻
    m2, dl2, v2 = check(D, [("hp", "hy_chg_pctl", 95001), ("cp", "ccc_chg_pctl", 3612)], s)
    r["hy_chg_pctl"] = v2.get("hp", (None, np.nan))[1]
    r["ccc_chg_pctl"] = v2.get("cp", (None, np.nan))[1]
    r["c6_fix_pctl"] = status(m2, dl2, (not m2) and (v2["hp"][1] > CREDIT_CHG_PCTL or v2["cp"][1] > CREDIT_CHG_PCTL))

    # ⑦ SMH、XLE 同日 < −1.5%（route：取兩者 inner join 的最後一天）
    m, dl, v = check(D, [("SMH", "etf_SMH_close", "etf_SMH_close"), ("XLE", "etf_XLE_close", "etf_XLE_close"),
                         ("smh", "lt_smh_ret1d", "etf_SMH_close"), ("xle", "lt_xle_ret1d", "etf_XLE_close"),
                         ("spx", "spx_ret", 2)], s)
    smh, xle, spx = (v.get(k, (None, np.nan))[1] for k in ("smh", "xle", "spx"))
    r["smh_ret"], r["xle_ret"], r["spx_ret"] = smh, xle, spx
    base_m = [x for x in m if x != "spx"]
    base_dl = [x for x in dl if x != "spx"]
    r["c7"] = status(base_m, base_dl, (not base_m) and smh < lt.BARBELL_DROP and xle < lt.BARBELL_DROP)
    r["c7_fix"] = status(m, dl, (not m) and (smh - spx) < EXCESS_DROP and (xle - spx) < EXCESS_DROP)   # §7 #4
    ma, dla, va = check(D, [("xsd", "lieta_xsd_ivpct", "lieta_xsd_ivpct"), ("xop", "lieta_xop_ivpct", "lieta_xop_ivpct")], s)
    r["c7_aux"] = status(ma, dla, (not ma) and va["xsd"][1] > lt.BARBELL_IV_PCTL and va["xop"][1] > lt.BARBELL_IV_PCTL)

    # ⑧ VX1−VX2 > 0 或 VX1−VIX < 0
    m, dl, v = check(D, [("sp", "lieta_vx1_vx2_spread", "lieta_vx1_vx2_spread"),
                         ("bs", "lieta_vx1_vix_basis", "lieta_vx1_vix_basis"),
                         ("ct", "lieta_vx_contango_30d", "lieta_vx_contango_30d")], s)
    r["c8"] = status(m, dl, (not m) and (v["sp"][1] > 0 or v["bs"][1] < 0))

    # ⑨ QQQ−SPX p25/p50 差的 1Y 百分位 > 85 且 QQQ 3M put skew 1Y 百分位 > 85
    m, dl, v = check(D, [("sp", "lt_qqq_spx_p25_p50_spread", "lt_qqq_spx_p25_p50_spread"),
                         ("pc", "lt_qqq_spx_p25_p50_spread_pctl1y", "lt_qqq_spx_p25_p50_spread_pctl1y"),
                         ("pk", "lieta_qqq_put_skew3m_pctl1y", "lieta_qqq_put_skew3m_pctl1y")], s)
    r["c9"] = status(m, dl, (not m) and v["pc"][1] > lt.SPREAD_PCTL and v["pk"][1] > lt.QQQ_SKEW_PCTL)

    # ---- 站 ----
    a = [r[f"c{i}"] for i in (1, 2, 3, 8, 9)]
    r["n_ok"] = sum(r[f"c{i}"] == OK for i in range(1, 10))
    r["n_unk"] = sum(r[f"c{i}"] == UNK for i in range(1, 10))
    r["A_ok"], r["A_unk"] = a.count(OK), a.count(UNK)
    r["A"] = station_a(a)
    r["B"] = station_any([r["c4"], r["c5"]])
    r["C"] = station_any([r["c6"]])
    r["D"] = station_any([r["c7"]])
    r["結論"] = verdict(r["A"], r["B"], r["C"], r["D"])
    r["B_fix"] = station_any([r["c4"], r["c5_fix"]])
    r["C_fix"] = station_any([r["c6_fix"]])
    r["D_fix"] = station_any([r["c7_fix"]])
    r["結論_fix"] = verdict(r["A"], r["B_fix"], r["C_fix"], r["D_fix"])
    return r


def station_a(a):
    """§0：5 條中 ≥3 ✅ 亮；✅+❓ <3 一定不亮；其他不確定。"""
    if a.count(OK) >= 3:
        return OK
    if a.count(OK) + a.count(UNK) < 3:
        return NO
    return UNK


def station_any(xs):
    if OK in xs:
        return OK
    if UNK in xs:
        return UNK
    return NO


def verdict(A, B, C, D):
    """只有 A／A+B／A+B+C；A 不確定或未亮時照實寫出 B/C/D 的狀態。"""
    if A == OK:
        lvl = "A+B+C" if (B == OK and C == OK) else ("A+B" if B == OK else "只有A")
    elif A == UNK:
        lvl = "A不確定"
    else:
        lvl = "A未亮"
    return f"{lvl}｜B{B} C{C} D{D}"


def sensitivity(all_days):
    """單一門檻上下移動時，各段觸發天數與日期（輸入值已在逐日表；狀態為 ❓ 的日子不計）。"""
    d = pd.concat(all_days, ignore_index=True)
    ok = {i: d[f"c{i}"] != UNK for i in range(1, 10)}
    rules = []
    for g in (7, 6, 5, 4):
        rules.append((f"① VXN−VIX >{g} 且 VXN 百分位 >{lt.VXN_PCTL}", ok[1] & (d.vxn_vix_gap > g) & (d.vxn_pctl > lt.VXN_PCTL)))
    for p in (80, 75):
        rules.append((f"① VXN−VIX >{lt.VXN_VIX_GAP} 且 VXN 百分位 >{p}", ok[1] & (d.vxn_vix_gap > lt.VXN_VIX_GAP) & (d.vxn_pctl > p)))
    rules.append(("② 只看 VVIX 單日 ≥+10（skew 腿缺時的 OR 下限）", d.vvix_d1 >= lt.VVIX_JUMP))
    for p in (90, 85, 80):
        rules.append((f"④ MOVE 百分位 >{p}", ok[4] & (d.move_pctl > p)))
    rules.append(("⑤ 原版 CORR20 >0", ok[5] & (d.corr20 > 0)))
    rules.append(("⑤ §7#1 CORR60 ≤0 且 CORR20 >0", ok[5] & (d.corr60 <= 0) & (d.corr20 > 0)))
    rules.append(("⑤ §7#1 替代 CORR20−CORR60 >0.3", ok[5] & (d.corr20 - d.corr60 > 0.3)))
    for hy, ccc in ((1.0, 1.0), (0.5, 1.5), (0.5, 1.0), (0.4, 1.0)):
        rules.append((f"⑥ HY >{hy} 或 CCC >{ccc}", ok[6] & ((d.hy_chg20 > hy) | (d.ccc_chg20 > ccc))))
    rules.append((f"⑥ §7#2 百分位 HY 或 CCC 20 日變化 1Y 百分位 >{CREDIT_CHG_PCTL}", d.c6_fix_pctl == OK))
    for x in (-1.5, -1.0, -2.0):
        rules.append((f"⑦ SMH、XLE 同日 <{x}%", ok[7] & (d.smh_ret < x) & (d.xle_ret < x)))
    for x in (-0.5, -1.0):
        rules.append((f"⑦ §7#4 SMH−SPX、XLE−SPX 同日 <{x}%", ok[7] & (d.smh_ret - d.spx_ret < x) & (d.xle_ret - d.spx_ret < x)))
    out = []
    for name, mask in rules:
        row = {"rule": name}
        for p in PERIODS:
            hit = d[mask.fillna(False) & (d.period == p)]
            row[p] = f"{len(hit)}：" + ",".join(x[5:] for x in hit.date)
        out.append(row)
    return pd.DataFrame(out)


def main():
    global REF
    os.makedirs(OUT_DIR, exist_ok=True)
    s = build()
    REF = pd.DatetimeIndex(lt._ref_index()).normalize().unique()
    spx = s[2]
    spx_idx = list(spx.index)

    # 資料可得性
    inv = []
    for key in ("cboe_VXN", "cboe_VIX", "cboe_VVIX", "gex_spx_put_skew_1m", "lt_putskew1m_prior_high20",
                "lieta_spx_flip_dist_pct", "lieta_qqq_flip_dist_pct", 17581, "lt_move_pctl1y", "cboe_TNX",
                "corr20", "corr60", 95001, "lt_hy_oas_chg20", "hy_chg_pctl", 3612, "ccc_chg_pctl", "etf_SMH_close",
                "etf_XLE_close", "lieta_xsd_ivpct", "lieta_xop_ivpct", "lieta_vx1_vx2_spread", "lieta_vx1_vix_basis",
                "lieta_vx_contango_30d", "lt_qqq_spx_p25_p50_spread", "lt_qqq_spx_p25_p50_spread_pctl1y",
                "lieta_qqq_put_skew3m_pctl1y", "lt_vxn_pctl1y"):
        x = s[key].dropna()
        inv.append({"series": key, "first": x.index[0].strftime("%Y-%m-%d") if len(x) else "",
                    "last": x.index[-1].strftime("%Y-%m-%d") if len(x) else "",
                    **{p: int(((x.index >= a) & (x.index <= b)).sum()) for p, (a, b) in PERIODS.items()}})
    pd.DataFrame(inv).to_csv(os.path.join(OUT_DIR, "availability.csv"), index=False, encoding="utf-8-sig")

    summary, all_days = [], []
    for name, (a, b) in PERIODS.items():
        days = [t for t in spx_idx if pd.Timestamp(a) <= t <= pd.Timestamp(b)]
        rows = []
        for D in days:
            r = day_row(D, s)
            i = spx_idx.index(D)
            r["spx"] = float(spx.iloc[i])
            for k, n in FWD.items():
                r[k] = (float(spx.iloc[i + n]) / r["spx"] - 1) * 100 if i + n < len(spx_idx) else np.nan
            r["fwd_1m_maxdd"] = (float(spx.iloc[i + 1:i + 22].min()) / r["spx"] - 1) * 100
            rows.append(r)
        df = pd.DataFrame(rows)
        df["period"] = name
        all_days.append(df)
        df.to_csv(os.path.join(OUT_DIR, f"replay_{name}.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
        sm = {"period": name, "days": len(df)}
        for c in [f"c{i}" for i in range(1, 10)] + ["c5_fix", "c6_fix", "c6_fix_pctl", "c7_fix", "c7_aux",
                                                     "A", "B", "C", "D", "B_fix", "C_fix", "D_fix"]:
            vc = df[c].value_counts()
            sm[c] = f"{OK}{vc.get(OK, 0)}/{NO}{vc.get(NO, 0)}/{UNK}{vc.get(UNK, 0)}"
        summary.append(sm)
        print(f"\n===== {name} {a}~{b}（{len(df)} 交易日）=====")
        cols = ["date", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "結論", "c5_fix", "c6_fix", "c7_fix",
                "結論_fix", "spx_ret", "fwd_1w", "fwd_1m", "fwd_3m"]
        with pd.option_context("display.width", 250, "display.max_columns", 40, "display.max_rows", 200):
            print(df[cols].to_string(index=False, float_format=lambda x: f"{x:+.2f}"))
    sens = sensitivity(all_days)
    sens.to_csv(os.path.join(OUT_DIR, "sensitivity.csv"), index=False, encoding="utf-8-sig")
    print("\n===== 門檻敏感度（只動單一門檻；❓ 日不計）=====")
    with pd.option_context("display.width", 300, "display.max_colwidth", 200, "display.max_rows", 200):
        print(sens.to_string(index=False))
    sm = pd.DataFrame(summary)
    sm.to_csv(os.path.join(OUT_DIR, "summary_counts.csv"), index=False, encoding="utf-8-sig")
    print("\n===== 各段 ✅/⬜/❓ 天數 =====")
    print(sm.T.to_string())
    print(f"\nCSV 輸出：{OUT_DIR}")


if __name__ == "__main__":
    main()
