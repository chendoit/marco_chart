# -*- coding: utf-8 -*-
"""官方 Excel/CSV/ZIP 報告下載(AAII / S&P DJI / WSTS / NY Fed / CIER / TWSE)

10 條 M² series 落地,動態推算目前應發布期別 + 失敗 fallback。
"""

import io
import os
import pickle
import re
import urllib.request
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl
import requests
import xlrd
from curl_cffi import requests as creq
import pandas as pd

import log_config  # noqa: F401
from loguru import logger

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# ============================================================================
# title 對照表:沿用舊 pkl 顯示名稱
# ============================================================================
TITLE_MAP = {
    6783: "aaii-sentiment-survey-bullish",
    6784: "aaii-sentiment-survey-neutral",
    6785: "aaii-sentiment-survey-bearish",
    17586: "sp500-eps",
    2752: "americas-semiconductor-billings-yoy",
    2756: "global-semiconductor-billings-yoy",
    4433: "us-debt-severe-delinquency-student",
    590: "tw-pmi-new-orders",
    595: "tw-pmi-customers-invertories",
    5683: "taiwan-stock-price-to-earnings-ratio",
}

# OLE magic for xls validation
OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


# ============================================================================
# 通用 _save_series 防呆
# ============================================================================
def _save_series(sid: int, obs: list):
    """寫出 {'title', 'data': [[datetime(08:00), float], ...]} 格式 pkl,同舊格式。
    防呆:新點數少於既有 pkl 的一半時不覆寫(避免 API 異常清空歷史)。
    例外:若新數據最新日期 > 舊數據最新日期,允許寫入。"""
    out_file = Path(folder) / f"series_{sid}.pkl"
    old_n = 0
    old_last_dt = None
    if out_file.exists():
        try:
            with open(out_file, "rb") as f:
                old = pickle.load(f)
            old_n = len(old.get("data", [])) if isinstance(old, dict) else 0
            old_data = old.get("data", [])
            if old_data:
                old_last_dt = old_data[-1][0]
        except Exception:
            old_n = 0
    new_has_more = len(obs) > old_n if old_n > 0 else True
    new_is_newer = (obs[-1][0] > old_last_dt) if old_last_dt else True
    if old_n > 0 and not new_has_more and not new_is_newer and len(obs) < old_n * 0.5:
        raise RuntimeError(
            f"series_{sid}: new data n={len(obs)} < 50% of existing n={old_n}, skip write"
        )
    data = {"title": TITLE_MAP.get(sid, str(sid)), "data": [[d, v] for d, v in obs]}
    with open(out_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(obs)} last={obs[-1][0]:%Y-%m-%d} (old n={old_n})"
    )


# ============================================================================
# 1) AAII 系列 6783/6784/6785
#    來源: AAII 官方 sentiment.xls, Imperva WAF 需 curl_cffi
#    使用 safari17_0 指紋;失敗時退 Wayback Machine
# ============================================================================
AAII_XLS_URL = "https://www.aaii.com/files/surveys/sentiment.xls"
AAII_WB_PINNED_URL = (
    "https://web.archive.org/web/20260911211233id_/https://www.aaii.com/files/surveys/sentiment.xls"
)
AAII_WB_CDX_URL = (
    "https://web.archive.org/cdx/search/cdx?url=aaii.com%2Ffiles%2Fsurveys%2Fsentiment.xls&output=json&from=20250101"
)


def _aaii_try_live(impersonate: str):
    """嘗試從 AAII 官方取得 xls。"""
    r = creq.get(AAII_XLS_URL, impersonate=impersonate, timeout=60)
    if r.status_code == 200 and r.content[:8] == OLE_MAGIC and len(r.content) > 100000:
        return r.content
    return None


def _aaii_try_wayback():
    """從 Wayback Machine 取得 xls。"""
    # CDX 查最新
    try:
        cdx = creq.get(AAII_WB_CDX_URL, impersonate="chrome120", timeout=60).json()
        stamps = [row[1] for row in cdx[1:]
                  if row[3] == "application/vnd.ms-excel" and row[4] == "200"]
        for ts in reversed(stamps[-3:]):
            r = creq.get(
                f"https://web.archive.org/web/{ts}id_/https://www.aaii.com/files/surveys/sentiment.xls",
                impersonate="chrome120", timeout=120)
            if r.status_code == 200 and r.content[:8] == OLE_MAGIC:
                return r.content
    except Exception:
        pass
    # 釘選備份
    r = creq.get(AAII_WB_PINNED_URL, impersonate="chrome120", timeout=120)
    if r.status_code == 200 and r.content[:8] == OLE_MAGIC:
        return r.content
    return None


