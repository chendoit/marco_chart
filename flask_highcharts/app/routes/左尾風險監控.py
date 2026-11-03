"""左尾風險監控：盤點 WN §4 確認清單 7 條 + 實作 WN §3.2 的修改（第 3、7 條）與新增（第 8、9 條）。
第 7 條分「主條件（SMH、XLE 同日 < −1.5%）」與「輔助條件（XSD、XOP IV 百分位都 > 0.8）」，兩者分開顯示。

資料來源：lieta_*（get_lieta_eod_series.py）、complacency_*（get_complacency_series.py）與既有 pkl。
需要的衍生值（百分位、單日變動、20 日變化、報酬）在本檔現算，以 `lt_` 為前綴的序列 id 注入
highcharts_utils 的 series cache（不落地 pkl；cache 被清掉後下次請求會重新注入）。
每張圖的 subtitle 顯示各序列自己的 as-of 日期，總覽（第一張）列 9 條狀態與各自 as-of。
"""
import json
import os
import re

import numpy as np
import pandas as pd

from app.utils import ChartModule, highcharts_utils as _hu, load_series_data, process_expression

# ---- 閾值（盤點 WN §4、實作 WN §3.2）----
VXN_VIX_GAP = 7             # ① VXN−VIX
VXN_PCTL = 85               # ① VXN 1Y 百分位
VVIX_JUMP = 10              # ② VVIX 單日變動（點）
NEW_HIGH_DAYS = 20          # ② put skew 創 N 日新高
MOVE_PCTL = 90              # ④ MOVE 1Y 百分位
CREDIT_WIDEN = 1.0          # ⑥ HY / CCC 利差 20 日擴大（百分點）
BARBELL_DROP = -1.5         # ⑦ SMH、XLE 單日報酬（%）
BARBELL_IV_PCTL = 0.8       # ⑦ 輔助：XSD、XOP IV 百分位（lieta 原值 0–1）都須 > 此值
DEEP_OTM_PCT = 10           # flow：深價外 put 的 OTM %（與 fetcher 的 is_deep_otm_put 一致）
FLOW_TREND_DAYS = 120       # flow 趨勢圖顯示最近幾個 query_date
QQQ_SKEW_PCTL = 85          # ⑨ QQQ 3M put skew 1Y 百分位
SPREAD_PCTL = 85            # ⑨ (QQQ − SPX) p25/p50 差的 1Y 百分位
CONTANGO_FALSIFY = 5        # ⑧ 證偽：contango 回到 > 5%
PCTL_WINDOW, PCTL_MIN = 252, 126
VIX_OVERLAY = "cboe_VIX"   # 每張圖疊加的 VIX

# 延遲判斷：基準 = 最近一個已收盤的交易日。本 repo 沒有 NYSE 日曆工具，改用 series_2（SPX 收盤）與
# cboe_VIX 兩者中較新的最後日期；兩者都停更時偵測不到（已知限制）。
# 容忍天數分兩組：lieta 的 screener／vx／iv_rv／hist_skew（列日期 D = D 前一交易日收盤）與 FRED
# 結構性落後 1 個交易日（WN §5-7）；其他序列（含 lieta term，其 EOD 暫定點 = 當日）= 0。
# Phase 3：L6 sector_vol（xsd／xop 的 iv、ivpct，as-of = 回應 date 前一交易日）屬 lieta 前一日收盤組，容忍 1；
# L7 dsi 與 L8 flow（query_date 當日成交）= 當日，容忍 0。
LAG_TOL_LAGGED = 1
LAG_TOL_DEFAULT = 0
FRED_IDS = {95001, 3612, 93001}
_LIETA_LAGGED = re.compile(
    r"^lieta_(vx1|vx2|vx1_vx2_spread|vx1_vix_basis|vx_contango_30d|"
    r"[a-z]+_(spot|flip_dist_pct|regime|protection_cost_1m|iv1m|rv1m|vrp|"
    r"put_skew3m|skew3m|put_skew3m_pctl1y|iv|ivpct))$")
_LT_LAGGED = {"lt_hy_oas_chg20", "lt_ccc_spread_chg20", "lt_bbb_spread_chg20"}
_TERM_SID = re.compile(r"^lieta_([a-z]+)_(p25_p50_1m|p25_atm_1m|p25_atm_1m_bucket|term_slope)$")
_TERM_DERIVED = {"lt_qqq_spx_p25_p50_spread": ("QQQ", "SPX"),
                 "lt_qqq_spx_p25_p50_spread_pctl1y": ("QQQ", "SPX")}

# gex_* 序列的日期是 lieta 原始 date，資料日 = 序列日期 − 1 交易日（合約補充 #3 第 5 點）
GEX_PREFIX = "gex_"

DATA_DIR = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")
TERM_META = "lieta_term_meta.json"   # get_lieta_eod_series.py 寫的 EOD 暫定 sidecar
FLOW_META = "lieta_flow_top.json"    # get_lieta_eod_series.py 寫的 flow 最新 query_date 前 20 大表


# ============================================================
# 衍生序列（現算，注入 series cache）
# ============================================================

def _raw(sid):
    d = load_series_data(sid)
    s = pd.Series({pd.Timestamp(t): float(v) for t, v in d["data"]
                   if v is not None and not pd.isna(v)})
    return s.sort_index()


def _rolling_pctl(s, window=PCTL_WINDOW, min_points=PCTL_MIN):
    """過去 window 個觀測（含當日）內 ≤ 當日值的比例 ×100；樣本 < min_points 為 NaN
    （同 get_lieta_eod_series._rolling_pctl 的定義）。"""
    vals = s.values
    out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        w = vals[max(0, i - window + 1):i + 1]
        if len(w) >= min_points:
            out[i] = (w <= vals[i]).mean() * 100
    return pd.Series(out, index=s.index)


def _ret_pct(sid):
    return _raw(sid).pct_change() * 100


def _barbell_both_down():
    j = pd.concat([_ret_pct("etf_SMH_close").rename("smh"),
                   _ret_pct("etf_XLE_close").rename("xle")], axis=1, join="inner").dropna()
    return ((j["smh"] < BARBELL_DROP) & (j["xle"] < BARBELL_DROP)).astype(float)


def _qqq_spx_p25_p50_spread():
    j = pd.concat([_raw("lieta_qqq_p25_p50_1m").rename("q"), _raw("lieta_spx_p25_p50_1m").rename("s")],
                  axis=1, join="inner").dropna()
    return j["q"] - j["s"]


