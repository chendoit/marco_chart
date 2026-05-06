"""
LINE Bot 通知模組。

使用 LINE Messaging API 推送文字訊息。
需要 .env 設定 CHANNEL_ACCESS_TOKEN 和 TO_QUEEN。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_DIR = Path(__file__).resolve().parent
load_dotenv(_ENV_DIR / ".env")

logger = logging.getLogger(__name__)


def send_line_notification(message: str) -> None:
    """發送 LINE 推播通知。"""
    try:
        from linebot import LineBotApi
        from linebot.models import TextSendMessage

        token = os.getenv("CHANNEL_ACCESS_TOKEN")
        to_user = os.getenv("TO_QUEEN")

        if not token or not to_user:
            logger.warning("LINE Bot 未設定 (CHANNEL_ACCESS_TOKEN / TO_QUEEN)，跳過通知")
            return

        line_bot_api = LineBotApi(token)
        line_bot_api.push_message(to_user, TextSendMessage(text=message))
        logger.info("已發送 LINE 通知: %s", message[:80])
    except Exception as e:
        logger.error("LINE 通知發送失敗: %s", e)


def notify_macromicro_login_failure(script_name: str, error_message: str) -> None:
    """MacroMicro 登入失敗時推播（帳密錯誤、Cloudflare、表單找不到等）。"""
    text = f"[MacroMicro 登入失敗]\n腳本: {script_name}\n原因: {error_message}"
    send_line_notification(text)