def _parse_aaii_xls_xlrd(content: bytes, skiprows: int = 5) -> list:
    """用 xlrd 解析 xls,返回 [(datetime, value), ...]。"""
    wb = xlrd.open_workbook(file_contents=content)
    sh = wb.sheet_by_name("SENTIMENT")
    out = []
    for row in range(skiprows, sh.nrows):
        d = sh.cell_value(row, 0)
        b = sh.cell_value(row, 1)
        if not isinstance(d, float) or not isinstance(b, float):
            continue
        dt = datetime(*xlrd.xldate_as_tuple(d, wb.datemode)).replace(hour=8)
        out.append((dt, round(b * 100, 4)))
    out.sort()
    return out


def _parse_aaii_xls_pandas(content: bytes, skiprows: int = 5) -> list:
    """用 pandas 解析 xls,返回 [(datetime, value), ...]。"""
    df = pd.read_excel(io.BytesIO(content), sheet_name=0, header=None, skiprows=skiprows)
    df = df.iloc[:, :4]
    df.columns = ["date", "bullish", "neutral", "bearish"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    col_name = "neutral" if skiprows == 5 else "bearish"
    df[col_name] = pd.to_numeric(df[col_name], errors="coerce")
    df = df.dropna(subset=["date", col_name])
    out = [
        (ts.to_pydatetime().replace(hour=8, minute=0, second=0, microsecond=0),
         float(v) * 100.0)
        for ts, v in zip(df["date"], df[col_name])
    ]
    out.sort(key=lambda x: x[0])
    return out


def _fetch_aaii_bullish() -> list:
    """AAII Sentiment Survey weekly Bullish %, 1987-07 ~ now."""
    # 嘗試官方直連
    content = _aaii_try_live("safari17_0") or _aaii_try_live("firefox135") or _aaii_try_live("chrome120")
    if content:
        return _parse_aaii_xls_xlrd(content)
    # Wayback fallback
    content = _aaii_try_wayback()
    if content:
        return _parse_aaii_xls_xlrd(content)
    raise RuntimeError("AAII Bullish xls: live + wayback all failed")


def _fetch_aaii_neutral() -> list:
    """AAII Sentiment Survey weekly Neutral %, 1987-07 ~ now."""
    # 嘗試官方直連
    content = _aaii_try_live("safari17_0") or _aaii_try_live("firefox135")
    if content:
        return _parse_aaii_xls_pandas(content, skiprows=5)
    # Wayback fallback
    content = _aaii_try_wayback()
    if content:
        return _parse_aaii_xls_pandas(content, skiprows=5)
    raise RuntimeError("AAII Neutral xls: live + wayback all failed")


def _fetch_aaii_bearish() -> list:
    """AAII Sentiment Survey weekly Bearish %, 1987-07 ~ now."""
    content = _aaii_try_live("safari17_0")
    if content:
        return _parse_aaii_xls_pandas(content, skiprows=3)
    content = _aaii_try_wayback()
    if content:
        return _parse_aaii_xls_pandas(content, skiprows=3)
    raise RuntimeError("AAII Bearish xls: live + wayback all failed")


# ============================================================================
# 2) S&P500 EPS (sid 17586) [partial]
#    來源: S&P DJI sp-500-eps-est.xlsx, 官網 403 → web.archive.org if_ 鏡像
#    URL 寫死 2026-05-27 快照;檢查是否過期(>2 個月)→ 嘗試最新快照
# ============================================================================
SP_EPS_ARCHIVE_URL = "https://web.archive.org/web/20260527232437if_/https://www.spglobal.com/spdji/en/documents/additional-material/sp-500-eps-est.xlsx"
SP_EPS_CDX_URL = "https://web.archive.org/cdx/search/cdx?url=spglobal.com/spdji/en/documents/additional-material/sp-500-eps-est.xlsx&output=json&from=20260101"
SP_EPS_STALE_LIMIT = timedelta(days=60)


def _try_sp500_eps_url(url: str) -> list:
    """從指定 URL 抓取 S&P 500 EPS 數據。"""
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
    ws = wb["SECTOR EPS"]
    rows = list(ws.iter_rows(values_only=True))
    header = next(r for r in rows if r[0] == "INDEX NAME" and r[2] == "2008 Q1")
    srow = next(r for r in rows if r[0] == "S&P 500" and header[2] == "2008 Q1")
    pairs = []
    for i, h in enumerate(header):
        if h and isinstance(h, str) and " Q" in h:
            # 過濾預估(如 '2025E Q3')
            if "E" in str(h).split(" Q")[0]:
                continue
            val = srow[i]
            if isinstance(val, (int, float)):
                parts = h.strip().split()
                yr = int(parts[0])
                qn = parts[1]
                m = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}[qn]
                dt = datetime(yr, m, 1, 8, 0)
                pairs.append((dt, val))
    pairs.sort()
    return pairs


