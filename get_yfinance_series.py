# -*- coding: utf-8 -*-
"""Yahoo Finance chart API 替代 fetcher（WN-2026-09-22-A批 WP-A2，14 條）。

來源評估、tickers、驗證數字見 `C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py`
的 `fetch_yf()`/`fetch_yf_spread()`（已用 `verify_mapped.py` 驗證過）。

存檔邏輯採逐日期 merge（同日期新值覆蓋，其餘舊點全保留），**不能**用本專案其他腳本常見的整批
覆寫慣例：實測發現 Yahoo chart API 對好幾個 ticker（例如 AUDUSD=X、BTC-USD）能回溯的歷史範圍
比舊 M² pkl 短很多（M² 的起始日期早了數十年），若整批覆寫，新資料筆數雖然遠多於舊資料（daily
vs 舊資料的稀疏抽樣）、筆數防呆完全抓不到，但實際上會把舊資料裡新來源沒有的那段早期歷史默默
丟掉——正是 WN-2026-09-22-A批計畫 §1.2 開頭就在防的「無腦覆寫資料倒退」問題。
"""
import os
import pickle
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 日期檔日誌已集中設定於 log_config.py，本檔「禁止」再呼叫 logger.add()，
# 否則多個 sink 指向同一 log 檔，每筆訊息會重複寫入 N 次（2026-09 已踩過此坑）。

DATA_DIR = os.getenv("DATA_DIR")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# sid -> (yfinance ticker, 舊 pkl title，沿用既有命名不變)
TICKERS = {
    2: ("^GSPC", "sp500"),
    486: ("CL=F", "crude-oil-futures"),
    483: ("DX-Y.NYB", "us-dollar-index"),
    562: ("EURUSD=X", "fx-eur-usd"),
    385: ("USDJPY=X", "fx-usd-jpy"),
    745: ("AUDUSD=X", "fx-aud-usd"),
    386: ("USDCAD=X", "fx-usd-cad"),
    621: ("TWD=X", "fx-usd-twd"),
    485: ("GC=F", "gold-futures"),
    1281: ("^N225", "japan-nikkei225"),
    4249: ("BTC-USD", "bitcoin-usd"),
    7145: ("AUDJPY=X", "fx-aud-jpy"),
    7146: ("AUDNZD=X", "fx-aud-nzd"),
}
RATIO_SID = 4481  # 銅金比：HG=F * 100 / GC=F，沿用舊 pkl 的 0.1x 量級（不是單純比值）
RATIO_TITLE = "coppergold"


def _yf_chart(symbol: str) -> dict:
    """symbol -> {YYYY-MM-DD: close}，period1=0 取得全部可得歷史。"""
    s = urllib.parse.quote(symbol, safe="")
    r = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{s}",
        params={"interval": "1d", "period1": 0, "period2": int(time.time())},
        headers=HDRS,
        timeout=30,
    )
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    ts = result.get("timestamp") or []
    close = result["indicators"]["quote"][0].get("close") or []
    out = {}
    for t, v in zip(ts, close):
        if v is None:
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc)
        out[datetime(d.year, d.month, d.day, 8, 0).strftime("%Y-%m-%d")] = float(v)
    return out


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


def _fetch_close(ticker: str) -> list:
    pts = _yf_chart(ticker)
    return [(datetime.strptime(d, "%Y-%m-%d").replace(hour=8), round(v, 4)) for d, v in sorted(pts.items())]


def _fetch_coppergold() -> list:
    hg = _yf_chart("HG=F")
    gc = _yf_chart("GC=F")
    common = sorted(set(hg) & set(gc))
    return [
        (datetime.strptime(d, "%Y-%m-%d").replace(hour=8), round(hg[d] * 100.0 / gc[d], 4))
        for d in common
        if gc[d]
    ]


def fetch_yfinance_series():
    """供 get_all_series_data.py 呼叫的入口。任一抓取失敗會彙整後 raise。"""
    failures = []
    for sid, (ticker, title) in TICKERS.items():
        name = f"yfinance {sid} ({ticker})"
        try:
            logger.info(f"Starting: {name}")
            obs = _fetch_close(ticker)
            _save_series(sid, title, obs)
            logger.info(f"Completed: {name} (n={len(obs)})")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
        time.sleep(0.2)
    try:
        name = f"yfinance {RATIO_SID} (coppergold)"
        logger.info(f"Starting: {name}")
        obs = _fetch_coppergold()
        _save_series(RATIO_SID, RATIO_TITLE, obs)
        logger.info(f"Completed: {name} (n={len(obs)})")
    except Exception as e:
        logger.error(f"Failed: {name} — {e}")
        failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"yfinance 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    fetch_yfinance_series()
