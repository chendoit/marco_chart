# WN-2026-04-02 McElligott 框架中的專有/付費資料與替代方案

## 起因

閱讀 McElligott 10 篇分析框架文章後，系統性盤點其引用的所有指標，發現有 8 類核心資料為 Nomura 專有模型或付費來源，無法免費取得。本文記錄每項資料的具體內容、在 McElligott 框架中的角色、以及可行的替代/近似方案。

---

## 1. Vol Control / Target Volatility 配置（文章 04）

### 原始資料
- **Vol Control Allocation %ile**：Nomura QIS 模型估算的 Target Volatility 策略當前美股配置水準，以歷史百分位表達（3Y 和 10Y lookback）
- **Vol Control Rebalance Projection Table**：情境表，列出不同 SPX 日均波幅（0%, 0.5%, 1%, 1.5%...5%）下，未來 +1w/+2w/+1m/+2m/+3m 的預計美股期貨買/賣金額（$B）
- **Vol Control 1d Buy/Sell**：單日隱含再平衡金額及其百分位排名
- **Trailing rVol Dropoff Calendar**：逐日列出哪些歷史高波動日即將退出 1m/3m rVol 計算窗口

### 在框架中的角色
Vol Control 是 McElligott 框架中**最大的機械式股票配置流**。2024 年 10 月的預測顯示：SPX 日均波幅 0% 時，+1 週買入 +$45.5B（99th %ile）。這是 "Invisible Bid" 的主要來源。

### 替代方案
- **SPX Realized Vol 多窗口**（可自行計算）：10d/20d/60d trailing rVol。rVol 壓縮到極低（如 10d rVol < 8）= Vol Control 正在或即將大量買入
- **rVol vs iVol 比率**：rVol 持續低於 iVol = VRP 正值環境 = Vol Control 買入條件成立
- **邏輯推導**：Dealer Long Gamma（從 GEX-lieta 的 gamma_env = positive 觀察）→ rVol 被壓縮 → Vol Control 機械式買入。因此 gamma_env + rVol 水準的組合可間接推斷 Vol Control 行為
- **CBOE SHORTVOL DD60**：SHORTVOL 回撤深度反映 Vol Control 被迫賣出的程度

### 資訊缺口嚴重度：高
Vol Control 每週可以產生 $20-45B 的買/賣流，是短期最具預測力的流量指標之一。無直接替代。

---

## 2. CTA / Trend-Following 部位與觸發水準（文章 04）

### 原始資料
- **CTA Net $ Exposure by Asset Class**：Nomura QIS 模型估算的 CTA 跨資產配置（股票、債券、STIR、FX、商品），含 % 權重、百分位、隱含 $ 名義金額
- **CTA Signal Level**：每個合約的當前趨勢信號強度（-100% 到 +100%）
- **CTA Trigger Level Bands**：精確的價格水準，列出各全球股指在 -4%/-2%/+2%/+4% 移動時會觸發多少 $B 的買/賣
- **SG Trend Index**：Societe Generale 編制的 10 大 CTA 基金表現指數

### 在框架中的角色
CTA 在 2024 年 8 月從高位到低位賣出了 -$56B 全球股票。觸發水準提供精確的 "cliff levels"，例如 ES ~5332 是本地賣出觸發點。CTA 的倉位翻轉速度極快——兩週內 +$36B 股票回購。