DERIVED = {
    "lt_vxn_pctl1y": ("VXN 近 1 年百分位 (0–100；過去 252 個交易日含當日內 ≤ 當日值的比例)",
                      lambda: _rolling_pctl(_raw("cboe_VXN"))),
    "lt_move_pctl1y": ("MOVE 近 1 年百分位 (0–100；過去 252 個交易日含當日內 ≤ 當日值的比例)",
                       lambda: _rolling_pctl(_raw(17581))),
    "lt_vvix_d1": ("VVIX 單日變動 (點)", lambda: _raw("cboe_VVIX").diff()),
    "lt_putskew1m_prior_high20": (
        f"SPX 1M Put Skew 前 {NEW_HIGH_DAYS} 個觀測的最高點 (當日 > 此線 = 創 {NEW_HIGH_DAYS} 日新高)",
        lambda: _raw("gex_spx_put_skew_1m").shift(1).rolling(NEW_HIGH_DAYS).max()),
    "lt_qqq_spx_p25_p50_spread": (
        "QQQ − SPX 的 p25/p50 差 (p25/p50 = 25Δ put IV ÷ 50Δ put IV，30 天內插；>0 = QQQ skew 比 SPX 陡)",
        _qqq_spx_p25_p50_spread),
    "lt_qqq_spx_p25_p50_spread_pctl1y": (
        "QQQ − SPX p25/p50 差的近 1 年百分位 (0–100；過去 252 個觀測含當日內 ≤ 當日值的比例，樣本 <126 不輸出)",
        lambda: _rolling_pctl(_qqq_spx_p25_p50_spread())),
    "lt_hy_oas_chg20": ("HY OAS 20 日變化 (百分點；>0 = 擴大)", lambda: _raw(95001).diff(20)),
    "lt_ccc_spread_chg20": ("CCC−10Y 利差 20 日變化 (百分點；>0 = 擴大)", lambda: _raw(3612).diff(20)),
    "lt_bbb_spread_chg20": ("BBB−10Y 利差 20 日變化 (百分點；>0 = 擴大)", lambda: _raw(93001).diff(20)),
    "lt_smh_ret1d": ("SMH 單日報酬 (%)", lambda: _ret_pct("etf_SMH_close")),
    "lt_xle_ret1d": ("XLE 單日報酬 (%)", lambda: _ret_pct("etf_XLE_close")),
    "lt_barbell_both_down": (f"槓鈴兩腿同日跌 (SMH、XLE 同日 < {BARBELL_DROP}% = 1，否則 0)",
                             _barbell_both_down),
}


def _ensure_derived():
    """把 lt_* 序列放進 highcharts_utils 的 series cache（cache 被清掉後會重建）。"""
    for sid, (title, fn) in DERIVED.items():
        key = (sid, None)
        if key in _hu._series_cache:
            continue
        s = fn().dropna()
        _hu._series_cache[key] = {
            "title": title,
            "data": [[t.to_pydatetime(), float(v)] for t, v in s.items()],
        }


def _series(sid):
    """一般 pkl id / lt_ 衍生 id / 三元組運算式 / CORR 運算式 → 依日期遞增的 float Series。"""
    _ensure_derived()
    if isinstance(sid, tuple):
        d = process_expression(sid)
    elif isinstance(sid, str) and _hu.is_corr_expression(sid):
        d = _hu.process_corr(sid)
    else:
        d = load_series_data(sid)
    s = pd.Series({pd.Timestamp(t): float(v) for t, v in d["data"]
                   if v is not None and not pd.isna(v)})
    return s.sort_index()


def _exists(sid):
    try:
        _series(sid)
        return True
    except FileNotFoundError:
        return False


# ============================================================
# as-of / 延遲 / 缺資料
# ============================================================

def _ref_index():
    """最近已收盤交易日的基準：series_2（SPX 收盤）與 cboe_VIX 的日期聯集（沒有 NYSE 日曆工具）。"""
    idx = _series(2).index
    try:
        idx = idx.union(_series("cboe_VIX").index)
    except FileNotFoundError:
        pass
    return idx


def _lag_td(ts):
    """該日期之後基準序列還多出幾個交易日（見 _ref_index）。"""
    return int((_ref_index().normalize() > pd.Timestamp(ts).normalize()).sum())


def _lag_tol(sid):
    """該序列允許落後基準幾個交易日才算「延遲」；運算式取各成分中較嚴的。"""
    if isinstance(sid, tuple):
        return min(_lag_tol(sid[0]), _lag_tol(sid[2]))
    if isinstance(sid, int):
        return LAG_TOL_LAGGED if sid in FRED_IDS else LAG_TOL_DEFAULT
    if isinstance(sid, str) and (_LIETA_LAGGED.match(sid) or sid in _LT_LAGGED):
        return LAG_TOL_LAGGED
    return LAG_TOL_DEFAULT


def _prev_td(ts):
    """前一個交易日：用基準序列的日期；超過基準最後日期時退回週一到週五（不含假日）。"""
    ref = _ref_index()
    if len(ref) and ts <= ref[-1]:
        earlier = ref[ref < ts]
        if len(earlier):
            return earlier[-1]
    return ts - pd.offsets.BDay(1)


def _d(ts):
    return ts.strftime("%Y-%m-%d")


def _is_gex(sid):
    if isinstance(sid, tuple):
        return _is_gex(sid[0]) or _is_gex(sid[2])
    return isinstance(sid, str) and sid.startswith(GEX_PREFIX)


def _term_meta():
    """{TICKER: {EOD 暫定的 as-of 日期字串}}；sidecar 不存在或壞掉回 {}（退化為不標）。"""
    try:
        with open(os.path.join(DATA_DIR, TERM_META), encoding="utf-8") as f:
            meta = json.load(f)
        return {t: set(v.get("provisional_dates", [])) for t, v in meta["tickers"].items()}
    except (OSError, ValueError, KeyError, AttributeError):
        return {}


def _prov_tickers(sid):
    if isinstance(sid, tuple):
        return _prov_tickers(sid[0]) + _prov_tickers(sid[2])
    if isinstance(sid, str):
        m = _TERM_SID.match(sid)
        if m:
            return [m.group(1).upper()]
        return list(_TERM_DERIVED.get(sid, ()))
    return []


def _prov_tag(sid, ts):
    """term 序列在 ts 這個 as-of 日是 premarket=0（EOD）暫定點 → ' ⚠EOD暫定'。"""
    tickers = _prov_tickers(sid)
    if not tickers:
        return ""
    meta = _term_meta()
    return " ⚠EOD暫定" if any(_d(ts) in meta.get(t, ()) for t in tickers) else ""


def _asof_info(label, sid):
    """回 (文字, 落後交易日數, 容忍天數)：'label 2026-10-22'，gex 序列加 '（資料日 …）'，
    term 的 EOD 暫定點加 ' ⚠EOD暫定'，落後超過容忍天數加 ' ⚠延遲N日'。"""
    s = _series(sid)
    ts = s.index[-1]
    lag, tol = _lag_td(ts), _lag_tol(sid)
    text = f"{label} {_d(ts)}"
    if _is_gex(sid):
        text += f"（資料日 {_d(_prev_td(ts))}）"
    text += _prov_tag(sid, ts)
    if lag > tol:
        text += f" ⚠延遲{lag}日"
    return text, lag, tol


def _asof_text(label, sid):
    """檔案不存在標 缺資料。"""
    try:
        return _asof_info(label, sid)[0]
    except FileNotFoundError:
        return f"{label} 缺資料"


def _term_snapshot_note():
    """term 圖註：SPX 含夜盤變動、ETF 不含；EOD 暫定點讀 get_lieta_eod_series.py 的 sidecar。"""
    note = ("歷史點為 premarket=1 快照（as-of = 前一交易日收盤附近）；SPX 含夜盤變動（SPX 指數選擇權有夜盤），"
            "QQQ／SMH／TLT 不含。")
    try:
        with open(os.path.join(DATA_DIR, TERM_META), encoding="utf-8") as f:
            tickers = json.load(f)["tickers"]
    except (OSError, ValueError, KeyError):
        return note
    prov = [f"{t} {v['last_date']}" for t, v in tickers.items() if v.get("last_provisional")]
    if prov:
        note += (" 最新點為 EOD 暫定（premarket=0）：" + "、".join(prov) + "；EOD 快照品質較差（SPX 尤其明顯），"
                 "待下一個交易日的 premarket=1 快照取代。")
    return note


