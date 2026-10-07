# 交件：指派文件：逐條查證鋁市場論點＋ Alcoa／Century 財務敏感度

- 任務：`al-claims-companies`（專案 aluminum-c，readonly）
- 完成時間：2026-10-07T17:34:18+08:00
- 執行：agy:gemini-3.8-flash-high，第 2 次嘗試，tokens 862698
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-claims-companies` → pass
- reviewer：未啟用

## 摘要

已完成鋁市場 10 條論點之逐條嚴謹查證與出處溯源，並量化拆解 Alcoa 與 Century 之財務敏感度。透過 SEC EDGAR API 與 Yahoo Finance 實測抓取兩家公司 10 年季度財務及日股價資料，產出完整合規之 claims.csv、sources.csv、report.md、probe 腳本與樣本數據。機械驗收腳本 verify_wp.py 驗證通過（PASS），所有工作成果均符規範。

## 檔案產出

- `claims.csv`（6,737 bytes，sha256 `dc3de7a992f9…`）
- `probe_al_companies.py`（7,193 bytes，sha256 `71913ed81b73…`）
- `report.md`（26,402 bytes，sha256 `3fec27dd7396…`）
- `samples/aa_daily.csv`（234,652 bytes，sha256 `190592de7415…`）
- `samples/aa_quarterly.csv`（3,078 bytes，sha256 `79d064184e38…`）
- `samples/cenx_daily.csv`（228,130 bytes，sha256 `bcfe9521f690…`）
- `samples/cenx_quarterly.csv`（3,132 bytes，sha256 `f271a74fd2ff…`）
- `sources.csv`（2,088 bytes，sha256 `b2ead3f42a15…`）

## 收件

```
taskq accept al-claims-companies
```

退件：`taskq reject al-claims-companies --reason "..."`
