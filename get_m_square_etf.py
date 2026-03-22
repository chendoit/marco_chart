# pip install playwright==1.43.0
"""Fetch ETF close/volume data from MacroMicro.

Fund flow data is now handled by get_etf_csv.py (ProShares official CSV).
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
    "VIXM",  # ProShares VIX Mid-Term Futures ETF
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


def fetch_m_square_etfs():
    """Fetch all ETFs in etf_list."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.new_page()
        page.add_init_script(path="stealth.min.js")
        page.set_viewport_size({'width': 1024, 'height': 768})

        for ticker in etf_list:
            try:
                success = fetch_etf_data(page, ticker)
                if not success:
                    logger.warning(f"Retrying fetch_etf_data({ticker}) with new browser...")
                    browser.close()
                    browser = p.chromium.launch(
                        headless=False,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    page = browser.new_page()
                    page.add_init_script(path="stealth.min.js")
                    page.set_viewport_size({'width': 1024, 'height': 768})
                    fetch_etf_data(page, ticker)
            except Exception as e:
                logger.error(f"Error in fetch_etf_data({ticker}): {e}")

        browser.close()


if __name__ == "__main__":
    fetch_m_square_etfs()
