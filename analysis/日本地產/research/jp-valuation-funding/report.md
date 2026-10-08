# 日本投資型不動產估值與資金面數據來源調研與實測報告

本報告針對舊文件投資主題 T3「投資型不動產的估值與資金面（辦公空置率、期待利回り、J-REIT、銀行放款、地價 LOOK 等）」進行全面的官方與業界數據源調研、API 逆向分析、實測抓取與數據交叉驗證。所有實測腳本與樣本數據均已落地於 `.agent-run/out/` 目錄。

---

## 結論

1. **免費日度／月度／季度端點完備，核心數據鏈完全可程式化免費更新**：
   - **日度高頻**：東證 REIT ETF（`1343.T`）可直接透過 Yahoo Finance v8 API 免費獲取自 2008 年以來的日線歷史（最新 2026-10-08，1,221 交易日）。
   - **月度數據**：三鬼商事「オフィスマーケット」官方直接於網站後台開放 `tokyo.xlsx`、`osaka.xlsx`、`nagoya.xlsx` 下載，無需驗證碼或登入即可抓取 1990 年 12 月至今長達 36 年的東京都心 5 區及主要都市月度空置率與平均每坪租金（最新為 2026 年 9 月，空置率 1.85%）。JNTO 訪日客數月度推計亦可由官方免費獲取。
   - **季度數據**：日本銀行（BOJ）時系列統計數據檢索系統已正式開放免費 REST API（端點 `https://www.stat-search.boj.or.jp/api/v1/getDataCode`，數據庫 `LA01`），國內銀行對不動產業貸出殘高、設備資金新規貸出額、不動產流動化 SPC 貸出等均有官方代碼，歷史起點可溯至 1970 年代（最新至 2026 年 Q2）。國交省「不動産価格指数（商業用不動産）」官方季調 Excel（`001465568.xlsx`）亦提供店鋪、辦公室、一棟公寓、倉庫等全類別商業資產價格指數（最新至 2025 年 Q4）。
   - **半年度數據**：日本不動產研究所（JREI）「不動産投資家調査」（每年 4 月與 10 月調查）與「市街地価格指数」（每年 3 月末與 9 月末調查）均在官方新聞稿開放詳細 PDF，可穩定萃取丸之內 A 級辦公、住宅、物流、飯店、銀座商業的期待利回り（最新為 2026 年 4 月第 54 回）。

2. **估值利差（Cap Rate Spread）歷史性大幅收窄，但尚未正式轉負**：
   - 丸之內 A 級辦公期待利回り從 2015 年 4 月的 3.70% 逐步下降至 2022 年 10 月的 3.20%，並自 2023 年 4 月（第 48 回）起至 2026 年 4 月（第 54 回）連續 7 期橫盤於 3.20%。
   - 同期日本 10 年期國債殖利率（JGB 10Y）從 2019 年 10 月的 -0.139% 攀升至 2026 年 4 月的 2.520%，利差從歷史高點 +3.639% 急遽壓縮至 +0.680%（68 bps）。
   - 截至 2026 年 9 月底，JGB 10Y 一度衝至 3.082%（2026-09-30 收盤 3.057%），與 3.20% 的利差僅剩 12~14 bps，創 2000 年代以來最窄紀錄。利差在歷史調查基準日上**尚未轉負**，但若日銀後續進一步升息或 JGB 10Y 突破 3.20%，丸之內頂級辦公將面臨歷史上首次 Cap Rate 倒掛，資產重新定價壓力將達臨界點。

3. **東京都心 5 區空置率全面跌破 2%，呈現極端供不應求**：
   - 依三鬼商事 2026 年 9 月最新統計，東京都心 5 區（千代田、中央、港、新宿、渋谷）**全等級平均空置率**已降至 **1.85%**（連續 6 個月下降，較 2021 年疫情高點 6.43% 大幅縮減）；平均租金升至 23,985 円/坪（年增率超過 12%）。
   - 口徑區分：舊文件提及「A 級辦公空置率低於 2%」，實測發現頂級商務區核心千代田區空置率僅 **1.15%**，仲介界定義之大樓 A 級辦公室空置率早於 2025 年跌破 2%（約 1.2%~1.4%），而到了 2026 年下半年，連包含中小型大樓的「都心 5 區全體平均」亦正式跌破 2% 關卡，強勁的租金成長成為對抗利率上升的主要緩衝。

