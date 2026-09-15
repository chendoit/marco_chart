"""Google / MacroMicro Playwright 登入（共用 storage state）。"""
from __future__ import annotations

import os
import re
import time
from urllib.parse import urlparse

from loguru import logger
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from google_session import (
    BROWSER_ARGS,
    DEFAULT_MACROMICRO_LOGIN_URL,
    GOOGLE_STORAGE_STATE,
    MACROMICRO_STORAGE_STATE,
)


def _storage_state_path(path) -> str | None:
    p = path if isinstance(path, os.PathLike) else None
    if p is None:
        return None
    return str(p) if p.exists() else None


def _launch_browser(playwright, *, headless: bool) -> Browser:
    return playwright.chromium.launch(headless=headless, args=BROWSER_ARGS)


def _new_context(browser: Browser, storage_state=None) -> BrowserContext:
    kwargs = {}
    state_path = _storage_state_path(storage_state)
    if state_path:
        kwargs["storage_state"] = state_path
    return browser.new_context(**kwargs)


def _save_storage_state(context: BrowserContext, path) -> None:
    context.storage_state(path=str(path))
    logger.info(f"已儲存 session: {path}")


def _is_google_logged_in(page: Page) -> bool:
    page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(1500)
    try:
        login_link = page.locator('a[aria-label="登入"]')
        if login_link.count() > 0 and login_link.first.is_visible():
            return False
    except Exception:
        pass
    # 英文介面
    try:
        sign_in = page.get_by_role("link", name=re.compile(r"Sign in|登入", re.I))
        if sign_in.count() > 0 and sign_in.first.is_visible():
            return False
    except Exception:
        pass
    return True


def check_google_login(*, headless: bool = True) -> bool:
    """檢查 google_storage_state.json 中的 Google session 是否仍有效。"""
    if not GOOGLE_STORAGE_STATE.exists():
        logger.error(f"找不到 {GOOGLE_STORAGE_STATE}")
        return False

    with sync_playwright() as playwright:
        browser = _launch_browser(playwright, headless=headless)
        try:
            context = _new_context(browser, GOOGLE_STORAGE_STATE)
            page = context.new_page()
            ok = _is_google_logged_in(page)
            logger.info("Google session 有效" if ok else "Google session 已失效")
            return ok
        finally:
            browser.close()


def _is_macromicro_logged_in(page: Page) -> bool:
    path = urlparse(page.url).path.rstrip("/") or "/"
    if path == "/login":
        return False
    return True


def _verify_macromicro_session(page: Page) -> bool:
    """前往 /login；已登入時通常會被導走。"""
    current = page.url
    page.goto(DEFAULT_MACROMICRO_LOGIN_URL, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2000)
    logged_in = _is_macromicro_logged_in(page)
    if not logged_in and current != page.url:
        page.goto("https://www.macromicro.me/", wait_until="domcontentloaded", timeout=60000)
    return logged_in


def _click_google_login(page: Page) -> None:
    google_link = page.locator('a.btn-login-gp[href="/login/google"]')
    if google_link.count() == 0:
        google_link = page.locator('a[href="/login/google"]')
    if google_link.count() == 0:
        raise RuntimeError("MacroMicro 登入頁找不到 Google 登入按鈕")
    google_link.first.click(timeout=15000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(2000)

    # 已登入 Google 時通常會自動選帳號或一鍵繼續
    for selector in [
        'div[data-email]',
        'div[data-identifier]',
        '[data-identifier]',
    ]:
        try:
            account = page.locator(selector)
            if account.count() > 0 and account.first.is_visible():
                account.first.click(timeout=5000)
                page.wait_for_timeout(1500)
                break
        except Exception:
            continue

    for btn_name in [re.compile(r"Continue|繼續|允許|Allow|同意|Accept", re.I)]:
        try:
            btn = page.get_by_role("button", name=btn_name)
            if btn.count() > 0:
                btn.first.click(timeout=8000)
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(2000)
        except Exception:
            continue

    page.wait_for_timeout(3000)


def _ensure_macromicro_session_impl(page: Page, *, save_state: bool = True) -> None:
    login_url = (os.getenv("MACROMICRO_LOGIN_URL") or DEFAULT_MACROMICRO_LOGIN_URL).strip()
    logger.info("MacroMicro: 前往登入頁（Google OAuth）")
    page.goto(login_url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2500)

    if _is_macromicro_logged_in(page):
        logger.info("MacroMicro: 已有有效 session")
        return

    try:
        tab = page.get_by_role("tab", name="登入")
        if tab.count() > 0:
            tab.first.click(timeout=8000)
            page.wait_for_timeout(800)
    except Exception as e:
        logger.debug(f"MacroMicro: 無法或未找到「登入」分頁: {e}")

    _click_google_login(page)

    deadline = time.time() + 60
    while time.time() < deadline:
        page.wait_for_timeout(1000)
        if _is_macromicro_logged_in(page):
            logger.info("MacroMicro: Google 登入完成")
            if save_state:
                _save_storage_state(page.context, MACROMICRO_STORAGE_STATE)
            return

    raise RuntimeError("MacroMicro Google 登入失敗（逾時或仍停留在登入頁）")


def ensure_macromicro_session(page: Page, script_name: str = "MacroMicro", *, save_state: bool = True) -> None:
    """以 Google OAuth 登入 MacroMicro；失敗時發 LINE 通知。"""
    try:
        _ensure_macromicro_session_impl(page, save_state=save_state)
    except Exception as e:
        try:
            from line_notify import notify_macromicro_login_failure

            notify_macromicro_login_failure(script_name, str(e))
        except Exception as notify_err:
            logger.warning(f"MacroMicro 登入失敗 LINE 通知傳送失敗: {notify_err}")
        raise


def create_macromicro_browser_context(
    playwright,
    *,
    headless: bool = False,
    prefer_cached: bool = True,
) -> tuple[Browser, BrowserContext, Page]:
    """建立已帶 session 的 browser/context/page。

    優先使用 macromicro_storage_state.json；否則載入 google_storage_state.json 並走 OAuth。
    """
    browser = _launch_browser(playwright, headless=headless)

    if prefer_cached and MACROMICRO_STORAGE_STATE.exists():
        logger.info("MacroMicro: 載入已儲存的 M² session")
        context = _new_context(browser, MACROMICRO_STORAGE_STATE)
        page = context.new_page()
        if _verify_macromicro_session(page):
            return browser, context, page
        logger.warning("MacroMicro: 已儲存 session 失效，改以 Google OAuth 重新登入")
        context.close()

    if not GOOGLE_STORAGE_STATE.exists():
        browser.close()
        raise RuntimeError(f"找不到 {GOOGLE_STORAGE_STATE}，請先匯出 Google session")

    logger.info("MacroMicro: 載入 Google session 準備 OAuth")
    context = _new_context(browser, GOOGLE_STORAGE_STATE)
    page = context.new_page()
    ensure_macromicro_session(page, save_state=True)
    return browser, context, page
