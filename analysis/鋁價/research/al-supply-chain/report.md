# 鋁產業鏈供給（鋁土礦→氧化鋁→原鋁）與貿易流數據調研與實測報告

## 結論

1. **免費日度高頻更新序列（價格端）**：
   - **SHFE 氧化鋁期貨 (AO0) 與滬鋁期貨 (AL0)** 可透過新浪財經期貨日 K 線公開 API（`InnerFuturesNewService.getDailyKLine`）實現每日收盤自動更新，提供完整 OHLC、成交量、持倉量與結算價。氧化鋁期貨自 2023-06-19 上市首日至 2026-09-30 累積 798 根交易日數據；滬鋁連續合約自 2005-01-04 至今超過 5,290 根日資料，是追蹤中游氧化鋁與下游電解鋁現期定價動態的最佳高頻指標。
2. **免費月度更新序列（產量端）**：
   - **國際鋁業協會 (IAI)** 是全球產量最權威、覆蓋最長的主來源。其後端 ALVIS REST API 可直接透過公開 Token 與 `x-auth-token` 標頭免費取得 1973 年至今（截至 2026 年 8 月）全球與 10 大產區（中國、海灣合作委員會 GCC、北美、南美、西歐、俄羅斯與東歐、大洋洲、非洲等）的月度原鋁產量及冶金級氧化鋁月度產量。
   - **中國國家統計局 (NBS)** 月度產量可經由 **DBnomics API**（資料集代碼 `M_A02091H` 電解鋁、`M_A02091C` 氧化鋁、`M_A02091K` 鋁材）免費取得滾動近 13 個月之當期與累計產量。
3. **免費年度/月度貿易流更新序列**：
   - **UN Comtrade Public API** 可免費取得中國鋁土礦（HS 260600）、氧化鋁（HS 281820）、未鍛軋鋁（HS 7601）分國進口量與進口值，並可用於推算幾內亞鋁土礦進口 CIF 均價。針對美國原鋁進口（HS 7601），Comtrade（Reporter 842）亦可直接查詢加拿大、阿聯等來源國數據。
4. **只能付費的關鍵序列與免費替代方案**：
   - **中國電解鋁運行產能、有效產能與開工率**：權威數據源自上海有色網 (SMM)、百川盈孚 (Baiinfo)、阿拉丁 (Aladdiny) 及安泰科 (Antaike)，均屬付費數據庫。**免費替代途徑**：追蹤中國有色金屬工業協會 (CNIA) 每月發布的新聞統計公報、工信部/發改委產能置換公示，以及國內上市鋁企（中國鋁業 601600.SS、雲鋁股份 000807.SZ、天山鋁業 002532.SZ）之定期財務報告。
   - **澳洲 FOB 氧化鋁現貨價格指數 (PAX Index)**：Fastmarkets 與 S&P Global Platts 為行業付費基準。**免費替代途徑**：以上期所氧化鋁期貨主力合約結算價搭配人民幣匯率與海運費推算隱含 FOB，或參考中國海關進出口氧化鋁離岸單價。
   - **幾內亞到中國 CIF 鋁土礦現貨報價**：SMM 與 Fastmarkets 為付費現貨價。**免費替代途徑**：海關總署/UN Comtrade 月度「進口總金額 (CIF 美元) ÷ 進口淨重 (公噸)」推算之月度 CIF 均價。
5. **中國原鋁產能上限驗證（付鵬論點與數據事實）**：
   - 根據 IAI 最新實測數據，截至 2026 年 8 月（最新資料月份），**中國原鋁最近 12 個月（2025-09 至 2026-08）累計產量達 44,940.0 千噸（即 4,494.0 萬噸）**。
   - 距離中國供給側改革所設定的 **4,500 萬噸產能天花板上限僅相差 60 千噸（即 6.0 萬噸，僅剩 0.13% 空間）**。
   - 國家統計局 (NBS) 累計產量亦顯示 2025 年全年電解鋁產量達 4,501.6 萬噸，證實中國電解鋁供給彈性已被政策產能紅線徹底鎖死。
6. **幾內亞鋁土礦進口占比與趨勢**：
   - 2015 年中國自幾內亞進口鋁土礦僅約 33 萬噸（占比不到 0.6%），彼時印尼禁礦後主要依賴澳洲（占比 >35%）。
   - 2017 年幾內亞占比跳升至 40.3%（2,759 萬噸），2021 年突破 51.0%（5,474 萬噸），**2024 年進口量已高達 11,009 萬噸（1.1 億噸），占中國總進口量超過 70%**。
   - 中國對幾內亞單一國家的鋁土礦依賴已呈現寡占脆弱性，幾內亞政策（如政變後的礦約重審、最低離岸參考價要求、精煉廠本土化建設）直接構成整個產業鏈最上游的定價與供給衝擊核心。

