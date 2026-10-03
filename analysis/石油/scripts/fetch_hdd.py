# -*- coding: utf-8 -*-
"""石油／冬季取暖學習案例：採暖度日（HDD），一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/石油/data/：
- hdd_daily.csv     日 HDD，2015-01-01 起到昨天（Open-Meteo 歷史再分析）
                      hdd_<城市>    各城市 HDD（歐洲 °C 度日，美國 °F 度日）
                      eu_hdd         歐洲 8 城加權合成（base 18°C，無門檻）
                      eu_hdd_eurostat 同權重，但用 Eurostat 定義（Tm ≤ 15°C 才計 18 − Tm，否則 0）
                      us_ne_hdd      美東 4 城加權合成（base 65°F）
                    hdd_london 只作參考（英國非 EU、但 NBP 與 TTF 高度連動），不進 eu_hdd。
- hdd_5y.csv        以「取暖季」（7/1 起算）比較，index = 本季每一天（%Y-%m-%d，剔除 2/29）：
                      <x>_cur / <x>_prev             本季 / 上一季 當日 HDD
                      <x>_5y_min / _avg / _max        前 5 季同月日
                      <x>_cum_cur / _cum_prev / _cum_5y_avg   自 7/1 起累積 HDD
                      <x>_cum_dev_5y                  本季累積 − 5 季平均累積
                    x ∈ {eu_hdd, us_ne_hdd}
- hdd_forecast.csv  Open-Meteo 預報：過去 7 天 + 未來 16 天，各城市 HDD 與兩個合成，kind = past / fcst
- hdd_noaa_cpc.csv  NOAA CPC 官方「人口／用戶加權」日 HDD，美國 9 個 Census Division + CONUS，2006 起，°F
                      gas_<區>  Utility Gas 用戶加權（對天然氣需求最貼近）
                      pop_<區>  人口加權（新聞常引用的版本）
                      oil_<區>  燃油／煤油用戶加權（取暖油 = 柴油餾分，美東最重要）
                    區碼：ne New England、ma Middle Atlantic、enc East North Central、wnc West North Central、
                          sa South Atlantic、esc East South Central、wsc West South Central、mtn Mountain、
                          pac Pacific、conus 本土 48 州

來源：
- Open-Meteo 歷史：https://archive-api.open-meteo.com/v1/archive（best_match = ERA5/ERA5-Land + ECMWF IFS 分析，
  最後約 5 天是初步值，之後會被 ERA5 正式值取代）
- Open-Meteo 預報：https://api.open-meteo.com/v1/forecast（past_days=7, forecast_days=16；
  與 archive 模型不同，重疊日會有小差異）
- NOAA CPC：https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data/<年>/<權重>.Heating.txt
  （2026-09-30 實測到 2026-09-27；每日更新；每年一個檔）

HDD 定義（本腳本統一用 Tm = (Tmax + Tmin) / 2，與 NOAA、Eurostat 的官方慣例相同，而非 24 小時平均）：
- 歐洲：HDD = max(0, 18 − Tm)，°C。Eurostat 官方定義另有 15°C 門檻（Tm > 15°C 時 HDD = 0），
  另給 eu_hdd_eurostat 欄；兩者差異只在春秋過渡季。
- 美國：HDD = max(0, 65 − Tm)，°F（NOAA 慣例）。1 °F 度日 = 5/9 °C 度日，兩地數值不可直接相比。
- 城市點位 HDD 只是代理；Open-Meteo 格點是 ~9–25 km 網格，城市熱島效應未必反映。
- 水準偏差（2026-09-30 實測）：城市點位比官方全國／分區加權 HDD 偏低。
  us_ne_hdd 年合計約 4,200–5,100 °F，NOAA pop_ma 約 5,100–5,800、pop_ne 約 5,600–6,300（日相關 0.99）；
  eu_hdd 年合計約 2,300–2,800 °C，低於 Eurostat EU 全國口徑（約 2,900–3,000，未在本腳本驗證）。
  → 看「相對 5 年平均的偏離」沒問題，比絕對水準請用官方數據。

合成權重（粗估，自訂，非官方）：
- 歐洲：依各國天然氣年消費量的大約比例（約 2023 年 Eurostat nrg_cb_gas 量級，取整，僅 8 國內部相對比重）：
    Berlin(DE) 0.30、Milan(IT) 0.25、Paris(FR) 0.13、Amsterdam(NL) 0.12、Warsaw(PL) 0.08、
    Brussels(BE) 0.06、Vienna(AT) 0.03、Budapest(HU) 0.03
  注意：各國消費含發電與工業，並非全是取暖需求；一國一城也無法代表南北溫差（如義大利）。
- 美東：依都會區人口大約比例：New York 0.53、Philadelphia 0.17、Washington 0.17、Boston 0.13
  要看官方加權版本請用 hdd_noaa_cpc.csv 的 gas_ne / gas_ma。
"""
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UA = {"User-Agent": "Mozilla/5.0"}
START = "2015-01-01"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
NOAA = "https://ftp.cpc.ncep.noaa.gov/htdocs/degree_days/weighted/daily_data"

