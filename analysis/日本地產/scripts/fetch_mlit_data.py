# -*- coding: utf-8 -*-
"""日本地產分析：MLIT 不動產情報庫（reinfolib）XIT001 + 國土數值情報 L01 正式抓取（三大都市圈）

輸出到 analysis/日本地產/data/：
- shutoken_kenuri_quarterly.csv      首都圈四縣 新築建売代理（宅地(土地と建物)、屋齡 ≤1 年）季度成交筆數與總價中位數（萬圓）
- metro3_used_condo_quarterly.csv    東京／大阪／愛知 中古マンション等 季度成交筆數與㎡單價中位數（萬圓/㎡）
- tokyo23_condo_age_controlled.csv   東京 23 區中古公寓固定屋齡權重指數（權重 = 2021 全年各屋齡層成交筆數占比；待驗）
- metro3_land_price_yoy_annual.csv   東京／大阪／愛知 公示地價（L01）住宅地／商業地年變動率中位數與平均（2016–）

資料口徑（來自 mlit-api/research 三輪調研）：
- XIT001 的 PriceCategory 有兩種：不動産取引価格情報（問卷申報）與 成約価格情報（疑似來自 REINS，2021Q1 起）。
  2025Q1 筆數跳升約 98% 來自成約價格情報，所以所有序列都分 PriceCategory 輸出（全体／兩個分類），不要直接把 全体 當連續序列。
- 官方快照會被事後回補，每列帶 snapshot_date（該年檔案的抓取日）；最新 2 季標 provisional=True，只能畫暫定值。
- 常態更新：預設只重抓覆蓋最近 2 季的年份，其餘用快取；--refresh-all 全部重抓。

使用：
    venv\\Scripts\\python.exe -u analysis\\日本地產\\scripts\\fetch_mlit_data.py [--only xit001|l01] [--refresh-all] [--skip-fetch]

金鑰：專案根目錄 .env 的 MLIT_TOKEN（Ocp-Apim-Subscription-Key）。金鑰連續 3 年無呼叫會被廢止，嚴禁寫入程式碼或提交。
請求規範：每請求 timeout=60、間隔 >= 1.5 秒；XIT001 無資料時回 HTTP 404（視為空）。

對外發布時必須標示：出典：国土交通省 不動産情報ライブラリ（https://www.reinfolib.mlit.go.jp/）
「『不動産取引価格情報』（国土交通省）をもとに MacroMicro 作成」
"""
import argparse
import datetime
import json
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_DIR = OUT_DIR / "_mlit_cache"
XIT_URL = "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001"
L01_URL = "https://nlftp.mlit.go.jp/ksj/gml/data/L01/L01-{yy}/L01-{yy}_{pref}_GML.zip"
SLEEP = 1.5
TODAY = datetime.date.today()

SHUTOKEN = {13: "東京都", 14: "神奈川県", 11: "埼玉県", 12: "千葉県"}
METRO3 = {13: "東京都", 27: "大阪府", 23: "愛知県"}
XIT_AREAS = {**SHUTOKEN, **METRO3}
XIT_FIRST_YEAR = 2021  # 成約価格情報自 2021Q1 起
CATEGORIES = ["不動産取引価格情報", "成約価格情報"]
L01_PREFS = METRO3
L01_YEARS = range(2016, TODAY.year + 1)
MIN_BUCKET_N = 10


def get_token():
    env = ROOT / ".env"
    if not env.exists():
        raise RuntimeError(f"找不到 {env}")
    for line in env.read_text("utf-8", "ignore").splitlines():
        line = line.strip()
        if line.startswith("MLIT_TOKEN") and "=" in line:
            return line.split("=", 1)[1].strip().strip("'\"")
    raise RuntimeError(".env 中找不到 MLIT_TOKEN")


# ---------------------------------------------------------------- 解析
def parse_quarter(p):
    m = re.match(r"(\d{4})年第([1-4])四半期", p) if isinstance(p, str) else None
    return f"{m.group(1)}Q{m.group(2)}" if m else ""


