# 任務：抓 Fed 準備金與短債持有量（fed-balance-sheet）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標

取得驗證「準備金告急」和「RMP 暫停」所需的 H.4.1 週資料，並查明本地 `data/series_7449.pkl`（標題 us-fed-excess-reserves-weekly）是哪種口徑。做到四個欄位都有 2018-01-03 以前至 2026-11-04 的週資料、通過 verify.py，且 report.md 寫明下列兩個事實，就算完成。

## 產出

任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/fed-balance-sheet/`

`fed_balance.csv`，主鍵 date（週三），欄位順序固定，單位都是百萬美元：

`date,reserves_wed,reserves_wavg,bills_wed,treasuries_wed`

| 欄位 | 內容 | FRED 代碼（要到 FRED 系列頁確認標題） |
|---|---|---|
| `reserves_wed` | 準備金，週三水位 | `WRBWFRBL` |
| `reserves_wavg` | 準備金，週平均 | `WRESBAL` |
| `bills_wed` | Fed 持有 T-bill，週三水位 | `WSHOBL` |
| `treasuries_wed` | Fed 持有美債合計，週三水位 | `TREAST` |

代碼或單位不符時，改用 FRED 或 H.4.1 上正確的系列，並寫進報告。來源單位是十億美元時要換算成百萬美元，並記錄換算。

## report.md 必須另外寫明的事實

1. `series_7449` 較接近 `reserves_wed` 還是 `reserves_wavg`，附 verify.py 印出的差異。
2. 2026-10-28 的 `reserves_wed`、`reserves_wavg`，以及與前一週的差額。只列數字，不評論。

## 參考

`C:/code/2025-12-05-MacroMicro-Data/get_fred_csv.py` 的 FRED CSV 抓法。

## 驗收

`verify.py fed-balance-sheet`
