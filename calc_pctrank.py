# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
"""
集中式百分位計算腳本。

讀取 data/ 下的任意 pkl → 計算滾動歷史百分位 → 存為 {原名}_pctrank.pkl。
供 ChartModule 的 pctrank_id 機制讀取，在圖表標題動態附加 Nomura 風格百分位。

支援兩種 target：
  1. 字串 — 直接讀取 {name}.pkl
  2. dict  — expression，格式 {"id": "output_name", "expr": ("pkl1", "/", "pkl2")}
             先算兩個 pkl 的二元運算，再對結果算百分位

用法：
    python calc_pctrank.py          # 計算 PCTRANK_TARGETS 中所有項目
    python calc_pctrank.py series_id  # 計算指定 series
"""
import os
import re
import sys
import pickle

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

DATA_DIR = os.getenv("DATA_DIR")

MAX_WINDOW = 504  # 最多 2 年 lookback
MIN_POINTS = 20   # 至少 20 筆才開始算百分位

PCTRANK_TARGETS = [
    # Vol surface (from get_gex_series.py)
    "gex_spx_put_skew_3m",
    "gex_spx_skew_ratio_3m",
    "gex_spx_call_skew_3m",
    "gex_spx_put_skew_1m",
    "gex_spx_skew_ratio_1m",
    "gex_spx_term_slope",
    "gex_spx_iv30",
    "gex_spx_vrp_surface",
    # Gamma summary
    "gex_spx_net_gamma",
    "gex_spx_call_gamma",
    "gex_spx_put_gamma",
    "gex_spx_gamma_0dte",
    "gex_spx_gamma_non0dte",
    # VIX Gamma summary
    "gex_vix_net_gamma",
    "gex_vix_call_gamma",
    "gex_vix_put_gamma",
    # GEX levels
    "gex_spx_flip_distance",
    "gex_vix_flip_distance",
    # --- Phase 3: 既有圖表百分位 ---
    # CBOE
    "series_cboe_SKEW",
    "series_cboe_COR1M",
    "series_cboe_VIX",
    # MacroMicro (MOVE)
    "series_17581",
    # FRED
    "fed_DFII10",
    # NY Fed
    "series_nyfed_acmtp10",
    # CFTC E-mini
    "emini_spx_cme_net_position_asset_mgr",
    "emini_spx_cme_net_pct_of_oi_asset_mgr",
    # --- Expression targets ---
    # 格式: {"id": 輸出名稱, "expr": (pkl1, op, pkl2)}
    # pkl 名稱需完整對應 data/ 下的檔名（不含 .pkl）
    {"id": "expr_vvix_div_vix", "expr": ("series_22904", "/", "series_355")},
    {"id": "expr_vix_div_spx", "expr": ("series_355", "/", "series_2")},
    {"id": "expr_vix_div_vix3m", "expr": ("series_cboe_VIX", "/", "series_cboe_VIX3M")},
    {"id": "expr_bxm_div_spx", "expr": ("series_cboe_BXM", "/", "series_2")},
    {"id": "expr_put_div_spx", "expr": ("series_cboe_PUT", "/", "series_2")},
]


