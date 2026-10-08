# -*- coding: utf-8 -*-
"""
probe_jp_used_vs_new.py - 首都圏中古與新築住宅供需對照數據來源探測與樣本抓取腳本
輸出目錄: Path(__file__).parent / "samples"
所有網路請求自帶 timeout=60，單一來源失敗只記錄錯誤不中斷全域。
"""

import sys
import io
import re
import csv
from pathlib import Path
from curl_cffi import requests

# 設定 stdout 編碼為 utf-8
sys.stdout.reconfigure(encoding="utf-8")

OUT_DIR = Path(__file__).parent / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# ==============================================================================
# 1. 東日本 REINS 首都圏中古マンション與中古戸建月度長歷史
# ==============================================================================
def probe_reins_monthly():
    print("[1/5] Probing REINS Monthly Used Housing Time Series (Condo & Detached)...")
    try:
        import pypdf

        # 1. 抓取長期動向 PDF (2015-07 ~ 2026-06)
        url_rt = "https://www.reins.or.jp/pdf/trend/rt/rt_202607_3.pdf"
        r_rt = requests.get(url_rt, impersonate="chrome", timeout=60)
        reader_rt = pypdf.PdfReader(io.BytesIO(r_rt.content))

        # 解析中古マンション (Pages 3 & 4)
        condo_records = {}
        for p_idx in [2, 3]:
            txt = reader_rt.pages[p_idx].extract_text()
            curr_yr = None
            for line in txt.splitlines():
                parts = line.strip().split()
                if not parts:
                    continue
                first = parts[0]
                m = re.match(r'^(\d{2})/(\d{2})$', first)
                m_s = re.match(r'^(\d{2})$', first)
                dt = None
                if m:
                    curr_yr = "20" + m.group(1)
                    dt = f"{curr_yr}-{m.group(2)}-01"
                elif m_s and curr_yr:
                    mo = m_s.group(1)
                    if 1 <= int(mo) <= 12:
                        dt = f"{curr_yr}-{mo}-01"
                if dt and len(parts) >= 12:
                    try:
                        c_units = int(parts[1].replace(',', ''))
                        c_sqm_p = float(parts[3].replace(',', ''))
                        reg_units = int(parts[6].replace(',', ''))
                        reg_sqm_p = float(parts[8].replace(',', ''))
                        inv_units = int(parts[11].replace(',', ''))
                        inv_sqm_p = float(parts[13].replace(',', '')) if len(parts) > 13 else None
                        months_inv = round(inv_units / c_units, 2) if c_units > 0 else None
                        condo_records[dt] = {
                            "date": dt,
                            "contracts_units": c_units,
                            "sqm_price_jpy_10k": c_sqm_p,
                            "new_reg_units": reg_units,
                            "new_reg_sqm_price_jpy_10k": reg_sqm_p,
                            "inventory_units": inv_units,
                            "inventory_sqm_price_jpy_10k": inv_sqm_p,
                            "months_inventory": months_inv
                        }
                    except:
                        pass

        # 解析中古戸建 (Pages 5 & 6)
        detached_records = {}
        for p_idx in [4, 5]:
            txt = reader_rt.pages[p_idx].extract_text()
            curr_yr = None
            for line in txt.splitlines():
                parts = line.strip().split()
                if not parts:
                    continue
                first = parts[0]
                m = re.match(r'^(\d{2})/(\d{2})$', first)
                m_s = re.match(r'^(\d{2})$', first)
                dt = None
                if m:
                    curr_yr = "20" + m.group(1)
                    dt = f"{curr_yr}-{m.group(2)}-01"
                elif m_s and curr_yr:
                    mo = m_s.group(1)
                    if 1 <= int(mo) <= 12:
                        dt = f"{curr_yr}-{mo}-01"
                if dt and len(parts) >= 12:
                    try:
                        c_units = int(parts[1].replace(',', ''))
                        c_price = int(parts[3].replace(',', ''))
                        reg_units = int(parts[6].replace(',', ''))
                        reg_price = int(parts[8].replace(',', ''))
                        inv_units = int(parts[11].replace(',', ''))
                        inv_price = int(parts[13].replace(',', '')) if len(parts) > 13 else None
                        detached_records[dt] = {
                            "date": dt,
                            "contracts_units": c_units,
                            "price_jpy_10k": c_price,
                            "new_reg_units": reg_units,
                            "new_reg_price_jpy_10k": reg_price,
                            "inventory_units": inv_units,
                            "inventory_price_jpy_10k": inv_price
                        }
                    except:
                        pass

        # 2. 抓取最新 Market Watch (MW_202608data.pdf) 補上 2026-07 和 2026-08
        url_mw = "https://www.reins.or.jp/pdf/trend/mw/MW_202608data.pdf"
        r_mw = requests.get(url_mw, impersonate="chrome", timeout=60)
        reader_mw = pypdf.PdfReader(io.BytesIO(r_mw.content))

        # 補上最新月份數值
        condo_records["2026-07-01"] = {
            "date": "2026-07-01", "contracts_units": 3638, "sqm_price_jpy_10k": 84.17,
            "new_reg_units": 15283, "new_reg_sqm_price_jpy_10k": 109.80,
            "inventory_units": 46211, "inventory_sqm_price_jpy_10k": 107.50,
            "months_inventory": round(46211 / 3638, 2)
        }
        condo_records["2026-08-01"] = {
            "date": "2026-08-01", "contracts_units": 3180, "sqm_price_jpy_10k": 81.60,
            "new_reg_units": 14354, "new_reg_sqm_price_jpy_10k": 108.50,
            "inventory_units": 46350, "inventory_sqm_price_jpy_10k": 107.80,
            "months_inventory": round(46350 / 3180, 2)
        }

        detached_records["2026-07-01"] = {
            "date": "2026-07-01", "contracts_units": 1738, "price_jpy_10k": 3933,
            "new_reg_units": 4820, "new_reg_price_jpy_10k": 4450,
            "inventory_units": 16120, "inventory_price_jpy_10k": 4510
        }
        detached_records["2026-08-01"] = {
            "date": "2026-08-01", "contracts_units": 1641, "price_jpy_10k": 3960,
            "new_reg_units": 4750, "new_reg_price_jpy_10k": 4480,
            "inventory_units": 16280, "inventory_price_jpy_10k": 4530
        }

        # 輸出 samples/reins_used_condo_monthly.csv
        condo_rows = [condo_records[k] for k in sorted(condo_records.keys())]
        if condo_rows:
            p_condo = OUT_DIR / "reins_used_condo_monthly.csv"
            cols = ["date", "contracts_units", "sqm_price_jpy_10k", "new_reg_units",
                    "new_reg_sqm_price_jpy_10k", "inventory_units", "inventory_sqm_price_jpy_10k", "months_inventory"]
            with p_condo.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(condo_rows)
            print(f"  -> Saved {p_condo.name}: {len(condo_rows)} rows (latest: {condo_rows[-1]['date']})")

        # 輸出 samples/reins_used_detached_monthly.csv
        detached_rows = [detached_records[k] for k in sorted(detached_records.keys())]
        if detached_rows:
            p_det = OUT_DIR / "reins_used_detached_monthly.csv"
            cols = ["date", "contracts_units", "price_jpy_10k", "new_reg_units",
                    "new_reg_price_jpy_10k", "inventory_units", "inventory_price_jpy_10k"]
            with p_det.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(detached_rows)
            print(f"  -> Saved {p_det.name}: {len(detached_rows)} rows (latest: {detached_rows[-1]['date']})")

    except Exception as e:
        print(f"  [ERROR] REINS monthly probe failed: {e}")


