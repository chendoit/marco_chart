# pip install playwright==1.43.0
"""Fetch ETF close/volume/fund-flow data from MacroMicro.

Close & volume come from the intro_main API (page load).
Weekly net fund flow & cumulative fund flow come from the intro_netflow API
(triggered by clicking the "資金淨流量" tab).

ProShares-derived daily fund flow is separately handled by get_etf_csv.py.
"""
# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import pickle
import os
from datetime import datetime

from playwright.sync_api import sync_playwright
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

folder = os.getenv("DATA_DIR")
if not os.path.exists(folder):
    os.makedirs(folder)

logger.info(f"m平方 ETF data is saved to {folder}")

etf_list = [
    "VIXM",   # ProShares VIX Mid-Term Futures ETF
    "TQQQ",   # ProShares UltraPro QQQ (3x Nasdaq-100)
    "SQQQ",   # ProShares UltraPro Short QQQ (-3x Nasdaq-100)
    "SOXL",   # Direxion Daily Semiconductor Bull 3X
    "SOXS",   # Direxion Daily Semiconductor Bear 3X
    "UVXY",   # ProShares Ultra VIX Short-Term Futures ETF
    "SVXY",   # ProShares Short VIX Short-Term Futures ETF
]


def fetch_etf_data(page, ticker):
    """Visit ETF intro page and intercept the timeseries API response."""
    api_pattern = f"/api/etf/us/timeseries/intro_main/{ticker}"
    captured = {}

    def on_response(response):
        if api_pattern in response.url and response.status == 200:
            try:
                captured["data"] = response.json()
                logger.info(f"Captured API for {ticker}: {response.url}")
            except Exception as e:
                logger.error(f"Error parsing {ticker} API response: {e}")

    page.on("response", on_response)
    url = f"https://www.macromicro.me/etf/us/intro/{ticker}"
    logger.info(f"Fetching ETF page: {url}")
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(8000)
    page.remove_listener("response", on_response)

    if "data" not in captured:
        logger.error(f"Failed to capture API data for {ticker}")
        return False

    raw = captured["data"]
    if not raw.get("success"):
        logger.error(f"API returned failure for {ticker}")
        return False

    series_list = raw["data"]["series"]
    logger.info(f"{ticker}: {len(series_list)} total records from API")

    close_data = []
    volume_data = []
    for item in series_list:
        dt = datetime.strptime(item["date"], "%Y-%m-%d").replace(hour=8)
        if item["close"] is not None:
            close_data.append([dt, float(item["close"])])
        if item["volume"] is not None:
            volume_data.append([dt, float(item["volume"])])

    os.makedirs(folder, exist_ok=True)

    close_path = os.path.join(folder, f"series_etf_{ticker}_close.pkl")
    with open(close_path, "wb") as f:
        pickle.dump({"title": f"{ticker}-close", "data": close_data}, f)
    logger.info(f"Saved {len(close_data)} close records -> {close_path}")

    volume_path = os.path.join(folder, f"series_etf_{ticker}_volume.pkl")
    with open(volume_path, "wb") as f:
        pickle.dump({"title": f"{ticker}-volume", "data": volume_data}, f)
    logger.info(f"Saved {len(volume_data)} volume records -> {volume_path}")

    return True


def fetch_etf_fundflow(page, ticker):
    """Click '資金淨流量' tab and intercept the intro_netflow API.

    API: /api/etf/us/timeseries/intro_netflow/{ticker}?date_range=all
    Returns weekly data: {date, val (weekly net flow), accu_val (cumulative)}.
    """
    api_pattern = f"/api/etf/us/timeseries/intro_netflow/{ticker}"
    captured = {}

    def on_response(response):
        if api_pattern in response.url and response.status == 200:
            try:
                captured["data"] = response.json()
                logger.info(f"Captured netflow API for {ticker}: {response.url}")
            except Exception as e:
                logger.error(f"Error parsing {ticker} netflow API: {e}")

    page.on("response", on_response)

    tab = page.locator("text=資金淨流量").first
    if not tab.is_visible(timeout=3000):
        logger.warning(f"{ticker}: '資金淨流量' tab not found, skipping fund flow")
        page.remove_listener("response", on_response)
        return False

    tab.click()
    page.wait_for_timeout(8000)
    page.remove_listener("response", on_response)

    if "data" not in captured:
        logger.error(f"Failed to capture netflow API for {ticker}")
        return False

    raw = captured["data"]
    if not raw.get("success"):
        logger.error(f"Netflow API returned failure for {ticker}")
        return False

    series_list = raw["data"]["series"]
    logger.info(f"{ticker}: {len(series_list)} netflow records from API")

    flow_data = []
    flow_cum_data = []
    for item in series_list:
        dt = datetime.strptime(item["date"], "%Y-%m-%d").replace(hour=8)
        if item.get("val") is not None:
            flow_data.append([dt, float(item["val"])])
        if item.get("accu_val") is not None:
            flow_cum_data.append([dt, float(item["accu_val"])])

    os.makedirs(folder, exist_ok=True)

    flow_path = os.path.join(folder, f"series_etf_{ticker}_m2fundflow.pkl")
    with open(flow_path, "wb") as f:
        pickle.dump({"title": f"{ticker}-m2fundflow", "data": flow_data}, f)
    logger.info(f"Saved {len(flow_data)} weekly net flow records -> {flow_path}")

    cum_path = os.path.join(folder, f"series_etf_{ticker}_m2fundflow_cum.pkl")
    with open(cum_path, "wb") as f:
        pickle.dump({"title": f"{ticker}-m2fundflow-cumulative", "data": flow_cum_data}, f)
    logger.info(f"Saved {len(flow_cum_data)} cumulative flow records -> {cum_path}")

    return True


def _launch_browser(p):
    """Create a fresh browser + page with stealth settings."""
    browser = p.chromium.launch(
        headless=False,
        args=['--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()
    page.add_init_script(path="stealth.min.js")
    page.set_viewport_size({'width': 1024, 'height': 768})
    return browser, page


def fetch_m_square_etfs():
    """Fetch all ETFs in etf_list."""
    with sync_playwright() as p:
        browser, page = _launch_browser(p)

        for ticker in etf_list:
            try:
                success = fetch_etf_data(page, ticker)
                if not success:
                    logger.warning(f"Retrying fetch_etf_data({ticker}) with new browser...")
                    browser.close()
                    browser, page = _launch_browser(p)
                    fetch_etf_data(page, ticker)

                fetch_etf_fundflow(page, ticker)
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")

        browser.close()


if __name__ == "__main__":
    fetch_m_square_etfs()
