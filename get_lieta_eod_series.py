# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
# 讀 goldmine 的 eod_metrics.db（schema 見 WN-2026-10-24-左尾風險-lieta-goldmine資料接入實作 §2.2），
# 輸出 data/lieta_*.pkl（序列 id 見該 WN §3.1）。
# Phase 1：vx、gex_screener、iv_rv 三組。
# Phase 2：hist_skew（put_skew3m / skew3m / pctl1y）、term_iv（p25_atm_1m / term_slope）。
# Phase 3：sector_vol（XSD／XOP iv、iv_percentile）、trend_dsi（dsi_1w）、flow_top（深價外 put 權利金、前 20 大表 sidecar）。
import argparse
import json
import math
import os
import pathlib
import pickle
import sqlite3
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 日期檔日誌已集中設定於 log_config.py，本檔「禁止」再呼叫 logger.add()，
# 否則多個 sink 指向同一 log 檔，每筆訊息會重複寫入 N 次（2026-09 已踩過此坑）。

DATA_DIR = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)

EOD_DB_PATH = r"C:\code\2026-09-09-new-lieta-goldmine\impulse\eod_metrics.db"

# WN §2.3：L2 gex_screener / L3 iv_rv 的 ticker 清單（DB 內為大寫，pkl 檔名一律小寫）
SCREENER_TICKERS = ["SPX", "QQQ", "SMH", "XLK", "XLE", "TLT",
                    "NVDA", "AVGO", "META", "ORCL", "CRWV"]
IVRV_TICKERS = ["SPX", "QQQ", "SMH", "XLK", "XLE", "IGV", "TLT", "HYG"]
IVRV_MATURITY = "1m"

CONTANGO_TARGET_DTE = 30

# WN §2.3：L4 hist_skew（不含 HYG）、L5 term_iv 的 ticker 清單
SKEW_TICKERS = ["SPX", "QQQ", "SMH", "XLK", "XLE", "IGV", "TLT"]
SKEW_MATURITY = "3m"
TERM_TICKERS = ["SPX", "QQQ", "SMH", "TLT"]

# Phase 3：L6 sector_vol（XSD = 半導體、XOP = 油氣探勘；實作 WN §5-4：以 ETF 發行商定義為準）、
# L7 trend_dsi（SPX 不在 DSI 清單，以 SPY 代）、L8 flow_top
SECTOR_TICKERS = ["XSD", "XOP"]
DSI_TICKERS = ["SMH", "XLE", "XLK", "IGV", "HYG", "JNK", "TLT", "SPY", "QQQ"]
FLOW_TICKERS = ["SPX", "QQQ"]
FLOW_TOP_N = 20
FLOW_META_NAME = "lieta_flow_top.json"   # 最新 query_date 的權利金前 20 大表，route 讀它畫表格

# put_skew3m 百分位：過去 252 個交易日（含當日），樣本不足 126 點不輸出
PCTL_WINDOW = 252
PCTL_MIN_POINTS = 126

# term_iv 內插目標（天）：p25/p50、p25/atm 取 30 天；term_slope = atm(9) − atm(90)
SKEW_TARGET_DTE = 30
SLOPE_FRONT_DTE = 9
SLOPE_BACK_DTE = 90
# 驗收對照用 _bucket 版：dte 22–35 各到期日 p25/atm 先相除再平均（gex v_skew_indicators '1m' 的口徑）
BUCKET_DTE_LO, BUCKET_DTE_HI = 22, 35
# term 壞值過濾（合約補充 #3 第 6 點）：到期日層 atm 或 p25 > TERM_IV_MAX、p25/p50 不在範圍；
# 快照層 dte 7–60 的到期日中 p25 < p50（或 p25 < atm）的比例 > BAD_SNAPSHOT_SHARE 整份不輸出。
# 快照層只套用 SPX：壞快照（EOD 夜盤報價稀薄）只在 SPX 實測到；TLT 的 put skew 本來就可能反向
# （p25 < p50 在 TLT 是正常行情，14 份快照會被誤刪），QQQ／SMH 的 p25 < atm 是 lieta atm 口徑造成。
# 其他 ticker 只寫 warning 不刪。要照字面套用到全部 ticker，把 TERM_SNAPSHOT_FILTER_TICKERS 改成 TERM_TICKERS。
TERM_IV_MAX = 1.0
TERM_P25_P50_RANGE = (0.8, 2.0)
BAD_SNAPSHOT_SHARE = 0.2
SNAPSHOT_DTE_LO, SNAPSHOT_DTE_HI = 7, 60
SNAPSHOT_MIN_EXPIRIES = 2
TERM_SNAPSHOT_FILTER_TICKERS = ("SPX",)
# 各 ticker 最後一點是否為 EOD 暫定（premarket=0）的 sidecar，route 讀它標「EOD 暫定」
TERM_META_NAME = "lieta_term_meta.json"

