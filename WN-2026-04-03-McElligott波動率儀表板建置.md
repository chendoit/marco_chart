# WN-2026-04-03 McElligott 波動率儀表板建置

## 起因

根據 McElligott 10 篇分析框架文章，規劃並實作四個新的 flask_highcharts route（共 43 張圖），涵蓋波動率微結構、相關性與部位、總經與利率、Dealer Gamma 四大支柱。需整合多個新資料來源：CBOE CDN 擴充、FRED 新增 series、GEX-lieta 本地 SQLite、NY Fed ACM Term Premium、CFTC TFF E-mini SPX、槓桿 ETF。

## 資料準備

### 1. CBOE CDN 擴充（get_cboe_index.py）

`CBOE_INDICES` 從原本 5 個擴充至 27 個：

| 類別 | 新增 symbols | 用途 |
|------|-------------|------|
| VIX 期限結構 | VIX1D, VIX9D, VIX3M, VIX6M, VIX1Y | McElligott 02: Contango/Backwardation |
| 跨指數波動率 | RVX, VXN | McElligott 06: 跨市場 vol 比較 |
| 市場結構 | SKEW, GAMMA, SMILE | McElligott 01/02: 波動率曲面 |
| 隱含相關性 | COR1M, COR3M, COR6M, COR1Y | McElligott 06: Dispersion Trade |
| VRP 策略 | BXM, PUT, VPD, CNDR | McElligott 03: Vol-Selling 生態系 |
| 集中度 | MGTN | McElligott 06: Magnificent 10 |
| 殖利率 | TNX, TYX, FVX, IRX | McElligott 07: 利率曲線 |
| 利率波動率 | VXTLT | McElligott 07: Rate Vol |

驗證：全部 27 個 close series + 3 個 OHLC 成功抓取，共 32 個 pkl。

### 2. FRED 新增（get_all_series_data.py）

| Series ID | 說明 | 用途 |
|-----------|------|------|
| DGS2 | 2Y 國債殖利率 | 殖利率曲線（CBOE 無 2Y） |
| T10Y2Y | 10Y-2Y Spread | 曲線斜率量化 |
| DFII10 | 10Y TIPS 實質殖利率 | FCI 收緊代理 |
| MMMFFAQ027S | Money Market Fund 總資產（季度） | 文章 09：現金觀望度 |

驗證：4 個 pkl 成功產生（fed_DGS2.pkl, fed_T10Y2Y.pkl, fed_DFII10.pkl, fed_MMMFFAQ027S.pkl）。

### 3. GEX 資料橋接（get_gex_series.py — 新建）

從 `C:\code\2026-03-24-GEX-lieta\gex_analysis.db` 讀取 SPX/SPY/VIX 三個 ticker 的 dealer gamma 資料，轉為 pkl。

每個 ticker 匯出 8 個 series：
- `gamma_flip` — Gamma Flip Level（原始）
- `gamma_flip_ce` — Gamma Flip Level（Conditional Expectation）
- `call_wall_ce` — Call Wall
- `put_wall_ce` — Put Wall
- `gamma_field_ce` — Gamma Field
- `spot_price` — Spot Price
- `gamma_env` — Gamma Environment（+1=Positive, -1=Negative）
- `flip_distance` — Gamma Flip Distance %（預計算 `(spot - flip_ce) / spot * 100`）

驗證結果：

| Ticker | 資料筆數（代表） | 日期範圍 |
|--------|-----------------|----------|
| SPX | 419 (gamma_flip), 421 (spot), 410 (gamma_env), 418 (flip_distance) | 2024-08~ |
| SPY | 425 (gamma_flip), 425 (spot), 415 (gamma_env), 424 (flip_distance) | 2024-07-25~ |
| VIX | 426 (gamma_flip), 427 (spot), 361 (gamma_env), 426 (flip_distance) | 2024-07-25~ |

共 24 個 pkl 成功產生。已整合至 `get_all_series_data.py` 的 tasks list。

### 4. CFTC TFF E-mini S&P 500（get_ctfc_series.py 擴充）

`COTReportCache` 和 `get_cot_data()` 新增 `report_type` 參數（預設 `"legacy_fut"`）。新增 `fetch_cftc_tff_data()` 使用 `traders_in_financial_futures_fut` 報告取得 E-mini S&P 500 的 Asset Manager / Leveraged Fund 持倉。

| 類別 | pkl 檔案 | 說明 |
|------|---------|------|
| Asset Manager | `emini_spx_cme_net_position_asset_mgr.pkl` | AM 淨持倉 |
| Leveraged Fund | `emini_spx_cme_net_position_lev_money.pkl` | LF 淨持倉 |
| % of OI | `emini_spx_cme_net_pct_of_oi_asset_mgr.pkl` / `_lev_money.pkl` | 淨持倉佔 OI 百分比 |

