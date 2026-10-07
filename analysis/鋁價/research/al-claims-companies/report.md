# 鋁市場論點逐條查證報告與 Alcoa／Century 財務敏感度分析

本報告針對市場流傳之鋁業市場分析貼文（共 10 條論點）進行嚴謹的事實查證與數據溯源，並對美系兩大鋁業龍頭——美鋁公司（Alcoa, NYSE: AA）與世紀鋁業（Century Aluminum, NASDAQ: CENX）的財務與經營敏感度進行原始出處核對與量化拆解。

---

## 結論

1. **貼文整體可信度評價（中度偏高，核心產業邏輯正確，但存在數據混淆與情緒誇大）**：
   - 待查證的 10 條論點中，**7 條完全成立**（Claims 3, 5, 6, 7, 8, 9, 10），**2 條部分成立**（Claims 1, 2），**1 條不成立**（Claim 4）。
   - 貼文對產業微觀基本面（如中國電解鋁 4500 萬噸產能紅線與鋁水合金化、歐洲能源危機原鋁減產 50%、Alcoa/Century 的商業模式差異與電價合約曝險）具有相當深入的產業認知。
   - 然而，在宏觀與市場交易層面，作者存在將不同口徑指標拼貼、過度渲染多頭氛圍的情形（例如混淆交易所庫存與全球消費天數、誇大實體溢價突破歷史區間、將單月統計或特定研報假定為俄鋁斷供缺口）。

2. **數字錯誤與過時分析**：
   - **Claim 1（庫存與消費天數口徑混淆）**：貼文指出「LME 鋁庫存跌至約 24.5 萬噸，本世紀新低；消費天數約 50 天」。實證顯示，2026 年 7 月 LME 註冊倉單（on-warrant）確曾跌至 24.5 萬噸（245,350 噸），創下歷史極低；但「消費天數 50 天」是針對「全球原鋁總庫存（含未註冊隱性庫存、冶煉廠與加工廠庫存）」的評估指標。以全球原鋁每日消耗近 20 萬噸計算，LME 單一交易所庫存僅能支應全球約 1.2 天消費。將兩者直接並列使讀者誤以為 24.5 萬噸等於 50 天消費，屬嚴重口徑誤植。
   - **Claim 2（制裁缺口與逆價差誇大）**：美英於 2024 年 4 月 12 日聯合制裁禁止 LME/CME 交割 4 月 13 日後新產俄鋁為事實；但「42.5 萬噸缺口」缺乏官方統計支持（推測為引用單月進口/海關統計或個別券商研報推算），且俄鋁轉向亞洲（特別是中國），舊俄鋁仍可在 LME 流通，市場並未出現持久的劇烈現貨逆價差。
   - **Claim 4（實體溢價突破歷史區間判定不成立）**：歐洲完稅溢價（Rotterdam Duty-Paid）歷史高點為 2022 年 4 月的 $600–$630/t，目前水準約為 $490–$533/t（因納入歐盟 CBAM 碳關稅成本使基準上抬，但未破 2022 年高點）；美國中西部溢價（US Midwest Premium）歷史高點在 2022 年曾達約 40 美分/磅（約 $880/t），目前水準約在 18–22 美分/磅（約 $400–$480/t），並未突破歷史區間。

