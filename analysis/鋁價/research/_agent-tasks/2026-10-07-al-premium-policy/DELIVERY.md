# 交件：指派文件：鋁區域溢價、政策時間線、部位與能源成本的數據調研＋實測

- 任務：`al-premium-policy`（專案 aluminum-b，readonly）
- 完成時間：2026-10-07T17:18:15+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 470542
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-premium-policy` → pass
- reviewer：未啟用

## 摘要

已完成鋁區域溢價、政策時間線、部位與能源成本之全面調研與實測，產出20個序列來源清單與9組樣本資料。成功實測CME美歐溢價期貨、CFTC與LME部位報表、MISO與德國電價，並建立2018-2026年完整政策時間線。所有驗收指標均已通過驗證腳本檢驗。

## 檔案產出

- `probe_premium_policy.py`（24,971 bytes，sha256 `86a27a973bc6…`）
- `report.md`（21,098 bytes，sha256 `7b979e0f0847…`）
- `samples/cftc_aluminum_cot_legacy.csv`（85,953 bytes，sha256 `68120591ebc5…`）
- `samples/cme_aluminum_futures.csv`（27,427 bytes，sha256 `8ba0397bc656…`）
- `samples/european_dutypaid_premium_cme.csv`（26,181 bytes，sha256 `11e68c362368…`）
- `samples/german_power_dayahead.csv`（1,302 bytes，sha256 `670ceee399e7…`）
- `samples/miso_indiana_hub_lmp.csv`（712 bytes，sha256 `63729f0b9b50…`）
- `samples/mjp_quarterly_premium.csv`（1,524 bytes，sha256 `67511b57fd98…`）
- `samples/policy_timeline.csv`（8,027 bytes，sha256 `90fb17d86424…`）
- `samples/ttf_gas_daily.csv`（28,565 bytes，sha256 `fb079f9df497…`）
- `samples/us_midwest_premium_cme.csv`（26,216 bytes，sha256 `0fd90b72235a…`）
- `sources.csv`（5,238 bytes，sha256 `698f91bb1632…`）

## 收件

```
taskq accept al-premium-policy
```

退件：`taskq reject al-premium-policy --reason "..."`