# name: (lat, lon, weight)
EU_CITIES = {
    "berlin": (52.52, 13.405, 0.30),
    "milan": (45.464, 9.19, 0.25),
    "paris": (48.857, 2.352, 0.13),
    "amsterdam": (52.37, 4.895, 0.12),
    "warsaw": (52.23, 21.012, 0.08),
    "brussels": (50.85, 4.35, 0.06),
    "vienna": (48.208, 16.373, 0.03),
    "budapest": (47.498, 19.04, 0.03),
}
REF_CITIES = {"london": (51.507, -0.128, 0.0)}  # 只作參考，°C
US_CITIES = {
    "newyork": (40.713, -74.006, 0.53),
    "philadelphia": (39.953, -75.165, 0.17),
    "washington": (38.907, -77.037, 0.17),
    "boston": (42.36, -71.06, 0.13),
}
NOAA_WEIGHTS = {"gas": "UtilityGas", "pop": "Population", "oil": "FuelOilKeroseneEtc"}
NOAA_REGIONS = {"1": "ne", "2": "ma", "3": "enc", "4": "wnc", "5": "sa",
                "6": "esc", "7": "wsc", "8": "mtn", "9": "pac", "CONUS": "conus"}


def get(url, params=None, tries=5, text=False):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=120)
            if r.status_code == 429:
                print("  429 rate limited，等 65 秒…")
                time.sleep(65)
                continue
            r.raise_for_status()
            return r.text if text else r.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
            wait = 5 * (i + 1)
            print(f"  網路錯誤 {type(e).__name__}: {e}；{wait} 秒後重試（{i + 1}/{tries}）")
            time.sleep(wait)
    raise RuntimeError(f"重試 {tries} 次仍失敗：{url} {params}")


def tm_series(j):
    d = j["daily"]
    s = (pd.Series(d["temperature_2m_max"], dtype=float) + pd.Series(d["temperature_2m_min"], dtype=float)) / 2
    s.index = pd.to_datetime(d["time"])
    return s


def city_tm(url, lat, lon, unit, extra):
    params = {"latitude": lat, "longitude": lon, "daily": "temperature_2m_max,temperature_2m_min",
              "timezone": "auto", "temperature_unit": unit, **extra}
    return tm_series(get(url, params))


def hdd_frame(url, extra):
    """回傳 (各城市 HDD DataFrame)，欄 hdd_<城市>，加上 eu_hdd / eu_hdd_eurostat / us_ne_hdd。"""
    cols, tms = {}, {}
    for group, unit, base in [(EU_CITIES, "celsius", 18), (REF_CITIES, "celsius", 18), (US_CITIES, "fahrenheit", 65)]:
        for name, (lat, lon, _) in group.items():
            tm = city_tm(url, lat, lon, unit, extra)
            tms[name] = tm
            cols[f"hdd_{name}"] = (base - tm).clip(lower=0)
            time.sleep(2.0)
    df = pd.DataFrame(cols)
    # 合成：任一城市缺值 → 合成為 NaN（sum(min_count) 以避免把缺值當 0）
    eu_w = pd.Series({f"hdd_{k}": v[2] for k, v in EU_CITIES.items()})
    us_w = pd.Series({f"hdd_{k}": v[2] for k, v in US_CITIES.items()})
    df["eu_hdd"] = df[eu_w.index].mul(eu_w).sum(axis=1, min_count=len(eu_w))
    df.loc[df[eu_w.index].isna().any(axis=1), "eu_hdd"] = float("nan")
    euro = pd.DataFrame({f"hdd_{k}": (18 - tms[k]).where(tms[k] <= 15, 0.0) for k in EU_CITIES})
    df["eu_hdd_eurostat"] = euro.mul(eu_w).sum(axis=1, min_count=len(eu_w))
    df.loc[euro.isna().any(axis=1), "eu_hdd_eurostat"] = float("nan")
    df["us_ne_hdd"] = df[us_w.index].mul(us_w).sum(axis=1, min_count=len(us_w))
    df.loc[df[us_w.index].isna().any(axis=1), "us_ne_hdd"] = float("nan")
    df.index.name = "date"
    return df


def season_start(ts):
    return ts.year if ts.month >= 7 else ts.year - 1