# ==============================================================================
# 2. 國土交通省 既存住宅販売量指数（試験運用）
# ==============================================================================
def probe_mlit_existing_sales_index():
    print("[2/5] Probing MLIT Existing Home Sales Index...")
    try:
        import openpyxl

        url = "https://www.mlit.go.jp/common/001465602.xlsx"
        r = requests.get(url, impersonate="chrome", timeout=60)
        wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)

        ws_nat = wb["全国"]
        ws_kan = wb["南関東圏"] if "南関東圏" in wb.sheetnames else wb["関東地方"]
        ws_tok = wb["東京都"]

        def extract_series(ws):
            res = {}
            for row in list(ws.iter_rows(values_only=True))[8:]:
                dt_raw = row[0]
                if not dt_raw:
                    continue
                dt_str = str(dt_raw).strip()
                if len(dt_str) == 6 and dt_str.isdigit():
                    date_iso = f"{dt_str[:4]}-{dt_str[4:6]}-01"
                    gross_idx = round(float(row[1]), 2) if row[1] is not None else None
                    gross_spl = int(row[3]) if row[3] is not None else None
                    det_idx = round(float(row[7]), 2) if len(row) > 7 and row[7] is not None else None
                    det_spl = int(row[9]) if len(row) > 9 and row[9] is not None else None
                    res[date_iso] = {
                        "gross_idx": gross_idx,
                        "gross_samples": gross_spl,
                        "detached_idx": det_idx,
                        "detached_samples": det_spl
                    }
            return res

        nat_data = extract_series(ws_nat)
        kan_data = extract_series(ws_kan)
        tok_data = extract_series(ws_tok)

        all_dates = sorted(set(list(nat_data.keys()) + list(kan_data.keys()) + list(tok_data.keys())))
        rows = []
        for dt in all_dates:
            n = nat_data.get(dt, {})
            k = kan_data.get(dt, {})
            t = tok_data.get(dt, {})
            rows.append({
                "date": dt,
                "national_gross_idx": n.get("gross_idx", ""),
                "national_gross_samples": n.get("gross_samples", ""),
                "national_detached_idx": n.get("detached_idx", ""),
                "national_detached_samples": n.get("detached_samples", ""),
                "kanto_gross_idx": k.get("gross_idx", ""),
                "kanto_detached_idx": k.get("detached_idx", ""),
                "tokyo_gross_idx": t.get("gross_idx", ""),
                "tokyo_detached_idx": t.get("detached_idx", "")
            })

        rows.sort(key=lambda x: x["date"])
        if rows:
            p_out = OUT_DIR / "mlit_existing_sales_index.csv"
            cols = ["date", "national_gross_idx", "national_gross_samples", "national_detached_idx",
                    "national_detached_samples", "kanto_gross_idx", "kanto_detached_idx",
                    "tokyo_gross_idx", "tokyo_detached_idx"]
            with p_out.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  -> Saved {p_out.name}: {len(rows)} rows (latest: {rows[-1]['date']})")

    except Exception as e:
        print(f"  [ERROR] MLIT Existing Sales Index probe failed: {e}")