驗證：共 20 個 pkl，1,033 週（2006 年起）。已整合至 `get_all_series_data.py`。

### 5. 槓桿 ETF 資料（get_etf_csv.py + get_m_square_etf.py 擴充）

新增 TQQQ/SQQQ（ProShares CSV fund flow + MacroMicro close/volume）及 SOXL/SOXS（MacroMicro close/volume）。詳見 WN-2026-04-03-槓桿ETF資料抓取擴充.md。

## 功能擴充

### highcharts_utils.py — 新增 `.RVOL` 衍生表達式

仿照 `.DD` / `.REV` 模式，新增 `is_rvol_expression()` 和 `process_rvol()`:

- 格式：`"cboe_SPX.RVOL20"` → 20 日已實現波動率（年化）
- 公式：`log_return.rolling(window).std() * sqrt(252) * 100`
- 同步更新 `generate_chart_data` dispatch chain 和 `resolve_series_title`

驗證：`cboe_SPX.RVOL10` 產生 12,910 筆資料（覆蓋 SPX 全部歷史）。

### highcharts_utils.py — 擴充 `.MA` + 新增 `.TREND` 衍生表達式

**(a) `.MA` 擴充**：`process_ma()` regex 從 `r'(\d+)\.MA(\d+)'` 改為 `r'(.+)\.MA(\d+)'`，支援字串 ID（如 `"cboe_SPX.MA50"`），與 `.RVOL` 模式一致。

**(b) `.TREND` 新增**：CTA 趨勢信號代理
- 格式：`"cboe_SPX.TREND"` → 計算 price 高於幾條 MA (10/20/50/100/200) 的數量
- 輸出 0-5：5=全面做多，0=全面做空
- 用途：Vol Control / CTA 曝險的間接推斷

**(c) `_resolve_operand()` 擴充**：支援 RVOL / MA / TREND 衍生表達式作為二元運算的操作元（如 `("cboe_VIX", '-', "cboe_SPX.RVOL20")` 計算 VRP）。

驗證：`cboe_SPX.MA50` 產生 12,871 筆、`cboe_SPX.TREND` 產生 12,721 筆。

## 四個新 Route

### Route 1：McElligott波動率微結構（14 張圖）

| # | 標題 | 對應文章 | McElligott 概念 | 核心 ids |
|---|------|---------|----------------|---------|
| 1-1 | VVIX/VIX 凸性比率 | **02** VIX/VVIX 動態 | VVIX Never Lies — 凸性壓力偵測 | VVIX/VIX ratio |
| 1-2 | VIX Spot Beta | **02** VIX/VVIX 動態 | VIX 對 SPX 1% 變動的反應強度 | VIX/SPX ratio |
| 1-3 | Spot-Vol 相關性體制 | **02** VIX/VVIX 動態 | Crash-Up（正相關）vs Crash-Down（負相關） | SPX+VIX+VVIX |
| 1-4 | VIX 完整期限結構 | **02** VIX/VVIX 動態 | Contango = Carry Trade 有利；Backwardation = 急性壓力 | VIX1D~VIX1Y |
| 1-5 | VIX 期限結構斜率 | **02** VIX/VVIX 動態 | VIX/VIX3M >1 = Backwardation 量化 | VIX/VIX3M ratio |
| 1-6 | SKEW+GAMMA+SMILE | **01** Dealer Gamma / **02** | SKEW 判斷 crash-down 條件；GAMMA 量化 dealer 曝險 | CBOE 三指標 |
| 1-7 | VRP 策略基準健康度 | **03** VRP 生態系 | $260B Perpetual Vega Supply 的官方追蹤指標 | BXM/PUT/VPD/CNDR |
| 1-8 | SHORTVOL vs LONGVOL | **03** VRP 生態系 | Vol-Selling 直接損益，比率急跌 = 惡性循環啟動 | 比率 + 個別 |
| 1-9 | VIX ETF 資金流向 | **05** 槓桿 ETF | Slide Risk — short VIX 部位累積後的強制回補 | ZSUM 正規化淨流 |
| 1-10 | VIX ETF 成交量異常 | **05** 槓桿 ETF | 投機活動暴增偵測，反射性 vol selling 行為判斷 | UVXY/SVXY volume |
| 1-11 | Put/Call Ratio | **09** 部位與情緒 | P/C >1.2 = 恐慌（Scar Tissue）；<0.75 = 自滿 | MM 1650 |
| 1-12 | iVol vs Realized Vol (VRP) | **03/04** VRP 量化 | VIX - RVol20 = Variance Risk Premium 代理 | VIX-RVOL20 差值 |
| 1-13 | 股票型槓桿 ETF 成交量 | **05** 槓桿 ETF | Synthetic Short Gamma — AUM $129B 日再平衡追漲殺跌 | TQQQ/SQQQ/SOXL/SOXS vol |
| 1-14 | TQQQ/SQQQ Fund Flow | **05** 槓桿 ETF | Nasdaq 槓桿資金方向 — Retail Animal Spirits 代理 | TQQQ/SQQQ fundflow |

