"""抓 CFTC Traders in Financial Futures（TFF）Futures Only 美債期貨週資料。

來源：CFTC Public Reporting（Socrata）資料集 gpe5-46if（TFF Futures Only）。
用法：
    PYTHONUTF8=1 venv\\Scripts\\python.exe fetch.py [--start 2006-01-01]

輸出：
    cftc_treasury_tff.csv   長表，主鍵 (contract, date)
    raw/{code}.json         各合約來源原始回應快取（每次執行覆寫）
"""
import argparse
import csv
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "cftc_treasury_tff.csv")
BASE = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
UA = "research-fetch/1.0"
TIMEOUT = 60
PAUSE = 1.0

# contract 欄照 prompt 寫；code 為 CFTC cftc_contract_market_code
CONTRACTS = [
    ("2Y", "042601"),
    ("5Y", "044601"),
    ("10Y", "043602"),
    ("ULTRA10Y", "043607"),
    ("TBOND", "020601"),
    ("ULTRABOND", "020604"),
]

# 來源欄位 -> 輸出欄位
FIELD_MAP = {
    "open_interest": "open_interest_all",
    "lev_long": "lev_money_positions_long",
    "lev_short": "lev_money_positions_short",
    "asset_mgr_long": "asset_mgr_positions_long",
    "asset_mgr_short": "asset_mgr_positions_short",
    "dealer_long": "dealer_positions_long_all",
    "dealer_short": "dealer_positions_short_all",
}
OUT_COLS = ["date", "contract", "open_interest", "lev_long", "lev_short", "lev_net",
            "asset_mgr_long", "asset_mgr_short", "dealer_long", "dealer_short"]


def get_json(params, retries=3):
    url = BASE + "?" + urllib.parse.urlencode(params, safe="$'=,")
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001 - 重試後再拋出
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"請求失敗：{url}：{last}")


def fetch_contract(code, start):
    params = {
        "$where": f"cftc_contract_market_code='{code}' AND futonly_or_combined='FutOnly' "
                  f"AND report_date_as_yyyy_mm_dd >= '{start}T00:00:00.000'",
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "50000",
    }
    text = get_json(params)
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, f"{code}.json"), "w", encoding="utf-8") as f:
        f.write(text)
    return json.loads(text)


def to_int(v):
    if v is None or v == "":
        return None
    return int(round(float(v)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2006-01-01", help="報告日下限（含），預設為此資料集可得的最早日期附近")
    args = ap.parse_args()

    rows = []
    for i, (contract, code) in enumerate(CONTRACTS):
        if i:
            time.sleep(PAUSE)
        recs = fetch_contract(code, args.start)
        if not recs:
            raise RuntimeError(f"{contract}（{code}）無資料")
        names = {r.get("contract_market_name") for r in recs}
        print(f"{contract} {code}: {len(recs)} 筆，商品名稱 {sorted(names)}，"
              f"{recs[0]['report_date_as_yyyy_mm_dd'][:10]} ~ {recs[-1]['report_date_as_yyyy_mm_dd'][:10]}")
        for r in recs:
            if r.get("futonly_or_combined") != "FutOnly":
                raise RuntimeError(f"{contract} 出現非 FutOnly 列：{r.get('futonly_or_combined')}")
            rec = {"date": r["report_date_as_yyyy_mm_dd"][:10], "contract": contract}
            for out_col, src_col in FIELD_MAP.items():
                rec[out_col] = to_int(r.get(src_col))
            if rec["lev_long"] is None or rec["lev_short"] is None:
                rec["lev_net"] = None
            else:
                rec["lev_net"] = rec["lev_long"] - rec["lev_short"]
            rows.append(rec)

    # 依 contract（字串升冪）再依 date 升冪；與 verify.py 的 sort_values([contract, date]) 一致
    rows.sort(key=lambda x: (x["contract"], x["date"]))
    keys = [(x["contract"], x["date"]) for x in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("主鍵 (contract, date) 重複")

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(OUT_COLS)
        for x in rows:
            w.writerow(["" if x[c] is None else x[c] for c in OUT_COLS])
    print(f"寫入 {OUT}：{len(rows)} 列")


if __name__ == "__main__":
    main()
