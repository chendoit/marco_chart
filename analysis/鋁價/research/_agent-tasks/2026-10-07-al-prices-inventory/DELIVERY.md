# 交件：指派文件：鋁價、期限結構與庫存的數據來源調研＋實測

- 任務：`al-prices-inventory`（專案 aluminum-b，readonly）
- 完成時間：2026-10-07T17:02:13+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 633738
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-prices-inventory` → pass
- reviewer：未啟用

## 摘要

完成鋁價、期限結構與庫存數據來源調研與實測，確認 LME 最新庫存 238,875 噸為近 25 年歷史最低，Cash-3M 當前呈 -14 USD/t Contango 狀態。成功實測並產出 20 項序列、8 份樣本資料集與完整探測腳本，驗證程序已機械驗收通過。

## 檔案產出

- `probe_al_prices_inventory.py`（12,605 bytes，sha256 `fe75385bfd90…`）
- `report.md`（22,711 bytes，sha256 `f74196d2ca8b…`）
- `samples/comex_al_futures_daily.csv`（109,356 bytes，sha256 `6255792c8870…`）
- `samples/comex_al_stocks_snapshot.csv`（97 bytes，sha256 `e72b7b83b09c…`）
- `samples/fred_al_prices_monthly.csv`（16,755 bytes，sha256 `ffff9e01b534…`）
- `samples/lme_al_prices_daily.csv`（147,606 bytes，sha256 `e3449d03dddf…`）
- `samples/lme_al_stock_daily.csv`（101,214 bytes，sha256 `52660c326954…`）
- `samples/shfe_al_futures_daily.csv`（266,540 bytes，sha256 `2c5475ec99ab…`）
- `samples/shfe_al_warrant_daily.csv`（1,981 bytes，sha256 `51611a63fd46…`）
- `samples/shfe_ao_futures_daily.csv`（37,375 bytes，sha256 `ad8d1bdca70a…`）
- `samples/yahoo_al_equities_daily.csv`（169,298 bytes，sha256 `9e86bb6a8c39…`）
- `sources.csv`（4,586 bytes，sha256 `7d9c1b23ea27…`）

## 收件

```
taskq accept al-prices-inventory
```

退件：`taskq reject al-prices-inventory --reason "..."`
