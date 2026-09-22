# WN-2026-09-17: 9 國 5Y 主權 CDS (sid 27118/27119/27126/27129/27131/27134/27135/27136/27138) 落地紀錄

> **一句話**: 9 條 M² series 改由 investing.com 內部 API (主) + worldgovernmentbonds.com (備援) 接管,
> `get_cds_series.py` 已落地,`get_all_series_data.py` tasks 表、`get_m_square_series.py`、
> `calc_pctrank.py` 均已同步。全部 status = approx。

---

## 1. 覆蓋範圍

| sid | 國家 | 主源 | 舊 n | 新 n | 最後資料日 | 重疊中位差 |
|---|---|---|---|---|---|---|
| 27118 | 英國 | investing.com pair_id=1115185 | 37 | 3571 | 2026-09-15 | 4.68%(重疊10點) |
| 27119 | 德國 | investing.com pair_id=1202222 | 33 | 4674 | 2026-09-15 | 7.04%(重疊10點) |
| 27126 | 法國 | investing.com instrument_id=1158922 | 33 | 3568 | 2026-09-15 | 6.79%(重疊10點) |
| 27129 | 葡萄牙 | WGB (investing.com 無此頁) | 37 | 3099 | 2026-09-17 | 5.05%(重疊25點) |
| 27131 | 西班牙 | investing.com pair_id=1115764 | 37 | 3570 | 2026-09-15 | 4.57%(重疊10點) |
| 27134 | 墨西哥 | investing.com pair_id=1158921 | 37 | 3831 | 2026-09-15 | 1.98%(重疊10點) |
| 27135 | 義大利 | investing.com instrument_id=1115161 | 37 | 3572 | 2026-09-15 | 3.18%(重疊10點) |
| 27136 | 巴西 | investing.com instrument_id=1116031 | 37 | 3574 | 2026-09-16 | 2.26%(重疊10點) |
| 27138 | 土耳其 | investing.com pair_id=1096486 | 37 | 3564 | 2026-09-15 | 1.48%(重疊11點) |

---

## 2. 端點活著確認 (2026-09-17)

全部 9 個 reference fetcher 函式實跑通,端點均存活:
- investing.com `api.investing.com/api/financialdata/historical/{id}` 返回 2013~最新日頻
- WGB `wp-json/common/v1/historical` POST 返回 2017-04 起日頻

---

## 3. approx 說明

全部 9 條 status = approx,原因:
- 舊 M² 值與新源有 **~2-8% 中位數口徑差**(不同評價機構/日內時點)
- 方向與量級一致,可用於延續曲線
- 舊 pkl 稀疏快照 (n=33-37,停 2026-08-14),新源為日頻全歷史 → 點數暴增是預期
- 葡萄牙 (27129) 2013-01~2016-11 有 gap(WGB 該段無資料),重疊點僅 25 筆

---

## 4. 踩坑紀錄

- 需 `curl_cffi impersonate="chrome131"` + `verify=False` + Origin/Referer/domain-id headers
- 葡萄牙 (27129) investing.com 無此頁,只能 WGB
- WGB 的 `COUNTRY1.SYMBOL` 給錯國家不會報錯、只默默回錯國資料 → 逐國從頁面 `jsGlobalVars` 抓正確值
- 土耳其 (27138) investing.com 一次拉 13 年會回壞點 → 分塊 ≤2 年
- 投資組合:portugal (27129) 端點回傳 2026-09-17 資料,其它 8 國最新為 2026-09-15

---

## 5. 檔案變更

| 檔案 | 動作 |
|---|---|
| `C:/code/2025-12-05-MacroMicro-Data/get_cds_series.py` | 新增:9 個 fetch + TITLE_MAP + `_save_series` + JOBS + 入口 |
| `C:/code/2025-12-05-MacroMicro-Data/get_all_series_data.py` | 新增 import + tasks 表插入 `("CDS 9 countries (27118-27138)", fetch_cds_series)` |
| `C:/code/2025-12-05-MacroMicro-Data/get_m_square_series.py` | 9 條 CDS url 改註解 `# [2026-09-17] 9 條 CDS 改由 get_cds_series.py 抓取` |
| `C:/code/2025-12-05-MacroMicro-Data/data/series_271*.pkl` | 9 個 pkl 更新為日頻全歷史 |
| `%TEMP%/pkl_backup_03/` | 9 個舊 pkl 備份 |

---

## 6. 歷史說明

這 9 條 series 歷史上由 `get_m_square_chart.py` 時代或其他管道產生,
本次起由 `get_cds_series.py` 供料。`get_m_square_series.py` 中對應 url 已註記摘除。

---

## 7. 驗收

- ✅ 端點活著確認
- ✅ 舊 pkl 備份完成
- ✅ `get_cds_series.py` 開發完成
- ✅ `get_all_series_data.py` tasks 掛載
- ✅ `get_m_square_series.py` url 註記摘除
- ✅ 實跑通 + 逐 datetime 重疊比對 (approx,方向量級一致)
- ✅ `calc_pctrank` 重跑完成 (35 computed, 0 skipped)
- ✅ 本 WN 已寫入