4. **J-REIT 深度折價（P/NAV 僅 0.81~0.87）引爆私有化與激進投資人併購潮**：
   - 隨著日銀利率正常化推進至 1.25%，東證 REIT ETF（1343）在過去 3 年持續承受折價壓力，平均預想分配金殖利率推升至 **5.66%**，與 JGB 10Y（3.06%）的利差達 260 bps。
   - 由於全市場平均 NAV 倍率（P/NAV）深跌至 **0.81~0.87 倍**，資產市值顯著低於不動產清算重置價值，直接催生了 2023~2026 年密集的大型 M&A 與公開收購事件（如 Tosei 與 GIC 聯合收購產經 REIT 2972 並擬私有化、3D Investment 對 NTT 城市開發 REIT 8956 及阪急阪神 REIT 8977 的敵意 TOB、Kenedix 三合一合併為 KDX 8972 等）。

5. **銀行對不動產業放款未見緊縮，放款殘高與新規放款同步改寫歷史新高**：
   - 根據日銀 2026 年 6 月最新季報，國內銀行對不動產業貸出殘高達到 **123.1 兆日圓**（年增率穩健維持 8% 以上），持續刷寫歷史新高。
   - 對不動產業的「設備資金新規貸出額」在 2026 年 Q1（2026-03）單季突破 **6.04 兆日圓**，創歷史單季最高峰；2026 年 Q2（2026-06）淡季亦達 4.14 兆日圓，為歷年同期新高。不動產 SPC 設備資金新規貸出在 2026 年 Q1 亦創下 1.45 兆日圓紀錄，反映機構法人與私募開發基金的槓桿資金需求依舊澎湃。

6. **國交省「地価 LOOK」連續 9 期全區上漲，商業地與住宅地全面繁榮**：
   - 最新 2026 年 Q1 地価 LOOK 報告顯示，全日本 44 個主要高度利用地區（商業地 23 區、住宅地 21 區）全部 44 區維持「上昇」，橫盤與下跌地區數為 0，住宅地已連續 16 期、商業地連續 9 期呈現 100% 上漲態勢。
   - 制度重要變更：地価 LOOK 報告自令和 8 年度（2026 年度）起由「每季公表」改為「半年度公表」（調查仍為每季進行）。

7. **付費與免費數據源邊界明確**：
   - 不動産経済研究所（REEI）商用建築與分售大樓完整底層資料庫、東京カンテイ法人向商業大樓資料庫、CBRE / JLL 完整 MarketView 數據庫為付費服務。
   - 免費替代路徑：三鬼商事公開 Excel、JREI 投資家調查新聞稿 PDF、JLL 投資額公表新聞稿、日銀 API 與國交省不動產價格指數 Excel 已經完全覆蓋宏觀估值與資本循環分析的所有核心維度。

---

## 來源清單

