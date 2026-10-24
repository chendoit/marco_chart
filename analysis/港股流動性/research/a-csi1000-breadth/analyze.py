"""由 cache/ 計算中證1000 成分股自高點跌幅分布，輸出 breadth_latest.csv 並列印分布表。

跌幅口徑（dd 皆為正值，= 1 - 最新收盤 / 區間最高收盤）：
- dd_120：近 120 個交易日（含最新一日）最高收盤
- dd_250：近 250 個交易日最高收盤
- dd_since_20241008：2024-10-08（含）以來最高收盤
- vol_ratio_20_120：近 20 日日均成交額 / 其之前 120 日日均成交額

分組：AI 相關 = 命中 AI 概念板塊成員，或行業屬電子／通信／計算機；其餘為「其他」。
"""

import csv
import json
import os
import statistics

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
OUT_CSV = os.path.join(HERE, "breadth_latest.csv")
TECH_KEYWORDS = ["电子", "半导体", "通信", "计算机", "计算机设备", "软件", "IT", "光学", "元件"]
OUT_COLS = ["code", "name", "group", "dd_120", "dd_250", "dd_since_20241008", "vol_ratio_20_120"]


def dd(closes, window=None):
    s = closes if window is None else closes[-window:]
    if len(s) == 0 or s.isna().all():
        return None
    return 1 - s.iloc[-1] / s.max()


def load_kline(path):
    df = pd.read_csv(path, dtype={"date": str})
    df = df.dropna(subset=["close"])
    return df.reset_index(drop=True)


def metrics(df):
    close = df["close"].astype(float)
    m = {
        "n": len(df),
        "dd_120": dd(close, 120) if len(df) >= 120 else None,
        "dd_250": dd(close, 250) if len(df) >= 250 else None,
        "dd_since_20241008": dd(close[df["date"] >= "2024-10-08"]),
        "vol_ratio_20_120": None,
    }
    amt = df["amount"].astype(float)
    if len(df) >= 140:
        m["vol_ratio_20_120"] = amt.iloc[-20:].mean() / amt.iloc[-140:-20].mean()
    return m


def bucket(v):
    if v is None:
        return "資料不足"
    if v > 0.5:
        return ">50%"
    if v > 0.3:
        return "30–50%"
    if v > 0.1:
        return "10–30%"
    if v >= 0.02:
        return "2–10%"
    return "<2%（近高點／創新高）"


def describe(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return {"n": 0}
    n = len(vals)
    out = {"n": n, "median": statistics.median(vals), "mean": statistics.fmean(vals)}
    for name, pred in [(">50%", lambda v: v > 0.5), ("30–50%", lambda v: 0.3 < v <= 0.5),
                       ("10–30%", lambda v: 0.1 < v <= 0.3), ("<10%", lambda v: v <= 0.1),
                       ("<2%創新高附近", lambda v: v < 0.02)]:
        k = sum(1 for v in vals if pred(v))
        out[name] = (k, k / n)
    return out


def main():
    with open(os.path.join(CACHE, "ai_concepts.json"), encoding="utf-8") as f:
        concepts = json.load(f)
    ai_members = {}
    for board, members in concepts.items():
        for c in members:
            ai_members.setdefault(c, set()).add(board)

    cons = pd.read_excel(os.path.join(HERE, "raw", "000852cons.xls"), dtype=str)
    cons = cons.rename(columns={"成份券代码Constituent Code": "code", "成份券名称Constituent Name": "name"})
    cons = cons[["code", "name"]].drop_duplicates("code")

    rows = []
    for code, name in zip(cons["code"], cons["name"]):
        kpath = os.path.join(CACHE, "kline", f"{code}.csv")
        mpath = os.path.join(CACHE, "meta", f"{code}.json")
        if not os.path.exists(kpath) or not os.path.exists(mpath):
            continue
        with open(mpath, encoding="utf-8") as f:
            industry = json.load(f).get("industry", "")
        df = load_kline(kpath)
        m = metrics(df)
        ai_boards = ai_members.get(code, set())
        tech = any(k in industry for k in TECH_KEYWORDS)
        group = "AI相關" if (ai_boards or tech) else "其他"
        rows.append({"code": code, "name": name, "group": group, "industry": industry,
                     "boards": ";".join(sorted(ai_boards)), **m})

    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r[c] is None else (f"{r[c]:.6f}" if isinstance(r[c], float) else r[c]))
                        for c in OUT_COLS})

    detail = os.path.join(HERE, "breadth_detail.csv")
    pd.DataFrame(rows).to_csv(detail, index=False, encoding="utf-8")

    print(f"[rows] 可計算 {len(rows)} 檔；AI相關 {sum(r['group']=='AI相關' for r in rows)} 檔；其他 {sum(r['group']=='其他' for r in rows)} 檔")
    for g in ["全體", "AI相關", "其他"]:
        sub = rows if g == "全體" else [r for r in rows if r["group"] == g]
        for key in ["dd_120", "dd_250", "dd_since_20241008", "vol_ratio_20_120"]:
            d = describe([r[key] for r in sub])
            if key == "vol_ratio_20_120":
                print(f"[{g}] {key}: n={d['n']} median={d.get('median', float('nan')):.3f}")
                continue
            print(f"[{g}] {key}: n={d['n']} median={d.get('median', float('nan')):.4f} mean={d.get('mean', float('nan')):.4f} "
                  f"| >50%={d.get('>50%')} | 30-50%={d.get('30–50%')} | 10-30%={d.get('10–30%')} "
                  f"| <10%={d.get('<10%')} | <2%={d.get('<2%創新高附近')}")

    # 指數本身
    idx = load_kline(os.path.join(CACHE, "index_000852.csv"))
    im = metrics(idx)
    print(f"[index] 000852 最新 {idx['date'].iloc[-1]} 收盤 {idx['close'].iloc[-1]}；"
          f"dd_120={im['dd_120']:.4f} dd_250={im['dd_250'] if im['dd_250'] is None else round(im['dd_250'], 4)} "
          f"dd_since_20241008={im['dd_since_20241008']:.4f}")
    print(f"[index-bins] 120/250/since 距高點 <2% 範圍: "
          f"{[bucket(im[k]) for k in ['dd_120', 'dd_250', 'dd_since_20241008'] if im[k] is not None]}")


if __name__ == "__main__":
    main()
