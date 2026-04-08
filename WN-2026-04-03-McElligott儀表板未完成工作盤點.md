# WN-2026-04-03 McElligott 儀表板未完成工作盤點

## 起因

McElligott 波動率儀表板（4 routes / 36 charts）及相關資料管線已完成初版建置（見 WN-2026-04-03-McElligott波動率儀表板建置.md）。本文系統性 review 尚未實作的項目，依優先順序排列。

---

## 文章覆蓋度分析

基於 4 routes 共 36 張圖對 McElligott 10 篇文章的覆蓋：


| 文章  | 主題                | 覆蓋圖數 | 覆蓋狀態                                                         |
| --- | ----------------- | ---- | ------------------------------------------------------------ |
| 01  | Dealer Gamma      | 8+2  | ✅ 完整（Route 4 全部 + Route 1 SKEW/GAMMA）                        |
| 02  | VIX/VVIX 動態       | 6    | ✅ 完整（Route 1 前 6 張）                                          |
| 03  | VRP / Vega Supply | 4    | ✅ 良好（Route 1 BXM/PUT/VPD/CNDR + SHORTVOL；Route 2 VRP vs SPX） |
| 04  | Vol Control / CTA | 1    | ⚠️ 薄弱 — 僅 RVOL 多窗口間接推斷，缺 CTA 信號代理                            |
| 05  | 槓桿 ETF            | 2    | ⚠️ 部分 — VIX ETF 有，但缺 TQQQ/SQQQ 等股票型槓桿 ETF                    |
| 06  | 相關性 / Dispersion  | 4    | ✅ 良好（COR + MGTN + 跨資產 Vol）                                   |
| 07  | 利率 / Term Premium | 5    | ✅ 完整（殖利率曲線 + VXTLT + DFII10 + ACM）                           |
| 08  | FCI / 流動性         | 4    | ✅ 良好（NFCI + OFR + SOFR + OIS）                                |
| 09  | 部位與情緒             | 3    | ⚠️ 部分 — CFTC FX + Put/Call，缺 E-mini SPX positioning          |
| 10  | VaR Shock / 跨資產   | 2    | ⚠️ 散布於其他 route（JPY Carry + Flip Distance + 跨資產 Vol）          |


---

## 未完成工作清單

### P0（高優先：直接填補文章覆蓋缺口）

#### 1. CFTC E-mini S&P 500 COT 報告（文章 09 / 06 替代）

**缺口**：McElligott 本人引用 "CFTC/TFF Asset Manager Futures at 100th %ile"，這是 HF Net/Gross Exposure 的最佳公開替代。目前 CFTC 抓取（`get_ctfc_series.py`）只有 FX（JPY/EUR/AUD）和原油。

**待辦**：

- 在 `get_ctfc_series.py` 擴充 E-mini S&P 500 Futures（CFTC Code: 13874A）
- 取得 Asset Manager + Leveraged Fund 的 Long/Short/Net 持倉
- 產出 pkl：`emini_asset_mgr_net_position.pkl` 等
- 新增 1-2 張圖至 Route 2（部位擁擠度）

**可行性**：高 — CFTC TFF (Traders in Financial Futures) 報告是免費公開的

#### 2. CTA 趨勢信號代理（文章 04 強化）

**缺口**：文章 04 是 McElligott 框架中最核心的系統性流量分析（Vol Control + CTA），但目前僅有 RVOL 間接推斷。

**待辦**：

- 在 `highcharts_utils.py` 新增 `.MA` 衍生表達式（移動平均線）
- 建構 SPX 的 10d/20d/50d/100d/200d MA 交叉信號作為 CTA 趨勢代理
- 可計算「多少條 MA 看多」作為 CTA 信號強度的簡化版
- 新增 1-2 張圖至 Route 2 或新建 Route

**可行性**：高 — 純計算，不需新資料來源

### P1（中優先：增強現有覆蓋）

#### 3. 槓桿 ETF 成交量追蹤（文章 05 強化）

**缺口**：目前只追蹤 VIX ETF（UVXY/SVXY），缺少股票型槓桿 ETF（TQQQ/SQQQ/SOXL/SOXS 等）的成交量追蹤。McElligott 稱槓桿 ETF 為 "Synthetic Short Gamma"，AUM $129B 是歷史最高。

**待辦**：

- 新增 TQQQ/SQQQ/SSO/SDS 的歷史成交量資料來源（Yahoo Finance API 或 Alpha Vantage）
- 建構「槓桿 ETF 日再平衡估計」= AUM × 日漲跌幅 × 槓桿倍率
- 新增 1 張成交量異常圖至 Route 1 或 Route 2

**可行性**：中 — 需新增資料來源（Yahoo Finance），但 API 免費