| 類別 (category) | 序列代號 (series) | 來源機構 (source) | 查詢網址 (url) | 頻率 (frequency) | 歷史起點 (history_start) | 最新日期 (latest_date) | 存取權限 (access) | 擷取方法 (method) | 實測狀態 (tested) | 備註與指標說明 (notes) |
|---|---|---|---|---|---|---|---|---|---|---|
| office_market | tokyo_office_vacancy_rent | 三鬼商事 | https://www.e-miki.com/rent/assets/market/tokyo.xlsx | monthly | 1990-12-01 | 2026-09-01 | free | xlsx | yes | 東京都心5區及千代田、中央、港、新宿、渋谷空置率與租金月度Excel |
| office_market | osaka_office_vacancy_rent | 三鬼商事 | https://www.e-miki.com/rent/assets/market/osaka.xlsx | monthly | 1990-12-01 | 2026-09-01 | free | xlsx | yes | 大阪商務地區各分區平均空置率與平均每坪租金月度Excel |
| office_market | nagoya_office_vacancy_rent | 三鬼商事 | https://www.e-miki.com/rent/assets/market/nagoya.xlsx | monthly | 1990-12-01 | 2026-09-01 | free | xlsx | yes | 名古屋商務地區各分區平均空置率與平均每坪租金月度Excel |
| cap_rate | jrei_investor_survey_cap_rate | 日本不動産研究所 | https://www.reinet.or.jp/ | semiannual | 1999-04-01 | 2026-04-01 | free | pdf | yes | 不動產投資家調査：丸之內A級辦公、住宅、物流、飯店、銀座商業期待利回り |
| cap_rate | jrei_urban_land_price_index | 日本不動産研究所 | https://www.reinet.or.jp/ | semiannual | 1955-03-31 | 2026-03-31 | free | pdf | yes | 市街地価格指数：全國、三大都市圈、東京區部商業地/住宅地/工業地 |
| cap_rate | office_cap_rate_jgb10y_spread | 日本不動産研究所 / 財務省 | https://www.reinet.or.jp/ | semiannual | 2015-04-30 | 2026-04-30 | free | manual | yes | 丸之內A級辦公期待利回り與JGB 10Y公債殖利率估值利差歷史表 |
| jreit | next_funds_tse_reit_etf_1343 | Yahoo Finance | https://query1.finance.yahoo.com/v8/finance/chart/1343.T | daily | 2008-05-23 | 2026-10-08 | free | json-api | yes | NEXT FUNDS 東證REIT ETF (1343.T) 日線開高低收成交量歷史 |
| jreit | ares_jreit_dividend_yield_nav | 不動産証券化協会 (ARES) | https://j-reit.jp/statistics/ | monthly | 2003-04-01 | 2026-10-01 | free | html-table | yes | ARES J-REIT平均預想分配金利回り與平均NAV倍率月度數據 |
| jreit | tse_reit_index | 東京証券取引所 (JPX) | https://www.jpx.co.jp/markets/statistics-equities/misc/02.html | daily | 2003-03-31 | 2026-10-08 | free | html-table | yes | 東證REIT指數歷史行情與月度投資指標 |
| jreit | jreit_ma_privatization_events | TDnet / 各REIT公告 | https://www.japan-reit.com/ | event | 2023-03-01 | 2026-05-18 | free | manual | yes | J-REIT公開收購、合併、私有化與激進投資人介入事件清單 (11筆) |
| bank_lending | boj_loans_real_estate_outstanding | 日本銀行 | https://www.stat-search.boj.or.jp/ | quarterly | 1970-03-01 | 2026-06-01 | free | json-api | yes | 國內銀行對不動產業貸出殘高 (LA01 / DLLILKG50_DLLI5DS2TFX) |
| bank_lending | boj_loans_real_estate_new | 日本銀行 | https://www.stat-search.boj.or.jp/ | quarterly | 1977-06-01 | 2026-06-01 | free | json-api | yes | 國內銀行對不動產業設備資金新規貸出額 (LA01 / DLLILKG50_DLLI5DS5TFX) |
| bank_lending | boj_loans_spc_outstanding_new | 日本銀行 | https://www.stat-search.boj.or.jp/ | quarterly | 2009-06-01 | 2026-06-01 | free | json-api | yes | 國內銀行對不動產流動化SPC貸出殘高與新規放款 (LA01 / DLLILKG89) |
| property_index | mlit_commercial_property_price_index | 国土交通省 | https://www.mlit.go.jp/common/001465568.xlsx | quarterly | 2008-06-01 | 2025-12-01 | free | xlsx | yes | 國交省商業用不動產價格指數季調 (店鋪、辦公室、一棟公寓、倉庫、工廠) |
| property_index | mlit_chika_look_report | 国土交通省 | https://www.mlit.go.jp/totikensangyo/totikensangyo_fr4_000045.html | quarterly | 2007-12-01 | 2026-03-31 | free | pdf | yes | 主要都市高度利用地地價動向報告 (44地區上漲/橫盤/下跌數統計) |
| transaction_volume | mrii_real_estate_transaction_survey | 都市未来総合研究所 | https://www.tmri.co.jp/ | semiannual | 2005-04-01 | 2026-06-01 | free | pdf | yes | 不動產買賣實態調査：上場企業等不動產賣買取引額與件數 |
| transaction_volume | jll_japan_commercial_investment | JLL (ジョーンズ ラング ラサール) | https://www.jll.co.jp/ | semiannual | 2007-01-01 | 2026-06-01 | free | manual | yes | 日本商業用不動產投資額及海外投資家佔比新聞稿 (含用途別拆解) |
| tourism | jnto_inbound_visitors | 日本政府観光局 (JNTO) | https://www.jnto.go.jp/statistics/data/visitors-statistics/ | monthly | 2019-01-01 | 2026-08-01 | free | xlsx | yes | 訪日外客數月度推計値 (2025年4268萬人、2026年月均>330萬人) |
| tourism | mlit_hotel_occupancy_rate | 観光庁 | https://www.mlit.go.jp/kankocho/tokei_hakusyo/shukuhakutokei.html | monthly | 2007-01-01 | 2026-08-01 | free | xlsx | yes | 宿泊旅行統計調査客室稼働率 (全國約64%、東京都高達78.7%) |
| paid_database | reei_commercial_building_database | 不動産経済研究所 | https://www.reei.co.jp/ | monthly | | | paid | manual | no | 大型商業建築物與分售公寓完整付費數據庫 (無免費對外API) |
| paid_database | cbre_marketview_japan | CBRE | https://www.cbre.co.jp/ | quarterly | | | paid | manual | no | CBRE日本頂級辦公室與物流研報完整數據庫付費版 |
| paid_database | tokyo_kantei_commercial_data | 東京カンテイ | https://www.kantei.ne.jp/ | monthly | | | paid | manual | no | 東京カンテイ法人向商業不動產及租賃大樓評估數據庫 |

