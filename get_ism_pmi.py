# -*- coding: utf-8 -*-\
"""ISM PMI 子指標與合成差值指標

5 條 series:
  - sid=267  ISM 製造業新訂單 (ok, bellwether JSON)
  - sid=277  ISM 製造業客戶存貨 (partial, ISM PDF 當月)
  - sid=281  ISM 未完成訂單 (ok 但脆弱, Wayback HTML)
  - sid=22807 美 PMI 新訂單 − 客戶存貨 (approx, 267 − 277)
  - sid=22806 台 PMI 新訂單 − 客戶存貨 (approx, 590 − 595)

依賴: 05 檔已先完成 → series_590.pkl / series_595.pkl 均更新到 2026-08-01(n=170)。

日期慣例: 所有 datetime 統一 08:00:00(UTC+8),月頻放當月 1 日。
(舊 pkl 觀察: 277 PDF 的 July 值 → pkl 2026-07-01,非 (M+1)-01)

来源: migration/agent_results/series_{267,277,281,22807,22806}.json
"""

import os
import pickle
import json
import re
import urllib.request
import io
from datetime import datetime
from pathlib import Path

from loguru import logger
from curl_cffi import requests as cffi_requests
from curl_cffi import requests  # 281 Wayback 用
from pypdf import PdfReader

import log_config  # noqa: F401