#### 4. Money Market Fund AUM（文章 09 強化）

**缺口**：McElligott 追蹤 "MMF AUM 在 90th+ %ile = 大量現金觀望中"，FRED 有此序列但未抓取。

**待辦**：

- 在 `get_all_series_data.py` 新增 FRED `MMMFFAQ027S`（季度）或 ICI 週報數據
- 可放入 Route 3 作為流動性補充指標

**可行性**：高 — FRED API 一行代碼

#### 5. iVol vs rVol 差距量化（文章 03/04 強化）

**缺口**：VRP（Variance Risk Premium）= iVol - rVol，是 Vol Control 和 Vega Supply 的核心輸入。目前有 RVOL 和 VIX 分別存在，但未建構差值圖。

**待辦**：

- 在某個 Route 新增 VIX - RVOL20 差值圖（VRP 代理）
- 或在 `highcharts_utils.py` 中支援 CBOE 與衍生序列的混合運算

**可行性**：高 — 用現有 ids 表達式 `(cboe_VIX, '-', cboe_SPX.RVOL20)` 即可

### P2（低優先：錦上添花）

#### 6. SG Trend Index

**現狀**：免費每日資料不可直接取得。官方網站只顯示 MTD/YTD 彙總，完整每日資料需付費或聯繫 SG。

**替代**：Barclay BTOP50 Index 月度資料，或從 Top Traders Unplugged 網站 scrape 月度回報。

**可行性**：低 — 免費每日資料無法取得

#### 7. CBOE Put/Call Ratio 歷史補齊

**現狀**：MacroMicro series 1650 已有此資料且已在 `get_m_square_series.py` URL 列表中。CBOE 官方 CSV 只到 2019-10-04 停更。

**確認事項**：驗證 MM 1650 的資料頻率和更新及時性是否滿足需求。若 MM 抓取失敗，需考慮從 CBOE Daily Market Statistics 頁面 scrape 作為備援。

**可行性**：已有替代（MM 1650），無需額外工作

---

## 資料管線完整性檢查

### 已確認正常運作的資料來源


| 來源                                                   | 腳本                         | 狀態  |
| ---------------------------------------------------- | -------------------------- | --- |
| FRED API（STLFSI4, THREEFYTP10, DGS2, T10Y2Y, DFII10） | `get_fed_series.py`        | ✅   |
| MacroMicro Series（~80+ series）                       | `get_m_square_series.py`   | ✅   |
| MacroMicro Charts（OIS, FedWatch, 領先指標）               | `get_m_square_chart.py`    | ✅   |
| CBOE CDN（27 indices + 3 OHLC）                        | `get_cboe_index.py`        | ✅   |
| CFTC（JPY/EUR/AUD/原油）                                 | `get_ctfc_series.py`       | ✅   |
| NY Fed ACM Term Premium（2Y/5Y/10Y）                   | `get_nyfed_termpremium.py` | ✅   |
| GEX-lieta（SPX/SPY/VIX × 8 series）                    | `get_gex_series.py`        | ✅   |
| ETF Fund Flow（ProShares CSV）                         | `get_etf_csv.py`           | ✅   |


### 需新增的資料來源


| 需求                  | 建議腳本                           | 優先順序 |
| ------------------- | ------------------------------ | ---- |
| CFTC E-mini S&P 500 | 擴充 `get_ctfc_series.py`        | P0   |
| FRED MMMFFAQ027S    | 擴充 `get_all_series_data.py` 一行 | P1   |
| TQQQ/SQQQ 成交量       | 新建 Yahoo Finance 抓取            | P1   |


---

## WN-2026-04-02 下一步進度追蹤


| 原始項目                    | 狀態    | 備註                   |
| ----------------------- | ----- | -------------------- |
| 優先擴充 CBOE CDN 抓取        | ✅ 完成  | 5→27 symbols         |
| 擴充 FRED API 殖利率/實質殖利率   | ✅ 完成  | DGS2, T10Y2Y, DFII10 |
| CFTC E-mini S&P 500 COT | ⬜ 未完成 | 本文 P0 項目 #1          |
| 可計算指標在 route 中實作        | ✅ 完成  | .RVOL 衍生表達式          |


## 建議執行順序

1. **CFTC E-mini SPX**（P0 #1）— 填補文章 09 最大缺口，McElligott 本人引用
2. **CTA 趨勢信號**（P0 #2）— 填補文章 04 覆蓋缺口，純計算
3. **iVol vs rVol 差值**（P1 #5）— 一張圖即可，用現有表達式
4. **FRED MMF AUM**（P1 #4）— 一行 code
5. **槓桿 ETF 成交量**（P1 #3）— 需新資料來源，可後續