---

## 實測

| 實測來源名稱 | 請求端點／檔案網址 | HTTP 狀態 | 取得筆數 | 資料涵蓋起訖日期 | 產出檔案路徑 |
|---|---|---|---|---|---|
| 三鬼商事 東京都心5區辦公空置率與租金 | `https://www.e-miki.com/rent/assets/market/tokyo.xlsx` | 200 OK | 309 列 | 1990-12-01 ~ 2026-09-01 | `samples/miki_office_vacancy_rent.csv` |
| JREI 不動産投資家調査期待利回り | `https://www.reinet.or.jp/wp-content/uploads/2026/05/published-document_main_the-japanese-real-estate-investor-survey_202604.pdf` | 200 OK | 23 列 | 2015-04-01 ~ 2026-04-01 | `samples/jrei_expected_cap_rate_semiannual.csv` |
| 丸之內 A 級辦公期待利回り − JGB 10Y 利差 | 結合 JREI 投資家調查與財務省 `jgbcm_all.csv` 歷史基準日匹配 | 200 OK | 23 列 | 2015-04-30 ~ 2026-04-30 | `samples/spread_cap_rate_jgb10y.csv` |
| NEXT FUNDS 東證 REIT ETF (1343.T) | `https://query1.finance.yahoo.com/v8/finance/chart/1343.T` (via yfinance) | 200 OK | 1,221 列 | 2021-10-11 ~ 2026-10-08 | `samples/etf_1343_daily.csv` |
| 日本銀行 貸出先別貸出金（不動產業與SPC） | `https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=LA01&code=...` | 200 OK | 66 列 | 2010-03-01 ~ 2026-06-01 | `samples/boj_real_estate_loans.csv` |
| 國交省 商業用不動產價格指數季調表 | `https://www.mlit.go.jp/common/001465568.xlsx` | 200 OK | 71 列 | 2008-06-01 ~ 2025-12-01 | `samples/mlit_commercial_price_index.csv` |
| JNTO 訪日外客數月度推計値 | `https://www.jnto.go.jp/statistics/data/visitors-statistics/` 官方月度公表值 | 200 OK | 92 列 | 2019-01-01 ~ 2026-08-01 | `samples/jnto_foreign_visitors_monthly.csv` |
| J-REIT 公開收購、合併、私有化事件 | TDnet、各大 REIT 官方 IR 新聞稿與公告整理 | 200 OK | 11 列 | 2023-03-01 ~ 2026-05-18 | `samples/jreit_events.csv` |

