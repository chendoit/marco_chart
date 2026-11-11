# 任務：交易商融資、回購折扣率、對沖基金槓桿（dealer-funding）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`。預算有限（總花費上限 2 美元），不要做不必要的探索：每個來源最多嘗試 3 種做法，抓不到就寫進報告和 task.blocked，其餘照常完成。**先把最容易的來源做完並寫出 CSV，再做下一個**，避免預算用完時什麼都沒有。

## 目標
取得三類公開資料，影片只有敘述沒有數字，我們要補上可以檢驗的資料：
- F1：一級交易商（Primary Dealer）的融資與部位，來源紐約 Fed Primary Dealer Statistics（Markets API：`https://markets.newyorkfed.org/api/pd/...`，週頻）。要含：附買回（repo）與附賣回（reverse repo）融資、美債淨部位。
- F2：回購折扣率（haircut）。優先找金融研究辦公室 OFR（`https://data.financialresearch.gov/v1/`，API 公開，先查 `/metadata/mnemonics` 或搜尋含 haircut、repo 的系列），其次 NY Fed 或 SEC 公開資料。沒有逐日資料就取得最細的頻率。
- F4：對沖基金槓桿（Form PF，季頻且落後）。優先 OFR Hedge Fund Monitor（同一個 OFR API，系列名稱含 FPF、leverage、gross/net asset value 等），其次 SEC Private Funds Statistics。要含：總槓桿、借款（含回購）占淨資產比等可得的槓桿系列，以及 Treasury 相關的曝險系列（若有）。

## 產出
任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/dealer-funding/`

三個 CSV，統一長表格式，主鍵 (`date`, `series_key`)，依 date、series_key 升冪，UTF-8：
`date,series_key,description,value,unit`
- `pd_financing.csv`（F1）：`date` 是資料所屬的週日期，週頻，2018-01 到最新。
- `repo_haircuts.csv`（F2）：2018 到最新（有多早算多早，寫進報告）。
- `hedge_fund_leverage.csv`（F4）：季頻，2018 到最新（最新通常落後半年到一年，寫進報告）。
- `description` 用來源給的名稱，`unit` 照來源（百萬美元、%、倍數等），不要換算。
- 不要為了湊數把整個資料集全抓；選與主題相關的系列，在報告列出「選了哪些、沒選哪些及原因」。

另外：`fetch.py`（可重跑，`--start`）、`raw/`、`report.md`（依 _common.md 的必備章節；報告要列出每個 CSV 的 series_key 清單與最新值）。

## 驗收
`verify.py dealer-funding`