def _check_archive_stale(url: str) -> bool:
    """檢查 archive 快照是否過期(>2 個月)。"""
    try:
        match = re.search(r"/web/(\d{14})", url)
        if not match:
            return True
        snap_date = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        return (datetime.now() - snap_date) > SP_EPS_STALE_LIMIT
    except Exception:
        return True


def _fetch_sp500_eps_fallback_url() -> str:
    """從 CDX 取得最新快照 URL。"""
    try:
        cdx = requests.get(SP_EPS_CDX_URL, timeout=60).json()
        for row in reversed(cdx[1:]):
            if "spreadsheet" in row[3] or row[3] == "application/octet-stream":
                return f"https://web.archive.org/web/{row[1]}id_/{row[2]}"
    except Exception:
        pass
    return None


def _fetch_sp500_eps() -> list:
    """Fetch S&P 500 EPS (quarterly, 2008-Q1 ~ latest).
    [partial]: 2027 預估抓不到(官網 403),舊 pkl 有 8 筆 2027 預估。
    新 pkl 不含 2027 預估是預期行為。"""
    url = SP_EPS_ARCHIVE_URL
    if _check_archive_stale(url):
        latest_url = _fetch_sp500_eps_fallback_url()
        if latest_url:
            url = latest_url
            logger.info(f"17586: archive stale, using fallback: {url}")
        else:
            logger.warning("17586: no fresh snapshot, using original archive URL")
    return _try_sp500_eps_url(url)


# ============================================================================
# 3) WSTS 半導體 (sid 2752 / 2756)
#    來源: WSTS Historical Billings Report, URL 含月份
#    從 WSTS 官方頁面取得最新可用 xlsx
# ============================================================================
WSTS_PAGE_URL = "https://www.wsts.org/67/Historical-Billings-Report"


def _get_wsts_url() -> str:
    """從 WSTS 官方頁面找到最新可下載的 xlsx URL。"""
    try:
        r = requests.get(WSTS_PAGE_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        links = re.findall(r'href="([^"]+\.xlsx)"', r.text)
        if links:
            return links[0]
    except Exception:
        pass
    return "https://www.wsts.org/esraCMS/extension/media/f/WST/7771/WSTS-Historical-Billings-Report-Jul_2026.xlsx"


def _parse_wsts_americas(url: str) -> list:
    """解析 WSTS Monthly Data sheet 的 Americas 行,計算 YoY。"""
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    with open("/tmp/wsts_americas.xlsx", "wb") as f:
        f.write(r.content)
    wb = openpyxl.load_workbook("/tmp/wsts_americas.xlsx", data_only=True)
    ws = wb["Monthly Data"]
    americas = {}
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True)):
        if row[0] and isinstance(row[0], str) and "mericas" in row[0]:
            for j in range(i - 1, max(i - 10, 0), -1):
                v = ws.cell(row=j + 1, column=1).value
                if isinstance(v, (int, float)):
                    year = int(v)
                    months = row[1:13]
                    for m in range(12):
                        val = months[m]
                        if val is not None:
                            americas[(year, m + 1)] = float(val)
                    break
    yoy = {}
    for (y, m), val in americas.items():
        if (y - 1, m) in americas:
            prev = americas[(y - 1, m)]
            if prev > 0:
                yoy[(y, m)] = round((val / prev - 1) * 100, 2)
    return [(datetime(y, m, 1, 8, 0), v) for (y, m), v in sorted(yoy.items())]


