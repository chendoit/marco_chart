"""
LINE Bot 通知模組。

使用 LINE Messaging API 推送文字訊息。
需要 .env 設定 CHANNEL_ACCESS_TOKEN 和 TO_QUEEN。

表頭規則與多專案共用範本一致（C:\\code\\2026-09-18-程式收集\\line-notify\\line_notify.py，
該檔 docstring 有完整說明）；本檔沿用 line-bot-sdk v2 (LineBotApi)。
所有訊息自動加上表頭，讓多專案共用同一個 LINE 帳號時能辨識來源：
    【MacroMicro-Data】get_all_series_data
    <原訊息>
    ─ 2026-09-27 08:21
專案名稱：.env 的 LINE_NOTIFY_PROJECT_NAME，否則取資料夾名去掉日期前綴。
功能名稱：呼叫時傳 job=...，否則取執行中的腳本檔名。
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

_ENV_DIR = Path(__file__).resolve().parent
load_dotenv(_ENV_DIR / ".env")

logger = logging.getLogger(__name__)

_LINE_TEXT_LIMIT = 5000  # LINE 單則文字訊息上限


def _project_name() -> str:
    name = (os.getenv("LINE_NOTIFY_PROJECT_NAME") or "").strip()
    return name or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", _ENV_DIR.name)


def _default_job() -> str:
    argv0 = sys.argv[0] if sys.argv else ""
    stem = Path(argv0).stem if argv0 and argv0 != "-c" else ""
    return stem or "python"


def format_message(message: str, job: str | None = None) -> str:
    """加上【專案】功能 表頭與發送時間；已含表頭（以「【」開頭）則不重複加。"""
    message = message.strip()
    if message.startswith("【"):
        return message[:_LINE_TEXT_LIMIT]
    header = f"【{_project_name()}】{job or _default_job()}"
    footer = f"─ {datetime.now():%Y-%m-%d %H:%M}"
    return f"{header}\n{message}\n{footer}"[:_LINE_TEXT_LIMIT]


def send_line_notification(message: str, job: str | None = None) -> None:
    """發送 LINE 推播通知。job 為功能名稱（省略時用腳本檔名）。"""
    try:
        from linebot import LineBotApi
        from linebot.models import TextSendMessage

        token = os.getenv("CHANNEL_ACCESS_TOKEN")
        to_user = os.getenv("TO_QUEEN")

        if not token or not to_user:
            logger.warning("LINE Bot 未設定 (CHANNEL_ACCESS_TOKEN / TO_QUEEN)，跳過通知")
            return

        text = format_message(message, job)
        line_bot_api = LineBotApi(token)
        line_bot_api.push_message(to_user, TextSendMessage(text=text))
        logger.info("已發送 LINE 通知: %s", text[:80])
    except Exception as e:
        logger.error("LINE 通知發送失敗: %s", e)


def notify_macromicro_login_failure(script_name: str, error_message: str) -> None:
    """MacroMicro 登入失敗時推播（帳密錯誤、Cloudflare、表單找不到等）。"""
    text = f"🔐 MacroMicro 登入失敗\n原因: {error_message}"
    send_line_notification(text, job=script_name)
