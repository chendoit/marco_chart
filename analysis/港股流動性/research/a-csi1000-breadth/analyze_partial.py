"""快取不完整時的暫行分析：用 cache/kline 已有的成分股算自高點跌幅分布。

由父 agent 在子 agent 回報 blocked（東財斷線，1000 檔只抓到 811 檔）後補寫。
分組只用東財行業（cache/meta），沒有行業資料的歸「未分類」；未用概念板塊。
"""
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
TECH = ["半导体", "电子", "元件", "光学", "通信", "计算机", "软件", "IT服务"]

cons = pd.read_excel(HERE / "raw" / "000852cons.xls", dtype=str)
code_col = [c for c in cons.columns if "代码" in c and "成份" in c or "Constituent Code" in c][0]
name_col = [c for c in cons.columns if "名称" in c and "成份" in c or "Constituent Name" in c][0]
names = dict(zip(cons[code_col].str.zfill(6), cons[name_col]))


def dd(close, n=None):
    s = close if n is None else close.iloc[-n:]
    return 1 - s.iloc[-1] / s.max()


def stats(close, amount):
    return {
        "dd_120": dd(close, 120),
        "dd_250": dd(close, 250),
        "dd_since_20241008": dd(close[close.index >= "2024-10-08"]),
        "vol_ratio_20_120": amount.iloc[-20:].mean() / amount.iloc[-140:-20].mean(),
    }


rows = []
for f in sorted((HERE / "cache" / "kline").glob("*.csv")):
    df = pd.read_csv(f, index_col="date").dropna(subset=["close"])
    if len(df) < 140:
        continue
    meta = HERE / "cache" / "meta" / f"{f.stem}.json"
    ind = json.loads(meta.read_text(encoding="utf-8")).get("industry", "") if meta.exists() else ""
    group = "未分類" if not ind else ("科技" if any(k in ind for k in TECH) else "其他")
    rows.append({"code": f.stem, "name": names.get(f.stem, ""), "industry": ind, "group": group,
                 "last_date": df.index[-1], **stats(df["close"], df["amount"])})
out = pd.DataFrame(rows)
out.to_csv(HERE / "breadth_latest_partial.csv", index=False, encoding="utf-8")

idx = pd.read_csv(HERE / "cache" / "index_000852.csv", index_col="date")
print("指數", {k: round(v, 3) for k, v in stats(idx["close"], idx["amount"]).items()}, "last", idx.index[-1])
print("樣本", len(out), "最新日分布", out.last_date.value_counts().head(3).to_dict())

bins = [-1, 0.02, 0.10, 0.30, 0.50, 1]
labels = ["距高<2%", "2-10%", "10-30%", "30-50%", ">50%"]
for col in ["dd_120", "dd_250", "dd_since_20241008"]:
    print(f"\n== {col}")
    for g, sub in [("全體", out)] + list(out.groupby("group")):
        dist = pd.cut(sub[col], bins, labels=labels).value_counts(normalize=True).reindex(labels).mul(100).round(1)
        print(f"{g:4s} n={len(sub):3d} 中位 {sub[col].median()*100:5.1f}% |", " ".join(f"{l}:{v}" for l, v in dist.items()))
print("\nvol_ratio_20_120 中位：", out.groupby("group").vol_ratio_20_120.median().round(2).to_dict(), "全體", round(out.vol_ratio_20_120.median(), 2))
print("vol_ratio<0.7 比例：", round((out.vol_ratio_20_120 < 0.7).mean() * 100, 1), "%")
