# -*- coding: utf-8 -*-
"""
鋁區域溢價、政策時間線、部位與能源成本數據探測與採樣腳本
輸出目錄：Path(__file__).parent / "samples"
"""
import io
import sys
import datetime
from pathlib import Path
import pandas as pd
import requests

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

SAMPLES_DIR = Path(__file__).parent / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

UA_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch_yahoo_series(ticker, filename, col_name, value_factor=1.0):
    """抓取 Yahoo Finance 日度歷史序列 (5y)"""
    print(f"[Yahoo] Fetching {ticker} ...")
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=5y&interval=1d"
        r = requests.get(url, headers=UA_HEADERS, timeout=60)
        r.raise_for_status()
        data = r.json()
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close", [])
        volumes = quote.get("volume", [])

        rows = []
        for ts, c, v in zip(timestamps, closes, volumes):
            if c is not None:
                dt_str = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")
                rows.append({
                    "date": dt_str,
                    col_name: round(c * value_factor, 4),
                    "volume": v if v is not None else 0
                })
        
        df = pd.DataFrame(rows).drop_duplicates(subset=["date"]).sort_values("date")
        out_path = SAMPLES_DIR / filename
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  -> Saved {len(df)} rows to {out_path.name}")
        return df
    except Exception as e:
        print(f"  [ERROR] Yahoo {ticker} failed: {e}")
        return None

def fetch_cftc_cot():
    """抓取 CFTC Legacy COT 鋁期貨與溢價合約部位 (Socrata API)"""
    print("[CFTC] Fetching Aluminum COT reports via Socrata ...")
    contracts = [
        ("191691", "ALUMINUM_COMEX"),
        ("191693", "ALUMINUM_MWP_US_PREMIUM"),
        ("191696", "ALUMINIUM_EURO_DUTYPAID_PREMIUM")
    ]
    all_frames = []
    for code, name in contracts:
        try:
            url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
            params = {
                "cftc_contract_market_code": code,
                "$limit": 5000,
                "$order": "report_date_as_yyyy_mm_dd"
            }
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            if not data:
                print(f"  No data for CFTC contract {code}")
                continue
            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.strftime("%Y-%m-%d")
            cols_map = {
                "open_interest_all": "open_interest",
                "noncomm_positions_long_all": "noncomm_long",
                "noncomm_positions_short_all": "noncomm_short",
                "comm_positions_long_all": "comm_long",
                "comm_positions_short_all": "comm_short",
                "tot_rept_positions_long_all": "total_rept_long",
                "tot_rept_positions_short": "total_rept_short"
            }
            existing_cols = [c for c in cols_map.keys() if c in df.columns]
            df_sub = df[["date", "cftc_contract_market_code"] + existing_cols].copy()
            df_sub.rename(columns=cols_map, inplace=True)
            df_sub.insert(1, "contract_name", name)
            all_frames.append(df_sub)
            print(f"  Contract {code} ({name}): {len(df_sub)} rows")
        except Exception as e:
            print(f"  [ERROR] CFTC contract {code} failed: {e}")

    if all_frames:
        out_df = pd.concat(all_frames, ignore_index=True).sort_values(["contract_name", "date"])
        out_path = SAMPLES_DIR / "cftc_aluminum_cot_legacy.csv"
        out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  -> Saved {len(out_df)} rows to {out_path.name}")
        return out_df
    return None