---

## 來源清單

| 類別 (category) | 序列名稱 (series) | 數據源 (source) | 查詢網址 (url) | 頻率 (frequency) | 歷史起點 (history_start) | 最新日期 (latest_date) | 權限 (access) | 抓取方式 (method) | 實測 (tested) | 備註 (notes) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| production | iai_primary_aluminium_global | IAI | https://international-aluminium.org/statistics/primary-aluminium-production/ | monthly | 1973-01-01 | 2026-08-31 | free | json-api | yes | 全球原鋁月度產量（千噸），經 ALVIS REST API 抓取 |
| production | iai_primary_aluminium_china | IAI | https://international-aluminium.org/statistics/primary-aluminium-production/ | monthly | 1973-01-01 | 2026-08-31 | free | json-api | yes | 中國原鋁月度產量估算（千噸），經 ALVIS REST API 抓取 |
| production | iai_primary_aluminium_north_america | IAI | https://international-aluminium.org/statistics/primary-aluminium-production/ | monthly | 1973-01-01 | 2026-08-31 | free | json-api | yes | 北美原鋁月度產量（千噸），經 ALVIS REST API 抓取 |
| production | iai_primary_aluminium_gcc | IAI | https://international-aluminium.org/statistics/primary-aluminium-production/ | monthly | 1973-01-01 | 2026-08-31 | free | json-api | yes | 海灣合作委員會(GCC)原鋁月度產量（千噸），經 ALVIS REST API 抓取 |
| production | iai_metallurgical_alumina_global | IAI | https://international-aluminium.org/statistics/alumina-production/ | monthly | 1974-01-01 | 2026-08-31 | free | json-api | yes | 全球冶金級氧化鋁月度產量（千噸），經 ALVIS REST API 抓取 |
| production | iai_metallurgical_alumina_china | IAI | https://international-aluminium.org/statistics/alumina-production/ | monthly | 1974-01-01 | 2026-08-31 | free | json-api | yes | 中國冶金級氧化鋁月度產量估算（千噸），經 ALVIS REST API 抓取 |
| production | china_electrolytic_aluminum_output_monthly | NBS (via DBnomics) | https://api.db.nomics.world/v22/series/NBS/M_A02091H | monthly | 2025-02-01 | 2026-02-01 | free | json-api | yes | 中國國家統計局電解鋁月度當期/累計產量（萬噸），API固定提供滾動13個月 |
| production | china_alumina_output_monthly | NBS (via DBnomics) | https://api.db.nomics.world/v22/series/NBS/M_A02091C | monthly | 2025-02-01 | 2026-02-01 | free | json-api | yes | 中國國家統計局氧化鋁月度當期/累計產量（萬噸），API固定提供滾動13個月 |
| production | china_aluminum_products_output_monthly | NBS (via DBnomics) | https://api.db.nomics.world/v22/series/NBS/M_A02091K | monthly | 2025-02-01 | 2026-02-01 | free | json-api | yes | 中國國家統計局鋁材月度當期/累計產量（萬噸），API固定提供滾動13個月 |
| production | usgs_world_aluminum_reserves_production | USGS | https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-aluminum.pdf | annual | 1995-01-01 | 2024-01-31 | free | pdf | yes | USGS MCS 全球各國原鋁產量與儲量年度統計報告（千噸） |
| production | usgs_world_bauxite_reserves_production | USGS | https://www.usgs.gov/centers/national-minerals-information-center/bauxite-and-alumina-statistics-and-information | annual | 1995-01-01 |  | free | xlsx | no | USGS 鋁土礦分國儲量與產量年度資料檔（年報發布） |
| production | china_aluminum_operating_capacity | SMM / Baiinfo | https://www.smm.cn/ | monthly |  |  | paid | manual | no | 中國電解鋁運行產能與開工率（萬噸），付費報告；免費替代為CNIA官方公報與上市鋁企定期報告 |
| price | shfe_alumina_futures_ao | SHFE (via Sina) | https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AO0 | daily | 2023-06-19 | 2026-09-30 | free | json-api | yes | 上海期貨交易所氧化鋁期貨連續主力合約日收盤價與持倉量（元/噸） |
| price | shfe_aluminium_futures_al | SHFE (via Sina) | https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AL0 | daily | 2005-01-04 | 2026-09-30 | free | json-api | yes | 上海期貨交易所滬鋁期貨連續主力合約日收盤價與持倉量（元/噸） |
| price | alumina_fob_australia | Fastmarkets / S&P Platts | https://www.spglobal.com/commodityinsights/ | daily |  |  | paid | manual | no | 澳洲 FOB 氧化鋁現貨指數(PAX)，國際基準價；無免費公開API |
| price | china_bauxite_guinea_cif_derived | UN Comtrade / China Customs | https://comtradeapi.un.org/public/v1/preview/C/A/HS | annual | 2015-12-31 | 2024-12-31 | free | json-api | yes | 中國自幾內亞進口鋁土礦推算CIF均價（美元/噸），以進口總值÷進口量計算 |
| trade | china_bauxite_import_by_partner | UN Comtrade | https://comtradeapi.un.org/public/v1/preview/C/A/HS | annual | 2015-12-31 | 2024-12-31 | free | json-api | yes | 中國鋁土礦分國進口量與進口值（HS 260600，幾內亞/澳洲/印尼等） |
| trade | china_customs_stats_platform | China Customs | http://stats.customs.gov.cn/ | monthly |  |  | free | html-table | no | 海關總署統計在線查詢平台，含圖形驗證碼，支援查詢 HS 2606/2818.20/7601 |
| trade | guinea_bauxite_export_policy | Guinea Ministry of Mines / BCRG | https://mines.gov.gn/ | quarterly |  |  | free | pdf | no | 幾內亞鋁土礦季度出口統計與官方政策公告（礦權整頓與最低離岸參考價） |
| trade | us_unwrought_aluminum_imports | US Census / UN Comtrade | https://api.census.gov/data/timeseries/intltrade/imports/hs | monthly | 2015-01-01 | 2023-12-31 | free | json-api | yes | 美國原鋁未鍛軋鋁進口（HS 7601），Census API連線超時，Comtrade(Reporter 842)實測成功 |

