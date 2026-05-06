import json
import os
import pickle
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from get_fed_series import fetch_and_save_fred_data, fetch_sofr_data
from get_m_square_chart import fetch_m_square_charts
from get_m_square_series import fetch_m_square_series
from get_m_square_etf import fetch_m_square_etfs
from get_ctfc_series import fetch_cftc_data, fetch_cftc_tff_data
from get_cboe_index import fetch_cboe_indices
from get_etf_csv import fetch_all as fetch_etf_csv
from get_nyfed_termpremium import fetch_nyfed_acm
from get_gex_series import fetch_gex_series
from get_cme_daily_volume import fetch_cme_daily_volume
from calc_pctrank import main as calc_pctrank
from line_notify import send_line_notification
from notify_macromicro_blog import run as check_macromicro_blog_new_posts

LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).resolve().parent / "data"

ERROR_HISTORY_FILE = LOGS_DIR / "error_history.json"
NFCI_LAST_SIGNAL_FILE = LOGS_DIR / "nfci_last_signal.json"

CONSECUTIVE_DAYS_THRESHOLD = 3

# ---------------------------------------------------------------------------
# 1. 執行所有抓取任務
# ---------------------------------------------------------------------------
tasks = [
    ("FRED STLFSI4", lambda: fetch_and_save_fred_data('STLFSI4')),
    ("FRED THREEFYTP10 (Kim-Wright Term Premium)", lambda: fetch_and_save_fred_data('THREEFYTP10')),
    ("FRED DGS2 (2Y Treasury)", lambda: fetch_and_save_fred_data('DGS2')),
    ("FRED T10Y2Y (10Y-2Y Spread)", lambda: fetch_and_save_fred_data('T10Y2Y')),
    ("FRED DFII10 (10Y Real Yield)", lambda: fetch_and_save_fred_data('DFII10')),
    ("FRED MMMFFAQ027S (MMF AUM)", lambda: fetch_and_save_fred_data('MMMFFAQ027S')),
    ("NY Fed SOFR (rate/percentiles)", fetch_sofr_data),
    ("MacroMicro charts", fetch_m_square_charts),
    ("MacroMicro series", fetch_m_square_series),
    ("MacroMicro ETFs", fetch_m_square_etfs),
    ("CFTC data", fetch_cftc_data),
    ("CFTC E-mini SPX TFF", fetch_cftc_tff_data),
    ("CBOE indices", fetch_cboe_indices),
    ("ETF fund flow (ProShares CSV)", fetch_etf_csv),
    ("NY Fed ACM Term Premium", fetch_nyfed_acm),
    ("GEX-lieta (SPX/SPY/VIX)", fetch_gex_series),
    ("CME daily_volume (OI+Volume)", fetch_cme_daily_volume),
    ("Percentile rank (all targets)", calc_pctrank),
]

failed = []
for name, func in tasks:
    try:
        logger.info(f"Starting: {name}")
        func()
        logger.info(f"Completed: {name}")
    except Exception as e:
        logger.error(f"Failed: {name} — {e}")
        failed.append(name)

if failed:
    logger.warning(f"Failed tasks: {', '.join(failed)}")
else:
    logger.info("All tasks completed successfully")

# ---------------------------------------------------------------------------
# 2. 記錄錯誤歷史，檢查連續 3 天失敗 → LINE 通知
# ---------------------------------------------------------------------------

