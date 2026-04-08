# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
"""Fetch daily volume + OI from CME FTP and produce pkl time series.

CME anti-scraping requires Playwright headless=False + account login.
Uses persistent browser context to reuse login session across runs.

Standalone:
    python get_cme_daily_volume.py                  # latest missing dates (interactive login)
    python get_cme_daily_volume.py --backfill 90    # last 90 calendar days
    python get_cme_daily_volume.py --rebuild-pkl    # rebuild pkl from downloaded xlsx only

Orchestrator:
    from get_cme_daily_volume import fetch_cme_daily_volume
    # Non-interactive: skips download if no valid CME session; always rebuilds pkl.
"""
import argparse
import base64
import datetime
import os
import pickle
import re
import sys
import io
import time
from pathlib import Path

import pandas as pd
import requests
from loguru import logger
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from line_notify import send_line_notification

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
XLSX_DIR = DATA_DIR / "cme_daily_volume"
BROWSER_PROFILE_DIR = Path(__file__).resolve().parent / ".cme_browser_profile"
CME_FTP_URL = "https://www.cmegroup.com/ftp/daily_volume/"
LOGIN_SIGNAL_FILE = Path(__file__).resolve().parent / ".cme_login_ready"

XLSX_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTS = {
    "6J": {"clearing_code": "J1", "exchange_pat": "Chicago Mercantile Exchange", "exchange_code": "xcme", "desc": "Japanese Yen"},
    "6E": {"clearing_code": "EC", "exchange_pat": "Chicago Mercantile Exchange", "exchange_code": "xcme", "desc": "Euro FX"},
    "6A": {"clearing_code": "AD", "exchange_pat": "Chicago Mercantile Exchange", "exchange_code": "xcme", "desc": "Australian Dollar"},
    "CL": {"clearing_code": "CL", "exchange_pat": "NYMEX",                       "exchange_code": "xnym", "desc": "WTI Crude Oil"},
    "ES": {"clearing_code": "ES", "exchange_pat": "Chicago Mercantile Exchange", "exchange_code": "xcme", "desc": "E-mini S&P 500"},
    "NQ": {"clearing_code": "NQ", "exchange_pat": "Chicago Mercantile Exchange", "exchange_code": "xcme", "desc": "E-mini Nasdaq 100"},
}

DOWNLOAD_DELAY_SEC = 2.0