def parse_build_year(by):
    if not isinstance(by, str) or not by.strip():
        return None
    by = by.strip()
    if by == "戦前":
        return 1945
    for era, base in [("令和", 2018), ("平成", 1988), ("昭和", 1925)]:
        m = re.match(era + r"(\d+|元)年?", by)
        if m:
            return base + (1 if m.group(1) == "元" else int(m.group(1)))
    m = re.match(r"(\d{4})年?", by)
    return int(m.group(1)) if m else None


def clean_area(a):
    s = re.sub(r"[^\d.]", "", str(a)) if a is not None else ""
    try:
        v = float(s)
        return v if v > 0 else np.nan
    except ValueError:
        return np.nan


# ---------------------------------------------------------------- XIT001 抓取
def years_to_refresh():
    """覆蓋最近 2 季的年份：1–3 月要連前一年一起重抓。"""
    ys = {TODAY.year}
    if TODAY.month <= 3:
        ys.add(TODAY.year - 1)
    return ys


def fetch_xit001(refresh_all):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    mf_path = CACHE_DIR / "xit001_manifest.json"
    manifest = json.loads(mf_path.read_text("utf-8")) if mf_path.exists() else {}
    token = get_token()
    headers = {"Ocp-Apim-Subscription-Key": token, "User-Agent": "MacroMicro-MLIT-Fetch/1.0"}
    fresh = years_to_refresh()
    tasks = [(a, y) for a in XIT_AREAS for y in range(XIT_FIRST_YEAR, TODAY.year + 1)]
    n_req = 0
    for area, y in tasks:
        key = f"{area}_{y}"
        cf = CACHE_DIR / f"xit001_{key}.json"
        if cf.exists() and key in manifest and not refresh_all and y not in fresh:
            continue
        data = None
        for attempt in range(3):
            try:
                r = requests.get(XIT_URL, params={"year": y, "area": area}, headers=headers, timeout=60)
                if r.status_code == 200:
                    data = r.json().get("data", [])
                elif r.status_code == 404:
                    data = []
                else:
                    print(f"  HTTP {r.status_code} area={area} year={y}（第 {attempt + 1} 次）")
            except Exception as e:  # noqa: BLE001
                print(f"  請求異常 area={area} year={y}: {e}（第 {attempt + 1} 次）")
            n_req += 1
            time.sleep(SLEEP)
            if data is not None:
                break
        if data is None:
            print(f"  放棄 area={area} year={y}，沿用舊快取（若有）")
            continue
        cf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        manifest[key] = TODAY.isoformat()
        mf_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  XIT001 area={area} year={y}: {len(data):,} 筆")
    print(f"XIT001 本次請求 {n_req} 次")


def load_xit001():
    manifest = json.loads((CACHE_DIR / "xit001_manifest.json").read_text("utf-8"))
    keep = ["Type", "PriceCategory", "Period", "TradePrice", "Area", "BuildingYear", "MunicipalityCode"]
    frames = []
    for area, name in XIT_AREAS.items():
        for y in range(XIT_FIRST_YEAR, TODAY.year + 1):
            key = f"{area}_{y}"
            cf = CACHE_DIR / f"xit001_{key}.json"
            if not cf.exists():
                continue
            recs = json.loads(cf.read_text("utf-8"))
            if not recs:
                continue
            df = pd.DataFrame(recs)
            df = df[[c for c in keep if c in df.columns]].copy()
            df["area_code"] = area
            df["prefecture"] = name
            df["snapshot_date"] = manifest.get(key, "")
            frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["quarter"] = df["Period"].map(parse_quarter)
    df = df[df["quarter"] != ""].copy()
    df["trade_year"] = df["quarter"].str[:4].astype(int)
    df["price"] = pd.to_numeric(df["TradePrice"], errors="coerce")
    df["area_sqm"] = df["Area"].map(clean_area)
    df["build_year"] = df["BuildingYear"].map(parse_build_year)
    return df[df["price"] > 0].copy()


def with_all_category(df):
    """加上 全体 分類（= 兩種 PriceCategory 合計）。"""
    all_df = df.copy()
    all_df["PriceCategory"] = "全体"
    return pd.concat([df, all_df], ignore_index=True)


