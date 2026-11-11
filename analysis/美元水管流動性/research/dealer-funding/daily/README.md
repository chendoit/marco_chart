# dealer-funding 日頻資料（daily/）

## 結論
- **F2 日頻 haircut：找不到公開來源。** `daily_repo.csv` 裡全部都是 repo 利率／成交量**代理**，沒有一個是 haircut。
- **F1（一級交易商融資與部位）：沒有日頻來源。** NY Fed Primary Dealer Statistics 只到週頻（週三），前一輪已抓（`../pd_financing.csv`）。
- **F4（對沖基金槓桿）：沒有日頻來源。** OFR Hedge Fund Monitor（SEC Form PF 彙總）是季頻，SCOOS 也是季頻；前一輪已抓（`../hedge_fund_leverage.csv`）。
- F1、F4 沒有另外寫檔案。

## 檔案
- `daily_repo.csv`：長表 `date,series_key,description,value,unit`，13 個系列，25,443 列，日期 2018-01-02 ～ 2026-11-06。
- `fetch_daily.py`：抓取腳本（快取放在 `raw/`；要重新抓取，設 `REFRESH=1`）。
- `candidates.md`：候選系列清單。

## 系列（全部都是代理，不是 haircut）
| series_key | 來源 | 起 | 迄 | 筆數 | 單位 |
|---|---|---|---|---|---|
| REPO-DVP_AR_OO-F | OFR | 2018-05-08 | 2026-06-30 | 1947 | 取自 OFR metadata |
| REPO-DVP_TV_TOT-F | OFR | 2018-05-07 | 2026-06-30 | 2034 | 同上 |
| REPO-DVP_OV_TOT-F | OFR | 2018-05-07 | 2026-06-30 | 2034 | 同上 |
| REPO-GCF_AR_OO-F | OFR | 2018-06-15 | 2026-06-30 | 270 | 同上（稀疏，中位數間隔 4 天） |
| REPO-GCF_TV_TOT-F | OFR | 2018-05-07 | 2026-06-30 | 2034 | 同上 |
| REPO-TRIV1_AR_OO-F | OFR | 2018-01-02 | 2026-06-30 | 2115 | 同上 |
| REPO-TRIV1_TV_TOT-F | OFR | 2018-01-02 | 2026-06-30 | 2115 | 同上 |
| NYF-SOFR/BGCR/TGCR-RATE | NY Fed | 2018-04-02 | 2026-11-06 | 各 2149 | Percent |
| NYF-SOFR/BGCR/TGCR-VOL | NY Fed | 2018-04-02 | 2026-11-06 | 各 2149 | Billions of USD |

注意：
- OFR 的 Final 版只到 2026-06-30（落後發布）。如果要近期資料，可以改用 `-P`（Preliminary）系列，這一版沒抓。
- GCF 隔夜利率資料稀疏，只有 270 筆，用的時候要留意。

## 驗收
- `verify.py dealer-funding` → `PASS dealer-funding`（既有檔案沒動）。
- 全部日期的相鄰間隔中位數是 1 天；逐系列看，除了 REPO-GCF_AR_OO-F 是 4 天，其他都是 1 天。

## 試過但失敗／不用的來源
- OFR `/v1/` repo 資料集：有日頻資料，但 164 個系列只有利率與成交量（DVP、Tri-Party、GCF），沒有 haircut。已採用部分系列作為代理。
- NY Fed Markets API：secured rates（SOFR／BGCR／TGCR）有日頻，但只有利率、百分位與成交量，沒有擔保品折扣。其他類別（rp、pd、seclending、soma）沒有 haircut 序列（依類別判斷，沒有逐一抓取）。
- 依任務指示，沒有再追 SEC 或其他網站。已知的 haircut 相關公開資料（NY Fed 三方回購統計的 margin 分布、OFR NCCBR 試點）都不是日頻 API，這次沒有嘗試。
- F2 最接近的公開近似仍是前一輪的季頻 FPF 過度擔保率（`../repo_haircuts.csv`）。
