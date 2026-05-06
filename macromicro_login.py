"""MacroMicro 網站 Playwright 登入（共用於 series / chart / ETF 抓取腳本）。"""
from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DEFAULT_MACROMICRO_LOGIN_URL = "https://www.macromicro.me/login"


def _find_login_form(page):
    """登入表單僅有一個密碼欄位；註冊表單另有「確認密碼」。"""
    forms = page.locator("form")
    for i in range(forms.count()):
        f = forms.nth(i)
        if f.locator('input[type="password"]').count() != 1:
            continue
        if f.locator('input[type="email"], input[name="email"], input[autocomplete="username"]').count() < 1:
            continue
        return f
    return None


def _ensure_macromicro_session_impl(page):
    uid = (os.getenv("MACROMICRO_ID") or "").strip()
    pwd = (os.getenv("MACROMICRO_PASSWORD") or "").strip()
    if not uid or not pwd:
        raise RuntimeError("請在 .env 設定 MACROMICRO_ID 與 MACROMICRO_PASSWORD")

    login_url = (os.getenv("MACROMICRO_LOGIN_URL") or DEFAULT_MACROMICRO_LOGIN_URL).strip()
    logger.info("MacroMicro: 前往登入頁")
    page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2500)

    try:
        tab = page.get_by_role("tab", name="登入")
        if tab.count() > 0:
            tab.first.click(timeout=8000)
            page.wait_for_timeout(800)
    except Exception as e:
        logger.debug(f"MacroMicro: 無法或未找到「登入」分頁: {e}")

    login_form = _find_login_form(page)
    if login_form is not None:
        email_in = login_form.locator(
            'input[type="email"], input[name="email"], input[autocomplete="username"]'
        ).first
        email_in.fill(uid)
        login_form.locator('input[type="password"]').fill(pwd)
        btn = login_form.get_by_role("button", name=re.compile("登入"))
        if btn.count() == 0:
            btn = login_form.locator('button[type="submit"]')
        if btn.count() == 0:
            btn = login_form.locator('input[type="submit"]')
        btn.first.click(timeout=15000)
    else:
        if page.locator('input[type="email"]').count() == 0:
            raise RuntimeError(
                "MacroMicro 登入頁找不到 Email 表單（可能被 Cloudflare 擋下，請改 headless=False 或手動通過驗證）"
            )
        page.locator('input[type="email"]').first.fill(uid)
        page.locator('input[type="password"]').first.fill(pwd)
        page.get_by_role("button", name=re.compile("^登入$")).first.click(timeout=15000)

    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3500)
    path = urlparse(page.url).path.rstrip("/") or "/"
    if path == "/login":
        raise RuntimeError("MacroMicro 登入失敗（仍停留在登入頁，請檢查帳密）")

    logger.info("MacroMicro: 登入完成")


def ensure_macromicro_session(page, script_name: str = "MacroMicro"):
    """使用 .env 的 MACROMICRO_ID / MACROMICRO_PASSWORD 登入；失敗時發 LINE 通知再抛出例外。"""
    try:
        _ensure_macromicro_session_impl(page)
    except Exception as e:
        try:
            from line_notify import notify_macromicro_login_failure

            notify_macromicro_login_failure(script_name, str(e))
        except Exception as notify_err:
            logger.warning(f"MacroMicro 登入失敗 LINE 通知傳送失敗: {notify_err}")
        raise
