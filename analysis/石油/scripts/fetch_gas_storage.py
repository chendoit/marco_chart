# -*- coding: utf-8 -*-
"""石油／歐洲天然氣學習案例：GIE AGSI+ 儲氣日資料，一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/石油/data/：
- gas_storage_eu.csv     日資料（gas day），寬表，欄位前綴 = 地區：eu_ / de_ / nl_ / fr_ / it_
                         每個地區 6 欄：
                           <p>_twh        gasInStorage，儲氣量，TWh
                           <p>_full       full，儲氣率，%（= gasInStorage / workingGasVolume）
                           <p>_inj        injection，注氣，GWh/d
                           <p>_wdr        withdrawal，抽氣，GWh/d
                           <p>_wgv        workingGasVolume，工作氣容量，TWh
                           <p>_trend      trend，GIE 原欄位，約等於 full 的日變化（百分點）；定義以 GIE 為準
- gas_storage_eu_5y.csv  EU 儲氣率（%）季節比較，index = 今年每個日曆日（%Y-%m-%d，剔除 2/29）：
                           eu_full_cur      今年
                           eu_full_prev     去年
                           eu_full_5y_min / _avg / _max   前 5 個完整年度（今年−5 ～ 今年−1）同一月日
                           eu_full_dev_5y   今年 − 5 年平均（百分點）

來源：GIE AGSI+ REST API  https://agsi.gie.eu/api
  - EU 合計：?type=eu；國家：?country=DE 等；from / to / page / size（size 上限 300）
  - 必須帶 header「x-key: <API key>」，沒有 key 會回 "Invalid or missing API key"（2026-09-30 實測）。
    免費註冊 https://agsi.gie.eu/account 取得 key，放在 repo 根目錄 .env：GIE_API_KEY=xxxx
  - Rate limit：每 IP 每分鐘 60 次，超過會被鎖 60 秒；本腳本每次呼叫間隔 1.1 秒，遇 429 等 65 秒重試。
  - API 文件：https://www.gie.eu/transparency-platform/GIE_API_documentation_v007.pdf

注意：
- 資料由各 SSO 申報，GIE 不修改；歷史值偶爾會被回溯修正，重跑會拿到最新版。
- EU 合計的成員／設施口徑隨時間變動（英國脫歐、新設施加入、設施除役），TWh 與 wgv 有斷點；
  長期比較以 full（%）為主。
- 各國 AGSI+ 資料約 2011 年起；早年部分設施未申報，容量（wgv）偏低。
- gas day = 06:00 CET 起算的 24 小時；API 值多為字串，缺值為 "-" 或空字串，一律轉 NaN。
- 最新一兩天可能仍是部分申報（status 欄 = "E" estimated / "C" confirmed），這裡不過濾，使用時留意尾端。
"""
import os
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
REPO_ROOT = Path(__file__).resolve().parents[3]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
API = "https://agsi.gie.eu/api"
START = "2011-01-01"
AREAS = [("eu", {"type": "eu"}), ("de", {"country": "DE"}), ("nl", {"country": "NL"}),
         ("fr", {"country": "FR"}), ("it", {"country": "IT"})]
FIELDS = {"gasInStorage": "twh", "full": "full", "injection": "inj",
          "withdrawal": "wdr", "workingGasVolume": "wgv", "trend": "trend"}
PAUSE = 1.1  # 秒；60 calls/min 上限


def get_key():
    load_dotenv(REPO_ROOT / ".env")
    key = os.getenv("GIE_API_KEY", "").strip()
    if not key:
        sys.exit(
            "找不到 GIE_API_KEY。AGSI+ API 需要免費 API key：\n"
            "  1. 到 https://agsi.gie.eu/account 註冊並登入，在 API 頁面複製 key\n"
            f"  2. 在 {REPO_ROOT / '.env'} 加一行  GIE_API_KEY=你的key\n"
            "  3. 重跑本腳本"
        )
    return key