def _parse_wsts_worldwide(url: str) -> list:
    """解析 WSTS 3MMA sheet 的 Worldwide 行,計算 YoY。"""
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
    ws = wb["3MMA"]
    mma3 = {}
    current_year = None
    for row in ws.iter_rows(values_only=True):
        label = row[0]
        if isinstance(label, int):
            current_year = label
        elif label == "Worldwide":
            vals = [row[m] for m in range(1, 13)]
            mma3[current_year] = vals
            current_year = None
    yoy = {}
    for y in sorted(mma3.keys()):
        vals = mma3[y]
        for m in range(1, 13):
            mm_val = vals[m - 1]
            if not mm_val or mm_val == 0:
                continue
            py = y - 1
            if py >= 1986 and py in mma3 and mma3[py][m - 1] and mma3[py][m - 1] != 0:
                prev_mm = mma3[py][m - 1]
                yoy[(y, m)] = round((mm_val - prev_mm) / prev_mm * 100, 2)
    return [(datetime(y, m, 1, 8, 0), v) for (y, m), v in sorted(yoy.items())]


def _fetch_2752() -> list:
    """美洲半導體產值年增 [approx]。"""
    url = _get_wsts_url()
    logger.info(f"2752: {url}")
    return _parse_wsts_americas(url)


def _fetch_2756() -> list:
    """全球半導體產值年增 [ok]。"""
    url = _get_wsts_url()
    logger.info(f"2756: {url}")
    return _parse_wsts_worldwide(url)


# ============================================================================
# 4) NY Fed 學貸嚴重拖欠率 (sid 4433) [approx]
#    來源: NY Fed HHD_C_Report_{Q}.xlsx, URL 含季度
# ============================================================================
NYFED_REPORT_URL = "https://www.newyorkfed.org/medialibrary/interactives/householdcredit/data/xls/HHD_C_Report_{quarter}.xlsx"


def _get_current_quarter() -> str:
    """推算目前已發布的 NY Fed 季度報告。"""
    today = datetime.now()
    quarter_idx = (today.month - 1) // 3
    q_map = ["Q1", "Q2", "Q3", "Q4"]
    for offset in range(4):
        qi = (quarter_idx - offset) % 4
        yr = today.year if qi <= quarter_idx else today.year - 1
        quarter = f"{yr}{q_map[qi]}"
        url = NYFED_REPORT_URL.format(quarter=quarter)
        try:
            r = requests.head(url, timeout=10)
            if r.status_code == 200:
                return quarter
        except Exception:
            pass
    return "2026Q2"


def _fetch_4433() -> list:
    """Fetch NY Fed student loan 90+ serious delinquency rate。"""
    quarter = _get_current_quarter()
    url = NYFED_REPORT_URL.format(quarter=quarter)
    logger.info(f"4433: {quarter}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
    ws = wb["Page 28 Data"]
    month_map = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}
    data = []
    for i in range(4, ws.max_row + 1):
        q_val = ws.cell(row=i, column=1).value
        all_val = ws.cell(row=i, column=6).value
        if q_val and all_val is not None:
            try:
                year_str, q_label = str(q_val).split(":")
                year = int("20" + year_str)
                dt = datetime(year, month_map[q_label], 1, 8, 0)
                val = float(all_val)
                data.append((dt, val))
            except (ValueError, KeyError):
                continue
    data.sort(key=lambda x: x[0])
    return data


# ============================================================================
# 5) 台灣 PMI (sid 590 / 595)
#    來源: CIER PMI-歷史資料-季節調整.xlsx, URL 含發布月
# ============================================================================
CIER_BASE_URL = "https://www.cier.edu.tw/wp-content/uploads/{year}/{month:02d}/PMI-歷史資料-季節調整.xlsx"
CIER_SHEET_NAME = "(季調後)臺灣製造業PMI與各項擴散指標時間序列-報告發布"


def _get_cier_publish_month() -> tuple:
    """推算 CIER 報告發布月份(YYYY, MM)。"""
    today = datetime.now()
    return today.year, today.month


def _fetch_cierm_pmi(col_idx: int) -> list:
    """通用 CIER PMI 抓取。col_idx: 2=新增訂單, 7=客戶存貨。"""
    year, month = _get_cier_publish_month()
    url = CIER_BASE_URL.format(year=year, month=month)
    logger.info(f"CIER col{col_idx}: {url}")
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
    ws = wb[CIER_SHEET_NAME]
    data = []
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row, values_only=True):
        date_val = row[0]
        col_val = row[col_idx]
        if date_val and col_val is not None:
            data.append([date_val.strftime("%Y-%m-%d"), round(float(col_val), 1)])
    return [(datetime.strptime(d, "%Y-%m-%d").replace(hour=8, minute=0, second=0, microsecond=0), v) for d, v in data]


