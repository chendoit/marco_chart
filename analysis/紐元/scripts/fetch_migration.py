#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
一次性抓取「紐西蘭國際移民淨流量」歷史資料 -> data/nz_migration.csv

輸出三條序列：
  1. net_total        全體淨移民 (all citizenships)
  2. net_nz_citizens  紐西蘭公民淨移民（長期為負 = 人才外流）
  3. net_non_nz       非紐西蘭公民淨移民

================================================================================
來源
================================================================================
Stats NZ《International migration》月度發佈（provisional estimates）。
本次取用最新一期「July 2026」發佈頁面（發佈日 2026-09-14）：

  發佈頁面（主要來源）
    https://www.stats.govt.nz/information-releases/international-migration-july-2026/

  發佈頁面「Download data」區塊的原始檔案（同一份資料，備用來源）：
    xlsx
    https://www.stats.govt.nz/assets/Uploads/International-migration/International-migration-July-2026/Download-data/international-migration-july-2026.xlsx
    csv（年齡/性別）
    https://www.stats.govt.nz/assets/Uploads/International-migration/International-migration-July-2026/Download-data/international-migration-july-2026-estimated-migration-by-age-and-sex.csv
    csv（國籍/簽證/前永久居留國）
    https://www.stats.govt.nz/assets/Uploads/International-migration/International-migration-July-2026/Download-data/international-migration-july-2026-citizenship-by-visa-by-country-of-last-permanent-residence.csv

實作說明
  www.stats.govt.nz 前置 Incapsula 機器人防護，資產檔（xlsx/csv）常被攔截；
  但發佈頁面 HTML 本身可取得，且頁面內以 JSON 內嵌每張圖表的完整 CSV
  （SeriesData[].GraphCsvData）。本腳本直接解析這些內嵌 CSV，資料與官方
  下載檔完全一致。取得失敗時會自動改用 r.jina.ai 純文字代理。

取用的兩張圖表
  - "Estimated migration by direction, rolling year ended December 2001–July 2026"
        -> 資料列 "Net migration"                          => net_total
  - "Estimated migration by citizenship, rolling year ended December 2001–July 2026"
        -> 資料列 "Net migration (NZ citizens)"            => net_nz_citizens
        -> 資料列 "Net migration (non-NZ citizens)"        => net_non_nz

================================================================================
關於資料頻率（重要）
================================================================================
Stats NZ 的 outcomes-based provisional 遷移估計，對外主體格式是
「rolling year ended <月份>」的 12 個月滾動值。發佈頁面雖另有一張
「Estimated net migration, monthly, January 2001–July 2026」的單月表，
但該表「並未依國籍拆分」，因此無法同時滿足「月頻」與「三條序列」兩項需求。
故本檔採官方 12 個月滾動值，source 欄標記 rolling12。
date 欄 = 該滾動年度的結束月份，格式 YYYY-MM-01，由舊到新排序。

================================================================================
用法
================================================================================
  python scripts/fetch_migration.py