folder = os.environ.get("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# title 對照表:沿用舊 pkl 顯示名稱
TITLE_MAP = {
    267: "ism-manufacturing-neworders",
    277: "ism-manufacturing-customersinventories",
    281: "ism-manufacturing-backlogoforders",
    22807: "us-pmi-new-orders-minus-customers-invertories",
    22806: "tw-pmi-new-orders-minus-customers-invertories",
}

# ---------------------------------------------------------------------------
# sid=267  ISM 新訂單  [ok]
# 來源: RealMaxPower/bellwether — pmi-subindices-wayback.json (GitHub raw)
# 覆蓋: 2014-09 ~ 2026-06 (n=80), 缺 2026-07
# ---------------------------------------------------------------------------
def fetch_267_new_orders():
    """Fetch ISM Manufacturing New Orders from bellwether Wayback JSON.

    Returns: [(datetime(08:00), float), ...] sorted ascending.
    Note: bellwether JSON 僅覆蓋 2014-09 ~ 2026-06 (n=80),缺 2026-07。
    函式本身只回傳新源資料;由 fetch_267_with_merge() 做 merge 舊 pkl。
    """
    url = "https://raw.githubusercontent.com/RealMaxPower/bellwether/main/data/pmi-subindices-wayback.json"
    data = json.load(urllib.request.urlopen(url))
    obs = data["observations"]
    out = []
    for o in obs:
        y, m, d = map(int, o["date"].split("-"))
        out.append((datetime(y, m, d, 8, 0), float(o["newOrders"])))
    out.sort()
    logger.info(f"267: fetched {len(out)} points from bellwether, last={out[-1][0]:%Y-%m-%d}")
    return out


def _load_old_267():
    """讀舊 pkl 做 merge base。"""
    p = Path(folder) / "series_267.pkl"
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    return None


def fetch_267_with_merge():
    """Fetch ISM New Orders with merge strategy(累積,不捨棄)。

    bellwether JSON 只有 2014-09~2026-06,舊 pkl 有 1948-2026-07 全歷史(n=159)。
    策略: merge 舊 pkl 全歷史 + bellwether 新值(2014-09 後的新值覆蓋舊)。
    確保 1948-2013 深層歷史不丟失,2026-07 舊值(56.7)保留。

    Returns: [(datetime(08:00), float), ...] sorted ascending。
    """
    new_pts = fetch_267_new_orders()
    new_map = {d: v for d, v in new_pts}

    old_data = _load_old_267()
    old_pts = old_data.get("data", []) if old_data else []
    merged_map = {d: v for d, v in old_pts}  # 先複製舊 pkl 全歷史

    # 用 bellwether 新值覆蓋(2014-09 之後的)
    for dt, val in new_pts:
        merged_map[dt] = val

    out = sorted(merged_map.items())
    logger.info(f"267: merged n={len(out)}, old_n={len(old_pts)}, bellwether_new={len(new_pts)}, last={out[-1][0]:%Y-%m-%d} val={out[-1][1]}")
    return out


# ---------------------------------------------------------------------------
# sid=277  ISM 客戶存貨  [partial]
# 來源: ISM 官方 PDF (Manufacturing at a Glance)
# 策略: merge 舊 pkl 歷史 + 當月 PDF 新值(累積,不捨棄)
# 注意: ISM 官網不穩定(常 520),失敗時保留舊 pkl 並 warning,不 raise
# ---------------------------------------------------------------------------
def _fetch_277_pdf_current():
    """從 ISM 官方 PDF 抓取最新月份的 Customers' Inventories 值。

    Returns: list of (datetime(08:00), float) — 新增點(可能 0~2 筆)。
    URL pattern: https://www.ismworld.org/globalassets/pub/research-and-surveys/rob/pmi/mwf{YYYYMM}pmi.pdf
    其中 YYYYMM = 報告月份(= pkl 日期的年月)。
    """
    # 動態推算最新報告月份:當前月的前一個月(ISM M 月報告 M+1 發,但 mwf 編號是報告月)
    # 驗證: mwf4202607pmi.pdf → 2026-07 → pkl 2026-07-01
    today = datetime.now()
    report_month = today.month
    report_year = today.year
    # 若本月還未發布,使用上月(保守)
    # ISM 通常在月初發布上月報告,所以最新可用 = 上月
    # 但 mwf4202607pmi.pdf 對應 pkl 2026-07-01,表示「7 月的報告」
    # 我們嘗試當前月與上月各一次
    candidates = []
    # 嘗試 report_year-report_month (可能還未發布)
    candidates.append((report_year, report_month))
    # 嘗試上月
    if report_month == 1:
        candidates.append((report_year - 1, 12))
    else:
        candidates.append((report_year, report_month - 1))

    new_pts = []
    for y, m in candidates:
        ym = f"{y}{m:02d}"
        url = f"https://www.ismworld.org/globalassets/pub/research-and-surveys/rob/pmi/mwf{ym}pmi.pdf"
        try:
            r = cffi_requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200 or len(r.content) < 1000:
                logger.warning(f"277: PDF {ym} status={r.status_code}, len={len(r.content)}")
                continue
            reader = PdfReader(io.BytesIO(r.content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            # 找 Customers' Inventories 行: "Customers' Inventories 40.7 42.3 -1.6 ..."
            # 第一個數字是當月,第二個是上月
            m_obj = re.search(r"Customers['’]\s*Inventories\s+([\d.]+)\s+([\d.]+)", text)
            if m_obj:
                cur_val = float(m_obj.group(1))
                # pkl 日期 = 報告月(月首) 08:00
                dt = datetime(y, m, 1, 8, 0)
                new_pts.append((dt, cur_val))
                logger.info(f"277: fetched PDF {ym}: Customers' Inventories={cur_val}")
                break  # 成功拿到就跳出
        except Exception as e:
            logger.warning(f"277: PDF fetch {ym} failed: {e}")
            continue
    return new_pts


def _load_old_277():
    """讀舊 pkl 做 merge base。"""
    p = Path(folder) / "series_277.pkl"
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    return None


def fetch_277_customers_inventories():
    """Fetch ISM Manufacturing Customers' Inventories (partial).

    策略(已裁示: 累積): merge 舊 pkl 歷史 + 當月 PDF 新值。
    若 PDF 拿不到,照舊輸出舊 pkl 歷史,WN 註明「新點等待下月」。
    整條失敗才 raise。

    Returns: [(datetime(08:00), float), ...] sorted ascending.
    """
    old_data = _load_old_277()
    old_pts = old_data["data"] if old_data else []
    if old_data:
        old_map = {d: v for d, v in old_pts}
    else:
        old_map = {}

    new_pts = _fetch_277_pdf_current()

    # 合併:新點覆蓋舊點(同日期取新值),其餘保留舊
    merged_map = dict(old_map)
    for dt, val in new_pts:
        merged_map[dt] = val

    # 檢查是否需要補 2026-08 (若 PDF 拿到的是 2026-07 但 pkl 已有到 2026-07)
    # 實際上舊 pkl 已到 2026-07-01,PDF 拿的也是 2026-07,無需補
    # 若拿到更新的月份(如 2026-08),自然補上

    out = sorted(merged_map.items())
    logger.info(f"277: merged n={len(out)}, old_n={len(old_pts)}, new_added={len(new_pts)}, last={out[-1][0]:%Y-%m-%d}")
    return out


# ---------------------------------------------------------------------------
# sid=281  ISM 未完成訂單  [ok 但脆弱]
# 來源: Wayback Machine 快照頁 HTML 解析
# 注意: wayback_ts_map 寫死時間戳,每月新報告要人工加 key
# 步驟(每月新報告):
#   1. 打 ISM 官網報告頁,取得該月報告頁的 Wayback 快照時間戳
#      方法: https://web.archive.org/web/20260901000000*/ismworld.org/.../pmi/{month}/
#      或用 CDX API: http://web.archive.org/cdx/search/cdx?url=ismworld.org/.../pmi/{month}/*&output=json&limit=1
#   2. 將 {month}_{year} 的 ts_map 條目加上新時間戳
#   3. 程式讀 ts_map 抓快照頁 HTML 解析 Backlog of Orders
# ---------------------------------------------------------------------------
# Wayback ts_map: 每個 key = '{month}_{year}', value = Wayback snapshot timestamp (yyyyMMddHHMMSS)
# 每月新報告時,需人工更新此 map(見上方步驟說明)
_WAYBACK_TS_MAP = {
    "july_2026":  "20260902000000",
    "june_2026":  "20260701142312",
    "may_2026":   "20260701000000",
    "august_2026":"20260902000000",
    "january_2026":"20260207174004",
    "august_2025":"20250902155544",
    "october_2025":"20251105180446",
}


def _get_wayback_ts(month: str, year: int) -> str | None:
    """取得 Wayback snapshot timestamp。"""
    key = f"{month}_{year}"
    return _WAYBACK_TS_MAP.get(key)


def fetch_281_backlog_of_orders():
    """Fetch ISM Manufacturing Backlog of Orders from Wayback Machine.

    從 ISM 官網每月的 ISM PMI Report on Business 頁面 HTML 解析。
    Wayback ts_map 寫死時間戳(每月新報告需人工加 key,見模組註解)。

    Returns: [(datetime(08:00), float), ...] sorted ascending。
    若某月 ts_map 缺 key,跳過該月並 warning。
    """
    # 構建所有已知的 (month, year) 組合
    # 從舊 pkl 讀取現有日期範圍,再補上已知的 ts_map 覆蓋
    old_data_path = Path(folder) / "series_281.pkl"
    old_pts = []
    if old_data_path.exists():
        with open(old_data_path, "rb") as f:
            old = pickle.load(f)
            old_pts = old.get("data", [])

    # 從 ts_map 提取有覆蓋的年月
    covered_months = set()
    for key in _WAYBACK_TS_MAP:
        parts = key.rsplit("_", 1)
        if len(parts) == 2:
            month_name, year_str = parts
            # month_name -> num
            month_num = _month_name_to_num(month_name)
            if month_num:
                covered_months.add((int(year_str), month_num))

    # 確保至少覆蓋舊 pkl 最後幾個月
    # 舊 pkl 已有 1993-01 ~ 2026-07,我們只重新取最近幾個月(ts_map 有的)
    # 為了簡化,直接用 ts_map 的 key 來產生資料
    # 但若 ts_map 只有部分月,舊 pkl 仍保留

    out = [(d, v) for d, v in old_pts]  # 統一為 tuple
    out_map = {d: v for d, v in out}

    for key, ts in _WAYBACK_TS_MAP.items():
        parts = key.rsplit("_", 1)
        if len(parts) != 2:
            continue
        month_name, year_str = parts
        month_num = _month_name_to_num(month_name)
        if not month_num:
            continue
        year = int(year_str)
        dt = datetime(year, month_num, 1, 8, 0)
        if dt in out_map:
            continue  # 舊 pkl 已有,跳過
        url = f"https://web.archive.org/web/{ts}/https://www.ismworld.org/supply-management-news-and-reports/reports/ism-pmi-reports/pmi/{month_name}/"
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                logger.warning(f"281: Wayback {key} status={r.status_code}")
                continue
            text = r.text
            trs = re.findall(r"<tr[^>]*>.*?</tr>", text, re.DOTALL)
            found = False
            for tr in trs:
                if "Backlog of Orders" in tr and "<th" in tr:
                    cells = re.findall(r"<t[dh][^>]*>([^<]+)</t[dh]>", tr)
                    if len(cells) >= 3 and cells[1].replace(".", "").isdigit():
                        val = float(cells[1])
                        out_map[dt] = val
                        out.append((dt, val))
                        logger.info(f"281: fetched {key}: Backlog={val}")
                        found = True
                        break
            if not found:
                logger.warning(f"281: Backlog not found in Wayback {key}")
        except Exception as e:
            logger.warning(f"281: Wayback fetch {key} failed: {e}")

    out.sort()
    logger.info(f"281: total n={len(out)}, last={out[-1][0]:%Y-%m-%d}")
    return out


def _month_name_to_num(name: str) -> int | None:
    """英文月份名 -> 數字。"""
    m = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
         "july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
    return m.get(name.lower())


# ---------------------------------------------------------------------------
# sid=22807  美 PMI 新訂單 − 客戶存貨  [approx]
# 合成 = 267 − 277
# 策略: merge 舊 pkl 歷史 + 新合成點
# ---------------------------------------------------------------------------
def _load_old_22807():
    p = Path(folder) / "series_22807.pkl"
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    return None


def fetch_22807_us_pmi_diff():
    """Compose sid=22807 = ISM New Orders (267) − ISM Customers' Inventories (277).

    策略: merge 舊 pkl 歷史 + 新合成點。
    267 用 fetch_267_with_merge() 確保 1948-2013 深層歷史不丟失。
    277 用 fetch_277_customers_inventories() 做 merge。

    Returns: [(datetime(08:00), float), ...] sorted ascending。
    """
    # 用 fetch_267_with_merge 確保 1948-2026 全歷史
    import importlib
    get_ism_pmi_mod = importlib.import_module('get_ism_pmi')
    no_pts = get_ism_pmi_mod.fetch_267_with_merge()
    no_map = {d: v for d, v in no_pts}

    # 277 資料(含 merge 邏輯)
    pts_277 = fetch_277_customers_inventories()
    ci_map = {d: v for d, v in pts_277}

    # 舊 pkl 22807
    old = _load_old_22807()
    old_pts = old.get("data", []) if old else []
    out_map = {d: v for d, v in old_pts}

    # 合成:取 267 和 277 都有的日期
    common_dates = sorted(set(no_map.keys()) & set(ci_map.keys()))
    for dt in common_dates:
        out_map[dt] = round(no_map[dt] - ci_map[dt], 4)

    out = sorted(out_map.items())
    logger.info(f"22807: merged n={len(out)}, old_n={len(old_pts)}, last={out[-1][0]:%Y-%m-%d} val={out[-1][1]}")
    return out


# ---------------------------------------------------------------------------
# sid=22806  台 PMI 新訂單 − 客戶存貨  [approx]
# 合成 = 590 − 595(依賴 05 檔)
# 策略: merge 舊 pkl 歷史 + 新合成點
# ---------------------------------------------------------------------------
def _load_old_22806():
    p = Path(folder) / "series_22806.pkl"
    if p.exists():
        with open(p, "rb") as f:
            return pickle.load(f)
    return None


def fetch_22806_tw_pmi_diff():
    """Compose sid=22806 = TW PMI New Orders (590) − TW PMI Customer Inventories (595).

    依賴 05 檔的 series_590.pkl / series_595.pkl。
    策略: merge 舊 pkl 歷史 + 新合成點。

    Returns: [(datetime(08:00), float), ...] sorted ascending。
    """
    # 讀 590
    p590 = Path(folder) / "series_590.pkl"
    with open(p590, "rb") as f:
        d590 = pickle.load(f)
    no_map = {dt: v for dt, v in d590["data"]}

    # 讀 595
    p595 = Path(folder) / "series_595.pkl"
    with open(p595, "rb") as f:
        d595 = pickle.load(f)
    ci_map = {dt: v for dt, v in d595["data"]}

    # 舊 pkl 22806
    old = _load_old_22806()
    old_pts = old.get("data", []) if old else []
    out_map = {d: v for d, v in old_pts}

    # 合成:取 590 和 595 都有的日期(內連 join)
    common_dates = sorted(set(no_map.keys()) & set(ci_map.keys()))
    for dt in common_dates:
        out_map[dt] = round(no_map[dt] - ci_map[dt], 4)

    out = sorted(out_map.items())
    logger.info(f"22806: merged n={len(out)}, old_n={len(old_pts)}, last={out[-1][0]:%Y-%m-%d}")
    return out


# ---------------------------------------------------------------------------
# _save_series: 寫 pkl,防呆(新點 < 舊 50% 拒寫)
# ---------------------------------------------------------------------------
def _save_series(sid, obs):
    """寫出 {'title': str, 'data': [[datetime(08:00), float], ...]} 格式 pkl,同舊格式。
    防呆:新點數少於既有 pkl 的一半時不覆寫。
    """
    out_file = Path(folder) / f"series_{sid}.pkl"
    old = None
    if out_file.exists():
        with open(out_file, "rb") as f:
            old = pickle.load(f)
    old_n = len(old.get("data", [])) if isinstance(old, dict) else 0
    if old and len(obs) < old_n * 0.5:
        raise RuntimeError(f"series_{sid}: new n={len(obs)} < 50% of old n={old_n}, skip write")
    data = {"title": TITLE_MAP.get(sid, str(sid)), "data": [[d, v] for d, v in obs]}
    with open(out_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(f"Saved series_{sid}.pkl n={len(obs)} last={obs[-1][0]:%Y-%m-%d} (old n={old_n})")


# ---------------------------------------------------------------------------
# JOBS + fetch_ism_pmi 入口
# ---------------------------------------------------------------------------
JOBS = [
    ("267 ISM New Orders (bellwether JSON + merge old pkl)", fetch_267_with_merge),
    ("277 ISM Customers' Inventories (PDF, merge)", fetch_277_customers_inventories),
    ("281 ISM Backlog of Orders (Wayback HTML)", fetch_281_backlog_of_orders),
    ("22807 US PMI diff = 267 - 277 (merge)", fetch_22807_us_pmi_diff),
    ("22806 TW PMI diff = 590 - 595 (merge)", fetch_22806_tw_pmi_diff),
]


def fetch_ism_pmi():
    """供 get_all_series_data.py 呼叫的入口。
    任一失敗彙整後 raise,交由 orchestrator 記入 error_history。
    """
    failures = []
    results = {}
    for name, fn in JOBS:
        try:
            logger.info(f"Starting: {name}")
            obs = fn()
            sid = int(name.split()[0])
            _save_series(sid, obs)
            results[sid] = len(obs)
            logger.info(f"Completed: {name}")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            f"ISM PMI 抓取失敗 {len(failures)} 項:\n" + "\n".join(failures)
        )
    return results


if __name__ == "__main__":
    fetch_ism_pmi()