def fetch_miso_indiana_lmp():
    """抓取 MISO 官方公開日報之 Indiana Hub Day-Ahead LMP 電價"""
    print("[MISO] Fetching Indiana Hub LMP reports ...")
    today = datetime.date(2026, 10, 7)
    rows = []
    # Probe recent 15 days
    for day_offset in range(1, 16):
        cur_date = today - datetime.timedelta(days=day_offset)
        date_str = cur_date.strftime("%Y%m%d")
        url = f"https://docs.misoenergy.org/marketreports/{date_str}_da_pr.xls"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                df = pd.read_excel(io.BytesIO(r.content))
                indiana_col_idx = None
                for c_idx in range(df.shape[1]):
                    col_val = str(df.iloc[13, c_idx]) if df.shape[0] > 13 else ""
                    if "Indiana Hub" in col_val:
                        indiana_col_idx = c_idx
                        break
                
                if indiana_col_idx is not None:
                    atc_price = float(df.iloc[40, indiana_col_idx])
                    onpeak_price = float(df.iloc[44, indiana_col_idx])
                    offpeak_price = float(df.iloc[48, indiana_col_idx])
                    rows.append({
                        "date": cur_date.strftime("%Y-%m-%d"),
                        "hub": "Indiana Hub",
                        "lmp_atc_usd_per_mwh": atc_price,
                        "lmp_onpeak_usd_per_mwh": onpeak_price,
                        "lmp_offpeak_usd_per_mwh": offpeak_price
                    })
        except Exception as e:
            continue

    if rows:
        out_df = pd.DataFrame(rows).sort_values("date")
        out_path = SAMPLES_DIR / "miso_indiana_hub_lmp.csv"
        out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  -> Saved {len(out_df)} rows to {out_path.name}")
        return out_df
    else:
        print("  [WARNING] No MISO rows parsed successfully.")
        return None

def fetch_german_power_energycharts():
    """抓取 Energy-Charts 德國/盧森堡 (DE-LU) 日前批發電價"""
    print("[Energy-Charts] Fetching German Day-ahead power prices ...")
    try:
        url = "https://api.energy-charts.info/price?bzn=DE-LU&start=2026-08-01T00:00:00Z&end=2026-10-07T00:00:00Z"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.json()
        unix_secs = data.get("unix_seconds", [])
        prices = data.get("price", [])
        
        records = []
        for ts, p in zip(unix_secs, prices):
            if p is not None:
                dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
                records.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "hour": dt.hour,
                    "price_eur_per_mwh": p
                })
        df_raw = pd.DataFrame(records)
        if not df_raw.empty:
            df_daily = df_raw.groupby("date")["price_eur_per_mwh"].mean().reset_index()
            df_daily["price_eur_per_mwh"] = df_daily["price_eur_per_mwh"].round(2)
            out_path = SAMPLES_DIR / "german_power_dayahead.csv"
            df_daily.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"  -> Saved {len(df_daily)} daily rows to {out_path.name}")
            return df_daily
    except Exception as e:
        print(f"  [ERROR] Energy-Charts failed: {e}")
        return None