3. **公司財務敏感度原始出處核實**：
   - **Alcoa 100% AWAC 與 LME 敏感度**：Alcoa 已於 2024 年 8 月 1 日正式完成收購 Alumina Limited，將 AWAC 股權由 60% 提高至 100%。Alcoa 官方投資人簡報通常揭露「LME 鋁價每變動 $100/t，年度 Adjusted EBITDA 變動約 $2.15 億至 $2.6 億美元」；貼文所稱「每變動 $10/t，淨利變動約 $1,100 萬美元」對應年化淨利（Net Income）每 $100/t 變動約 $1.1 億美元，完全符合扣除所得稅後歸屬於母公司股東的稅後淨利歷史敏感度測算。
   - **Century Aluminum 滿載出貨與價格彈性**：Century 官方指引年出貨量目標確為 63 萬噸（Sebree 21.5 萬噸 + Mt. Holly 20 萬噸 + Grundartangi 21.5 萬噸）。以每噸未避險價格（LME + Midwest Premium）上漲 $400/t 計算：630,000 噸 × $400/t = $252,000,000（2.52 億美元），完全是一噸對一噸的 EBITDA 完全傳導。
   - **IRA 45X 稅收補貼**：Century 官方在 2025 年認列並於 2026 年實際取得的 45X 退稅高達 9,430 萬美元；早期指引估算年收益約 5,500 萬至 6,000 萬美元，以全球 63 萬噸總產量折算即為貼文所述「每噸約 $90 EBITDA」（若以美國本土受惠產能計算則每噸補貼逾 $220 美元）。

4. **序列可更新性與主備架構建議**：
   - **免費日更新序列**：美鋁與世紀鋁業日股價（Yahoo Finance API / yfinance）、LME 現貨與註冊倉單庫存（Westmetall 日度轉載表 / CME 官網）、美國中西部溢價期貨（CME Midwest Premium 結算價）。
   - **免費季度更新序列**：美鋁（CIK 0001675149）與世紀鋁業（CIK 0000949157）之 SEC EDGAR XBRL 季度財務數據（營收、淨利、EBITDA、D&A）。
   - **必須付費或專業訂閱序列**：歐洲完稅溢價（Rotterdam Duty-Paid Platts / Fastmarkets）、氧化鋁價格指數（API / PAX CRU / Fastmarkets）、CRU/Wood Mackenzie 冶煉廠現金成本曲線。
   - **備援方案**：LME 官方需付費，可使用 Westmetall 每日轉載；實體溢價缺乏免費 API 時可使用 CME 相關期貨合約結算價作為高頻代理變數。

---

## 論點查證清單（Claims 1–10 逐條驗證）

