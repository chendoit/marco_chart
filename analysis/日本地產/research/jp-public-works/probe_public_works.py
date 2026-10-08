# -*- coding: utf-8 -*-
"""
公共工事先行指標與營建供給受限數據採集與探測腳本 (probe_public_works.py)
用途：自動探測與下載公共工事前払金保証、建設受注、水泥/生コン、建機出貨、勞動求人倍率等核心指標。
輸出目錄：Path(__file__).parent / "samples"
"""

import sys
import os
import io
import csv
import time
from pathlib import Path
import requests

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pypdf
except ImportError:
    pypdf = None

BASE_DIR = Path(__file__).resolve().parent
SAMPLES_DIR = BASE_DIR / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 60

def probe_advance_payment_guarantee():
    """1. 公共工事前払金保証（東日本・西日本建設業保証）"""
    print("[1/6] Probing Advance Payment Guarantee Statistics (EJCS / WJCS)...")
    url_west = "https://www.wjcs.net/files/kokyodoko/maebrai_tokei_202608.xlsx"
    url_east = "https://www.ejcs.co.jp/ejcsv1/wp-content/uploads/2026/09/east_r0808.xls"
    try:
        r = requests.get(url_west, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> WJCS maebrai_tokei_202608.xlsx: HTTP {r.status_code}, {len(r.content)} bytes")
        if r.status_code == 200:
            print("  -> WJCS Excel download successful.")
    except Exception as e:
        print(f"  [ERROR] WJCS probe failed: {e}")

    try:
        r_e = requests.get(url_east, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> EJCS east_r0808.xls: HTTP {r_e.status_code}, {len(r_e.content)} bytes")
    except Exception as e:
        print(f"  [ERROR] EJCS probe failed: {e}")

def probe_ready_mixed_concrete():
    """2. 全国生コンクリート出荷実績（全生連）"""
    print("[2/6] Probing Ready-Mixed Concrete Shipment (Zennama)...")
    url_z = "https://www.zennama.or.jp/3-toukei/getuji/pdf/r_08_shukka.pdf"
    try:
        r = requests.get(url_z, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> Zennama r_08_shukka.pdf: HTTP {r.status_code}, {len(r.content)} bytes")
        if r.status_code == 200 and pypdf is not None:
            reader = pypdf.PdfReader(io.BytesIO(r.content))
            print(f"  -> PDF parsed successfully, total {len(reader.pages)} pages")
    except Exception as e:
        print(f"  [ERROR] Zennama probe failed: {e}")

def probe_cement_association():
    """3. セメント需給（セメント協会）"""
    print("[3/6] Probing Cement Domestic Demand (Cement Association)...")
    url_c = "https://www.jcassoc.or.jp/cement/1jpn/jh1.html"
    try:
        r = requests.get(url_c, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> Cement Assoc jh1.html: HTTP {r.status_code}, {len(r.content)} bytes")
    except Exception as e:
        print(f"  [ERROR] Cement Association probe failed: {e}")

def probe_construction_machinery():
    """4. 建設機械出荷金額統計（日本建設機械工業会 CEMA）"""
    print("[4/6] Probing Construction Machinery Shipment (CEMA)...")
    url_cema = "https://www.cema.or.jp/general/statistics/tmfjj600000003nc-att/shipment_value_Statistics_DomesticDemand_ExternalDemand_2026.xlsx?1791350570742"
    try:
        r = requests.get(url_cema, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> CEMA shipment 2026.xlsx: HTTP {r.status_code}, {len(r.content)} bytes")
    except Exception as e:
        print(f"  [ERROR] CEMA probe failed: {e}")

def probe_construction_orders_mlit():
    """5. 建設工事受注動態統計（国土交通省 大手50社）"""
    print("[5/6] Probing MLIT Construction Orders 50 Firms...")
    url_mlit = "https://www.mlit.go.jp/report/press/joho04_hh_001300.html"
    try:
        r = requests.get(url_mlit, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> MLIT Orders press page: HTTP {r.status_code}, {len(r.content)} bytes")
    except Exception as e:
        print(f"  [ERROR] MLIT orders probe failed: {e}")

def probe_labor_job_openings():
    """6. 一般職業紹介状況（厚生労働省 有効求人倍率）"""
    print("[6/6] Probing Job Openings Ratio (MHLW)...")
    url_mhlw = "https://www.mhlw.go.jp/stf/houdou/index.html"
    try:
        r = requests.get(url_mhlw, headers=HEADERS, timeout=TIMEOUT)
        print(f"  -> MHLW press release page: HTTP {r.status_code}, {len(r.content)} bytes")
    except Exception as e:
        print(f"  [ERROR] MHLW probe failed: {e}")

def main():
    print("=" * 60)
    print("Starting probe_public_works.py execution...")
    print(f"Target sample directory: {SAMPLES_DIR}")
    print("=" * 60)
    probe_advance_payment_guarantee()
    probe_ready_mixed_concrete()
    probe_cement_association()
    probe_construction_machinery()
    probe_construction_orders_mlit()
    probe_labor_job_openings()
    print("=" * 60)
    print("Probe finished. Existing samples preserved in:", SAMPLES_DIR)

if __name__ == "__main__":
    main()