### 替代方案
- **SG Trend Index**：可嘗試從 [SG Prime Services](https://cib.societegenerale.com/en/sg-prime-services-indices/) 取得每日資料（聲稱免費提供，但需確認實際可及性）
- **價格趨勢信號自建**：用 SPX 的 10d/20d/50d/100d/200d 移動平均線交叉作為 CTA 信號代理。多數 CTA 使用多時間窗口趨勢跟蹤，MA 交叉是最簡單的近似
- **跨資產動量**：追蹤 SPX、UST 10Y、USD Index、Gold、Crude Oil 的 3m/6m 動量，判斷 CTA 可能持有的方向
- **CFTC Leveraged Fund Futures Positioning**：已有 FX 部分（JPY/EUR/AUD/CRU），可擴充到 S&P 500 E-mini（CFTC 有此合約的 COT 報告）

### 資訊缺口嚴重度：中高
CTA 觸發水準是高價值的戰術資訊，但自建趨勢信號可提供方向性近似。

---

## 3. 槓桿型 ETF AUM 時間序列（文章 05）

### 原始資料
- **Leveraged ETF Total AUM**：所有槓桿/反向 ETF 的總資產，含百分位排名（2024 年底 $129B，100th %ile）
- **AUM Category Breakdown**：按類別（Tech Leadership 89%, All Other 11%）
- **1w/1m Cumulative Rebalance** ($B, %ile)：過去一週/月的累計 EOD 再平衡金額
- **Daily Projected Rebalance by Sector**：即時估算當日各板塊的 EOD 再平衡金額

### 在框架中的角色
McElligott 稱槓桿型 ETF 為 "Synthetic Short Gamma"——2024 年 8 月單日再平衡 -$29.7B（vs SPX -1.3%），接近 2020 年 3 月疫情崩盤的 -$31.7B，但當時 AUM 只有現在的四分之一。AUM 越大，同樣的百分比波動產生的再平衡流量越大。

### 替代方案
- **TQQQ/SQQQ/SSO/SDS Volume**：槓桿 ETF 成交量急升 = 投機活動暴增，間接反映 AUM 膨脹和再平衡壓力
- **自行計算再平衡估計**：用已知的主要槓桿 ETF（TQQQ, SQQQ, SSO, SDS, SPXL, SPXS, SOXL, SOXS, UPRO, SDOW）的每日收盤價 + 成交量，結合槓桿比率（2x/3x），可粗略估算日再平衡金額
- **CBOE MGTN (Magnificent 10 Index)**：間接追蹤槓桿 ETF 集中度最高的標的走勢
- **VIX ETF Fund Flow** + **Volume**（已有資料）：VIX 槓桿產品（UVXY, UVIX）的資金流和成交量是 "Slide Risk" 的直接代理

### 資訊缺口嚴重度：中
精確的 AUM 和再平衡金額無法取得，但成交量和自建計算可提供合理近似。

---

## 4. Dispersion PnL — Top 50（文章 06）

### 原始資料
- **S&P Top 50 Dispersion PnL**：Nomura Vol 團隊追蹤的標準 Dispersion Trade（做多個股波動率 + 做空指數波動率）的損益
- 包含：PnL（vol points）、Sharpe、Max Drawdown、PnL %ile（across 1w/2w/1m/3m/YTD/1Y）

### 在框架中的角色
Dispersion trade 的虧損是 McElligott 框架中 "相關性衝擊" 的即時量化。2024 年 8 月：-6.1v PnL = 0th %ile（兩年最差單週）。當 Dispersion bleed 時，做空指數波動率的那一腿被迫回補 = 指數 vol 買壓飆升 = 惡性循環觸發。

### 替代方案
- **CBOE COR1M / COR3M**（已驗證 CDN 可用）：隱含相關性是 Dispersion PnL 的**反向代理**。COR1M 急升 = Dispersion 正在虧損；COR1M 在 1st %ile = Dispersion 正在大賺
- **COR1M 急速變化率**：COR1M 的 5 日變化量可近似 Dispersion 的短期 PnL 方向
- **CBOE COR10D vs COR3M 比率**：短期 vs 中期相關性比率急升 = 短期相關性衝擊正在發生
- **Mag7/8 vs Equal-Weight SPX**：MGTN（Mag 10）vs SPX 的報酬差異可近似 "集中度驅動的偽低相關性"

### 資訊缺口嚴重度：中
COR1M/COR3M 提供了良好的反向代理，雖然無法精確量化 PnL，但可捕捉相關性體制轉換。

---

## 5. EPFR Fund Flows（文章 09）

### 原始資料
- **EPFR Weekly Fund Flows**：全球股票/債券/貨幣市場基金的每週資金流數據，以百分位排名（1w/4w/3m/1y）
- **Passive vs Active Flows**：結構性流向分歧（Passive 95-99th %ile vs Active 1-8th %ile）
- **EM vs DM Equity Flows**：新興市場 vs 已開發市場的風險偏好

### 在框架中的角色
EPFR 是 McElligott 判斷 "群眾在哪裡" 的主要工具。2024 年初 US Equity flows 在 94th %ile = 擁擠看多。2024 年 8 月後 Leveraged Fund 降至 1st %ile = 極端反向信號。

### 替代方案
- **AAII Sentiment Survey**（已有 `AAII情緒.py` route）：每週散戶情緒調查，Bullish/Bearish 分布可近似零售投資者的風險偏好
- **CFTC Positioning**（已有 JPY/EUR/AUD/CRU）：投機者的期貨部位反映機構風險偏好方向
- **VIX ETF Fund Flow**（已有）：做多 VIX ETF 資金流急增 = 避險需求；做空 VIX ETF 資金流增 = 風險偏好回歸
- **Money Market Fund AUM**（FRED series: MMMFFAQ027S 或 ICI 週報）：MMF AUM 持續在 90th+ %ile = 大量現金觀望中
- **ETF.com 或 ICI Weekly Data**：免費的 ETF 資金流摘要，但粒度較 EPFR 粗

### 資訊缺口嚴重度：中
AAII + CFTC + VIX ETF Flow 的組合提供多維度的部位/情緒近似。

---

## 6. 對沖基金 Net/Gross Exposure（文章 09）

### 原始資料
- **HF Net Exposure**：對沖基金多空淨曝險百分位
- **HF Gross Exposure**：對沖基金總槓桿百分位（100th %ile = 最大槓桿風險）
- **Mutual Fund Beta to Mag7/Top50**：主動基金對大型股的 beta 曝險

### 在框架中的角色
這是 McElligott "Pain Trade" 判斷的核心：低 Net + 市場在 ATH = "trading like they're short" = Pain Trade 是漲。高 Gross = 去槓桿風險極大。2024 年 8 月 Leveraged Fund 降至 1st %ile = 強烈反向做多信號。

### 替代方案
- **CFTC E-mini S&P 500 Positioning**：可從 CFTC COT 報告取得 Asset Manager 和 Leveraged Fund 的 E-mini SPX 期貨部位。這是最接近的公開替代——McElligott 本人也引用此數據（"CFTC/TFF Asset Manager Futures at 100th %ile"）
- **Put/Call Ratio**（計畫中已有）：極端高 P/C ratio = 過度避險 = 低隱含淨曝險
- **CBOE SKEW + Call Skew 組合**：Put Skew 高 + Call Skew 低 = 過度避險 = 類似於低 Net Exposure
- **VIX/VVIX 結構**：VVIX 偏高但 VIX 中等 = "wider distribution" = 市場分歧大，暗示部位兩極化

### 資訊缺口嚴重度：高
HF Gross Exposure 是系統性風險的最直接量化，無完美替代。CFTC E-mini positioning 是最佳公開代理。

---

## 7. SPX Daily Options PnL Summary（文章 03）

### 原始資料
- **系統性 Options Selling 策略的 Sharpe Ratio 表**：涵蓋多種策略（Sell Daily ATM Straddle, ATM Put, ATM Call, Strangle, 25-delta P/C, Risk Reversal 等）
- 時間窗口：1d/10d/20d/60d/YTD/1Y 的 Sharpe、PnL、Max Drawdown
- 這是 McElligott 判斷 VRP trade 是否 "working" 的即時脈搏

### 在框架中的角色
VRP Sharpe 從 +19.1（2024 年 12 月）崩到 -3.4（2024 年 8 月），標誌著良性循環的完全反轉。這張表是 "Perpetual Vega Supply" 健康度的最直接量化。

### 替代方案
- **CBOE BXM (BuyWrite Index)**（已驗證 CDN 可用）：S&P 500 BuyWrite 策略的官方基準指數。BXM vs SPX 的相對表現 = Covered Call 策略的超額收益/虧損
- **CBOE PUT (PutWrite Index)**（已驗證 CDN 可用）：PutWrite 策略基準。PUT 回撤 = Put selling 受創
- **CBOE VPD (VIX Premium Strategy)**（已驗證 CDN 可用）：VIX Premium 收割策略基準
- **CBOE CNDR (Iron Condor)**（已驗證 CDN 可用）：Iron Condor 策略基準。CNDR 回撤 = Vol selling 全面受創
- **組合使用**：BXM + PUT + VPD + CNDR 的表現 vs SPX，可建構 "VRP 策略綜合健康度" 指標
- **SHORTVOL vs LONGVOL 比率**（已在計畫中）：SHORTVOL 急跌 = VRP 受創

### 資訊缺口嚴重度：中低
CBOE 策略指數提供了良好的替代——雖然不是逐日 Sharpe ratio，但可觀察 VRP 策略群組的相對表現和回撤。

---

## 8. Monthly Vega Supply Estimate（文章 03）

### 原始資料
- **Derivatives/Income Fund + Exo Vega Supply Per Month**：Nomura Vol 團隊估算的每月結構性 Vega 供給量（2024 年 11 月：268M vega/月）
- **ETFs with Embedded Options Selling Strategies — AUM Growth**：Options-selling ETF 的 AUM 變化（Past Week/Month/3M/YTD），如 +$30B YTD

### 在框架中的角色
這是 "Perpetual Vega Supply" 的直接量化——AUM 越大，結構性 vol 供給越大，dealer 被塞入的 Long Gamma 越多，rVol 壓縮越嚴重。是良性/惡性循環的上游輸入。

### 替代方案
- **無直接替代**：精確的月度 Vega 供給量是 Nomura 內部模型的產出
- **間接代理 1**：CBOE BXM/PUT AUM（如果能取得）或其指數水準的趨勢——持續創新高 = Vega 供給持續增加
- **間接代理 2**：SPX ATM iVol vs rVol 的差距持續擴大 = Vega 供給過剩（options 定價持續高於實際波動）
- **間接代理 3**：Dealer Gamma 持續在 positive territory（從 GEX-lieta）= 有人在持續賣出 options 給 dealer
- **間接代理 4**：QYLD/XYLD ETF 的 AUM 或成交量趨勢（這些是最大的 systematic covered call 產品）

### 資訊缺口嚴重度：中
整體 Vega 供給的精確量化無法取得，但 Dealer Gamma 狀態 + VRP 策略指數 + rVol/iVol 差距的組合可推斷供給是否充足。

---

## 替代方案總覽圖

```
McElligott 專有資料          最佳免費替代
─────────────────          ─────────────
Vol Control Allocation  →  SPX rVol (10d/20d/60d) + Gamma Env
CTA Positioning         →  CFTC E-mini COT + 自建 MA 趨勢信號
Lev ETF AUM             →  TQQQ/SQQQ Volume + 自算再平衡估計
Dispersion PnL          →  CBOE COR1M / COR3M
EPFR Fund Flows         →  AAII Sentiment + CFTC + VIX ETF Flow
HF Net/Gross            →  CFTC E-mini COT (Asset Mgr + Lev Fund)
Options PnL Summary     →  CBOE BXM + PUT + VPD + CNDR
Monthly Vega Supply     →  Dealer Gamma state + iVol/rVol gap
```

## 下一步

1. 優先擴充 CBOE CDN 抓取（A 類資料），這是成本最低、價值最高的改進
2. 擴充 FRED API 抓取殖利率和實質殖利率（B 類）
3. 研究 CFTC E-mini S&P 500 COT 報告的抓取可行性（替代 HF positioning）
4. 對於可計算指標（C 類），在建構 route 時一併實作
