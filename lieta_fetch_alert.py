"""lieta EOD 抓取失敗告警：goldmine impulse/eod_metrics.db 的 fetch_log 連續 2 個交易日全部 failed 就通知。

規則（實作 WN §5-1）：
- 「一天」＝ fetch_log 裡有紀錄的一個 date；該日所有 status 都是 failed 才算失敗日。
  empty 不算失敗（一天只要有 empty 或 ok 就不算）；沒有紀錄的日子不算也不補。
- `*_asof` 端點（term_asof／sectorvol_asof／dsi_asof，永遠是 empty 的缺口紀錄）不納入判斷。
- 從最新有紀錄的日子往回數，連續失敗日 >= 2 即為一個事件（事件以連續失敗的起始日為鍵，
  失敗天數增加仍是同一個事件）。
- 同一事件一天只通知一次；狀態檔預設放 cron 專案 data/jobs/left-tail-eod/alert_state.json。
- 通知失敗只記 log，不丟例外；沒有任何管道送成功時不寫狀態（下次再試）。

用法（由 cron 任務 left-tail-eod 呼叫）：
    venv\\Scripts\\python.exe lieta_fetch_alert.py [--db PATH] [--state PATH]
最後一行 stdout 為 `ALERT status=<...> ...`；除非程式本身出錯，exit code 一律 0。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Callable

logger = logging.getLogger("lieta_fetch_alert")

DB_PATH = Path(r"C:\code\2026-09-09-new-lieta-goldmine\impulse\eod_metrics.db")
STATE_PATH = Path(r"C:\code\2026-10-01-cron-job-agent\data\jobs\left-tail-eod\alert_state.json")
MIN_STREAK = 2
JOB = "lieta_fetch_alert"
SUBJECT = "【左尾風險】lieta EOD 抓取連續失敗"

Sender = Callable[[str, str], None]  # (subject, 純文字內文)


def load_days(db_path: Path) -> list[dict] | None:
    """-> 依日期由新到舊的 [{date, statuses, failed:[(endpoint, ticker)], note}]；沒有資料庫／沒有表／空表回 None。"""
    if not Path(db_path).exists():
        return None
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True, timeout=10)
    try:
        rows = db.execute(
            "SELECT date, endpoint, ticker, status, note, fetched_at FROM fetch_log "
            "WHERE endpoint NOT LIKE '%\\_asof' ESCAPE '\\' ORDER BY date DESC").fetchall()
    except sqlite3.OperationalError as e:  # 沒有 fetch_log 表
        if "no such table" in str(e):
            return None
        raise
    finally:
        db.close()
    if not rows:
        return None
    by_day: dict[str, dict] = {}
    for d, endpoint, ticker, status, note, fetched_at in rows:
        day = by_day.setdefault(d, {"date": d, "statuses": set(), "failed": [], "note": None, "_at": ""})
        day["statuses"].add(status)
        if status == "failed":
            day["failed"].append((endpoint, ticker))
            if note and (fetched_at or "") >= day["_at"]:
                day["note"], day["_at"] = note, fetched_at or ""
    return [by_day[d] for d in sorted(by_day, reverse=True)]


def failed_streak(days: list[dict]) -> list[dict]:
    """由最新日往回數，連續「全部 failed」的日子（新到舊）。"""
    streak = []
    for day in days:
        if day["statuses"] != {"failed"}:
            break
        streak.append(day)
    return streak


def build_message(streak: list[dict]) -> str:
    newest, oldest = streak[0], streak[-1]
    endpoints = sorted({f"{e}/{t}" if t else e for day in streak for e, t in day["failed"]})
    note = next((d["note"] for d in streak if d["note"]), "（無 note）")
    return (f"lieta EOD 抓取連續 {len(streak)} 個交易日全部 failed（{oldest['date']} ~ {newest['date']}）。\n"
            f"失敗端點：{', '.join(endpoints)}\n"
            f"最近一筆 note：{note}\n"
            "可能是 JWT／登入過期（跑 goldmine login_lieta.py）、9333 被占用或 lieta 改版；"
            "看 goldmine impulse/fetch_eod_metrics_<日期>.log。")


def default_senders() -> list[Sender]:
    """沿用本 repo 的 line_notify（send_line_notification）與 gmail_smtp（send_html_email_from_env）。"""
    def line(subject: str, body: str) -> None:
        from line_notify import send_line_notification
        send_line_notification(f"{subject}\n{body}", job=JOB)

    def gmail(subject: str, body: str) -> None:
        from html import escape
        from gmail_smtp import send_html_email_from_env
        send_html_email_from_env(subject, "<p>" + escape(body).replace("\n", "<br>") + "</p>")

    return [line, gmail]


def _load_state(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _save_state(path: Path, state: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")
    os.replace(tmp, path)


def check_and_alert(db_path: Path = DB_PATH, state_path: Path = STATE_PATH,
                    senders: list[Sender] | None = None, today: date | None = None) -> dict:
    """-> {status, streak, event}；status：no_data／db_error／ok／alerted／already_alerted／send_failed。不丟例外。"""
    try:
        days = load_days(db_path)
    except Exception as e:  # 被鎖、檔案壞掉：不讓任務崩潰
        logger.error("讀 fetch_log 失敗：%s: %s", type(e).__name__, e)
        return {"status": "db_error", "streak": 0, "event": None}
    if days is None:
        return {"status": "no_data", "streak": 0, "event": None}
    streak = failed_streak(days)
    if len(streak) < MIN_STREAK:
        return {"status": "ok", "streak": len(streak), "event": None}

    event = streak[-1]["date"]
    day_key = (today or datetime.now().date()).isoformat()
    state = _load_state(state_path)
    if state.get("event") == event and state.get("notified_day") == day_key:
        return {"status": "already_alerted", "streak": len(streak), "event": event}

    message = build_message(streak)
    sent = 0
    for send in (senders if senders is not None else default_senders()):
        try:
            send(SUBJECT, message)
            sent += 1
        except Exception as e:
            logger.error("告警通知失敗（%s）：%s: %s", getattr(send, "__name__", send), type(e).__name__, e)
    if not sent:
        return {"status": "send_failed", "streak": len(streak), "event": event}
    try:
        _save_state(state_path, {"event": event, "notified_day": day_key, "streak": len(streak)})
    except OSError as e:
        logger.error("寫告警狀態檔失敗：%s", e)
    return {"status": "alerted", "streak": len(streak), "event": event}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    ap.add_argument("--state", type=Path, default=STATE_PATH)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s")
    r = check_and_alert(args.db, args.state)
    print(f"ALERT status={r['status']} streak={r['streak']} event={r['event']}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
