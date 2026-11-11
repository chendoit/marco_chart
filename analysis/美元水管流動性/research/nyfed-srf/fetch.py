"""nyfed-srf 資料抓取（可重跑）。

來源：
- 紐約 Fed Markets API：repo 操作結果（`/api/rp/repo/all/results/last/N.json`，N 上限實測 999）。
  SRF 篩選條件：operationType == "Repo"（此 feed 內的操作皆為 standing repo／SRF 操作，含 Term 與 SVE 小額測試）。
- FRED（fredgraph.csv，無需金鑰）：
  - RPTTLD：Repurchase Agreements: Total Securities Purchased by the Fed in Temporary OMO（總量，十億美元）
  - RPONTTLD：Overnight 部分；RPONTSYD／RPONAGYD／RPONMBSD：Overnight 依擔保品（十億美元）
  - DFEDTARU：聯邦資金利率目標區間上限
  用途：NY Fed API 只回傳最近 N 筆操作（實測約 2024-04 起），更早的 SRF 用量改用 FRED，
  只填 accepted 系列；FRED 沒有的欄位（ops_count、submitted、min_bid_rate）留空。

用法：
  PYTHONUTF8=1 python -I fetch.py [--start 2021-07-28] [--end 2026-11-06] [--offline]
  --offline：不連網，改讀 raw/ 內既有快取。
"""
import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
UA = "nyfed-srf-research-fetch/1.0"
TIMEOUT = 60
SLEEP = 1.0
NYFED_TEMPLATE = "https://markets.newyorkfed.org/api/rp/repo/all/results/last/{n}.json"
NYFED_SIZES = [999, 950, 900, 800]
FRED_TEMPLATE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2018-01-01"
FRED_IDS = ["RPTTLD", "RPONTTLD", "RPONTSYD", "RPONAGYD", "RPONMBSD", "DFEDTARU"]
RATE_START = "2018-01-02"
RATE_END_DEFAULT = "2026-11-06"


def http_get(url, tries=3):
    last_err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code in (400, 404):  # 參數不被接受，重試無用
                break
        except Exception as e:  # noqa: BLE001
            last_err = repr(e)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"抓取失敗 {url}: {last_err}")


def fetch_nyfed(offline):
    path = os.path.join(RAW, "nyfed_repo_results.json")
    if offline:
        with open(path, "rb") as f:
            return json.load(f), "offline-cache"
    last_err = None
    for n in NYFED_SIZES:
        url = NYFED_TEMPLATE.format(n=n)
        try:
            _, body = http_get(url)
        except RuntimeError as e:
            last_err = e
            time.sleep(SLEEP)
            continue
        os.makedirs(RAW, exist_ok=True)
        with open(path, "wb") as f:
            f.write(body)
        with open(os.path.join(RAW, "nyfed_repo_results.url.txt"), "w", encoding="utf-8") as f:
            f.write(url + "\n")
        return json.loads(body.decode("utf-8")), url
    raise RuntimeError(f"NY Fed API 全部嘗試失敗：{last_err}")


def fetch_fred(offline):
    out = {}
    os.makedirs(RAW, exist_ok=True)
    for sid in FRED_IDS:
        path = os.path.join(RAW, f"fred_{sid}.csv")
        if offline:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            _, body = http_get(FRED_TEMPLATE.format(sid=sid))
            text = body.decode("utf-8")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(text)
            time.sleep(SLEEP)
        rows = {}
        for r in csv.reader(text.splitlines()):
            if len(r) >= 2 and len(r[0]) == 10 and r[0][:2] == "20":
                rows[r[0]] = r[1].strip()  # 空字串 = FRED 無觀測值（假日）
        out[sid] = rows
    return out


def dec_bn(dollars):
    """美元整數 → 十億美元字串（不留尾隨 0）。"""
    d = Decimal(dollars) / Decimal(10**9)
    return format(d.normalize(), "f")