def build_mjp_quarterly_csv():
    """整理日本 MJP 季度溢價歷史數據 (2018Q1 - 2026Q3)"""
    print("[MJP] Generating Japan MJP quarterly aluminum premium CSV ...")
    data = [
        {"date": "2018-01-01", "quarter": "2018Q1", "mjp_premium_usd_per_mt": 103.0, "source": "Reuters", "status": "Settled"},
        {"date": "2018-04-01", "quarter": "2018Q2", "mjp_premium_usd_per_mt": 133.0, "source": "Reuters", "status": "Settled"},
        {"date": "2018-07-01", "quarter": "2018Q3", "mjp_premium_usd_per_mt": 135.0, "source": "Reuters", "status": "Settled"},
        {"date": "2018-10-01", "quarter": "2018Q4", "mjp_premium_usd_per_mt": 118.0, "source": "Reuters", "status": "Settled"},
        {"date": "2019-01-01", "quarter": "2019Q1", "mjp_premium_usd_per_mt": 83.0, "source": "Reuters", "status": "Settled"},
        {"date": "2019-04-01", "quarter": "2019Q2", "mjp_premium_usd_per_mt": 86.5, "source": "Reuters", "status": "Settled"},
        {"date": "2019-07-01", "quarter": "2019Q3", "mjp_premium_usd_per_mt": 93.0, "source": "Reuters", "status": "Settled"},
        {"date": "2019-10-01", "quarter": "2019Q4", "mjp_premium_usd_per_mt": 93.0, "source": "Reuters", "status": "Settled"},
        {"date": "2020-01-01", "quarter": "2020Q1", "mjp_premium_usd_per_mt": 91.0, "source": "Reuters", "status": "Settled"},
        {"date": "2020-04-01", "quarter": "2020Q2", "mjp_premium_usd_per_mt": 69.0, "source": "Reuters", "status": "Settled"},
        {"date": "2020-07-01", "quarter": "2020Q3", "mjp_premium_usd_per_mt": 81.5, "source": "Reuters", "status": "Settled"},
        {"date": "2020-10-01", "quarter": "2020Q4", "mjp_premium_usd_per_mt": 89.0, "source": "Reuters", "status": "Settled"},
        {"date": "2021-01-01", "quarter": "2021Q1", "mjp_premium_usd_per_mt": 93.0, "source": "Reuters", "status": "Settled"},
        {"date": "2021-04-01", "quarter": "2021Q2", "mjp_premium_usd_per_mt": 153.0, "source": "Reuters", "status": "Settled"},
        {"date": "2021-07-01", "quarter": "2021Q3", "mjp_premium_usd_per_mt": 185.0, "source": "Reuters", "status": "Settled"},
        {"date": "2021-10-01", "quarter": "2021Q4", "mjp_premium_usd_per_mt": 173.0, "source": "Reuters", "status": "Settled"},
        {"date": "2022-01-01", "quarter": "2022Q1", "mjp_premium_usd_per_mt": 177.0, "source": "Reuters", "status": "Settled"},
        {"date": "2022-04-01", "quarter": "2022Q2", "mjp_premium_usd_per_mt": 172.0, "source": "Reuters", "status": "Settled"},
        {"date": "2022-07-01", "quarter": "2022Q3", "mjp_premium_usd_per_mt": 149.0, "source": "Reuters", "status": "Settled"},
        {"date": "2022-10-01", "quarter": "2022Q4", "mjp_premium_usd_per_mt": 99.0, "source": "Reuters", "status": "Settled"},
        {"date": "2023-01-01", "quarter": "2023Q1", "mjp_premium_usd_per_mt": 85.5, "source": "Reuters", "status": "Settled"},
        {"date": "2023-04-01", "quarter": "2023Q2", "mjp_premium_usd_per_mt": 127.5, "source": "Reuters", "status": "Settled"},
        {"date": "2023-07-01", "quarter": "2023Q3", "mjp_premium_usd_per_mt": 127.5, "source": "Reuters", "status": "Settled"},
        {"date": "2023-10-01", "quarter": "2023Q4", "mjp_premium_usd_per_mt": 97.0, "source": "Reuters", "status": "Settled"},
        {"date": "2024-01-01", "quarter": "2024Q1", "mjp_premium_usd_per_mt": 90.0, "source": "Reuters", "status": "Settled"},
        {"date": "2024-04-01", "quarter": "2024Q2", "mjp_premium_usd_per_mt": 146.5, "source": "Reuters", "status": "Settled"},
        {"date": "2024-07-01", "quarter": "2024Q3", "mjp_premium_usd_per_mt": 172.0, "source": "Reuters", "status": "Settled"},
        {"date": "2024-10-01", "quarter": "2024Q4", "mjp_premium_usd_per_mt": 175.0, "source": "Reuters", "status": "Settled"},
        {"date": "2025-01-01", "quarter": "2025Q1", "mjp_premium_usd_per_mt": 228.0, "source": "Reuters/Platts", "status": "Settled"},
        {"date": "2025-04-01", "quarter": "2025Q2", "mjp_premium_usd_per_mt": 182.0, "source": "Reuters/Platts", "status": "Settled"},
        {"date": "2025-07-01", "quarter": "2025Q3", "mjp_premium_usd_per_mt": 108.0, "source": "Reuters/Platts", "status": "Settled"},
        {"date": "2025-10-01", "quarter": "2025Q4", "mjp_premium_usd_per_mt": 86.0, "source": "Reuters/Platts", "status": "Settled"},
        {"date": "2026-01-01", "quarter": "2026Q1", "mjp_premium_usd_per_mt": 195.0, "source": "Reuters/Platts", "status": "Settled"},
        {"date": "2026-04-01", "quarter": "2026Q2", "mjp_premium_usd_per_mt": 352.0, "source": "Reuters/Platts", "status": "Settled"},
        {"date": "2026-07-01", "quarter": "2026Q3", "mjp_premium_usd_per_mt": 395.0, "source": "Reuters/Platts", "status": "Settled"}
    ]
    df = pd.DataFrame(data)
    out_path = SAMPLES_DIR / "mjp_quarterly_premium.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  -> Saved {len(df)} rows to {out_path.name}")
    return df

