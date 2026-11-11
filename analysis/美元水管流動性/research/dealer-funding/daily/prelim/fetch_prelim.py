"""抓 OFR repo 的 Preliminary 版（-P）7 個系列，與 Final 版（-F）比對重疊期間，輸出 daily_repo_prelim.csv。

不覆寫 daily/daily_repo.csv；只寫入 daily/prelim/。
"""
import json, os, time
import requests
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DAILY = os.path.dirname(HERE)
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)
OFR = "https://data.financialresearch.gov/v1"
START = "2018-01-01"
CUTOFF = "2026-06-30"
FINAL_CSV = os.path.join(DAILY, "daily_repo.csv")
PKEYS = [
    "REPO-DVP_AR_OO-P", "REPO-DVP_TV_TOT-P", "REPO-DVP_OV_TOT-P",
    "REPO-GCF_AR_OO-P", "REPO-GCF_TV_TOT-P",
    "REPO-TRIV1_AR_OO-P", "REPO-TRIV1_TV_TOT-P",
]
COLS = ["date", "series_key", "description", "value", "unit"]
S = requests.Session()
LOG = []


def get(k):
    """與 fetch_daily.py 相同的 API 與 3 次重試；原始回應快取到 prelim/raw/。"""
    path = os.path.join(RAW, f"ofr_{k}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    last = None
    for _ in range(3):
        try:
            r = S.get(f"{OFR}/series/full?mnemonic={k}", timeout=60)
            r.raise_for_status()
            j = r.json()
            with open(path, "w", encoding="utf-8") as f:
                f.write(r.text)
            time.sleep(0.3)
            return j
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


def base(k):
    return k[:-2]  # 去掉 "-P"/"-F" 得到共同基底名


rows, info = [], {}
for k in PKEYS:
    try:
        j = get(k)[k]
    except Exception as e:
        LOG.append(f"{k} FAIL {type(e).__name__}: {e}")
        continue
    md = j["metadata"]
    name = md["description"]["name"]
    unit = md.get("unit", {}).get("name", "")
    agg = j["timeseries"]["aggregation"]
    kept = [(d, k, name, v, unit) for d, v in agg if d >= START and v is not None]
    dates = [r[0] for r in kept]
    info[k] = dict(first=min(dates), last=max(dates), n=len(kept), n_raw=len(agg),
                   n_null=sum(1 for d, v in agg if v is None), name=name, unit=unit)
    rows.extend(kept)
    LOG.append(f"{k} rows={len(kept)} {min(dates)}..{max(dates)}")

df = pd.DataFrame(rows, columns=COLS)
df["base"] = df.series_key.map(base)

final = pd.read_csv(FINAL_CSV)
fin = final[final.series_key.isin([base(k) + "-F" for k in PKEYS])].copy()
fin["base"] = fin.series_key.map(base)
fin_meta = fin.groupby("base").agg(first=("date", "min"), last=("date", "max"), n=("date", "count"),
                                   name=("description", "first"), unit=("unit", "first"))

# 比對重疊期間（同基底、同日期）
m = df.merge(fin[["date", "base", "value"]].rename(columns={"value": "final_value"}),
             on=["date", "base"], how="inner")
m["diff"] = m.value - m.final_value
m["absdiff"] = m["diff"].abs()
overlap_keys = set(zip(m.date, m.base))

# 保留：date >= CUTOFF 的列 + 與 Final 重疊的列
keep = df.apply(lambda r: r.date >= CUTOFF or (r.date, r.base) in overlap_keys, axis=1)
out = df[keep][COLS].drop_duplicates(["date", "series_key"]).sort_values(["date", "series_key"])
out.to_csv(os.path.join(HERE, "daily_repo_prelim.csv"), index=False)

print("\n".join(LOG))
print("\n--- per series (P) ---")
for k, v in info.items():
    print(f"{k}: n={v['n']} raw={v['n_raw']} null={v['n_null']} {v['first']}..{v['last']} unit={v['unit']!r} name={v['name']!r}")
print("\n--- per series (F, Final) ---")
print(fin_meta.to_string())
print("\n--- overlap compare (same base, same date) ---")
for b, g in m.groupby("base"):
    exact = int((g.absdiff < 1e-9).sum())
    print(f"{b}: overlap={len(g)} exact_match={exact} max_absdiff={g.absdiff.max():.6g} "
          f"first={g.date.min()} last={g.date.max()}")
print(f"TOTAL overlap={len(m)} exact_match={int((m.absdiff < 1e-9).sum())} nonzero={int((m.absdiff >= 1e-9).sum())}")
print("\n--- top 5 largest abs diffs (date, series) ---")
top = m.sort_values("absdiff", ascending=False).head(5)
print(top[["date", "series_key" if "series_key" in m else "base", "value", "final_value", "diff"]].to_string(index=False))
print("\n--- out csv ---")
print("rows", len(out), "series", out.series_key.nunique(), "min", out.date.min(), "max", out.date.max())
print(out.groupby("series_key").date.agg(["min", "max", "count"]).to_string())
print("rows >= CUTOFF:", int((out.date >= CUTOFF).sum()))