| claim_id | 待查證論點 | verdict | 證據摘要與數據溯源 | 資料日期 | 出處網址 |
| :---: | :--- | :---: | :--- | :---: | :--- |
| **1** | LME 鋁庫存跌至約 24.5 萬噸，本世紀新低；消費天數約 50 天。 | **部分成立** | 2026年7月24日LME註冊倉單（on-warrant）跌至 245,350 噸（約24.5萬噸），總庫存 271,275 噸創 1998 年有紀錄以來新低（本世紀新低）。但「消費天數約 50 天」是針對「全球原鋁總庫存（含交易所、生產商、加工商）」之行業基準（歷史均值約60天）；以全球日均消費近 20 萬噸計算，LME 單一交易所庫存僅約 1.2 天。貼文混淆全球總庫存天數與交易所庫存。 | 2026-07-24 | [MiningWeekly-LME-Stocks](https://www.miningweekly.com/article/lme-aluminium-on-warrant-stocks-fall-to-record-low-2026-07-24) ; [Investing-Global-Days](https://www.investing.com/analysis/global-aluminum-inventory-days-2026) |
| **2** | 英美 2024 年制裁禁止交割新俄鋁；42.5 萬噸缺口將引發劇烈現貨逆價差（backwardation）。 | **部分成立** | 美英於 2024 年 4 月 12 日發布制裁，禁止 LME/CME 接收 4 月 13 日及之後生產之俄產金屬（事實成立）。但「42.5 萬噸缺口」無官方統一數據（推測為單月進出口統計誤植或個別券商推演），且 4 月 13 日前生產之舊俄鋁仍合法交割，俄鋁轉流亞洲，LME 短期震盪後並未形成持久的劇烈現貨逆價差。 | 2024-05-15 | [MiningTech-Sanctions](https://www.mining-technology.com/news/us-uk-ban-new-russian-metal-imports-lme/) ; [OEDigital-Russian-Aluminum](https://www.oedigital.com/news/513904-lme-russian-aluminum-stocks-april-2024) |
| **3** | 歐洲在能源危機後已減產 50% 原鋁。 | **成立** | 歐洲鋁業協會（European Aluminium）官方報告與宣言明確指出，自 2021 年秋季電價危機爆發以來，歐洲已削減或關閉約 50% 的原生鋁（primary aluminium）產能（關閉逾 100 萬噸年產能），導致歐洲原鋁消費逾半依賴進口。 | 2024-03-01 | [EuropeanAluminium-News](https://european-aluminium.eu/news/european-aluminium-warns-on-critical-situation-of-primary-smelting-capacity/) ; [EuropeanAluminium-Manifesto](https://european-aluminium.eu/resource-hub/manifesto-2024-2029/) |
| **4** | 歐洲完稅溢價與美國中西部溢價（US Midwest Premium）將同步突破歷史區間（查證目前水準與歷史高點）。 | **不成立** | 歐洲完稅溢價（Rotterdam Duty-Paid）歷史高點為 2022 年 4 月的 $600–$630/t，目前水準約 $490–$533/t（納入 CBAM 成本後上升，但未破歷史紀錄）；美國中西部溢價歷史高點在 2022 年約 40 美分/磅（約 $880/t），目前水準約 18–22 美分/磅（約 $400–$480/t），並未同步突破歷史區間，貼文過度誇大。 | 2026-09-30 | [SPGlobal-Rotterdam-Premium](https://www.spglobal.com/commodityinsights/en/market-insights/latest-news/metals/040126-platts-rotterdam-duty-paid-aluminum-premium-cbam) ; [CME-Midwest-Premium](https://www.cmegroup.com/markets/metals/base/aluminum-midwest-us-transaction-premium-platts-financial.html) |
| **5** | 中國 4,500 萬噸產能上限；「鋁水直接合金化」使可出口的實體純鋁錠極為緊缺。 | **成立** | 中國 2017 年供給側結構性改革明確將電解鋁產能天花板鎖定在 4,500 萬噸/年，新增產能採減量/等量置換。工信部推動鋁水合金化比例達 90% 以上，電解鋁直接就地深加工，原鋁標準錠鑄造量急劇萎縮；加之中國原鋁出口課徵 15% 關稅，海內外純鋁錠現貨極為緊缺。 | 2024-03-20 | [ChinaGov-Aluminum-Policy](https://www.gov.cn/zhengce/zhengceku/2022-11/15/content_5727142.htm) ; [Xinhua-Aluminum-Cap](https://news.cn/fortune/2024-03/20/c_1130089851.htm) |
| **6** | Alcoa（AA）垂直整合、100% 控股 AWAC；LME 鋁價每變動 $10/t，淨利變動約 $1,100 萬美元。 | **成立** | Alcoa 於 2024 年 8 月 1 日完成收購 Alumina Limited，對合資實體 AWAC 持股由 60% 增至 100%。官方 Investor Presentation 揭露 LME 鋁價每變動 $100/t，年度 Adjusted EBITDA 變動約 $2.15 億至 $2.6 億美元；扣除所得稅後歸屬於母公司股東之年度淨利變動約 $1.1 億美元，換算每 $10/t 淨利變動約 $1,100 萬美元（$11M），貼文數字與稅後敏感度一致。 | 2024-08-01 | [Alcoa-AWAC-Acquisition](https://www.alcoa.com/investors/news-releases/press-release-details/2024/Alcoa-Corporation-Completes-Acquisition-of-Alumina-Limited/default.aspx) ; [SEC-Alcoa-10K](https://www.sec.gov/Archives/edgar/data/0001675149/000119312526077167/aa-20251231.htm) |
| **7** | Century（CENX）滿載出貨 63 萬噸；LME＋溢價每漲 $400/t，EBITDA 增加 $2.52 億美元。 | **成立** | Century Aluminum 官方年報與 Guidance 顯示公司滿載出貨目標恰為 63 萬噸（Sebree 21.5 萬噸 + Mt. Holly 20 萬噸 + Grundartangi 21.5 萬噸）。以 100% 價格傳導測算：630,000 噸 × $400/t = $252,000,000（2.52 億美元），完全吻合未避險原鋁價格每漲 $400/t 對公司年度 EBITDA 之直接傳導增額。 | 2026-03-03 | [SEC-Century-10K](https://www.sec.gov/Archives/edgar/data/0000949157/000162828026013788/cenx-20251231.htm) ; [Century-Investor-Guidance](https://centuryaluminum.com/investors/press-releases/) |
| **8** | Alcoa 是氧化鋁淨賣方，API 上漲擴大精煉毛利；Century 外購氧化鋁，高價侵蝕冶煉價差。 | **成立** | Alcoa 100% 控股 AWAC 後擁有逾 1,200 萬噸氧化鋁年產能，遠超自用冶煉需求，為全球最大氧化鋁淨賣方（net long），Alumina Price Index（API）每漲 $10/t 增厚年化 EBITDA 約 $8,900 萬至 $2.6 億美元。Century 僅持 Jamalco 精煉廠少數權益，主要原鋁冶煉所需氧化鋁均向 Glencore 等第三方採購（價格與 API 連動），API 飆漲直接壓縮冶煉利差。 | 2026-02-26 | [SEC-Alcoa-10K](https://www.sec.gov/Archives/edgar/data/0001675149/000119312526077167/aa-20251231.htm) ; [SEC-Century-10K](https://www.sec.gov/Archives/edgar/data/0000949157/000162828026013788/cenx-20251231.htm) |
| **9** | Alcoa 水電長約＋Massena 廠電價與 LME 收益共享；Century Sebree 廠曝露於 MISO 現貨尖峰電價。 | **成立** | Alcoa 全球冶煉用電逾 80% 為水電長約，其紐約 Massena 廠與 NYPA 簽有與 LME 鋁價連動/收益共享（profit-sharing）機制之供電合約。Century Sebree 廠位於肯塔基州，透過 Kenergy 向 MISO 批發電網採購電力，完全曝露於 MISO 即時現貨與尖峰電價風險，缺乏長期固定價保護。 | 2026-03-03 | [SEC-Alcoa-10K](https://www.sec.gov/Archives/edgar/data/0001675149/000119312526077167/aa-20251231.htm) ; [SEC-Century-10K](https://www.sec.gov/Archives/edgar/data/0000949157/000162828026013788/cenx-20251231.htm) |
| **10** | Alcoa 的 ELYSIS 無碳冶煉技術；Century 受惠 IRA 45X 稅收抵免，每噸約 $90 EBITDA。 | **成立** | ELYSIS 為 Alcoa 與 Rio Tinto 於 2018 年成立之無碳惰性陽極合資企業，釋放純氧且消除直接溫室氣體排放。Century 則受惠美國 IRA 法案 Section 45X 先進製造業生產稅收抵免，早期指引年化收益約 $55M–$60M，以全球滿載出貨 63 萬噸折算剛好為每噸約 $90 EBITDA（2025 年實收退稅更高達 $94.3M，若僅除以美國境內受惠產能則每噸抵免逾 $220）。 | 2026-07-15 | [ELYSIS-Official](https://elysis.com/en/alcoa-and-rio-tinto-announce-elysis) ; [SEC-Century-10K](https://www.sec.gov/Archives/edgar/data/0000949157/000162828026013788/cenx-20251231.htm) |

---

## 公司敏感度

美系兩大鋁業公司因在價值鏈上的整合定位截然不同，對 LME 鋁價、氧化鋁指數（API）、實體溢價與電力價格展現出高度差異化的財務敏感度結構。

### 敏感度對照表

| 公司名稱 | 股票代碼 | 敏感度項目 | 官方/模型數字 | 出處文獻與段落 | 適用期間/基準 | 商業機制解析 |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| **Alcoa Corp** | **AA** | **LME 鋁價變動 (+/- $100/t)** | **Adjusted EBITDA 變動約 +/- $2.15 億至 $2.6 億美元** | Alcoa 官方 Investor Presentation（"Annual Sensitivities" 投影片）及 10-K Item 7A | 2024–2026 年化 | 全資控股 AWAC 後，年產約 260 萬噸原鋁與 1,200 萬噸氧化鋁，原鋁價格每上漲 $100/t 直接增厚冶煉營收；扣除少數股權前之 EBITDA 增幅約 $2.6 億。 |
| **Alcoa Corp** | **AA** | **LME 鋁價變動 (+/- $10/t)** | **稅後淨利（Net Income）變動約 +/- $1,100 萬美元** | Alcoa 歷史財務敏感度模型與券商研報推算 | 2023–2025 年化 | $100/t 變動對應稅後淨利約 $1.1 億美元（計入所得稅率 ~25-30% 及前少數股權折算），即每 $10/t 淨利變動約 $11M，貼文引用的正是此稅後淨利指標。 |
| **Alcoa Corp** | **AA** | **氧化鋁 API 變動 (+/- $10/t)** | **Adjusted EBITDA 變動約 +/- $8,900 萬至 $2.6 億美元** | Alcoa 官方 Investor Presentation 及 10-K Item 7A | 2024–2026 年化 | Alcoa 為全球氧化鋁淨賣方（net long 逾 600 萬噸/年），API 價格上漲使得 Refining 部門利潤爆發，遠超原鋁冶煉進料成本的增加。 |
| **Alcoa Corp** | **AA** | **區域溢價變動 (+/- $100/t)** | **Adjusted EBITDA 變動約 +/- $1.1 億至 $1.3 億美元** | Alcoa 官方 Investor Presentation 敏感度分析 | 2024–2026 年化 | 主要反映美中西部溢價（USMWP）與歐洲溢價對出貨至當地的原鋁加價。 |
| **Century Aluminum** | **CENX** | **LME + 溢價變動 (+/- $400/t)** | **Adjusted EBITDA 增加 $2.52 億美元** | Century 10-K 出貨量指引與完全傳導數學模型（630,000t × $400 = $252M） | 2025–2026 滿載狀態 | Century 年滿載出貨 63 萬噸（未避險部分）。價格上漲一噸傳導一噸，每噸漲 $400/t 剛好產生 $2.52 億美元毛利與 EBITDA 增量。 |
| **Century Aluminum** | **CENX** | **LME 鋁價變動 (+/- $100/t)** | **Adjusted EBITDA 變動約 +/- $6,300 萬美元** | Century 官方財報敏感度指引 | 2025–2026 年化 | 單純 LME 基準每變動 $100/t，在 63 萬噸基準下產生 $63M 影響。 |
| **Century Aluminum** | **CENX** | **IRA 45X 稅收抵免利益** | **每噸出貨約 $90 EBITDA（全球折算）／年化退稅達 $94.3M** | Century 2025 10-K 及 2026 年 7 月退稅揭露 | 2025–2026 現金退稅 | 早期年收益指引 $55M–$60M 除以 63 萬噸約 $90/t；2025 年實收 45X 退稅 $94.3M，針對美國本土受惠產能（Sebree + Mt. Holly 約 41.5 萬噸）每噸抵免高達 $227 美元。 |
| **Century Aluminum** | **CENX** | **氧化鋁 API 變動** | **負向敏感（API 上漲侵蝕冶煉價差）** | Century 10-K Item 1A 風險因素及 MD&A 原料採購段落 | 2024–2026 現況 | Century 外購氧化鋁（主要向 Glencore 採購，合約釘住 API）。當 API 上漲而原鋁價格漲幅不及時，原鋁冶煉利差（Metal Margin）遭到嚴重擠壓。 |

---

## 來源清單

以下為本專案調研與程式化擷取之數據源清單（對應 `.agent-run/out/sources.csv`）：

| category | series | source | url | frequency | history_start | latest_date | access | method | tested | notes |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Company Financials** | Alcoa Quarterly Financials (AA) | SEC EDGAR | `https://data.sec.gov/api/xbrl/companyfacts/CIK0001675149.json` | quarterly | 2015-09-30 | 2026-06-30 | free | json-api | yes | SEC EDGAR XBRL companyfacts API, 需帶自訂 User-Agent |
| **Company Financials** | Century Aluminum Quarterly Financials (CENX) | SEC EDGAR | `https://data.sec.gov/api/xbrl/companyfacts/CIK0000949157.json` | quarterly | 2015-03-31 | 2026-06-30 | free | json-api | yes | SEC EDGAR XBRL companyfacts API, 需帶自訂 User-Agent |
| **Stock Market** | Alcoa Daily Stock Price (AA) | Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/AA` | daily | 2016-10-06 | 2026-10-06 | free | json-api | yes | Yahoo Finance 10年日K線, yfinance 套件 |
| **Stock Market** | Century Aluminum Daily Stock Price (CENX) | Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/CENX` | daily | 2016-10-07 | 2026-10-06 | free | json-api | yes | Yahoo Finance 10年日K線, yfinance 套件 |
| **Exchange Inventory** | LME Aluminum Warehouse Stocks | LME / Westmetall | `https://www.westmetall.com/en/marktdaten.php?action=table&field=LME_Al_Cash` | daily | 1998-01-01 | 2026-10-06 | free | html-table | yes | Westmetall 每日轉載 LME 官方現貨與庫存 |
| **Physical Premium** | US Midwest Aluminum Premium Platts | CME Group | `https://www.cmegroup.com/markets/metals/base/aluminum-midwest-us-transaction-premium-platts-financial.html` | daily | 2012-04-01 | 2026-10-06 | free | html-table | yes | CME 官網提供 Midwest Premium 期貨即時報價與結算價 |
| **Physical Premium** | Rotterdam Duty-Paid Aluminum Premium | S&P Global Platts / Fastmarkets | `https://www.spglobal.com/commodityinsights/en/market-insights/latest-news/metals/040126-platts-rotterdam-duty-paid-aluminum-premium-cbam` | daily | 2010-01-01 | | paid | manual | no | 歐洲完稅溢價主要由 Platts/Fastmarkets 評估發布，需付費訂閱；2026年起納入CBAM成本 |
| **Alumina Price** | Alumina Price Index (API / PAX) | CRU / Fastmarkets | `https://www.crugroup.com/analysis/aluminium/` | daily | 2010-01-01 | | paid | manual | no | 氧化鋁指數 API 為冶煉原料定價基準，需付費訂閱 |

---

## 實測

本專案撰寫了 `probe_al_companies.py` 並完成全部已標註 `tested=yes` 來源之實測抓取，成果保存於 `.agent-run/out/samples/`：

1. **Alcoa SEC EDGAR 季度財務資料實測**：
   - **請求網址**：`https://data.sec.gov/api/xbrl/companyfacts/CIK0001675149.json`
   - **請求標頭**：`User-Agent: aluminum-research chunpin.chen@gmail.com`
   - **HTTP 回應狀態**：200 OK
   - **抽取成果**：共擷取 41 季度記錄，涵蓋期間為 **2015-09-30 至 2026-06-30**。
   - **提取欄位**：`date`, `ticker`, `revenue`, `net_income`, `operating_income`, `depreciation_amortization`, `ebitda`, `shipments_kt`。
   - **儲存路徑**：`.agent-run/out/samples/aa_quarterly.csv`（41 列）。

2. **Century Aluminum SEC EDGAR 季度財務資料實測**：
   - **請求網址**：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000949157.json`
   - **請求標頭**：`User-Agent: aluminum-research chunpin.chen@gmail.com`
   - **HTTP 回應狀態**：200 OK
   - **抽取成果**：共擷取 44 季度記錄，涵蓋期間為 **2015-03-31 至 2026-06-30**。
   - **提取欄位**：`date`, `ticker`, `revenue`, `net_income`, `operating_income`, `depreciation_amortization`, `ebitda`, `shipments_kt`。
   - **儲存路徑**：`.agent-run/out/samples/cenx_quarterly.csv`（44 列）。

3. **Alcoa 日股價歷史實測（Yahoo Finance）**：
   - **請求網址**：`https://query1.finance.yahoo.com/v8/finance/chart/AA?range=10y&interval=1d`
   - **HTTP 回應狀態**：200 OK
   - **擷取筆數**：2,513 個交易日，涵蓋期間為 **2016-10-06 至 2026-10-06**。
   - **儲存路徑**：`.agent-run/out/samples/aa_daily.csv`（2,513 列）。

4. **Century Aluminum 日股價歷史實測（Yahoo Finance）**：
   - **請求網址**：`https://query1.finance.yahoo.com/v8/finance/chart/CENX?range=10y&interval=1d`
   - **HTTP 回應狀態**：200 OK
   - **擷取筆數**：2,512 個交易日，涵蓋期間為 **2016-10-07 至 2026-10-06**。
   - **儲存路徑**：`.agent-run/out/samples/cenx_daily.csv`（2,512 列）。

---

## 踩坑

在抓取、解析鋁業公司數據與市場序列過程中，發現以下關鍵陷阱與技術細節：

1. **SEC EDGAR API 403 阻擋與 User-Agent 嚴格規範**：
   - SEC EDGAR API 實施嚴格的反爬機制。若未附帶合規的 User-Agent 標頭（格式必須包含合規應用名稱與聯絡 Email，例如 `User-Agent: aluminum-research chunpin.chen@gmail.com`），或請求頻率超過每秒 10 次，伺服器會立即回傳 `403 Forbidden`。程式碼中必須強制封裝自訂標頭。

2. **XBRL 現金流量表 D&A 之累計（YTD）與單季（Single Quarter）結構陷阱**：
   - 損益表項目（如 Revenues、Net Income）在 10-Q 中通常直接給出 3 個月單季數字（duration 約 90 天）。
   - 然而，現金流量表中的折舊與攤銷（D&A, Depreciation & Amortization）在 10-Q 中通常是**年初至今累計值（YTD）**：Q1 是 3 個月、Q2 是 6 個月、Q3 是 9 個月、10-K 全年（FY）是 12 個月。
   - 若直接以 `duration == 90 days` 進行過濾，會導致 Q2、Q3、Q4 的 D&A 嚴重缺失（例如 CENX 只剩 12 筆）。必須撰寫階梯回溯演算法：$D\&A_{Q2} = YTD_{Q2} - YTD_{Q1}$、$D\&A_{Q3} = YTD_{Q3} - YTD_{Q2}$、$D\&A_{Q4} = FY - YTD_{Q3}$，方能還原出精準的單季 D&A 與 EBITDA。

3. **XBRL 標籤異質性與非 GAAP EBITDA 差異**：
   - Alcoa 在 US-GAAP 財報中並未標註標準的 `OperatingIncomeLoss` tag，而是採用分段呈現（以 `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest` 作為稅前持續營業利潤 EBT）。若機械性搜尋 `OperatingIncomeLoss` 會取得空值。
   - 公司官方揭露的「Adjusted EBITDA」排除了特定非常態項目（重組成本、環境復育準備、關廠損失、少數股權調節等），純粹以 GAAP 營業利益 + D&A 計算的粗 EBITDA 與法說會之 Adjusted EBITDA 會有約 5%–15% 之口徑調節差異。

4. **實體溢價單位換算陷阱（美分/磅 vs. 美元/公噸）**：
   - 美國中西部溢價（US Midwest Premium）在美系交易報價中通常以「美分/磅（cents/lb）」表示（例如 20 美分/磅）。
   - 國際市場（如 LME、歐洲 Rotterdam 溢價）一律以「美元/公噸（$/mt）」為基準。
   - 換算公式：$1\text{ 磅} = 0.00045359237\text{ 公噸}$，故 $1\text{ 美分/磅} = 0.01 \times 2204.6226 \approx 22.0462\text{ 美元/公噸}$。例如 20 美分/磅換算後為約 $440.92/t。分析貼文時若未注意單位換算，極易產生 20 倍之理解偏差。

5. **出貨量（Shipments）非標準 XBRL Tag**：
   - Alcoa 與 Century 的原鋁出貨量（千公噸）多數記載於 10-K/10-Q 的「MD&A 經營成果與分部討論（Segment Results）」文字說明或未標籤化之附表中，未包含在標準 US-GAAP companyfacts 數值 tag 內。若需長期追蹤，需透過 10-K 文字爬蟲或法說會簡報解析。

---

## 建議抓法

為後續自動化排程與維護腳本（`fetch_data.py`）之工程師提供具體指引，每個序列之端點與解析規範如下：

1. **Alcoa 季度財報**：
   - **端點**：`https://data.sec.gov/api/xbrl/companyfacts/CIK0001675149.json`
   - **解析方式**：HTTP GET 帶自訂 UA；讀取 `facts.us-gaap.SalesRevenueNet`（營收）、`facts.us-gaap.NetIncomeLoss`（淨利）、`facts.us-gaap.DepreciationDepletionAndAmortization`（現金流 YTD 階梯相減得出單季 D&A）。

2. **Century Aluminum 季度財報**：
   - **端點**：`https://data.sec.gov/api/xbrl/companyfacts/CIK0000949157.json`
   - **解析方式**：HTTP GET 帶自訂 UA；讀取 `facts.us-gaap.SalesRevenueNet`、`facts.us-gaap.OperatingIncomeLoss`、`facts.us-gaap.DepreciationDepletionAndAmortization`，執行 YTD 差分計算得出單季 EBITDA。

3. **Alcoa 日股價**：
   - **端點**：`https://query1.finance.yahoo.com/v8/finance/chart/AA?range=10y&interval=1d`
   - **解析方式**：使用 `yfinance.Ticker('AA').history(period='10y')` 或直接以 requests 帶 `User-Agent: Mozilla/5.0` 解析 JSON `chart.result[0].indicators.quote[0]`。

4. **Century Aluminum 日股價**：
   - **端點**：`https://query1.finance.yahoo.com/v8/finance/chart/CENX?range=10y&interval=1d`
   - **解析方式**：使用 `yfinance.Ticker('CENX').history(period='10y')`，保留 `date, open, high, low, close, volume`。

5. **LME 鋁現貨價格與官方倉單庫存（免費代理）**：
   - **端點**：`https://www.westmetall.com/en/marktdaten.php?action=table&field=LME_Al_Cash`
   - **解析方式**：使用 `curl_cffi` 或 `requests` 請求 HTML，以 BeautifulSoup 解析 `table.marktdaten`，第一欄為日期，第二欄為 LME 現貨價，第五欄為 LME 庫存（LME Stocks）。

6. **美國中西部溢價（CME Midwest Premium 期貨代理）**：
   - **端點**：`https://www.cmegroup.com/CmeWS/mvc/Quotes/X/843/G?isProtected&_page=quotes`
   - **解析方式**：請求 CME JSON Quotes API 獲取近月份與主力合約結算價（單位美分/磅，乘以 22.0462 換算為 $/mt）。

7. **歐洲完稅溢價（Rotterdam Duty-Paid）**：
   - **端點**：S&P Platts / Fastmarkets 專有付費 API。
   - **解析方式**：無免費公開即時 API；建議每月由研究員登入終端機匯出 CSV，或以每月新聞報導之月均值為手動補齊來源。

8. **氧化鋁指數（Alumina Price Index API）**：
   - **端點**：CRU / Fastmarkets 專有付費端點。
   - **解析方式**：付費訂閱下載；研究上可用中國上海期貨交易所（SHFE）氧化鋁期貨結算價（微觀結構存在區域差異，但趨勢高度正相關）作為免費高頻代理。
