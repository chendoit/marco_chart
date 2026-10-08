# -*- coding: utf-8 -*-
"""日本地產分析案例：一次性抓取（不進專案 ETL，不寫入專案 data/）

輸出到 analysis/日本地產/data/：
量
- starts_monthly_use.csv        新設住宅着工 利用関係別月報（持家/貸家/給与/分譲/マンション/建売、季調年率；1965-01–）
- starts_annual_history.csv     新設住宅着工 利用関係別年計（1948–）
- starts_monthly_shutoken.csv   首都圏（東京・神奈川・埼玉・千葉）月度着工
- starts_monthly_structure.csv  月度 木造／プレハブ／ツーバイフォー 戸數與占比
價
- price_index_mlit.csv          不動産価格指数（住宅）全国／南関東圏／東京都，季調（2008–）
- reins_market_watch.csv        東日本 REINS 中古マンション／中古戸建／新築戸建 成約價格（PDF 只有近 13 個月，已存在的舊資料會保留累積）
利率
- policy_rate_boj.csv           日銀政策利率（BIS WS_CBPOL，日資料，失敗退回月資料）
- jgb_yield.csv                 財務省 國債利回り 1/5/10/20/30Y（日，1974–）
- prime_rate_boj.csv            日銀 短期／長期プライムレート（2001–）
成本與供給
- deflator_construction.csv     國交省 建設工事費デフレーター（2020 基準，月）
- ppi_building_materials.csv    日銀 企業物価指数：木材、製材、合板、セメント、鋼材（月）
- bankruptcy_monthly.csv        中小企業庁（TSR 轉載）全產業／建設業／不動産業倒產件數（月）
- labor_shortage_monthly.csv    國交省 建設労働需給調査 8 職種過不足率（月）
公司
- stocks_daily.csv              飯田GHD、Open House、Tama Home、永大、Nichiha、ERI、Star Mica、積水ハウス、大和ハウス、TOPIX ETF 日收盤（Yahoo Finance）

不在這支腳本內（來源只有新聞稿／決算 PDF，或 probe 階段是手抄數字、未實測）：
- 飯田、Open House 季度決算 → 之後從決算短信 PDF 抽
- REEI 首都圈マンション平均價、東京カンテイ年收倍率、フラット35 利率、NRI 預測、空き家率、MAFF 木材價格 → 待找到可程式化來源或另行手建
- 建築確認半月度（只有 2025 前後 14 列的連絡会議資料）、政策時間線 → 手建

來源：
- 國交省 建築着工統計：https://www.mlit.go.jp/sogoseisaku/jouhouka/content/
- 國交省 不動産価格指数：https://www.mlit.go.jp/totikensangyo/totikensangyo_tk5_000085.html
- 東日本 REINS Market Watch：http://www.reins.or.jp/pdf/trend/mw/MW_<YYYYMM>data.pdf
- BIS：https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/
- 財務省：https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv
- 日銀：https://www.boj.or.jp/statistics/dl/loan/prime/prime.htm、https://www.stat-search.boj.or.jp/api/v1/getDataCode
- 國交省 デフレーター：https://www.mlit.go.jp/statistics/details/content/deftsuki_<YYMM>.xlsx
- 中小企業庁：https://www.chusho.meti.go.jp/koukai/chousa/tousan/bankruptcy.xlsx
- 國交省 建設労働需給：https://www.mlit.go.jp/toukeijouhou/chojou/ex/labor_xls_data/labor_R<NN>.<MM>.xls
- Yahoo Finance：https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>
"""
import datetime
import io
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True, parents=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
MLIT = "https://www.mlit.go.jp/sogoseisaku/jouhouka/content"
TODAY = datetime.date.today()
ERA = {"S": 1925, "H": 1988, "R": 2018}


def get(url, binary=True, impersonate=False, verify=True, **kw):
    """GET，失敗拋例外。impersonate=True 時用 curl_cffi 模擬 Chrome（部分政府站會擋一般 requests）。
    verify=False 只給憑證鏈不完整的公開站（reins.or.jp）。"""
    if not verify:
        r = requests.get(url, headers=UA, timeout=60, verify=False, **kw)
    elif impersonate and cffi_requests:
        r = cffi_requests.get(url, impersonate="chrome", timeout=60, **kw)
    else:
        r = requests.get(url, headers=UA, timeout=60, **kw)
    r.raise_for_status()
    return r.content if binary else r.text


