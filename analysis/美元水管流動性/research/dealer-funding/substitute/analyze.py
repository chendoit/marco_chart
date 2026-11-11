"""日頻 repo 代理 → 季頻，與 Form PF 過度擔保率（haircut 近似）對齊並算相關。

只讀既有檔案，不抓外部資料，不改動既有檔案。輸出寫到本目錄：
  quarterly_align.csv、corr_table.csv、corr.md
用法：venv\\Scripts\\python.exe substitute/analyze.py
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MIN_N = 20  # 少於 20 季不下結論

# ---------- 讀日頻 ----------
d = pd.read_csv(os.path.join(ROOT, "daily", "daily_repo.csv"), parse_dates=["date"])
w = d.pivot_table(index="date", columns="series_key", values="value").sort_index()

# NY Fed SOFR 百分位（既有 raw JSON，只取需要欄位）
with open(os.path.join(ROOT, "daily", "raw", "nyf_sofr.json"), encoding="utf-8") as f:
    rr = json.load(f)["refRates"]
pct = pd.DataFrame(
    [(r["effectiveDate"], r.get("percentPercentile1"), r.get("percentPercentile25"),
      r.get("percentPercentile75"), r.get("percentPercentile99")) for r in rr],
    columns=["date", "p1", "p25", "p75", "p99"])
pct["date"] = pd.to_datetime(pct["date"])
pct = pct.set_index("date").sort_index().apply(pd.to_numeric, errors="coerce")
w = w.join(pct, how="left")

# ---------- 日頻候選指標 ----------
c = pd.DataFrame(index=w.index)
bp = 100.0
c["sofr_tgcr_bp"] = (w["NYF-SOFR-RATE"] - w["NYF-TGCR-RATE"]) * bp
c["bgcr_tgcr_bp"] = (w["NYF-BGCR-RATE"] - w["NYF-TGCR-RATE"]) * bp
c["dvp_tri_bp"] = (w["REPO-DVP_AR_OO-F"] - w["REPO-TRIV1_AR_OO-F"]) * bp
c["gcf_sofr_bp"] = (w["REPO-GCF_AR_OO-F"] - w["NYF-SOFR-RATE"]) * bp  # 稀疏
c["sofr_p99_p1_bp"] = (w["p99"] - w["p1"]) * bp
c["sofr_p75_p25_bp"] = (w["p75"] - w["p25"]) * bp
c["sofr_p99_med_bp"] = (w["p99"] - w["NYF-SOFR-RATE"]) * bp


def rel60(s):
    s = s.dropna()
    return (s / s.rolling(60, min_periods=40).mean() - 1) * 100


c["dvp_vol_rel60_pct"] = rel60(w["REPO-DVP_TV_TOT-F"])
c["tri_vol_rel60_pct"] = rel60(w["REPO-TRIV1_TV_TOT-F"])
ov = w["REPO-DVP_OV_TOT-F"].dropna()
c["dvp_ov_chg60_pct"] = (np.log(ov) - np.log(ov.shift(60))) * 100
c["nontri_share_pct"] = (1 - w["NYF-TGCR-VOL"] / w["NYF-SOFR-VOL"]) * 100
c["dvp_ov_to_tri_vol"] = w["REPO-DVP_OV_TOT-F"] / w["REPO-TRIV1_TV_TOT-F"]

# ---------- 聚合到季 ----------
c = c.loc[c.index >= "2018-01-01"]
qmean = c.resample("QE").mean()
qcount = c.resample("QE").count()
qmean = qmean.where(qcount >= 20)  # 季內少於 20 個交易日不算平均（GCF 稀疏會被剔掉）
qend = c.resample("QE").last()  # 季內最後一筆可得值
qend_n = c.resample("QE").apply(lambda s: s.dropna().index.max() if s.notna().any() else pd.NaT)

# ---------- 參照：Form PF 過度擔保率 ----------
h = pd.read_csv(os.path.join(ROOT, "repo_haircuts.csv"), parse_dates=["date"])
ref = h.pivot_table(index="date", columns="series_key", values="value")
ref.index = ref.index + pd.offsets.QuarterEnd(0)
REFS = {"FPF-OCRATEALL_PERCENT": "fpf_oc_all", "FPF-OCRATECASHSEC_PERCENT": "fpf_oc_cashsec"}
ref = ref[list(REFS)].rename(columns=REFS)

align = ref.copy()
for col in c.columns:
    align[f"{col}__qmean"] = qmean[col]
    align[f"{col}__qend"] = qend[col]
align = align.loc[align.index >= "2018-03-31"].dropna(how="all")
align.index.name = "date"
out = align.reset_index()
out["date"] = out["date"].dt.strftime("%Y-%m-%d")
out.round(4).to_csv(os.path.join(HERE, "quarterly_align.csv"), index=False, encoding="utf-8")

# ---------- 相關 ----------
rows = []
for refc in REFS.values():
    for col in c.columns:
        for agg in ("qmean", "qend"):
            x = align[f"{col}__{agg}"]
            y = align[refc]
            for kind in ("level", "diff"):
                xx, yy = (x, y) if kind == "level" else (x.diff(), y.diff())
                m = pd.concat([xx, yy], axis=1).dropna()
                n = len(m)
                if n >= 5:
                    pr = m.iloc[:, 0].corr(m.iloc[:, 1])
                    sp = m.iloc[:, 0].rank().corr(m.iloc[:, 1].rank())
                else:
                    pr = sp = np.nan
                rows.append(dict(reference=refc, candidate=col, agg=agg, kind=kind, n=n,
                                 pearson=round(pr, 3) if pd.notna(pr) else np.nan,
                                 spearman=round(sp, 3) if pd.notna(sp) else np.nan,
                                 conclusive=n >= MIN_N))
ct = pd.DataFrame(rows)
ct.to_csv(os.path.join(HERE, "corr_table.csv"), index=False, encoding="utf-8")

# ---------- 組合（等權 z 分數，季平均） ----------
COMBO = ["sofr_tgcr_bp", "dvp_tri_bp", "sofr_p75_p25_bp"]  # 價格面：非三方溢價 + 中介價差 + 利率分散
combo_res = []
for agg in ("qmean", "qend"):
    z = pd.DataFrame({k: align[f"{k}__{agg}"] for k in COMBO})
    z = (z - z.mean()) / z.std()
    comp = z.mean(axis=1, skipna=False)
    for refc in REFS.values():
        for kind in ("level", "diff"):
            a, b = (comp, align[refc]) if kind == "level" else (comp.diff(), align[refc].diff())
            m = pd.concat([a, b], axis=1).dropna()
            combo_res.append(dict(reference=refc, agg=agg, kind=kind, n=len(m),
                                  pearson=round(m.iloc[:, 0].corr(m.iloc[:, 1]), 3),
                                  spearman=round(m.iloc[:, 0].rank().corr(m.iloc[:, 1].rank()), 3)))
cr = pd.DataFrame(combo_res)
cr.to_csv(os.path.join(HERE, "combo_corr.csv"), index=False, encoding="utf-8")

# ---------- 分段（體制檢查，各段 < 20 季，僅供說明） ----------
SPLIT = "2022-06-30"
seg_rows = []
for col in ["dvp_ov_to_tri_vol", "sofr_p75_p25_bp", "dvp_tri_bp", "sofr_tgcr_bp", "dvp_ov_chg60_pct"]:
    for lab, sl in (("2018Q1-2022Q2", align.index <= SPLIT), ("2022Q3-2026Q2", align.index > SPLIT)):
        m = align.loc[sl, [f"{col}__qmean", "fpf_oc_all"]].dropna()
        seg_rows.append(dict(candidate=col, period=lab, n=len(m),
                             pearson=round(m.iloc[:, 0].corr(m.iloc[:, 1]), 3),
                             cand_mean=round(m.iloc[:, 0].mean(), 3), fpf_mean=round(m.iloc[:, 1].mean(), 2)))
seg = pd.DataFrame(seg_rows)
seg.to_csv(os.path.join(HERE, "split_corr.csv"), index=False, encoding="utf-8")

# ---------- corr.md ----------
def md(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r.values) + " |")
    return "\n".join(lines)


main = ct[ct.reference == "fpf_oc_all"].copy()
piv = main.pivot_table(index="candidate", columns=["agg", "kind"], values="pearson")
piv.columns = [f"{a}_{k}" for a, k in piv.columns]
nn = main.pivot_table(index="candidate", columns=["agg", "kind"], values="n")
nn.columns = [f"n_{a}_{k}" for a, k in nn.columns]
summ = piv.join(nn[["n_qmean_level", "n_qmean_diff"]]).reset_index()
summ = summ[["candidate", "qmean_level", "qend_level", "qmean_diff", "qend_diff", "n_qmean_level", "n_qmean_diff"]]
summ = summ.reindex(summ.qmean_level.abs().sort_values(ascending=False).index)

sp_main = main.pivot_table(index="candidate", columns=["agg", "kind"], values="spearman")
sp_main.columns = [f"{a}_{k}" for a, k in sp_main.columns]
sp_main = sp_main.reset_index()[["candidate", "qmean_level", "qend_level", "qmean_diff", "qend_diff"]]

cash = ct[(ct.reference == "fpf_oc_cashsec") & (ct["agg"] == "qmean")].pivot_table(
    index="candidate", columns="kind", values="pearson").reset_index()

# 季平均 vs 季末：比較 |r| 的中位數（只計 n>=20）
ok = main[main.conclusive]
cmp_ = ok.assign(absr=ok.pearson.abs()).groupby(["agg", "kind"]).absr.median().round(3).reset_index()

text = f"""# 日頻代理（聚合到季）與 Form PF 過度擔保率的相關

