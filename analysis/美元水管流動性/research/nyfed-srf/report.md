# nyfed-srf 報告：紐約 Fed 常備回購機制（SRF）用量與利率

產出：`srf_usage.csv`（E1，SRF 用量）、`srf_rate.csv`（E2，SRF 利率與目標區間上限）。
抓取程式：`fetch.py`（可重跑，`--start` 預設 2021-07-28，`--end` 預設 2026-11-06，`--offline` 只讀 raw/ 快取）。
驗收：`verify.py nyfed-srf` 通過（PASS）。

## 資料來源

### srf_usage.csv

| 區段 | 日期 | 來源 | 網址 | 取得方式 |
|---|---|---|---|---|
| A（主來源） | 2024-04-23 ～ 2026-11-06（635 個操作日） | 紐約 Fed Markets API，repo 操作結果 | `https://markets.newyorkfed.org/api/rp/repo/all/results/last/999.json` | 單次 GET，回傳最近 999 筆操作；快取於 `raw/nyfed_repo_results.json` |
| B（補齊） | 2021-07-28 ～ 2024-04-22（683 個列） | FRED（聖路易 Fed），`RPTTLD` | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=RPTTLD` | 快取於 `raw/fred_RPTTLD.csv`，只填 accepted 系列（見下） |

- **SRF 篩選條件**：NY Fed API 回傳的 `operationType == "Repo"` 且 `auctionStatus == "Results"` 的全部操作。此 feed 內的操作皆為 standing repo（SRF）操作，包含 Term 操作（窗口內 3 筆）與 Small Value Exercise（SVE）小額測試（窗口內 10 筆，計入 ops_count）。備註含 "SRF" 字樣的操作有 120 筆。窗口內無 `operationType != "Repo"` 或非 Results 的操作（排除 0 筆）。
- **為何需要 FRED**：API 端點只能取得最近 N 筆，實測 N ≤ 999（N = 1000 起回 HTTP 400），窗口起點是 2024-04-22，早於此的操作無法從 API 取得。
- **切點**：API 窗口最早日期（2024-04-22）可能只含部分操作，因此只有嚴格晚於該日的日期用 API，2024-04-22（含）以前用 FRED。
- **重疊檢驗**：2024-04-23 之後，FRED `RPTTLD` 與 API 每日總量一致 631 天、不一致 4 天（共 635 個 API 操作日）（2026-02-18、2026-02-19、2026-10-20、2026-10-21）。不一致的原因是 FRED 有時把操作記在次一營業日（結算日）：2026-10-20 為 Term 操作 0.067 bn（API 記在 10-20，FRED 記在 10-21）；2026-02-18 為一筆 Overnight 操作 0.06 bn（API 記在 02-18，FRED 記在 02-19）。其餘日期兩者一致。

### srf_rate.csv

| 欄位 | 來源 | 網址 | 說明 |
|---|---|---|---|
| `target_upper` | FRED `DFEDTARU`（Federal Funds Target Range - Upper Limit） | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU` | 快取於 `raw/fred_DFEDTARU.csv`，日曆日序列 |
| `srf_min_bid_rate` | NY Fed API 的操作最低投標利率（同上 A 段） | 同上 | 只有 2024-04-23 起有值（635 列）；之前留空 |

### 試過但不用的來源

- `https://markets.newyorkfed.org/api/rp/repo/all/results/search.json?startDate=...&endDate=...`（及 operationTypes、format 等參數變體）：全部 HTTP 400，無法依日期區間查詢。
- `…/results/last/N.json`，N ≥ 1000：HTTP 400（999 可用）。
- `…/reverserepo/all/results/search.json?...`：HTTP 400（與本任務無關，未採用）。
- FRED `RPONTSYAWARD`、`RPONTTLAWARD`、`RPONTSYPD` 等代碼：HTTP 404（不存在），未採用。
- SRF 最低投標利率的逐日歷史來源：本次沒有找到可直接抓取的逐日公布資料。搜尋結果摘要（未開啟全文）提到聯準會 2021-07-28 新聞稿（`https://www.federalreserve.gov/newsevents/pressreleases/monetary20210728b.htm`）載明起始利率 0.25%（即當時目標區間上限），以及紐約 Fed SRF FAQ（`https://www.newyorkfed.org/markets/repo-agreement-ops-faq-241107`）載明 2024-11 時點為 4.75%。這些都不是逐日資料，因此未用來填 2024-04-22 以前的 `srf_min_bid_rate`，也沒有以 `target_upper` 代填。

## 欄位與單位

### srf_usage.csv