# iv_rv 離群值偵測（只警告不刪點）：單日偏離前後兩日中位數的倍數與絕對差（vol 點）門檻
OUTLIER_RATIO = 3
OUTLIER_MIN_DIFF = 3


def _save_pkl(name, title, data, out_dir=None):
    if not data:
        logger.warning(f"No data, skip {name}")
        return
    out_dir = out_dir or DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    pkl_path = os.path.join(out_dir, f"{name}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": title, "data": data}, f)
    logger.info(f"Saved {len(data)} records -> {pkl_path}")


def _to_dt(date_str):
    """DB 的 date 欄（YYYY-MM-DD 或 YYYYMMDD）轉 08:00 datetime；無法解析回 None。"""
    s = str(date_str).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).replace(hour=8)
        except ValueError:
            continue
    return None


def _to_float(v):
    """NULL / 空字串 / NaN / 非數字 → None（該點跳過，不補 0）；字串數字轉 float。"""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _table_exists(conn, table):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _load_pkl_by_date(path):
    """讀 pkl，回傳 {date: float}；檔案不存在回傳 None。"""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        obj = pickle.load(f)
    return {d.date(): float(v) for d, v in obj["data"] if v is not None}


def _interp_dte(contracts, target):
    """contracts 為 [(dte, settlement)] 且依 dte 遞增；線性內插到 target 天，
    target 落在範圍外不外推，回 None。"""
    if len(contracts) == 1 and contracts[0][0] == target:
        return contracts[0][1]
    for (d0, p0), (d1, p1) in zip(contracts, contracts[1:]):
        if d0 <= target <= d1:
            if d1 == d0:
                return p0
            return p0 + (p1 - p0) * (target - d0) / (d1 - d0)
    return None


def _export_vx(conn, out_dir, vix_by_date):
    """vx_curve → lieta_vx1 / vx2 / vx1_vx2_spread / vx1_vix_basis / vx_contango_30d。"""
    if not _table_exists(conn, "vx_curve"):
        logger.warning("vx_curve table not found, skip vx series")
        return
    rows = conn.execute(
        "SELECT date, dte, settlement FROM vx_curve ORDER BY date, dte"
    ).fetchall()
    by_date = {}
    for date_str, dte, settle in rows:
        dte_f = _to_float(dte)
        # dte < 1：到期日當天的合約已由 SOQ 結算，不當 VX1/VX2
        if dte_f is None or dte_f < 1:
            continue
        by_date.setdefault(date_str, []).append((dte_f, _to_float(settle)))

    vx_dts = [dt for dt in map(_to_dt, by_date) if dt is not None]
    if vix_by_date and vx_dts and max(vix_by_date) < max(vx_dts).date():
        logger.warning(
            f"VIX last date {max(vix_by_date)} is earlier than vx last date "
            f"{max(vx_dts).date()}: latest vx1_vix_basis / vx_contango_30d lag vx1")

    vx1, vx2, spread, basis, contango = [], [], [], [], []
    for date_str in sorted(by_date):
        dt = _to_dt(date_str)
        if dt is None:
            continue
        # 先依 dte 排名再看 settlement：VX1 缺價時不讓 VX2 遞補成 VX1
        ranked = sorted(by_date[date_str], key=lambda x: x[0])
        p1 = ranked[0][1] if len(ranked) >= 1 else None
        p2 = ranked[1][1] if len(ranked) >= 2 else None
        # VIX 期貨結算價不可能 <= 0，視為缺值
        p1 = p1 if p1 is not None and p1 > 0 else None
        p2 = p2 if p2 is not None and p2 > 0 else None
        if p1 is not None:
            vx1.append([dt, p1])
        if p2 is not None:
            vx2.append([dt, p2])
        if p1 is not None and p2 is not None:
            spread.append([dt, p1 - p2])
        vix = vix_by_date.get(dt.date()) if vix_by_date else None
        if vix is not None:
            if p1 is not None:
                basis.append([dt, p1 - vix])
            if vix > 0:
                dte1 = ranked[0][0]
                if dte1 > CONTANGO_TARGET_DTE:
                    # VX1 dte > 30：VX1 之前沒有合約，改用 VIX 現貨（dte=0）和 VX1 內插
                    f30 = (vix + (p1 - vix) * CONTANGO_TARGET_DTE / dte1
                           if p1 is not None else None)
                else:
                    valid = [(d, p) for d, p in ranked if p is not None and p > 0]
                    f30 = _interp_dte(valid, CONTANGO_TARGET_DTE)
                if f30 is not None:
                    contango.append([dt, (f30 / vix - 1) * 100])

    _save_pkl("lieta_vx1", "Lieta VX1 結算價（近月 VIX 期貨）", vx1, out_dir)
    _save_pkl("lieta_vx2", "Lieta VX2 結算價（次月 VIX 期貨）", vx2, out_dir)
    _save_pkl("lieta_vx1_vx2_spread", "Lieta VX1 − VX2（>0 為前端倒掛）", spread, out_dir)
    _save_pkl("lieta_vx1_vix_basis", "Lieta VX1 − VIX 現貨基差", basis, out_dir)
    _save_pkl("lieta_vx_contango_30d",
              "Lieta VIX 期貨 30 天內插價 / VIX − 1 (%)；VX1 dte>30 時用 VIX 現貨與 VX1 內插，"
              "全部合約 dte<30 不外推", contango, out_dir)


