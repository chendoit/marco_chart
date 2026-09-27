# -*- coding: utf-8 -*-
"""TradingView Desktop 管線替代 fetcher（WN-2026-09-22-C批）。

來源：`C:/code/2026-04-05-tradingview-control/tv_daily_export.py`（TVC:DE10Y、
INDEX:S5FI/S5TH 等 symbol，經 CDP 連 TradingView Desktop 抓 OHLCV）產出的
`tv_export/*.pkl`，本檔只負責讀那份 pkl、merge 進本專案的 `data/series_<sid>.pkl`。

**不連 TradingView**：`tv_daily_export.py` 要先手動（或未來排程）在
`2026-04-05-tradingview-control` 專案那邊跑過一次，這裡才有檔案可讀；
沒有 tv_export pkl 時視為該項失敗（不擋其他任務）。

驗證數字（與舊 pkl 重疊天數比較，見 WN-2026-09-22-C批）：
  1916  germany-bond-10-year          中位差 0.18%（取代 ECB 歐元區代打的 11.5% approx）
  4448  de-10-year-yield-spread       中位差 2.14%（同上，取代 approx）
  18331 sp500-50ma-breadth            中位差 0.000%（取代口徑錯的指數vs自身均線版）
  22718 sp-500-200ma-breadth          中位差 0.000%（取代 curl_cffi 爬蟲版，偏差曾達 6.85%）

8219（WTI 現貨）也測過 TVC:USOIL，中位差 2.13% 反而比現行 CL=F 的 1.78% 差，
故意不放進這裡，維持 get_yfinance_series.py 的 CL=F 方案。

存檔邏輯採逐日期 merge（同日期新值覆蓋，其餘舊點全保留），與 get_yfinance_series.py
同一套「不能整批覆寫」的防呆理由：tv_export 只有 TradingView 免費帳號約 300 根日線
（約一年），遠短於本專案深歷史（1916/4448 回溯到 1979，18331/22718 回溯到 1990），
整批覆寫會把重疊窗口外的舊歷史默默丟掉。
"""
import os
import pickle
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

import log_config  # noqa: F401

DATA_DIR = os.getenv("DATA_DIR")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

TV_EXPORT_DIR = Path("C:/code/2026-04-05-tradingview-control/tv_export")

# sid -> (tv_export pkl 檔名, 沿用舊 pkl 的 title)
JOBS = {
    1916: ("tv_TVC-DE10Y_D.pkl", "germany-bond-10-year"),
    4448: ("tv_DE-US-10Y-spread_D.pkl", "de-10-year-yield-spread-germany-us"),
    18331: ("tv_INDEX-S5FI_D.pkl", "sp500-50ma-breadth"),
    22718: ("tv_INDEX-S5TH_D.pkl", "sp-500-200ma-breadth"),
}


def _save_series(sid: int, title: str, obs: list):
    """逐日期 merge 存檔：新舊資料以日期 union，同日期新值覆蓋，其餘舊點全保留。
    `lost`（union 後仍缺失的舊日期）理論上必為空集合，用 assert 當防呆而非事後檢查。"""
    out_file = Path(DATA_DIR) / f"series_{sid}.pkl"
    old_data = []
    if out_file.exists():
        try:
            with open(out_file, "rb") as f:
                old = pickle.load(f)
            old_data = old.get("data", []) if isinstance(old, dict) else []
        except Exception:
            old_data = []
    merged = {d.date(): (d, v) for d, v in old_data}
    merged.update({d.date(): (d, v) for d, v in obs})
    lost = set(d.date() for d, v in old_data) - set(merged)
    assert not lost, f"series_{sid}: 資料倒退！遺失 {len(lost)} 個舊日期: {sorted(lost)[:5]}"
    rows = sorted(merged.values(), key=lambda x: x[0])
    data = {"title": title, "data": [[d, v] for d, v in rows]}
    with open(out_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(rows)} (old n={len(old_data)}, new n={len(obs)}) "
        f"range={rows[0][0]:%Y-%m-%d}~{rows[-1][0]:%Y-%m-%d}"
    )


def _load_tv_export(filename: str) -> list:
    path = TV_EXPORT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} 不存在 — 先在 2026-04-05-tradingview-control 專案跑一次 "
            f"tv_daily_export.py（需 TradingView Desktop + CDP 9222）"
        )
    with open(path, "rb") as f:
        tv = pickle.load(f)
    return [(datetime(d.year, d.month, d.day, 8, 0), v) for d, v in tv["data"]]


def fetch_tradingview_series():
    """供 get_all_series_data.py 呼叫的入口。任一項失敗會彙整後 raise。"""
    failures = []
    for sid, (filename, title) in JOBS.items():
        name = f"tradingview {sid} ({filename})"
        try:
            logger.info(f"Starting: {name}")
            obs = _load_tv_export(filename)
            _save_series(sid, title, obs)
            logger.info(f"Completed: {name} (n={len(obs)})")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"tradingview 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    fetch_tradingview_series()
