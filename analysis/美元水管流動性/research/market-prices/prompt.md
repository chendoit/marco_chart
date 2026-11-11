# 任務：抓跨資產日線 OHLCV（market-prices）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標

取得驗證「股金同跌」所需的跨資產日線，讓後續能計算 2018 年至今每個交易日的跌幅、RSP 相對 SPY 表現和黃金回歸殘差。做到下列 13 檔都有 2018-01-02 以前至 2026-11-06 的完整日線，且通過 verify.py，就算完成。

## 標的（ticker 欄照寫）

`^GSPC`、`^DJI`、`^SOX`、`^NDX`、`QQQ`、`SPY`、`RSP`、`INTC`、`GLD`、`GC=F`、`SI=F`、`DX-Y.NYB`、`BTC-USD`

## 產出

任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/market-prices/`

`market_prices.csv`，長表，主鍵 (ticker, date)，先依 ticker、再依 date 升冪，欄位順序固定：

`date,ticker,open,high,low,close,adj_close,volume`

- `close` 是未還原收盤價，`adj_close` 是還原價；來源沒有還原價（指數、期貨）時留空。
- 抓來源能提供的最早日期。
- 只保留已收盤的交易日，最新到 2026-11-06。不要收 2026-11-07 之後的列（BTC-USD 例外，可收到 2026-11-08）。

## 參考

`C:/code/2025-12-05-MacroMicro-Data/get_yfinance_series.py` 的 `_yf_chart`（Yahoo chart API）。該檔開頭註解說明 Yahoo 對部分 ticker 的回溯範圍問題，先讀那段。yfinance 套件已在 venv，可用。

## 驗收

`verify.py market-prices`