---

## 實測

本調研對指派文件要求之各核心端點進行程式碼抓取實測，記錄請求結果、筆數、時間跨度與數據發布延遲：

### 1. 國際鋁業協會 IAI (International Aluminium Institute)
- **請求端點**：
  - 原鋁：`GET https://alvis.international-aluminium.org/api/publication/?publication=primary-aluminium-production`
  - 氧化鋁：`GET https://alvis.international-aluminium.org/api/publication/?publication=alumina-production`
- **認證方式**：HTTP Header `x-auth-token: VqJoChv3cGZei872eHVKUL4kdbk3CG2qw5RUpq8eV4VmMCbCJxncfzOyCo3nknz59qoWzPjVsPFffSULSWceeWAuywurxWiRVXdkqADVfKSvItSkOstAcU8yoiL6Hmr6`
- **回應狀態**：`200 OK`（JSON 格式，原鋁約 424 KB，氧化鋁約 966 KB）
- **實測筆數與起訖日期**：
  - 原鋁月度產量：共 **644 筆** 月度資料，起訖區間 `1973-01-01` 至 `2026-08-31`。
  - 冶金級氧化鋁月產量：共 **632 筆** 月度資料，起訖區間 `1974-01-01` 至 `2026-08-31`。
- **發布延遲**：通常於每個月 20~22 日發布上個月統計數據（延遲約 20~25 天）。實測時（2026-10-07）最新已發布至 2026 年 8 月份數據。

### 2. 中國國家統計局 NBS (經 DBnomics 轉載)
- **請求端點**：
  - 電解鋁：`GET https://api.db.nomics.world/v22/series/NBS/M_A02091H?observations=1`
  - 氧化鋁：`GET https://api.db.nomics.world/v22/series/NBS/M_A02091C?observations=1`
  - 鋁材：`GET https://api.db.nomics.world/v22/series/NBS/M_A02091K?observations=1`
- **回應狀態**：`200 OK`
- **實測筆數與起訖日期**：
  - 各序列各取得 **13 筆** 滾動月度資料（DBnomics 保持與 NBS 官網一致的近 13 個月滾動視窗），起訖區間為 `2025-02` 至 `2026-02`。
- **發布延遲**：國家統計局通常於每月中旬（15~18日）發布上月工業產品產量（延遲約 15~18 天）；其中每年 1、2 月受春節長假影響不單獨發布 1 月單月產量，而於 3 月合併發布 1-2 月累計產量。

