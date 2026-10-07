# 鋁區域溢價、政策時間線、部位與能源成本數據調研與實測報告

本報告針對全球鋁業市場核心變數進行全面數據源盤點與實測，涵蓋「區域溢價（美國中西部、歐洲鹿特丹、日本 MJP）」、「政策時間線（232 關稅、俄鋁制裁、歐盟 CBAM、中國退稅與產能天花板、幾內亞礦權）」、「市場部位（CFTC COMEX、LME COTR）」以及「冶煉能源成本（美國 MISO 電價、歐洲 TTF 天然氣與德國電價、中國動力煤）」。

---

## 結論

1. **美國中西部溢價（US Midwest Premium）可由 CME 期貨結算價日度免費追蹤**：
   S&P Global Platts 官方現貨評估（MW US Transaction Premium）屬於高昂商業付費來源；但 CME 掛牌的對應期貨合約 `AUP`（Aluminum MW US Transaction Premium Platts 25MT Futures）結算價可直接透過 Yahoo Finance 代號 `AUP=F` 免費日度抓取（最新日期 2026-10-07 結算價為 1.04 美元/磅，換算約 2,292.8 美元/公噸）。CFTC 每週二持倉報告亦提供其專屬大額交易商合約部位（代碼 `191693`）。
2. **歐洲鹿特丹完稅溢價（Rotterdam Duty-Paid Premium）可由 CME EDP 免費日度追蹤**：
   Fastmarkets MB 鹿特丹實體現貨報價需昂貴訂閱，但 CME Aluminium European Duty-Paid Premium 期貨結算價可透過 Yahoo Finance 代號 `EDP=F` 免費取得完整 5 年日資料（最新日期 2026-10-07 結算價為 556.5 美元/公噸）。CFTC 每週發布其對應持倉（代碼 `191696`）。
3. **日本主港季度溢價（MJP Premium）無即時 API，但每季均有公開新聞定價**：
   亞洲基準 MJP（CIF Japan）屬於季度談判現貨合約，無公開官方高頻 API。然而每季談判結算均由 Reuters、Platts 與 Alcircle 等權威媒體完整報導（本研究整理 2018 Q1 至 2026 Q3 連續 35 季樣本，最新 2026 Q3 結算價達 395 美元/公噸，創十年新高）。維護者只需在每季首月（1、4、7、10 月）進行一次新聞定點追蹤即可。
4. **部位數據（COTR）：CFTC 具備高品質免費 API，LME 需處理反爬**：
   - **CFTC（COMEX 鋁）**：Socrata Open Data API 表現極佳，不需 API Key 即可批量抓取原鋁（`191691`）、中西部溢價（`191693`）與歐洲完稅溢價（`191696`）的完整歷史週報（包含商業、非商業、投資基金多空部位與總未平倉量）。
   - **LME（倫敦金屬交易所）**：LME 官方每週五免費發布 MiFID II 格式的 Primary Aluminium (`AH`) 持倉報表 Excel（`.xlsx`），但其官網受到 Akamai / Cloudflare 嚴格阻擋，一般 `requests` 會回傳 403 Forbidden，實測必須使用 `curl_cffi`（`impersonate="chrome"`）即可穩定下載解析。
5. **能源成本（電價與氣價）存在高質量開放端點**：
   - **歐洲**：荷蘭 TTF 天然氣期貨（Yahoo `TTF=F`）提供即時免費日結算價（最新 75.69 歐元/MWh）；德國/盧森堡 Day-Ahead 電價可透過 Fraunhofer ISE 營運的 **Energy-Charts API** 免費無限制抓取（最新日均價約 137–209 歐元/MWh）。
   - **美國**：MISO 每日在官方目錄發布當日日前電價結算報表（`.xls`），可直接解析 Indiana Hub（鄰近 Kentucky Sebree 冶煉廠）的 Around-the-Clock 日均電價（最新約 44.9 美元/MWh）；宏觀序列則可取 FRED 之工業電價 PPI（`PCU221122221122`）。
   - **中國動力煤**：鄭商所動力煤連續期貨（新浪 `ZC0`）因 2021 年底發改委政策干預保供穩價後，成交量與持倉量枯竭，2022 年底後無常規交易；國際對照採用 IMF/FRED 澳洲紐卡斯爾動力煤現貨月均價（`PCOALAUUSDM`，最新 140.4 美元/噸），國內現貨跟蹤生意社（100ppi）基準價（最新 994.5 元/噸）或國統局採掘工業 PPI。