# ============================================================
# 9 條確認清單狀態（總覽用）
# ============================================================

OK, NO, UNK = "✅", "⬜", "❓"


def _fmt(v, nd=2):
    return "n/a" if v is None else f"{v:.{nd}f}"


def _last_at(s, ts=None):
    if ts is None:
        return s.index[-1], float(s.iloc[-1])
    return ts, float(s.loc[ts])


def _diff_note(*dates):
    """AND 條件的各項 as-of 不同日時提醒（各項用自己的最後一點，不強迫對齊）。"""
    return "；注意各項 as-of 不同日" if len({d for d in dates}) > 1 else ""


def _check(series_labels):
    """series_labels: [(label, sid)] → (各序列 as-of 文字, 缺資料的 label, 延遲說明)。"""
    asof, missing, delayed = [], [], []
    for label, sid in series_labels:
        try:
            text, lag, tol = _asof_info(label, sid)
        except FileNotFoundError:
            missing.append(label)
            asof.append(f"{label} 缺資料")
            continue
        asof.append(text)
        if lag > tol:
            delayed.append(f"{label} 落後 {lag} 個交易日（容忍 {tol}）")
    return asof, missing, delayed


def _cond(no, name, series_labels, build):
    """series_labels: [(label, sid)]；先檢查缺資料與延遲，再呼叫 build() 回 (triggered, detail)。"""
    asof, missing, delayed = _check(series_labels)
    if missing:
        return {"no": no, "name": name, "status": UNK, "detail": "缺資料：" + "、".join(missing),
                "asof": asof}
    triggered, detail = build()
    status = OK if triggered else NO
    if delayed:
        detail = f"延遲（{'；'.join(delayed)}），不能當成未觸發。最後值判斷：{'成立' if triggered else '未成立'}。{detail}"
        status = UNK
    return {"no": no, "name": name, "status": status, "detail": detail, "asof": asof}


def _barbell_aux():
    """第 7 條輔助條件：lieta_xsd_ivpct、lieta_xop_ivpct（XSD 半導體、XOP 油氣探勘 IV 百分位）都 > BARBELL_IV_PCTL。
    回 (✅／⬜／❓, 說明, 各序列 as-of)。缺資料或延遲 → ❓（不當成 ⬜）；不影響主條件。"""
    labels = [("XSD IV 百分位", "lieta_xsd_ivpct"), ("XOP IV 百分位", "lieta_xop_ivpct")]
    asof, missing, delayed = _check(labels)
    if missing:
        return UNK, "缺資料：" + "、".join(missing), asof
    (xt, xv), (ot, ov) = _last_at(_series(labels[0][1])), _last_at(_series(labels[1][1]))
    triggered = xv > BARBELL_IV_PCTL and ov > BARBELL_IV_PCTL
    detail = (f"XSD 百分位={xv:.2f}（{_d(xt)}）、XOP={ov:.2f}（{_d(ot)}）（皆 >{BARBELL_IV_PCTL:g} 成立）"
              + _diff_note(xt, ot))
    if delayed:
        detail = f"延遲（{'；'.join(delayed)}），不能當成未觸發。最後值判斷：{'成立' if triggered else '未成立'}。{detail}"
        return UNK, detail, asof
    return (OK if triggered else NO), detail, asof


