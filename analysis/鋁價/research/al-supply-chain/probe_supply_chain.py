# -*- coding: utf-8 -*-
"""鋁產業鏈供給與貿易流探測與抓取腳本 (Supply Chain & Trade Probe)

覆蓋：
1. IAI 原鋁產量（全球、中國、分區，月度）
2. IAI 冶金級氧化鋁產量（全球、中國，月度）
3. 中國國家統計局 NBS 電解鋁與氧化鋁月度產量（DBnomics 轉載）
4. SHFE 氧化鋁期貨連續合約日行情 (AO0)
5. SHFE 滬鋁期貨連續合約日行情 (AL0)
6. UN Comtrade 中國進口鋁土礦 (HS 260600) 與幾內亞 CIF 推算均價

所有輸出寫入 Path(__file__).parent / "samples"。
每個請求 timeout=60，單一來源失敗只印錯誤、不中斷其他來源。
"""
import io
import json
import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("probe_supply_chain")

OUT_DIR = Path(__file__).resolve().parent / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_TIMEOUT = 60
COMMON_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def fetch_iai_data():
    """抓取 IAI 統計數據 (原鋁產量與氧化鋁產量)"""
    logger.info("Fetching IAI statistics...")
    base_url = "https://alvis.international-aluminium.org/api/publication/"
    token = "VqJoChv3cGZei872eHVKUL4kdbk3CG2qw5RUpq8eV4VmMCbCJxncfzOyCo3nknz59qoWzPjVsPFffSULSWceeWAuywurxWiRVXdkqADVfKSvItSkOstAcU8yoiL6Hmr6"
    headers = {
        "User-Agent": COMMON_UA["User-Agent"],
        "x-auth-token": token,
        "Accept": "application/json"
    }

    # 1. Primary Aluminium
    try:
        r = requests.get(f"{base_url}?publication=primary-aluminium-production", headers=headers, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        d = r.json()
        charts = d.get("data", {}).get("publication", {}).get("charts", {})
        data_list = charts.get("data", [])
        
        rows_glo = []
        rows_chn = []
        for item in data_list:
            dt = item["period"]["from"][:10]
            pname = item["period"]["name"]
            d_map = item.get("data", {}).get("85", {})
            tot = d_map.get("11", {}).get("value") if d_map.get("11") else None
            daily = d_map.get("12", {}).get("value") if d_map.get("12") else None
            chn = d_map.get("9", {}).get("value") if d_map.get("9") else None
            
            if tot is not None:
                rows_glo.append({"date": dt, "period": pname, "global_production_kt": tot, "daily_average_kt": daily})
            if chn is not None:
                rows_chn.append({"date": dt, "period": pname, "china_production_kt": chn})

        if rows_glo:
            pd.DataFrame(rows_glo).to_csv(OUT_DIR / "iai_primary_aluminium_production_global.csv", index=False, encoding="utf-8")
            logger.info("Saved iai_primary_aluminium_production_global.csv (%d rows)", len(rows_glo))
        if rows_chn:
            pd.DataFrame(rows_chn).to_csv(OUT_DIR / "iai_primary_aluminium_production_china.csv", index=False, encoding="utf-8")
            logger.info("Saved iai_primary_aluminium_production_china.csv (%d rows)", len(rows_chn))
    except Exception as e:
        logger.error("Failed fetching IAI primary aluminium: %s", e)

    # 2. Alumina Production
    try:
        r = requests.get(f"{base_url}?publication=alumina-production", headers=headers, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        d = r.json()
        charts = d.get("data", {}).get("publication", {}).get("charts", {})
        data_list = charts.get("data", [])
        
        rows_glo = []
        rows_chn = []
        for item in data_list:
            dt = item["period"]["from"][:10]
            pname = item["period"]["name"]
            m_data = item.get("data", {}).get("2", {}) # row 2 is Metallurgical Alumina
            tot = m_data.get("21", {}).get("value") if m_data.get("21") else None
            daily = m_data.get("22", {}).get("value") if m_data.get("22") else None
            chn = m_data.get("19", {}).get("value") if m_data.get("19") else None
            
            if tot is not None:
                rows_glo.append({"date": dt, "period": pname, "global_metallurgical_alumina_kt": tot, "daily_avg_kt": daily})
            if chn is not None:
                rows_chn.append({"date": dt, "period": pname, "china_metallurgical_alumina_kt": chn})

        if rows_glo:
            pd.DataFrame(rows_glo).to_csv(OUT_DIR / "iai_alumina_production_global.csv", index=False, encoding="utf-8")
            logger.info("Saved iai_alumina_production_global.csv (%d rows)", len(rows_glo))
        if rows_chn:
            pd.DataFrame(rows_chn).to_csv(OUT_DIR / "iai_alumina_production_china.csv", index=False, encoding="utf-8")
            logger.info("Saved iai_alumina_production_china.csv (%d rows)", len(rows_chn))
    except Exception as e:
        logger.error("Failed fetching IAI alumina production: %s", e)


def fetch_shfe_futures():
    """抓取 SHFE 期貨日 K 線 (氧化鋁 AO0 與 滬鋁 AL0)"""
    logger.info("Fetching SHFE futures daily klines...")
    headers = {"Referer": "https://finance.sina.com.cn", "User-Agent": COMMON_UA["User-Agent"]}
    
    # AO0
    try:
        url_ao = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AO0"
        r = requests.get(url_ao, headers=headers, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        m = re.search(r"\((.*)\)", r.text)
        if m:
            data = json.loads(m.group(1))
            rows = [{"date": x["d"], "open": x["o"], "high": x["h"], "low": x["l"], "close": x["c"],
                     "volume": x["v"], "open_interest": x["p"], "settle": x["s"]} for x in data]
            pd.DataFrame(rows).to_csv(OUT_DIR / "shfe_alumina_futures_ao.csv", index=False, encoding="utf-8")
            logger.info("Saved shfe_alumina_futures_ao.csv (%d rows)", len(rows))
    except Exception as e:
        logger.error("Failed fetching SHFE AO futures: %s", e)

    # AL0
    try:
        url_al = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AL0"
        r = requests.get(url_al, headers=headers, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        m = re.search(r"\((.*)\)", r.text)
        if m:
            data = json.loads(m.group(1))
            rows = [{"date": x["d"], "open": x["o"], "high": x["h"], "low": x["l"], "close": x["c"],
                     "volume": x["v"], "open_interest": x["p"], "settle": x["s"]} for x in data]
            pd.DataFrame(rows).to_csv(OUT_DIR / "shfe_aluminium_futures_al.csv", index=False, encoding="utf-8")
            logger.info("Saved shfe_aluminium_futures_al.csv (%d rows)", len(rows))
    except Exception as e:
        logger.error("Failed fetching SHFE AL futures: %s", e)


def fetch_nbs_production():
    """抓取中國國家統計局 NBS 工業產品產量 (經 DBnomics)"""
    logger.info("Fetching NBS production via DBnomics...")
    datasets = {
        "electrolytic_aluminum": ("M_A02091H", "nbs_china_electrolytic_aluminum_monthly.csv", "A02091H01", "A02091H02"),
        "alumina": ("M_A02091C", "nbs_china_alumina_monthly.csv", "A02091C01", "A02091C02"),
    }
    for name, (ds, fname, cur_code, acc_code) in datasets.items():
        try:
            url = f"https://api.db.nomics.world/v22/series/NBS/{ds}?observations=1"
            r = requests.get(url, headers=COMMON_UA, timeout=DEFAULT_TIMEOUT)
            r.raise_for_status()
            docs = r.json().get("series", {}).get("docs", [])
            cur_doc = next((x for x in docs if x.get("series_code") == cur_code), None)
            acc_doc = next((x for x in docs if x.get("series_code") == acc_code), None)
            if acc_doc:
                periods = acc_doc.get("period", [])
                acc_vals = acc_doc.get("value", [])
                cur_vals = cur_doc.get("value", []) if cur_doc else [None]*len(periods)
                rows = [{"date": f"{p}-01", "period": p, "monthly_output_10kt": c, "accumulated_output_10kt": a}
                        for p, a, c in zip(periods, acc_vals, cur_vals)]
                pd.DataFrame(rows).to_csv(OUT_DIR / fname, index=False, encoding="utf-8")
                logger.info("Saved %s (%d rows)", fname, len(rows))
        except Exception as e:
            logger.error("Failed fetching NBS %s: %s", name, e)


def fetch_comtrade_bauxite():
    """抓取 UN Comtrade 中國鋁土礦進口 (HS 260600) 並計算幾內亞占比與 CIF 均價"""
    logger.info("Fetching UN Comtrade bauxite data...")
    records = []
    # Query recent 10 years
    years = [str(y) for y in range(2015, 2025)]
    for yr in years:
        url = f"https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={yr}&reporterCode=156&cmdCode=260600&flowCode=M"
        for attempt in range(3):
            try:
                r = requests.get(url, headers=COMMON_UA, timeout=DEFAULT_TIMEOUT)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                    records.extend(data)
                    time.sleep(1.5)
                    break
                elif r.status_code == 429:
                    time.sleep(2.5)
                else:
                    break
            except Exception as e:
                time.sleep(2)

    if records:
        try:
            df = pd.DataFrame(records)
            rows = []
            for p, grp in sorted(df.groupby("period")):
                w_row = grp[grp["partnerCode"] == 0]
                w_val = w_row["primaryValue"].values[0] if len(w_row) else grp["primaryValue"].sum()
                w_qty = w_row["netWgt"].values[0] if len(w_row) and w_row["netWgt"].values[0] else grp["netWgt"].sum()
                
                g_row = grp[grp["partnerCode"] == 324] # Guinea
                g_val = g_row["primaryValue"].values[0] if len(g_row) else 0
                g_qty = g_row["netWgt"].values[0] if len(g_row) else 0

                g_share = (g_qty / w_qty * 100) if w_qty else None
                g_cif = (g_val / (g_qty / 1000)) if g_qty else None
                w_cif = (w_val / (w_qty / 1000)) if w_qty else None
                
                rows.append({
                    "date": f"{p}-12-31",
                    "year": p,
                    "world_import_qty_mt": round(w_qty / 1e9, 3) if w_qty else None,
                    "guinea_import_qty_mt": round(g_qty / 1e9, 3) if g_qty else None,
                    "guinea_share_pct": round(g_share, 2) if g_share else None,
                    "guinea_cif_usd_t": round(g_cif, 2) if g_cif else None,
                    "world_avg_cif_usd_t": round(w_cif, 2) if w_cif else None
                })
            pd.DataFrame(rows).to_csv(OUT_DIR / "china_bauxite_import_guinea_cif.csv", index=False, encoding="utf-8")
            logger.info("Saved china_bauxite_import_guinea_cif.csv (%d rows)", len(rows))
        except Exception as e:
            logger.error("Failed processing Comtrade bauxite records: %s", e)


def main():
    logger.info("Starting supply chain data probe...")
    fetch_iai_data()
    fetch_shfe_futures()
    fetch_nbs_production()
    fetch_comtrade_bauxite()
    logger.info("Supply chain data probe completed.")


if __name__ == "__main__":
    main()
