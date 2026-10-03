# -*- coding: utf-8 -*-
"""石油／天然氣冬季路徑推演：一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/石油/data/：
- prices_daily.csv  寬表，日頻（各來源交易日聯集，未 forward-fill），各欄盡量拉最長歷史：

  欄位            內容                                   單位        來源
  ttf_eur_mwh     荷蘭 TTF 天然氣近月期貨                EUR/MWh     Yahoo  TTF=F
  hh_spot         Henry Hub 天然氣現貨                   USD/MMBtu   FRED   DHHNGSP
  ng_fut          NYMEX 天然氣近月期貨                   USD/MMBtu   Yahoo  NG=F
  wti_spot        WTI Cushing 現貨                       USD/bbl     FRED   DCOILWTICO
  wti_fut         NYMEX WTI 近月期貨                     USD/bbl     Yahoo  CL=F
  brent_spot      Brent 現貨（Europe）                   USD/bbl     FRED   DCOILBRENTEU
  brent_fut       ICE Brent 近月期貨                     USD/bbl     Yahoo  BZ=F
  ho_fut          NYMEX NY Harbor ULSD（舊稱 Heating Oil）近月  USD/gal  Yahoo  HO=F
  rb_fut          NYMEX RBOB 汽油近月                    USD/gal     Yahoo  RB=F
  nyh_ulsd_spot   NY Harbor 超低硫柴油現貨 FOB           USD/gal     EIA    PET.EER_EPD2DXL0_PF4_Y35NY_DPG.D
  gasoil_usd_mt   ICE London Gas Oil 近月連續            USD/公噸    Investing.com pair_id=8861
  eurusd          歐元兌美元                             USD per EUR FRED   DEXUSEU

來源 URL：
- FRED:  https://api.stlouisfed.org/fred/series/observations（env FED_API_KEY）；
         失敗則退回 https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>
- Yahoo: https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?period1=0（全歷史）
- EIA:   https://api.eia.gov/v2/seriesid/<ID>（env EIA_API_KEY；單次上限 5000 筆，用 offset 分頁）
- Investing.com: https://api.investing.com/api/financialdata/historical/8861
         （curl_cffi 模擬 Chrome；單次上限 5000 筆，依年份分段抓）

注意事項：
- Yahoo 期貨是「近月連續」，換月日會有跳空，沒有做 roll 調整；且 Yahoo 的 TTF=F 歷史只到 2017 年底左右。
- FRED 的 DHHNGSP / DCOIL* / DEXUSEU 通常落後 1 週左右；EIA 現貨也落後約一週。
- Gasoil：Yahoo 沒有 ICE Gasoil 期貨代碼（search API 只找到 S&P GSCI Gasoil 指數與歐洲 ETC/權證），
  所以改用 Investing.com「London Gas Oil」（pair_id 8861，1990 起）。2015 年前 ICE 基準合約是 0.1% 硫含量
  Gas Oil，之後改為 10ppm Low Sulphur Gasoil，Investing 的連續序列在此處是拼接的，長期比較要小心口徑。
  換算：1 公噸 gasoil ≈ 7.45 桶 ≈ 313 加侖，gasoil_usd_mt / 313 ≈ USD/gal，可和 ho_fut 比較。
- 所有欄位都是收盤（settle/close）原始值，不補值；某來源失敗時該欄整欄省略並在終端印出原因。
"""
import io
import os
import time
import urllib.parse
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / ".env")

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}


def _get(url, retries=3, **kw):
    kw.setdefault("timeout", 90)
    kw.setdefault("headers", UA)
    for i in range(retries):
        try:
            r = requests.get(url, **kw)
            r.raise_for_status()
            return r
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  retry {i + 1}/{retries - 1} {url[:80]} — {type(e).__name__}")
            time.sleep(3 * (i + 1))


def fred(series):
    """優先用 keyed FRED API；免 key 的 fredgraph.csv 常 RemoteDisconnected，只當備援。"""
    key = os.getenv("FED_API_KEY")
    if key:
        try:
            obs = _get("https://api.stlouisfed.org/fred/series/observations",
                       params={"series_id": series, "api_key": key, "file_type": "json"}).json()["observations"]
            s = pd.Series({pd.Timestamp(o["date"]): o["value"] for o in obs})
            return pd.to_numeric(s, errors="coerce").dropna()
        except Exception as e:
            print(f"  FRED API {series} 失敗，改用 fredgraph.csv — {type(e).__name__}")
    r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"])
    return pd.to_numeric(d.set_index("date").v, errors="coerce").dropna()


