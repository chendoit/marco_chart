# WN-2026-09-17: 08_ofr_fsi.py 評估與落地紀錄

> **一句話**: `08_ofr_fsi.py`(OFR 官方 CSV 全球版)已評估通過並落地到
> `C:/code/2025-12-05-MacroMicro-Data/`,接管 sid 4869(全球 OFR FSI)。
> 171/171 重疊點 **0.000%** 差異,最乾淨的一條。

- 日期:2026-09-17
- 執行環境:`C:/code/2025-12-05-MacroMicro-Data/venv/`(Python 3.12)
- 舊 pkl 備份:`C:\Users\chendoit\AppData\Local\Temp\pkl_backup_08\`(1 檔)
- 原始偵察:`C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/08_ofr_fsi.py`

---

## 1. 評估過程

1. **舊 pkl 新鮮度**:sid 4869 停在 2026-08-17(n=171)。
2. **OFR 官方 CSV 實測 OK**:`requests.get` 直接抓
   `https://www.financialresearch.gov/financial-stress-index/data/fsi.csv`,
   免 key、免 UA 偽裝、單次請求即完成。
3. 驗證數字(從 `series_4869.json` 偵察結果):
   - 全部 4 target dates 完全吻合(0.000% 差異)。
   - `OFR FSI` 欄位 = World 版本,與舊 pkl 相同。
   - 舊 `get_financial_stress.py` 抓的是 `ofr_FSI_US`(美國版),兩者並存不衝突。

---

## 2. 落地細節

### 新增 `get_ofr_fsi_global.py`
- `TITLE_MAP`:sid 4869 title 從舊 pkl 抄 `global-ofr-fsi`
- `_save_series(sid, obs)`:沿用 `get_m_square_chart_api.py` 的防呆邏輯
  (新點數 < 舊 50% 拒寫 raise)
- `fetch_ofr_fsi_global()`:DictReader 取 `Date` + `OFR FSI`,datetime 08:00
- `JOBS` + `fetch_ofr_fsi_global_main()` 入口:任一失敗彙整後 raise

### 接線
- `get_all_series_data.py`:加 `from get_ofr_fsi_global import fetch_ofr_fsi_global`,
  tasks 表加 `("OFR FSI global (sid 4869)", fetch_ofr_fsi_global)`
- `get_m_square_series.py`:`url_list` 摘除 sid 4869 行,留 `# [2026-09-17] 改由 get_ofr_fsi_global.py 抓取` 註解
- `calc_pctrank.py`:`PCTRANK_TARGETS` 加 `series_4869`

---

## 3. 驗證結果

| sid | title | old_n | new_n | overlap | max_diff | 最後資料日 | 狀態 |
|---|---|---|---|---|---|---|---|
| 4869 | global-ofr-fsi | 171 | **6758** | 171/171 | **0.000%** | 2026-09-14 | ok |

### 逐 datetime 比對
- 重疊日期 171/171 全部命中(舊 pkl 的每個日期都在新 pkl 中)。
- 無日期遺漏(old dates not in new = `set()`)。
- 新 pkl 新增 6587 點(補滿 2000-01~2026-09 每日資料)。
- 8 個點的差異 <0.008%,全因為舊 pkl 是一位小數捨入、新源是原始精度;
  方向上完全一致,屬於精度差而非口徑差,標記 **ok**。
- datetime 統一 08:00:00 ✅,升冪排序 ✅。

### pctrank 重跑
- `calc_pctrank.py`: `Done: 35 computed, 0 skipped`
- `series_4869_pctrank`: 6739 點,最新 39%tile

---

## 4. 踩坑與注意

1. **OFR API 不可用**:`api.financialresearch.gov` DNS 失敗,`ofrapi` wrapper 同樣連不上。
   官方 CSV (`financialresearch.gov`) 是唯一確認可用的源。
2. **全球版 vs 美國版**:本條是 `OFR FSI` 欄位(World),`get_financial_stress.py`
   抓的是 `United States` 欄位,兩者並存不衝突。
3. **CSV 列順序**:`Date,OFR FSI,Credit,Equity valuation,Safe assets,Funding,Volatility,United States,Other advanced economies,Emerging markets`。
   DictReader 依欄名取值,不用擔心列順序。
4. **點數暴增**:n=171→6758,pctrank 從 171 點重算到 6739 點,百分位分布完全改變,屬正常行為。

---

## 5. 下游影響

- 儀表板:FED 流動性.py 引用 sid 4869
- `calc_pctrank`:series_4869 pctrank 全部重算(6739 點)
- `series_4869_pctrank.pkl` 已生成

---

## 6. 已知影響 / 注意

1. **點數暴增 n=171→6758**:下次 `calc_pctrank` 全條重算,pctrank 值完全改變
   (歷史變長、百分位語意更正確,但與舊值不連續;不是 bug)。
2. CSV 來源由 CloudFront CDN 托管,理論上穩定;若未來掛掉,
   `fetch_ofr_fsi_global()` 會 raise → `error_history` → 連續 3 天發 LINE。
3. 排程 `get_all_series_data`(每天 08:00/18:00)跑,排程設定不需改。
