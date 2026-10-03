# -*- coding: utf-8 -*-
"""石油／冬季取暖框架：EIA 餾分油（柴油／取暖油）資料，一次性抓取（不進 ETL，不寫入專案 data/）

框架：PADD 1（美國東岸）結構性缺餾分油，靠 Colonial 管線從 PADD 3（墨西哥灣岸）輸入、
再加上進口補足；寒流 → PADD 1 庫存急降 → NYMEX HO 上漲 → 煉廠開工率被推高。

輸出到 analysis/石油/data/：

eia_dist_weekly.csv（週，週五為 period，EIA 每週三公布，全歷史；各欄起始日不同，早期為空）
  煉廠開工率（%，毛投入 / 最新月度可運轉產能）
  - util_us            WPULEUS3              美國
  - util_padd1         W_NA_YUP_R10_PER      東岸 PADD 1
  - util_padd3         W_NA_YUP_R30_PER      墨西哥灣岸 PADD 3
  餾分油期末庫存（千桶 kbbl）
  - dist_stk_us        WDISTUS1              美國
  - dist_stk_padd1     WDISTP11              PADD 1
  - dist_stk_padd1a    WDIST1A1              PADD 1A New England
  - dist_stk_padd1b    WDIST1B1              PADD 1B Central Atlantic（紐約港／NYH 所在）
  - dist_stk_padd1c    WDIST1C1              PADD 1C Lower Atlantic
  - dist_stk_padd3     WDISTP31              PADD 3（供給端對照）
  PADD 1 餾分油庫存按硫含量拆分（千桶；三者相加 ≈ dist_stk_padd1）
  - dist_stk_padd1_ulsd    WD0ST_R10_1       0–15 ppm（ULSD；東北各州取暖油已大多改為 ULSD 規格）
  - dist_stk_padd1_15_500  WD1ST_R10_1       >15–500 ppm
  - dist_stk_padd1_gt500   WDGSTP11          >500 ppm（傳統高硫取暖油）
  流量（千桶／日 kbpd）
  - dist_imp_padd1     WDIIM_R10-Z00_2       PADD 1 餾分油進口
  - dist_prod_padd1    WDIRPP12              PADD 1 煉廠＋調和商淨產量
  - dist_prod_us       WDIRPUS2              美國煉廠＋調和商淨產量
  - dist_exp_us        WDIEXUS2              美國餾分油出口（週資料為估計值，常大幅修正）
  - dist_supplied_us   WDIUPUS2              美國餾分油「產品供應」＝表觀需求（僅美國層級）
  取暖油價格（美元／加侖；只在取暖季約 10 月初–3 月底調查，其餘月份為空）
  - ho_resid_padd1     W_EPD2F_PRS_R10_DPG   PADD 1 No.2 取暖油住宅零售價
  - ho_resid_us        W_EPD2F_PRS_NUS_DPG   美國 No.2 取暖油住宅零售價
  - ho_whsl_padd1      W_EPD2F_PWR_R10_DPG   PADD 1 No.2 取暖油批發／轉售價
  注意：取暖油價的 period 是週一，其他週資料 period 是週五，所以價格欄會落在不同列（不對齊，
  需要時請自行 resample / asof 對齊）。

eia_dist_monthly.csv（月，Petroleum Supply Monthly，約落後 2–3 個月）
  - pipe_p3_to_p1_kbbl     MDIMPP1P31        PADD 1 經管線自 PADD 3 收貨之餾分油（千桶／月；Colonial＋Plantation 代理）
  - pipe_p3_to_p1_kbpd     由上欄 ÷ 當月天數 自行換算（非 EIA 原始欄）
  - pipe_p3_to_p1_ulsd_kbbl MD0MP_R10-R30_1  同上，0–15 ppm 部分
  - tb_p3_to_p1_kbbl       MDIMTP1P31        PADD 1 經油輪／駁船自 PADD 3 收貨之餾分油（千桶／月；Jones Act 船運）
  - dist_imp_padd1_kbpd    MDIIMP12          PADD 1 餾分油進口（千桶／日）
  - dist_imp_padd1_ca_kbpd MDIIMP1CA2        其中來自加拿大（千桶／日）
  注意：國別細項只在有進口的月份有值，EIA 對該月無進口的國家不回傳資料（CSV 為空而非 0）。

來源：EIA API v2  https://api.eia.gov/v2/seriesid/PET.<SERIES_ID>.<W|M>?api_key=...
     （seriesid 端點要帶 v1 格式的 PET. 前綴與 .W/.M 頻率後綴，裸 ID 會 404）
     （series ID 均已用 v2 browse 端點 petroleum/pnp/wiup、stoc/wstk、move/wkly、pnp/wprodrb、
       cons/wpsup、pri/wfr、move/pipe、move/tb、move/impcp 逐一確認）
金鑰：repo 根目錄 .env 的 EIA_API_KEY。
"""
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

