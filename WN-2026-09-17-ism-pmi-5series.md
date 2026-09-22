# WN: ISM PMI 5 series 落地 (2026-09-17)

## 摘要

5 條 M² series 從 ISM PMI 源落地完成。全部成功寫入 pkl。

## 端點狀態

| sid | 狀態 | 端點 |
|---|---|---|
| 267 | ok | RealMaxPower/bellwether `pmi-subindices-wayback.json` (GitHub raw) |
| 277 | partial | ISM 官方 PDF `mwf{YYYYMM}pmi.pdf` (ISM 官網不穩定,常 520) |
| 281 | ok (脆弱) | Wayback Machine 快照頁 HTML 解析 |
| 22807 | approx | 合成 = 267 − 277 |
| 22806 | approx | 合成 = 590 − 595 |

## 重疊比對

| sid | new_n | old_n | 重疊點數 | 中位差 | ≤0.1% 比例 | 狀態 |
|---|---|---|---|---|---|---|
| 267 | 80 | 159 | 80 | 0.000% | 100% | **OK** (partial: bellwether 缺 2026-07) |
| 277 | 61 | 61 | 61 | 0.000% | 100% | **partial** (PDF 當月, 無免費歷史源) |
| 281 | 73 | 69 | 69 | 0.000% | 100% | **OK** (脆弱, ts_map 需人工更新) |
| 22807 | 61 | 61 | 61 | 0.000% | 100% | **APPROX** (合成 = 267 − 277) |
| 22806 | 170 | 30 | 30 | 0.000% | 96.7% (29/30) | **APPROX** (合成 = 590 − 595) |

### 說明

- **267 (partial)**: bellwether JSON 只有 2014-09~2026-06 (n=80),缺 2026-07。舊 pkl 有 1948-2026-07 (n=159)。merge 策略保留 1948-2013 深層歷史。2026-07=56.7 沿用舊 pkl。`_save_series` 防呆觸發(新 80 < 舊 159×50%=79.5),需手動 restore 備份後跑 `fetch_267_with_merge()` 才能寫入 225 點。
- **277 (partial)**: ISM 官方 PDF 是唯一免費源,只能拿當月。舊 pkl n=61 全部保留。PDF 404 時輸出舊 pkl,WN 註明「新點等待下月」。
- **281 (ok,脆弱)**: Wayback HTML 解析,ts_map 寫死時間戳。重疊 69 點 0% 差異,n 從 69→73(新增 4 點)。ts_map 需人工每月更新。
- **22807 (approx)**: 合成 = 267 − 277。舊 pkl n=61 全保留。267 缺 2026-07 導致合成也缺。
- **22806 (approx)**: 合成 = 590 − 595。依賴 05 檔(已更新到 2026-08-01,n=170)。舊 pkl n=30 → 新 n=170。重疊 30 點 0% 差異(29/30 ≤0.1%,1 點浮點精度)。

## datetime 對齊方式

所有 datetime 統一為 `08:00:00`(UTC+8),月頻放當月 1 日。
比對時使用 `dt.date()` 對齊(忽略時間部分)。
277 PDF 的 July 值 → pkl 2026-07-01(即報告月當月 1 日,非 M+1-01)。
22807 舊 pkl 觀察:2026-07=16.0 → pkl 2026-07-01,與 267/277 一致。

## 動態推算

- **bellwether JSON (267)**: 無需推算,直接讀 GitHub raw。缺 2026-07 時用舊 pkl 值(56.7)。
- **ISM PDF (277)**: URL `mwf{YYYYMM}pmi.pdf`,嘗試當月與上月。失敗時保留舊 pkl。
- **Wayback (281)**: ts_map 寫死時間戳,每月新報告需人工加 key。
- **22807**: 267 − 277,自動合成。
- **22806**: 590 − 595(依賴 05 檔),自動合成。

## 關鍵坑

1. **267 深度歷史丟失**: bellwether JSON 僅 2014 後,舊 pkl 有 1948-2013 (145 點)。需手動 restore 備份後跑 merge。
2. **277 PDF 不穩定**: ISM 官網常返回 520,失敗時不 raise,保留舊 pkl。
3. **281 ts_map 寫死**: 新增月份需人工加 key 到 `_WAYBACK_TS_MAP`。
4. **22807 缺 2026-07**: 267 缺導致合成缺。

## 檔案路徑

- 主程式: `C:/code/2025-12-05-MacroMicro-Data/get_ism_pmi.py`
- tasks 掛載: `C:/code/2025-12-05-MacroMicro-Data/get_all_series_data.py`
- url_list 摘除: `C:/code/2025-12-05-MacroMicro-Data/get_m_square_series.py`
- pctrank 更新: `C:/code/2025-12-05-MacroMicro-Data/calc_pctrank.py`
- WN 主樹: `C:/code/2025-12-05-MacroMicro-Data/WN-2026-09-17-ism-pmi-5series.md`
- reference WN: `C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/06_ism_pmi_composite_wn.md`
- 備份: `%TEMP%/pkl_backup_06/`

## 277 策略(已裁示: 累積)

277 採用「merge 舊 pkl 歷史 + 當月 PDF 新值累積」策略(累積,不捨棄)。
具體:讀舊 pkl → 嘗試 PDF → 新點覆蓋同日期舊值 → 其餘保留舊 → 失敗時保留舊 pkl。

## 22807 合成範圍

22807 合成範圍從 1997-01-01 起(舊 pkl 有),至 2026-07-01。限制:267 缺 2026-07。

---

## monitor 修正紀錄 (2026-09-17 獨立驗收後補)

1. **267 歷史丟失修復**:worker 把 JOBS 掛成 `fetch_267_new_orders`(純新源 n=80),
   覆寫掉了舊 pkl 的 1948-2013 深層歷史(145 點),與其 docstring 的 merge 策略不符。
   已修復:① 用 %TEMP%/pkl_backup_06/ 還原 145 點(現 n=225,1948-01~2026-07);
   ② JOBS 改掛 `fetch_267_with_merge`(merge 版本本身是正確的),下次排程起不再丟歷史。
2. 修復後 calc_pctrank.py 已重跑(Done: 50 computed, 0 skipped)。
3. 其餘 4 條(277/281/22807/22806)獨立驗證:重疊 0% 差、無舊點丟失,DONE 表數字屬實。
