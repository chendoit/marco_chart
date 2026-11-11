# 日頻代理（聚合到季）與 Form PF 過度擔保率的相關

由 `analyze.py` 產生。參照：`FPF-OCRATEALL_PERCENT`（Form PF 合格對沖基金 repo 借款的過度擔保率，%），
另附 `FPF-OCRATECASHSEC_PERCENT`。Form PF 期間 2018Q1–2026Q2，最多 34 季。

**判讀規則**
- 樣本少於 20 季的列不下結論（`conclusive=False`）。`gcf_sofr_bp` 季內資料常不足 20 天，季平均會變 NaN，季末值也很稀疏。
- 30 多季的相關，|r| 約 0.35 才達 5% 顯著（雙尾，n≈32）；又因序列有自我相關，實際有效樣本更少，門檻應更高。
- **相關只代表同步，不代表可以互換**。季頻相關高，不表示日頻代理能告訴你某一天的 haircut。
- level = 水準相關（容易被共同趨勢與利率體制拉高）；diff = 季變動相關（較嚴格）。

## 1. 主表：Pearson r，參照 fpf_oc_all（依季平均水準 |r| 排序）

| candidate | qmean_level | qend_level | qmean_diff | qend_diff | n_qmean_level | n_qmean_diff |
|---|---|---|---|---|---|---|
| dvp_ov_to_tri_vol | -0.58 | -0.638 | -0.343 | -0.176 | 33.0 | 32.0 |
| sofr_p75_p25_bp | -0.554 | -0.4 | -0.298 | -0.392 | 33.0 | 32.0 |
| dvp_ov_chg60_pct | -0.515 | -0.318 | -0.127 | 0.099 | 32.0 | 31.0 |
| dvp_tri_bp | -0.492 | -0.438 | -0.112 | -0.215 | 33.0 | 32.0 |
| dvp_vol_rel60_pct | -0.38 | -0.434 | 0.002 | -0.125 | 32.0 | 31.0 |
| sofr_tgcr_bp | -0.16 | -0.492 | -0.156 | -0.233 | 33.0 | 32.0 |
| nontri_share_pct | -0.143 | -0.218 | -0.294 | -0.234 | 33.0 | 32.0 |
| bgcr_tgcr_bp | -0.091 |  | 0.098 |  | 33.0 | 32.0 |
| tri_vol_rel60_pct | -0.024 | 0.162 | 0.466 | 0.23 | 34.0 | 33.0 |
| sofr_p99_p1_bp | -0.021 | -0.13 | -0.121 | -0.43 | 33.0 | 32.0 |
| sofr_p99_med_bp | 0.019 | -0.12 | -0.084 | -0.4 | 33.0 | 32.0 |
| gcf_sofr_bp |  | -0.415 |  | 0.066 | 4.0 | 2.0 |

## 2. Spearman（秩相關），參照 fpf_oc_all

| candidate | qmean_level | qend_level | qmean_diff | qend_diff |
|---|---|---|---|---|
| bgcr_tgcr_bp | -0.145 |  | -0.037 |  |
| dvp_ov_chg60_pct | -0.498 | -0.285 | 0.104 | 0.134 |
| dvp_ov_to_tri_vol | -0.621 | -0.678 | -0.226 | -0.126 |
| dvp_tri_bp | -0.572 | -0.471 | -0.019 | 0.003 |
| dvp_vol_rel60_pct | -0.338 | -0.492 | 0.209 | -0.056 |
| gcf_sofr_bp |  | -0.49 |  | 0.188 |
| nontri_share_pct | -0.008 | -0.141 | -0.178 | -0.081 |
| sofr_p75_p25_bp | -0.535 | -0.638 | -0.227 | -0.3 |
| sofr_p99_med_bp | 0.06 | -0.421 | -0.119 | -0.153 |
| sofr_p99_p1_bp | 0.002 | -0.385 | -0.164 | -0.247 |
| sofr_tgcr_bp | -0.029 | -0.484 | -0.048 | -0.177 |
| tri_vol_rel60_pct | -0.159 | 0.136 | 0.312 | 0.384 |

## 3. 季平均 vs 季末：可下結論列的 |Pearson r| 中位數

| agg | kind | absr |
|---|---|---|
| qend | diff | 0.23 |
| qend | level | 0.4 |
| qmean | diff | 0.127 |
| qmean | level | 0.16 |

## 4. 參照改為 fpf_oc_cashsec（季平均，Pearson）

| candidate | diff | level |
|---|---|---|
| bgcr_tgcr_bp | 0.051 | -0.159 |
| dvp_ov_chg60_pct | -0.077 | -0.455 |
| dvp_ov_to_tri_vol | -0.314 | -0.542 |
| dvp_tri_bp | -0.032 | -0.261 |
| dvp_vol_rel60_pct | 0.036 | -0.323 |
| nontri_share_pct | -0.307 | -0.371 |
| sofr_p75_p25_bp | -0.242 | -0.29 |
| sofr_p99_med_bp | -0.093 | 0.085 |
| sofr_p99_p1_bp | -0.138 | 0.011 |
| sofr_tgcr_bp | -0.14 | -0.004 |
| tri_vol_rel60_pct | 0.438 | 0.023 |

## 5. 組合（等權 z 分數：sofr_tgcr_bp, dvp_tri_bp, sofr_p75_p25_bp）

| reference | agg | kind | n | pearson | spearman |
|---|---|---|---|---|---|
| fpf_oc_all | qmean | level | 33 | -0.476 | -0.503 |
| fpf_oc_all | qmean | diff | 32 | -0.236 | -0.104 |
| fpf_oc_cashsec | qmean | level | 33 | -0.219 | -0.216 |
| fpf_oc_cashsec | qmean | diff | 32 | -0.181 | 0.002 |
| fpf_oc_all | qend | level | 33 | -0.592 | -0.622 |
| fpf_oc_all | qend | diff | 32 | -0.389 | -0.285 |
| fpf_oc_cashsec | qend | level | 33 | -0.395 | -0.376 |
| fpf_oc_cashsec | qend | diff | 32 | -0.32 | -0.158 |

## 6. 分段檢查（季平均水準，參照 fpf_oc_all；每段 < 20 季，只用來看體制，不下結論）

| candidate | period | n | pearson | cand_mean | fpf_mean |
|---|---|---|---|---|---|
| dvp_ov_to_tri_vol | 2018Q1-2022Q2 | 17 | -0.411 | 1.099 | 17.01 |
| dvp_ov_to_tri_vol | 2022Q3-2026Q2 | 16 | -0.309 | 1.353 | 13.04 |
| sofr_p75_p25_bp | 2018Q1-2022Q2 | 17 | -0.56 | 5.692 | 17.01 |
| sofr_p75_p25_bp | 2022Q3-2026Q2 | 16 | -0.353 | 7.121 | 13.04 |
| dvp_tri_bp | 2018Q1-2022Q2 | 17 | -0.119 | -2.179 | 17.01 |
| dvp_tri_bp | 2022Q3-2026Q2 | 16 | -0.607 | 0.369 | 13.04 |
| sofr_tgcr_bp | 2018Q1-2022Q2 | 17 | -0.246 | 1.412 | 17.01 |
| sofr_tgcr_bp | 2022Q3-2026Q2 | 16 | 0.738 | 2.094 | 13.04 |
| dvp_ov_chg60_pct | 2018Q1-2022Q2 | 16 | -0.512 | 1.581 | 17.18 |
| dvp_ov_chg60_pct | 2022Q3-2026Q2 | 16 | -0.285 | 5.787 | 13.04 |

完整表見 `corr_table.csv`、`combo_corr.csv`。