def list_remote_dates() -> list[str]:
    """Parse CME FTP directory listing HTML to get available YYYYMMDD date strings.

    The directory page itself is accessible without login; only file downloads
    are protected by anti-scraping.
    """
    resp = requests.get(CME_FTP_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    dates = sorted(set(re.findall(r"daily_volume_(\d{8})\.xlsx", resp.text)))
    if dates:
        logger.info(f"CME FTP: {len(dates)} xlsx files available ({dates[0]}~{dates[-1]})")
    else:
        logger.warning("CME FTP: no xlsx files found in directory listing")
    return dates


def list_local_dates() -> set[str]:
    """Return set of YYYYMMDD strings already downloaded locally."""
    pattern = re.compile(r"daily_volume_(\d{8})\.xlsx$")
    return {m.group(1) for f in XLSX_DIR.iterdir() if (m := pattern.match(f.name))}


def _list_dates_from_page(page) -> list[str]:
    """Parse available YYYYMMDD dates from the Playwright page content."""
    dates = sorted(set(re.findall(r"daily_volume_(\d{8})\.xlsx", page.content())))
    if dates:
        logger.info(f"CME FTP (browser): {len(dates)} files ({dates[0]}~{dates[-1]})")
    else:
        logger.warning("CME FTP (browser): no xlsx files found in page")
    return dates


_JS_FETCH_BASE64 = """
async (url) => {
    const resp = await fetch(url, {credentials: 'include'});
    if (!resp.ok) return {error: resp.status};
    const buf = await resp.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return {data: btoa(binary)};
}
"""


def _download_one_xlsx(page, date_str: str) -> bool:
    """Download a single xlsx via page.evaluate(fetch) and save locally."""
    url = f"{CME_FTP_URL}daily_volume_{date_str}.xlsx"
    dest = XLSX_DIR / f"daily_volume_{date_str}.xlsx"
    if dest.exists():
        return True

    try:
        result = page.evaluate(_JS_FETCH_BASE64, url)
        if "error" in result:
            logger.warning(f"CME download {date_str}: HTTP {result['error']}")
            return False
        raw = base64.b64decode(result["data"])
        dest.write_bytes(raw)
        logger.info(f"Downloaded daily_volume_{date_str}.xlsx ({len(raw):,} bytes)")
        return True
    except Exception as e:
        logger.error(f"CME download {date_str} failed: {e}")
        return False


def _wait_for_login(page):
    """Open CME in browser; create signal file and wait for user to delete it after login."""
    page.goto("https://www.cmegroup.com/", wait_until="domcontentloaded", timeout=30_000)

    LOGIN_SIGNAL_FILE.write_text(
        "CME browser is open.\n"
        "1. Log in to your CME account in the browser window.\n"
        "2. DELETE this file to continue the download.\n",
        encoding="utf-8",
    )
    logger.info(f"Waiting for CME login — delete {LOGIN_SIGNAL_FILE.name} when done.")

    while LOGIN_SIGNAL_FILE.exists():
        time.sleep(2)

    logger.info("Login signal received, navigating back to FTP directory...")
    try:
        page.goto(CME_FTP_URL, wait_until="domcontentloaded", timeout=60_000)
        time.sleep(3)
        logger.info(f"Post-login page URL: {page.url}")
    except Exception as e:
        logger.error(f"Failed to navigate to FTP directory after login: {e}")
        raise


def _check_session_valid(page) -> tuple[bool, list[str]]:
    """Navigate to FTP directory; return (can_download, available_dates)."""
    try:
        page.goto(CME_FTP_URL, wait_until="domcontentloaded", timeout=30_000)
    except Exception:
        return False, []
    time.sleep(1)

    dates = _list_dates_from_page(page)
    if not dates:
        return False, []

    test_url = f"{CME_FTP_URL}daily_volume_{max(dates)}.xlsx"
    js = "async (url) => { const r = await fetch(url, {credentials:'include'}); return r.ok; }"
    try:
        can_dl = page.evaluate(js, test_url)
    except Exception:
        can_dl = False
    return can_dl, dates


def download_dates(
    dates_to_download: list[str] | None = None,
    *,
    backfill_days: int = 7,
    interactive: bool = True,
) -> tuple[int, int, str]:
    """Download xlsx files using Playwright persistent context.

    If *dates_to_download* is ``None``, the function lists available dates from
    the browser session and calculates missing ones automatically.  This avoids
    needing a separate ``requests``-based directory listing (which CME blocks).

    Returns ``(success_count, fail_count, skip_reason)``.
    *skip_reason* is empty when downloads were attempted.
    """
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 720},
        )
        page = context.pages[0] if context.pages else context.new_page()

        session_ok, remote = _check_session_valid(page)

        if dates_to_download is None:
            local = list_local_dates()
            cutoff = (
                datetime.date.today() - datetime.timedelta(days=backfill_days)
            ).strftime("%Y%m%d")
            dates_to_download = [d for d in remote if d >= cutoff and d not in local]
            logger.info(f"Missing dates (since {cutoff}): {len(dates_to_download)}")

        if not dates_to_download:
            logger.info("No dates to download.")
            context.close()
            return 0, 0, ""

        if not session_ok:
            if interactive:
                try:
                    _wait_for_login(page)
                except Exception as e:
                    logger.error(f"Login/navigation failed: {e}")
                    context.close()
                    return 0, 0, f"login failed: {e}"
            else:
                reason = "session invalid (non-interactive)"
                logger.warning(f"CME {reason} — run script directly for initial login.")
                context.close()
                return 0, 0, reason

        logger.info(f"Downloading {len(dates_to_download)} xlsx files from CME FTP...")
        logger.info(f"Dates: {dates_to_download}")
        success, fail = 0, 0
        for i, date_str in enumerate(dates_to_download):
            logger.info(f"[{i+1}/{len(dates_to_download)}] Fetching {date_str}...")
            if _download_one_xlsx(page, date_str):
                success += 1
            else:
                fail += 1
            if i < len(dates_to_download) - 1:
                time.sleep(DOWNLOAD_DELAY_SEC)

        context.close()
    logger.info(f"CME download complete: {success} ok, {fail} failed")
    return success, fail, ""