def yahoo(ticker):
    """Yahoo chart API，period1=0 取全部可得歷史，日期取 UTC 日。"""
    r = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker, safe='')}",
             params={"interval": "1d", "period1": 0, "period2": int(time.time())})
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(res["timestamp"], unit="s").normalize(), dtype=float)
    s = s.dropna()
    return s[~s.index.duplicated(keep="last")]


def eia(series_id):
    key = os.getenv("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY 不在 .env")
    rows, offset = [], 0
    while True:
        j = _get(f"https://api.eia.gov/v2/seriesid/{series_id}",
                 params={"api_key": key, "offset": offset, "length": 5000}).json()["response"]
        batch = j.get("data", [])
        rows += batch
        offset += len(batch)
        if not batch or offset >= int(j.get("total", 0)):
            break
    s = pd.Series({pd.Timestamp(x["period"]): x["value"] for x in rows})
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def investing(pair_id, start_year, referer):
    """Investing.com 內部 API；單次最多回 5000 筆（由舊到新截斷），所以每 10 年一段。"""
    from curl_cffi import requests as creq
    import urllib3
    urllib3.disable_warnings()
    hdr = {"Origin": "https://www.investing.com", "Referer": referer,
           "domain-id": "www", "Accept": "application/json"}
    out = {}
    today = date.today()
    for y0 in range(start_year, today.year + 1, 10):
        y1 = min(y0 + 9, today.year)
        end = today.isoformat() if y1 == today.year else f"{y1}-12-31"
        url = (f"https://api.investing.com/api/financialdata/historical/{pair_id}"
               f"?start-date={y0}-01-01&end-date={end}&time-frame=Daily&add-missing-rows=false")
        r = creq.get(url, impersonate="chrome131", timeout=90, verify=False, headers=hdr)
        r.raise_for_status()
        data = r.json().get("data") or []
        assert len(data) < 5000, f"investing {pair_id} {y0}-{y1} 回傳達上限 5000 筆，需縮小區間"
        for row in data:
            out[pd.Timestamp(row["rowDateTimestamp"][:10])] = float(row["last_closeRaw"])
        time.sleep(1)
    return pd.Series(out, dtype=float).sort_index()


SPECS = [
    ("ttf_eur_mwh", lambda: yahoo("TTF=F")),
    ("hh_spot", lambda: fred("DHHNGSP")),
    ("ng_fut", lambda: yahoo("NG=F")),
    ("wti_spot", lambda: fred("DCOILWTICO")),
    ("wti_fut", lambda: yahoo("CL=F")),
    ("brent_spot", lambda: fred("DCOILBRENTEU")),
    ("brent_fut", lambda: yahoo("BZ=F")),
    ("ho_fut", lambda: yahoo("HO=F")),
    ("rb_fut", lambda: yahoo("RB=F")),
    ("nyh_ulsd_spot", lambda: eia("PET.EER_EPD2DXL0_PF4_Y35NY_DPG.D")),
    ("gasoil_usd_mt", lambda: investing(8861, 1990,
                                        "https://www.investing.com/commodities/london-gas-oil-historical-data")),
    ("eurusd", lambda: fred("DEXUSEU")),
]


def main():
    cols, failed = {}, {}
    for name, fn in SPECS:
        try:
            s = fn()
            if s.empty:
                raise ValueError("無資料")
            cols[name] = s
            print(f"{name:14s} {len(s):6d} rows  {s.index.min():%Y-%m-%d} → {s.index.max():%Y-%m-%d}  last={s.iloc[-1]:.4g}")
        except Exception as e:
            failed[name] = f"{type(e).__name__}: {e}"
            print(f"{name:14s} FAILED — {failed[name]}")
    df = pd.DataFrame(cols).sort_index()
    df = df[[n for n, _ in SPECS if n in df.columns]]
    df.index.name = "date"
    df.to_csv(OUT / "prices_daily.csv", date_format="%Y-%m-%d")
    print(f"prices_daily   {len(df)} rows  {df.index.min():%Y-%m-%d} → {df.index.max():%Y-%m-%d}  → {OUT / 'prices_daily.csv'}")
    if failed:
        print("缺欄：", failed)


if __name__ == "__main__":
    main()
