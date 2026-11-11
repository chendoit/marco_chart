# 任務：用 TradingView 取得 GLD 1 分鐘線（tv-gld-1m）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`。**例外**：本任務需要 TradingView，不可只用 Yahoo；`fetch.py` 的 `--start` 參數改為 `--from-date`。

## 目標
取得 G4 需要的 GLD 日內資料：2026-10-29 到 2026-11-06 的 1 分鐘 K 線，重點是 2026-10-30 全天。

## 做法（TradingView Desktop 已開，CDP 9222 已就緒）
- 專案：`C:/code/2026-04-05-tradingview-control`。先讀它的 `tv_client.py` 與 `tv_daily_export.py`（用 Grep 找 `set_symbol`、`set_timeframe`、`ohlcv`、`scroll_to_date`、`set_range`，不要整檔讀），照它的 Python wrapper 用法呼叫；用該專案的 venv：`C:/code/2026-04-05-tradingview-control/venv/Scripts/python.exe`。你的腳本放在本任務資料夾，用 sys.path 或 subprocess 引用 `tv_client`。
- **不可**啟動、重啟或關閉 TradingView，不要加入或移除指標、不要改任何檔案（該專案內一律唯讀）。
- 開始前用 `state()` 記下目前圖表的 symbol 與 timeframe；結束時（含失敗時）一定要用 `set_symbol`、`set_timeframe` 還原。
- 商品 `AMEX:GLD`（用 `search_symbol` 確認 exchange 前綴；寫進報告）。timeframe 1 分鐘（`1`）。要確認取得的 bars 涵蓋 2026-10-29～11-06；不夠時用 `scroll_to_date`／`set_range` 分段取、合併、去重。
- 切換後等待圖表載入（參考專案內的 settle 秒數）。
- 比對：同日 Yahoo 日線 close（`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/market-prices/market_prices.csv` 的 GLD）與你取得的當日最後一根 1 分鐘 close，差異要寫進報告。

## 產出
任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/tv-gld-1m/`
`gld_1m.csv`，主鍵 (`date`, `time_et`)，升冪，欄位：
`date,time_et,open,high,low,close,volume`
- `date`：美東日期；`time_et`：美東時間 HH:MM（K 線開始時間）。TradingView 時間戳是 UTC epoch，要換成美東（2026-11-01 之前為 EDT，之後為 EST，用 zoneinfo America/New_York）。
- 盤前盤後的 K 線有就保留，並在報告說明 TradingView 圖表是否包含延長時段。

## 驗收
`verify.py tv-gld-1m`。報告另外要列出 2026-10-30 的：第一根與最後一根、日高低點與時間、09:30、10:00、10:30、11:00、12:00、13:00、14:00、15:00、15:45、16:00 各時點的 close。