def num(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan
    s = str(v).strip().replace(",", "")
    if s in ("", "－", "-", "…", "nan", "None", "x", "X"):
        return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def months_back(n):
    """由本月起往前 n 個月的 (year, month)。"""
    y, m = TODAY.year, TODAY.month
    for _ in range(n):
        yield y, m
        m -= 1
        if m == 0:
            y, m = y - 1, 12


def reiwa(y, m):
    return f"labor_R{y - 2018:02d}.{m:02d}.xls"


def yahoo_chart(ticker, range_str="10y"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_str}&interval=1d"
    res = requests.get(url, headers=UA, timeout=60)
    res.raise_for_status()
    result = res.json()["chart"]["result"][0]
    q = result["indicators"]["quote"][0]
    jst = datetime.timezone(datetime.timedelta(hours=9))
    rows = []
    for ts, o, h, lo, c, v in zip(result["timestamp"], q["open"], q["high"], q["low"], q["close"], q["volume"]):
        if c is None:
            continue
        rows.append({
            "date": datetime.datetime.fromtimestamp(ts, jst).strftime("%Y-%m-%d"),
            "open": o, "high": h, "low": lo, "close": c, "volume": v,
        })
    return pd.DataFrame(rows).drop_duplicates("date").sort_values("date").reset_index(drop=True)


# =========================================================
# 量：國交省建築着工統計
# =========================================================
def build_starts_monthly_use():
    print("[1/14] 國交省 新設住宅着工 利用関係別（月）...")
    df = pd.read_excel(io.BytesIO(get(f"{MLIT}/jyuu_ken.xls")), sheet_name="jyuu", header=None)
    records, year = [], None
    for i in range(46, len(df)):
        raw = str(df.iloc[i, 0]).strip()
        if raw in ("nan", "", "None"):
            continue
        c0 = unicodedata.normalize("NFKC", raw).replace(" ", "")
        m_ym = re.match(r"^([SHR])(\d+)年(\d+)月?$", c0)
        if m_ym:
            era, ey, month = m_ym.groups()
            year, month = ERA[era] + int(ey), int(month)
        else:
            m_m = re.match(r"^(\d+)月?$", c0)
            if not m_m or year is None:
                continue
            month = int(m_m.group(1))
        tot, area = num(df.iloc[i, 1]), num(df.iloc[i, 3])
        records.append({
            "date": f"{year:04d}-{month:02d}-01",
            "starts_total_units": tot,
            "floor_area_1000sqm": area,
            "avg_floor_area_sqm": round(area * 1000 / tot, 2) if tot and not np.isnan(area) and tot > 0 else np.nan,
            "starts_owner_units": num(df.iloc[i, 5]),            # 持家
            "starts_rental_units": num(df.iloc[i, 9]),           # 貸家
            "starts_issued_units": num(df.iloc[i, 11]),          # 給与住宅
            "starts_sale_units": num(df.iloc[i, 13]),            # 分譲住宅
            "starts_condo_units": num(df.iloc[i, 15]),           # 分譲：マンション
            "starts_detached_sale_units": num(df.iloc[i, 18]),   # 分譲：一戸建（建売）
            "starts_saar_k_units": num(df.iloc[i, 20]),          # 季調年率（千戸）
        })
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date").reset_index(drop=True)


def build_starts_annual_history():
    print("[2/14] 國交省 新設住宅着工 利用関係別（年計，1948–）...")
    df = pd.read_excel(io.BytesIO(get(f"{MLIT}/001979030.xls")), sheet_name="年計", header=None)
    era_base = {"昭和": 1925, "平成": 1988, "令和": 2018}
    records, era = [], "昭和"
    for i in range(7, len(df)):
        raw = str(df.iloc[i, 0]).strip()
        if not raw or raw in ("nan", "None") or "※" in raw:
            continue
        for k in era_base:
            if k in raw:
                era, raw = k, raw.replace(k, "")
                break
        raw = raw.replace("年", "").replace("元", "1").strip()
        if not raw.isdigit():
            continue
        tot, area = num(df.iloc[i, 1]), num(df.iloc[i, 2])
        records.append({
            "date": f"{era_base[era] + int(raw):04d}-01-01",
            "starts_total_units": tot,
            "floor_area_sqm": area,
            "avg_floor_area_sqm": round(area / tot, 2) if tot and not np.isnan(area) and tot > 0 else np.nan,
            "starts_owner_units": num(df.iloc[i, 3]),
            "starts_rental_units": num(df.iloc[i, 5]),
            "starts_issued_units": num(df.iloc[i, 7]),
            "starts_sale_units": num(df.iloc[i, 9]),
            "starts_condo_units": num(df.iloc[i, 11]),
            "starts_detached_sale_units": num(df.iloc[i, 13]),
        })
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date").reset_index(drop=True)


def build_starts_shutoken():
    print("[3/14] 國交省 首都圏月度着工（東京・神奈川・埼玉・千葉）...")
    xls = pd.ExcelFile(io.BytesIO(get(f"{MLIT}/kenbetu808.xls")))
    names = {"東京", "東京都", "神奈川", "神奈川県", "埼玉", "埼玉県", "千葉", "千葉県"}
    records = []
    for s in xls.sheet_names:
        m = re.match(r"^(\d+)年(\d+)月$", unicodedata.normalize("NFKC", s).strip())
        if not m:
            continue
        y_raw, month = int(m.group(1)), int(m.group(2))
        year = (2018 + y_raw) if y_raw <= 10 else (1988 + y_raw)  # 令和 1–10 / 平成 11–30
        df = pd.read_excel(xls, s, header=None)
        acc, found = dict.fromkeys(["total", "owner", "rental", "condo", "detached"], 0.0), 0
        for i in range(len(df)):
            if str(df.iloc[i, 1]).strip() in names:
                found += 1
                for key, col in (("total", 2), ("owner", 4), ("rental", 6), ("condo", 12), ("detached", 14)):
                    v = num(df.iloc[i, col])
                    acc[key] += 0 if np.isnan(v) else v
        if found == 4:
            records.append({
                "date": f"{year:04d}-{month:02d}-01",
                "shutoken_starts_total_units": acc["total"],
                "shutoken_starts_owner_units": acc["owner"],
                "shutoken_starts_rental_units": acc["rental"],
                "shutoken_starts_condo_units": acc["condo"],
                "shutoken_starts_detached_sale_units": acc["detached"],
            })
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date").reset_index(drop=True)


def build_starts_structure():
    print("[4/14] 國交省 構造別（木造）與工法別（プレハブ、ツーバイフォー）...")
    df2 = pd.read_excel(io.BytesIO(get(f"{MLIT}/jyuu2.xls")), header=None)
    df3 = pd.read_excel(io.BytesIO(get(f"{MLIT}/jyuu3.xls")), header=None)
    records = []
    for i in range(41, len(df2)):
        raw = str(df2.iloc[i, 0]).strip()
        if not raw or raw in ("nan", "None") or "※" in raw:
            continue
        m = re.match(r"^(\d+)年(\d+)月$", unicodedata.normalize("NFKC", raw).replace(" ", ""))
        if not m:
            continue
        y_raw, month = int(m.group(1)), int(m.group(2))
        year = (2018 + y_raw) if y_raw <= 10 else (1988 + y_raw)
        tot, wood = num(df3.iloc[i, 1]), num(df3.iloc[i, 3])
        prefab, tbf = num(df2.iloc[i, 1]), num(df2.iloc[i, 11])

        def pct(x):
            return round(x / tot * 100, 2) if tot and not np.isnan(x) else np.nan

        records.append({
            "date": f"{year:04d}-{month:02d}-01",
            "starts_total_units": tot,
            "starts_wood_units": wood, "wood_ratio_pct": pct(wood),
            "starts_prefab_units": prefab, "prefab_ratio_pct": pct(prefab),
            "starts_two_by_four_units": tbf, "two_by_four_ratio_pct": pct(tbf),
        })
    return pd.DataFrame(records).drop_duplicates("date").sort_values("date").reset_index(drop=True)


# =========================================================
# 價：不動産価格指数、REINS
# =========================================================
def _find_price_index_url():
    """從國交省頁面找最新的 不動産価格指数（住宅）Excel；找不到就用 probe 時的固定檔。"""
    page = "https://www.mlit.go.jp/totikensangyo/totikensangyo_tk5_000085.html"
    try:
        html = get(page, binary=False, impersonate=True)
        # 頁面上的 xlsx 連結：以「住宅」「季節調整」附近的連結優先，其次取第一個 /content/*.xlsx
        links = re.findall(r'href="([^"]*content/\d+\.xlsx)"', html)
        for href in links:
            return requests.compat.urljoin(page, href)
    except Exception as e:
        print(f"  價格指數頁面解析失敗，改用固定檔: {e}")
    return "https://www.mlit.go.jp/totikensangyo/content/001473668.xlsx"


def build_price_index():
    print("[5/14] 國交省 不動産価格指数（住宅）...")
    import openpyxl
    candidates = [_find_price_index_url(), "https://www.mlit.go.jp/totikensangyo/content/001473668.xlsx"]
    wb = None
    for url in dict.fromkeys(candidates):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(get(url, impersonate=True)), data_only=True)
            if "全国Japan季節調整" in wb.sheetnames:
                print(f"  使用 {url}")
                break
        except Exception as e:
            print(f"  {url} 失敗: {e}")
            wb = None
    if wb is None:
        raise RuntimeError("找不到可用的不動産価格指数檔案")

    sheets = {"national": "全国Japan季節調整", "minamikanto": "南関東圏Tokyo including季節調整", "tokyo": "東京都Tokyo季節調整"}
    # 欄位：1 合計、4 土地、7 戸建、10 マンション
    cols = {1: "composite_idx", 4: "land_idx", 7: "detached_idx", 10: "condo_idx"}
    records = {}
    for key, sheet in sheets.items():
        if sheet not in wb.sheetnames:
            continue
        for r in list(wb[sheet].iter_rows(values_only=True))[9:]:
            if not isinstance(r[0], (datetime.datetime, datetime.date)):
                continue
            d = r[0].strftime("%Y-%m-01")
            rec = records.setdefault(d, {"date": d})
            for ci, suffix in cols.items():
                if len(r) > ci and r[ci] is not None:
                    rec[f"{key}_{suffix}"] = round(float(r[ci]), 2)
    return pd.DataFrame([records[k] for k in sorted(records)])