### Route 2：McElligott相關性與部位（11 張圖）

| # | 標題 | 對應文章 | McElligott 概念 | 核心 ids |
|---|------|---------|----------------|---------|
| 2-1 | 隱含相關性 vs SPX | **06** 相關性/Dispersion | COR1M 低 = Dispersion 獲利 = index vol 壓制 | COR1M/COR3M |
| 2-2 | 相關性期限結構 | **06** 相關性/Dispersion | COR1M 急超 COR3M = 短期相關性衝擊 | COR1M~COR1Y |
| 2-3 | MGTN vs 市場寬度 | **06** 相關性/Dispersion | 集中度悖論：指數漲但廣度惡化 = Negative Breadth | MGTN+50MA/200MA |
| 2-4 | CFTC 多空比率 | **09** 部位與情緒 | Crowding = Shadow Leverage，極值 = Pain Trade 反轉 | JPY/EUR/AUD |
| 2-5 | 日圓 Carry Trade 壓力 | **09** 部位 / **10** VaR Shock | McElligott's Canary：JPY 空頭下滑 + VVIX 升至 100 | JPY空頭+VVIX |
| 2-6 | 跨資產 Vol 比較 | **06** 相關性/Dispersion | 三大指數 vol 同步飆升 = 系統性壓力（非輪動） | VIX/RVX/VXN |
| 2-7 | VRP vs SPX 相對表現 | **03** VRP 生態系 | Vol-Selling Sharpe 追蹤：做空 vol = 合成做多 Beta | BXM/SPX, PUT/SPX |
| 2-8 | SPX Realized Vol 多窗口 | **04** Vol Control/CTA | rVol 壓縮 → Vol Control 機械式買入（Exposure Toggle） | RVOL10/20/60 |
| 2-9 | E-mini SPX AM vs LF 淨部位 | **09** 部位與情緒 | CFTC TFF：AM 100th %ile = HF Exposure 最佳公開替代 | emini_spx net position |
| 2-10 | E-mini SPX 持倉 % of OI | **09** 部位與情緒 | 淨持倉佔 OI 百分比 — 擁擠度量化 | emini_spx % of OI |
| 2-11 | SPX CTA 趨勢信號 | **04** Vol Control/CTA | MA 交叉計數 (0-5) — CTA 曝險代理 | cboe_SPX.TREND |

### Route 3：McElligott總經與利率（10 張圖）

| # | 標題 | 對應文章 | McElligott 概念 | 核心 ids |
|---|------|---------|----------------|---------|
| 3-1 | 跨市場壓力指標 | **07** 利率 / **08** FCI | Rate Vol → Equity RP 壓縮 → 跨資產傳導鏈 | MOVE+VIX+信用利差 |
| 3-2 | 金融條件反身性 | **08** FCI/流動性 | FCI Reflexivity：市場預期 ↔ Fed 行動的反身性循環 | NFCI+OFR FSI |
| 3-3 | 殖利率曲線（含 2Y） | **07** 利率 | 2Y 對 Fed 路徑最敏感；CTA 債券部位翻轉觸發器 | IRX~TYX+DGS2 |
| 3-4 | 曲線斜率+利率 Vol | **07** 利率 | T10Y2Y 急變 + VXTLT 高 = Rates Regime Change | T10Y2Y+VXTLT |
| 3-5 | 10Y 實質殖利率 | **07** 利率 | 實質殖利率上升 = FCI 實質收緊代理 | DFII10 |
| 3-6 | SOFR+OIS 利差 | **08** FCI/流動性 | SOFR 99th > IORB = 流動性危機；OIS 利差 = Fed 押注 | SOFR 體系 |
| 3-7 | OIS 利差 vs SPX/VIX | **08** FCI/流動性 | Landing 概率分佈：Soft/Hard/No Landing 的 repricing | 1Y-3M OIS |
| 3-8 | 跨資產波動率 | **07** 利率 / **10** VaR Shock | 四大資產 vol 同步高位 = 跨資產波動率共振 | VIX/VXTLT/MOVE/OVX |
| 3-9 | ACM Term Premium | **07** 利率 | 「2025 年風險資產的真正總經風險催化劑」 | ACMTP02/05/10+KW |
| 3-10 | Money Market Fund AUM | **09** 部位與情緒 | MMF AUM 90th+ %ile = 大量現金觀望中 | MMMFFAQ027S |

### Route 4：McElligottDealerGamma（8 張圖）