def call(session, params, tries=5):
    for i in range(tries):
        try:
            r = session.get(API, params=params, timeout=60)
            if r.status_code == 429:
                print("  429 too many requests，等 65 秒…")
                time.sleep(65)
                continue
            r.raise_for_status()
            j = r.json()
            if j.get("error"):
                raise RuntimeError(f"GIE API 錯誤：{j.get('error')} / {j.get('message')}")
            return j
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            wait = 5 * (i + 1)
            print(f"  網路錯誤 {type(e).__name__}，{wait} 秒後重試（{i + 1}/{tries}）")
            time.sleep(wait)
    raise RuntimeError(f"GIE API 重試 {tries} 次仍失敗：{params}")


def fetch_area(session, prefix, base):
    rows, page, last = [], 1, 1
    to = date.today().isoformat()
    while page <= last:
        j = call(session, {**base, "from": START, "to": to, "page": page, "size": 300})
        last = int(j.get("last_page") or 0)
        rows += j.get("data", [])
        page += 1
        time.sleep(PAUSE)
    if not rows:
        raise RuntimeError(f"{prefix}: API 沒回資料")
    d = pd.DataFrame(rows)
    d["date"] = pd.to_datetime(d["gasDayStart"])
    d = d.drop_duplicates("date").set_index("date").sort_index()
    out = pd.DataFrame(index=d.index)
    for src, short in FIELDS.items():
        out[f"{prefix}_{short}"] = pd.to_numeric(d.get(src), errors="coerce")
    print(f"  {prefix}: {len(out)} rows {out.index[0]:%Y-%m-%d} → {out.index[-1]:%Y-%m-%d}（{last} 頁）")
    return out


def build_5y(full):
    """EU 儲氣率：今年 vs 前 5 年同月日 min/avg/max。"""
    s = full.dropna()
    s = s[~((s.index.month == 2) & (s.index.day == 29))]
    cur_year = s.index[-1].year
    md = s.index.strftime("%m-%d")
    tab = pd.DataFrame({"md": md, "year": s.index.year, "v": s.values}).pivot(index="md", columns="year", values="v")
    prior = [y for y in range(cur_year - 5, cur_year) if y in tab.columns]
    idx = pd.date_range(f"{cur_year}-01-01", f"{cur_year}-12-31", freq="D")
    idx = idx[~((idx.month == 2) & (idx.day == 29))]
    keys = idx.strftime("%m-%d")
    res = pd.DataFrame(index=idx)
    res.index.name = "date"
    res["eu_full_cur"] = tab.get(cur_year).reindex(keys).values
    res["eu_full_prev"] = tab.get(cur_year - 1).reindex(keys).values if cur_year - 1 in tab.columns else float("nan")
    res["eu_full_5y_min"] = tab[prior].min(axis=1).reindex(keys).values
    res["eu_full_5y_avg"] = tab[prior].mean(axis=1).reindex(keys).values
    res["eu_full_5y_max"] = tab[prior].max(axis=1).reindex(keys).values
    res["eu_full_dev_5y"] = res["eu_full_cur"] - res["eu_full_5y_avg"]
    print(f"  5 年比較基期：{prior[0]}–{prior[-1]}（{len(prior)} 年）")
    return res


def save(df, name):
    df.to_csv(OUT / name, date_format="%Y-%m-%d", float_format="%.4f")
    print(f"{name} {len(df)} rows {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}")


def main():
    key = get_key()
    s = requests.Session()
    s.headers.update({"x-key": key, "User-Agent": "Mozilla/5.0"})
    frames = []
    for prefix, base in AREAS:
        frames.append(fetch_area(s, prefix, base))
    wide = pd.concat(frames, axis=1).sort_index()
    wide.index.name = "date"
    save(wide, "gas_storage_eu.csv")

    bad = wide.filter(like="_full").stack()
    bad = bad[(bad < 0) | (bad > 100.5)]
    if len(bad):
        print(f"  !! full 超出 0–100 的值 {len(bad)} 筆，例：\n{bad.head()}")
    last = wide["eu_full"].dropna()
    print(f"  EU 最新：{last.index[-1]:%Y-%m-%d} full={last.iloc[-1]:.2f}% "
          f"twh={wide.loc[last.index[-1], 'eu_twh']:.1f}")

    save(build_5y(wide["eu_full"]), "gas_storage_eu_5y.csv")


if __name__ == "__main__":
    main()
