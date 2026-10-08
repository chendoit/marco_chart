# 交件：指派文件：工務店倒產、建築成本與法規變化的數據來源調研＋實測

- 任務：`jp-builders-cost`（專案 jp-realestate-c，readonly）
- 完成時間：2026-10-08T15:36:46+08:00
- 執行：agy:gemini-3.8-flash-high，第 3 次嘗試，tokens 961972
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-builders-cost` → pass
- reviewer：未啟用

## 摘要

已完成工務店倒產、建築成本與法規變化數據來源調研與實測，驗收腳本 verify_wp.py jp-builders-cost 完全通過（7 個 samples 檔案皆包含 2025-06 以後最新數據）。完成詳細調研報告、來源清單及可重複執行之抓取腳本 probe_builders_cost.py。

## 檔案產出

- `probe_builders_cost.py`（24,620 bytes，sha256 `ebc3d5ded166…`）
- `report.md`（25,602 bytes，sha256 `f1de9126e099…`）
- `samples/bankruptcy_construction_monthly.csv`（1,359 bytes，sha256 `4996bd08f50c…`）
- `samples/boj_ppi_building_materials.csv`（4,943 bytes，sha256 `16d5712bf854…`）
- `samples/contractors_licensed_annual.csv`（689 bytes，sha256 `7a69e4e51d3b…`）
- `samples/deflator_construction_cost.csv`（5,099 bytes，sha256 `49e3b2ad26ff…`）
- `samples/labor_shortage_rate_monthly.csv`（1,789 bytes，sha256 `8b3a44a88ff4…`）
- `samples/maff_timber_prices.csv`（1,120 bytes，sha256 `cd5bbbd6f8ef…`）
- `samples/policy_timeline.csv`（4,433 bytes，sha256 `429a89edff05…`）
- `sources.csv`（4,128 bytes，sha256 `72deb57cc2ac…`）

## 收件

```
taskq accept jp-builders-cost
```

退件：`taskq reject jp-builders-cost --reason "..."`
