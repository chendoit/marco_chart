# 交件：指派文件：reinfolib API 第二輪——資料落後期、地價取得、指數對照與屋齡控制

- 任務：`mlit-api-survey-2`（專案 _ws2，readonly）
- 完成時間：2026-10-15T11:51:24+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 404939
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py` → pass
- reviewer：未啟用

## 摘要

已完成 reinfolib API 第二輪調查，釐清成交申報落後期（2026Q1 僅七成應標暫定），確認公示地價以國土數值情報 L01 整檔下載為最佳解；完成官方指數對照（相關性 0.9782）與屋齡固定權重控制（證實第一輪 +28.6% 漲幅反被老化低估 8 個百分點），並提出 38 分鐘抓完 22 年全國 580 萬筆的年×縣最佳架構。

## 檔案產出

- `probe_mlit2.py`（15,757 bytes，sha256 `77a0cead0328…`）
- `report.md`（33,941 bytes，sha256 `6258397bde67…`）
- `samples/age_controlled_tokyo_condo.csv`（2,651 bytes，sha256 `19b953c64af5…`）
- `samples/index_comparison.csv`（742 bytes，sha256 `e1ffc40df98d…`）
- `samples/official_price_index_housing.xlsx`（859,366 bytes，sha256 `76ad3577bd28…`）
- `samples/rate_limit_probe_5.json`（348 bytes，sha256 `1ac7f28d985c…`）
- `samples/request_budget.csv`（954 bytes，sha256 `c18a7accce1a…`）
- `samples/sample_l01_land_price_tokyo_2023.geojson`（139,731 bytes，sha256 `e5deda4a4023…`）
- `samples/xct001_divisions_tokyo_2024.json`（830 bytes，sha256 `7425f21259c0…`）
- `samples/xit001_quarter_counts.csv`（546 bytes，sha256 `fd6d59e25f6b…`）

## 派工脈絡（handoff）

- 為什麼派：第一輪調研留下 5 個未解疑問（資料落後期、地價全國取得、與官方指數對照、屋齡控制、請求量），需上網與實測
- 依據的計畫 / worknote：
  - `C:\code\2025-12-05-MacroMicro-Data\WN-2026-10-15-MLIT不動產資訊庫API能力調查.md`
- 收件後的下一步：
  - 更新 WN 或另寫補充 WN，決定是否寫正式抓取腳本並上線東京／大阪／愛知中古公寓序列

## 收件

```
taskq accept mlit-api-survey-2
```

退件：`taskq reject mlit-api-survey-2 --reason "..."`