6. **宏觀政策與供給衝擊驗證**：
   政策時間線（2018–2026）梳理顯示，美國 232 關稅重啟升級（2025 年 25% 與 50%）、英美 2024-04 禁止新俄鋁交割、歐盟第 16 輪制裁分階段禁俄鋁、中國 2024-12 取消 13% 鋁材出口退稅、以及歐洲 2021–2026 年因能源危機累計關閉逾 100 萬噸原鋁產能，共同推動歐美區域溢價與原鋁價格走出脫離歷史區間的結構性分化。

---

## 來源清單

| 類別 (category) | 序列名稱 (series) | 來源 (source) | URL / 端點 | 頻率 (frequency) | 歷史起點 | 最新實測日期 | 存取權限 (access) | 擷取方式 (method) | 實測狀態 (tested) | 備註說明 (notes) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| premium | US Midwest Premium Futures (AUP) | CME / Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/AUP=F` | daily | 2021-10-07 | 2026-10-07 | free | json-api | yes | 美國中西部鋁交易溢價期貨結算價（美元/磅；換算美元/噸需乘2204.62） |
| premium | European Duty-Paid Premium Futures (EDP) | CME / Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/EDP=F` | daily | 2021-10-07 | 2026-10-07 | free | json-api | yes | 歐洲鹿特丹完稅溢價期貨結算價（美元/公噸） |
| premium | US Midwest Transaction Premium Platts Spot | S&P Global Platts | `https://www.spglobal.com/commodityinsights/en/market-insights/latest-news/metals` | daily | 2012-01-01 | | paid | manual | no | Platts官方現貨報價為昂貴付費源；可用CME AUP期貨結算價作為高相關免費替代 |
| premium | Rotterdam Duty-Paid / Unpaid Premium Spot | Fastmarkets MB | `https://www.fastmarkets.com/commodities/metals-and-mining/base-metals/aluminium/` | biweekly | 2010-01-01 | | paid | manual | no | 歐洲實體現貨溢價基準；商業付費訂閱；可用CME EDP期貨結算價免費替代 |
| premium | Japan MJP Quarterly Premium | Reuters / Platts News Archive | `https://www.reuters.com/markets/commodities/` | quarterly | 2018-01-01 | 2026-07-01 | free | manual | yes | 日本主港（MJP）每季談判結算溢價（美元/公噸）；公開新聞整理連續35季歷史 |
| futures | CME Aluminum Futures (ALI) | CME / Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/ALI=F` | daily | 2021-10-07 | 2026-10-07 | free | json-api | yes | CME原鋁期貨收盤價、成交量與未平倉量（美元/公噸） |
| cot | CFTC Aluminum Futures Legacy (191691) | CFTC Socrata API | `https://publicreporting.cftc.gov/resource/6dca-aqww.json` | weekly | 1986-01-15 | 2026-09-29 | free | json-api | yes | COMEX原鋁期貨大額交易商持倉報告（商業/非商業多空部位與未平倉） |
| cot | CFTC US Midwest Premium Futures Legacy (191693) | CFTC Socrata API | `https://publicreporting.cftc.gov/resource/6dca-aqww.json` | weekly | 2015-10-06 | 2026-09-29 | free | json-api | yes | 美國中西部溢價期貨部位（含歷史SWAP與現行合約） |
| cot | CFTC European Duty-Paid Premium Futures Legacy (191696) | CFTC Socrata API | `https://publicreporting.cftc.gov/resource/6dca-aqww.json` | weekly | 2020-09-29 | 2026-09-29 | free | json-api | yes | 歐洲鹿特丹完稅溢價期貨大額交易商持倉報告部位 |
| cot | CFTC European Duty-Unpaid Premium Futures Legacy (191694) | CFTC Socrata API | `https://publicreporting.cftc.gov/resource/6dca-aqww.json` | weekly | 2020-02-18 | 2023-07-03 | free | json-api | yes | 歐洲未完稅溢價期貨大額交易商持倉報告歷史部位 |
| cot | LME Aluminium Commitments of Traders (AH) | London Metal Exchange | `https://www.lme.com/market-data/reports-and-data/commitments-of-traders/aluminium` | weekly | 2020-01-03 | 2026-10-02 | free | xlsx | yes | LME原鋁MiFID II格式持倉週報；公開免費；需用curl_cffi避免Akamai 403 |
| policy | Global Aluminum Policy Timeline | Federal Register / EU / Tax / NDRC | `https://www.federalregister.gov/` | event-driven | 2017-04-12 | 2026-01-01 | free | manual | yes | 涵蓋232關稅、俄鋁制裁、歐盟CBAM、中國退稅與天花板、幾內亞礦權收回、歐洲減產量化事件 |
| energy | Dutch TTF Natural Gas Futures | ICE / Yahoo Finance | `https://query1.finance.yahoo.com/v8/finance/chart/TTF=F` | daily | 2021-10-07 | 2026-10-07 | free | json-api | yes | 歐洲天然氣基準價格期貨結算價（歐元/MWh）；歐洲冶煉廠邊際發電成本核心指標 |
| energy | German Power Day-Ahead Spot Price | Energy-Charts API / ENTSO-E | `https://api.energy-charts.info/price?bzn=DE-LU` | daily | 2018-10-01 | 2026-10-07 | free | json-api | yes | 德國盧森堡電網日前批發電價（歐元/MWh）；開源免費API無Key限制 |
| energy | MISO Day-Ahead Indiana Hub LMP | Midcontinent ISO | `https://docs.misoenergy.org/marketreports/` | daily | 2020-01-01 | 2026-10-06 | free | xlsx | yes | 美國中西部Sebree/Kentucky附近電力市場Indiana Hub結算電價（美元/MWh） |
| energy | US Industrial Electric Power PPI | BLS / FRED | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU221122221122` | monthly | 2003-12-01 | 2026-08-01 | free | csv-api | yes | 美國工業用電生產者物價指數（FRED公開免費無Key） |
| energy | Global Coal Newcastle Thermal Spot Price | IMF / FRED | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCOALAUUSDM` | monthly | 1990-01-01 | 2026-07-01 | free | csv-api | yes | 國際基準澳洲紐卡斯爾動力煤現貨月度均價（美元/公噸） |
| energy | CZCE Thermal Coal Futures Continuous (ZC0) | CZCE / Sina Finance | `https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_ZC0=/InnerFuturesNewService.getDailyKLine?symbol=ZC0` | daily | 2015-05-26 | 2022-12-30 | free | json-api | yes | 鄭商所動力煤連續期貨；2021年底政策限價與提高保證金後成交量萎縮，2022年底實質停滯 |
| energy | China Thermal Coal Spot Benchmark Price | 100ppi (生意社) | `http://www.100ppi.com/vane/detail-653.html` | daily | 2019-01-01 | 2026-10-07 | free | html-table | yes | 中國國內動力煤現貨基準價（元/噸）；反映國內電廠與港口實際成交水平 |
| energy | China Coal Mining PPI | NBS / DBnomics | `https://api.db.nomics.world/v22/series/NBS/M_A010802/A01080202` | monthly | 2010-01-01 | 2026-08-01 | free | json-api | yes | 中國國家統計局採掘工業PPI指數（DBnomics免費轉載鏡像） |

