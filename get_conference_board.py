# -*- coding: utf-8 -*-
"""Conference Board ESF API（CB LEI/CEI），取代 M² sid 374/376 (WN-2026-09-22-A批 WP-A9)。

抓法沿用 `C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py` 的 `fetch_cb_bci()`
（已用 verify_mapped.py 驗證過）。流程：.conference-board.org sign-in → ESGagugeAction.cfm 取
SSO token → /api/auth/sso/exchange-token 換 JWT → POST /api/catalog/data。

帳密從本專案 `.env` 讀（`CONFERENCE_BOARD_ACCOUNT`/`CONFERENCE_BOARD_PW`，2026-09-15 gate G0
已加入）。PUBLIC_RESTRICTED tier 每次查詢只回最後 7 筆（約 7 個月），故歷史要用 ≤6 個月窗口
往回迭代 backfill，token 一次性、每個窗口都要重取。
"""
import os
import pickle
import time
from datetime import datetime, timedelta

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

CB_SSO_URL = "https://www.conference-board.org/data/datasubscription/ESGagugeAction.cfm"
CB_ESF_BASE = "https://esf.conferenceboard.esgauge.org/api"

# (sid, mnemonic, title)
CB_SERIES = [
    (374, "G0M910", "cb-leading-index"),
    (376, "G0M920", "cb-coincident-index"),
]


def _cb_get_jwt() -> str:
    """CB 官網登入 → ESGagugeAction SSO token → ESF JWT(token 一次性)。"""
    acc = os.getenv("CONFERENCE_BOARD_ACCOUNT", "")
    pw = os.getenv("CONFERENCE_BOARD_PW", "")
    if not acc or not pw:
        raise RuntimeError("CONFERENCE_BOARD_ACCOUNT/CONFERENCE_BOARD_PW not found in .env")
    s = requests.Session()
    r = s.post(
        "https://www.conference-board.org/signin/signincontroller.cfm",
        data={
            "username": acc,
            "password": pw,
            "pathInfo": "/signin/index.cfm?esgaugeUrl=https://esf.conferenceboard.esgauge.org",
            "remember": "true",
        },
        timeout=30,
    )
    r.raise_for_status()
    r = s.post(
        CB_SSO_URL,
        data={"Email": acc, "firstName": "doit", "lastName": "chendoit", "permission": ""},
        timeout=30,
    )
    r.raise_for_status()
    tok = r.json().get("token")
    if not tok:
        raise RuntimeError(f"CB SSO token fail: {r.text[:120]}")
    r = requests.post(f"{CB_ESF_BASE}/auth/sso/exchange-token", json={"token": tok}, timeout=30)
    r.raise_for_status()
    j = r.json()
    if not j.get("access_token"):
        raise RuntimeError(f"CB JWT fail: {j.get('message')}")
    return j["access_token"]


def _fetch_cb_bci(mnemonic: str) -> list:
    """PUBLIC tier 每查詢回最尾 7 筆 → 從最新往回以 6 個月窗口迭代抓全史。"""
    jwt = _cb_get_jwt()
    pts = {}
    end = datetime.today().date()
    start = end
    empty_streak = 0
    while empty_streak < 3 and start > datetime(1959, 1, 1).date():
        end = start
        start = start - timedelta(days=180)
        payload = {"mnemonics": [mnemonic], "dateFrom": start.isoformat(), "dateTo": end.isoformat()}
        r = requests.post(
            f"{CB_ESF_BASE}/catalog/data", json=payload, headers={"Authorization": f"Bearer {jwt}"}, timeout=30
        )
        r.raise_for_status()
        data = r.json()["indicators"][0]["data"]
        for x in data:
            pts[x["date"]] = float(x["value"])
        empty_streak = empty_streak + 1 if not data else 0
        time.sleep(0.3)
    if not pts:
        raise RuntimeError(f"CB {mnemonic}: no data")
    return [(datetime.strptime(k, "%Y-%m-%d").replace(day=1, hour=8), v) for k, v in sorted(pts.items())]


def _save_series(sid: int, title: str, obs: list):
    """逐日期 merge 存檔（同 get_yfinance_series.py／get_fred_csv.py 的防呆邏輯）。"""
    out_file = os.path.join(DATA_DIR, f"series_{sid}.pkl")
    old_data = []
    if os.path.exists(out_file):
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
    with open(out_file, "wb") as f:
        pickle.dump({"title": title, "data": [[d, v] for d, v in rows]}, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(rows)} (old n={len(old_data)}, new n={len(obs)})"
    )


def fetch_conference_board():
    """供 get_all_series_data.py 呼叫的入口。任一 series 失敗會彙整後 raise。"""
    failures = []
    for sid, mnemonic, title in CB_SERIES:
        name = f"Conference Board {mnemonic} (sid {sid})"
        try:
            logger.info(f"Starting: {name}")
            obs = _fetch_cb_bci(mnemonic)
            _save_series(sid, title, obs)
            logger.info(f"Completed: {name} (n={len(obs)})")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"Conference Board 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    fetch_conference_board()