def _parse_reins_pdf(data):
    import pypdf
    reader = pypdf.PdfReader(io.BytesIO(data))

    def table(page_idx):
        text = reader.pages[page_idx].extract_text().split("○東京都")[0]
        out, year = {}, None
        for line in text.splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            m = re.match(r"^(\d{2})/(\d{2})$", parts[0])
            if m:
                year = f"20{m.group(1)}"
                d = f"{year}-{m.group(2)}-01"
            elif re.match(r"^\d{2}$", parts[0]) and year and 1 <= int(parts[0]) <= 12:
                d = f"{year}-{parts[0]}-01"
            else:
                continue
            if len(parts) >= 4:
                out[d] = parts[1:]
        return out

    condo, used_h, new_h = table(1), table(19), table(40)
    rows = []
    for d in sorted(set(condo) | set(used_h) | set(new_h)):
        def pick(t, i, cast):
            return cast(t[d][i].replace(",", "")) if d in t else np.nan
        rows.append({
            "date": d,
            "used_condo_contracts_units": pick(condo, 0, int),
            "used_condo_sqm_price_jpy_10k": pick(condo, 2, float),
            "used_condo_price_jpy_10k": pick(condo, 5, int),
            "used_detached_contracts_units": pick(used_h, 0, int),
            "used_detached_price_jpy_10k": pick(used_h, 2, int),
            "new_detached_contracts_units": pick(new_h, 0, int),
            "new_detached_price_jpy_10k": pick(new_h, 2, int),
        })
    return pd.DataFrame(rows)