def mark_provisional(out, quarters):
    last2 = sorted(set(quarters))[-2:]
    out["provisional"] = out["quarter"].isin(last2)
    return out


def snapshot(g):
    return g["snapshot_date"].max()


def build_kenuri(df):
    d = df[(df["Type"] == "宅地(土地と建物)") & (df["area_code"].isin(SHUTOKEN))].copy()
    age = d["trade_year"] - d["build_year"]
    d = d[(age >= -1) & (age <= 1)]
    d["price_10k"] = d["price"] / 1e4
    d = with_all_category(d)
    rows = []
    for (q, cat), g in d.groupby(["quarter", "PriceCategory"]):
        for scope, sub in [("首都圏4縣合計", g)] + [(n, g[g["area_code"] == a]) for a, n in SHUTOKEN.items()]:
            if len(sub):
                rows.append({"quarter": q, "prefecture": scope, "price_category": cat, "transactions": len(sub),
                             "median_total_price_10k_yen": round(float(sub["price_10k"].median()), 1),
                             "snapshot_date": snapshot(sub)})
    out = pd.DataFrame(rows).sort_values(["price_category", "prefecture", "quarter"])
    return mark_provisional(out, out["quarter"])


def build_condo(df):
    d = df[(df["Type"] == "中古マンション等") & (df["area_code"].isin(METRO3)) & (df["area_sqm"] > 0)].copy()
    d["sqm_10k"] = d["price"] / d["area_sqm"] / 1e4
    d = with_all_category(d)
    rows = []
    for (q, cat, pref), g in d.groupby(["quarter", "PriceCategory", "prefecture"]):
        rows.append({"quarter": q, "prefecture": pref, "price_category": cat, "transactions": len(g),
                     "median_sqm_price_10k_yen": round(float(g["sqm_10k"].median()), 2),
                     "snapshot_date": snapshot(g)})
    out = pd.DataFrame(rows).sort_values(["price_category", "prefecture", "quarter"])
    return mark_provisional(out, out["quarter"])


AGE_BUCKETS = [("≤10年", 0, 10), ("11-20年", 11, 20), ("21-30年", 21, 30), (">30年", 31, 999)]


def build_age_controlled(df):
    d = df[(df["Type"] == "中古マンション等") & (df["area_code"] == 13) & (df["area_sqm"] > 0)].copy()
    code = pd.to_numeric(d["MunicipalityCode"], errors="coerce")
    d = d[(code >= 13101) & (code <= 13123)]
    d["sqm_10k"] = d["price"] / d["area_sqm"] / 1e4
    d["age"] = (d["trade_year"] - d["build_year"]).clip(lower=0)
    d = d.dropna(subset=["age"])
    d["bucket"] = None
    for name, lo, hi in AGE_BUCKETS:
        d.loc[(d["age"] >= lo) & (d["age"] <= hi), "bucket"] = name
    d = with_all_category(d)
    names = [b[0] for b in AGE_BUCKETS]
    rows = []
    for cat, gc in d.groupby("PriceCategory"):
        base = gc[gc["trade_year"] == 2021]
        if cat == "成約価格情報":  # 2021 全年都有資料，不特別處理；保留以便日後改基期
            pass
        w = base["bucket"].value_counts(normalize=True).reindex(names).fillna(0.0)
        for q, g in gc.groupby("quarter"):
            med = g.groupby("bucket")["sqm_10k"].median().reindex(names)
            cnt = g.groupby("bucket").size().reindex(names).fillna(0).astype(int)
            ok = cnt >= MIN_BUCKET_N
            wsum = w[ok].sum()
            idx = float((med[ok] * w[ok]).sum() / wsum) if wsum > 0 else np.nan
            row = {"quarter": q, "price_category": cat, "transactions": len(g),
                   "median_unadjusted_10k_per_sqm": round(float(g["sqm_10k"].median()), 2),
                   "fixed_weight_10k_per_sqm": round(idx, 2) if idx == idx else None,
                   "buckets_used": "|".join(n for n in names if ok[n]), "snapshot_date": snapshot(g)}
            for n in names:
                row[f"median_{n}"] = round(float(med[n]), 2) if med[n] == med[n] else None
                row[f"n_{n}"] = int(cnt[n])
            rows.append(row)
    out = pd.DataFrame(rows).sort_values(["price_category", "quarter"])
    return mark_provisional(out, out["quarter"])


