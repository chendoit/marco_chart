# 交件：指派文件：營建供給受限與公共投資先行指標（前払保証、受注、水泥／生コン、就業者）的數據來源調研＋實測

- 任務：`jp-public-works`（專案 jp-realestate-i，readonly）
- 完成時間：2026-10-08T17:34:30+08:00
- 執行：agy:gemini-3.8-flash-high，第 3 次嘗試，tokens 648335
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-public-works` → pass
- reviewer：未啟用

## 摘要

已完成日本營建供給受限與公共投資先行指標的調研與實測，產出7組高質量樣本數據與可重跑探測腳本。機械驗收verify_wp.py jp-public-works通過，包含前払保証、建設受注、水泥/生コン、建機、勞動力結構及預鑄三家財務數據。所有核實事項（2023水泥需求3458萬噸、軀體工事求人倍率超6、就業者年齡結構等）皆已查證完畢。

## 檔案產出

- `probe_public_works.py`（5,068 bytes，sha256 `fb397b93aebb…`）
- `report.md`（24,944 bytes，sha256 `f39077cfbcb2…`）
- `samples/advance_payment_guarantee_monthly.csv`（1,964 bytes，sha256 `7d7c5bd6ec73…`）
- `samples/cement_and_concrete_annual_trend.csv`（419 bytes，sha256 `ee54875707c5…`）
- `samples/construction_job_openings_ratio_monthly.csv`（920 bytes，sha256 `540866cf4990…`）
- `samples/construction_machinery_shipment_monthly.csv`（1,282 bytes，sha256 `44370ec9399b…`）
- `samples/construction_orders_50_firms_monthly.csv`（1,126 bytes，sha256 `d07c343d152d…`）
- `samples/precast_companies_quarterly.csv`（511 bytes，sha256 `d563d169e72a…`）
- `samples/ready_mixed_concrete_shipment_monthly.csv`（1,764 bytes，sha256 `94e0c5c0e8ab…`）
- `sources.csv`（5,383 bytes，sha256 `04dfc010a49c…`）

## 收件

```
taskq accept jp-public-works
```

退件：`taskq reject jp-public-works --reason "..."`