# ---------------------------------------------------------------------------
# xlsx parsing → pkl
# ---------------------------------------------------------------------------

def parse_xlsx(filepath: Path) -> dict[str, dict]:
    """Parse one daily_volume xlsx; aggregate futures Volume + OI per product.

    Handles the current CME FTP format (second sheet "CME Group Vol and OI by
    Product", clearing codes, trade date in header area).

    Returns ``{product_code: {"volume": float, "oi": float, "date": datetime}}``.
    """
    try:
        sheets = pd.read_excel(filepath, sheet_name=None, header=None, engine="openpyxl")
    except Exception as e:
        logger.error(f"Failed to read {filepath.name}: {e}")
        return {}

    detail_sheet = None
    for name, sheet_df in sheets.items():
        if "by product" in name.lower():
            detail_sheet = sheet_df
            break
    if detail_sheet is None:
        detail_sheet = list(sheets.values())[-1]

    trade_date = None
    header_row = None
    for i, row in detail_sheet.iterrows():
        row_str = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        if "trade date" in row_str.lower():
            m = re.search(r"(\d{2}/\d{2}/\d{4})", row_str)
            if m:
                try:
                    trade_date = pd.to_datetime(m.group(1), format="%m/%d/%Y")
                except ValueError:
                    trade_date = pd.to_datetime(m.group(1), format="%d/%m/%Y")
        first_val = str(row.iloc[0]).lower().replace("\n", " ") if pd.notna(row.iloc[0]) else ""
        if "description" in first_val or "commodity" in first_val:
            header_row = i
            break

    if header_row is None:
        logger.warning(f"Cannot find header row in {filepath.name}")
        return {}

    df = detail_sheet.iloc[header_row:].copy()
    df.columns = [str(c).replace("\n", " ").strip() for c in df.iloc[0]]
    df = df.iloc[1:].reset_index(drop=True)

    col_map: dict[str, str] = {}
    for c in df.columns:
        cl = c.lower()
        if "commodity" in cl and "indicator" in cl:
            col_map["product_code"] = c
        elif "exchange" in cl and "name" in cl:
            col_map["exchange"] = c
        elif "future" in cl and ("option" in cl or "indicator" in cl):
            col_map["fut_opt"] = c
        elif "open" in cl and "interest" in cl:
            col_map["oi"] = c
        elif "total" in cl and "volume" in cl:
            col_map["volume"] = c

    required = {"product_code", "exchange", "fut_opt", "volume"}
    if not required.issubset(col_map.keys()):
        logger.warning(f"Missing columns in {filepath.name}: {required - col_map.keys()}")
        return {}

    mask = df[col_map["fut_opt"]].astype(str).str.strip().str.upper() == "F"
    df_fut = df[mask]

    if trade_date is None:
        m = re.search(r"(\d{8})", filepath.name)
        if m:
            trade_date = pd.to_datetime(m.group(1), format="%Y%m%d")
        else:
            logger.warning(f"Cannot determine trade date from {filepath.name}")
            return {}

    result = {}
    for code, spec in PRODUCTS.items():
        clearing = spec["clearing_code"]
        prod_mask = (
            (df_fut[col_map["product_code"]].astype(str).str.strip() == clearing)
            & df_fut[col_map["exchange"]].astype(str).str.contains(spec["exchange_pat"], case=False)
        )
        sub = df_fut[prod_mask]
        if sub.empty:
            continue

        total_vol = pd.to_numeric(sub[col_map["volume"]], errors="coerce").sum()
        total_oi = 0.0
        if "oi" in col_map:
            total_oi = pd.to_numeric(sub[col_map["oi"]], errors="coerce").sum()

        result[code] = {
            "volume": float(total_vol),
            "oi": float(total_oi),
            "date": trade_date.replace(hour=8),
        }

    return result