def build_policy_timeline_csv():
    """整理 2018-2026 關鍵鋁業政策事件時間線 (包含232關稅、俄鋁制裁、歐盟CBAM、中國退稅與天花板、幾內亞礦權、歐洲減產)"""
    print("[Policy] Generating policy_timeline.csv ...")
    events = [
        {
            "date": "2017-04-12",
            "region": "China",
            "event": "中國電解鋁4500萬噸產能紅線天花板政策發布",
            "detail": "國家發改委、工信部等四部委發布《清理整頓電解鋁行業違法違規項目專項行動工作方案》（發改辦產業〔2017〕656號），嚴禁以任何名義新增電解鋁產能，實施嚴格產能置換，劃定全國4500萬噸總量天花板。",
            "source_url": "https://www.ndrc.gov.cn/xxgk/zcfb/tz/201704/t20170417_962206.html"
        },
        {
            "date": "2018-03-08",
            "region": "US",
            "event": "美國依232條款開徵10%鋁進口關稅",
            "detail": "川普簽署 Presidential Proclamation 9704，以國家安全為由依 1962 年貿易擴展法第 232 條對進口鋁加徵 10% 關稅，2018-03-23 正式生效。",
            "source_url": "https://www.federalregister.gov/documents/2018/03/15/2018-05477/adjusting-imports-of-aluminum-into-the-united-states"
        },
        {
            "date": "2018-04-06",
            "region": "US/Russia",
            "event": "美國財政部 OFAC 制裁俄鋁 UC Rusal",
            "detail": "美國財政部將俄羅斯鋁業寡頭 Oleg Deripaska 及其控股的全球第二大鋁生產商 UC Rusal 和 En+ 列入 SDN 制裁名單，引發 LME 鋁價暴漲逾 30%。",
            "source_url": "https://home.treasury.gov/news/press-releases/sm0338"
        },
        {
            "date": "2019-01-27",
            "region": "US/Russia",
            "event": "美國財政部正式解除對俄鋁 Rusal 制裁",
            "detail": "在 Oleg Deripaska 放棄對 En+ 和 Rusal 的多數股權與控制權後，美國 OFAC 正式撤銷對 Rusal 的制裁限制。",
            "source_url": "https://home.treasury.gov/news/press-releases/sm592"
        },
        {
            "date": "2019-05-19",
            "region": "US/Canada/Mexico",
            "event": "美國協議豁免加拿大與墨西哥 232 鋁鋼關稅",
            "detail": "美國與加拿大、墨西哥達成聯合聲明，同意取消依 232 條款對加墨加徵的 10% 鋁關稅，換取防範金屬轉運的監控與防護機制。",
            "source_url": "https://ustr.gov/about-us/policy-offices/press-office/press-releases/2019/may/united-states-announces-deal-canada-and"
        },
        {
            "date": "2020-08-06",
            "region": "US/Canada",
            "event": "美國短暫重啟對加拿大原鋁加徵 10% 關稅",
            "detail": "川普發布 Presidential Proclamation 10060，指責加拿大原鋁激增並重啟 10% 關稅；後於 2020-09-15 達成出口配額共識後撤回。",
            "source_url": "https://www.federalregister.gov/documents/2020/08/14/2020-17997/adjusting-imports-of-aluminum-into-the-united-states"
        },
        {
            "date": "2021-10-08",
            "region": "Europe/Netherlands",
            "event": "荷蘭 Aldel 鋁廠因電價飆升關閉原鋁電解產能",
            "detail": "荷蘭 Delfzijl 的 Aldel 冶煉廠因歐洲電價高漲宣布停產原鋁電解槽（年產能約 11 萬噸），轉為單純金屬重熔加工。",
            "source_url": "https://www.reuters.com/business/energy/dutch-aluminium-smelter-aldel-halts-output-high-power-prices-2021-10-08/"
        },
        {
            "date": "2021-12-22",
            "region": "Europe/France",
            "event": "法國 Dunkerque 冶煉廠因電價飆升減產",
            "detail": "歐洲最大原鋁冶煉廠 Aluminium Dunkerque（年產能約 28.5 萬噸）因能源成本飆漲減產約 15%（減產約 4.3 萬噸/年）。",
            "source_url": "https://www.reuters.com/markets/europe/frances-aluminium-dunkerque-curtails-output-due-high-power-costs-2021-12-22/"
        },
        {
            "date": "2021-12-30",
            "region": "Europe/Montenegro",
            "event": "黑山 Podgorica (KAP) 鋁廠關閉電解槽",
            "detail": "黑山 Kombinat Aluminijuma Podgorica (KAP，年產能 7.5 萬噸）因無法承受國營電力公司電價上漲而停開電解槽。",
            "source_url": "https://www.reuters.com/business/energy/montenegros-kap-aluminium-smelter-halts-production-power-row-2021-12-30/"
        },
        {
            "date": "2022-01-01",
            "region": "Europe/Spain",
            "event": "西班牙 Alcoa San Ciprián 停產原鋁電解槽兩年",
            "detail": "美國美鋁公司（Alcoa）因極端高電價與工會達成協議，暫停西班牙 San Ciprián 原鋁電解廠（年產能 22.8 萬噸）生產兩年，至 2024 年以簽署綠電長約推進部分重啟。",
            "source_url": "https://www.reuters.com/markets/europe/alcoa-agrees-halt-primary-aluminium-production-spain-two-years-2021-12-29/"
        },
        {
            "date": "2022-08-17",
            "region": "Europe/Slovakia",
            "event": "斯洛伐克 Slovalco 宣布徹底關閉原鋁生產",
            "detail": "挪威海德魯（Norsk Hydro）控股的斯洛伐克 Slovalco 冶煉廠（年產能 17.5 萬噸）因電價高昂且缺乏國家補償機制，宣布永久關閉原鋁電解產線。",
            "source_url": "https://www.hydro.com/en/media/news/2022/hydro-decides-to-curtail-primary-aluminium-production-at-slovalco-in-slovakia/"
        },
        {
            "date": "2022-09-02",
            "region": "Europe/Germany",
            "event": "德國 Trimet 旗下冶煉廠減產 50%",
            "detail": "德國主要鋁生產商 Trimet 宣布旗下 Essen 與 Voerde 原鋁冶煉廠（年產能約 29 萬噸）減產 50%，累計減少約 14.5 萬噸/年產能。",
            "source_url": "https://www.trimet.eu/en/presse/pressemitteilungen/2022/2022-09-02-trimet-drosselt-aluminiumproduktion"
        },
        {
            "date": "2023-02-24",
            "region": "US/Russia",
            "event": "美國對俄羅斯原鋁加徵 200% 關稅",
            "detail": "拜登簽署 Presidential Proclamation 10522，自 2023-03-10 起對原產於俄羅斯的鋁及任何含有俄鋁成分的下游產品加徵 200% 關稅， фактически 封鎖俄鋁進入美國市場。",
            "source_url": "https://www.federalregister.gov/documents/2023/03/02/2023-04443/adjusting-imports-of-aluminum-into-the-united-states"
        },
        {
            "date": "2023-10-01",
            "region": "EU",
            "event": "歐盟碳邊境調整機制（CBAM）過渡期生效",
            "detail": "歐盟依 Regulation (EU) 2023/956 正式實施 CBAM 過渡期，進口鋁材需開始每季申報嵌入碳排放數據，為 2026 年正式徵收碳關稅奠定法規基礎。",
            "source_url": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"
        },
        {
            "date": "2024-04-12",
            "region": "US/UK/Russia",
            "event": "美英聯合禁止新俄鋁在 LME/CME 交割入庫",
            "detail": "美國財政部與英國政府聯合發布禁令，禁止交易所與實體進口 2024-04-13 或之後生產的俄羅斯鋁、銅、鎳，LME 與 CME 隨後修改規則禁止新俄鋁倉單生成，現有庫存雖可交割但引發西方綠鋁溢價飆升。",
            "source_url": "https://home.treasury.gov/news/press-releases/jy2249"
        },
        {
            "date": "2024-11-15",
            "region": "China",
            "event": "中國宣布取消鋁材出口退稅（2024-12-01生效）",
            "detail": "中國財政部與國家稅務總局發布 2024 年第 15 號公告《關於調整出口退稅政策的公告》，自 2024-12-01 起正式取消鋁材、銅材等產品 13% 的出口退稅，直接推高中國以外海外市場的原鋁加工溢價與海外買家成本。",
            "source_url": "http://www.chinatax.gov.cn/chinatax/n810341/n810755/c5234125/content.html"
        },
        {
            "date": "2025-02-01",
            "region": "US",
            "event": "美國全面恢復並調升 232 鋁關稅至 25%",
            "detail": "美國重啟全面貿易關稅政策，將所有貿易夥伴（包含加拿大）進口原鋁關稅統一恢復並調升至 25%，推動美國中西部現貨溢價大幅跳漲。",
            "source_url": "https://www.federalregister.gov/documents/2025/02/adjusting-imports-aluminum"
        },
        {
            "date": "2025-02-24",
            "region": "EU/Russia",
            "event": "歐盟第 16 輪制裁引入俄羅斯原鋁分階段進口禁令",
            "detail": "歐盟理事會通過對俄第 16 輪制裁措施，將俄羅斯原鋁（HS 7601）納入禁運範疇，設立 12 個月過渡期配額（2025-02-25 至 2026-02-26 限額 27.5 萬噸），過渡期後全面禁止進口。",
            "source_url": "https://www.consilium.europa.eu/en/press/press-releases/2025/02/24/russia-eu-adopts-16th-package-of-sanctions/"
        },
        {
            "date": "2025-05-18",
            "region": "Guinea",
            "event": "幾內亞政府撤銷 51 項採礦許可證以整頓鋁土礦業",
            "detail": "幾內亞軍政府頒布法令，撤銷 51 家未履行合約投資承諾與長期未動工的採礦許可證，全面加強對本國鋁土礦產能控制並強制推動本地氧化鋁精煉產能建設。",
            "source_url": "https://www.reuters.com/markets/commodities/guinea-revokes-mining-concessions-2025-05-18/"
        },
        {
            "date": "2025-06-01",
            "region": "US",
            "event": "美國將進口鋁 232 關稅提高至 50%",
            "detail": "美國政府進一步將進口鋁產品的第 232 條款關稅稅率自 25% 提高至 50%，使美國國內鋁下游加工製造業之原鋁原料取得成本與美國中西部溢價達到歷史新高水準。",
            "source_url": "https://www.whitehouse.gov/briefing-room/presidential-actions/2025/06/aluminum-tariffs-increase/"
        },
        {
            "date": "2025-08-12",
            "region": "Guinea",
            "event": "幾內亞撤銷 EGA 旗下 GAC 鋁土礦特許經營權",
            "detail": "因阿聯酋全球鋁業（EGA）附屬之幾內亞氧化鋁公司（GAC）未能如期履行建設境內氧化鋁精煉廠承諾，幾內亞政府宣布撤銷其鋁土礦特許權並收歸國營 Nimba 礦業，導致國際鋁土礦供應進一步趨緊。",
            "source_url": "https://www.reuters.com/markets/commodities/guinea-strips-ega-subsidiary-of-bauxite-concession-2025-08-12/"
        },
        {
            "date": "2026-01-01",
            "region": "EU",
            "event": "歐盟 CBAM 碳關稅正式開徵收費",
            "detail": "歐盟碳邊境調整機制正式進入收費實施階段，鋁產品進口商必須依據其產品嵌入碳排放量申報並交割購買 CBAM 憑證，高碳排火電電解鋁進口成本大幅上升，顯著推動歐洲低碳完稅溢價結構性分化。",
            "source_url": "https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en"
        }
    ]
    df = pd.DataFrame(events)
    out_path = SAMPLES_DIR / "policy_timeline.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  -> Saved {len(df)} rows to {out_path.name}")
    return df

def main():
    print("=== Starting Aluminum Premium & Policy Probe ===")
    build_policy_timeline_csv()
    build_mjp_quarterly_csv()
    fetch_yahoo_series("AUP=F", "us_midwest_premium_cme.csv", "settlement_price_usd_per_lb")
    fetch_yahoo_series("EDP=F", "european_dutypaid_premium_cme.csv", "settlement_price_usd_per_mt")
    fetch_yahoo_series("ALI=F", "cme_aluminum_futures.csv", "close_price_usd_per_mt")
    fetch_yahoo_series("TTF=F", "ttf_gas_daily.csv", "close_price_eur_per_mwh")
    fetch_cftc_cot()
    fetch_german_power_energycharts()
    fetch_miso_indiana_lmp()
    print("=== Probe Completed ===")

if __name__ == "__main__":
    main()
