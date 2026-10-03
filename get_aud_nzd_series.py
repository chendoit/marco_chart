# -*- coding: utf-8 -*-
"""澳元／紐元儀表板資料（flask 頁面「澳元」「紐元」），把 analysis/澳元、analysis/紐元 的一次性抓取搬進每日排程。

來源與原型：analysis/澳元/scripts/fetch_data.py + build_chart_data.py、
analysis/紐元/scripts/fetch_data.py + fetch_race.py + fetch_dairy.py + fetch_migration.py。
計算方式（換月週、交割週、四象限、支撐線、波動率百分位、4 季滾動）與原型一致。

輸出 pkl（{'title', 'data': [[datetime 08:00, float], ...]}），前綴：
- ccy_*   匯率：AUD/NZD 日頻（FRED，尾端 Yahoo 補）、AUDNZD、廣義美元倒數、G10 對美元、
          澳元 63 日實現波動率與百分位、兩條長期支撐線
- cot_*   CFTC Socrata（Legacy + TFF，futures-only）：AUD/NZD 全部類別、淨部位、
          剔除換月／交割週的 OI、四象限代碼；CAD 只存淨部位佔 OI %
- rate_*  BIS 政策利率（US AU NZ CA GB XM JP CH）、OECD MEI 10Y/3M（AU NZ US，經 FRED）
- cn_*    鐵礦石、銅（IMF，經 FRED）、中國 PPI（FRED 到 2022-12，之後 DBnomics 轉載 NBS）、
          12 個月變化與 z 分數
- bop_*   澳洲／紐西蘭國際收支（OECD SDMX DF_BOP），4 季滾動，十億本幣
- nz_*    GDT 乳製品價格指數（每場拍賣）、Stats NZ 淨移民（12 個月滾動）

各區塊獨立 try：一個來源掛掉不影響其他區塊；結束時若有失敗就 raise，讓 get_all_series_data
記進 error_history（連 3 天失敗發 LINE）。
"""
import csv
import html as html_mod
import io
import json
import os
import pickle
import re
import time
from datetime import date, datetime

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 日期檔日誌已集中設定於 log_config.py，本檔「禁止」再呼叫 logger.add()。

DATA_DIR = os.getenv("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"}
START = "2000-01-01"


# ---------------------------------------------------------------------------
# 共用：HTTP、存檔
# ---------------------------------------------------------------------------
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
            logger.warning(f"retry {i + 1}/{retries - 1} {url[:90]} — {e}")
            time.sleep(3 * (i + 1))


def _save(name, title, s):
    """逐日期 merge 存檔（同 get_fred_csv._save_series）：新值覆蓋同日期舊值，舊日期全保留。"""
    s = pd.Series(s).dropna()
    s = s[np.isfinite(s.astype(float))]
    if s.empty:
        raise ValueError(f"{name}: 無資料")
    path = os.path.join(DATA_DIR, f"{name}.pkl")
    old = []
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                old = pickle.load(f).get("data", [])
        except Exception:
            old = []
    merged = {d.date(): (d, v) for d, v in old}
    merged.update({d.date(): (datetime(d.year, d.month, d.day, 8), round(float(v), 6))
                   for d, v in s.items()})
    rows = sorted(merged.values(), key=lambda x: x[0])
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump({"title": title, "data": [[d, v] for d, v in rows]}, f)
    os.replace(tmp, path)
    return len(rows)


def _read(name):
    with open(os.path.join(DATA_DIR, f"{name}.pkl"), "rb") as f:
        d = pickle.load(f)["data"]
    return pd.Series([v for _, v in d], index=pd.to_datetime([k for k, _ in d]).normalize())


def fred(series):
    """優先用 keyed FRED API（FED_API_KEY，get_fed_series.py 同一把）；免 key 的 fredgraph.csv
    常 RemoteDisconnected（2026-09-29 實測連 3 次都斷），只當備援。"""
    key = os.getenv("FED_API_KEY")
    if key:
        try:
            obs = _get("https://api.stlouisfed.org/fred/series/observations",
                       params={"series_id": series, "api_key": key, "file_type": "json"}).json()["observations"]
            s = pd.Series({pd.Timestamp(o["date"]): o["value"] for o in obs})
            return pd.to_numeric(s, errors="coerce").dropna()
        except Exception as e:
            logger.warning(f"FRED API {series} 失敗，改用 fredgraph.csv — {e}")
    r = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
    d = pd.read_csv(io.StringIO(r.text))
    d.columns = ["date", "v"]
    d["date"] = pd.to_datetime(d["date"])
    return pd.to_numeric(d.set_index("date").v, errors="coerce").dropna()