| 欄位 | 單位 | 說明 | API 段來源欄位 | FRED 段來源 |
|---|---|---|---|---|
| `date` | — | 操作日（`operationDate`）；FRED 段為 FRED 觀測日 | `operationDate` | `observation_date` |
| `ops_count` | 場 | 當日 SRF 操作場數（含 SVE、Term） | 計數 | 留空 |
| `submitted_bn` | 十億美元 | 當日投標總額（同日加總） | `totalAmtSubmitted`（美元）÷ 1e9 | 留空 |
| `accepted_bn` | 十億美元 | 當日得標總額（同日加總） | `totalAmtAccepted` ÷ 1e9 | FRED `RPTTLD`（十億美元；Overnight + Term 總量） |
| `accepted_treasury_bn` | 十億美元 | 公債得標 | `details[securityType=Treasury].amtAccepted` 加總 | FRED `RPONTSYD`（僅 Overnight） |
| `accepted_agency_bn` | 十億美元 | 機構債得標 | `details[securityType=Agency].amtAccepted` 加總 | FRED `RPONAGYD`（僅 Overnight） |
| `accepted_mbs_bn` | 十億美元 | MBS 得標 | `details[securityType=Mortgage-Backed].amtAccepted` 加總 | FRED `RPONMBSD`（僅 Overnight） |
| `min_bid_rate` | 百分比（%） | 當日各操作最低投標利率的最高值 | 每筆操作：有 `minimumBidRate` 用它，固定利率操作（Full Allotment）用 `percentOfferingRate`，取 details 內最大值；之後取當日最高 | 留空 |

- 金額：API 為美元整數，換算十億美元後保留精確小數（最多 9 位）；FRED 為十億美元，三位小數（即百萬美元精度）。
- 用量為 0 的日子：API 段有操作即有列（accepted 為 0 的列）；FRED 段 `RPTTLD` 有值即有列（值為 0 的列）。
- 列數：API 段 635 列（2024-04-23 ～ 2026-11-06），FRED 段 683 列（2021-07-28 ～ 2024-04-22）。FRED 段的平日若 FRED 無觀測值（見缺口），不補列。

### srf_rate.csv

| 欄位 | 單位 | 說明 |
|---|---|---|
| `date` | — | 日曆日（FRED 序列所有有值的日期，含週末與假日，值為延續值） |
| `target_upper` | 百分比（%） | FRED `DFEDTARU`，聯邦資金利率目標區間上限 |
| `srf_min_bid_rate` | 百分比（%） | 該日 SRF 操作最低投標利率（來自 srf_usage 的 `min_bid_rate` 對齊）；無 API 操作的日期（週末、假日、2024-04-22 以前）留空 |

- 日曆日的範圍採 FRED `DFEDTARU` 的全部有值日期（2018-01-02 ～ 2026-11-06，共 3231 列，即日曆日數）。這是對「每個日曆營業日一列」的解讀：本次保留週末與假日，若要改成純營業日，需改 `fetch.py` 的篩選。

## 公布時間

- **NY Fed SRF 結果**：操作當日公布。每場次有 `releaseTime`（公布）與 `closeTime`（截止）欄位，例：近期早場 08:15 公布、08:30 截止；2024-07-02 的一場為 13:30 公布、13:45 截止（午場）。`lastUpdated` 為結果更新時間。資料所屬日期（`operationDate`）與公布日期相同。
- **FRED `RPTTLD` 等**：日頻序列，所屬日期為觀測日（操作日或結算日，依序列定義）。Term 操作可能落在結算日（見上方重疊檢驗）。本次未驗證 FRED 的每日更新時間點。
- **FRED `DFEDTARU`**：日頻，值為目標區間上限在該日生效的值。本次未核對 FOMC 決議日與 FRED 變動日的對應關係。

## 實測結果

### 列數與起訖

| 檔案 | 列數（含表頭） | 資料列 | 起 | 訖 |
|---|---|---|---|---|
| `srf_usage.csv` | 1319 | 1318 | 2021-07-28 | 2026-11-06 |
| `srf_rate.csv` | 3232 | 3231 | 2018-01-02 | 2026-11-06 |

- `srf_usage.csv` 中 accepted_bn > 0 的天數：API 段 356 天（共 635）、FRED 段 175 天（共 683）。API 段最大值 74.6 bn（2025-12-31），FRED 段最大值 0.203 bn（2023-12-05）。
- `srf_usage.csv` 最新 5 筆：

