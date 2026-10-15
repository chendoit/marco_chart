# 交件：指派文件：日本國交省「不動產資訊庫 API」（reinfolib）能做什麼

- 任務：`mlit-api-survey`（專案 _ws，readonly）
- 完成時間：2026-10-15T11:17:21+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 600704
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py` → pass
- reviewer：未啟用

## 摘要

已完成日本國土交通省不動產資訊庫 35 支 API 完整規格調研與 12 支核心端點實測，產出逾 4 萬字繁中分析報告與近 5 年東京都季度房價彙總數據，並通過 verify_wp.py 驗收且無金鑰外洩。

## 檔案產出

- `endpoints.csv`（13,296 bytes，sha256 `f3ee4e932d2c…`）
- `probe_mlit.py`（7,619 bytes，sha256 `a0324054b147…`）
- `report.md`（41,115 bytes，sha256 `880cd42cf756…`）
- `samples/sample_xct001_appraisal_reports.json`（1,403,588 bytes，sha256 `6ded079c8e4c…`）
- `samples/sample_xgt001_evacuation_sites.geojson`（94,691 bytes，sha256 `259ad4c5110c…`）
- `samples/sample_xit001_trade_prices.json`（127,836 bytes，sha256 `bfe21fbb72f0…`）
- `samples/sample_xit002_municipalities.json`（4,132 bytes，sha256 `53f503c3bef6…`）
- `samples/sample_xkt001_city_planning_areas.geojson`（9,274 bytes，sha256 `88f2232bee9e…`）
- `samples/sample_xkt002_use_areas.geojson`（20,120 bytes，sha256 `28372edee42d…`）
- `samples/sample_xkt013_future_population_mesh.geojson`（52,896 bytes，sha256 `2e8e21d41a45…`）
- `samples/sample_xkt015_station_ridership.geojson`（10,680 bytes，sha256 `796775553fa5…`）
- `samples/sample_xkt026_flood_risk.geojson`（273,504 bytes，sha256 `4849dab64733…`）
- `samples/sample_xpt001_trade_points.geojson`（257,894 bytes，sha256 `7edb70821c01…`）
- `samples/sample_xpt002_land_price_points.geojson`（34,096 bytes，sha256 `d2038491f2ce…`）
- `samples/sample_xst001_disaster_history.geojson`（14,239 bytes，sha256 `4f28d9cf44b2…`）
- `samples/trade_quarterly_summary.csv`（2,356 bytes，sha256 `f57088e17eff…`）

## 派工脈絡（handoff）

- 為什麼派：想知道國交省 reinfolib API 能提供哪些資料，需上網讀文件並實測多支端點，耗時且唯讀
- 依據的計畫 / worknote：
  - `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\wp\WP-mlit-api-survey.md`
- 收件後的下一步：
  - 寫 WN 彙整 API 能力，評估可做的日本地產指標，必要時再派第二輪追問

## 收件

```
taskq accept mlit-api-survey
```

退件：`taskq reject mlit-api-survey --reason "..."`