def build_pkl_series():
    """Rebuild pkl time series from all downloaded xlsx files."""
    xlsx_files = sorted(XLSX_DIR.glob("daily_volume_*.xlsx"))
    if not xlsx_files:
        logger.warning(f"No xlsx files found in {XLSX_DIR}")
        return

    logger.info(f"Rebuilding pkl from {len(xlsx_files)} xlsx files...")

    series: dict[str, dict[str, list]] = {
        code: {"volume": [], "oi": []} for code in PRODUCTS
    }

    for f in xlsx_files:
        parsed = parse_xlsx(f)
        for code, vals in parsed.items():
            series[code]["volume"].append([vals["date"], vals["volume"]])
            series[code]["oi"].append([vals["date"], vals["oi"]])

    count = 0
    for code, spec in PRODUCTS.items():
        for field in ("volume", "oi"):
            data = sorted(series[code][field], key=lambda x: x[0])
            if not data:
                continue
            seen: dict = {}
            for row in data:
                seen[row[0]] = row[1]
            data = [[dt, val] for dt, val in seen.items()]
            result = {
                "title": f"CME {spec['desc']} Daily {field.upper()}",
                "data": data,
            }
            pkl_name = f"cme_daily_{code.lower()}_{spec['exchange_code']}_{field}.pkl"
            pkl_path = DATA_DIR / pkl_name
            with open(pkl_path, "wb") as fh:
                pickle.dump(result, fh)
            logger.info(f"Saved {pkl_name} ({len(data)} points)")
            count += 1

    logger.info(f"Built {count} pkl files from {len(xlsx_files)} xlsx")


# ---------------------------------------------------------------------------
# entry points
# ---------------------------------------------------------------------------

def fetch_cme_daily_volume():
    """Orchestrator entry: download latest missing dates (non-interactive) + rebuild pkl.

    Tries ``requests`` first for a quick directory listing.  If that fails
    (CME anti-scraping 403), falls back to Playwright which uses the stored
    browser session / cookies.  If no valid session exists, download is
    skipped but existing xlsx are still parsed to pkl.

    Raises ``RuntimeError`` when there are missing dates but download failed
    (session expired, download errors, etc.) so the orchestrator's error
    tracking / LINE notification pipeline can pick it up.
    """
    explicit_missing: list[str] | None = None
    try:
        remote = list_remote_dates()
        local = list_local_dates()
        cutoff = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y%m%d")
        explicit_missing = [d for d in remote if d >= cutoff and d not in local]
        if not explicit_missing:
            logger.info("CME daily_volume: no new dates to download")
            build_pkl_series()
            return
    except Exception as e:
        logger.warning(f"requests listing failed ({e}), falling back to Playwright")

    success, fail, skip_reason = download_dates(
        explicit_missing, backfill_days=7, interactive=False,
    )
    build_pkl_series()

    if skip_reason:
        if "session invalid" in skip_reason:
            send_line_notification(
                "⚠️ CME daily_volume: 瀏覽器 session 已過期\n"
                "請手動執行 python get_cme_daily_volume.py 重新登入"
            )
        raise RuntimeError(f"CME daily_volume download skipped: {skip_reason}")
    if fail > 0:
        raise RuntimeError(
            f"CME daily_volume download: {fail} failed, {success} ok"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CME FTP daily_volume downloader")
    parser.add_argument("--backfill", type=int, default=0,
                        help="Backfill last N calendar days (interactive login)")
    parser.add_argument("--rebuild-pkl", action="store_true",
                        help="Rebuild pkl from existing xlsx without downloading")
    args = parser.parse_args()

    if args.rebuild_pkl:
        build_pkl_series()
    else:
        backfill_days = args.backfill if args.backfill > 0 else 7
        download_dates(backfill_days=backfill_days, interactive=True)
        build_pkl_series()