WEEKLY = {
    "util_us": "WPULEUS3",
    "util_padd1": "W_NA_YUP_R10_PER",
    "util_padd3": "W_NA_YUP_R30_PER",
    "dist_stk_us": "WDISTUS1",
    "dist_stk_padd1": "WDISTP11",
    "dist_stk_padd1a": "WDIST1A1",
    "dist_stk_padd1b": "WDIST1B1",
    "dist_stk_padd1c": "WDIST1C1",
    "dist_stk_padd3": "WDISTP31",
    "dist_stk_padd1_ulsd": "WD0ST_R10_1",
    "dist_stk_padd1_15_500": "WD1ST_R10_1",
    "dist_stk_padd1_gt500": "WDGSTP11",
    "dist_imp_padd1": "WDIIM_R10-Z00_2",
    "dist_prod_padd1": "WDIRPP12",
    "dist_prod_us": "WDIRPUS2",
    "dist_exp_us": "WDIEXUS2",
    "dist_supplied_us": "WDIUPUS2",
    "ho_resid_padd1": "W_EPD2F_PRS_R10_DPG",
    "ho_resid_us": "W_EPD2F_PRS_NUS_DPG",
    "ho_whsl_padd1": "W_EPD2F_PWR_R10_DPG",
}
MONTHLY = {
    "pipe_p3_to_p1_kbbl": "MDIMPP1P31",
    "pipe_p3_to_p1_ulsd_kbbl": "MD0MP_R10-R30_1",
    "tb_p3_to_p1_kbbl": "MDIMTP1P31",
    "dist_imp_padd1_kbpd": "MDIIMP12",
    "dist_imp_padd1_ca_kbpd": "MDIIMP1CA2",
}


def fetch_eia(series_id, freq, retries=4):
    """EIA v2 seriesid 端點，回傳以日期為索引的 Series（仿 get_eia_series._fetch_eia，加重試）。"""
    key = os.getenv("EIA_API_KEY", "")
    if not key:
        raise RuntimeError("EIA_API_KEY not found in .env")
    url = f"https://api.eia.gov/v2/seriesid/PET.{series_id}.{freq}"
    for i in range(retries):
        try:
            r = requests.get(url, params={"api_key": key}, timeout=60)
            r.raise_for_status()
            resp = r.json()["response"]
            break
        except Exception as e:  # 不印 URL（含金鑰）
            if i == retries - 1:
                raise RuntimeError(f"{series_id} 抓取失敗：{type(e).__name__}") from None
            time.sleep(2 * (i + 1))
    data = resp.get("data", [])
    total = int(resp.get("total", len(data)) or 0)
    if total > len(data):
        print(f"  警告：{series_id} total={total} 但只回傳 {len(data)} 筆（可能被截斷）")
    rows = {}
    for x in data:
        p, v = str(x.get("period", "")).strip(), x.get("value")
        if v is None:
            continue
        try:
            if len(p) == 7:
                d = pd.Timestamp(p + "-01")
            elif len(p) == 10:
                d = pd.Timestamp(p)
            else:
                continue
            rows[d] = float(v)
        except (ValueError, TypeError):
            continue
    if not rows:
        raise RuntimeError(f"{series_id} 無資料")
    return pd.Series(rows, name=series_id).sort_index()


def build(spec, freq):
    cols = {}
    for name, sid in spec.items():
        s = fetch_eia(sid, freq)
        cols[name] = s
        print(f"  {name:26s} {sid:22s} {len(s):5d}  {s.index[0]:%Y-%m-%d} → {s.index[-1]:%Y-%m-%d}  last={s.iloc[-1]:g}")
    df = pd.DataFrame(cols).sort_index()
    df.index.name = "date"
    return df


def save(df, fname):
    df.to_csv(OUT / fname, date_format="%Y-%m-%d")
    print(f"{fname} {len(df)} rows {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}")


def main():
    print("[weekly]")
    w = build(WEEKLY, "W")
    save(w, "eia_dist_weekly.csv")

    print("[monthly]")
    m = build(MONTHLY, "M")
    days = m.index.days_in_month
    m.insert(1, "pipe_p3_to_p1_kbpd", (m["pipe_p3_to_p1_kbbl"] / days).round(1))
    save(m, "eia_dist_monthly.csv")


if __name__ == "__main__":
    main()
