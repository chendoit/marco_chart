# 交件：指派文件：投資型不動產的估值與資金面（空置率、期待利回り、J-REIT、銀行放款、地價 LOOK）的數據來源調研＋實測

- 任務：`jp-valuation-funding`（專案 jp-realestate-g，readonly）
- 完成時間：2026-10-08T16:47:46+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 1096245
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-valuation-funding` → pass
- reviewer：未啟用

## 摘要

完成投資型不動產估值與資金面（空置率、期待利回り、J-REIT、銀行放款、地價LOOK）之數據源調研與實測，成功產出8組樣本數據且機械驗收verify_wp.py全部通過。實測證實東京都心5區空置率跌至1.85%低於2%，銀行對不動產業放款殘高達123兆日圓續創新高。丸之內A級辦公期待利回り與JGB 10Y利差壓縮至14~68 bps，歷史調查期尚未轉負但已逼近倒掛臨界點。

## 檔案產出

- `probe_valuation_funding.py`（31,581 bytes，sha256 `8eb184b154b6…`）
- `report.md`（26,114 bytes，sha256 `40fe8789aa43…`）
- `samples/boj_real_estate_loans.csv`（3,705 bytes，sha256 `9c3464691fca…`）
- `samples/etf_1343_daily.csv`（57,548 bytes，sha256 `82d8b22fbda5…`）
- `samples/jnto_foreign_visitors_monthly.csv`（1,810 bytes，sha256 `62d95f8bd30d…`）
- `samples/jrei_expected_cap_rate_semiannual.csv`（1,828 bytes，sha256 `3242ae29519e…`）
- `samples/jreit_events.csv`（2,626 bytes，sha256 `46873601853c…`）
- `samples/miki_office_vacancy_rent.csv`（36,042 bytes，sha256 `f8779ae26a2c…`）
- `samples/mlit_commercial_price_index.csv`（3,839 bytes，sha256 `3d5fdd20ed4b…`）
- `samples/spread_cap_rate_jgb10y.csv`（2,052 bytes，sha256 `56d1c04d6ab2…`）
- `sources.csv`（4,830 bytes，sha256 `9793721da6c8…`）

## 收件

```
taskq accept jp-valuation-funding
```

退件：`taskq reject jp-valuation-funding --reason "..."`
