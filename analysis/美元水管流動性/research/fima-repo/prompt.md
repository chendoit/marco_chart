# 任務：Fed FIMA 回購機制用量（fima-repo）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標
取得 E3：Fed 對外國官方機構（FIMA）的附買回協議餘額，週資料。

## 產出
任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/fima-repo/`

`fima_repo.csv`，主鍵 `date`，每個週三一列，單位百萬美元：
`date,fima_repo_wed,fima_repo_wavg`
- `fima_repo_wed`：H.4.1「Repurchase agreements – Foreign official」週三水位；`fima_repo_wavg`：週平均。
- 來源優先 FRED（`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<代碼>`，免 key）。代碼自行確認（可到 FRED 搜尋「Repurchase Agreements: Foreign Official」；參考 `C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/fed-balance-sheet/fetch.py` 的抓法）。要在報告寫明代碼與系列標題。
- 2018-01-03 以前到 2026-11-04（週三）。FIMA 沒動用時值為 0，要保留為 0，不要當缺值。
- 另外在報告列出：2026-09 到 2026-11-04 逐週的值，以及歷史上最大值與日期。

## 驗收
`verify.py fima-repo`