# regime_raw 對映：+GEX=1、NEUTRAL=0、−GEX=−1
def _regime_value(raw):
    if raw is None:
        return None
    s = str(raw).strip().upper().replace("−", "-")
    if not s:
        return None
    if "NEUTRAL" in s:
        return 0.0
    if s.startswith("+") or s.startswith("POS"):
        return 1.0
    if s.startswith("-") or s.startswith("NEG"):
        return -1.0
    return None


def _warn_outliers(name, points):
    """points 為 [[datetime, vol 點]]；單日偏離前後兩日中位數 > OUTLIER_RATIO 倍
    且絕對差 > OUTLIER_MIN_DIFF 時寫 warning（lieta 偶有單日尖刺），不改動資料。"""
    hits = []
    for (_, p), (d, v), (_, n) in zip(points, points[1:], points[2:]):
        med = (p + n) / 2  # 兩個值的中位數
        if med <= 0 or abs(v - med) <= OUTLIER_MIN_DIFF:
            continue
        if v > med * OUTLIER_RATIO or v < med / OUTLIER_RATIO:
            hits.append(f"{d.date()}={v:.2f}(鄰日中位數 {med:.2f})")
    if hits:
        logger.warning(f"{name} outlier points (kept): " + ", ".join(hits))


def _export_screener(conn, out_dir):
    """gex_screener → lieta_{t}_spot / flip_dist_pct / regime / protection_cost_1m。"""
    if not _table_exists(conn, "gex_screener"):
        logger.warning("gex_screener table not found, skip screener series")
        return
    unknown_regime = {}  # 無法辨識的 regime_raw → 筆數，每次執行只警告一次
    for ticker in SCREENER_TICKERS:
        rows = conn.execute(
            "SELECT date, spot_price, flip_distance_pct, regime_raw, protection_cost_25_1m "
            "FROM gex_screener WHERE UPPER(ticker)=? ORDER BY date",
            (ticker,),
        ).fetchall()
        spot, flip, regime, prot = [], [], [], []
        for date_str, sp, fd, rg, pc in rows:
            dt = _to_dt(date_str)
            if dt is None:
                continue
            if _regime_value(rg) is None and rg is not None and str(rg).strip():
                key = str(rg).strip()
                unknown_regime[key] = unknown_regime.get(key, 0) + 1
            for lst, val in ((spot, _to_float(sp)), (flip, _to_float(fd)),
                             (regime, _regime_value(rg)), (prot, _to_float(pc))):
                if val is not None:
                    lst.append([dt, val])
        tk, tk_upper = ticker.lower(), ticker
        _save_pkl(f"lieta_{tk}_spot", f"Lieta {tk_upper} Spot", spot, out_dir)
        _save_pkl(f"lieta_{tk}_flip_dist_pct",
                  f"Lieta {tk_upper} 現貨對 Gamma Flip 距離 % (<0 = 跌破 flip)", flip, out_dir)
        _save_pkl(f"lieta_{tk}_regime",
                  f"Lieta {tk_upper} GEX 環境 (+GEX=1, NEUTRAL=0, −GEX=−1)", regime, out_dir)
        _save_pkl(f"lieta_{tk}_protection_cost_1m",
                  f"Lieta {tk_upper} 25Δ Put 保護成本 1M（占現貨比例）", prot, out_dir)
    if unknown_regime:
        logger.warning("Unknown regime_raw values skipped: "
                       + ", ".join(f"{k!r} x{n}" for k, n in sorted(unknown_regime.items())))