def dec_str(s):
    """FRED 字串（十億或利率）→ 去尾隨 0 的字串；空字串維持空。"""
    if s is None or s == "":
        return ""
    return format(Decimal(s).normalize(), "f")


def op_rate(op):
    """單一操作的最低投標利率：有 minimumBidRate 用它，固定利率（Full Allotment）用 percentOfferingRate。
    3 筆只有 percentHighRate／percentLowRate、沒有上述欄位的操作不計入（見報告）。"""
    vals = []
    for x in op.get("details", []):
        for f in ("minimumBidRate", "percentOfferingRate"):
            if x.get(f) is not None:
                vals.append(Decimal(str(x[f])))
    return max(vals) if vals else None


def build(args):
    nyfed, nyfed_url = fetch_nyfed(args.offline)
    fred = fetch_fred(args.offline)

    ops_all = nyfed["repo"]["operations"]
    ops = [o for o in ops_all if o.get("operationType") == "Repo" and o.get("auctionStatus") == "Results"]
    excluded_not_repo = sum(1 for o in ops_all if o.get("operationType") != "Repo")
    excluded_status = sum(1 for o in ops_all if o.get("operationType") == "Repo" and o.get("auctionStatus") != "Results")
    api_first = min(o["operationDate"] for o in ops_all)
    api_last = max(o["operationDate"] for o in ops_all)
    sve_ops = sum(1 for o in ops if "Small Value Exercise" in (o.get("note") or "") or "small value" in (o.get("note") or "").lower())
    srf_note_ops = sum(1 for o in ops if "SRF" in (o.get("note") or ""))

    # 依日彙總 API 操作
    agg = {}
    for o in ops:
        d = o["operationDate"]
        a = agg.setdefault(d, {"ops": 0, "sub": 0, "acc": 0, "tsy": 0, "agy": 0, "mbs": 0, "rates": [], "terms": set()})
        a["ops"] += 1
        a["sub"] += int(o["totalAmtSubmitted"])
        a["acc"] += int(o["totalAmtAccepted"])
        a["terms"].add(o.get("term"))
        for x in o["details"]:
            st = x["securityType"]
            amt = int(x["amtAccepted"])
            if st == "Treasury":
                a["tsy"] += amt
            elif st == "Agency":
                a["agy"] += amt
            elif st == "Mortgage-Backed":
                a["mbs"] += amt
            else:
                raise RuntimeError(f"未知擔保品類別 {st}")
        r = op_rate(o)
        if r is not None:
            a["rates"].append(r)

    # API 窗口：最早日期可能只含部分操作，故 API 只用於嚴格大於最早日期者；最早日期及之前改用 FRED
    api_cut = api_first
    usage = []
    for d in sorted(agg):
        if d <= api_cut or d < args.start or d > args.end:
            continue
        a = agg[d]
        usage.append({
            "date": d,
            "ops_count": str(a["ops"]),
            "submitted_bn": dec_bn(a["sub"]),
            "accepted_bn": dec_bn(a["acc"]),
            "accepted_treasury_bn": dec_bn(a["tsy"]),
            "accepted_agency_bn": dec_bn(a["agy"]),
            "accepted_mbs_bn": dec_bn(a["mbs"]),
            "min_bid_rate": format(max(a["rates"]).normalize(), "f") if a["rates"] else "",
            "_src": "nyfed_api",
        })

    # FRED 補齊 api_cut（含）之前的 SRF 用量（僅 accepted 系列）
    tot, tsy, agy, mbs = fred["RPTTLD"], fred["RPONTSYD"], fred["RPONAGYD"], fred["RPONMBSD"]
    ovn = fred["RPONTTLD"]
    fred_rows = []
    for d in sorted(tot):
        if d > api_cut or d < args.start or d > args.end:
            continue
        if tot[d] == "":
            continue  # FRED 無觀測值（假日），不補
        fred_rows.append({
            "date": d,
            "ops_count": "",
            "submitted_bn": "",
            "accepted_bn": dec_str(tot[d]),
            "accepted_treasury_bn": dec_str(tsy.get(d, "")),
            "accepted_agency_bn": dec_str(agy.get(d, "")),
            "accepted_mbs_bn": dec_str(mbs.get(d, "")),
            "min_bid_rate": "",
            "_src": "fred_RPTTLD",
        })
    all_usage = sorted(fred_rows + usage, key=lambda r: r["date"])

    # 驗證 FRED 總量與 API 總量在重疊期是否一致（僅統計，不改值）
    cmp_ok = cmp_bad = 0
    cmp_detail = []
    for r in usage:
        d = r["date"]
        if d in tot and tot[d] != "":
            diff = abs(Decimal(tot[d]) - Decimal(r["accepted_bn"]))
            if diff < Decimal("0.0005"):
                cmp_ok += 1
            else:
                cmp_bad += 1
                cmp_detail.append((d, tot[d], r["accepted_bn"]))

    # 利率表：DFEDTARU 每個有值的日曆日一列
    srf_min_map = {r["date"]: r["min_bid_rate"] for r in usage if r["min_bid_rate"] != ""}
    rate_rows = []
    blanks_target = 0
    for d in sorted(fred["DFEDTARU"]):
        if d < RATE_START or d > args.end:
            continue
        v = fred["DFEDTARU"][d]
        if v == "":
            blanks_target += 1
            continue
        rate_rows.append({
            "date": d,
            "target_upper": dec_str(v),
            "srf_min_bid_rate": srf_min_map.get(d, ""),
        })

    # 寫出 CSV
    usage_cols = ["date", "ops_count", "submitted_bn", "accepted_bn", "accepted_treasury_bn",
                  "accepted_agency_bn", "accepted_mbs_bn", "min_bid_rate"]
    with open(os.path.join(HERE, "srf_usage.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(usage_cols)
        for r in all_usage:
            w.writerow([r[c] for c in usage_cols])
    rate_cols = ["date", "target_upper", "srf_min_bid_rate"]
    with open(os.path.join(HERE, "srf_rate.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(rate_cols)
        for r in rate_rows:
            w.writerow([r[c] for c in rate_cols])

    # 摘要（給報告用）
    n_fred = len(fred_rows)
    n_api = len(usage)
    print(f"NY Fed 來源：{nyfed_url}")
    print(f"API 操作總筆數 {len(ops_all)}；日期範圍 {api_first} ~ {api_last}；"
          f"非 Repo 排除 {excluded_not_repo}；非 Results 排除 {excluded_status}")
    print(f"SVE 小額測試操作 {sve_ops} 筆；備註含 SRF 字樣 {srf_note_ops} 筆；"
          f"無最低投標利率欄位的操作 {sum(1 for o in ops if op_rate(o) is None)} 筆")
    print(f"srf_usage 列數 {len(all_usage)}（FRED 段 {n_fred}，API 段 {n_api}）；"
          f"起訖 {all_usage[0]['date']} ~ {all_usage[-1]['date']}")
    print(f"API 段切點（最早 API 日期，不含）：{api_cut}")
    print(f"重疊比對（FRED RPTTLD vs API 總量，同一日）：一致 {cmp_ok}，不一致 {cmp_bad} {cmp_detail[:5]}")
    print(f"srf_rate 列數 {len(rate_rows)}；起訖 {rate_rows[0]['date']} ~ {rate_rows[-1]['date']}；"
          f"DFEDTARU 空值略過 {blanks_target}；srf_min_bid_rate 有值列數 "
          f"{sum(1 for r in rate_rows if r['srf_min_bid_rate'] != '')}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2021-07-28", help="SRF 用量起始日（SRF 首次操作日）")
    p.add_argument("--end", default="2026-11-06", help="資料截止日")
    p.add_argument("--offline", action="store_true", help="只用 raw/ 既有快取，不連網")
    args = p.parse_args()
    build(args)


if __name__ == "__main__":
    sys.exit(main())
