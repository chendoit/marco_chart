# -*- coding: utf-8 -*-
"""鋁價、期限結構與庫存數據探測與抓取腳本 (al-prices-inventory)

資料來源：
1. LME 鋁 Cash、3M 結算價與庫存：Westmetall (markdaten.php)
2. SHFE 滬鋁連續 (AL0) 與氧化鋁連續 (AO0)：新浪財經期貨 API (InnerFuturesNewService)
3. IMF 全球鋁價與美國 PPI：FRED (PALUMUSDM, WPU102501, WPU1022)
4. COMEX 鋁期貨 (ALI=F) 與鋁業股票：Yahoo Finance API
5. SHFE 倉單日報庫存：東方財富網 Datacenter API (RPT_FUTU_STOCKDATA)
6. COMEX 鋁倉單庫存報告：CME Group Delivery Reports (Aluminum_Stocks.xls)

輸出目錄：同層級 samples/
"""
import io
import re
import json
import datetime
from pathlib import Path
import pandas as pd
from curl_cffi import requests as cffi_requests
import requests
from bs4 import BeautifulSoup

OUT_DIR = Path(__file__).resolve().parent / "samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def probe_lme_westmetall():
    """抓取 LME 現貨價、3M 期貨價、Cash-3M 價差與總庫存 (2008-2026)。"""
    print("[1/6] 正在抓取 Westmetall LME 鋁價與庫存歷史...")
    records = []
    current_year = datetime.date.today().year
    for yr in range(2008, current_year + 1):
        url = f"https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Al_cash&year={yr}"
        try:
            r = cffi_requests.get(url, impersonate="chrome", timeout=60)
            if r.status_code != 200:
                print(f"  Westmetall {yr} HTTP {r.status_code}")
                continue
            soup = BeautifulSoup(r.text, "html.parser")
            tbl = soup.find("table")
            if not tbl:
                continue
            rows = tbl.find_all("tr")
            for tr in rows[1:]:
                cols = [td.text.strip().replace('\xa0', ' ') for td in tr.find_all(["th", "td"])]
                if len(cols) >= 4:
                    try:
                        dt = datetime.datetime.strptime(cols[0], "%d. %B %Y").strftime("%Y-%m-%d")
                        cash = float(cols[1].replace(",", ""))
                        three_m = float(cols[2].replace(",", ""))
                        stock = float(cols[3].replace(",", ""))
                        records.append({
                            "date": dt,
                            "cash": cash,
                            "three_month": three_m,
                            "spread_cash_3m": round(cash - three_m, 2),
                            "stock": stock
                        })
                    except Exception:
                        continue
        except Exception as e:
            print(f"  Westmetall 年份 {yr} 抓取失敗: {e}")

    if records:
        df = pd.DataFrame(records).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        # 輸出 1：價格與價差
        df_p = df[["date", "cash", "three_month", "spread_cash_3m"]]
        df_p.to_csv(OUT_DIR / "lme_al_prices_daily.csv", index=False, encoding="utf-8-sig")
        # 輸出 2：LME 庫存
        df_s = df[["date", "stock"]].rename(columns={"stock": "stock_mt"})
        df_s.to_csv(OUT_DIR / "lme_al_stock_daily.csv", index=False, encoding="utf-8-sig")
        print(f"  -> LME 價格與庫存抓取成功：共 {len(df)} 筆 ({df['date'].min()} 至 {df['date'].max()})")
    else:
        print("  -> LME 抓取失敗，無資料。")


