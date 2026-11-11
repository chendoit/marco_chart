# 任務：抓美債期貨 TFF 部位（cftc-treasury）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標

取得基差交易的公開代理資料：美債期貨槓桿基金部位。做到下列 6 個合約都有 2018-01-02 以前至 2026-11-03 的週資料，且通過 verify.py，就算完成。

## 合約（contract 欄照寫）

| contract | 商品 | CFTC 代碼（要到資料內確認商品名稱） |
|---|---|---|
| `2Y` | 2-Year T-Note | 042601 |
| `5Y` | 5-Year T-Note | 044601 |
| `10Y` | 10-Year T-Note | 043602 |
| `ULTRA10Y` | Ultra 10-Year T-Note | 043607 |
| `TBOND` | U.S. Treasury Bond | 020601 |
| `ULTRABOND` | Ultra U.S. Treasury Bond | 020604 |

代碼不符時，改用資料內正確的代碼，並寫進報告。

## 產出

任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/cftc-treasury/`

`cftc_treasury_tff.csv`，長表，主鍵 (contract, date)，先依 contract、再依 date 升冪，欄位順序固定，單位都是口數：

`date,contract,open_interest,lev_long,lev_short,lev_net,asset_mgr_long,asset_mgr_short,dealer_long,dealer_short`

- 使用 Traders in Financial Futures 的 **Futures Only** 報告，不要用 Combined。
- `date` 是報告日（通常週二），不是公布日。
- `lev_net = lev_long - lev_short`，這是唯一的衍生欄位。

## 參考

`C:/code/2025-12-05-MacroMicro-Data/get_aud_nzd_series.py` 第 200 行附近的 TFF 欄位對應與抓法（CFTC Public Reporting）。

## 驗收

`verify.py cftc-treasury`