def _fetch_590() -> list:
    """台灣 PMI 新增訂單 [ok]。"""
    return _fetch_cierm_pmi(2)


def _fetch_595() -> list:
    """台灣 PMI 客戶存貨 [ok]。"""
    return _fetch_cierm_pmi(7)


# ============================================================================
# 6) 台股 PE (sid 5683)
#    來源: TWSE 市場交易月報 zip→xlrd, 民國年 +1911
# ============================================================================
TWSE_URL_TPL = "https://www.twse.com.tw/rwd/zh/statistics/count?l1=市場交易月報&l2=【證券市場統計概要與市場總市值、投資報酬率、本益比、殖利率一覽表】月報&url=/staticFiles/inspection/inspection/02/001/{yyyymm}_C02001.zip"


def _get_twse_month() -> str:
    """推算 TWSE 最新月份(YYYYMM)。"""
    today = datetime.now()
    ym = (today.replace(day=1) - timedelta(days=1)).strftime("%Y%m")
    return ym


def _fetch_5683() -> list:
    """台股 PE [ok]。TWSE 市場統計月報,民國年 +1911。
    算法差 ~7-9%(舊 pkl 與 TWSE 數據比對差 0%)。"""
    ym = _get_twse_month()
    url = TWSE_URL_TPL.format(yyyymm=ym)
    logger.info(f"5683: {url}")
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    xls_data = z.read(z.namelist()[0])
    wb = xlrd.open_workbook(file_contents=xls_data)
    sheet = wb.sheet_by_index(0)
    pe_data = []
    # Annual rows (13-17): '110(2021)' -> ROC 110 = Greg 2021
    for row_idx in range(13, 18):
        year_str = str(sheet.cell(row_idx, 0).value).strip()
        pe_val = sheet.cell(row_idx, 11).value
        if pe_val and pe_val != "":
            m = re.match(r"(\d{3})", year_str)
            if m:
                roc_year = int(m.group(1))
                greg_year = roc_year + 1911
                pe_data.append((f"{greg_year:04d}-01-01", float(pe_val)))
    # Monthly rows (19-30): track ROC year context
    current_roc_year = None
    for row_idx in range(19, 31):
        year_str = str(sheet.cell(row_idx, 0).value).strip()
        pe_val = sheet.cell(row_idx, 11).value
        if not pe_val or pe_val == "":
            continue
        m = re.match(r"(\d{3})", year_str)
        if m:
            current_roc_year = int(m.group(1))
        month_match = re.search(r"(\d{1,2})月", year_str)
        if month_match:
            month = int(month_match.group(1))
        elif re.match(r"\s*(\d{1,2})\s*$", year_str):
            month = int(re.match(r"\s*(\d{1,2})\s*$", year_str).group(1))
        else:
            continue
        if current_roc_year is None:
            continue
        greg_year = current_roc_year + 1911
        pe_data.append((f"{greg_year:04d}-{month:02d}-01", float(pe_val)))
    return [(datetime.strptime(d, "%Y-%m-%d").replace(hour=8, minute=0, second=0, microsecond=0), v) for d, v in pe_data]


# ============================================================================
# JOBS + 入口函式
# ============================================================================
JOBS = [
    ("AAII Bullish 6783", _fetch_aaii_bullish),
    ("AAII Neutral 6784", _fetch_aaii_neutral),
    ("AAII Bearish 6785", _fetch_aaii_bearish),
    ("S&P500 EPS 17586", _fetch_sp500_eps),
    ("WSTS Americas 2752", _fetch_2752),
    ("WSTS Worldwide 2756", _fetch_2756),
    ("NY Fed Student Delinquency 4433", _fetch_4433),
    ("CIER PMI New Orders 590", _fetch_590),
    ("CIER PMI Customer Inventories 595", _fetch_595),
    ("TWSE PE 5683", _fetch_5683),
]


def fetch_official_xlsx():
    """供 get_all_series_data.py 呼叫的入口。任一抓取失敗會彙整後 raise。"""
    failures = []
    for name, fn in JOBS:
        try:
            logger.info(f"Starting: {name}")
            obs = fn()
            sid = int(name.split()[-1])
            _save_series(sid, obs)
            logger.info(f"Completed: {name} (n={len(obs)})")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"官方 XLSX 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )


if __name__ == "__main__":
    fetch_official_xlsx()