def _export_ivrv(conn, out_dir):
    """iv_rv（maturity=1m）→ lieta_{t}_iv1m / rv1m / vrp。
    lieta 的 1m rv = 30 個交易日 RMS 波動率（log 報酬、不去均值、×√252）；
    as-of 日期由 goldmine fetcher 處理，本檔照抄 DB 的 date。"""
    if not _table_exists(conn, "iv_rv"):
        logger.warning("iv_rv table not found, skip iv_rv series")
        return
    for ticker in IVRV_TICKERS:
        rows = conn.execute(
            "SELECT date, iv, rv FROM iv_rv "
            "WHERE UPPER(ticker)=? AND maturity=? ORDER BY date",
            (ticker, IVRV_MATURITY),
        ).fetchall()
        iv_data, rv_data, vrp_data = [], [], []
        for date_str, iv, rv in rows:
            dt = _to_dt(date_str)
            if dt is None:
                continue
            iv_f, rv_f = _to_float(iv), _to_float(rv)
            # lieta 給小數（0.15），本 repo 慣例是 vol 點（×100，同 gex_*_iv30）
            iv_f = iv_f * 100 if iv_f is not None else None
            rv_f = rv_f * 100 if rv_f is not None else None
            if iv_f is not None:
                iv_data.append([dt, iv_f])
            if rv_f is not None:
                rv_data.append([dt, rv_f])
            if iv_f is not None and rv_f is not None:
                vrp_data.append([dt, iv_f - rv_f])
        tk, tk_upper = ticker.lower(), ticker
        _warn_outliers(f"lieta_{tk}_iv1m", iv_data)
        _warn_outliers(f"lieta_{tk}_rv1m", rv_data)
        # lieta 只給 2 位小數，iv / rv / vrp 解析度約 1 vol 點，不適合細門檻
        _save_pkl(f"lieta_{tk}_iv1m",
                  f"Lieta {tk_upper} IV 1M (vol 點，解析度約 1 vol 點)", iv_data, out_dir)
        _save_pkl(f"lieta_{tk}_rv1m",
                  f"Lieta {tk_upper} RV 30 日 (vol 點，解析度約 1 vol 點)", rv_data, out_dir)
        _save_pkl(f"lieta_{tk}_vrp",
                  f"Lieta {tk_upper} VRP (IV−RV) 1M (vol 點，解析度約 1 vol 點)",
                  vrp_data, out_dir)


def _rolling_pctl(values, window=PCTL_WINDOW, min_points=PCTL_MIN_POINTS):
    """values 依日期遞增；回傳每點在過去 window 點（含當日）內的百分位（0–100，
    rank ≤ 當日值 的比例），視窗內樣本 < min_points 為 None。"""
    out = []
    for i, v in enumerate(values):
        win = values[max(0, i - window + 1):i + 1]
        if len(win) < min_points:
            out.append(None)
        else:
            out.append(sum(1 for x in win if x <= v) / len(win) * 100)
    return out


def _export_skew(conn, out_dir):
    """hist_skew（maturity=3m）→ lieta_{t}_put_skew3m / skew3m / put_skew3m_pctl1y。
    日期為 as-of（由 goldmine fetcher 處理），本檔照抄 DB 的 date。"""
    if not _table_exists(conn, "hist_skew"):
        logger.info("hist_skew table not found, skip skew series")
        return
    if conn.execute("SELECT 1 FROM hist_skew LIMIT 1").fetchone() is None:
        logger.info("hist_skew table is empty, skip skew series")
        return
    for ticker in SKEW_TICKERS:
        rows = conn.execute(
            "SELECT date, skew, put_skew FROM hist_skew "
            "WHERE UPPER(ticker)=? AND maturity=? ORDER BY date",
            (ticker, SKEW_MATURITY),
        ).fetchall()
        skew, put_skew = [], []
        for date_str, sk, psk in rows:
            dt = _to_dt(date_str)
            if dt is None:
                continue
            sk_f, psk_f = _to_float(sk), _to_float(psk)
            if sk_f is not None:
                skew.append([dt, sk_f])
            if psk_f is not None:
                put_skew.append([dt, psk_f])
        pctl = [[dt, p] for (dt, _), p in
                zip(put_skew, _rolling_pctl([v for _, v in put_skew])) if p is not None]
        tk, tk_upper = ticker.lower(), ticker
        _save_pkl(f"lieta_{tk}_put_skew3m",
                  f"Lieta {tk_upper} 3M Put Skew (hist_skew)", put_skew, out_dir)
        _save_pkl(f"lieta_{tk}_skew3m",
                  f"Lieta {tk_upper} 3M Skew (hist_skew)", skew, out_dir)
        _save_pkl(f"lieta_{tk}_put_skew3m_pctl1y",
                  f"Lieta {tk_upper} 3M Put Skew 近 1 年百分位 "
                  f"(0–100；過去 {PCTL_WINDOW} 個交易日含當日內 ≤ 當日值的比例，"
                  f"樣本 <{PCTL_MIN_POINTS} 點不輸出)", pctl, out_dir)


