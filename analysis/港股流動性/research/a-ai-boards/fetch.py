"""抓 A 股 AI 相關概念板塊與傳統板塊的日成交額，算 AI 籃子佔全 A 成交額比例。

來源：東方財富 push2his kline API（板塊與指數日線）；板塊清單由 push2 clist API 取得。
全 A 成交額口徑：上證綜指 (1.000001) 額 + 深證成指 (0.399001) 額（依任務指定）。
另外附深證綜指 (0.399106) 額作為口徑敏感度檢查（欄位 a_turnover_alt）。

注意：requests 會被東財 TLS 握手擋住（連線逾時 / RemoteDisconnected），改用 curl_cffi impersonate。

用法：
    venv\\Scripts\\python.exe fetch.py                      # 2023-01-01 起全部
    venv\\Scripts\\python.exe fetch.py --start 2026-01-01   # 增量：只重抓該日起，合併進既有 CSV
    venv\\Scripts\\python.exe fetch.py --list               # 只列出全部概念板塊到 concepts_all.csv
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import time
from zoneinfo import ZoneInfo

from curl_cffi import requests as cr

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "ai_boards.csv")
LIST_CSV = os.path.join(HERE, "concepts_all.csv")
RAW_CACHE = os.path.join(HERE, "raw_cache.json")  # 原始 kline 快取，中斷後重跑可接續

# 板塊 secid = 90.BKxxxx；代號於 2026-10-23 由 clist (fs=m:90+t:3) 實查確認
BOARDS = {
    "ai_ai": ("BK0800", "人工智能"),
    "ai_cpo": ("BK1128", "CPO概念"),
    "ai_compute": ("BK1134", "算力概念"),
    "ai_optical_module": ("BK1136", "光通信模块"),
    "ai_liquid_cooling": ("BK1138", "液冷服务器"),
    "ai_adv_packaging": ("BK1101", "先进封装"),
    "ai_aigc": ("BK1111", "AIGC概念"),
    "ai_domestic_chip": ("BK0891", "国产芯片"),
    "ai_semicap": ("BK0884", "光刻机"),
    "ai_semi": ("BK0917", "半导体概念"),
    "ai_pc": ("BK1164", "AIPC"),
    "ai_phone": ("BK1162", "AI手机"),
    "ai_datacenter": ("BK0922", "数据中心"),
    "trad_construction_mach": ("BK0991", "工程机械概念"),
    "trad_chem_raw": ("BK0512", "化工原料"),
    "trad_retail": ("BK1655", "零售概念"),
    "trad_chinese_medicine": ("BK0615", "中药概念"),
}
# 籃子下限候選：人工智能 總板塊 + CPO + 算力，取當日最大者
FLOOR_SET = ["ai_ai", "ai_cpo", "ai_compute"]
# 上限：上述三者 + 光通信模块、液冷、先進封裝、AIGC、端側 AI（AIPC、AI手機）加總（有重疊，僅供上限參考）
CEIL_SET = FLOOR_SET + ["ai_optical_module", "ai_liquid_cooling", "ai_adv_packaging", "ai_aigc", "ai_pc", "ai_phone"]
INDEXES = {"sh": "1.000001", "sz_component": "0.399001", "sz_composite": "0.399106"}

COLUMNS = (
    ["date"]
    + list(BOARDS)
    + ["ai_share_low", "ai_share_high", "trad_share_mean", "a_turnover", "a_turnover_alt"]
)
HEADERS = {"Referer": "https://quote.eastmoney.com/"}
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
CLIST_URL = "https://82.push2.eastmoney.com/api/qt/clist/get"
MIN_GAP = 1.2  # 秒，請求間隔
CN_TZ = ZoneInfo("Asia/Shanghai")


def get_json(url, params, retries=6):
    """東財偶爾斷線（curl 56 / RemoteDisconnected），逐次退避重試。"""
    for i in range(retries):
        try:
            r = cr.get(url, params=params, headers=HEADERS, timeout=25, impersonate="chrome")
            r.raise_for_status()
            return r.json()
        except (cr.RequestsError, ValueError) as e:
            if i == retries - 1:
                raise
            print(f"[retry] {e}", file=sys.stderr, flush=True)
            time.sleep(2 ** i * 3)
        finally:
            time.sleep(MIN_GAP)


def load_cache():
    if os.path.exists(RAW_CACHE):
        with open(RAW_CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(RAW_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def fetch_turnover(secid, start, end, cache):
    """回傳 {date: 成交額(元)}。日線、不還原（板塊與指數無還原概念）。已快取的 secid 直接讀取。"""
    ckey = f"{secid}|{start}|{end}"
    if ckey in cache:
        print(f"[cache] {ckey}", flush=True)
        return cache[ckey]
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",  # 日期,開,收,高,低,量,額
        "klt": "101",
        "fqt": "0",
        "beg": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
    }
    payload = get_json(KLINE_URL, params)
    data = payload.get("data")
    if not data or not data.get("klines"):
        raise RuntimeError(f"{secid} 無資料 rc={payload.get('rc')}")
    amt = {}
    for line in data["klines"]:
        parts = line.split(",")
        amt[parts[0]] = float(parts[6])  # 第 7 欄 = 額
    print(f"[ok] {secid} {data.get('name')}: {len(amt)} 筆 {min(amt)} ~ {max(amt)}", flush=True)
    cache[ckey] = amt
    save_cache(cache)
    return amt


def list_concepts():
    """clist 分頁抓全部概念板塊（fs=m:90+t:3），每頁最多 100 筆。"""
    seen = {}
    for pn in range(1, 20):
        params = {
            "pn": pn, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
            "fid": "f3", "fs": "m:90+t:3", "fields": "f12,f14,f6",
        }
        diff = (get_json(CLIST_URL, params).get("data") or {}).get("diff") or []
        if not diff:
            break
        for x in diff:
            seen[x["f12"]] = x
    print(f"[ok] 概念板塊 {len(seen)} 個", flush=True)
    with open(LIST_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "turnover_yuan_today"])
        for code in sorted(seen):
            w.writerow([code, seen[code]["f14"], seen[code]["f6"]])
    return seen


def load_existing():
    if not os.path.exists(OUT_CSV):
        return {}
    rows = {}
    with open(OUT_CSV, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows[row["date"]] = row
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01", help="起始日 YYYY-MM-DD（增量時用）")
    ap.add_argument("--list", action="store_true", help="只列出概念板塊清單")
    args = ap.parse_args()
    if args.list:
        list_concepts()
        return

    start = dt.date.fromisoformat(args.start)
    # A 股 15:00 收盤；15:30 之後才視為當日已完整，否則丟掉盤中未完成的當日 K 線
    now_cn = dt.datetime.now(CN_TZ)
    end = now_cn.date() if now_cn.hour * 60 + now_cn.minute >= 15 * 60 + 30 else now_cn.date() - dt.timedelta(days=1)

    cache = load_cache()
    series = {}
    for key, (code, _name) in BOARDS.items():
        series[key] = fetch_turnover(f"90.{code}", start, end, cache)
    for key, secid in INDEXES.items():
        series[key] = fetch_turnover(secid, start, end, cache)

    fresh = {}
    all_dates = sorted(set().union(*[set(s) for s in series.values()]))
    for d in all_dates:
        row = {"date": d}
        for key in BOARDS:
            v = series[key].get(d)
            row[key] = "" if v is None else f"{v / 1e8:.4f}"  # 單位：億元
        floor = [series[k].get(d) for k in FLOOR_SET]
        ceil = [series[k].get(d) for k in CEIL_SET]
        a_tot = (series["sh"].get(d) or 0) + (series["sz_component"].get(d) or 0)
        a_alt = (series["sh"].get(d) or 0) + (series["sz_composite"].get(d) or 0)
        row["a_turnover"] = f"{a_tot / 1e8:.4f}" if a_tot else ""
        row["a_turnover_alt"] = f"{a_alt / 1e8:.4f}" if a_alt else ""
        # 下限 = 已有資料的板塊中最大者：缺值的板塊只會讓下限變保守，仍是真正的下限
        floor_avail = [v for v in floor if v is not None]
        if a_tot and floor_avail:
            row["ai_share_low"] = f"{max(floor_avail) / a_tot:.6f}"
        else:
            row["ai_share_low"] = ""
        # 上限 = 加總：缺任何一個成分就不是上限，留空
        if a_tot and all(v is not None for v in ceil):
            row["ai_share_high"] = f"{sum(ceil) / a_tot:.6f}"
        else:
            row["ai_share_high"] = ""
        # 傳統板塊：取當日已有資料的板塊平均佔比（零售概念 2026-03-16 才有資料）
        trad = [series[k].get(d) for k in BOARDS if k.startswith("trad_")]
        trad_avail = [v for v in trad if v is not None]
        row["trad_share_mean"] = f"{sum(trad_avail) / len(trad_avail) / a_tot:.6f}" if a_tot and trad_avail else ""
        fresh[d] = row

    merged = {d: r for d, r in load_existing().items() if d <= end.isoformat()}  # 舊檔可能殘留盤中列
    merged.update(fresh)  # 新抓的覆蓋重疊日

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for d in sorted(merged):
            w.writerow({c: merged[d].get(c, "") for c in COLUMNS})
    print(f"[done] {OUT_CSV}：共 {len(merged)} 列，最新 {max(merged)}", flush=True)


if __name__ == "__main__":
    main()