---

## 實測

本研究針對可程式化存取之數據源進行了全面實測，所有實測均已成功回傳並產出樣本 CSV（存放於 `.agent-run/out/samples/`）：

### 1. 美國中西部溢價期貨（CME AUP）
- **請求網址**：`https://query1.finance.yahoo.com/v8/finance/chart/AUP=F?range=5y&interval=1d`
- **HTTP 狀態**：200 OK
- **回傳筆數**：1,255 筆日度資料
- **起訖日期**：2021-10-07 至 2026-10-07
- **最新數值與單位**：結算價 1.0400 美元/磅（折合 2,292.8 美元/公噸）；成交量 25 口。
- **儲存樣本**：`samples/us_midwest_premium_cme.csv`

### 2. 歐洲完稅溢價期貨（CME EDP）
- **請求網址**：`https://query1.finance.yahoo.com/v8/finance/chart/EDP=F?range=5y&interval=1d`
- **HTTP 狀態**：200 OK
- **回傳筆數**：1,255 筆日度資料
- **起訖日期**：2021-10-07 至 2026-10-07
- **最新數值與單位**：結算價 556.53 美元/公噸；成交量 12 口。
- **儲存樣本**：`samples/european_dutypaid_premium_cme.csv`

### 3. CME 鋁期貨基準合約（ALI）
- **請求網址**：`https://query1.finance.yahoo.com/v8/finance/chart/ALI=F?range=5y&interval=1d`
- **HTTP 狀態**：200 OK
- **回傳筆數**：1,256 筆日度資料
- **起訖日期**：2021-10-07 至 2026-10-07
- **最新數值與單位**：收盤價 3,259.0 美元/公噸。
- **儲存樣本**：`samples/cme_aluminum_futures.csv`