def yahoo(ticker, rng="3mo"):
    r = _get(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}",
             params={"range": rng, "interval": "1d"})
    res = r.json()["chart"]["result"][0]
    s = pd.Series(res["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(res["timestamp"], unit="s").normalize(), dtype=float)
    return s.dropna()


# ---------------------------------------------------------------------------
# 1. 匯率
# ---------------------------------------------------------------------------
# FRED id, Yahoo 補尾 ticker, 是否取倒數（統一成「1 單位外幣 = ? 美元」）
G10 = {"AU": ("DEXUSAL", "AUDUSD=X", False), "NZ": ("DEXUSNZ", "NZDUSD=X", False),
       "CA": ("DEXCAUS", "CADUSD=X", True), "GB": ("DEXUSUK", "GBPUSD=X", False),
       "XM": ("DEXUSEU", "EURUSD=X", False), "JP": ("DEXJPUS", "JPYUSD=X", True),
       "CH": ("DEXSZUS", "CHFUSD=X", True)}
AREA_NAME = {"US": "美國", "AU": "澳洲", "NZ": "紐西蘭", "CA": "加拿大", "GB": "英國",
             "XM": "歐元區", "JP": "日本", "CH": "瑞士"}


def fx_usd(area):
    fid, yid, inv = G10[area]
    s = fred(fid)
    s = 1 / s if inv else s
    try:  # FRED 延遲約一週，用 Yahoo 補尾端（Yahoo 的 JPYUSD=X 等已是外幣/美元方向）
        tail = yahoo(yid)
        s = pd.concat([s, tail[tail.index > s.index.max()]])
    except Exception as e:
        logger.warning(f"Yahoo {yid} 補尾失敗，只用 FRED — {e}")
    return s[~s.index.duplicated(keep="last")].sort_index()


def support_line(px, windows):
    """原型 trendFn：在每個視窗取最低點，對 log(價格) 做最小平方直線，從第一個低點延伸到最新日期。"""
    lows = [px.loc[a:b].idxmin() for a, b in windows]
    t0 = lows[0]
    xs = np.array([(d - t0).days for d in lows], float)
    ys = np.log(px.loc[lows].values)
    b, a = np.polyfit(xs, ys, 1)
    idx = px.loc[t0:].index
    return pd.Series(np.exp(a + b * (idx - t0).days.values), index=idx)


def job_fx():
    fx = {a: fx_usd(a) for a in G10}
    for a, s in fx.items():
        _save(f"ccy_usdfx_{a.lower()}", f"{AREA_NAME[a]}貨幣兌美元（1 單位外幣＝?美元）", s.loc["1999-12":])
    aud, nzd = fx["AU"].loc[START:], fx["NZ"].loc[START:]
    _save("ccy_audusd", "AUD/USD", aud)
    _save("ccy_nzdusd", "NZD/USD", nzd)
    _save("ccy_audnzd", "AUD/NZD", (aud / nzd).dropna())
    usd = fred("DTWEXBGS")
    _save("ccy_usd_broad_inv", "美元走弱（100 / 廣義美元指數）", 100 / usd)

    # 63 日實現波動率（年化 %）；百分位用週資料、只用當時已知的歷史（expanding，52 週起算）
    lr = np.log(fx["AU"].loc["1999":]).diff()
    rv = (lr.rolling(63).std() * np.sqrt(252) * 100).dropna()
    _save("ccy_aud_rv63", "AUD/USD 63日實現波動率(年化%)", rv.loc[START:])
    wk = rv.groupby(rv.index.to_period("W-FRI")).tail(1).loc[START:]
    pct = wk.expanding(52).apply(lambda v: (v[:-1] < v[-1]).mean() * 100, raw=True)
    _save("ccy_aud_rv63_pct", "AUD 實現波動率 歷史百分位(2000起)", pct)

    # 支撐線：AUD 用 2022-10、2023-10、2024-08 三個低點（付鵬 ①② 的上升支撐，推測重建）；
    # NZD 用 2015、2020、2022 三個低點（付鵬圖上的長期下降支撐）
    _save("ccy_aud_support", "AUD 上升支撐線(22/23/24低點)",
          support_line(aud, [("2022-09-01", "2022-11-30"), ("2023-09-01", "2023-11-30"),
                             ("2024-07-15", "2024-08-31")]))
    _save("ccy_nzd_lowline", "NZD 長期低點連線(15/20/22低點)",
          support_line(nzd, [("2015-06-01", "2015-12-31"), ("2020-01-01", "2020-06-30"),
                             ("2022-08-01", "2022-12-31")]))
    logger.info(f"fx: AUD {aud.index[-1]:%Y-%m-%d} {aud.iloc[-1]:.4f}, NZD {nzd.iloc[-1]:.4f}")
    return fx


# ---------------------------------------------------------------------------
# 2. CFTC 持倉
# ---------------------------------------------------------------------------
COT_CODES = {"aud": "232741", "nzd": "112741", "cad": "090741"}
LEGACY_COLS = {
    "open_interest_all": "oi",
    "noncomm_positions_long_all": "nc_long",
    "noncomm_positions_short_all": "nc_short",
    "comm_positions_long_all": "comm_long",
    "comm_positions_short_all": "comm_short",
    "nonrept_positions_long_all": "nonrep_long",
    "nonrept_positions_short_all": "nonrep_short",
}
TFF_COLS = {
    "dealer_positions_long_all": "dealer_long",
    "dealer_positions_short_all": "dealer_short",
    "asset_mgr_positions_long": "am_long",
    "asset_mgr_positions_short": "am_short",
    "lev_money_positions_long": "lev_long",
    "lev_money_positions_short": "lev_short",
}
COT_TITLE = {
    "oi": "總持倉 OI（口）", "oi_clean": "總持倉 OI（剔除換月/交割週）",
    "nc_long": "非商業多頭", "nc_short": "非商業空頭", "comm_long": "商業多頭", "comm_short": "商業空頭",
    "nonrep_long": "非報告部位多頭", "nonrep_short": "非報告部位空頭",
    "am_long": "TFF 資產管理多頭", "am_short": "TFF 資產管理空頭",
    "lev_long": "TFF 槓桿基金多頭", "lev_short": "TFF 槓桿基金空頭",
    "dealer_long": "TFF 交易商多頭", "dealer_short": "TFF 交易商空頭",
    "am_net": "TFF 資產管理淨部位", "lev_net": "TFF 槓桿基金淨部位", "dealer_net": "TFF 交易商淨部位",
    "minside": "多空對峙 min(非商業多, 空)", "net_pct": "非商業淨部位佔OI%",
    "regime": "價格×持倉四象限代碼",
}
# 四象限代碼（route 端依此上色）：0 = 換月／交割週不判讀
REGIME_CODE = {"new_short": 1, "long_liq": 2, "short_cover": 3, "new_long": 4, "roll": 0}


def fetch_cot(dataset, code, cols):
    r = _get(f"https://publicreporting.cftc.gov/resource/{dataset}.json",
             params={"cftc_contract_market_code": code, "$limit": 50000,
                     "$order": "report_date_as_yyyy_mm_dd"})
    d = pd.DataFrame(r.json())
    miss = [c for c in cols if c not in d.columns]
    if miss:
        raise KeyError(f"CFTC {dataset}/{code} 缺欄位 {miss}")
    d.index = pd.to_datetime(d["report_date_as_yyyy_mm_dd"]).dt.normalize()
    return d[list(cols)].rename(columns=cols).apply(pd.to_numeric)


def third_wednesday(y, m):
    first = pd.Timestamp(y, m, 1)
    return first + pd.Timedelta(days=(2 - first.weekday()) % 7 + 14)


def is_roll_window(d):
    """IMM 季月換月週：週二報告日在第三個週三之前 6–9 天，新舊合約並存、OI 雙計。"""
    if d.month not in (3, 6, 9, 12):
        return False
    return 6 <= (third_wednesday(d.year, d.month) - d).days <= 9


def job_cot(fx):
    cad = fetch_cot("6dca-aqww", COT_CODES["cad"], LEGACY_COLS)
    _save("cot_cad_net_pct", "加元 " + COT_TITLE["net_pct"],
          ((cad.nc_long - cad.nc_short) / cad.oi * 100).loc[START:])
    for ccy, area in (("aud", "AU"), ("nzd", "NZ")):
        label = "澳元" if ccy == "aud" else "紐元"
        w = fetch_cot("6dca-aqww", COT_CODES[ccy], LEGACY_COLS).join(
            fetch_cot("gpe5-46if", COT_CODES[ccy], TFF_COLS), how="left").loc[START:]
        for k in ("dealer", "am", "lev"):
            w[k + "_net"] = w[k + "_long"] - w[k + "_short"]
        w["minside"] = np.minimum(w.nc_long, w.nc_short)
        w["net_pct"] = (w.nc_long - w.nc_short) / w.oi * 100

        # 換月週 + 交割週異常（2025-12 起季月第三個週三前一天那週，非報告部位多空同時暴增 4–10 倍）
        roll = pd.Series([is_roll_window(d) for d in w.index], index=w.index)
        nonrep = w.nonrep_long + w.nonrep_short
        anom = nonrep > 3 * nonrep.rolling(26, min_periods=8).median().shift(1)
        anom &= w.index >= "2025-01-01"  # 2004 年 NZD 非報告部位基數太小會誤判；此型態 2025-12 才出現
        w["oi_clean"] = w.oi.where(~(roll | anom))

        px = fx[area].reindex(w.index, method="ffill")
        dp, doi = px.diff(), w.oi.diff()
        reg = np.select([(dp < 0) & (doi > 0), (dp < 0) & (doi <= 0), (dp >= 0) & (doi <= 0), (dp >= 0) & (doi > 0)],
                        [1, 2, 3, 4], default=np.nan)
        skip = roll | roll.shift(1, fill_value=False) | anom | anom.shift(1, fill_value=False)
        w["regime"] = pd.Series(np.where(skip, 0, reg), index=w.index).iloc[1:]

        for col in list(LEGACY_COLS.values()) + list(TFF_COLS.values()) + \
                ["dealer_net", "am_net", "lev_net", "minside", "net_pct", "oi_clean", "regime"]:
            _save(f"cot_{ccy}_{col}", f"{label} {COT_TITLE[col]}", w[col])
        logger.info(f"cot {ccy}: {w.index[-1]:%Y-%m-%d} OI={w.oi.iloc[-1]:,.0f} "
                    f"roll={int(roll.sum())} anom={list(w.index[anom].strftime('%Y-%m-%d'))}")


# ---------------------------------------------------------------------------
# 3. 利率：BIS 政策利率 + OECD MEI 市場利率
# ---------------------------------------------------------------------------
POLICY_TITLE = {"US": "Fed 政策利率", "AU": "RBA 現金利率", "NZ": "RBNZ OCR", "CA": "BoC 政策利率",
                "GB": "BoE 政策利率", "XM": "ECB 政策利率", "JP": "BoJ 政策利率", "CH": "SNB 政策利率"}
MEI = {"au10": "IRLTLT01AUM156N", "nz10": "IRLTLT01NZM156N", "us10": "IRLTLT01USM156N",
       "au3m": "IR3TIB01AUM156N", "nz3m": "IR3TIB01NZM156N", "us3m": "IR3TIB01USM156N"}
MEI_TITLE = {"au10": "澳 10Y(月)", "nz10": "紐 10Y(月)", "us10": "美 10Y(月)",
             "au3m": "澳 3M 票據(月)", "nz3m": "紐 3M 票據(月)", "us3m": "美 3M(月)"}


def job_rates():
    u = (f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{'+'.join(POLICY_TITLE)}"
         "?startPeriod=2000-01&format=csv")
    d = pd.read_csv(io.StringIO(_get(u, headers={**UA, "Accept": "text/csv"}).text))
    d["date"] = pd.to_datetime(d.TIME_PERIOD)
    p = d.pivot_table(index="date", columns="REF_AREA", values="OBS_VALUE")
    for a, t in POLICY_TITLE.items():
        _save(f"rate_pol_{a.lower()}", t, p[a])
    for k, sid in MEI.items():
        _save(f"rate_{k}", MEI_TITLE[k], fred(sid).loc["1990":])
    logger.info(f"rates: BIS 到 {p.index[-1]:%Y-%m}, RBA {p.AU.iloc[-1]}, RBNZ {p.NZ.iloc[-1]}")
    return p


# ---------------------------------------------------------------------------
# 4. 中國與商品（澳元頁）
# ---------------------------------------------------------------------------
def job_china(fx, policy):
    iron, cu = fred("PIORECRUSDM"), fred("PCOPPUSDM")
    ppi = fred("CHNPIEATI01GYM")  # OECD MEI，到 2022-12
    s = _get("https://api.db.nomics.world/v22/series/NBS/M_A010801/A01080101?observations=1").json()["series"]["docs"][0]
    nbs = pd.Series([v - 100 if v not in (None, "NA") else None for v in s["value"]],
                    index=pd.to_datetime(s["period"]), dtype=float).dropna()  # 上年同月=100 → 年增率
    ppi = pd.concat([ppi, nbs[nbs.index > ppi.index.max()]])
    aud_m = fx["AU"].resample("MS").mean()
    yoy = lambda x: (x / x.shift(12) - 1) * 100
    z = lambda x: (x - x.loc[START:].mean()) / x.loc[START:].std()
    _save("cn_iron_ore", "鐵礦石(美元/噸, IMF)", iron.loc["1999":])
    _save("cn_copper", "銅(美元/噸, IMF)", cu.loc["1999":])
    _save("cn_ppi_yoy", "中國 PPI 年增率%", ppi.loc["1999":])
    _save("cn_iron_yoy", "鐵礦石 12個月變化%", yoy(iron).loc[START:])
    _save("cn_copper_yoy", "銅 12個月變化%", yoy(cu).loc[START:])
    _save("ccy_aud_yoy_m", "AUD/USD 12個月變化%(月均)", yoy(aud_m).loc[START:])
    _save("cn_iron_z", "鐵礦石 z分數(2000起)", z(iron).loc[START:])
    _save("rate_rba_z", "RBA 現金利率 z分數(2000起)", z(policy.AU).loc[START:])
    logger.info(f"china: iron 到 {iron.index[-1]:%Y-%m}, PPI 到 {ppi.index[-1]:%Y-%m}")


# ---------------------------------------------------------------------------
# 5. 國際收支（OECD）
# ---------------------------------------------------------------------------
BOP_KEEP = {"CA": "ca", "G": "goods", "S": "services", "IN1": "primary_income",
            "FA": "fa", "FA_D_F": "fa_direct", "FA_P_F": "fa_portfolio", "FA_O_F": "fa_other", "EO": "eo"}


def job_bop(iso3, pfx, cur):
    u = (f"https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_BOP@DF_BOP,/{iso3}.........."
         "?startPeriod=1990-Q1&format=csvfile")
    d = pd.read_csv(io.StringIO(_get(u, timeout=180).text))
    q = d[(d.FREQ == "Q") & (d.UNIT_MEASURE == "XDC") & (d.ADJUSTMENT == "N")
          & d.ACCOUNTING_ENTRY.isin(["B", "N"])]
    b = q.pivot_table(index="TIME_PERIOD", columns="MEASURE", values="OBS_VALUE")
    b = b[[c for c in BOP_KEEP if c in b.columns]].rename(columns=BOP_KEEP)
    b.index = pd.PeriodIndex(b.index.str.replace("-", ""), freq="Q").to_timestamp(how="end").normalize()
    r4 = lambda s: s.rolling(4).sum() / 1000  # 4 季滾動，十億本幣；BPM6 FA>0 = 淨流出，取負號 = 淨流入
    out = {
        "ca4": (r4(b.ca), "經常帳"), "inflow4": (-r4(b.fa), "資本淨流入(−金融帳)"), "eo4": (r4(b.eo), "誤差遺漏"),
        "goods4": (r4(b.goods), "商品貿易"), "serv4": (r4(b.services), "服務"),
        "gs4": (r4(b.goods + b.services), "商品＋服務"), "pi4": (r4(b.primary_income), "初級收入(投資收益)"),
        "port4": (-r4(b.fa_portfolio), "證券投資淨流入"), "fdi4": (-r4(b.fa_direct), "直接投資淨流入"),
        "oth4": (-r4(b.fa_other), "其他投資淨流入"),
    }
    for k, (s, t) in out.items():
        _save(f"bop_{pfx}_{k}", f"{t}（4季滾動, 十億{cur}）", s.loc[START:])
    logger.info(f"bop {iso3}: 到 {b.index[-1]:%Y-%m}")


# ---------------------------------------------------------------------------
# 6. 紐西蘭：GDT 乳價、Stats NZ 淨移民
# ---------------------------------------------------------------------------
GDT = "https://s3.amazonaws.com/www-production.globaldairytrade.info/results/"


def job_dairy():
    guid = _get(GDT + "latest.json").json()["latestEvent"]
    ev = _get(f"{GDT}{guid}/price_indices_ten_years.json").json()["PriceIndicesTenYears"]["Events"]["EventDetails"]
    s = pd.Series({datetime.strptime(e["EventDate"], "%B %d, %Y %H:%M:%S"): float(e["PriceIndex"]) for e in ev})
    s.index = s.index.normalize()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    _save("nz_gdt_index", "GDT 乳製品價格指數(每場拍賣)", s)
    logger.info(f"dairy: {len(s)} 場，最新 {s.index[-1]:%Y-%m-%d} = {s.iloc[-1]:,.0f}")


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]
MON_ABBR = {m[:3]: i + 1 for i, m in enumerate(MONTHS)}


def _statsnz_latest_page():
    """Stats NZ 每月中發佈前 2 個月的資料，網址 international-migration-<month>-<year>；
    從上個月往回找第一個存在的發佈頁（未發佈的月份回 404）。"""
    today = date.today()
    for back in range(1, 7):
        y, m = divmod(today.year * 12 + today.month - 1 - back, 12)
        url = f"https://www.stats.govt.nz/information-releases/international-migration-{MONTHS[m]}-{y}/"
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 200 and "GraphCsvData" in r.text:
            return url, r.text
        time.sleep(1)
    raise RuntimeError("找不到近 6 個月的 Stats NZ international-migration 發佈頁")


def _graph_csvs(page):
    """頁面內嵌的 SeriesData[].GraphCsvData（與官方下載檔一致），回傳 {圖表標題: DataFrame}。"""
    text = html_mod.unescape(page)
    out = {}
    for m in re.finditer(r'"Title":"((?:[^"\\]|\\.)*)","ClassName":"SeriesGroup"', text):
        j = text.find('"GraphCsvData":"', m.end())
        if j == -1 or j - m.end() > 2000:
            continue
        k = j + len('"GraphCsvData":"')
        raw = re.match(r'((?:[^"\\]|\\.)*)"', text[k:]).group(1)
        rows = [r for r in csv.reader(io.StringIO(json.loads('"' + raw + '"').lstrip("﻿")))
                if any(c.strip() for c in r)]
        if len(rows) < 2 or len(rows[0]) < 3:
            continue
        idx = []
        for lab in rows[0][1:]:
            mm = re.match(r"([A-Za-z]{3})\s*[-\s]\s*(\d{4})", lab.strip())
            idx.append(pd.Timestamp(int(mm.group(2)), MON_ABBR[mm.group(1).lower()], 1) if mm else pd.NaT)
        width = min([len(idx)] + [len(r) - 1 for r in rows[1:]])
        df = pd.DataFrame({r[0].strip(): pd.to_numeric(r[1:width + 1], errors="coerce") for r in rows[1:]},
                          index=idx[:width])
        out[json.loads('"' + m.group(1) + '"')] = df[df.index.notna()]
    return out


def job_migration():
    url, page = _statsnz_latest_page()
    frames = _graph_csvs(page)

    def pick(title_sub, col):
        for t, df in frames.items():
            if title_sub in t.lower() and col in df.columns:
                return df[col]
        raise KeyError(f"Stats NZ 頁面找不到 {title_sub} / {col}（頁面結構可能已變更）")

    total = pick("migration by direction, rolling", "Net migration")
    nz = pick("migration by citizenship, rolling", "Net migration (NZ citizens)")
    non = pick("migration by citizenship, rolling", "Net migration (non-NZ citizens)")
    _save("nz_migr_net_total", "紐西蘭全體淨移民(12個月滾動)", total)
    _save("nz_migr_net_nz", "紐西蘭公民淨移民(12個月滾動)", nz)
    _save("nz_migr_net_non_nz", "非紐西蘭公民淨移民(12個月滾動)", non)
    logger.info(f"migration: {url.rsplit('/', 2)[-2]}，到 {total.index[-1]:%Y-%m} net={total.iloc[-1]:,.0f}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def fetch_aud_nzd_series():
    failed = []

    def run(name, fn, *a):
        try:
            return fn(*a)
        except Exception as e:
            logger.exception(f"aud/nzd {name} 失敗 — {e}")
            failed.append(f"{name}: {e}")

    fx = run("fx", job_fx)
    policy = run("rates", job_rates)
    if fx is not None:
        run("cot", job_cot, fx)
        if policy is not None:
            run("china", job_china, fx, policy)
    run("bop AUS", job_bop, "AUS", "au", "澳元")
    run("bop NZL", job_bop, "NZL", "nz", "紐元")
    run("dairy", job_dairy)
    run("migration", job_migration)
    if fx is None:
        failed.append("cot/china: 因 fx 失敗而略過")
    if failed:
        raise RuntimeError("; ".join(failed))


if __name__ == "__main__":
    fetch_aud_nzd_series()