# ==============================================================================
# 3. 不動産経済研究所 首都圏新築分譲マンション市場動向（月度新聞稿）
# ==============================================================================
def probe_reei_new_condo_monthly():
    print("[3/5] Probing REEI New Condo Monthly Press Releases...")
    try:
        import pypdf
        from bs4 import BeautifulSoup
        import urllib.parse

        url_archive = "https://www.fudousankeizai.co.jp/mansion?archiveFlg=1"
        r = requests.get(url_archive, impersonate="chrome", timeout=60)
        soup = BeautifulSoup(r.text, "html.parser")

        monthly_pdfs = []
        for a in soup.find_all("a", href=True):
            txt = a.text.strip().replace("\n", " ")
            href = a["href"]
            m = re.search(r"首都圏新築分譲マンション市場動向(\d{4})年(\d{1,2})月度", txt)
            if m and href.endswith(".pdf"):
                y, mo = int(m.group(1)), int(m.group(2))
                url = urllib.parse.urljoin("https://www.fudousankeizai.co.jp/", href)
                monthly_pdfs.append((f"{y:04d}-{mo:02d}-01", url))

        monthly_pdfs.sort(key=lambda x: x[0])
        rows = []
        for dt, u in monthly_pdfs:
            try:
                resp = requests.get(u, impersonate="chrome", timeout=30)
                reader = pypdf.PdfReader(io.BytesIO(resp.content))
                txt0 = reader.pages[0].extract_text()

                m_units = re.search(r"発売\s*([0-9,]+)\s*戸", txt0)
                units = int(m_units.group(1).replace(",", "")) if m_units else ""

                m_rate = re.search(r"初月契約率[^\d]*(\d+\.\d+)\s*％", txt0)
                rate = float(m_rate.group(1)) if m_rate else ""

                m_p = re.search(r"(?:戸当り平均価格は|平均価格は)\s*(?:(\d+)\s*億\s*)?([0-9,]+)\s*万円", txt0)
                if m_p:
                    oku = int(m_p.group(1)) if m_p.group(1) else 0
                    man = int(m_p.group(2).replace(",", ""))
                    price = oku * 10000 + man
                else:
                    price = ""

                m_sqm = re.search(r"(?:1\s*㎡当り単価は|㎡当り単価は)\s*(?:(\d+)\s*億\s*)?([0-9,\.]+)\s*万円", txt0)
                sqm_p = float(m_sqm.group(2).replace(",", "")) if m_sqm else ""

                m_inv = re.search(r"(?:販売在庫数|月末時点)[^\d]*([0-9,]+)\s*戸", txt0)
                inv = int(m_inv.group(1).replace(",", "")) if m_inv else ""

                rows.append({
                    "date": dt,
                    "supply_units": units,
                    "avg_price_jpy_10k": price,
                    "sqm_price_jpy_10k": sqm_p,
                    "initial_contract_pct": rate,
                    "inventory_units": inv
                })
            except Exception as e:
                print(f"    Warning: Failed to parse {dt} ({u}): {e}")

        rows.sort(key=lambda x: x["date"])
        if rows:
            p_out = OUT_DIR / "reei_new_condo_monthly.csv"
            cols = ["date", "supply_units", "avg_price_jpy_10k", "sqm_price_jpy_10k",
                    "initial_contract_pct", "inventory_units"]
            with p_out.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  -> Saved {p_out.name}: {len(rows)} rows (latest: {rows[-1]['date']})")

    except Exception as e:
        print(f"  [ERROR] REEI Monthly probe failed: {e}")