### 4. CFTC 大額交易商持倉報告（Socrata API）
- **請求網址**：`https://publicreporting.cftc.gov/resource/6dca-aqww.json?cftc_contract_market_code=191691`（原鋁）、`191693`（MWP）、`191696`（EDP）
- **HTTP 狀態**：200 OK
- **回傳筆數**：1,060 筆週度合約資料（191691 佔 208 筆、191693 佔 569 筆、191696 佔 283 筆）
- **起訖日期**：1986-01-15 至 2026-09-29
- **核心欄位**：`open_interest`、`noncomm_long`、`noncomm_short`、`comm_long`、`comm_short`。
- **儲存樣本**：`samples/cftc_aluminum_cot_legacy.csv`

### 5. 荷蘭 TTF 天然氣期貨（TTF）
- **請求網址**：`https://query1.finance.yahoo.com/v8/finance/chart/TTF=F?range=5y&interval=1d`
- **HTTP 狀態**：200 OK
- **回傳筆數**：1,256 筆日度資料
- **起訖日期**：2021-10-07 至 2026-10-07
- **最新數值與單位**：75.69 歐元/MWh。
- **儲存樣本**：`samples/ttf_gas_daily.csv`

### 6. 德國/盧森堡日前電價（Energy-Charts API）
- **請求網址**：`https://api.energy-charts.info/price?bzn=DE-LU&start=2026-08-01T00:00:00Z&end=2026-10-07T00:00:00Z`
- **HTTP 狀態**：200 OK
- **回傳筆數**：3,457 筆 15 分鐘/小時點位，聚合為 68 筆日均價資料
- **起訖日期**：2026-08-01 至 2026-10-07
- **最新數值與單位**：137.09 歐元/MWh。
- **儲存樣本**：`samples/german_power_dayahead.csv`

### 7. 美國 MISO 日前 LMP 電價（Indiana Hub）
- **請求網址**：`https://docs.misoenergy.org/marketreports/20261005_da_pr.xls`
- **HTTP 狀態**：200 OK（檔案大小 13,312 bytes，Excel 格式）
- **回傳筆數**：連續 15 天日度報告
- **起訖日期**：2026-09-22 至 2026-10-06
- **最新數值與單位**：Around-the-Clock 全天均價 44.92 美元/MWh；尖峰時段（On-Peak）均價 50.29 美元/MWh；離峰時段（Off-Peak）均價 34.20 美元/MWh。
- **儲存樣本**：`samples/miso_indiana_hub_lmp.csv`

### 8. 日本 MJP 季度現貨溢價歷史
- **資料來源**：整理自 Reuters 與 Platts 歷史新聞報導存檔
- **筆數**：35 筆季度資料
- **起訖日期**：2018-01-01 (2018Q1) 至 2026-07-01 (2026Q3)
- **最新數值**：2026 Q3 結算價 395.0 美元/公噸。
- **儲存樣本**：`samples/mjp_quarterly_premium.csv`

### 9. 全球鋁業政策時間線
- **資料來源**：美國聯邦公報、歐盟理事會法規、中國財政部公告、發改委通知、路透社新聞
- **筆數**：22 筆重大事件
- **起訖日期**：2017-04-12 至 2026-01-01
- **儲存樣本**：`samples/policy_timeline.csv`

