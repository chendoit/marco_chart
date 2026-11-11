"""B3：黃金回歸殘差。GC=F ~ 10Y 實質利率(fed_DFII10) + DXY。執行：PYTHONUTF8=1 venv\Scripts\python.exe <本檔>"""
import pickle, numpy as np, pandas as pd
ROOT = "C:/code/2025-12-05-MacroMicro-Data/"
def ls(n):
    o = pickle.load(open(f"{ROOT}data/{n}.pkl", "rb"))
    return pd.Series({pd.Timestamp(d).normalize(): v for d, v in o["data"]}).sort_index()
m = pd.read_csv(ROOT + "analysis/美元水管流動性/research/market-prices/market_prices.csv", parse_dates=["date"])
g = m[m.ticker == "GC=F"].set_index("date").close; d = m[m.ticker == "DX-Y.NYB"].set_index("date").close
df = pd.concat([g.rename("g"), d.rename("d"), ls("fed_DFII10").rename("r")], axis=1).dropna()
df = df[df.index >= "2018-01-01"]
T = "2026-10-30"
D = pd.concat([(df.g.pct_change() * 100).rename("y"), (df.r.diff() * 100).rename("dr"), (df.d.pct_change() * 100).rename("dd")], axis=1).dropna()
for w in [250, 500, len(D)]:
    tr = D[D.index < T].tail(w); A = np.c_[np.ones(len(tr)), tr[["dr", "dd"]].values]
    b = np.linalg.lstsq(A, tr.y.values, rcond=None)[0]; res = tr.y.values - A @ b; s = res.std(ddof=3)
    row = D.loc[T]; pred = b[0] + b[1] * row.dr + b[2] * row.dd
    print(f"日變動 窗口{w}: R2={1 - res.var() / tr.y.var():.2f} 預測{pred:.2f}% 實際{row.y:.2f}% 殘差{(row.y - pred) / s:.2f}σ")
for w in [250, 500, 750]:
    L = df[df.index < T].tail(w); A = np.c_[np.ones(len(L)), L.r, np.log(L.d)]
    b = np.linalg.lstsq(A, np.log(L.g), rcond=None)[0]; res = np.log(L.g) - A @ b
    r = df.loc[T]; fair = np.exp(b[0] + b[1] * r.r + b[2] * np.log(r.d))
    print(f"水準 窗口{w}: R2={1 - res.var() / np.log(L.g).var():.2f} 公允{fair:.0f} 實際{r.g:.0f} 殘差{np.log(r.g / fair) * 100:.2f}% = {np.log(r.g / fair) / res.std():.2f}σ")