| # | 標題 | 對應文章 | McElligott 概念 | 核心 ids |
|---|------|---------|----------------|---------|
| 4-1 | SPX Gamma Flip vs Price | **01** Dealer Gamma | 最重要單一水準：Long Gamma = 穩定器；Short = 加速器 | SPX spot+flip+VIX |
| 4-2 | SPX 完整結構圖 | **01** Dealer Gamma | Flip/Call Wall/Put Wall/Field — Tactical Map | 完整結構 |
| 4-3 | SPY Gamma Flip | **01** Dealer Gamma | ETF 級對照，0DTE SPY 選擇權使 SPY gamma 不可忽視 | SPY spot+flip |
| 4-4 | SPX Gamma Environment | **01** Dealer Gamma / **04** | 體制二元判斷：Positive Gamma = 良性；Negative = 惡性 | gamma_env+VIX+VVIX |
| 4-5 | VIX Gamma Flip | **01** Dealer Gamma | VIX 有獨立 dealer gamma，VIX spike 自我加速機制 | VIX spot+flip |
| 4-6 | VIX 完整結構圖 | **01** Dealer Gamma | VIX Call Wall 被突破 = dealer 被迫買 VIX = 加速上漲 | VIX 完整結構 |
| 4-7 | VIX Gamma Environment | **01** Dealer Gamma | Negative Gamma + VVIX 飆升 = VIX ETN 被迫回補 = overshoot | VIX gamma_env+VVIX |
| 4-8 | Gamma Flip Distance | **01** Dealer Gamma / **10** | 雙重 Negative Gamma 預警：SPX 負 + VIX 負 = VaR Shock 級別 | SPX+VIX flip_distance% |

## 驗證結果

Flask 啟動於 `http://127.0.0.1:6002`，24 個 group 全部載入成功（含 4 個 McElligott route）。

API 測試結果（擴充後）：
```
McElligott波動率微結構  => 200 ✓  14 charts
McElligott相關性與部位  => 200 ✓  11 charts
McElligott總經與利率    => 200 ✓  10 charts
McElligottDealerGamma  => 200 ✓   8 charts
```

共 43 張圖，全部正常載入。

## 修改檔案清單

| 檔案 | 動作 |
|------|------|
| `get_cboe_index.py` | 修改 — 擴充 CBOE_INDICES +22 symbols |
| `get_all_series_data.py` | 修改 — 新增 FRED (DGS2/T10Y2Y/DFII10/MMMFFAQ027S) + GEX + CFTC TFF |
| `get_gex_series.py` | **新建** — GEX-lieta SQLite → pkl 橋接（含 flip_distance） |
| `get_ctfc_series.py` | 修改 — 新增 TFF report_type 支援 + E-mini SPX + tuple report_name 相容 |
| `get_etf_csv.py` | 修改 — 新增 TQQQ/SQQQ fund flow（ProShares CSV） |
| `get_m_square_etf.py` | 修改 — 新增 TQQQ/SQQQ/SOXL/SOXS（MacroMicro close/volume） |
| `flask_highcharts/app/utils/highcharts_utils.py` | 修改 — `.RVOL` + `.MA` 擴充 + `.TREND` 新增 + `_resolve_operand` 擴充 |
| `flask_highcharts/app/routes/McElligott波動率微結構.py` | **新建** → 修改 — Route 1（11→14 charts） |
| `flask_highcharts/app/routes/McElligott相關性與部位.py` | **新建** → 修改 — Route 2（8→11 charts） |
| `flask_highcharts/app/routes/McElligott總經與利率.py` | **新建** → 修改 — Route 3（9→10 charts） |
| `flask_highcharts/app/routes/McElligottDealerGamma.py` | **新建** — Route 4（8 charts） |

## 踩坑記錄

- **多個 Flask 進程佔用 port 6002**：Windows 上舊 Flask 進程未被清理，新啟動的 server 能 bind 但 client 被路由到舊進程（使用舊程式碼）。需用 `netstat -ano | Select-String ":6002"` 找到所有 LISTENING PID 並 `taskkill` 後重啟。
- **FRED API 時區問題**：`pystlouisfed` 使用本地日期作為 `realtime_start`，但 FRED API 以美東時間為準。跨日時段（UTC+8 已是隔日但 ET 仍是前一天）會導致 400 Bad Request。`MMMFFAQ027S` 改用直接 REST API 呼叫避開此問題。
- **FRED WRMFSL 已停更**：原計畫使用週頻 `WRMFSL`，但該 series 於 2021 年停更。改用季頻 `MMMFFAQ027S`（303 筆，1945~2025Q4）。
- **CFTC report_name 含連字號**：`get_prefix_from_name()` 原用 `split('-')` 分割商品名與交易所，但 "E-MINI S&P 500" 自身含 `-`，導致 prefix 錯誤為 `e_` 而非 `emini_spx_`。改用 `split(' - ')` 修正。