def probe_shfe_sina():
    """抓取 SHFE 滬鋁連續 (AL0) 與氧化鋁連續 (AO0) 日 K 線。"""
    print("[2/6] 正在抓取新浪期貨 SHFE 滬鋁與氧化鋁日 K 線...")
    targets = [
        ("AL0", "shfe_al_futures_daily.csv", "滬鋁連續"),
        ("AO0", "shfe_ao_futures_daily.csv", "氧化鋁連續")
    ]
    for sym, fname, name in targets:
        try:
            url = f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php//InnerFuturesNewService.getDailyKLine?symbol={sym}"
            r = requests.get(url, headers=UA, timeout=60)
            txt = r.text.strip()
            m = re.search(r'\(\s*(\[.*?\])\s*\);?', txt, re.DOTALL)
            if not m:
                print(f"  SHFE {name} ({sym}) 解析失敗: 無法提取 JSON")
                continue
            data = json.loads(m.group(1))
            rows = []
            for it in data:
                rows.append({
                    "date": it["d"],
                    "open": float(it["o"]),
                    "high": float(it["h"]),
                    "low": float(it["l"]),
                    "close": float(it["c"]),
                    "volume": int(it["v"])
                })
            df = pd.DataFrame(rows).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
            df.to_csv(OUT_DIR / fname, index=False, encoding="utf-8-sig")
            print(f"  -> {name} ({sym}) 抓取成功：共 {len(df)} 筆 ({df['date'].min()} 至 {df['date'].max()})")
        except Exception as e:
            print(f"  SHFE {name} ({sym}) 抓取失敗: {e}")


def probe_fred():
    """抓取 FRED 全球鋁均價 (IMF PALUMUSDM) 與美國 PPI 指數。"""
    print("[3/6] 正在抓取 FRED 鋁價與 PPI 月資料...")
    series_map = {
        "PALUMUSDM": "palumusdm_usd_per_mt",
        "WPU102501": "ppi_aluminum_mill_shapes",
        "WPU1022": "ppi_primary_aluminum"
    }
    dfs = []
    for sid, col in series_map.items():
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
            r = cffi_requests.get(url, impersonate="chrome", timeout=60)
            if r.status_code == 200:
                df = pd.read_csv(io.StringIO(r.text))
                df.columns = ["date", col]
                df[col] = pd.to_numeric(df[col], errors="coerce")
                dfs.append(df.dropna())
            else:
                print(f"  FRED {sid} HTTP {r.status_code}")
        except Exception as e:
            print(f"  FRED {sid} 抓取失敗: {e}")

    if dfs:
        merged = dfs[0]
        for d in dfs[1:]:
            merged = pd.merge(merged, d, on="date", how="outer")
        merged = merged.sort_values("date").dropna(subset=["palumusdm_usd_per_mt"]).reset_index(drop=True)
        merged.to_csv(OUT_DIR / "fred_al_prices_monthly.csv", index=False, encoding="utf-8-sig")
        print(f"  -> FRED 序列抓取成功：共 {len(merged)} 筆 ({merged['date'].min()} 至 {merged['date'].max()})")
    else:
        print("  -> FRED 抓取失敗。")