def _term_points(rows):
    """同一 (date, ticker) 快照的 [(dte, p25_iv, p50_iv, atm_iv)] →
    (依 dte 遞增的有效點 [(dte, p25, p50, atm)]，被到期日層過濾丟掉的 [(dte, 原因)])。
    排除 dte<1（到期日當天，與 gex_spx_put_skew_1m 一致）；p25 / p50 / atm 缺值或 <=0 記 None，
    各序列自己挑需要的欄位都有值的到期日，讓分子分母用同一組到期日。
    到期日層壞值過濾（合約補充 #3 第 6 點）：atm 或 p25 > TERM_IV_MAX，或 p25/p50 不在
    TERM_P25_P50_RANGE → 該到期日整個丟掉。"""
    pts, dropped = {}, []
    for dte, p25, p50, atm in rows:
        dte_f = _to_float(dte)
        if dte_f is None or dte_f < 1:
            continue
        p25_f, p50_f, atm_f = (v if v is not None and v > 0 else None
                               for v in (_to_float(p25), _to_float(p50), _to_float(atm)))
        if (atm_f is not None and atm_f > TERM_IV_MAX) or (p25_f is not None and p25_f > TERM_IV_MAX):
            dropped.append((dte_f, f"atm={atm_f} p25={p25_f} > {TERM_IV_MAX:g}"))
            continue
        if p25_f is not None and p50_f is not None:
            r = p25_f / p50_f
            if not TERM_P25_P50_RANGE[0] <= r <= TERM_P25_P50_RANGE[1]:
                dropped.append((dte_f, f"p25/p50={r:.2f} 不在 {TERM_P25_P50_RANGE}"))
                continue
        pts[dte_f] = (p25_f, p50_f, atm_f)
    return [(d, p, q, a) for d, (p, q, a) in sorted(pts.items())], dropped


def _snapshot_bad_reason(rows):
    """快照層（合約補充 #3 第 6 點）：dte 7–60 的到期日中，p25 < p50（或 p25 < atm）的比例 >
    BAD_SNAPSHOT_SHARE → 回原因字串，整份快照不輸出；正常回 None。
    lieta 的 atm 是 VIX 型口徑（約 1.15 × 50Δ），正常快照 p25 > atm；SPX EOD 快照在夜盤報價稀薄時
    近端 p25 / p50 / atm 會亂（review：EOD 15% 到期日 p25 < atm，1206 份 premarket 快照 0%）。"""
    near = []
    for dte, p25, p50, atm in rows:
        dte_f, p25_f = _to_float(dte), _to_float(p25)
        if dte_f is None or p25_f is None or p25_f <= 0 or not SNAPSHOT_DTE_LO <= dte_f <= SNAPSHOT_DTE_HI:
            continue
        near.append((p25_f, _to_float(p50), _to_float(atm)))
    for label, idx in (("p25<p50", 1), ("p25<atm", 2)):
        pairs = [(n[0], n[idx]) for n in near if n[idx] is not None and n[idx] > 0]
        if len(pairs) < SNAPSHOT_MIN_EXPIRIES:
            continue
        share = sum(1 for p25, other in pairs if p25 < other) / len(pairs)
        if share > BAD_SNAPSHOT_SHARE:
            return f"{label} {share:.0%}"
    return None