def build_reins():
    print("[6/14] 東日本 REINS Market Watch（PDF，往前找最新一期）...")
    new = None
    for y, m in months_back(8):
        url = f"http://www.reins.or.jp/pdf/trend/mw/MW_{y}{m:02d}data.pdf"
        try:
            new = _parse_reins_pdf(get(url, verify=False))  # reins.or.jp 憑證鏈不完整
            print(f"  使用 {url}（{len(new)} 個月）")
            break
        except Exception as e:
            print(f"  {y}{m:02d} 不可用: {str(e)[:60]}")
    if new is None or new.empty:
        raise RuntimeError("找不到可用的 REINS Market Watch")
    # PDF 只有近 13 個月：與先前抓過的檔案合併累積，新抓的覆蓋舊的
    old_path = OUT / "reins_market_watch.csv"
    if old_path.exists():
        old = pd.read_csv(old_path)
        new = pd.concat([old, new]).drop_duplicates("date", keep="last")
    return new.sort_values("date").reset_index(drop=True)


# =========================================================
# 利率
# =========================================================
def build_policy_rate():
    print("[7/14] 日銀政策利率（BIS WS_CBPOL）...")
    last_err = None
    for freq in ("D", "M"):
        try:
            text = get(f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/{freq}.JP?format=csv", binary=False)
            df = pd.read_csv(io.StringIO(text))
            df = df.rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "boj_policy_rate_pct"})[["date", "boj_policy_rate_pct"]]
            df = df.dropna()
            if freq == "M":
                df["date"] = df["date"] + "-01"
            df = df.sort_values("date").reset_index(drop=True)
            print(f"  使用 {freq} 頻率")
            return df
        except Exception as e:
            last_err = e
    raise RuntimeError(f"BIS 失敗: {last_err}")


