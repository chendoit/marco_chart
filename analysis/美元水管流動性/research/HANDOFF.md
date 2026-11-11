# 交接：收件 3 個 Haiku worker 的資料抓取

使用者會和你（Sonnet）一起工作，收件結果直接向使用者回報。全程用繁體中文。

## 背景

- 工作筆記：`C:/code/2025-12-05-MacroMicro-Data/WN-2026-11-09-美元水管流動性擠壓-邏輯鏈與指標拆解.md`。先讀「補齊待查指標」和「核對結果」兩節，其他段落需要時再讀。
- 共通規則：`research/_common.md`
- 驗收腳本：`research/verify.py <name>`，最後一行要是 `PASS <name>`。
- Python：`C:/code/2025-12-05-MacroMicro-Data/venv/Scripts/python.exe`，執行時設 `PYTHONUTF8=1`。

以下相對路徑都以 `C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/` 為根目錄。

## Worker 狀態（交接當下仍視為執行中，尚未收件）

| Worker | 資料夾 | Orca handle | 產出 |
|---|---|---|---|
| market-prices | `research/market-prices/` | `term_3f26ed79-85e4-4e5d-9a7f-a705ec746b39` | `market_prices.csv` |
| fed-balance-sheet | `research/fed-balance-sheet/` | `term_7fdf60b1-5a7e-4a54-81d9-347cb3747a3b` | `fed_balance.csv` |
| cftc-treasury | `research/cftc-treasury/` | `term_06334203-0fe8-4835-a6c8-d1638c695e27` | `cftc_treasury_tff.csv` |

每個 worker 都是 headless：`claude -p --model haiku`，輸出到各自的 `out.json`，上限 `--max-budget-usd 2`。結束後終端會自己關掉。

## 收件步驟

1. 等待結束：`orca terminal wait --terminal <handle> --for exit --timeout-ms 580000 --json`，要看 `result.wait.satisfied`，逾時也會印出正常 JSON。handle 失效時用 `orca terminal list` 確認。
2. 讀 `out.json` 的 `is_error`、`result`、`session_id`、`total_cost_usd`，並確認有 `task.done`。有 `task.blocked` 就讀原因。
3. **自己重跑** `verify.py <name>`，不要只信 worker 的回報。
4. 讀 `report.md`，確認必備章節都在，並看「缺口與異常」。
5. `git status --short` 檢查 worker 有沒有寫到自己資料夾以外的地方。
6. 不合格時用 `claude -p --resume <session_id> --model haiku --dangerously-skip-permissions --output-format json "<修正要求>"` 交回原 worker，不要另開新 worker，也不要默默自己補資料。

## 已知風險

- `verify.py` 是交接前剛寫的，**還沒實際跑過**。如果判定失敗，先分辨是資料有問題還是腳本有問題；腳本有錯就修腳本，並告訴使用者改了什麼。
- 預算上限可能讓 worker 中途停止，此時 `is_error` 可能為 true，且沒有 `task.done`。
- 本地 `series_7449` 的口徑還沒確認，要看 fed-balance-sheet 的報告。

## 收件後要做

1. 更新 WN 的「執行結果」，取代目前的「進行中」：每個 worker 的結果、列數、起訖日、花費和缺口。
2. 更新 WN 指標表的「本地」欄，把已取得的項目從待查改掉。盤點已確認本地有的項目也一起改（見「本地盤點結果」）。
3. 用新資料核對影片數字並寫進 WN「核對結果」，分清相符與不符：
   - 10/30 當日：INTC、^SOX、QQQ、^GSPC、RSP、GLD、白銀、BTC、DXY。
   - 10/28 準備金 2.89 兆、一週減 743 億；10/29 TGA 1.04 兆（`data/series_29123.pkl`）。
   - 8 月中到 10 月中 T-bill 持有量是否停止增加（RMP 暫停的說法）。
   - 11/3 利差 +7bp 前後的股市表現（WN 的樣本外測試）。

## 範圍

- 回測（利差、股金同跌）和「缺」指標（E 組、F1、F2、F4、G4）不在這輪，要做先問使用者。
- 不要改 `data/`、`get_*.py`、`flask_highcharts/`。
- commit 或 push 要等使用者開口。
- `.claude/` 和 `analysis/台股落底訊號/` 的未追蹤檔案與這項工作無關，不要動。

## 開始

讀完後先確認 3 個 worker 的狀態，用幾句話告訴使用者目前進度，然後開始收件。