def compute_status():
    """回傳 9 條的 [{no, name, status, detail, asof: [..]}]；第 7 條另帶 aux（輔助條件）與 label（主＋輔助）。"""
    out = []

    def c1():
        gap = _series(("cboe_VXN", "-", "cboe_VIX"))
        pct = _series("lt_vxn_pctl1y")
        (gt, gv), (pt, pv) = _last_at(gap), _last_at(pct)
        return (gv > VXN_VIX_GAP and pv > VXN_PCTL,
                f"VXN−VIX={gv:.2f}（{_d(gt)}，>{VXN_VIX_GAP}）；VXN 1Y 百分位={pv:.0f}（{_d(pt)}，>{VXN_PCTL}）"
                + _diff_note(gt, pt))
    out.append(_cond(1, "科技股 vol 領漲", [("VXN", "cboe_VXN"), ("VIX", "cboe_VIX")], c1))

    def c2():
        d1 = _series("lt_vvix_d1")
        sk, hi = _series("gex_spx_put_skew_1m"), _series("lt_putskew1m_prior_high20").dropna()
        dt, dv = _last_at(d1)
        st, sv = _last_at(sk)
        hv = float(hi.loc[st]) if st in hi.index else float(hi.iloc[-1])
        new_high = sv > hv
        return (dv >= VVIX_JUMP or new_high,
                f"VVIX 單日 {dv:+.1f}（{_d(dt)}，≥{VVIX_JUMP}）；SPX 1M put skew={sv:.3f}"
                f"（序列日 {_d(st)}、資料日 {_d(_prev_td(st))}）{'>' if new_high else '≤'} "
                f"前 {NEW_HIGH_DAYS} 日高點 {hv:.3f}")
    out.append(_cond(2, "翼部需求", [("VVIX", "cboe_VVIX"), ("SPX 1M put skew", "gex_spx_put_skew_1m")], c2))

    def c3():
        sp, qq = _series("lieta_spx_flip_dist_pct"), _series("lieta_qqq_flip_dist_pct")
        (st, sv), (qt, qv) = _last_at(sp), _last_at(qq)
        reg = []
        for t in ("spx", "qqq"):
            r = _series(f"lieta_{t}_regime")
            reg.append(f"{t.upper()} regime={_last_at(r)[1]:+.0f}")
        # 字面規則：lieta 最後日期 < series_2 最後日期 → 延遲；其中結構性落後 1 個交易日已扣掉
        literal = "字面規則（最後日期 < series_2 最後日期）= 延遲" if st < _series(2).index[-1] else "與 series_2 同日"
        return (sv < 0 and qv < 0,
                f"SPX 距 flip={sv:+.2f}%（{_d(st)}）、QQQ={qv:+.2f}%（{_d(qt)}）（<0 = 跌破 flip）；"
                f"{'、'.join(reg)}；{literal}，扣除結構性 {LAG_TOL_LAGGED} 個交易日後落後 "
                f"{max(_lag_td(st) - LAG_TOL_LAGGED, 0)} 日" + _diff_note(st, qt))
    out.append(_cond(3, "跌破 gamma flip", [("SPX flip 距離", "lieta_spx_flip_dist_pct"),
                                              ("QQQ flip 距離", "lieta_qqq_flip_dist_pct")], c3))

    def c4():
        t, v = _last_at(_series("lt_move_pctl1y"))
        mt, mv = _last_at(_series(17581))
        return v > MOVE_PCTL, f"MOVE={mv:.1f}（{_d(mt)}）；1Y 百分位={v:.0f}（{_d(t)}，>{MOVE_PCTL}）"
    out.append(_cond(4, "利率 vol 被買", [("MOVE", 17581)], c4))

    def c5():
        t, v = _last_at(_series("2:ret~cboe_TNX.CORR20"))
        return v > 0, f"corr(SPX 報酬, Δ10Y) 20 日={v:+.2f}（{_d(t)}，>0 = 股跌債漲 = 公債在避險）"
    out.append(_cond(5, "公債恢復避險", [("SPX", 2), ("TNX", "cboe_TNX")], c5))

    def c6():
        parts, hit = [], False
        for label, sid in (("HY OAS", "lt_hy_oas_chg20"), ("CCC−10Y", "lt_ccc_spread_chg20"),
                           ("BBB−10Y", "lt_bbb_spread_chg20")):
            t, v = _last_at(_series(sid))
            parts.append(f"{label} 20 日 {v:+.2f}pp（{_d(t)}）")
            if label != "BBB−10Y" and v > CREDIT_WIDEN:
                hit = True
        return hit, "；".join(parts) + f"（HY 或 CCC >{CREDIT_WIDEN}pp 成立；BBB 僅供參考）"
    out.append(_cond(6, "信用跟上", [("HY OAS", 95001), ("CCC−10Y", 3612)], c6))

    def c7():
        smh, xle = _series("lt_smh_ret1d"), _series("lt_xle_ret1d")
        j = pd.concat([smh.rename("smh"), xle.rename("xle")], axis=1, join="inner").dropna()
        t = j.index[-1]
        both = j.tail(5)
        n_both = int(((both["smh"] < BARBELL_DROP) & (both["xle"] < BARBELL_DROP)).sum())
        return (j["smh"].iloc[-1] < BARBELL_DROP and j["xle"].iloc[-1] < BARBELL_DROP,
                f"SMH {j['smh'].iloc[-1]:+.2f}%、XLE {j['xle'].iloc[-1]:+.2f}%（{_d(t)}，皆 <{BARBELL_DROP}% 成立）；"
                f"近 5 日同日達標 {n_both} 天")
    row7 = _cond(7, "槓鈴兩腿同跌", [("SMH", "etf_SMH_close"), ("XLE", "etf_XLE_close")], c7)
    # 輔助條件獨立判斷：缺資料或延遲標 ❓，不影響主條件的 status
    aux_status, aux_detail, aux_asof = _barbell_aux()
    row7["aux"] = {"status": aux_status, "detail": aux_detail, "asof": aux_asof}
    row7["label"] = f"主{row7['status']} 輔{aux_status}"
    row7["detail"] += f"｜輔助 {aux_status}：{aux_detail}"
    row7["asof"] = row7["asof"] + aux_asof
    out.append(row7)

    def c8():
        sp, bs = _series("lieta_vx1_vx2_spread"), _series("lieta_vx1_vix_basis")
        ct = _series("lieta_vx_contango_30d")
        (st, sv), (bt, bv), (ct_t, cv) = _last_at(sp), _last_at(bs), _last_at(ct)
        note = ""
        if st != bt:
            note = f"；注意 spread as-of {_d(st)}、basis as-of {_d(bt)} 不同日（VIX 與 vx 更新時間差）"
        return (sv > 0 or bv < 0,
                f"VX1−VX2={sv:+.2f}（{_d(st)}，>0 倒掛）；VX1−VIX={bv:+.2f}（{_d(bt)}，<0 現貨高於期貨）；"
                f"contango_30d={cv:+.2f}%（{_d(ct_t)}；證偽：回到 >{CONTANGO_FALSIFY}%）{note}")
    out.append(_cond(8, "VIX 期貨前端倒掛", [("VX1−VX2", "lieta_vx1_vx2_spread"),
                                           ("VX1−VIX", "lieta_vx1_vix_basis"),
                                           ("contango", "lieta_vx_contango_30d")], c8))

    def c9():
        sp = _series("lt_qqq_spx_p25_p50_spread")
        pc = _series("lt_qqq_spx_p25_p50_spread_pctl1y")
        pk = _series("lieta_qqq_put_skew3m_pctl1y")
        (t1, v1), (t2, v2), (t3, v3) = _last_at(sp), _last_at(pc), _last_at(pk)
        return (v2 > SPREAD_PCTL and v3 > QQQ_SKEW_PCTL,
                f"QQQ−SPX p25/p50 差={v1:+.4f}（{_d(t1)}{_prov_tag('lt_qqq_spx_p25_p50_spread', t1)}），"
                f"其 1Y 百分位={v2:.0f}（{_d(t2)}，>{SPREAD_PCTL}）；QQQ 3M put skew 1Y 百分位={v3:.0f}"
                f"（{_d(t3)}，>{QQQ_SKEW_PCTL}）；兩項都成立才算" + _diff_note(t2, t3))
    out.append(_cond(9, "科技股 skew 比 SPX 陡",
                     [("QQQ−SPX p25/p50 差", "lt_qqq_spx_p25_p50_spread"),
                      ("差的 1Y 百分位", "lt_qqq_spx_p25_p50_spread_pctl1y"),
                      ("QQQ put skew 1Y 百分位", "lieta_qqq_put_skew3m_pctl1y")], c9))
    return out


STATUS_COLOR = {OK: "#d64545", NO: "#b8b8b8", UNK: "#e8a838"}
STATUS_HEIGHT = {OK: 1.0, NO: 0.15, UNK: 0.5}


def _overview():
    rows = compute_status()
    n_ok = sum(r["status"] == OK for r in rows)
    n_unk = sum(r["status"] == UNK for r in rows)
    config = {
        "chart": {"type": "column"},
        "title": {"text": f"左尾風險確認清單總覽 — {n_ok}/9 成立（❓ {n_unk} 條缺資料或延遲）",
                  "style": {"fontWeight": "bold"}},
        "subtitle": {"text": "✅ 條件成立 ｜ ⬜ 未成立 ｜ ❓ 缺資料或延遲（不能當成未觸發）。第 7 條顯示「主＋輔助」："
                             "主條件決定狀態與計數，輔助條件缺資料或延遲只標 ❓、不影響主條件。"
                             "各條 as-of 見下方表格，不要拿各序列最後一點直接一起判斷。"},
        "xAxis": {"categories": [f"{r['no']} {r['name']}" for r in rows], "labels": {"style": {"fontSize": "11px"}}},
        "yAxis": {"title": {"text": None}, "min": 0, "max": 1.15, "labels": {"enabled": False},
                  "gridLineWidth": 0},
        "legend": {"enabled": False},
        "tooltip": {"useHTML": True, "pointFormat": "{point.detail}"},
        "credits": {"enabled": False},
        "plotOptions": {"column": {"dataLabels": {"enabled": True, "format": "{point.label}",
                                                  "style": {"fontSize": "16px"}}}},
        "series": [{
            "name": "狀態",
            "data": [{"y": STATUS_HEIGHT[r["status"]], "color": STATUS_COLOR[r["status"]],
                      "label": r.get("label", r["status"]), "detail": r["detail"]} for r in rows],
        }],
    }
    tr = "".join(
        f"<tr><td style='padding:2px 8px'>{r['no']}</td><td style='padding:2px 8px'>{r['name']}</td>"
        f"<td style='padding:2px 8px'>{r.get('label', r['status'])}</td><td style='padding:2px 8px'>{r['detail']}</td>"
        f"<td style='padding:2px 8px;font-size:12px'>{' ｜ '.join(r['asof'])}</td></tr>" for r in rows)
    summary = (
        "盤點 WN §4 確認清單（含實作 WN §3.2 的修改與新增），同時成立越多越接近「真正去風險化」而不是一般回檔。<br>"
        "狀態：✅ 成立、⬜ 未成立、❓ 缺資料或延遲（序列落後最近收盤交易日超過容忍天數、或序列缺檔；"
        "lieta screener／vx／iv_rv／hist_skew 與 FRED 容忍 1 日，其他 0 日；基準 = series_2 與 cboe_VIX 較新者）。"
        "每條序列的 as-of 日期不同，gex_* 序列標「資料日 = 序列日期 − 1 交易日」、term 的 EOD 暫定點標「⚠EOD暫定」，"
        "請看各自的 as-of，不要用「各序列最後一點」直接一起判斷。<br>"
        "<table style='border-collapse:collapse;font-size:13px'><tr><th>#</th><th>條件</th><th>狀態</th>"
        f"<th>最新值</th><th>各序列 as-of</th></tr>{tr}</table><br>"
        "<b>證偽訊號</b>（出現代表只是部位清洗）：SPX 1–3 天收復 gamma flip 且 VVIX 回到 95 以下；"
        "股債相關性轉負；10Y 下跌主要來自損益兩平而 DFII10 沒跌；CCC 利差回落而 BBB 沒跟上；"
        "COR1M 單日跳升後快速回落；VX 曲線 2–3 天內回到正價差（contango > 5%）。")
    return {"config": config, "summary": summary}