def probe_yahoo():
    """抓取 COMEX 鋁期貨 (ALI=F) 與鋁業股票日線。"""
    print("[4/6] 正在抓取 Yahoo COMEX 鋁期貨與鋁業股票...")
    # 1. COMEX 鋁期貨
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/ALI=F"
        r = requests.get(url, params={"range": "10y", "interval": "1d"}, headers=UA, timeout=60)
        res = r.json()["chart"]["result"][0]
        ts = res.get("timestamp", [])
        q = res["indicators"]["quote"][0]
        rows = []
        for i, t in enumerate(ts):
            dt = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d")
            c = q["close"][i]
            if c is not None:
                rows.append({
                    "date": dt,
                    "open": round(q.get("open", [None])[i] or 0.0, 2),
                    "high": round(q.get("high", [None])[i] or 0.0, 2),
                    "low": round(q.get("low", [None])[i] or 0.0, 2),
                    "close": round(c, 2),
                    "volume": q.get("volume", [0])[i] or 0
                })
        df = pd.DataFrame(rows).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        df.to_csv(OUT_DIR / "comex_al_futures_daily.csv", index=False, encoding="utf-8-sig")
        print(f"  -> COMEX 鋁期貨 (ALI=F) 抓取成功：共 {len(df)} 筆 ({df['date'].min()} 至 {df['date'].max()})")
    except Exception as e:
        print(f"  Yahoo ALI=F 抓取失敗: {e}")

    # 2. 鋁業輔助股票
    equities = ["AA", "CENX", "NHY.OL", "2600.HK", "601600.SS", "1378.HK", "RIO"]
    eq_dfs = {}
    for sym in equities:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
            r = requests.get(url, params={"range": "5y", "interval": "1d"}, headers=UA, timeout=60)
            res = r.json()["chart"]["result"][0]
            ts = res.get("timestamp", [])
            q = res["indicators"]["quote"][0]
            s = pd.Series(
                q["close"],
                index=[datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d") for t in ts]
            ).dropna()
            eq_dfs[sym] = s
        except Exception as e:
            print(f"  Yahoo 股票 {sym} 抓取失敗: {e}")

    if eq_dfs:
        df_eq = pd.DataFrame(eq_dfs).sort_index().reset_index().rename(columns={"index": "date"})
        df_eq.to_csv(OUT_DIR / "yahoo_al_equities_daily.csv", index=False, encoding="utf-8-sig")
        print(f"  -> Yahoo 鋁業股票抓取成功：共 {len(df_eq)} 筆 ({df_eq['date'].min()} 至 {df_eq['date'].max()})")


def probe_shfe_stock_em():
    """抓取上期所滬鋁與氧化鋁倉單日報庫存 (東方財富 Datacenter API)。"""
    print("[5/6] 正在抓取東方財富上期所倉單日報庫存...")
    try:
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_FUTU_STOCKDATA",
            "columns": "SECURITY_CODE,TRADE_DATE,ON_WARRANT_NUM,ADDCHANGE,UNIT",
            "filter": '(SECURITY_CODE="AL")',
            "pageNumber": 1,
            "pageSize": 500,
            "sortTypes": 1,
            "sortColumns": "TRADE_DATE",
            "source": "WEB",
            "client": "WEB"
        }
        r = requests.get(url, params=params, headers=UA, timeout=60)
        items = r.json().get("result", {}).get("data", [])
        rows = []
        for it in items:
            rows.append({
                "date": it["TRADE_DATE"].split()[0],
                "on_warrant_num_mt": it["ON_WARRANT_NUM"],
                "addchange_mt": it["ADDCHANGE"]
            })
        df = pd.DataFrame(rows).drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        df.to_csv(OUT_DIR / "shfe_al_warrant_daily.csv", index=False, encoding="utf-8-sig")
        print(f"  -> 上期所滬鋁倉單庫存抓取成功：共 {len(df)} 筆 ({df['date'].min()} 至 {df['date'].max()})")
    except Exception as e:
        print(f"  東方財富倉單庫存抓取失敗: {e}")


def probe_cme_stock():
    """抓取 CME 每日倉單庫存報告 (Aluminum_Stocks.xls)。"""
    print("[6/6] 正在抓取 CME COMEX 每日倉單庫存報告...")
    try:
        url = "https://www.cmegroup.com/delivery_reports/Aluminum_Stocks.xls"
        r = cffi_requests.get(url, impersonate="chrome", timeout=60)
        df_raw = pd.read_excel(io.BytesIO(r.content))
        date_str = datetime.date.today().strftime("%Y-%m-%d")
        for val in df_raw.values.flatten():
            if isinstance(val, str) and "report date:" in val.lower():
                try:
                    m = re.search(r'(\d+/\d+/\d+)', val)
                    if m:
                        date_str = datetime.datetime.strptime(m.group(1), "%m/%d/%Y").strftime("%Y-%m-%d")
                except Exception:
                    pass
        reg = None
        elig = None
        tot = None
        for _, row in df_raw.iterrows():
            vals = [v for v in row.values if pd.notna(v)]
            if vals:
                txt = str(vals[0]).strip().lower()
                if "total registered" in txt:
                    reg = float(vals[1])
                elif "total eligible" in txt:
                    elig = float(vals[1])
                elif "total aluminum" in txt:
                    tot = float(vals[1])
        df_out = pd.DataFrame([{
            "date": date_str,
            "total_registered_mt": reg,
            "total_eligible_mt": elig,
            "total_aluminum_mt": tot
        }])
        df_out.to_csv(OUT_DIR / "comex_al_stocks_snapshot.csv", index=False, encoding="utf-8-sig")
        print(f"  -> CME 庫存報告抓取成功：日期 {date_str}，註冊倉單 {reg} MT，合約庫存總計 {tot} MT")
    except Exception as e:
        print(f"  CME 庫存報告抓取失敗: {e}")


if __name__ == "__main__":
    probe_lme_westmetall()
    probe_shfe_sina()
    probe_fred()
    probe_yahoo()
    probe_shfe_stock_em()
    probe_cme_stock()
    print("\n所有抓取程序執行完畢。")