def build_jgb_yield():
    print("[8/14] 財務省 國債利回り...")
    text = get("https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv").decode("shift_jis", errors="ignore")
    # 欄位：基準日,1年,2年,3年,4年,5年,6年,7年,8年,9年,10年,15年,20年,25年,30年,40年
    keep = {1: "jgb_1y_yield_pct", 5: "jgb_5y_yield_pct", 10: "jgb_10y_yield_pct", 20: "jgb_20y_yield_pct", 30: "jgb_30y_yield_pct"}
    header = next(l for l in text.splitlines() if l.startswith("基準日"))
    names = [c.strip() for c in header.split(",")]
    col_idx = {int(re.match(r"(\d+)", n).group(1)): i for i, n in enumerate(names) if re.match(r"^\d+年$", n)}
    rows = []
    for line in text.splitlines():
        parts = line.split(",")
        m = re.match(r"^([SHR])(\d+)\.(\d+)\.(\d+)$", parts[0].strip())
        if not m:
            continue
        era, y, mo, d = m.groups()
        rec = {"date": f"{ERA[era] + int(y):04d}-{int(mo):02d}-{int(d):02d}"}
        for tenor, col in keep.items():
            rec[col] = num(parts[col_idx[tenor]]) if tenor in col_idx and col_idx[tenor] < len(parts) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def build_prime_rate():
    print("[9/14] 日銀 短期／長期プライムレート...")
    from bs4 import BeautifulSoup
    html = get("https://www.boj.or.jp/statistics/dl/loan/prime/prime.htm", binary=False)
    table = BeautifulSoup(html, "html.parser").find("table")

    def val(s):
        if "↓" in s:
            return None  # 「↓」＝同上一列
        m = re.match(r"^([\d.]+)", s.replace("不定", "").strip())
        return float(m.group(1)) if m else None

    last = [None] * 4
    rows = []
    for tr in table.find_all("tr")[2:]:
        tds = tr.find_all(["td", "th"])
        texts = [td.text.strip().replace("\xa0", " ") for td in tds]
        m = re.search(r"（(\d{4})）年\s*(\d+)月\s*(\d+)日", " ".join(texts))
        if not m:
            continue
        for i, t in enumerate(texts[-4:]):
            v = val(t)
            if v is not None:
                last[i] = v
        rows.append({
            "date": f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}",
            "short_prime_mode_pct": last[0], "short_prime_max_pct": last[1],
            "short_prime_min_pct": last[2], "long_prime_rate_pct": last[3],
        })
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


