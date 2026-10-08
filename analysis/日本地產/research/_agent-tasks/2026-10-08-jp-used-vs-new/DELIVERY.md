# 交件：指派文件：首都圏中古與新築住宅供需對照（REINS、既存住宅販売量指数、不動産経済研究所月度）的數據來源調研＋實測

- 任務：`jp-used-vs-new`（專案 jp-realestate-e，readonly）
- 完成時間：2026-10-08T16:42:13+08:00
- 執行：agy:gemini-3.8-flash-high，第 1 次嘗試，tokens 498673
- verify：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-used-vs-new` → pass
- reviewer：未啟用

## 摘要

完成首都圏中古與新築住宅供需對照調研與實測，補齊REINS月度長歷史（2015-2026）、國交省既存住宅販売量指数（2008-2026）及不動産経済研究所新築月度等6組樣本。驗證中古成約件數自2016年起連續10年超越新築發售戶數（2025年達2.25倍），最新單價比為56.5%，且REINS在庫月數自2026年起回升至14.6個月。全部驗收條件通過。

## 檔案產出

- `probe_jp_used_vs_new.py`（22,515 bytes，sha256 `caa34c24de03…`）
- `report.md`（27,622 bytes，sha256 `cdd0901bb0eb…`）
- `samples/mlit_existing_sales_index.csv`（14,304 bytes，sha256 `ca75204ab365…`）
- `samples/reei_new_condo_monthly.csv`（899 bytes，sha256 `da636425e2c5…`）
- `samples/reins_annual_used_vs_new.csv`（1,638 bytes，sha256 `c6e874c72ef4…`）
- `samples/reins_used_condo_monthly.csv`（6,717 bytes，sha256 `bf76f718e3a8…`）
- `samples/reins_used_detached_monthly.csv`（5,463 bytes，sha256 `c8c30e47c4f0…`）
- `samples/tokyo_kantei_used_70sqm_monthly.csv`（451 bytes，sha256 `880358edd468…`）
- `sources.csv`（5,053 bytes，sha256 `cf877910b713…`）

## 收件

```
taskq accept jp-used-vs-new
```

退件：`taskq reject jp-used-vs-new --reason "..."`
