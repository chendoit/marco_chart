# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
# Complacency（WN-2026-10-24 左尾風險 §3.4）：本地自算，取代 lieta market/complacency 端點。
#   ratio = cboe_VVIX / cboe_VIX（同日內連接）；ma50 / sd50 = ratio 的 50 日滾動均值 / 標準差；
#   lower / upper = ma50 ∓ 1.67 * sd50；breakdown = ratio < lower（0/1）；breakout = ratio > upper（0/1，備用）。
# 與 goldmine 參考 CSV（complacency_20250101_20260916.csv）比對：同日對齊（lag 0）、sd 用 ddof=1（pandas 預設）最貼近。
import argparse
import os
import pickle
from datetime import datetime

import pandas as pd
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 日期檔日誌已集中設定於 log_config.py，本檔「禁止」再呼叫 logger.add()，
# 否則多個 sink 指向同一 log 檔，每筆訊息會重複寫入 N 次（2026-09 已踩過此坑）。

DATA_DIR = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)

WINDOW = 50
BAND_SD = 1.67


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


def _load_pkl_by_date(path):
    """讀 pkl，回傳 {date: float}；檔案不存在回傳 None。"""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        obj = pickle.load(f)
    return {d.date(): float(v) for d, v in obj["data"] if v is not None}


def compute_complacency(vvix_by_date, vix_by_date, window=WINDOW, band_sd=BAND_SD, ddof=1):
    """回傳依日期遞增的 [(date, ratio, ma, lower, upper, breakdown, breakout)]；
    前 window−1 天沒有均線，ma / bands / 標記為 None（ratio 照常有值）。"""
    dates = sorted(set(vvix_by_date) & set(vix_by_date))
    dates = [d for d in dates if vix_by_date[d] > 0]
    ratio = pd.Series([vvix_by_date[d] / vix_by_date[d] for d in dates], index=dates)
    ma = ratio.rolling(window).mean()
    sd = ratio.rolling(window).std(ddof=ddof)
    lower, upper = ma - band_sd * sd, ma + band_sd * sd
    out = []
    for d in dates:
        r = ratio[d]
        if ma[d] != ma[d]:  # NaN：窗口未滿
            out.append((d, r, None, None, None, None, None))
        else:
            out.append((d, r, ma[d], lower[d], upper[d],
                        1.0 if r < lower[d] else 0.0, 1.0 if r > upper[d] else 0.0))
    return out


def fetch_complacency_series(out_dir=None, data_dir=None):
    """Read cboe_VVIX / cboe_VIX pkl, export complacency_* pkl."""
    out_dir = out_dir or DATA_DIR
    data_dir = data_dir or DATA_DIR
    vvix = _load_pkl_by_date(os.path.join(data_dir, "series_cboe_VVIX.pkl"))
    vix = _load_pkl_by_date(os.path.join(data_dir, "series_cboe_VIX.pkl"))
    if vvix is None or vix is None:
        logger.warning(f"series_cboe_VVIX / series_cboe_VIX pkl not found in {data_dir}, skip complacency")
        return
    rows = compute_complacency(vvix, vix)

    def pts(i):
        return [[datetime.combine(r[0], datetime.min.time()).replace(hour=8), r[i]]
                for r in rows if r[i] is not None]

    _save_pkl("complacency_ratio", "Complacency Ratio (VVIX / VIX)", pts(1), out_dir)
    _save_pkl("complacency_ma50", f"Complacency Ratio {WINDOW} 日均線", pts(2), out_dir)
    _save_pkl("complacency_lower", f"Complacency 下緣 ({WINDOW}dma − {BAND_SD} SD)", pts(3), out_dir)
    _save_pkl("complacency_upper", f"Complacency 上緣 ({WINDOW}dma + {BAND_SD} SD)", pts(4), out_dir)
    _save_pkl("complacency_breakdown",
              "Complacency Breakdown (ratio < 下緣 = 1，否則 0)", pts(5), out_dir)
    _save_pkl("complacency_breakout",
              "Complacency Breakout (ratio > 上緣 = 1，否則 0)", pts(6), out_dir)
    logger.info("Complacency series export complete")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="cboe_VVIX / cboe_VIX → data/complacency_*.pkl")
    ap.add_argument("--out-dir", default=None, help="pkl 輸出目錄（預設 DATA_DIR）")
    ap.add_argument("--data-dir", default=None,
                    help="讀 series_cboe_VVIX.pkl / series_cboe_VIX.pkl 的目錄（預設 DATA_DIR）")
    args = ap.parse_args()
    fetch_complacency_series(args.out_dir, args.data_dir)