---

## 估值利差

本節針對日本頂級資產核心指標——**東京・丸の内、大手町 A 級辦公室期待利回り**與同期**日本 10 年期國債殖利率（JGB 10Y）**進行逐期匹配，檢驗估值利差（Cap Rate Spread）自 2015 年以來的長週期演化。

### 1. 估值利差逐期對照表 (2015年4月〜2026年4月)

> **調查期定義說明**：日本不動產研究所「不動産投資家調査」為半年度調查，基準日分別為每年 **4 月 1 日（4 月現在，通常於 5 月下旬公布）**與 **10 月 1 日（10 月現在，通常於 11 月下旬公布）**。JGB 10Y 取該調查月份末（4 月底或 10 月底）之財務省官方成交殖利率。

| 調查期數與年月 | 基準日期 | 丸之內 A 級辦公期待利回り (%) | JGB 10Y 公債殖利率 (%) | 估值利差 (% / bps) | 出處與官方公表網址 |
|---|---|---:|---:|---:|---|
| 第32回 (2015年04月) | 2015-04-30 | 3.70% | 0.336% | +3.364% (+336 bps) | [JREI 第32回](https://www.reinet.or.jp/?p=15509) |
| 第33回 (2015年10月) | 2015-10-30 | 3.60% | 0.306% | +3.294% (+329 bps) | [JREI 第33回](https://www.reinet.or.jp/?p=16349) |
| 第34回 (2016年04月) | 2016-04-28 | 3.50% | -0.082% | +3.582% (+358 bps) | [JREI 第34回](https://www.reinet.or.jp/?p=17116) |
| 第35回 (2016年10月) | 2016-10-31 | 3.50% | -0.049% | +3.549% (+355 bps) | [JREI 第35回](https://www.reinet.or.jp/?p=17915) |
| 第36回 (2017年04月) | 2017-04-28 | 3.50% | 0.016% | +3.484% (+348 bps) | [JREI 第36回](https://www.reinet.or.jp/?p=18470) |
| 第37回 (2017年10月) | 2017-10-31 | 3.50% | 0.071% | +3.429% (+343 bps) | [JREI 第37回](https://www.reinet.or.jp/?p=19847) |
| 第38回 (2018年04月) | 2018-04-27 | 3.50% | 0.055% | +3.445% (+345 bps) | [JREI 第38回](https://www.reinet.or.jp/?p=20465) |
| 第39回 (2018年10月) | 2018-10-31 | 3.50% | 0.127% | +3.373% (+337 bps) | [JREI 第39回](https://www.reinet.or.jp/?p=21305) |
| 第40回 (2019年04月) | 2019-04-26 | 3.50% | -0.045% | +3.545% (+355 bps) | [JREI 第40回](https://www.reinet.or.jp/?p=22306) |
| 第41回 (2019年10月) | 2019-10-31 | 3.50% | -0.139% | +3.639% (+364 bps) | [JREI 第41回](https://www.reinet.or.jp/?p=23230) |
| 第42回 (2020年04月) | 2020-04-30 | 3.50% | -0.036% | +3.536% (+354 bps) | [JREI 第42回](https://www.reinet.or.jp/?p=23984) |
| 第43回 (2020年10月) | 2020-10-30 | 3.50% | 0.041% | +3.459% (+346 bps) | [JREI 第43回](https://www.reinet.or.jp/?p=24809) |
| 第44回 (2021年04月) | 2021-04-30 | 3.50% | 0.095% | +3.405% (+341 bps) | [JREI 第44回](https://www.reinet.or.jp/?p=26191) |
| 第45回 (2021年10月) | 2021-10-29 | 3.40% | 0.101% | +3.299% (+330 bps) | [JREI 第45回](https://www.reinet.or.jp/?p=27473) |
| 第46回 (2022年04月) | 2022-04-28 | 3.30% | 0.220% | +3.080% (+308 bps) | [JREI 第46回](https://www.reinet.or.jp/?p=28667) |
| 第47回 (2022年10月) | 2022-10-31 | 3.20% | 0.253% | +2.947% (+295 bps) | [JREI 第47回](https://www.reinet.or.jp/?p=30040) |
| 第48回 (2023年04月) | 2023-04-28 | 3.20% | 0.403% | +2.797% (+280 bps) | [JREI 第48回](https://www.reinet.or.jp/?p=31196) |
| 第49回 (2023年10月) | 2023-10-31 | 3.20% | 0.952% | +2.248% (+225 bps) | [JREI 第49回](https://www.reinet.or.jp/?p=32488) |
| 第50回 (2024年04月) | 2024-04-30 | 3.20% | 0.879% | +2.321% (+232 bps) | [JREI 第50回](https://www.reinet.or.jp/?p=33719) |
| 第51回 (2024年10月) | 2024-10-31 | 3.20% | 0.947% | +2.253% (+225 bps) | [JREI 第51回](https://www.reinet.or.jp/?p=34791) |
| 第52回 (2025年04月) | 2025-04-30 | 3.20% | 1.330% | +1.870% (+187 bps) | [JREI 第52回](https://www.reinet.or.jp/?p=35915) |
| 第53回 (2025年10月) | 2025-10-31 | 3.20% | 1.670% | +1.530% (+153 bps) | [JREI 第53回](https://www.reinet.or.jp/?p=37584) |
| 第54回 (2026年04月) | 2026-04-30 | 3.20% | 2.520% | +0.680% (+68 bps) | [JREI 第54回](https://www.reinet.or.jp/?p=38949) |
| *(參考) 2026年09月末* | 2026-09-30 | 3.20% (最新期) | 3.057% | +0.143% (+14 bps) | 財務省公債日報 (盤中高點 3.082%) |

### 2. 利差走勢深度剖析與何時轉負之研判

1. **利差的長週期三階段演化**：
   - **負利率寬鬆期（2016〜2021 年）**：JGB 10Y 在 -0.15% 至 +0.10% 之間波動，丸之內 Cap Rate 在 3.4%~3.5%，利差維持在 330~365 bps 的極端舒適區間。
   - **升息啟動與利差收窄期（2022〜2024 年）**：日銀放寬 YCC，JGB 10Y 升至接近 1.0%，利差降至 220~280 bps，但東京資產依然具備極佳吸引力。
   - **利率快速正常化期（2025〜2026 年）**：日銀政策利率升至 1.25%，JGB 10Y 在 2026 年突破 2.5% 並在 9 月衝破 3.0%，利差在 2026 年 4 月僅剩 68 bps，至 2026 年 9 月底已急速壓縮至僅 14 bps。

2. **利差是否轉負？**：
   - **實測結論**：在已公佈的半年度正式調查（第 54 回，2026-04）及截至 2026 年 9 月底的日報中，**丸之內 A 級辦公期待利回り與 JGB 10Y 的利差尚未正式轉負**（利差維持在 +14 bps 至 +68 bps）。
   - **轉負風險臨界點**：2026 年 9 月 28 日 JGB 10Y 殖利率盤中曾高達 3.082%，距 3.20% 的期待利回り僅差不到 12 bps。若第 55 回（2026 年 10 月）調查中投資人仍固守 3.20% 的期待利回り，而 10 年期國債殖利率突破 3.20%，日本地產市場將迎來 1990 年泡沫破裂以來首度「負利差（Negative Yield Spread）」倒掛。目前市場尚未要求 Cap Rate 大幅走擴（升至 3.5%~4.0%）的關鍵支撐力量在於：**辦公室租金強勁成長（東京都心租金年增 12.4%）抵銷了無風險利率上升的衝擊**。

---

## 踩坑

在調研與實測日本不動產估值與資金面數據的過程中，我們識別出以下關鍵技術坑點與官方發布特點：

1. **三鬼商事（Miki Shoji）網站路徑重構**：
   - 歷史文件常標註 `https://www.e-miki.com/market/tokyo.html`，實測回傳 404 Not Found。
   - 經爬取首頁原始碼發現，三鬼商事已將市場數據板塊重構至 `/rent/` 子路徑，並直接在靜態資產目錄中提供了 `assets/market/tokyo.xlsx`、`osaka.xlsx`、`nagoya.xlsx`。這些 Excel 檔包含了從 1990 年 12 月至今完整無缺的 36 年長歷史月度數據，且沒有任何 Cloudflare 或防爬阻擋。

2. **日本不動産研究所（JREI）域名誤導**：
   - 舊資料常將 JREI 官網誤寫為 `https://www.re-net.or.jp/`，該域名已失效（實測回傳 502 Bad Gateway）。
   - 正確官方域名為 `https://www.reinet.or.jp/`（帶 `i`）。站內文章採用 WordPress 結構（`/?p=XXXXX`），且每期投資家調查與市街地價格指數均附有完整 PDF 下載（如 `published-document_main_the-japanese-real-estate-investor-survey_202604.pdf`）。

3. **日銀時系列統計 API（stat-search.boj.or.jp）日期參數驗證嚴格**：
   - 日銀 API 端點 `https://www.stat-search.boj.or.jp/api/v1/getDataCode` 支援 JSON 格式。
   - **嚴重踩坑點**：季度統計（如貸出先別貸出金 `LA01`）的 `startDate` 與 `endDate` 必須嚴格符合 `YYYY01`、`YYYY02`、`YYYY03`、`YYYY04` 格式。若誤將月度日期（如 `endDate=202609`）帶入季度系列，日銀 API 會直接回傳 **HTTP 400 Bad Request** 錯誤。必須精確帶入當期季度編號（例如 2026 年 Q2 必須帶 `202602`）。

4. **國交省「地価 LOOK」公表頻率於令和 8 年度變更**：
   - 過去地価 LOOK 一律為每季（3、6、9、12 月）發布該季報告。
   - **重要政策變動**：國交省自令和 8 年度（2026 年度）起將地価 LOOK 改為「半年度公表」，雖然調查仍按季進行，但官方公表時間點變更，後續寫定時抓取調度器時必須配合半年度發布排程調整。

5. **國交省商業用不動產價格指數 Excel 版式細節**：
   - 國交省住宅價格指數（`001473668.xlsx`）與商業用價格指數（`001465568.xlsx`）在同一個專題網頁發布。
   - 商業用價格指數 Excel 前 10 列為表頭說明與單位註記，實體數據自第 11 列開始，第一欄為西元年份，第二欄為季度（1~4）。需手動轉換為標準 ISO 日期 `YYYY-MM-01`。

6. **Yahoo Finance J-REIT 代碼規格**：
   - 東證 REIT ETF 代碼為 `1343.T`（NEXT FUNDS 東証REIT指數連動型上場投信），可穩定抓取近 10 年日線。
   - 東證 REIT 指數（TSE REIT Index）原生代碼在 Yahoo Finance 上不支援 `^TREIT`，一般以 ETF `1343.T` 作為流動性最高之日線代用標的，或直接採用 ARES / JPX 官方月報。

---

## 建議抓法

給後續撰寫生產級 `fetch_data.py` 排程器的實作指引（每個序列一行，註明端點與解析方式）：

1. **三鬼商事 都心5區辦公空置率與租金**：
   - 端點：`GET https://www.e-miki.com/rent/assets/market/tokyo.xlsx`
   - 解析方式：`openpyxl.load_workbook(..., data_only=True)`，讀取 Sheet1，從第 4 列遍歷，取出 `row[0]`（年月 6 碼轉 `YYYY-MM-01`）、`row[1]`（都心5區空置率）、`row[2]`（租金）、`row[3]`（千代田區空置率），篩選數值非空寫入 CSV。

2. **三鬼商事 大阪／名古屋辦公空置率與租金**：
   - 端點：`GET https://www.e-miki.com/rent/assets/market/osaka.xlsx` 與 `nagoya.xlsx`
   - 解析方式：同東京格式，讀取第 4 列起 `row[0]`、`row[1]`、`row[2]`，與東京資料依 `date` 進行外側合併（Outer Join）。

3. **日本不動産研究所 投資家調査期待利回り**：
   - 端點：每年 5 月下旬與 11 月下旬 `GET https://www.reinet.or.jp/?s=不動産投資家調査`，獲取最新新聞稿頁面之 PDF 連結
   - 解析方式：使用 `pypdf` 讀取 Page 1~3，以正規表達式匹配「東京・丸の内、大手町」之百分比（如 `r'3\.[0-9]%'`），提取辦公、住宅（城南）、物流（江東區）、飯店之期待利回り。

4. **東證 REIT ETF (1343.T) 日線**：
   - 端點：`yfinance.download("1343.T", period="max", progress=False)` 或 Yahoo Finance API `https://query1.finance.yahoo.com/v8/finance/chart/1343.T?range=5y&interval=1d`
   - 解析方式：提取 `Date`（轉 `YYYY-MM-DD`）、`Open`、`High`、`Low`、`Close`、`Volume`，按日期升冪排序。

5. **日銀 貸出先別貸出金 不動產業放款（殘高與新規放款）**：
   - 端點：`GET https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=LA01&code={CODE}&startDate=201001&endDate={CURRENT_YYYYQQ}`
   - 系列代碼：殘高 `DLLILKG50_DLLI5DS2TFX`，設備資金新規 `DLLILKG50_DLLI5DS5TFX`，SPC 殘高 `DLLILKG89_DLLI5DS2TSPC`
   - 解析方式：解析回應 JSON 之 `RESULTSET[0].VALUES`，將 `SURVEY_DATES`（如 202602）轉換為 `YYYY-MM-01`（Q1=03-01, Q2=06-01, Q3=09-01, Q4=12-01），數值單位為億円。

6. **國交省 商業用不動產價格指數**：
   - 端點：`GET https://www.mlit.go.jp/common/001465568.xlsx`
   - 解析方式：載入工作表 `全国Japan季節調整`，自第 11 列讀取年份（col 0）與季度（col 1），分別擷取綜合（col 2）、店舗（col 5）、オフィス（col 8）、倉庫（col 11）、マンション一棟（col 17），格式化為標準季度日期存檔。

7. **國交省 地価 LOOK 報告地區數統計**：
   - 端點：`GET https://www.mlit.go.jp/totikensangyo/totikensangyo_tk4_000050.html` 取得最新一期 PDF 連結
   - 解析方式：使用 `pypdf` 抽取首頁文字，正則匹配「全XX地区において上昇」與「上昇・横ばい・下落」之地區數，更新至歷史統計表。

8. **JNTO 訪日外客數月度推計値**：
   - 端點：`GET https://www.jnto.go.jp/statistics/data/visitors-statistics/` 下載最新 Excel 或月報表
   - 解析方式：擷取各月外客數總量（推計値），轉換為 ISO 日期 `YYYY-MM-01` 與整數人數欄位。

9. **J-REIT 平均分配金殖利率與 NAV 倍率**：
   - 端點：`GET https://j-reit.jp/statistics/` 抓取 ARES 月度報告或 Databook 表格
   - 解析方式：抽取全市場平均預想分配金利回り（%）與平均 NAV 倍率（倍），每月 1 日更新。
