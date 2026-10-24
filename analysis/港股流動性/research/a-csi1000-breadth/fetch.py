"""抓中證1000（000852）成分股日 K、個股所屬行業與 AI 相關概念成員，寫入 cache/。

來源：
- 成分股清單：中證指數官網 Excel（oss-ch.csindex.com.cn），存 raw/。
- 日 K：東方財富 push2his kline（個股 fqt=1 前復權，指數 fqt=0），從 2024-06-01 起。
- 行業：東方財富 push2 stock/get 的 f127（行業名）。
- AI 概念成員：東方財富 push2 clist，概念板塊依名稱關鍵字篩出後逐板塊抓成員。

分批：每次執行最多跑 --max-seconds 秒（預設 540），已快取的股票直接跳過，
未完成就再跑一次，直到輸出 "[done]"。

用法：
    venv\\Scripts\\python.exe fetch.py                    # 跑到時限或全部完成
    venv\\Scripts\\python.exe fetch.py --max-seconds 540
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW_XLS = os.path.join(HERE, "raw", "000852cons.xls")
CACHE = os.path.join(HERE, "cache")
CONS_URL = "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/000852cons.xls"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
QUOTE_URL = "https://push2.eastmoney.com/api/qt/stock/get"
CLIST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
START = "20240601"
INTERVAL = 1.0  # 秒；東財請求間隔（連線被斷時加大）
WORKERS = 1  # 併發數；節流由 throttle() 保證全域請求起始間隔
_lock = threading.Lock()
_last = [0.0]


def throttle():
    """全域請求起始間隔至少 INTERVAL 秒（多執行緒共用）。"""
    with _lock:
        wait = _last[0] + INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()

# 概念板塊名稱關鍵字（大小寫不敏感，子字串比對）；比對結果會列印出來供 report 引用
AI_KEYWORDS = ["算力", "CPO", "光模块", "光模组", "液冷", "先进封装", "半导体", "人工智能", "AI",
               "芯片", "服务器", "数据中心", "光通信", "大模型", "昇腾", "HBM", "存储芯片", "国产芯片"]


def get_json(url, params, retries=4):
    """東財偶爾斷線或超時，逐次退避重試。"""
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if i == retries - 1:
                raise
            print(f"[retry] {e}", file=sys.stderr, flush=True)
            time.sleep(2 ** i * 2)


def secid_of(code):
    return ("1." if code.startswith("6") else "0.") + code


def load_constituents():
    if not os.path.exists(RAW_XLS):
        os.makedirs(os.path.dirname(RAW_XLS), exist_ok=True)
        r = requests.get(CONS_URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        with open(RAW_XLS, "wb") as f:
            f.write(r.content)
    d = pd.read_excel(RAW_XLS, dtype=str)
    d = d.rename(columns={"成份券代码Constituent Code": "code", "成份券名称Constituent Name": "name"})
    return d[["code", "name"]].drop_duplicates("code").reset_index(drop=True)


def fetch_kline_file(secid, path, fqt):
    """抓一檔日 K 存成 csv；欄位：date,open,close,high,low,vol,amount。"""
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",
        "klt": "101",
        "fqt": str(fqt),
        "beg": START,
        "end": "20991231",
    }
    payload = get_json(KLINE_URL, params)
    data = payload.get("data") or {}
    rows = [line.split(",") for line in data.get("klines") or []]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "close", "high", "low", "vol", "amount"])
        for p in rows:
            w.writerow([p[0], p[1], p[2], p[3], p[4], p[5], p[6]])
    return len(rows)


def fetch_industry(code):
    path = os.path.join(CACHE, "meta", f"{code}.json")
    if os.path.exists(path):
        return
    payload = get_json(QUOTE_URL, {"secid": secid_of(code), "fields": "f57,f58,f127"})
    data = payload.get("data") or {}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"code": code, "industry": data.get("f127") or ""}, f, ensure_ascii=False)


def fetch_ai_concept_members():
    """找出 AI 相關概念板塊，抓成員清單，存 cache/ai_concepts.json。"""
    path = os.path.join(CACHE, "ai_concepts.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    diff = []
    for pn in range(1, 20):  # 板塊清單分頁（單頁最多 100 筆）
        page = get_json(CLIST_URL, {"pn": pn, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                                    "fid": "f3", "fs": "m:90+t:3", "fields": "f12,f14"})
        items = (page.get("data") or {}).get("diff") or []
        diff.extend(items)
        if len(items) < 100:
            break
        time.sleep(INTERVAL)
    matched = [b for b in diff if any(k.lower() in b["f14"].lower() for k in AI_KEYWORDS)]
    print(f"[concept] 概念板塊共 {len(diff)}，AI 關鍵字命中 {len(matched)}：" +
          "、".join(b["f14"] for b in matched), flush=True)
    os.makedirs(os.path.join(CACHE, "concepts"), exist_ok=True)
    result, complete = {}, True
    for b in matched:
        bpath = os.path.join(CACHE, "concepts", f"{b['f12']}.json")
        if os.path.exists(bpath):  # 板塊成員已快取
            with open(bpath, encoding="utf-8") as f:
                result[b["f14"]] = json.load(f)
            continue
        try:
            members = []
            for pn in range(1, 50):  # 成員清單分頁（單頁最多 100 筆）
                time.sleep(INTERVAL)
                payload = get_json(CLIST_URL, {"pn": pn, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                                               "fid": "f3", "fs": f"b:{b['f12']}", "fields": "f12,f14"})
                items = (payload.get("data") or {}).get("diff") or []
                members.extend(m["f12"] for m in items)
                if len(items) < 100:
                    break
        except Exception as e:  # noqa: BLE001
            complete = False
            print(f"[fail-concept] {b['f14']} ({b['f12']}): {e}", file=sys.stderr, flush=True)
            continue
        with open(bpath, "w", encoding="utf-8") as f:
            json.dump(members, f, ensure_ascii=False)
        result[b["f14"]] = members
        print(f"[concept] {b['f14']} ({b['f12']}): {len(members)} 檔", flush=True)
    if complete:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-seconds", type=float, default=540, help="本次執行時限（秒）")
    args = ap.parse_args()
    t0 = time.time()
    os.makedirs(os.path.join(CACHE, "kline"), exist_ok=True)
    os.makedirs(os.path.join(CACHE, "meta"), exist_ok=True)

    cons = load_constituents()
    print(f"[cons] 成分股 {len(cons)} 檔", flush=True)

    idx_path = os.path.join(CACHE, "index_000852.csv")
    if not os.path.exists(idx_path):
        fetch_kline_file("1.000852", idx_path, fqt=0)
        time.sleep(INTERVAL)


    pending = [c for c in cons["code"] if not os.path.exists(os.path.join(CACHE, "kline", f"{c}.csv"))]
    print(f"[plan] 尚缺日 K {len(pending)} 檔", flush=True)
    fails = []

    def work(code):
        if time.time() - t0 > args.max_seconds:
            return
        try:
            throttle()
            n = fetch_kline_file(secid_of(code), os.path.join(CACHE, "kline", f"{code}.csv"), fqt=1)
            throttle()
            fetch_industry(code)
        except Exception as e:  # noqa: BLE001
            fails.append(code)
            print(f"[fail] {code}: {e}", file=sys.stderr, flush=True)
            return
        print(f"[ok] {code} {n} 筆", flush=True)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, pending))

    # 行業：日 K 已抓但行業缺的補抓（上一輪可能中斷）
    for code in cons["code"]:
        if time.time() - t0 > args.max_seconds:
            break
        if os.path.exists(os.path.join(CACHE, "kline", f"{code}.csv")) and \
                not os.path.exists(os.path.join(CACHE, "meta", f"{code}.json")):
            try:
                fetch_industry(code)
            except Exception as e:  # noqa: BLE001
                print(f"[fail-meta] {code}: {e}", file=sys.stderr, flush=True)
            time.sleep(INTERVAL)

    # 概念成員放在日 K 之後，東財 clist 偶發 502 時不擋住日 K 進度
    concepts = {}
    if time.time() - t0 <= args.max_seconds:
        try:
            concepts = fetch_ai_concept_members()
        except Exception as e:  # noqa: BLE001
            print(f"[fail-concept-list] {e}", file=sys.stderr, flush=True)

    left = [c for c in cons["code"] if not os.path.exists(os.path.join(CACHE, "kline", f"{c}.csv"))
            or not os.path.exists(os.path.join(CACHE, "meta", f"{c}.json"))]
    print(f"[status] 本次耗時 {time.time() - t0:.0f} 秒；失敗 {len(fails)}；尚未完成 {len(left)}", flush=True)
    if not left and os.path.exists(os.path.join(CACHE, "ai_concepts.json")):
        print(f"[done] 快取完成；AI 概念板塊 {len(concepts)} 個", flush=True)


if __name__ == "__main__":
    main()