### 3. 上海期貨交易所 SHFE 氧化鋁與電解鋁期貨 (經新浪財經 API)
- **請求端點**：
  - 氧化鋁連續合約 (AO0)：`GET https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AO0`
  - 滬鋁連續合約 (AL0)：`GET https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AL0`
- **認證與標頭**：需帶 `Referer: https://finance.sina.com.cn`
- **回應狀態**：`200 OK`
- **實測筆數與起訖日期**：
  - 氧化鋁 (AO0)：共 **798 根** 日 K 線，起訖區間 `2023-06-19`（合約上市日）至 `2026-09-30`。
  - 滬鋁 (AL0)：共 **5,290 根** 日 K 線，起訖區間 `2005-01-04` 至 `2026-09-30`。
- **發布延遲**：實時 / 當日收盤後（T+0），無發布延遲。

### 4. 聯合國商品貿易統計 UN Comtrade API
- **請求端點**：`GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={year}&reporterCode=156&cmdCode=260600&flowCode=M`
- **回應狀態**：`200 OK`（注意請求需間隔 2 秒以避免 429 Rate Limit）
- **實測筆數與起訖日期**：
  - 中國鋁土礦進口（HS 260600）：自 2015 年至 2024 年共抓取 **195 筆** 分來源國紀錄，匯總成 **10 筆** 年度幾內亞進口量、占比與 CIF 均價序列。
  - 美國未鍛軋鋁進口（Reporter 842, HS 7601）：2023 年抓取 **36 筆** 分來源國進口紀錄（包含加拿大 124、阿聯 784 等）。
- **發布延遲**：各國海關上傳至 UN Comtrade 存在 3~6 個月之延遲。

### 5. 美國地質調查局 USGS Mineral Commodity Summaries
- **請求端點**：`GET https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-aluminum.pdf`
- **回應狀態**：`200 OK`（大小 745 KB）
- **數據內容**：涵蓋美國與全球 20 餘國之原鋁與氧化鋁年產能、年產量及儲量。
- **發布延遲**：每年 1 月底發布上一年度之初步估計值與前兩年之修訂值（延遲約 1~2 個月）。

---

## 踩坑

在調研與實測過程中，發現多個重要的技術陷阱與反爬機制，需特別注意：

1. **IAI 官網動態架構與 Token 標頭陷阱**：
   - IAI 統計頁面（`international-aluminium.org/statistics/`）表面為 WordPress，但統計圖表完全由 SvelteKit 獨立應用動態渲染。
   - 若嘗試抓取頁面 HTML 中的表格，僅能獲得空骨架或定義說明；實際資料來自微服務 `https://alvis.international-aluminium.org/api/publication/`。
   - 認證標頭並非一般的 `Authorization: Bearer <token>`（會回傳 `401 Unauthorized`），而是專屬自訂標頭 `x-auth-token: <token>`。
2. **中國國家統計局官網 (data.stats.gov.cn) 嚴格反爬**：
   - 官方查詢接口 `easyquery.htm` 帶有動態 Session、Cookie 校驗及圖形驗證碼，非瀏覽器腳本直接請求高機率回傳 `403 Forbidden`。
   - 解法為改用 **DBnomics** 鏡像轉載端點（`api.db.nomics.world/v22/series/NBS/...`），既免反爬又穩定，但需注意必須帶參數 `?observations=1` 才會回傳時間與數值陣列（否則僅回傳元數據）。
3. **NBS 統計資料的春節斷層與滾動視窗限制**：
   - 中國國家統計局官方規定，每年 1 月不單獨發布單月工業產量，而於 2 月發布 1-2 月累計值；因此 1 月的當期產量數值為 `NA`。
   - DBnomics 僅保留 NBS 官方發布的最近 13 個月數據；若需數十年歷史月度產量，必須定期歸檔保存，或以 IAI 中國分區月產量作為長期時間序列。
4. **UN Comtrade 公開預覽 API 的 Rate Limit 限制**：
   - 公開端點（`comtradeapi.un.org/public/v1/preview/C/A/HS`）若連續並發請求，會立即觸發 `429 Too Many Requests`（錯誤提示 `Rate limit is exceeded. Try again in 2 seconds.`）。
   - 程式中必須加入 `time.sleep(2.0)` 以上之節流保護，並具備 429 自動退避重試邏輯。