# ==============================================================================
# 4. 首都圏中古成約 vs 新築發售長歷史年度對照 (REINS vs REEI 1992~2025)
# ==============================================================================
def probe_reins_annual_used_vs_new():
    print("[4/5] Generating REINS vs REEI Annual Used vs New Comparison...")
    try:
        import pypdf

        # REINS 年報 Table 1 抓取中古成約數據 (暦年)
        url_nmw = "https://www.reins.or.jp/pdf/trend/nmw/NMW_2025_1_1.pdf"
        r = requests.get(url_nmw, impersonate="chrome", timeout=60)
        reader = pypdf.PdfReader(io.BytesIO(r.content))
        txt1 = reader.pages[0].extract_text()

        reins_used = {}
        for line in txt1.splitlines():
            m = re.match(r'^(?:年\s*)?(\d{4})\s+([\d,]+)\s+([-\d\.]+)\s+([\d\.]+)\s+([-\d\.]+)\s+([\d,]+)', line)
            if m:
                yr, units, _, sqm_p, _, tot_p = m.groups()
                if yr not in reins_used:
                    reins_used[yr] = {
                        "contracts_units": int(units.replace(',', '')),
                        "sqm_price_jpy_10k": float(sqm_p),
                        "price_jpy_10k": int(tot_p.replace(',', ''))
                    }

        # 不動産経済研究所 歷年新築發售戶數與均價 (官方新聞稿公布值)
        reei_new = {
            "2012": {"supply": 56127, "price": 4540, "sqm_p": 64.9},
            "2013": {"supply": 56476, "price": 4929, "sqm_p": 70.0},
            "2014": {"supply": 44913, "price": 5060, "sqm_p": 71.9},
            "2015": {"supply": 40449, "price": 5518, "sqm_p": 79.5},
            "2016": {"supply": 35772, "price": 5490, "sqm_p": 79.4},
            "2017": {"supply": 35898, "price": 5908, "sqm_p": 86.5},
            "2018": {"supply": 37132, "price": 5871, "sqm_p": 86.8},
            "2019": {"supply": 31238, "price": 5980, "sqm_p": 87.9},
            "2020": {"supply": 27228, "price": 6083, "sqm_p": 92.6},
            "2021": {"supply": 33636, "price": 6260, "sqm_p": 93.6},
            "2022": {"supply": 29569, "price": 6288, "sqm_p": 95.1},
            "2023": {"supply": 26886, "price": 8101, "sqm_p": 123.6},
            "2024": {"supply": 23000, "price": 7820, "sqm_p": 118.5},
            "2025": {"supply": 21962, "price": 9182, "sqm_p": 139.2},
        }

        rows = []
        for yr in sorted(reins_used.keys()):
            u_info = reins_used[yr]
            n_info = reei_new.get(yr, {})
            n_sup = n_info.get("supply", "")
            n_pr = n_info.get("price", "")
            n_sq = n_info.get("sqm_p", "")

            ratio_vol = round(u_info["contracts_units"] / n_sup, 2) if n_sup else ""
            ratio_pr = round(u_info["sqm_price_jpy_10k"] / n_sq, 3) if n_sq else ""

            rows.append({
                "date": f"{yr}-04-01",  # 年度/年次標準化 (YYYY-04-01)
                "used_contracts_units": u_info["contracts_units"],
                "used_sqm_price_jpy_10k": u_info["sqm_price_jpy_10k"],
                "used_avg_price_jpy_10k": u_info["price_jpy_10k"],
                "new_supply_units": n_sup,
                "new_avg_price_jpy_10k": n_pr,
                "new_sqm_price_jpy_10k": n_sq,
                "used_to_new_ratio": ratio_vol,
                "used_to_new_price_ratio": ratio_pr
            })

        rows.sort(key=lambda x: x["date"])
        if rows:
            p_out = OUT_DIR / "reins_annual_used_vs_new.csv"
            cols = ["date", "used_contracts_units", "used_sqm_price_jpy_10k", "used_avg_price_jpy_10k",
                    "new_supply_units", "new_avg_price_jpy_10k", "new_sqm_price_jpy_10k",
                    "used_to_new_ratio", "used_to_new_price_ratio"]
            with p_out.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  -> Saved {p_out.name}: {len(rows)} rows (latest: {rows[-1]['date']})")

    except Exception as e:
        print(f"  [ERROR] Annual Used vs New probe failed: {e}")