# =========================================================
# 成本與供給
# =========================================================
def build_deflator():
    print("[10/14] 國交省 建設工事費デフレーター...")
    import openpyxl
    wb = None
    for y, m in months_back(10):
        url = f"https://www.mlit.go.jp/statistics/details/content/deftsuki_{y % 100:02d}{m:02d}.xlsx"
        try:
            wb = openpyxl.load_workbook(io.BytesIO(get(url)), data_only=True)
            print(f"  使用 {url}")
            break
        except Exception:
            continue
    if wb is None:
        raise RuntimeError("找不到 deftsuki_YYMM.xlsx")
    ws = wb["deftsuki2020（月別）"]
    rows = []
    for r in list(ws.iter_rows(values_only=True))[10:]:
        y, m = r[0], r[1]
        if y is None or m is None or not str(y).strip().isdigit() or not str(m).strip().isdigit() or r[2] in (None, ""):
            continue
        rows.append({
            "date": f"{int(str(y).strip()):04d}-{int(str(m).strip()):02d}-01",
            "deflator_total": num(r[2]), "deflator_building_total": num(r[3]),
            "deflator_residential_total": num(r[4]), "deflator_wooden_housing": num(r[5]),
            "deflator_nonwooden_housing": num(r[6]),
        })
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def build_ppi():
    print("[11/14] 日銀 企業物價指數：建材...")
    codes = {
        "ppi_lumber_wood_products": "PRCG20_2200320001",
        "ppi_sawnwood": "PRCG20_2200340001",
        "ppi_plywood": "PRCG20_2200340002",
        "ppi_cement": "PRCG20_2200840004",
        "ppi_steel": "PRCG20_2200920001",
    }
    end = f"{TODAY.year}{TODAY.month:02d}"
    merged = None
    for col, code in codes.items():
        url = f"https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=PR01&code={code}&startDate=201501&endDate={end}"
        res = requests.get(url, headers=UA, timeout=60).json()
        if res.get("STATUS") != 200:
            print(f"  {code}: {res.get('MESSAGE')}")
            continue
        vals = res["RESULTSET"][0]["VALUES"]
        d = pd.DataFrame({
            "date": [f"{str(x)[:4]}-{str(x)[4:6]}-01" for x in vals["SURVEY_DATES"]],
            col: [None if v is None else float(v) for v in vals["VALUES"]],
        }).dropna()
        merged = d if merged is None else merged.merge(d, on="date", how="outer")
    if merged is None:
        raise RuntimeError("BOJ PPI 全數失敗")
    return merged.sort_values("date").reset_index(drop=True)


def build_bankruptcy():
    print("[12/14] 中小企業庁 倒産の状況（TSR 轉載）...")
    import openpyxl
    wb = None
    for suffix in [f"?{y}{m:02d}" for y, m in months_back(4)] + [""]:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(get(f"https://www.chusho.meti.go.jp/koukai/chousa/tousan/bankruptcy.xlsx{suffix}", impersonate=True)), data_only=True)
            break
        except Exception:
            continue
    if wb is None:
        raise RuntimeError("bankruptcy.xlsx 下載失敗")

    def walk(ws, start):
        year = None
        for r in list(ws.iter_rows(values_only=True))[start:]:
            if r[0] and "年" in str(r[0]):
                m = re.search(r"(\d{4})", str(r[0]))
                if m:
                    year = int(m.group(1))
            if r[1] and "月" in str(r[1]) and year:
                m = re.search(r"(\d+)", str(r[1]))
                if m:
                    yield f"{year:04d}-{int(m.group(1)):02d}-01", r

    total = {d: int(r[2]) for d, r in walk(wb["倒産の状況（倒産件数、負債総額）"], 15) if r[2] is not None and str(r[2]).strip().isdigit()}
    rows = []
    for d, r in walk(wb["業種別倒産状況"], 13):
        if r[3] is not None and str(r[3]).strip().isdigit():
            rows.append({
                "date": d,
                "bankruptcies_total": total.get(d),
                "bankruptcies_construction": int(r[3]),
                "bankruptcies_real_estate": int(r[8]) if r[8] is not None and str(r[8]).strip().isdigit() else None,
            })
    return pd.DataFrame(rows).drop_duplicates("date").sort_values("date").reset_index(drop=True)


