# 交件：指派文件：日本住宅著工、建築確認與長期需求的數據來源調研＋實測

- 任務：`jp-housing-starts`（專案 jp-realestate-a，readonly）
- 完成時間：2026-10-08T15:13:53+08:00
- 執行：agy:gemini-3.8-flash-high，第 3 次嘗試，tokens 628318
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-housing-starts` → pass
- reviewer：未啟用

## 摘要

已完成日本住宅著工、建築確認與長期需求之數據來源調研與實測，驗證2025年著工74萬戶創62年新低且持家跌幅重於建売。產出report.md、sources.csv、probe腳本與7個高規格樣本CSV，機械驗收verify_wp已通過。

## 檔案產出

- `probe_jp_housing_starts.py`（19,005 bytes，sha256 `bbee82512991…`）
- `report.md`（23,011 bytes，sha256 `5480ad2c3f35…`）
- `samples/building_confirmations_semimonthly.csv`（854 bytes，sha256 `395108a096bf…`）
- `samples/nri_housing_forecast_history.csv`（464 bytes，sha256 `65f4918a1234…`）
- `samples/starts_annual_history.csv`（6,592 bytes，sha256 `59a836b7ee04…`）
- `samples/starts_monthly_shutoken.csv`（12,304 bytes，sha256 `658a47d88dbc…`）
- `samples/starts_monthly_structure_method.csv`（9,442 bytes，sha256 `38c2a4d009ef…`）
- `samples/starts_monthly_use.csv`（61,893 bytes，sha256 `63064ef60705…`）
- `samples/vacant_houses_5y_history.csv`（462 bytes，sha256 `fc736e7d4434…`）
- `sources.csv`（6,805 bytes，sha256 `306b16143ff1…`）

## 收件

```
taskq accept jp-housing-starts
```

退件：`taskq reject jp-housing-starts --reason "..."`