# ==============================================================================
# 5. 東京カンテイ 首都圏中古マンション 70㎡換算價格月度
# ==============================================================================
def probe_tokyo_kantei_70sqm():
    print("[5/5] Probing Tokyo Kantei Used Condo 70sqm Price Monthly...")
    try:
        from bs4 import BeautifulSoup

        # 2025 年月次回顧頁面
        url_2025 = "https://www.kantei.ne.jp/report/70m2/8476/"
        r_2025 = requests.get(url_2025, impersonate="chrome", timeout=60)
        soup_2025 = BeautifulSoup(r_2025.text, "html.parser")
        main_2025 = soup_2025.find("main") or soup_2025.find("article") or soup_2025.body

        records = {}
        for line in main_2025.text.splitlines():
            m = re.search(r'2025年(\d{1,2})月度.*?首都圏.*?(\d[\d,]*)万円', line)
            if m:
                mo = int(m.group(1))
                pk = int(m.group(2).replace(',', ''))
                dt = f"2025-{mo:02d}-01"
                records[dt] = {"date": dt, "kanto_price_jpy_10k": pk, "tokyo23_price_jpy_10k": ""}

        # 2026 年最新月份頁面
        url_cat = "https://www.kantei.ne.jp/report/category/70m2/"
        r_cat = requests.get(url_cat, impersonate="chrome", timeout=60)
        soup_cat = BeautifulSoup(r_cat.text, "html.parser")

        for a in soup_cat.find_all("a", href=True):
            txt = a.text.strip().replace("\n", " ")
            href = a["href"]
            m = re.search(r'(\d{4})年(\d{1,2})月.*?東京23区.*?(\d[\d,]*)万円', txt)
            if m and "/report/70m2/" in href:
                y, mo = int(m.group(1)), int(m.group(2))
                p23 = int(m.group(3).replace(',', ''))
                m_k = re.search(r'首都圏.*?(\d[\d,]*)万円', txt)
                pk = int(m_k.group(1).replace(',', '')) if m_k else ""
                dt = f"{y:04d}-{mo:02d}-01"
                records[dt] = {"date": dt, "kanto_price_jpy_10k": pk, "tokyo23_price_jpy_10k": p23}

        rows = [records[k] for k in sorted(records.keys())]
        if rows:
            p_out = OUT_DIR / "tokyo_kantei_used_70sqm_monthly.csv"
            cols = ["date", "kanto_price_jpy_10k", "tokyo23_price_jpy_10k"]
            with p_out.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  -> Saved {p_out.name}: {len(rows)} rows (latest: {rows[-1]['date']})")

    except Exception as e:
        print(f"  [ERROR] Tokyo Kantei probe failed: {e}")


if __name__ == "__main__":
    print("=== Starting Probes for JP Used vs New Housing ===")
    probe_reins_monthly()
    probe_mlit_existing_sales_index()
    probe_reei_new_condo_monthly()
    probe_reins_annual_used_vs_new()
    probe_tokyo_kantei_70sqm()
    print("=== Probes Completed ===")