# ============================================================
# flow：SPX／QQQ 權利金前 20 大表（sidecar）+ 深價外 put 權利金趨勢
# ============================================================

FLOW_TICKERS = ("SPX", "QQQ")
FLOW_COLORS = {"SPX": "#d64545", "QQQ": "#2f6fb5"}


def _flow_meta():
    """讀 get_lieta_eod_series.py 寫的 sidecar：{TICKER: {query_date, underlying_price, rows}}；缺檔回 {}。"""
    try:
        with open(os.path.join(DATA_DIR, FLOW_META), encoding="utf-8") as f:
            return json.load(f)["tickers"]
    except (OSError, ValueError, KeyError):
        return {}


def _flow_table_html(meta):
    """各 ticker 最新 query_date 的權利金前 20 大表；深價外 put（is_deep_otm_put）整列標色加粗。
    query_date 落後基準超過容忍天數（flow = 當日，容忍 0）標 ⚠延遲。"""
    if not meta:
        return "<b>缺資料</b>：data/lieta_flow_top.json 不存在（先跑 get_lieta_eod_series.py）。"
    th = "".join(f"<th style='padding:2px 8px'>{h}</th>" for h in
                 ["#", "標的", "類型", "履約價", "到期日", "dte", "OTM %", "權利金(百萬美元)", "口數", "方向", "深價外 put"])
    blocks = []
    for t in FLOW_TICKERS:
        info = meta.get(t)
        if not info:
            blocks.append(f"<p><b>{t}</b>：缺資料</p>")
            continue
        qd = pd.Timestamp(info["query_date"])
        lag = _lag_td(qd)
        warn = f" ⚠延遲{lag}日" if lag > LAG_TOL_DEFAULT else ""
        px = info.get("underlying_price")
        px_text = f"{px:,.2f}" if px is not None else "n/a"
        trs = []
        for i, r in enumerate(info["rows"], start=1):
            deep = bool(r.get("is_deep_otm_put"))
            style = "background:#fde2e2;font-weight:600" if deep else ""
            cells = [i, r["ticker"], r["option_type"], f"{r['strike']:g}", r["expiration"], r["dte"],
                     f"{r['otm_pct']:+.1f}", f"{r['premium'] / 1e6:,.1f}", f"{r['volume']:,.0f}",
                     r["contract_direction"] or "", "🔻是" if deep else ""]
            trs.append(f"<tr style='{style}'>" + "".join(f"<td style='padding:2px 8px;text-align:right'>{c}</td>"
                                                          for c in cells) + "</tr>")
        blocks.append(
            f"<p><b>{t}</b>：query_date <b>{info['query_date']}</b>{warn}；underlying 價格 {px_text}"
            f"（前 {len(info['rows'])} 大列的 underlying_price 中位數，為 {info['query_date']} 當日收盤附近）</p>"
            f"<table style='border-collapse:collapse;font-size:12px'><thead><tr>{th}</tr></thead>"
            f"<tbody>{''.join(trs)}</tbody></table>")
    return "".join(blocks)


def _flow_chart():
    """custom chart：SPX、QQQ 深價外 put（OTM > 10%）權利金合計（近 FLOW_TREND_DAYS 個 query_date）折線，
    summary 內附最新 query_date 的權利金前 20 大表。"""
    meta = _flow_meta()
    series, asof = [], []
    for t in FLOW_TICKERS:
        sid = f"lieta_{t.lower()}_deep_otm_put_premium"
        asof.append(_asof_text(t, sid))
        try:
            s = _series(sid).tail(FLOW_TREND_DAYS)
        except FileNotFoundError:
            continue
        series.append({"name": f"{t} 深價外 put 權利金合計", "color": FLOW_COLORS[t],
                       "data": [[int(pd.Timestamp(d).timestamp() * 1000), float(v)] for d, v in s.items()]})
    try:
        vix = _series(VIX_OVERLAY).tail(FLOW_TREND_DAYS)
        asof.append(_asof_text("VIX", VIX_OVERLAY))
        series.append({"name": "VIX", "color": "#555555", "yAxis": 1, "dashStyle": "ShortDash",
                       "data": [[int(pd.Timestamp(d).timestamp() * 1000), float(v)] for d, v in vix.items()]})
    except FileNotFoundError:
        pass
    note = ("flow 是 query_date 當日成交（underlying 為當日收盤附近），不位移；與 screener／iv_rv（前一日收盤）不同族，"
            f"容忍 {LAG_TOL_DEFAULT} 日。深價外 put = option_type P 且 OTM > {DEEP_OTM_PCT}%。")
    config = {
        "chart": {"zoomType": "x"},
        "title": {"text": f"② 翼部需求（三）參考：SPX／QQQ 深價外 put（OTM > {DEEP_OTM_PCT}%）權利金合計（百萬美元，近 {FLOW_TREND_DAYS} 日）"},
        "subtitle": {"text": "as-of：" + " ｜ ".join(asof) + "<br/>" + note, "style": {"fontSize": "11px"}},
        "xAxis": {"type": "datetime"},
        "yAxis": [{"title": {"text": "百萬美元"}, "min": 0},
                  {"title": {"text": "VIX"}, "opposite": True, "gridLineWidth": 0}],
        "tooltip": {"shared": True, "valueDecimals": 1},
        "legend": {"enabled": True},
        "credits": {"enabled": False},
        "plotOptions": {"series": {"dataGrouping": {"enabled": False}}},
        "series": series,
    }
    summary = (
        "期權大單（lieta option_flow，每個 query_date 取 premium 前 2000 筆，fetcher 留存 premium 前 200 ∪ 深價外 put）。"
        f"折線 = 每個 query_date 深價外 put（OTM > {DEEP_OTM_PCT}%，遠端下行保護）的權利金合計；持續放大 = 有人在買遠端保護。<br>"
        "下表 = 各 ticker 最新 query_date 的權利金前 20 大，<b>粉紅底粗體 = 深價外 put</b>。"
        "SPX 欄位含 SPXW 週選；OTM % 正 = 價外、負 = 價內（遠期深價內 put 多半是合成部位，不是保護需求，請看深價外那幾列）。<br>"
        "只是參考，不納入 9 條確認清單的判斷。已知限制：2025-12-24 SPX、2025-12-29 SPX、2025-11-28 QQQ 的列數不足 2000"
        "（來源限制），這幾天合計偏低；2025-12-29 QQQ、2025-12-30 SPX／QQQ 來源回 0 列，沒有點。<br>"
        + _flow_table_html(meta))
    return {"config": config, "summary": summary}