def _load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_and_check_errors(today_failed: list[str]):
    today_str = date.today().isoformat()
    history: dict[str, list[str]] = _load_json(ERROR_HISTORY_FILE)
    history[today_str] = today_failed

    cutoff = (date.today() - timedelta(days=7)).isoformat()
    history = {d: v for d, v in history.items() if d >= cutoff}
    _save_json(ERROR_HISTORY_FILE, history)

    recent_days = sorted(history.keys(), reverse=True)[:CONSECUTIVE_DAYS_THRESHOLD]
    if len(recent_days) < CONSECUTIVE_DAYS_THRESHOLD:
        return

    tasks_in_all = None
    for d in recent_days:
        s = set(history[d])
        tasks_in_all = s if tasks_in_all is None else tasks_in_all & s
    if not tasks_in_all:
        return

    msg = (
        f"⚠️ 資料抓取連續 {CONSECUTIVE_DAYS_THRESHOLD} 天失敗\n"
        f"任務：{', '.join(sorted(tasks_in_all))}\n"
        f"日期：{recent_days[-1]} ~ {recent_days[0]}"
    )
    logger.warning(msg)
    send_line_notification(msg)


record_and_check_errors(failed)

# ---------------------------------------------------------------------------
# 3. NFCI 翻轉信號 (5696.REV1) 檢查 → LINE 通知
# ---------------------------------------------------------------------------

def _compute_rev_signal(series_id, window: int):
    """輕量版 REV 信號計算（與 highcharts_utils.process_rev 邏輯一致）。"""
    candidates = [
        DATA_DIR / f"series_{series_id}.pkl",
        DATA_DIR / f"fed_{series_id}.pkl",
        DATA_DIR / f"{series_id}.pkl",
    ]
    pkl_path = next((p for p in candidates if p.exists()), None)
    if pkl_path is None:
        logger.warning(f"找不到 series {series_id} 的 pkl 檔案")
        return None, None

    with open(pkl_path, "rb") as f:
        data = pickle.load(f)

    df = pd.DataFrame(data["data"], columns=["Date", "Value"])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")

    smoothed = df["Value"].rolling(window=window, min_periods=window).mean()
    slope = smoothed.diff()
    sign = np.sign(slope)
    sign_change = sign.diff()

    raw_signal = np.where(sign_change >= 2, 1, np.where(sign_change <= -2, -1, 0))

    cooldown = max(window // 2, 1)
    debounced = np.zeros_like(raw_signal)
    last_signal_idx = -cooldown - 1
    for i in range(len(raw_signal)):
        if raw_signal[i] != 0 and (i - last_signal_idx) > cooldown:
            debounced[i] = raw_signal[i]
            last_signal_idx = i

    valid_idx = smoothed.dropna().index
    df = df.loc[valid_idx]
    df["Signal"] = debounced[: len(df)]

    nonzero = df[df["Signal"] != 0]
    if nonzero.empty:
        return None, None
    last_date = nonzero.index[-1]
    last_signal = int(nonzero.iloc[-1]["Signal"])
    return last_date, last_signal


def check_nfci_signal():
    last_date, signal = _compute_rev_signal(5696, window=1)
    if last_date is None:
        logger.info("NFCI REV1: 無信號")
        return

    date_str = last_date.strftime("%Y-%m-%d")
    logger.info(f"NFCI REV1 最新信號: {signal:+d} @ {date_str}")

    if signal == 0:
        return

    state = _load_json(NFCI_LAST_SIGNAL_FILE)
    if state.get("date") == date_str and state.get("signal") == signal:
        logger.info("NFCI REV1: 已通知過，跳過")
        return

    direction = "金融環境開始收緊（從谷底翻上）" if signal == 1 else "金融環境開始放鬆（從峰頂翻下）"
    msg = f"📊 NFCI 翻轉信號 ({date_str})\n信號: {signal:+d} → {direction}"
    logger.info(msg)
    send_line_notification(msg)

    _save_json(NFCI_LAST_SIGNAL_FILE, {"date": date_str, "signal": signal})


check_nfci_signal()

# ---------------------------------------------------------------------------
# 4. MacroMicro 部落格新文章 → Gmail（失敗不影響上方任務結束）
# ---------------------------------------------------------------------------
try:
    logger.info("Starting: MacroMicro blog new-post email check")
    check_macromicro_blog_new_posts()
    logger.info("Completed: MacroMicro blog new-post email check")
except Exception as e:
    logger.error(f"Failed: MacroMicro blog new-post email check — {e}")