5. **US Census 國際貿易 API 外部連線阻斷**：
   - 官方端點 `api.census.gov/data/timeseries/intltrade/imports/hs` 在部分網絡或非美國本地 IP 請求時會出現 `ConnectTimeoutError`（連線 30 秒超時）。
   - 備援方案可切換至 UN Comtrade（指定 Reporter Code 842 代表美國），獲取同等顆粒度的進口國別數據。
6. **期貨代碼在新浪財經的命名差異**：
   - 滬鋁期貨代碼在新浪包含 `AL0` 與 `nf_AL0`。
   - 氧化鋁期貨代碼在新浪即時報價中為 `nf_AO0`，在歷史日 K 線 API 中則為 `AO0`；若請求未加 `AO0` 或未帶 `Referer` 標頭，會回傳空 JSONP 或空陣列。

---

## 建議抓法

以下為日後撰寫資料收集腳本 `fetch_data.py` 時的標準端點與解析指引：

1. **IAI 全球與中國原鋁月度產量**：
   - **端點**：`GET https://alvis.international-aluminium.org/api/publication/?publication=primary-aluminium-production`
   - **標頭**：`{"x-auth-token": "VqJoChv3cGZei872eHVKUL4kdbk3CG2qw5RUpq8eV4VmMCbCJxncfzOyCo3nknz59qoWzPjVsPFffSULSWceeWAuywurxWiRVXdkqADVfKSvItSkOstAcU8yoiL6Hmr6", "User-Agent": "Mozilla/5.0"}`
   - **解析**：讀取 `json["data"]["publication"]["charts"]["data"]`，遍歷各期 `item["period"]["from"]`；全球總量取 `item["data"]["85"]["11"]["value"]`，中國取 `item["data"]["85"]["9"]["value"]`，單位千噸。
2. **IAI 全球與中國冶金級氧化鋁月度產量**：
   - **端點**：`GET https://alvis.international-aluminium.org/api/publication/?publication=alumina-production`
   - **標頭**：同上 `x-auth-token`。
   - **解析**：讀取 `json["data"]["publication"]["charts"]["data"]`；冶金級氧化鋁取 row key `"2"`，全球總量取 col key `"21"`，中國取 col key `"19"`，單位千噸。
3. **中國國家統計局電解鋁與氧化鋁月度產量**：
   - **端點**：
     - 電解鋁：`GET https://api.db.nomics.world/v22/series/NBS/M_A02091H?observations=1`
     - 氧化鋁：`GET https://api.db.nomics.world/v22/series/NBS/M_A02091C?observations=1`
   - **解析**：提取 `json["series"]["docs"]`，尋找 `series_code` 為 `A02091H01`（當期值）與 `A02091H02`（累計值），對應 `period` 與 `value` 陣列，單位萬噸。
4. **SHFE 氧化鋁期貨連續合約日度行情**：
   - **端點**：`GET https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AO0`
   - **標頭**：`{"Referer": "https://finance.sina.com.cn", "User-Agent": "Mozilla/5.0"}`
   - **解析**：以正則表達式 `re.search(r'\((.*)\)', resp.text)` 擷取 JSON 字串並反序列化，每筆物件欄位分別為 `d` (日期)、`o` (開盤)、`h` (最高)、`l` (最低)、`c` (收盤)、`v` (成交量)、`p` (持倉量)、`s` (結算價)。
5. **SHFE 滬鋁期貨連續合約日度行情**：
   - **端點**：`GET https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_kline=/InnerFuturesNewService.getDailyKLine?symbol=AL0`
   - **標頭與解析**：同上氧化鋁期貨。
6. **中國進口鋁土礦國別流向與幾內亞 CIF 價格推算**：
   - **端點**：`GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={YYYY}&reporterCode=156&cmdCode=260600&flowCode=M`
   - **解析**：遍歷回傳 `data` 陣列；全球總計為 `partnerCode == 0`，幾內亞為 `partnerCode == 324`，澳洲為 `partnerCode == 36`；幾內亞進口占比 = `(几内亚 netWgt / 全球 netWgt) * 100`；幾內亞 CIF 均價 (美元/噸) = `几内亚 primaryValue / (几内亚 netWgt / 1000)`。請求各年份時需間隔 2 秒以上。
7. **美國原鋁進口來源國分佈**：
   - **端點**：`GET https://comtradeapi.un.org/public/v1/preview/C/A/HS?period={YYYY}&reporterCode=842&cmdCode=7601&flowCode=M`
   - **解析**：過濾 `partnerCode == 124`（加拿大）及 `partnerCode == 784`（阿拉伯聯合大公國），提取 `primaryValue` 與 `netWgt` 計算來源國占比與進口均價。