```
2026-11-02,2,0.002,0.002,0.002,0,0,4
2026-11-03,2,0.005,0.005,0,0,0.005,4
2026-11-04,2,0,0,0,0,0,4
2026-11-05,2,0,0,0,0,0,4
2026-11-06,2,0,0,0,0,0,4
```

- `srf_rate.csv` 最新 5 筆：

```
2026-11-02,4,4
2026-11-03,4,4
2026-11-04,4,4
2026-11-05,4,4
2026-11-06,4,4
```

### verify.py 完整輸出

```
ok   欄位前段為 ['date', 'ops_count', 'submitted_bn', 'accepted_bn', 'accepted_treasury_bn', 'accepted_agency_bn', 'accepted_mbs_bn', 'min_bid_rate']（實際 ['date', 'ops_count', 'submitted_bn', 'accepted_bn', 'accepted_treasury_bn', 'accepted_agency_bn', 'accepted_mbs_bn', 'min_bid_rate']）
ok   主鍵 ['date'] 不重複
ok   依 ['date'] 升冪
ok   srf_usage 起始 <= 2021-08-31（2021-07-28）
ok   srf_usage 最新 >= 2026-11-05（2026-11-06）
ok   accepted_bn 非負且幾乎無空值
ok   日期都是工作日
ok   2026-10-26~11-05 至少 8 個營業日有列（9）
info 近期：
      date  ops_count  submitted_bn  accepted_bn  accepted_treasury_bn  accepted_agency_bn  accepted_mbs_bn  min_bid_rate
2026-10-28        2.0         0.006        0.006                 0.002               0.002            0.002           4.0
2026-10-29        2.0         0.031        0.031                 0.011               0.010            0.010           4.0
2026-10-30        2.0         0.000        0.000                 0.000               0.000            0.000           4.0
2026-11-02        2.0         0.002        0.002                 0.002               0.000            0.000           4.0
2026-11-03        2.0         0.005        0.005                 0.000               0.000            0.005           4.0
2026-11-04        2.0         0.000        0.000                 0.000               0.000            0.000           4.0
2026-11-05        2.0         0.000        0.000                 0.000               0.000            0.000           4.0
2026-11-06        2.0         0.000        0.000                 0.000               0.000            0.000           4.0
info accepted_bn 最大 74.6（2025-12-31）；>0 的天數 531
ok   欄位前段為 ['date', 'target_upper', 'srf_min_bid_rate']（實際 ['date', 'target_upper', 'srf_min_bid_rate']）
ok   主鍵 ['date'] 不重複
ok   依 ['date'] 升冪
ok   srf_rate 起始 <= 2018-01-03（2018-01-02）
ok   srf_rate 最新 >= 2026-11-05（2026-11-06）
ok   target_upper 無空值
PASS nyfed-srf
```

（`ops_count` 顯示 2.0 是 pandas 讀入時把含空值的欄位轉成浮點數，CSV 內為整數。）

### SRF 利率與目標區間上限的關係

- 2024-04-23 ～ 2026-11-06 的 635 個操作日，SRF 最低投標利率（當日最高值）與 `target_upper` **全部相等**（0 筆不同）。
- 2024-04-22 以前沒有逐日的 SRF 最低投標利率來源，`srf_min_bid_rate` 留空。上面的相等關係只適用於有 API 資料的區間。
- 聯準會 2021-07-28 新聞稿及 SRF FAQ 說明 SRF 最低投標利率設定在目標區間上限（僅由搜尋摘要得知，未開啟全文核對）。

### 目標區間上限（`target_upper`）變動日（FRED DFEDTARU）

| 日期 | 上限（%） | | 日期 | 上限（%） |
|---|---|---|---|---|
| 2018-01-02 | 1.50 | | 2022-07-28 | 2.50 |
| 2018-03-22 | 1.75 | | 2022-09-22 | 3.25 |
| 2018-06-14 | 2.00 | | 2022-11-03 | 4.00 |
| 2018-09-27 | 2.25 | | 2022-12-15 | 4.50 |
| 2018-12-20 | 2.50 | | 2023-02-02 | 4.75 |
| 2019-08-01 | 2.25 | | 2023-03-23 | 5.00 |
| 2019-09-19 | 2.00 | | 2023-05-04 | 5.25 |
| 2019-10-31 | 1.75 | | 2023-07-27 | 5.50 |
| 2020-03-04 | 1.25 | | 2024-09-19 | 5.00 |
| 2020-03-16 | 0.25 | | 2024-11-08 | 4.75 |
| 2022-03-17 | 0.50 | | 2024-12-19 | 4.50 |
| 2022-05-05 | 1.00 | | 2025-09-18 | 4.25 |
| 2022-06-16 | 1.75 | | 2025-10-30 | 4.00 |
| | | | 2025-12-11 | 3.75 |
| | | | 2026-09-17 | 4.00 |

