# 交件：指派文件：逐條查證日本地產論點＋飯田 GHD／Open House 等上市公司數據

- 任務：`jp-claims-companies`（專案 jp-realestate-d，readonly）
- 完成時間：2026-10-08T15:07:53+08:00
- 執行：agy:gemini-3.8-flash-high，第 3 次嘗試，tokens 1225405
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-claims-companies` → pass
- reviewer：未啟用

## 摘要

已逐條查證日本地產 15 項論點並核對官方決算與統計出處；實測抓取 10 檔日股 10 年歷史日資料、飯田與 Open House 近 5 年季度業績及 BIS 利率；全數通過 verify_wp.py 機械驗收。

## 檔案產出

- `claims.csv`（9,997 bytes，sha256 `357d88031d4c…`）
- `probe_companies.py`（14,272 bytes，sha256 `e24aaa58120b…`）
- `report.md`（23,182 bytes，sha256 `8adc619daee3…`）
- `samples/iida_quarterly.csv`（1,306 bytes，sha256 `944da6590c6c…`）
- `samples/openhouse_quarterly.csv`（1,557 bytes，sha256 `2aa6b04db5bc…`）
- `samples/policy_rate_boj.csv`（14,146 bytes，sha256 `7282453e196d…`）
- `samples/stock_1306_topix.csv`（112,041 bytes，sha256 `c880c10a74b7…`）
- `samples/stock_1419_tamahome.csv`（113,910 bytes，sha256 `1e42a4a8deed…`）
- `samples/stock_1925_daiwa.csv`（118,531 bytes，sha256 `5d70f6d0275b…`）
- `samples/stock_1928_sekisui.csv`（118,075 bytes，sha256 `10264dcf6636…`）
- `samples/stock_2975_starmica.csv`（77,656 bytes，sha256 `96cf0dfcf659…`）
- `samples/stock_3288_openhouse.csv`（115,934 bytes，sha256 `a7c3c80d5b4d…`）
- `samples/stock_3291_iida.csv`（115,950 bytes，sha256 `bf51e573035b…`）
- `samples/stock_6083_erihd.csv`（111,789 bytes，sha256 `e06794b45d21…`）
- `samples/stock_7822_eidai.csv`（103,437 bytes，sha256 `9fc446d32ba1…`）
- `samples/stock_7943_nichiha.csv`（113,695 bytes，sha256 `ed9347eda017…`）
- `sources.csv`（2,878 bytes，sha256 `7c5939c6986c…`）

## 收件

```
taskq accept jp-claims-companies
```

退件：`taskq reject jp-claims-companies --reason "..."`
