# 交件：指派文件：日本住宅價格、房貸利率與購買力的數據來源調研＋實測

- 任務：`jp-prices-rates`（專案 jp-realestate-b，readonly）
- 完成時間：2026-10-08T15:26:46+08:00
- 執行：agy:gemini-3.8-flash-high，第 3 次嘗試，tokens 546472
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-prices-rates` → pass
- reviewer：未啟用

## 摘要

已完成日本住宅價格、房貸利率與購買力全序列之調研與實測，產出18項來源清單與9組高頻長歷史樣本；查證確認首都圈新築公寓2025年度均價逼近9,500萬與建売透天比值達2.08倍，並釐清日銀當前基準利率已進一步調升至1.25%（素材0.75%已過時）；verify_wp.py 機械驗收已全數通過。

## 檔案產出

- `probe_jp_prices_rates.py`（25,931 bytes，sha256 `5945ada3266f…`）
- `report.md`（28,112 bytes，sha256 `5bd3fae1b272…`）
- `samples/boj_policy_rate_bis.csv`（14,160 bytes，sha256 `f71fa8ee3098…`）
- `samples/boj_prime_rate.csv`（6,587 bytes，sha256 `f1b5888bb8c3…`）
- `samples/boj_rate_timeline.csv`（1,856 bytes，sha256 `fe1f36c4dc40…`）
- `samples/flat35_mortgage_rate.csv`（794 bytes，sha256 `ac85414a72a6…`）
- `samples/mlit_property_price_index.csv`（30,246 bytes，sha256 `592cd2cd3e31…`）
- `samples/mof_jgb_10y_yield.csv`（485,995 bytes，sha256 `a775f4318cb3…`）
- `samples/reei_mansion_annual.csv`（691 bytes，sha256 `03cbdf601b17…`）
- `samples/reins_market_watch_prices.csv`（827 bytes，sha256 `a52b1e3241c3…`）
- `samples/tokyo_kantei_income_multiplier.csv`（406 bytes，sha256 `ae14bfe3a7fb…`）
- `sources.csv`（5,630 bytes，sha256 `b4002ec14b0f…`）

## 收件

```
taskq accept jp-prices-rates
```

退件：`taskq reject jp-prices-rates --reason "..."`