# ---------------------------------------------------------------- L01
def l01_zip(year, pref):
    yy = f"{year % 100:02d}"
    dest = CACHE_DIR / "l01" / f"L01-{yy}_{pref}_GML.zip"
    if dest.exists() and dest.stat().st_size > 1000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(L01_URL.format(yy=yy, pref=pref), timeout=60)
    time.sleep(SLEEP)
    if r.status_code != 200:
        print(f"  L01 {year} pref={pref}: HTTP {r.status_code}")
        return None
    dest.write_bytes(r.content)
    return dest


def read_l01(zpath):
    import geopandas as gpd

    tmp = Path(tempfile.mkdtemp(prefix="l01_"))
    try:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
        files = list(tmp.rglob("*.geojson")) or list(tmp.rglob("*.shp"))
        if not files:
            return None
        try:
            return gpd.read_file(files[0], ignore_geometry=True)
        except TypeError:
            return pd.DataFrame(gpd.read_file(files[0]).drop(columns="geometry"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# 2016–2021 檔案沒有現成年變動率欄位，用「當年價 / 前年價」自行計算（欄位對照見 report.md 的 L01 表）
L01_PRICE_COLS = {2016: ("L01_081", "L01_080"), 2017: ("L01_082", "L01_081"), 2018: ("L01_091", "L01_090"),
                  2019: ("L01_092", "L01_091"), 2020: ("L01_093", "L01_092"), 2021: ("L01_094", "L01_093")}


def l01_yoy(df, year):
    use_col = "L01_002" if year >= 2024 else "L01_001"
    if year in L01_PRICE_COLS:
        cur, prev = L01_PRICE_COLS[year]
        a = pd.to_numeric(df[cur], errors="coerce")
        b = pd.to_numeric(df[prev], errors="coerce")
        yoy = (a - b) / b * 100
    else:
        yoy = pd.to_numeric(df["L01_009" if year >= 2024 else "L01_007"], errors="coerce")
    return df[use_col].astype(str).str.strip(), yoy.replace([np.inf, -np.inf], np.nan)


def build_l01():
    rows = []
    for year in L01_YEARS:
        for pref, name in L01_PREFS.items():
            z = l01_zip(year, pref)
            if z is None:
                continue
            df = read_l01(z)
            if df is None:
                print(f"  L01 {year} {name}: 解壓後找不到 geojson/shp")
                continue
            use, yoy = l01_yoy(df, year)
            for code, label in [("000", "住宅地"), ("005", "商業地")]:
                s = yoy[(use == code) & yoy.notna()]
                if len(s):
                    rows.append({"year": year, "prefecture": name, "land_use": label, "n_points": len(s),
                                 "yoy_median_pct": round(float(s.median()), 2), "yoy_mean_pct": round(float(s.mean()), 2)})
            print(f"  L01 {year} {name}: {len(df):,} 點")
    return pd.DataFrame(rows).sort_values(["prefecture", "land_use", "year"])


# ---------------------------------------------------------------- main
def save(df, name):
    path = OUT_DIR / name
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"寫出 {path.name}: {len(df)} 列")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["xit001", "l01"])
    ap.add_argument("--refresh-all", action="store_true")
    ap.add_argument("--skip-fetch", action="store_true", help="XIT001 只用快取，不發請求")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.only != "l01":
        if not args.skip_fetch:
            fetch_xit001(args.refresh_all)
        df = load_xit001()
        print(f"XIT001 載入 {len(df):,} 筆，{df['quarter'].min()}–{df['quarter'].max()}")
        save(build_kenuri(df), "shutoken_kenuri_quarterly.csv")
        save(build_condo(df), "metro3_used_condo_quarterly.csv")
        save(build_age_controlled(df), "tokyo23_condo_age_controlled.csv")
    if args.only != "xit001":
        save(build_l01(), "metro3_land_price_yoy_annual.csv")


if __name__ == "__main__":
    main()
