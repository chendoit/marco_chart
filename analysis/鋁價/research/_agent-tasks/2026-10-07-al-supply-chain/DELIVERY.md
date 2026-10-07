# 交件：指派文件：鋁產業鏈供給（鋁土礦→氧化鋁→原鋁）與貿易流的數據調研＋實測

- 任務：`al-supply-chain`（專案 aluminum-a，readonly）
- 完成時間：2026-10-07T17:32:09+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 981631
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-supply-chain` → pass
- reviewer：未啟用

## 摘要

完成鋁產業鏈供給與貿易流數據調研，實測突破 IAI、NBS(DBnomics)、SHFE 及 UN Comtrade 等來源。確認中國原鋁近12個月產量達4494萬噸（距4500萬噸上限僅差6萬噸），幾內亞鋁土礦進口占比升至70%以上並推算出CIF均價。產出合規報告、來源表、9個樣本檔與可重跑probe腳本，機械驗收全數通過。

## 檔案產出

- `probe_supply_chain.py`（11,428 bytes，sha256 `2b18c0aff800…`）
- `report.md`（19,797 bytes，sha256 `c174ffd9049a…`）
- `samples/china_bauxite_import_guinea_cif.csv`（581 bytes，sha256 `f902f2314525…`）
- `samples/iai_alumina_production_china.csv`（19,361 bytes，sha256 `d376a9e9a0ae…`）
- `samples/iai_alumina_production_global.csv`（32,413 bytes，sha256 `43a237de5102…`）
- `samples/iai_primary_aluminium_production_china.csv`（19,700 bytes，sha256 `b4615697b852…`）
- `samples/iai_primary_aluminium_production_global.csv`（31,257 bytes，sha256 `c379f66ccd76…`）
- `samples/nbs_china_alumina_monthly.csv`（519 bytes，sha256 `26af212b99d6…`）
- `samples/nbs_china_electrolytic_aluminum_monthly.csv`（471 bytes，sha256 `1713e93237b3…`）
- `samples/shfe_alumina_futures_ao.csv`（56,239 bytes，sha256 `67742ca97b42…`）
- `samples/shfe_aluminium_futures_al.csv`（391,279 bytes，sha256 `fbf2628c77d7…`）
- `sources.csv`（5,068 bytes，sha256 `b19dcbaa5c0b…`）

## 收件

```
taskq accept al-supply-chain
```

退件：`taskq reject al-supply-chain --reason "..."`
