# 交件：指派文件：大繼承時代與不動產節稅商品（令和 8 年度稅制改正查證＋繼承稅統計）的調研＋實測

- 任務：`jp-inheritance-tax`（專案 jp-realestate-h，readonly）
- 完成時間：2026-10-08T17:29:25+08:00
- 執行：agy:gemini-3.8-flash-high，第 4 次嘗試，tokens 497373
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-inheritance-tax` → pass
- reviewer：未啟用

## 摘要

已完成令和8年度稅改對不動產小口化商品評價之查證，確認舊文件商業NK避風港論點已過時。成功抓取國稅廳2010-2024年繼承稅申報長歷史與厚勞省至2026年7月之死亡數月度序列，相關樣本作與抓取程式皆已交付。所有驗收指標均通過 verify_wp.py 機械檢驗。

## 檔案產出

- `claims.csv`（5,901 bytes，sha256 `91ed164dc830…`）
- `probe_inheritance_tax.py`（11,177 bytes，sha256 `d1146c597fe1…`）
- `report.md`（20,515 bytes，sha256 `a815b9946a05…`）
- `samples/jp_deaths_annual.csv`（2,643 bytes，sha256 `ca669a4a0183…`）
- `samples/jp_deaths_monthly.csv`（1,692 bytes，sha256 `19145ebb2726…`）
- `samples/jp_inheritance_tax_annual.csv`（1,440 bytes，sha256 `b67086e92e2f…`）
- `sources.csv`（3,314 bytes，sha256 `bc012a617b96…`）

## 收件

```
taskq accept jp-inheritance-tax
```

退件：`taskq reject jp-inheritance-tax --reason "..."`