def build_5y(daily, comps=("eu_hdd", "us_ne_hdd")):
    d = daily[~((daily.index.month == 2) & (daily.index.day == 29))]
    last = daily[list(comps)].dropna().index[-1]
    cur = season_start(last)
    prior = list(range(cur - 5, cur))
    idx = pd.date_range(f"{cur}-07-01", f"{cur + 1}-06-30", freq="D")
    idx = idx[~((idx.month == 2) & (idx.day == 29))]
    keys = idx.strftime("%m-%d")
    seas = d.index.map(season_start)
    res = pd.DataFrame(index=idx)
    res.index.name = "date"
    for c in comps:
        tab = pd.DataFrame({"md": d.index.strftime("%m-%d"), "season": seas, "v": d[c].values}) \
            .pivot(index="md", columns="season", values="v").reindex(keys)
        # 前 5 季要完整，否則累積值會被低估
        full_prior = [s for s in prior if s in tab.columns and tab[s].notna().all()]
        if len(full_prior) < len(prior):
            print(f"  !! {c}: 前 5 季中只有 {full_prior} 完整")
        cum = tab.cumsum(skipna=False)
        res[f"{c}_cur"] = tab[cur].values if cur in tab.columns else float("nan")
        res[f"{c}_prev"] = tab[cur - 1].values if cur - 1 in tab.columns else float("nan")
        res[f"{c}_5y_min"] = tab[full_prior].min(axis=1).values
        res[f"{c}_5y_avg"] = tab[full_prior].mean(axis=1).values
        res[f"{c}_5y_max"] = tab[full_prior].max(axis=1).values
        res[f"{c}_cum_cur"] = cum[cur].values if cur in cum.columns else float("nan")
        res[f"{c}_cum_prev"] = cum[cur - 1].values if cur - 1 in cum.columns else float("nan")
        res[f"{c}_cum_5y_avg"] = cum[full_prior].mean(axis=1).values
        res[f"{c}_cum_dev_5y"] = res[f"{c}_cum_cur"] - res[f"{c}_cum_5y_avg"]
    print(f"  本季 {cur}/{str(cur + 1)[2:]}；5 季比較基期 {prior[0]}/{str(prior[0] + 1)[2:]}"
          f" – {prior[-1]}/{str(prior[-1] + 1)[2:]}")
    return res


def parse_noaa(txt):
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    hdr_i = next(i for i, ln in enumerate(lines) if ln.startswith("Region|"))
    dates = pd.to_datetime(lines[hdr_i].split("|")[1:], format="%Y%m%d")
    out = {}
    for ln in lines[hdr_i + 1:]:
        parts = ln.split("|")
        if parts[0] not in NOAA_REGIONS:
            continue
        vals = pd.to_numeric(pd.Series(parts[1:len(dates) + 1]), errors="coerce")
        vals = vals.where(vals >= 0)  # 負值／缺值代碼 → NaN
        out[NOAA_REGIONS[parts[0]]] = pd.Series(vals.values, index=dates[:len(vals)])
    return pd.DataFrame(out)


def fetch_noaa():
    frames = []
    for pre, fname in NOAA_WEIGHTS.items():
        yrs = []
        for y in range(2006, date.today().year + 1):
            try:
                txt = get(f"{NOAA}/{y}/{fname}.Heating.txt", text=True, tries=3)
            except RuntimeError as e:
                print(f"  !! NOAA {y} {fname} 抓不到：{e}")
                continue
            yrs.append(parse_noaa(txt))
            time.sleep(0.3)
        df = pd.concat(yrs).sort_index()
        df = df[~df.index.duplicated(keep="last")]
        frames.append(df.add_prefix(f"{pre}_"))
    out = pd.concat(frames, axis=1).sort_index()
    out.index.name = "date"
    return out.dropna(how="all")


def save(df, name, fmt="%.3f"):
    df.to_csv(OUT / name, date_format="%Y-%m-%d", float_format=fmt)
    print(f"{name} {len(df)} rows {df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}")


def main():
    yday = (date.today() - timedelta(days=1)).isoformat()
    print("Open-Meteo archive …")
    daily = hdd_frame(ARCHIVE, {"start_date": START, "end_date": yday})
    daily = daily.dropna(how="all")
    save(daily, "hdd_daily.csv")
    summer = daily[daily.index.month.isin([7, 8])]
    print(f"  7–8 月平均：eu_hdd {summer['eu_hdd'].mean():.2f}、us_ne_hdd {summer['us_ne_hdd'].mean():.2f}；"
          f"1 月平均：eu_hdd {daily[daily.index.month == 1]['eu_hdd'].mean():.2f}、"
          f"us_ne_hdd {daily[daily.index.month == 1]['us_ne_hdd'].mean():.2f}")

    save(build_5y(daily), "hdd_5y.csv")

    print("Open-Meteo forecast …")
    fc = hdd_frame(FORECAST, {"past_days": 7, "forecast_days": 16}).dropna(how="all")
    fc.insert(0, "kind", ["past" if ts.date() < date.today() else "fcst" for ts in fc.index])
    save(fc, "hdd_forecast.csv")

    print("NOAA CPC …")
    save(fetch_noaa(), "hdd_noaa_cpc.csv", fmt="%.0f")


if __name__ == "__main__":
    main()