# ============================================================
# 圖表群組
# ============================================================

class _LeftTailModule(ChartModule):
    """ChartModule + 衍生序列注入 + 每張圖 subtitle 顯示各序列 as-of。"""

    def __init__(self, *, charts, **kw):
        self._labels = [c.get("labels") for c in charts]
        self._notes = [c.get("note") for c in charts]
        super().__init__(charts=charts, **kw)

    def generate_chart_data(self, chart_id_entry, months=600):
        _ensure_derived()
        return super().generate_chart_data(chart_id_entry, months)

    def get_chart_config(self, chart_id_list):
        _ensure_derived()
        config = super().get_chart_config(chart_id_list)
        idx = self.CHART_IDS.index(chart_id_list)
        labels = self._labels[idx] or [str(e) for e in chart_id_list]
        parts = ["as-of：" + " ｜ ".join(_asof_text(lb, sid) for lb, sid in zip(labels, chart_id_list))]
        note = self._notes[idx]
        if callable(note):
            note = note()
        if note:
            parts.append(note)
        config["subtitle"] = {"text": "<br/>".join(parts), "style": {"fontSize": "11px"}}
        return config


_CHARTS = [
        {"custom_config": _overview},
        {
            "title": f"① 科技股 vol 領漲：VXN−VIX（>{VXN_VIX_GAP} 觸發；越大 = 壓力集中在科技股）｜VXN 1Y 百分位（>{VXN_PCTL} 觸發）",
            "ids": [("cboe_VXN", '-', "cboe_VIX"), "lt_vxn_pctl1y"],
            "axis": [0, 1],
            "labels": ["VXN−VIX", "VXN 1Y 百分位"],
            "plot_lines": [(("cboe_VXN", '-', "cboe_VIX"), VXN_VIX_GAP), ("lt_vxn_pctl1y", VXN_PCTL)],
            "summary":
                f"條件：VXN−VIX > {VXN_VIX_GAP}，且 VXN 近 1 年百分位 > {VXN_PCTL}。<br>"
                "VXN−VIX > 0 = Nasdaq 隱含波動率高於 S&P；差距越大 = 壓力集中在科技／AI 股。"
                "百分位 = 過去 252 個交易日內 ≤ 當日值的比例（0–100）。<br>"
                "VXN 與 VIX 兩條序列的最後日期可能不同，差只在兩者都有值的最後一天計算。",
        },
        {
            "title": f"② 翼部需求（一）：VVIX 單日變動（≥ +{VVIX_JUMP} 點觸發；>0 = vVol 上升 = 買 VIX 選擇權的力道增加）",
            "ids": ["lt_vvix_d1", "cboe_VVIX"],
            "axis": [0, 1],
            "labels": ["VVIX 單日變動", "VVIX"],
            "plot_lines": [("lt_vvix_d1", [VVIX_JUMP, 0])],
            "summary":
                f"條件：VVIX 單日 +{VVIX_JUMP} 以上，或 SPX 1M put skew 創 {NEW_HIGH_DAYS} 日新高（下一張圖），兩者任一成立。<br>"
                "VVIX 是翼部需求的直接代理：單日大漲 = 保護性選擇權被搶買。證偽：VVIX 回到 95 以下。",
        },
        {
            "title": f"② 翼部需求（二）：SPX 1M Put Skew（25dP/ATM）vs 前 {NEW_HIGH_DAYS} 日高點（> 虛線 = 創新高；>1 = put 比 ATM 貴）",
            "ids": ["gex_spx_put_skew_1m", "lt_putskew1m_prior_high20"],
            "axis": [0, 0],
            "labels": ["SPX 1M put skew", f"前 {NEW_HIGH_DAYS} 日高點"],
            "note": "注意：gex_* 的日期是 lieta 原始日期，資料日 = 序列日期 − 1 交易日（as-of 欄已換算）；比 lieta_* 的 as-of 晚一個交易日。",
            "summary":
                "SPX 1 個月 25-delta Put IV ÷ ATM IV（gex 專案口徑）。當日值高於前 20 個觀測的最高點 = 創 20 日新高 = put skew 被買。"
                "閾值是動態的（虛線 = 前 20 日高點），所以不畫固定水平線。",
        },
        {"custom_config": _flow_chart},
        {
            "title": "③ 跌破 Gamma Flip：現貨對 flip 距離 %（<0 = 現貨低於 flip = 負 Gamma 側；>0 = 在 flip 之上）｜regime（+1 / 0 / −1）",
            "ids": ["lieta_spx_flip_dist_pct", "lieta_spx_regime",
                    "lieta_qqq_flip_dist_pct", "lieta_qqq_regime"],
            "axis": [0, 1, 0, 1],
            "labels": ["SPX 距 flip", "SPX regime", "QQQ 距 flip", "QQQ regime"],
            "plot_lines": [("lieta_spx_flip_dist_pct", 0)],
            "note": "screener 結構性落後 1 個交易日（列日期 D = D 前一交易日收盤）；落後最近收盤交易日超過 1 個交易日標 ⚠延遲。"
                    "lieta 的 gamma flip 與野村口徑不同，只看方向與相對距離。",
            "summary":
                "條件：lieta_spx_flip_dist_pct < 0 且 lieta_qqq_flip_dist_pct < 0（落地時已取負，負 = 跌破 flip）。<br>"
                "取代原本依賴停更的 gex_*_spot_price 的算法。regime：+GEX = 1、NEUTRAL = 0、−GEX = −1。"
                "當天缺資料或延遲時要沿用前值並標「延遲」，不能當成未觸發。證偽：SPX 1–3 天內收復 flip。",
        },
        {
            "title": f"④ 利率 vol 被買：MOVE 1Y 百分位（>{MOVE_PCTL} 觸發）｜MOVE 指數",
            "ids": ["lt_move_pctl1y", 17581],
            "axis": [0, 1],
            "labels": ["MOVE 1Y 百分位", "MOVE"],
            "plot_lines": [("lt_move_pctl1y", MOVE_PCTL)],
            "summary":
                f"條件：MOVE 近 1 年百分位 > {MOVE_PCTL}。MOVE 是 USD 利率 vol 的總代理，百分位高 = 利率 vol 被買。"
                "百分位 = 過去 252 個交易日內 ≤ 當日值的比例。",
        },
        {
            "title": "⑤ 公債恢復避險：corr(SPX 日報酬, Δ10Y 殖利率) 10／20／60 日（20 日 >0 觸發；>0 = 股跌債漲）",
            "ids": ["2:ret~cboe_TNX.CORR20", "2:ret~cboe_TNX.CORR10", "2:ret~cboe_TNX.CORR60"],
            "axis": [0, 0, 0],
            "labels": ["CORR20", "CORR10", "CORR60"],
            "plot_lines": [("2:ret~cboe_TNX.CORR20", 0)],
            "summary":
                "條件：corr(SPX 日報酬, Δ10Y) 20 日 > 0。正值 = 股跌、殖利率跌（債漲）= 公債在避險；"
                "負值 = 股債同跌（通膨／利率衝擊體制）。證偽：相關性重新轉負。",
        },
        {
            "title": f"⑥ 信用跟上：HY OAS、CCC−10Y 利差 20 日變化（百分點；>{CREDIT_WIDEN:g} 觸發；>0 = 擴大）",
            "ids": ["lt_hy_oas_chg20", "lt_ccc_spread_chg20", "lt_bbb_spread_chg20"],
            "axis": [0, 0, 0],
            "labels": ["HY OAS Δ20", "CCC−10Y Δ20", "BBB−10Y Δ20"],
            "plot_lines": [("lt_hy_oas_chg20", CREDIT_WIDEN)],
            "summary":
                f"條件：HY OAS 或 CCC−10Y 利差 20 日擴大 > {CREDIT_WIDEN:g} 個百分點（BBB 僅供參考）。<br>"
                "注意 3612 是「CCC 有效殖利率 − DGS10」，不是 OAS；HY OAS 是 FRED BAMLH0A0HYM2。"
                "FRED 資料通常晚 1 個交易日。證偽：CCC 回落而 BBB 沒有跟上 = 只有最弱一層有壓力。",
        },
        {
            "title": f"⑦ 槓鈴兩腿同跌：SMH、XLE 單日報酬 %（皆 <{BARBELL_DROP}% 觸發）｜同日達標旗標（1 = 兩腿同日跌）",
            "ids": ["lt_smh_ret1d", "lt_barbell_both_down", "lt_xle_ret1d"],
            "axis": [0, 1, 0],
            "labels": ["SMH 日報酬", "兩腿同日跌", "XLE 日報酬"],
            "plot_lines": [("lt_smh_ret1d", BARBELL_DROP)],
            "summary":
                f"<b>主條件</b>：SMH 與 XLE 同日 < {BARBELL_DROP}%，且連續多日（總覽列近 5 日同日達標天數）。兩腿同跌 = 去風險化，不是輪動。<br>"
                f"<b>輔助條件</b>（下一張圖）：XSD、XOP 的 IV 百分位兩者都 > {BARBELL_IV_PCTL:g}。總覽顯示「主 ✅／⬜ ＋ 輔助 ✅／⬜／❓」，"
                "輔助缺資料或延遲標 ❓，不影響主條件。兩者各有自己的 as-of。",
        },
        {
            "title": f"⑦ 輔助：XSD（半導體）、XOP（油氣探勘）IV 百分位（兩者都 >{BARBELL_IV_PCTL:g} 輔助成立；0–1）｜IV（vol 點）",
            "ids": ["lieta_xsd_ivpct", "lieta_xop_ivpct", "lieta_xsd_iv", "lieta_xop_iv"],
            "axis": [0, 0, 1, 1],
            "labels": ["XSD IV 百分位", "XOP IV 百分位", "XSD IV", "XOP IV"],
            "plot_lines": [("lieta_xsd_ivpct", BARBELL_IV_PCTL)],
            "note": "sector_vol 的 as-of = 回應 date 的前一交易日（與 screener／iv_rv 同族，容忍 1 日）；"
                    "iv 只有 2 位小數（0.43 = 43 vol 點），解析度 1 vol 點，不適合細門檻。",
            "summary":
                f"輔助條件：lieta_xsd_ivpct 與 lieta_xop_ivpct 都 > {BARBELL_IV_PCTL:g}（lieta 的 IV 百分位原值，0–1）。"
                "XSD = 半導體（SMH 腿的 vol）、XOP = 油氣探勘（XLE 腿的 vol）：兩腿的 vol 同時被買 = 槓鈴兩側同時避險。<br>"
                "已知限制：(1) 來源有洞（2025-07-03 缺、2025-07-31～08-06 只有 1 檔），這些日子沒點；"
                "(2) L6 的 ticker 集合在 15／26／27 檔間不穩定地變動（XLK、XLE 只在 27 檔那組），SMH 從未出現在 L6，"
                "所以輔助條件用 XSD／XOP 而不是 SMH／XLE；(3) 2 位小數 = 解析度 1 vol 點。",
        },
        {
            "title": "⑦ 參考：DSI 1W 分數（SMH、XLE、IGV；0–10；不納入條件）",
            "ids": ["lieta_smh_dsi_1w", "lieta_xle_dsi_1w", "lieta_igv_dsi_1w"],
            "axis": [0, 0, 0],
            "labels": ["SMH", "XLE", "IGV"],
            "plot_lines": [("lieta_smh_dsi_1w", 0)],
            "note": "dsi 的 date = 回應 date（不位移，當日），容忍 0 日。",
            "summary":
                "lieta trend/dsi 的 score_1w（分數量化成幾個檔位，多為 0 或 10；方向在 trend_1w 欄，這裡只畫強度）。"
                "只當參考圖，不納入第 7 條判斷。DSI 的 1d／1w 是約 3 根 K 棒的平滑，不是單日報酬。"
                "SPX 不在 DSI 清單（converter 另有 lieta_spy_dsi_1w、qqq、tlt、hyg、jnk、xlk 可用）；各 ticker 的檔數隨時間 63 → 65 變動。",
        },
        {
            "title": f"⑧ VIX 期貨前端倒掛：VX1−VX2（>0 = 前端倒掛）、VX1−VIX（<0 = 現貨高於期貨）｜30 天 contango %（證偽：>{CONTANGO_FALSIFY}%）",
            "ids": ["lieta_vx1_vx2_spread", "lieta_vx_contango_30d", "lieta_vx1_vix_basis"],
            "axis": [0, 1, 0],
            "labels": ["VX1−VX2", "contango 30d", "VX1−VIX"],
            "plot_lines": [("lieta_vx1_vx2_spread", 0), ("lieta_vx_contango_30d", CONTANGO_FALSIFY)],
            "note": "vx 修正為 as-of 後最新點是 D−1；basis／contango 依賴 cboe_VIX，最後日期可能比 spread 早一天（VIX 更新時間差）。",
            "summary":
                "條件：lieta_vx1_vx2_spread > 0 或 lieta_vx1_vix_basis < 0。VX1 為每日換月的近月合約結算價（dte ≥ 1）。<br>"
                f"contango_30d = (30 天期貨內插價 ÷ VIX − 1)×100%；證偽：2–3 天內回到 contango > {CONTANGO_FALSIFY}%。"
                "各序列 as-of 不同，請分別看圖註日期，不要把不同日的最後一點直接相比。",
        },
        {
            "title": f"⑨ 科技股 skew 比 SPX 陡（一）：QQQ − SPX 的 p25/p50 差之 1Y 百分位（>{SPREAD_PCTL} 觸發）｜差本身｜QQQ、SPX p25/p50",
            "ids": ["lt_qqq_spx_p25_p50_spread_pctl1y", "lt_qqq_spx_p25_p50_spread",
                    "lieta_qqq_p25_p50_1m", "lieta_spx_p25_p50_1m"],
            "axis": [0, 1, 2, 2],
            "labels": ["差的 1Y 百分位", "QQQ−SPX p25/p50", "QQQ p25/p50", "SPX p25/p50"],
            "plot_lines": [("lt_qqq_spx_p25_p50_spread_pctl1y", SPREAD_PCTL)],
            "note": _term_snapshot_note,
            "summary":
                f"條件：(QQQ p25/p50 − SPX p25/p50) 的近 1 年百分位 > {SPREAD_PCTL}，<b>且</b>下一張圖的 QQQ 3M put skew "
                f"1Y 百分位 > {QQQ_SKEW_PCTL}，兩者同時成立。<br>"
                "p25/p50 = 25-delta put IV ÷ 50-delta put IV（term 表對 dte 線性內插到 30 天，不外推）：50Δ put 當 ATM 代理。"
                "百分位 = 過去 252 個觀測內 ≤ 當日值的比例，樣本 < 126 不輸出。<br>"
                "<b>為什麼不用 p25/atm</b>：lieta term 表的 atm_iv 不是 ATM，而是 VIX 型口徑（約 50Δ IV 的 1.15 倍，30 天內插值約等於 VIX − 1），"
                "翼部被買時 atm 跟著漲，p25/atm 會被壓扁；p25/atm 與 gex 的水準相關只有 0.59，換成 p25/p50 以後與 gex "
                "put_25d/((put_50d+call_50d)/2) 的水準相關 0.980、日變動相關 0.943。"
                "也不用「QQQ − SPX > 0」的絕對門檻：兩者歷史上只有 0.9% 的日子 QQQ 比 SPX 陡，絕對值門檻沒有意義，"
                "要抓的是 QQQ 相對 SPX「異常地」變陡，所以用差的百分位。<br>"
                "SPX 的 EOD 暫定點品質較差（見圖註）；壞到期日與壞快照已在 converter 過濾並寫 warning。",
        },
        {
            "title": f"⑨ 科技股 skew 比 SPX 陡（二）：QQQ／SMH／XLK 3M Put Skew 1Y 百分位（QQQ >{QQQ_SKEW_PCTL} 觸發）",
            "ids": ["lieta_qqq_put_skew3m_pctl1y", "lieta_smh_put_skew3m_pctl1y", "lieta_xlk_put_skew3m_pctl1y"],
            "axis": [0, 0, 0],
            "labels": ["QQQ", "SMH", "XLK"],
            "plot_lines": [("lieta_qqq_put_skew3m_pctl1y", QQQ_SKEW_PCTL)],
            "note": "百分位 = 過去 252 筆內 ≤ 當日值的比例；hist_skew 一次只給 1 年，所以約 126 筆（半年）之後才有值。",
            "summary":
                f"條件：QQQ 3M put skew 近 1 年百分位 > {QQQ_SKEW_PCTL}（和上一張圖的差百分位 > {SPREAD_PCTL} 同時成立）。"
                "put_skew 來自 lieta hist_skew（maturity=3m），as-of = label 前一交易日。",
        },
        {
            "title": "⑨ 參考：p25/p50 1M（25Δ put IV ÷ 50Δ put IV，30 天內插；>1 = put 比 50Δ 貴）SPX／QQQ／SMH／TLT",
            "ids": ["lieta_spx_p25_p50_1m", "lieta_qqq_p25_p50_1m", "lieta_smh_p25_p50_1m", "lieta_tlt_p25_p50_1m"],
            "axis": [0, 0, 0, 0],
            "labels": ["SPX", "QQQ", "SMH", "TLT"],
            "plot_lines": [("lieta_spx_p25_p50_1m", 1)],
            "note": _term_snapshot_note,
            "summary":
                "lieta term 表的 25Δ put IV ÷ 50Δ put IV（對 dte 線性內插到 30 天，不外推；50Δ put 當 ATM 代理）。"
                "TLT 只有 2025-07-31 起，SMH／QQQ 2024-12-31 起，SPX 2021-12-31 起。",
        },
        {
            "title": "⑨ 參考：p25/atm 1M（25Δ put IV ÷ lieta atm_iv；atm_iv 是 VIX 型口徑，不是 ATM，只供參考）SPX／QQQ／SMH／TLT",
            "ids": ["lieta_spx_p25_atm_1m", "lieta_qqq_p25_atm_1m", "lieta_smh_p25_atm_1m", "lieta_tlt_p25_atm_1m"],
            "axis": [0, 0, 0, 0],
            "labels": ["SPX", "QQQ", "SMH", "TLT"],
            "plot_lines": [("lieta_spx_p25_atm_1m", 1)],
            "note": _term_snapshot_note,
            "summary":
                "舊版第 9 條用的量。lieta 的 atm_iv 約是 50Δ IV 的 1.15 倍（VIX 型口徑），gex 的 atm_iv 約是 50Δ IV 的 1.025 倍，"
                "所以 lieta p25/atm 平均 1.05、gex 約 1.21，兩者水準相關只有 0.2～0.6，不能和 gex_spx_put_skew_1m 比，"
                "也不再用於判斷第 9 條（改用上面的 p25/p50）。保留當對照。",
        },
        {
            "title": "⑧⑨ 參考：term slope = ATM IV(9 天) − ATM IV(90 天)（vol 點；>0 = 前端高於後端 = 前端恐慌／倒掛）",
            "ids": ["lieta_spx_term_slope", "lieta_qqq_term_slope", "lieta_smh_term_slope", "lieta_tlt_term_slope"],
            "axis": [0, 0, 0, 0],
            "labels": ["SPX", "QQQ", "SMH", "TLT"],
            "plot_lines": [("lieta_spx_term_slope", 0)],
            "note": _term_snapshot_note,
            "summary":
                "符號與 gex_spx_term_slope（遠端 − 近端）相反：這裡 > 0 = 前端高於後端。atm 用 lieta atm_iv 原值（VIX 型口徑，不是 ATM）。"
                "SMH／TLT 的最遠到期日實測都遠大於 90 天（SLOPE_BACK_DTE 維持 90）；極少數日子最近到期日 > 9 天（內插 9 天不外推）會沒有點。",
        },
        {
            "title": "參考：Complacency（VVIX/VIX 比率 vs 50 日均線 ±1.67SD；跌破下緣 = breakdown = 自滿被打破）",
            "ids": ["complacency_ratio", "complacency_breakdown", "complacency_ma50", "complacency_lower", "complacency_upper"],
            "axis": [0, 1, 0, 0, 0],
            "labels": ["ratio", "breakdown", "50dma", "下緣", "上緣"],
            "summary":
                "本地自算（get_complacency_series.py）：ratio = cboe_VVIX ÷ cboe_VIX；下緣／上緣 = 50 日均線 ∓ 1.67 個標準差（ddof=1）；"
                "ratio < 下緣 標成 breakdown（1），與 goldmine 參考 CSV 50dma 誤差 < 0.3%。"
                "最後一點取 VVIX、VIX 同日交集，VIX 晚一天時比 VVIX 少一點。",
        },
]

# 每張時間序列圖都疊上 VIX（獨立右軸），方便對照各指標與市場恐慌程度。
for _c in _CHARTS:
    if "ids" in _c:
        _c["axis"] = list(_c.get("axis") or range(len(_c["ids"]))) + [len(_c["ids"])]
        _c["labels"] = list(_c.get("labels") or [str(e) for e in _c["ids"]]) + ["VIX"]
        _c["ids"] = list(_c["ids"]) + [VIX_OVERLAY]

_module = _LeftTailModule(filename='左尾風險監控', charts=_CHARTS, reverse_ids=[])

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
get_custom_config = _module.get_custom_config