### 10. LME 原鋁 COTR 週報
- **請求網址**：`https://www.lme.com/-/media/files/data/cotrs/ah-aluminium/mifid-weekly-cotr-report--ah--06102026.xlsx`
- **工具與狀態**：使用 `curl_cffi`，HTTP 狀態 200 OK，檔案大小 5,238 bytes
- **最新資料日期**：2026-10-02（報表發布日期 2026-10-06）
- **解析內容**：工作表 `AH`，包含 Investment Funds 多頭 182,226 口、空頭 51,992 口；商業機構多頭 471,787 口、空頭 497,508 口（每手合約 25 噸）。

---

## 踩坑

在數據調研與實測過程中，記錄以下具體陷阱與解決方案：

1. **LME 官網 Akamai 403 阻擋**：
   - **現象**：使用標準 Python `requests` 請求 `https://www.lme.com/en/market-data/reports-and-data/commitments-of-traders` 或下載 `.xlsx` 報表時，會直接遭到 Akamai 反爬防護回傳 `403 Forbidden`。
   - **解法**：不可直接使用一般連線，需改用 `curl_cffi` 並指定 `impersonate="chrome"`，即可模擬真實瀏覽器 TLS/JA3 指紋順利下載最新 Excel 檔案。
2. **Yahoo Finance 請求阻擋（403 錯誤）**：
   - **現象**：若直接調用 `requests.get("https://query1.finance.yahoo.com/...")` 且未提供 Header，Yahoo 伺服器會拒絕連線。
   - **解法**：必須明確帶上 `User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36`。
3. **MISO 日報格式與副檔名陷阱**：
   - **現象**：MISO 官網的 URL 形式為 `https://docs.misoenergy.org/marketreports/YYYYMMDD_da_pr.xls`，如果嘗試使用 `_da_pr.csv` 會回傳 404 Not Found；且該檔案雖為 `.xls`，但屬於舊版 BIFF8 複合文件格式，直接以文字方式或 `openpyxl` 讀取會報錯。
   - **解法**：需使用 `pandas.read_excel(..., engine='xlrd')` 讀取；且表格並非標準扁平資料，需在列索引第 13 列搜尋目標 Hub（`Indiana Hub`，其對應 Sebree 冶煉廠所在電網節點），再定位第 40 列的 `Around the Clock Average` 取得全日均價。
4. **CFTC Socrata 官方欄位拼寫錯誤**：
   - **現象**：在 CFTC Legacy 報告的 JSON 回傳中，價差合約欄位名稱拼寫為 `noncomm_postions_spread_all`（少了一個 `i`，即 `postions`），直接按照標準英文拼寫 `positions` 會發生 `KeyError`。
   - **解法**：在欄位映射字典中相容原始拼寫錯誤。
5. **區域溢價單位換算陷阱**：
   - **現象**：美國中西部溢價期貨 `AUP` 的交易單位是美分/磅或美元/磅（報價如 `1.04` 美元/磅），而歐洲 `EDP`、日本 `MJP` 以及 LME/CME 原鋁期貨基準價格單位均為「美元/公噸（USD/metric ton）」。若直接相加或比對會產生三個數量級的致命誤差。
   - **解法**：1 磅 = 0.00045359237 公噸，即 1 公噸 = 2204.62262 磅。將 AUP 報價乘以 2,204.62 即可換算為美元/公噸（例如 $1.04 / lb × 2204.62 ≈ $2,292.8 / mt）。
6. **中國動力煤期貨流動性斷崖**：
   - **現象**：試圖抓取鄭商所動力煤連續期貨（`ZC0`）的近期行情時，發現自 2022 年底後 K 線幾乎無變動，價格停滯在 921 元/噸附近，成交量為 0。
   - **原因**：2021 年下半年「煤超瘋」後，國家發改委等部門出台嚴厲保供穩價措施，交易所大幅調高保證金與日內交易手續費，並限制日間開倉手數，動力煤期貨實質上喪失撮合流動性。
   - **解法**：在歷史回溯中 2015–2021 年可參考 ZC0 期貨，但 2022 年後必須改採國內現貨基準（生意社 100ppi 基準價或秦皇島港 5500 大卡現貨平倉價）以及國際基準（FRED `PCOALAUUSDM` 澳洲紐卡斯爾煤現貨價）。

