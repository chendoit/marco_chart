# 任務：紐約 Fed 常備回購機制（SRF）用量與利率（nyfed-srf）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標
取得 E1（SRF 用量）與 E2（SRF 利率）。完成條件：兩個 CSV 都產出且通過 verify.py。

## 產出
任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/nyfed-srf/`

1. `srf_usage.csv`：每個營業日一列，主鍵 `date`，欄位順序固定，金額單位十億美元：
   `date,ops_count,submitted_bn,accepted_bn,accepted_treasury_bn,accepted_agency_bn,accepted_mbs_bn,min_bid_rate`
   - 起 2021-07（SRF 成立後）至 2026-11-06。同一天有多場操作時加總金額，`ops_count` 為場數，`min_bid_rate` 取該日最高值。
   - 來源優先：紐約 Fed Markets API（`https://markets.newyorkfed.org/api/rp/...`，用 repo 操作結果、standing repo／term 以來源欄位判斷）。確認哪些操作屬 SRF，在報告寫明篩選條件。
   - 用量為 0 的日子也要有列（來源有列才算，來源沒列就不補，寫進缺口）。
2. `srf_rate.csv`：每個日曆營業日一列，主鍵 `date`，欄位：`date,target_upper,srf_min_bid_rate`
   - `target_upper`：聯邦資金利率目標區間上限（FRED `DFEDTARU`），2018-01-02 起至 2026-11-06。
   - `srf_min_bid_rate`：來源有明確公布的 SRF 最低投標利率就填（可由 srf_usage 的 min_bid_rate 對齊，或 Fed 公告）；沒有就留空，不要用 target_upper 代填。在報告寫明 SRF 利率和目標區間上限的關係（是否相等）以及調整歷史。

## 驗收
`verify.py nyfed-srf`