def build_labor_shortage():
    print("[13/14] 國交省 建設労働需給調査（8 職種過不足率）...")
    import xlrd
    book = None
    for y, m in months_back(8):
        url = f"https://www.mlit.go.jp/toukeijouhou/chojou/ex/labor_xls_data/{reiwa(y, m)}"
        try:
            book = xlrd.open_workbook(file_contents=get(url))
            print(f"  使用 {url}")
            break
        except Exception:
            continue
    if book is None:
        raise RuntimeError("找不到 labor_R*.xls")
    sheet = book.sheet_by_name("８職種計推移グラフ")
    # 第一列為 1993-01（平成5年1月），之後逐月；探測起始列：往下找第一個兩欄都是數字的列
    start = next(i for i in range(sheet.nrows) if isinstance(sheet.cell_value(i, 1), float) and isinstance(sheet.cell_value(i, 2), float))
    d = datetime.date(1993, 1, 1)
    rows = []
    for i in range(start, sheet.nrows):
        raw, sa = sheet.cell_value(i, 1), sheet.cell_value(i, 2)
        if isinstance(raw, float) and isinstance(sa, float):
            rows.append({"date": d.strftime("%Y-%m-01"), "labor_shortage_rate_8prof_raw": raw, "labor_shortage_rate_8prof_sa": sa})
        d = datetime.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    df = pd.DataFrame(rows)
    # 檔案預填到未來月份（值為 0），砍掉尾端連續的全 0 列
    empty = (df["labor_shortage_rate_8prof_raw"] == 0) & (df["labor_shortage_rate_8prof_sa"] == 0)
    keep = len(df) - int(empty[::-1].cumprod().sum())
    return df.iloc[:keep].reset_index(drop=True)


# =========================================================
# 公司股價
# =========================================================
STOCKS = [
    ("3291.T", "iida"), ("3288.T", "openhouse"), ("1419.T", "tamahome"), ("7822.T", "eidai"),
    ("7943.T", "nichiha"), ("6083.T", "eri"), ("2975.T", "starmica"), ("1928.T", "sekisui"),
    ("1925.T", "daiwa"), ("1306.T", "topix_etf"),
]


def build_stocks():
    print("[14/14] Yahoo Finance 日股日線...")
    merged = None
    for tk, prefix in STOCKS:
        try:
            d = yahoo_chart(tk)[["date", "close", "volume"]].rename(columns={"close": f"{prefix}_close", "volume": f"{prefix}_volume"})
        except Exception as e:
            print(f"  {tk} 失敗: {e}")
            continue
        merged = d if merged is None else merged.merge(d, on="date", how="outer")
    if merged is None:
        raise RuntimeError("Yahoo 全數失敗")
    return merged.sort_values("date").reset_index(drop=True)


# =========================================================
# 主執行流程
# =========================================================
if __name__ == "__main__":
    jobs = [
        ("starts_monthly_use", build_starts_monthly_use),
        ("starts_annual_history", build_starts_annual_history),
        ("starts_monthly_shutoken", build_starts_shutoken),
        ("starts_monthly_structure", build_starts_structure),
        ("price_index_mlit", build_price_index),
        ("reins_market_watch", build_reins),
        ("policy_rate_boj", build_policy_rate),
        ("jgb_yield", build_jgb_yield),
        ("prime_rate_boj", build_prime_rate),
        ("deflator_construction", build_deflator),
        ("ppi_building_materials", build_ppi),
        ("bankruptcy_monthly", build_bankruptcy),
        ("labor_shortage_monthly", build_labor_shortage),
        ("stocks_daily", build_stocks),
    ]
    only = set(sys.argv[1:])
    print(f"=== 日本地產數據抓取開始，輸出目錄：{OUT} ===")
    summary = []
    for name, fn in jobs:
        if only and name not in only:
            continue
        try:
            df = fn()
            df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")
            first, last = (df["date"].iloc[0], df["date"].iloc[-1]) if len(df) else ("N/A", "N/A")
            print(f"  -> [OK] {name:26s} rows={len(df):6d}  ({first} 至 {last})")
            summary.append((name, len(df), first, last, "OK"))
        except Exception as e:
            print(f"  -> [FAIL] {name:26s} {e}")
            summary.append((name, 0, "", "", f"FAIL: {e}"))

    print("\n=== 抓取完成摘要 ===")
    for s in summary:
        print(f"{s[0]:26s} rows={s[1]:6d}  {s[2]} → {s[3]}  [{s[4]}]")