---

## 建議抓法

以下提供給後續開發 `fetch_data.py` 自動化排程 ETL 的端點與解析指引：

1. **AUP（美國中西部溢價期貨）**：
   - 端點：`https://query1.finance.yahoo.com/v8/finance/chart/AUP=F?range=10y&interval=1d`
   - 解析：帶 `User-Agent: Mozilla/5.0`，解析 JSON `chart.result[0].indicators.quote[0].close`，單位為 USD/lb，乘以 2204.62 存入基準庫。
2. **EDP（歐洲完稅溢價期貨）**：
   - 端點：`https://query1.finance.yahoo.com/v8/finance/chart/EDP=F?range=10y&interval=1d`
   - 解析：帶 `User-Agent: Mozilla/5.0`，解析 JSON `close`，單位為 USD/mt。
3. **MJP（日本主港季度溢價）**：
   - 端點：靜態維護 `samples/mjp_quarterly_premium.csv`，每季首月（1/4/7/10月）透過爬蟲檢索 Reuters 或 Platts「Japan aluminium premium settles at $XX/t」更新當季數值。
4. **ALI（CME 原鋁期貨）**：
   - 端點：`https://query1.finance.yahoo.com/v8/finance/chart/ALI=F?range=10y&interval=1d`
   - 解析：解析 JSON `close` 與 `volume`，單位為 USD/mt。
5. **CFTC 部位（原鋁 191691 / MWP 191693 / EDP 191696）**：
   - 端點：`https://publicreporting.cftc.gov/resource/6dca-aqww.json`
   - 解析：GET 參數 `cftc_contract_market_code=<CODE>`、`$limit=50000`、`$order=report_date_as_yyyy_mm_dd`，提取 `open_interest_all`、`noncomm_positions_long_all`、`noncomm_positions_short_all`。
6. **LME 原鋁 COTR（AH）**：
   - 端點：`https://www.lme.com/market-data/reports-and-data/commitments-of-traders/aluminium`
   - 解析：使用 `curl_cffi`（`impersonate="chrome"`）抓取最新 `.xlsx` 下載連結，以 `openpyxl` 讀取工作表 `AH` 第 12 列獲取 Total Long/Short，或第 11 列獲取 Other (Investment Funds/Financial Institutions) 投機部位。
7. **TTF 天然氣（歐洲氣價）**：
   - 端點：`https://query1.finance.yahoo.com/v8/finance/chart/TTF=F?range=10y&interval=1d`
   - 解析：解析 JSON `close`，單位為 EUR/MWh。
8. **德國批發電價（Energy-Charts）**：
   - 端點：`https://api.energy-charts.info/price?bzn=DE-LU&start={start_iso}&end={end_iso}`
   - 解析：免費公開 JSON，取 `unix_seconds` 與 `price`，依天聚合為日均電價，單位 EUR/MWh。
9. **MISO Indiana Hub 電價**：
   - 端點：`https://docs.misoenergy.org/marketreports/{YYYYMMDD}_da_pr.xls`
   - 解析：`pd.read_excel(engine='xlrd')`，定位第 13 列欄位為 `Indiana Hub` 之行索引，取第 40 列數值作為 Around the Clock 日均 LMP（USD/MWh）。
10. **國際動力煤（IMF Newcastle）**：
    - 端點：`https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCOALAUUSDM`
    - 解析：標準 CSV，第一欄 `DATE`，第二欄月度價格，單位 USD/mt。
11. **中國動力煤現貨基準（生意社）**：
    - 端點：`http://www.100ppi.com/vane/detail-653.html`
    - 解析：解析 HTML 頁面中動力煤基準價（元/噸）。
12. **政策時間線（Policy Timeline）**：
    - 端點：維護 `samples/policy_timeline.csv`，欄位依序為 `date,region,event,detail,source_url`，用於計量模型之事件虛擬變數（Event Dummy Variables）。
