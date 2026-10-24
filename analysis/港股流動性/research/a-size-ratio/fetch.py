"""抓 A 股大小盤指數、全 A 成交額與全市場兩融餘額的日序列（2018-01-01 起，日頻）。

來源（皆為東方財富）：
- 指數收盤與「額」：push2his kline API（日線、不還原）
- 兩融餘額：datacenter-web RPTA_RZRQ_LSHJ（全市場 RZRQYE）
用法：
    venv\\Scripts\\python.exe fetch.py                      # 全部歷史（2018-01-01 起）
    venv\\Scripts\\python.exe fetch.py --start 2026-01-01   # 增量：只重抓該日起，合併進既有 CSV

單位：a_turnover、margin_balance 皆為「億元」；收盤為指數點位。
"""

import argparse
import datetime as dt
import os
import sys
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_CSV = os.path.join(HERE, "a_size_ratio.csv")

# 東方財富 secid：1 = 上交所、0 = 深交所、2 = 中證指數系列
SERIES = {
    "hs300": "1.000300",      # 滬深300
    "csi1000": "1.000852",    # 中證1000
    "csia500": "1.000510",    # 中證A500（2024-09-23 發布，之前留空）
    "csi2000": "2.932000",    # 中證2000
    "sh_comp": "1.000001",    # 上證綜指
    "sz_comp": "0.399001",    # 深證成指（只用來加總全 A 成交額）
}
CSIA500_RELEASE = "2024-09-23"
DD_BASE = "2024-10-01"        # 回撤起算日（自此以來的高點）
KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
RZRQ_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
KLINE_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
RZRQ_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
CST = ZoneInfo("Asia/Shanghai")
COLUMNS = [
    "date", "hs300", "csi1000", "csia500", "csi2000", "sh_comp",
    "a_turnover", "margin_balance", "ratio_csi1000_hs300", "ret20_spread",
]


def get_json(url, params, headers, retries=5):
    """東財常在連發請求時斷線（RemoteDisconnected），逐次退避重試。"""
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=20)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if i == retries - 1:
                raise
            print(f"[retry] {e}", file=sys.stderr, flush=True)
            time.sleep(3 + 3 * i)


def fetch_kline(secid, start, end):
    """回傳 {date: (收盤, 成交額元)}。"""
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",  # 日期,開,收,高,低,量,額
        "klt": "101",
        "fqt": "0",
        "beg": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
    }
    payload = get_json(KLINE_URL, params, KLINE_HEADERS)
    data = payload.get("data")
    if not data or not data.get("klines"):
        raise RuntimeError(f"{secid} 無資料 rc={payload.get('rc')}")
    out = {}
    for line in data["klines"]:
        parts = line.split(",")
        out[parts[0]] = (float(parts[2]), float(parts[6]))
    print(f"[ok] {secid} {data.get('name')}: {len(out)} 筆 {min(out)} ~ {max(out)}", flush=True)
    return out


def fetch_margin(start):
    """回傳 {date: 融資融券餘額元}，依日期由新到舊分頁抓到 start 為止。"""
    out = {}
    page = 1
    while True:
        params = {
            "reportName": "RPTA_RZRQ_LSHJ",
            "columns": "ALL",
            "pageNumber": page,
            "pageSize": 500,
            "sortColumns": "DIM_DATE",
            "sortTypes": "-1",
            "source": "WEB",
            "client": "WEB",
        }
        res = get_json(RZRQ_URL, params, RZRQ_HEADERS)["result"]
        rows = res["data"]
        for r in rows:
            d = r["DIM_DATE"][:10]
            if r.get("RZRQYE") is not None and d >= start.isoformat():
                out[d] = float(r["RZRQYE"])
        last_d = rows[-1]["DIM_DATE"][:10]
        if page >= res["pages"] or last_d < start.isoformat():
            break
        page += 1
        time.sleep(1.5)
    print(f"[ok] RZRQ_LSHJ: {len(out)} 筆 {min(out)} ~ {max(out)}", flush=True)
    return out


def load_existing():
    if not os.path.exists(OUT_CSV):
        return None
    return pd.read_csv(OUT_CSV, dtype=str, index_col="date")