def _term_snapshots(conn, ticker):
    """term_iv → [(date_str, premarket, rows)]：每個 as-of 日只留一份快照，優先 premarket=1，
    沒有才用 premarket=0（EOD 暫定）。查詢只用 date / premarket 欄，不假設主鍵
    （現行 DB 主鍵無 premarket、新 DB 主鍵含 premarket 且兩版本並存，兩種都能讀）；
    沒有 premarket 欄時視為 1。rows = [(dte, p25_iv, p50_iv, atm_iv)]。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(term_iv)")}
    pm_expr = "premarket" if "premarket" in cols else "1"
    rows = conn.execute(
        f"SELECT date, {pm_expr}, dte, p25_iv, p50_iv, atm_iv FROM term_iv "
        "WHERE UPPER(ticker)=? ORDER BY date", (ticker,)).fetchall()
    by_date = {}
    for date_str, pm, dte, p25, p50, atm in rows:
        # NULL 當 1（正式快照）；只有明確的 0 才是 EOD 暫定
        by_date.setdefault(date_str, {}).setdefault(0 if pm == 0 else 1, []).append(
            (dte, p25, p50, atm))
    out = []
    for date_str in sorted(by_date):
        snaps = by_date[date_str]
        pm = 1 if 1 in snaps else 0
        out.append((date_str, pm, snaps[pm]))
    return out


def _warn_term_filtered(name, bad_snapshots, bad_expiries, kept_snapshots):
    """term 壞值過濾的 warning（照 _warn_outliers 的寫法：每種一行，列出日期）。"""
    if bad_snapshots:
        logger.warning(f"{name} bad snapshots dropped: " + ", ".join(
            f"{d}({why})" for d, why in bad_snapshots))
    if bad_expiries:
        logger.warning(f"{name} bad expiries dropped: " + ", ".join(
            f"{d} dte{dte:g}({why})" for d, dte, why in bad_expiries))
    if kept_snapshots:
        logger.warning(f"{name} suspicious snapshots (kept; ticker not in "
                       "TERM_SNAPSHOT_FILTER_TICKERS): " + ", ".join(
                           f"{d}({why})" for d, why in kept_snapshots))


def _save_json(name, obj, out_dir=None):
    out_dir = out_dir or DATA_DIR
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    logger.info(f"Saved -> {path}")


def _export_term(conn, out_dir):
    """term_iv → lieta_{t}_p25_p50_1m / p25_atm_1m / p25_atm_1m_bucket / term_slope。
    正式值 = premarket=1 快照；沒有 premarket=1 的 as-of 日才用 premarket=0（EOD）當暫定最新點，
    各 ticker 的暫定日期寫進 data/lieta_term_meta.json，route 讀它標「EOD 暫定」。
    p25_p50_1m（主序列）：先對 dte 線性內插到 30 天的 p25_iv 與 p50_iv，再相除（不外推）。
      lieta 的 atm_iv 是 VIX 型口徑（約 50Δ IV 的 1.15 倍），不是 ATM；用 50Δ put 當 ATM 代理。
    p25_atm_1m（參考）：分母用 lieta 原 atm_iv，口徑與 gex 不同。
    p25_atm_1m_bucket（對照）：dte 22–35 各到期日 p25/atm 先相除再平均。
    term_slope：atm(9 天) − atm(90 天)，vol 點（term_iv 的 iv 是小數，×100）；> 0 = 前端高於後端；
      atm 用 lieta 原值（同樣是 VIX 型口徑）。
    壞值過濾見 _term_points（到期日層）與 _snapshot_bad_reason（快照層，只套用 TERM_SNAPSHOT_FILTER_TICKERS）。"""
    if not _table_exists(conn, "term_iv"):
        logger.info("term_iv table not found, skip term series")
        return
    if conn.execute("SELECT 1 FROM term_iv LIMIT 1").fetchone() is None:
        logger.info("term_iv table is empty, skip term series")
        return
    n_prov_rows, prov_dates_all, meta = 0, set(), {}
    for ticker in TERM_TICKERS:
        ratio, ratio_p50, bucket, slope = [], [], [], []
        bad_snaps, bad_exps, kept_snaps = [], [], []
        prov_dates, last_date = [], None
        for date_str, pm, rows in _term_snapshots(conn, ticker):
            dt = _to_dt(date_str)
            if dt is None:
                continue
            last_date = date_str
            if pm == 0:
                prov_dates.append(date_str)
                n_prov_rows += len(rows)
                prov_dates_all.add(date_str)
            why = _snapshot_bad_reason(rows)
            if why and ticker in TERM_SNAPSHOT_FILTER_TICKERS:
                bad_snaps.append((date_str, why))
                continue
            if why:
                kept_snaps.append((date_str, why))
            pts, dropped = _term_points(rows)
            bad_exps.extend((date_str, dte, w) for dte, w in dropped)

            def pair(i, j):
                return [(p[0], p[i], p[j]) for p in pts if p[i] is not None and p[j] is not None]

            for out, i, j in ((ratio, 1, 3), (ratio_p50, 1, 2)):
                pp = pair(i, j)
                num = _interp_dte([(d, x) for d, x, _ in pp], SKEW_TARGET_DTE)
                den = _interp_dte([(d, y) for d, _, y in pp], SKEW_TARGET_DTE)
                if num is not None and den is not None:
                    out.append([dt, num / den])
            in_bucket = [x / y for d, x, y in pair(1, 3) if BUCKET_DTE_LO <= d <= BUCKET_DTE_HI]
            if in_bucket:
                bucket.append([dt, sum(in_bucket) / len(in_bucket)])
            atm_pts = [(p[0], p[3]) for p in pts if p[3] is not None]
            atm_f = _interp_dte(atm_pts, SLOPE_FRONT_DTE)
            atm_b = _interp_dte(atm_pts, SLOPE_BACK_DTE)
            if atm_f is not None and atm_b is not None:
                slope.append([dt, (atm_f - atm_b) * 100])
        tk, tk_upper = ticker.lower(), ticker
        _warn_term_filtered(f"lieta_{tk} term", bad_snaps, bad_exps, kept_snaps)
        _save_pkl(f"lieta_{tk}_p25_p50_1m",
                  f"Lieta {tk_upper} 25Δ Put IV / 50Δ Put IV (50Δ put 當 ATM 代理；dte 線性內插到 30 天，"
                  "不外推；lieta 的 atm_iv 是 VIX 型口徑不是 ATM，所以不用 atm 當分母；"
                  "與 gex put_25d/((put_50d+call_50d)/2) 同口徑)", ratio_p50, out_dir)
        _save_pkl(f"lieta_{tk}_p25_atm_1m",
                  f"Lieta {tk_upper} 25Δ Put IV / lieta atm_iv (dte 線性內插到 30 天，不外推；"
                  "lieta atm_iv 為 VIX 型口徑，不是 ATM，與 gex_spx_put_skew_1m 口徑不同，僅供參考)",
                  ratio, out_dir)
        _save_pkl(f"lieta_{tk}_p25_atm_1m_bucket",
                  f"Lieta {tk_upper} 25Δ Put IV / lieta atm_iv (dte {BUCKET_DTE_LO}–{BUCKET_DTE_HI} 各到期日比值平均，"
                  "atm 為 VIX 型口徑不是 ATM，驗收對照用)", bucket, out_dir)
        _save_pkl(f"lieta_{tk}_term_slope",
                  f"Lieta {tk_upper} ATM IV 9 天 − 90 天 (vol 點，dte 線性內插；atm 用 lieta atm_iv 原值，"
                  "VIX 型口徑不是 ATM；>0 = 前端高於後端 = 前端恐慌/倒掛)", slope, out_dir)
        if last_date:
            meta[ticker] = {"last_date": last_date,
                            "last_provisional": last_date in prov_dates,
                            "provisional_dates": prov_dates}
    if n_prov_rows:
        logger.warning(f"term_iv premarket=0 provisional rows: {n_prov_rows} "
                       f"({len(prov_dates_all)} dates) — 該 as-of 日還沒有 premarket=1 快照，"
                       "EOD 暫定點與 premarket 快照混在同一條線上")
    if meta:
        _save_json(TERM_META_NAME, {"generated_at": datetime.now().isoformat(timespec="seconds"),
                                    "tickers": meta}, out_dir)


def _export_sector_vol(conn, out_dir):
    """sector_vol → lieta_{xsd,xop}_iv（vol 點）／lieta_{xsd,xop}_ivpct（iv_percentile，0–1）。
    date 已是 as-of（回應 date 的前一交易日），本檔照抄。lieta 只給 2 位小數（iv 0.43 = 43 vol 點），
    解析度 1 vol 點；ticker 集合隨時間在 15／26／27 檔間變動，XSD／XOP 缺漏的日子該點跳過。"""
    if not _table_exists(conn, "sector_vol"):
        logger.info("sector_vol table not found, skip sector_vol series")
        return
    if conn.execute("SELECT 1 FROM sector_vol LIMIT 1").fetchone() is None:
        logger.info("sector_vol table is empty, skip sector_vol series")
        return
    names = {"XSD": "半導體", "XOP": "油氣探勘"}
    for ticker in SECTOR_TICKERS:
        rows = conn.execute(
            "SELECT date, iv_latest, iv_percentile FROM sector_vol "
            "WHERE UPPER(ticker)=? ORDER BY date", (ticker,)).fetchall()
        iv_data, pct_data = [], []
        for date_str, iv, pct in rows:
            dt = _to_dt(date_str)
            if dt is None:
                continue
            iv_f, pct_f = _to_float(iv), _to_float(pct)
            if iv_f is not None:
                iv_data.append([dt, iv_f * 100])  # 小數 → vol 點
            if pct_f is not None:
                pct_data.append([dt, pct_f])
        tk, tk_upper = ticker.lower(), ticker
        _warn_outliers(f"lieta_{tk}_iv", iv_data)
        _save_pkl(f"lieta_{tk}_iv",
                  f"Lieta {tk_upper}（{names[ticker]}）IV (vol 點；lieta 只給 2 位小數 = 解析度 1 vol 點)",
                  iv_data, out_dir)
        _save_pkl(f"lieta_{tk}_ivpct",
                  f"Lieta {tk_upper}（{names[ticker]}）IV 百分位 (0–1，lieta 原值；槓鈴輔助條件 > 0.8)",
                  pct_data, out_dir)


def _export_dsi(conn, out_dir):
    """trend_dsi → lieta_{t}_dsi_1w（score_1w）。date 不位移（回應 date）。"""
    if not _table_exists(conn, "trend_dsi"):
        logger.info("trend_dsi table not found, skip dsi series")
        return
    if conn.execute("SELECT 1 FROM trend_dsi LIMIT 1").fetchone() is None:
        logger.info("trend_dsi table is empty, skip dsi series")
        return
    for ticker in DSI_TICKERS:
        rows = conn.execute(
            "SELECT date, score_1w FROM trend_dsi WHERE UPPER(ticker)=? ORDER BY date",
            (ticker,)).fetchall()
        data = []
        for date_str, sc in rows:
            dt, v = _to_dt(date_str), _to_float(sc)
            if dt is not None and v is not None:
                data.append([dt, v])
        _save_pkl(f"lieta_{ticker.lower()}_dsi_1w",
                  f"Lieta {ticker} DSI 1W score (trend_dsi.score_1w；分數量化成幾個檔位，date 不位移)",
                  data, out_dir)


def _flow_deep_put_sql(conn):
    """深價外 put 的判斷式：優先用 fetcher 存的 is_deep_otm_put，舊 schema 沒這欄時退回 P 且 otm_pct > 10。
    otm_pct 正 = 價外（SPX 20000P 在現貨 7653 時為 −161，是深價內）。"""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(flow_top)")}
    if "is_deep_otm_put" in cols:
        return "is_deep_otm_put=1"
    return "(UPPER(option_type)='P' AND otm_pct>10)"


def _export_flow(conn, out_dir):
    """flow_top → (1) lieta_{spx,qqq}_deep_otm_put_premium：每個 query_date 深價外 put（OTM > 10%）
    權利金合計（百萬美元）；(2) data/lieta_flow_top.json：各 ticker 最新 query_date 的 premium 前 20 大。
    date = query_date（當日成交，underlying 為當日收盤附近），不位移。
    合計只含 fetcher 留存的深價外 put（premium 前 200 ∪ 深價外 put），即回應 limit 2000 內的全部深價外 put。"""
    if not _table_exists(conn, "flow_top"):
        logger.info("flow_top table not found, skip flow series")
        return
    if conn.execute("SELECT 1 FROM flow_top LIMIT 1").fetchone() is None:
        logger.info("flow_top table is empty, skip flow series")
        return
    deep = _flow_deep_put_sql(conn)
    keys = ["ticker", "option_type", "strike", "expiration", "dte", "otm_pct", "premium", "volume",
            "contract_direction", "is_deep_otm_put"]
    meta = {}
    for ticker in FLOW_TICKERS:
        rows = conn.execute(
            f"SELECT date, SUM(premium) FROM flow_top WHERE UPPER(query_ticker)=? AND {deep} "
            "GROUP BY date ORDER BY date", (ticker,)).fetchall()
        data = []
        for date_str, prem in rows:
            dt, v = _to_dt(date_str), _to_float(prem)
            if dt is not None and v is not None:
                data.append([dt, v / 1e6])
        _save_pkl(f"lieta_{ticker.lower()}_deep_otm_put_premium",
                  f"Lieta {ticker} 深價外 put（OTM > 10%）權利金合計 (百萬美元；flow 前 2000 筆內的深價外 put，date = query_date)",
                  data, out_dir)
        last = conn.execute(
            "SELECT MAX(date) FROM flow_top WHERE UPPER(query_ticker)=?", (ticker,)).fetchone()[0]
        if last is None:
            continue
        top = conn.execute(
            f"SELECT {', '.join(keys[:-1])}, {deep}, underlying_price FROM flow_top "
            "WHERE UPPER(query_ticker)=? AND date=? ORDER BY premium DESC, id LIMIT ?",
            (ticker, last, FLOW_TOP_N)).fetchall()
        prices = sorted(p for p in (_to_float(r[-1]) for r in top) if p is not None)
        meta[ticker] = {
            "query_date": str(last)[:10],
            "underlying_price": prices[len(prices) // 2] if prices else None,
            "rows": [dict(zip(keys, r[:-1])) for r in top],
        }
        for row in meta[ticker]["rows"]:
            row["is_deep_otm_put"] = int(row["is_deep_otm_put"] or 0)
    if meta:
        _save_json(FLOW_META_NAME, {"top_n": FLOW_TOP_N, "tickers": meta}, out_dir)


def fetch_lieta_eod_series(db_path=None, out_dir=None, vix_pkl=None):
    """Read goldmine eod_metrics.db and export lieta_* series as pkl (vx / screener / iv_rv / hist_skew / term_iv / sector_vol / dsi / flow)."""
    db_path = db_path or EOD_DB_PATH
    out_dir = out_dir or DATA_DIR
    if not os.path.exists(db_path):
        logger.warning(f"EOD metrics DB not found: {db_path}")
        return

    vix_pkl = vix_pkl or os.path.join(DATA_DIR, "series_cboe_VIX.pkl")
    vix_by_date = _load_pkl_by_date(vix_pkl)
    if vix_by_date is None:
        logger.warning(f"VIX pkl not found: {vix_pkl}, skip vx basis / contango")

    # goldmine 的 DB 只讀（mode=ro）
    conn = sqlite3.connect(f"{pathlib.Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    logger.info(f"Connected to {db_path}")
    try:
        _export_vx(conn, out_dir, vix_by_date)
        _export_screener(conn, out_dir)
        _export_ivrv(conn, out_dir)
        _export_skew(conn, out_dir)
        _export_term(conn, out_dir)
        _export_sector_vol(conn, out_dir)
        _export_dsi(conn, out_dir)
        _export_flow(conn, out_dir)
    finally:
        conn.close()
    logger.info("Lieta EOD series export complete")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="eod_metrics.db → data/lieta_*.pkl")
    ap.add_argument("--db", default=EOD_DB_PATH, help="eod_metrics.db 路徑")
    ap.add_argument("--out-dir", default=None, help="pkl 輸出目錄（預設 DATA_DIR）")
    ap.add_argument("--vix-pkl", default=None,
                    help="VIX 現貨 pkl（預設 DATA_DIR/series_cboe_VIX.pkl）")
    args = ap.parse_args()
    fetch_lieta_eod_series(args.db, args.out_dir, args.vix_pkl)
