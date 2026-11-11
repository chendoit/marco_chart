"""treasury-ops 抓取：TreasuryDirect 標售發行資料（auction_settlements.csv）。

用法：python fetch.py [--start 2023-01-01] [--end 2026-11-06]
原始回應快取於 raw/，重跑時優先使用快取。
"""
import argparse
import csv
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
UA = "Mozilla/5.0 (research data fetch; treasury-ops)"
TD_SEARCH = "https://www.treasurydirect.gov/TA_WS/securities/search"
PAGESIZE = 1000
SLEEP = 1.0  # 網路請求間隔（秒）


def get_bytes(url, cache_name):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, cache_name)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    time.sleep(SLEEP)
    return data


def month_windows(start, end):
    """回傳 [(起日, 迄日)] 月份區間，迄日為含當月最後一天或 end。"""
    out = []
    y, m = start.year, start.month
    while True:
        first = dt.date(y, m, 1)
        if first > end:
            break
        nm = dt.date(y + (m // 12), m % 12 + 1, 1)
        last = min(nm - dt.timedelta(days=1), end)
        out.append((max(first, start), last))
        y, m = nm.year, nm.month
    return out


def fetch_auctions(start, end):
    """依 issueDate 月份分段抓取（pagenum 參數會讓 API 回空陣列，故不分頁，改用月份切段）。
    單月筆數達 PAGESIZE 時直接報錯，避免靜默截斷。"""
    records = {}
    for a, b in month_windows(start, end):
        params = {
            "format": "json",
            "dateFieldName": "issueDate",
            "startDate": a.isoformat(),
            "endDate": b.isoformat(),
            "pagesize": PAGESIZE,
        }
        url = TD_SEARCH + "?" + urllib.parse.urlencode(params)
        cache = f"td_issue_{a:%Y%m}.json"
        rows = json.loads(get_bytes(url, cache).decode("utf-8"))
        if len(rows) >= PAGESIZE:
            raise RuntimeError(f"{a:%Y-%m} 筆數達 {PAGESIZE}，需再切細")
        for r in rows:
            key = (r.get("cusip"), r.get("issueDate"), r.get("securityType"), r.get("securityTerm"))
            records[key] = r
        print(f"{a:%Y-%m}: {len(rows)} rows")
    return list(records.values())


def to_bn(v):
    if v in (None, ""):
        return ""
    return f"{float(v) / 1e9:.3f}".rstrip("0").rstrip(".")


def write_auctions(rows, start, end, path):
    out = []
    for r in rows:
        issue = (r.get("issueDate") or "")[:10]
        if not issue or not (start.isoformat() <= issue <= end.isoformat()):
            continue
        auction = (r.get("competitiveAuctionCloseDate") or r.get("noncompetitiveAuctionCloseDate") or "")[:10]
        out.append({
            "date": issue,
            "auction_date": auction,
            "security_type": r.get("securityType", ""),
            "security_term": r.get("securityTerm", ""),
            "cusip": r.get("cusip", ""),
            "offering_amount_bn": to_bn(r.get("offeringAmount")),
        })
    out.sort(key=lambda x: (x["date"], x["cusip"], x["security_term"]))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "auction_date", "security_type", "security_term", "cusip", "offering_amount_bn"])
        w.writeheader()
        w.writerows(out)
    return out


FD_BB = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/buybacks_operations"
FD_BB_SEC = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/buybacks_security_details"


def fetch_buybacks(start):
    """Fiscal Data（Treasury Securities Buybacks）公開 API，不需金鑰。
    operation 表每列 = 一次操作 × 年期區間；security details 表僅供核對，不進 CSV。"""
    q = f"?filter=operation_date:gte:{start.isoformat()}&page%5Bsize%5D=10000&sort=operation_date"
    ops = json.loads(get_bytes(FD_BB + q, f"fd_buybacks_operations_from_{start:%Y%m%d}.json").decode("utf-8"))
    sec = json.loads(get_bytes(FD_BB_SEC + q, f"fd_buybacks_security_details_from_{start:%Y%m%d}.json").decode("utf-8"))
    for name, obj in (("operations", ops), ("security_details", sec)):
        if obj.get("meta", {}).get("total-pages", 1) != 1:
            raise RuntimeError(f"{name} 分頁超過一頁，需改抓法")
    return ops["data"], sec["data"]


def bn_or_blank(v):
    if v in (None, "", "null"):
        return ""
    return to_bn(v)


def write_buybacks(ops, path):
    """主鍵 (date, bucket)。同一天同一年期區間若有兩筆操作：保留有成交結果（accepted 非空）者，
    另一筆視為未舉行（no results）並列印。兩筆都有結果時報錯。"""
    by_key = {}
    dropped = []
    for r in ops:
        key = (r["operation_date"], r["maturity_bucket"])
        if key in by_key:
            prev = by_key[key]
            pa = bn_or_blank(prev["total_par_amt_accepted"])
            ca = bn_or_blank(r["total_par_amt_accepted"])
            if pa and ca:
                raise RuntimeError(f"{key} 兩筆皆有結果，需人工判斷")
            if ca and not pa:
                dropped.append(prev)
                by_key[key] = r
            else:
                dropped.append(r)
            continue
        by_key[key] = r
    out = []
    for (date, bucket), r in sorted(by_key.items()):
        out.append({
            "date": date,
            "settle_date": r["settlement_date"],
            "bucket": bucket,
            "par_submitted_bn": bn_or_blank(r["total_par_amt_offered"]),
            "par_accepted_bn": bn_or_blank(r["total_par_amt_accepted"]),
        })
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "settle_date", "bucket", "par_submitted_bn", "par_accepted_bn"])
        w.writeheader()
        w.writerows(out)
    for r in dropped:
        print(f"排除同鍵未舉行紀錄：{r['operation_date']} {r['maturity_bucket']} {r['operation_start_time_est']} "
              f"offered={r['total_par_amt_offered']} accepted={r['total_par_amt_accepted']}")
    return out, dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2023-01-01", help="auction_settlements 起日")
    ap.add_argument("--end", default="2026-11-06")
    ap.add_argument("--bb-start", default="2024-05-01", help="buybacks 起日")
    args = ap.parse_args()
    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    rows = fetch_auctions(start, end)
    out = write_auctions(rows, start, end, os.path.join(HERE, "auction_settlements.csv"))
    print(f"auction_settlements.csv: {len(out)} rows")
    ops, _sec = fetch_buybacks(dt.date.fromisoformat(args.bb_start))
    bb, dropped = write_buybacks(ops, os.path.join(HERE, "treasury_buybacks.csv"))
    print(f"treasury_buybacks.csv: {len(bb)} rows（原始 operations {len(ops)} 列，排除未舉行 {len(dropped)} 列）")


if __name__ == "__main__":
    main()