def print_summary(df):
    """最新讀數與驗算，供 report.md 引用。"""
    last = df.dropna(subset=["hs300", "csi1000"]).iloc[-1]
    print(f"[latest] {df.index[-1]} 最後一列；有 hs300/csi1000 的最新日 {last.name}")
    print(f"[latest] hs300={last.hs300:.2f} csi1000={last.csi1000:.2f}")

    px = df.loc[df.index >= DD_BASE]
    for k in ["csi1000", "hs300"]:
        s = px[k].dropna()
        dd = s.iloc[-1] / s.cummax().iloc[-1] - 1
        peak_d = s[s == s.cummax()].index[-1]
        print(f"[dd] {k} 自 {DD_BASE} 以來高點 {s.max():.2f}（{s.idxmax()}）；最新回撤 {dd:.2%}，高點日 {peak_d}")

    r = df["ret20_spread"].dropna()
    cur = r.iloc[-1]
    pct = (r <= cur).mean() * 100
    print(f"[spread] ret20_spread 最新 {cur:.4f}（{r.index[-1]}）；2018 年以來百分位 {pct:.1f}%（樣本 {len(r)}）")

    m = df["margin_balance"].dropna()
    chg60 = m.iloc[-1] - m.iloc[-61]
    print(f"[margin] 最新 {m.iloc[-1]:.2f} 億元（{m.index[-1]}）；60 交易日前 {m.iloc[-61]:.2f}（{m.index[-61]}）；"
          f"變化 {chg60:+.2f} 億元 / {chg60 / m.iloc[-61]:+.2%}")

    t = df.loc["2024-10-08", "a_turnover"] if "2024-10-08" in df.index else float("nan")
    print(f"[check] 2024-10-08 全 A 成交額（滬+深成指）= {t:.2f} 億元 ≈ {t / 10000:.4f} 萬億")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01", help="起始日 YYYY-MM-DD（增量時用）")
    args = ap.parse_args()
    start = dt.date.fromisoformat(args.start)

    # A 股 15:00 收盤；15:30 後才視為今日完整，否則丟掉今日（可能是盤中值）
    now = dt.datetime.now(CST)
    end = now.date() if now.hour * 60 + now.minute >= 15 * 60 + 30 else now.date() - dt.timedelta(days=1)

    kl = {}
    for key, secid in SERIES.items():
        kl[key] = fetch_kline(secid, start, end)
        time.sleep(1.5)
    margin = fetch_margin(start)

    def ser(d):
        return pd.Series(d, dtype="float64")

    close = pd.DataFrame({k: ser({d: c for d, (c, _) in kl[k].items()})
                          for k in ["hs300", "csi1000", "csia500", "csi2000", "sh_comp"]})
    turnover = (ser({d: a for d, (_, a) in kl["sh_comp"].items()})
                + ser({d: a for d, (_, a) in kl["sz_comp"].items()})) / 1e8  # 元 → 億元，兩者皆有才有值
    df = pd.concat([close, pd.DataFrame({"a_turnover": turnover, "margin_balance": ser(margin) / 1e8})], axis=1)
    df = df.sort_index()
    df = df[df.index <= end.isoformat()]
    df.loc[df.index < CSIA500_RELEASE, "csia500"] = float("nan")

    df["ratio_csi1000_hs300"] = df["csi1000"] / df["hs300"]
    # 20 個交易日報酬以「兩指數皆有值」的列為準，避免日期錯位
    ret20 = df[["csi1000", "hs300"]].dropna().pct_change(20)
    df["ret20_spread"] = ret20["csi1000"] - ret20["hs300"]

    df.index.name = "date"
    fresh = df.reset_index()[COLUMNS]
    fresh_str = fresh.copy()
    for c in COLUMNS[1:]:
        fresh_str[c] = fresh[c].map(lambda v: "" if pd.isna(v) else f"{v:.6f}")
    fresh_str = fresh_str.set_index("date")

    old = load_existing()
    if old is not None and args.start != "2018-01-01":
        old = old[old.index < args.start]
        out = pd.concat([old, fresh_str])
    else:
        out = fresh_str
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out.to_csv(OUT_CSV, encoding="utf-8", columns=COLUMNS[1:], lineterminator="\n")

    # 摘要用 float 版本（未字串化）
    print_summary(df)
    print(f"[done] {OUT_CSV}：共 {len(out)} 列，最新 {out.index.max()}", flush=True)


if __name__ == "__main__":
    main()