"""

import csv
import io
import json
import os
import re
import sys
import time

import pandas as pd
import requests

TIMEOUT = 60  # seconds

RELEASE_SLUG = "international-migration-july-2026"
RELEASE_URL = f"https://www.stats.govt.nz/information-releases/{RELEASE_SLUG}/"

# 先直連；被 Incapsula 擋下時改用純文字代理（僅能取得 HTML/文字內容）
CONTENT_ENDPOINTS = [
    RELEASE_URL,
    f"https://r.jina.ai/{RELEASE_URL}",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
}

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.normpath(os.path.join(HERE, "..", "data", "nz_migration.csv"))

MONTH_ABBR = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


# --------------------------------------------------------------------------- #
# 1. 抓取
# --------------------------------------------------------------------------- #
def fetch_page() -> str:
    """取得發佈頁面 HTML 內容。"""
    errs = []
    for url in CONTENT_ENDPOINTS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            text = r.text
            if "_Incapsula_Resource" in text or "Request unsuccessful" in text:
                raise RuntimeError("被 Incapsula 防護攔截")
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")
            print(f"[fetch] OK   {url}  ({len(text):,} chars)")
            return text
        except Exception as e:  # noqa: BLE001
            errs.append(f"{url} -> {e}")
            print(f"[fetch] FAIL {url} -> {e}")
            time.sleep(2)
    raise SystemExit("無法取得 Stats NZ 發佈頁面：\n  " + "\n  ".join(errs))


# --------------------------------------------------------------------------- #
# 2. 解析頁面內嵌的 GraphCsvData
# --------------------------------------------------------------------------- #
def _scan_json_string(s: str, start: int):
    """s[start] 應為 '"'。回傳 (內容, 結束引號之後的索引)。處理跳脫字元。"""
    assert s[start] == '"'
    i = start + 1
    buf = []
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            buf.append(s[i:i + 2])  # 保留跳脫，交由 json 解析
            i += 2
            continue
        if c == '"':
            return "".join(buf), i + 1
        buf.append(c)
        i += 1
    raise ValueError("JSON 字串未正常結尾")


def extract_graph_csvs(html_text: str):
    """回傳 {chart_title: DataFrame}。每張圖表的 CSV 為『首列日期、每列一條序列』。"""
    # 頁面內容本身是 HTML-entity 編碼的 JSON；先解碼實體
    import html as html_mod
    text = html_mod.unescape(html_text)

    out = {}
    for m in re.finditer(
        r'"Title":"((?:[^"\\]|\\.)*)","ClassName":"SeriesGroup"', text
    ):
        try:
            title = json.loads('"' + m.group(1) + '"')
        except Exception:  # noqa: BLE001
            continue

        j = text.find('"GraphCsvData":', m.end())
        if j == -1 or j - m.end() > 2000:
            continue
        q = text.index('"', j + len('"GraphCsvData":'))
        try:
            raw, _ = _scan_json_string(text, q)
            csv_text = json.loads('"' + raw + '"')
        except Exception:  # noqa: BLE001
            continue

        rows = list(csv.reader(io.StringIO(csv_text.lstrip("\ufeff"))))
        rows = [r for r in rows if any(c.strip() for c in r)]
        if len(rows) < 2 or len(rows[0]) < 3:
            continue

        dates = rows[0][1:]
        data = {r[0].strip(): r[1:] for r in rows[1:] if r}
        width = min([len(dates)] + [len(v) for v in data.values()])
        out[title] = pd.DataFrame(
            {name: vals[:width] for name, vals in data.items()},
            index=pd.Index(dates[:width], name="period"),
        )
    return out


# --------------------------------------------------------------------------- #
# 3. 轉換
# --------------------------------------------------------------------------- #
def to_date(label: str):
    """'Dec-2001' / 'Dec 2001' -> Timestamp('2001-12-01')"""
    m = re.match(r"([A-Za-z]{3})\s*[-\s]\s*(\d{4})", str(label).strip())
    if not m:
        return None
    mon = MONTH_ABBR.get(m.group(1).lower())
    if not mon:
        return None
    return pd.Timestamp(year=int(m.group(2)), month=mon, day=1)


def pick(frames, title_sub: str, series: str):
    for title, df in frames.items():
        if title_sub.lower() in title.lower():
            for name in df.columns:
                if name.strip().lower() == series.lower():
                    return df[name]
    return None


def main():
    page = fetch_page()
    frames = extract_graph_csvs(page)
    print(f"[parse] 抓到 {len(frames)} 張內嵌圖表：")
    for t in frames:
        print("         -", t[:88])

    s_total = pick(frames, "migration by direction, rolling", "Net migration")
    s_nz = pick(frames, "migration by citizenship, rolling", "Net migration (NZ citizens)")
    s_non = pick(frames, "migration by citizenship, rolling", "Net migration (non-NZ citizens)")

    missing = [n for n, s in [("net_total", s_total), ("net_nz_citizens", s_nz),
                              ("net_non_nz", s_non)] if s is None]
    if missing:
        raise SystemExit(f"找不到必要序列：{missing}（頁面結構可能已變更）")

    out = pd.DataFrame({
        "date": [to_date(p) for p in s_total.index],
        "net_total": pd.to_numeric(s_total.values, errors="coerce"),
    })
    nz_map = {to_date(p): v for p, v in zip(s_nz.index, s_nz.values)}
    non_map = {to_date(p): v for p, v in zip(s_non.index, s_non.values)}
    out["net_nz_citizens"] = out["date"].map(
        lambda d: pd.to_numeric(nz_map.get(d), errors="coerce"))
    out["net_non_nz"] = out["date"].map(
        lambda d: pd.to_numeric(non_map.get(d), errors="coerce"))
    out["source"] = "rolling12"

    out = out.dropna(subset=["date"]).drop_duplicates("date", keep="last")
    out = out.sort_values("date").reset_index(drop=True)
    for c in ("net_total", "net_nz_citizens", "net_non_nz"):
        out[c] = out[c].round().astype("Int64")

    # 健全性檢查：net_total 應約等於 NZ citizens + non-NZ citizens
    chk = out.dropna(subset=["net_nz_citizens", "net_non_nz"])
    diff = (chk["net_total"] - (chk["net_nz_citizens"] + chk["net_non_nz"])).abs()
    print(f"[check] 國籍加總 vs 總數：最大差異 {int(diff.max())} 人"
          f"（|差異|>1 的筆數 {int((diff > 1).sum())}）")

    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8")

    print(f"[out] {OUT_CSV}  rows={len(out)}")
    print(out.tail(3).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