def _load_pkl(name):
    pkl_path = os.path.join(DATA_DIR, f"{name}.pkl")
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def _save_pkl(name, payload):
    pkl_path = os.path.join(DATA_DIR, f"{name}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump(payload, f)
    logger.info(f"Saved {len(payload.get('data', []))} records -> {pkl_path}")


_EXPR_OPS = {
    '-': lambda x, y: x - y,
    '+': lambda x, y: x + y,
    '*': lambda x, y: x * y,
    '/': lambda x, y: x / y if y != 0 else None,
}


def _compute_expression(pkl1_name, op, pkl2_name):
    """載入兩個 pkl，以 inner join（日期對齊）做二元運算，回傳 {'data': [...], 'title': ...}。"""
    d1 = _load_pkl(pkl1_name)
    d2 = _load_pkl(pkl2_name)
    map1 = {p[0]: p[1] for p in d1.get("data", []) if _is_valid_number(p[1])}
    map2 = {p[0]: p[1] for p in d2.get("data", []) if _is_valid_number(p[1])}
    common_dates = sorted(set(map1) & set(map2))
    func = _EXPR_OPS[op]
    op_sym = {'-': '-', '+': '+', '*': '×', '/': '÷'}[op]
    data = []
    for dt in common_dates:
        val = func(map1[dt], map2[dt])
        if val is not None and _is_valid_number(val):
            data.append([dt, val])
    return {
        "data": data,
        "title": f"{d1.get('title', pkl1_name)} {op_sym} {d2.get('title', pkl2_name)}",
    }


def _is_valid_number(v):
    """Check if v is a valid numeric value (not None, NaN, NaT, etc.)."""
    if v is None:
        return False
    try:
        return v == v  # NaN != NaN
    except (TypeError, ValueError):
        return False


def compute_pctrank(values, max_window=MAX_WINDOW, min_points=MIN_POINTS):
    """Compute rolling percent_rank for a list of (possibly None) values.

    percent_rank = count(window_values < current) / (window_size - 1)
    Returns list of same length with None where not computable.
    """
    result = []
    for i, val in enumerate(values):
        if not _is_valid_number(val):
            result.append(None)
            continue
        start = max(0, i - max_window + 1)
        window = [v for v in values[start:i + 1] if _is_valid_number(v)]
        if len(window) < min_points:
            result.append(None)
            continue
        rank = sum(1 for v in window if v < val)
        result.append(rank / (len(window) - 1))
    return result


def calc_pctrank_for(series_id):
    """Read {series_id}.pkl, compute pctrank, save {series_id}_pctrank.pkl."""
    try:
        data = _load_pkl(series_id)
    except FileNotFoundError:
        logger.warning(f"Source pkl not found: {series_id}.pkl — skipping")
        return False

    return _pctrank_from_data(data, series_id)


def calc_pctrank_for_expr(target):
    """Compute pctrank for an expression target (dict with 'id' and 'expr')."""
    out_id = target["id"]
    pkl1, op, pkl2 = target["expr"]
    try:
        data = _compute_expression(pkl1, op, pkl2)
    except FileNotFoundError as e:
        logger.warning(f"Expression pkl not found: {e} — skipping {out_id}")
        return False

    return _pctrank_from_data(data, out_id)


def _pctrank_from_data(data, out_id):
    """Shared logic: compute pctrank from data dict and save."""
    points = data.get("data", [])
    if not points:
        logger.warning(f"Empty data for {out_id} — skipping")
        return False

    values = [p[1] for p in points]
    pctranks = compute_pctrank(values)

    out_data = []
    for point, pr in zip(points, pctranks):
        if pr is not None:
            out_data.append([point[0], pr])

    _save_pkl(f"{out_id}_pctrank", {
        "title": f"{data.get('title', out_id)} %tile",
        "data": out_data,
    })

    if out_data:
        last_pctile = round(out_data[-1][1] * 100)
        logger.info(f"  {out_id}: latest = {last_pctile}%tile "
                     f"({len(out_data)} points)")
    return True


def main(targets=None):
    targets = targets or PCTRANK_TARGETS
    n_simple = sum(1 for t in targets if isinstance(t, str))
    n_expr = sum(1 for t in targets if isinstance(t, dict))
    logger.info(f"Computing pctrank for {n_simple} series + {n_expr} expressions...")
    ok, skip = 0, 0
    for t in targets:
        if isinstance(t, dict):
            success = calc_pctrank_for_expr(t)
        else:
            success = calc_pctrank_for(t)
        if success:
            ok += 1
        else:
            skip += 1
    logger.info(f"Done: {ok} computed, {skip} skipped")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1:])
    else:
        main()
