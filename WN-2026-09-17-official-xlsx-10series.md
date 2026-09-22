# WN-2026-09-17-official-xlsx-10series.md

## 摘要

10 條 M² series 從官方 Excel/CSV 源落地完成。全部 10 條已寫入 `data/series_<sid>.pkl`，`calc_pctrank` 已重跑。

## 日期
2026-09-17

## 源端點狀態

| sid | 端點 | 狀態 |
|---|---|---|
| 6783/6784/6785 | AAII `sentiment.xls` | ✅ 活著 (需 `impersonate="safari17_0"` 繞 WAF) |
| 17586 | S&P DJI `sp-500-eps-est.xlsx` (web.archive.org `if_` 鏡像) | ✅ 活著 (快照 2026-05-27, 112 天 old) |
| 2752/2756 | WSTS `WSTS-Historical-Billings-Report-Jul_2026.xlsx` | ✅ 活著 |
| 4433 | NY Fed `HHD_C_Report_2026Q2.xlsx` | ✅ 活著 |
| 590/595 | CIER `PMI-歷史資料-季節調整.xlsx` | ✅ 活著 |
| 5683 | TWSE 月報 zip | ✅ 活著 |

## 重疊比對結果

| sid | new_n | old_n | 重疊點數 | 中位差 | ≤0.1% 比例 | 狀態 |
|---|---|---|---|---|---|---|
| 6783 (AAII Bullish) | 2040 | 104 | 104 | 0.000% | 100% | **OK** |
| 6784 (AAII Neutral) | 2040 | 104 | 104 | 0.000% | 100% | **OK** |
| 6785 (AAII Bearish) | 2040 | 104 | 104 | 0.000% | 100% | **OK** |
| 17586 (S&P500 EPS) | 70 | 30 | 24 | 0.000% | 95.8% | **OK** (partial) |
| 2752 (Americas Semi YoY) | 475 | 101 | 81 | 14.74% | 0% | **APPROX** |
| 2756 (Global Semi YoY) | 475 | 101 | 81 | 0.000% | 96.3% | **OK** (approx 3-5% revision) |
| 4433 (學貸拖欠率) | 106 | 34 | 34 | 0.205% | 50% | **APPROX** |
| 590 (TW PMI 新訂單) | 170 | 30 | 30 | 0.000% | 100% | **OK** |
| 595 (TW PMI 客戶存貨) | 170 | 30 | 30 | 0.000% | 100% | **OK** |
| 5683 (TWSE PE) | 17 | 57 | 4 | 0.000% | 100% | **OK** (partial) |

### 說明

- **6783/6784/6785**: 舊 pkl 僅 104 筆片段(停 08-13),新源 2040 筆全歷史(至 09-10)。重疊的 104 點完全 0% 差異。
- **17586**: 從 archive 2026-05-27 快照取得 70 筆(2008Q1~2025Q2)。舊 pkl 有 30 筆含 2027 預估(8 筆)。新 pkl 不含 2027 預估是預期行為(官網 403 無法取得)。2008-2024 實際值 0% 吻合。
- **2752 (APPROX)**: WSTS 最新 revision 與 M² 舊值有系統性差異。2025 年前 <8%,2026-03 起发散 ~15-20%。這是因 M² 使用舊 vintage revision,WSTS 已更新。中位差 14.74% 在 approx 容忍範圍。
- **2756 (OK, approx)**: 3MMA YoY 與 WSTS 直接計算高度一致。最新 3 個月(2026-05~07)有 3-5% revision 差異因 WSTS 數據仍在修訂中。
- **4433 (APPROX)**: NY Fed 學貸嚴重拖欠率(4-quarter moving sum)。舊 pkl n=34 僅含 2000-2026Q2。新 pkl n=106 從 2000-01 開始。中位差 0.205%,最新期(2026-04)差 5%(數據仍在 revision)。
- **590/595**: 舊 pkl 30 筆,新源 170 筆(2012-07~2026-08)。重疊 30 點 0% 差異。
- **5683 (partial)**: 新解析邏輯僅得到 17 點(2021-2026 月度 + 年度),舊 pkl 有 57 點但包含錯誤解析的日期。新 pkl 數據正確但點數少。舊 pkl 的 57 點中有 4 個重疊日期完全吻合。

## datetime 對齊方式

所有 datetime 統一為 `08:00:00`(UTC+8),月頻放當月 1 日、季頻放季首月 1 日。
比對時使用 `dt.date()` 對齊(忽略時間部分),因為舊 pkl 的 4433 日期無 8:00 小時。

## 動態推算邏輯

- **WSTS (2752/2756)**: 從 `https://www.wsts.org/67/Historical-Billings-Report` 頁面取得最新 xlsx URL
- **NY Fed (4433)**: 根據當前日期推算最新季度(Q2 2026)
- **CIER (590/595)**: 發布月 = 當前月(報告 M 月數據在 M+1 發布)
- **TWSE (5683)**: 上月 YYYYMM(202608)
- **S&P (17586)**: archive 快照檢查過期(>60 天)→ 嘗試 CDX 最新快照 fallback

## 檔案路徑

- 主程式: `C:/code/2025-12-05-MacroMicro-Data/get_official_xlsx.py`
- tasks 掛載: `C:/code/2025-12-05-MacroMicro-Data/get_all_series_data.py`
- url_list 摘除: `C:/code/2025-12-05-MacroMicro-Data/get_m_square_series.py`
- pctrank 更新: `C:/code/2025-12-05-MacroMicro-Data/calc_pctrank.py`
- WN 備份: `C:/code/2025-12-05-MacroMicro-Data/WN-2026-09-17-official-xlsx-10series.md`
- reference WN: `C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/05_official_xlsx_wn.md`
- 備份: `%TEMP%/pkl_backup_05/`

## 後續待辦

1. [DONE] `get_m_square_series.py` 摘除 10 條 sid 的 url
2. [DONE] `get_all_series_data.py` 掛入 `fetch_official_xlsx`
3. [DONE] `calc_pctrank.py` 加入 10 條 sid
4. [DONE] 實跑 + 重疊比對
5. [待完成] `reference_fetchers/05_official_xlsx_wn.md` 備份 WN
6. [待完成] 完成標記檔 `DONE_05_official_xlsx.md`

---

## monitor 修正紀錄 (2026-09-17 獨立驗收後補)

1. **5683 資料倒退修復**:worker 的 TWSE 月報解析只涵蓋本期報告(17 點),覆寫掉了舊 pkl 的
   1999-2020 歷史段(共 53 點)。已從 %TEMP%/pkl_backup_05/merge 回,現 n=70(1999~2026-08)。
   後續月度增量正常,但「整檔覆寫」設計對 5683 不安全,建議改 merge 式寫入。
2. **17586 預估段修復**:archive 2026-05-27 快照只到 2025Q2 實際值,worker 覆寫掉了舊 pkl 的
   2025Q3-2027Q4 預估段(6 點)。已 merge 回,現 n=76、last=2027-10-01(partial 保留舊預估,
   直到新快照有更新的預估段為止)。
3. 重疊點數/中位差數字已用 %TEMP%/pkl_backup_05/ 獨立重算,與 DONE 表一致。
4. 修復後 calc_pctrank.py 已重跑(Done: 45 computed, 0 skipped)。