API 段 SRF 最低投標利率的變動點（2024-04-23 起）與上表 2024-09-19 之後的變動點一致：5.50（2024-04-23）、5.00（2024-09-19）、4.75（2024-11-08）、4.50（2024-12-19）、4.25（2025-09-18）、4.00（2025-10-30）、3.75（2025-12-11）、4.00（2026-09-17）。

## 缺口與異常

1. **2021-07-28 ～ 2024-04-22（FRED 段）**：`ops_count`、`submitted_bn`、`min_bid_rate` 留空（FRED 沒有這些欄位，NY Fed API 無法取得）。`accepted_treasury_bn`、`accepted_agency_bn`、`accepted_mbs_bn` 來自 FRED 的 Overnight 序列，不含 Term 操作。
2. **Term 操作在 FRED 段的拆解不一致**：FRED 段只有 1 天 `accepted_bn`（FRED `RPTTLD`，含 Term）與擔保品加總不同：2023-03-09，總量 0.059 bn，擔保品加總 0.003 bn（差額約 0.056 bn 屬 Term 操作，FRED 的 Overnight 序列未包含）。
3. **FRED 與 API 的日期口徑**：FRED 有時把操作記在次一營業日（結算日）。重疊期 4 天不一致（見資料來源），其中 2026-10-20 為 Term、2026-02-18 為 Overnight。FRED 段（2024-04-22 以前）因無 API 可對照，同類的日期位移無法逐日核對，可能使單日數字落在相鄰日。
4. **FRED 段精度**：三位小數（十億美元），即百萬美元精度；API 段為美元整數，精確到個位數。
5. **缺的平日（FRED 段 31 天）**：2021-09-06、2021-10-11、2021-11-11、2021-11-25、2021-12-24、2022-01-17、2022-02-21、2022-04-15（Good Friday）、2022-05-30、2022-06-20、2022-07-04、2022-09-05、2022-10-10、2022-11-11、2022-11-24、2022-12-26、2023-01-02、2023-01-16、2023-02-20、2023-04-07（Good Friday）、2023-05-29、2023-06-19、2023-07-04、2023-09-04、2023-10-09、2023-11-23、2023-12-25、2024-01-01、2024-01-15、2024-02-19、2024-03-29（Good Friday）。均為聯邦假日或 Good Friday，FRED 無觀測值，本次不補。
6. **缺的平日（API 段 29 天）**：2024-05-27、2024-06-19、2024-07-04、2024-09-02、2024-10-14、2024-11-11、2024-11-28、2024-12-25、2025-01-01、2025-01-20、2025-02-17、2025-04-18（Good Friday）、2025-05-26、2025-06-19、2025-07-04、2025-09-01、2025-10-13、2025-11-11、2025-11-27、2025-12-25、2026-01-01、2026-01-19、2026-02-16、2026-04-03（Good Friday）、2026-05-25、2026-06-19、2026-07-03、2026-09-07、2026-10-12。均為聯邦假日或 Good Friday，API 無該日操作，本次不補。
7. **非 Results 或非 Repo 操作**：API 窗口內皆為 Results 與 Repo，無排除。
8. **三筆操作無最低投標利率欄位**：`RP 050924 99`（2024-05-09）、`RP 022625 99`（2025-02-26）、`RP 100825 99`（2025-10-08）只有 percentHigh／percentLow 等欄位，無 `minimumBidRate` 或 `percentOfferingRate`，計算 `min_bid_rate` 時不計入。這三天仍有其他有利率的操作，因此當日 `min_bid_rate` 不留空。
9. **SVE 測試操作計入**：窗口內 10 筆 Small Value Exercise，依 SRF 篩選條件（operationType == Repo）計入 `ops_count` 與金額。若只想要正式操作，需另外排除。
10. **切點 2024-04-22**：API 窗口最早日期可能不完整，故該日改用 FRED（見缺口 1）。
11. **API 窗口上限**：`last/N` 的 N 最大 999，窗口會隨時間往前推進（每次抓取窗口起點不同）。若要重建 2024-04 之前的 `ops_count`、`submitted_bn`、`min_bid_rate`，需另找來源（例如 NY Fed 歷史下載檔），本次未找到。
12. **`srf_rate` 的日曆日**：本次採日曆日（含週末與假日），是對「每個日曆營業日一列」的解讀。
