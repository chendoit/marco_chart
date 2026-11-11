# 任務：財政部國債回購（buyback）與標售結算規模（treasury-ops）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標
取得 E5：美債 buyback 操作結果與標售發行規模。

## 產出
任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/treasury-ops/`

1. `treasury_buybacks.csv`，主鍵 (`date`, `bucket`)，單位十億美元面額：
   `date,settle_date,bucket,par_submitted_bn,par_accepted_bn`
   - `date`：操作日；`bucket`：年期區間或證券類別（照來源）。
   - 來源優先財政部 Buyback 結果頁（`home.treasury.gov` 的 Buybacks）或紐約 Fed 的 buyback 操作資料（Markets API）。2024-05 起至最新。
2. `auction_settlements.csv`，主鍵 `cusip`，依 `date` 升冪：
   `date,auction_date,security_type,security_term,cusip,offering_amount_bn`
   - `date`：發行（結算）日；`security_type`：Bill/Note/Bond/FRN/TIPS 照 TreasuryDirect 欄位；`offering_amount_bn`：公布發行金額，單位十億美元。
   - 來源：TreasuryDirect 公開 API（`https://www.treasurydirect.gov/TA_WS/securities/search`，JSON）。2023-01-01 起至 2026-11-06 的發行日。注意分頁與日期區間限制，要分段抓。
   - 另外在報告列出：2026-10 與 2026-11 的 2 年期、5 年期票據標售日期、發行日與金額。

## 驗收
`verify.py treasury-ops`