由 `analyze.py` 產生。參照：`FPF-OCRATEALL_PERCENT`（Form PF 合格對沖基金 repo 借款的過度擔保率，%），
另附 `FPF-OCRATECASHSEC_PERCENT`。Form PF 期間 2018Q1–2026Q2，最多 34 季。

**判讀規則**
- 樣本少於 {MIN_N} 季的列不下結論（`conclusive=False`）。`gcf_sofr_bp` 季內資料常不足 20 天，季平均會變 NaN，季末值也很稀疏。
- 30 多季的相關，|r| 約 0.35 才達 5% 顯著（雙尾，n≈32）；又因序列有自我相關，實際有效樣本更少，門檻應更高。
- **相關只代表同步，不代表可以互換**。季頻相關高，不表示日頻代理能告訴你某一天的 haircut。
- level = 水準相關（容易被共同趨勢與利率體制拉高）；diff = 季變動相關（較嚴格）。

## 1. 主表：Pearson r，參照 fpf_oc_all（依季平均水準 |r| 排序）

{md(summ)}

## 2. Spearman（秩相關），參照 fpf_oc_all

{md(sp_main)}

## 3. 季平均 vs 季末：可下結論列的 |Pearson r| 中位數

{md(cmp_)}

## 4. 參照改為 fpf_oc_cashsec（季平均，Pearson）

{md(cash)}

## 5. 組合（等權 z 分數：{', '.join(COMBO)}）

{md(cr)}

## 6. 分段檢查（季平均水準，參照 fpf_oc_all；每段 < 20 季，只用來看體制，不下結論）

{md(seg)}

完整表見 `corr_table.csv`、`combo_corr.csv`。
"""
with open(os.path.join(HERE, "corr.md"), "w", encoding="utf-8") as f:
    f.write(text)
print(summ.to_string(index=False))
print(cmp_.to_string(index=False))
print(cr.to_string(index=False))
print(cash.to_string(index=False))
print(seg.to_string(index=False))
