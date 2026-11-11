# treasury-ops 報告：財政部國債回購（buyback）與標售結算規模

狀態：**完成**。`treasury_buybacks.csv` 與 `auction_settlements.csv` 皆已產出，`verify.py treasury-ops` 結果 PASS。

## 資料來源

### treasury_buybacks.csv

- 來源：Fiscal Data（fiscaldata.treasury.gov）的 **Treasury Securities Buybacks** 公開資料集，不需金鑰。
  - 資料集頁面：https://fiscaldata.treasury.gov/datasets/treasury-securities-buybacks/
  - 使用的端點：`https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/buybacks_operations`
  - 核對用端點（不進 CSV）：`.../v1/accounting/od/buybacks_security_details`
- 取得方式：`fetch.py` 以 `filter=operation_date:gte:2024-05-01&page[size]=10000` 一次取得（單頁，程式會檢查 `total-pages`）。原始回應存於 `raw/fd_buybacks_operations_from_20240501.json`、`raw/fd_buybacks_security_details_from_20240501.json`。
- Fiscal Data 為財政部公開資料集；本次未與 TreasuryDirect buyback 頁面逐筆比對（該頁資料由 JavaScript 呼叫需金鑰的 API 取得）。
- 核對：171 筆 operations 依 (operation_date, 開始時間) 加總的 `total_par_amt_accepted`，與 `buybacks_security_details` 各 CUSIP `par_amt_accepted` 加總完全一致（0 筆差異 > 1 美元）。

試過但未採用的來源：
1. `home.treasury.gov` 的 buyback 頁面：HTTP 404。
2. TreasuryDirect `buy-backs/results-old/`：只有 2000–2001 年的 PDF，不含 2024 年後的資料。
3. TreasuryDirect buyback 頁面內嵌的 `api.fiscal.treasury.gov` 端點：需要 client_id/secret，**未使用**頁面內嵌的憑證。
4. 紐約 Fed Markets API `/api/buybacks/...`：HTTP 400，無此端點。
5. NY Fed 月報 PDF `ODM_Treasury_Buyback_1025.pdf`（已存於 `raw/odm1025.pdf`）：只有累計 sector 彙總，無逐次操作。
6. 第三方 tftc.io：只用來找到 Fiscal Data 資料集的名稱，數字未採用。

### auction_settlements.csv

- 來源：TreasuryDirect 公開 API `https://www.treasurydirect.gov/TA_WS/securities/search`（JSON）。
- 取得方式：`fetch.py`，`dateFieldName=issueDate`，依月份切段（2023-01 至 2026-11，共 47 段），每段 `pagesize=1000`。加 `pagenum` 會讓 API 回傳空陣列，故不分頁；程式在單段達 1000 筆時報錯，本次最大單月約 44 筆。原始回應存於 `raw/td_issue_YYYYMM.json`。
- 篩選：保留 `issueDate` 在 2023-01-01 至 2026-11-06 的紀錄，原始 1683 筆全部在範圍內。
- 去重：以 (cusip, issueDate, securityType, securityTerm) 去重，本次無重複移除。

## 欄位與單位

### treasury_buybacks.csv

| 欄位 | 說明 | 來源欄位 |
|---|---|---|
| date | 操作日（operation date），YYYY-MM-DD | `operation_date` |
| settle_date | 結算日，YYYY-MM-DD | `settlement_date` |
| bucket | 年期區間，照來源（如 `1Mo to 2Y`、`10Y to 20Y`、`1Y to 7.5Y`、`TIPS 1Y to 10Y` 之類的 maturity bucket） | `maturity_bucket` |
| par_submitted_bn | 提交的面額（offered），**十億美元** | `total_par_amt_offered` ÷ 1e9 |
| par_accepted_bn | 接受的面額（accepted），**十億美元**；未舉行或無結果者留空 | `total_par_amt_accepted` ÷ 1e9 |

- 來源另有 `security_type`（Nominal Coupons / TIPS）與 `operation_type`（Liquidity Support / Cash Management），未放入 CSV，因 prompt 欄位未列。需要時可從 `fetch.py` 的原始快取取得。
- 來源 bucket 名稱曾改名：TIPS 由 `1Y to 7.5Y`、`7.5Y to 30Y` 改為 `1Y to 10Y`、`10Y to 30Y`（依 NY Fed 月報註記，自 2025-07-30 起）。CSV 照來源原樣保存，未統一。

### auction_settlements.csv

| 欄位 | 說明 | 來源欄位 |
|---|---|---|
| date | 發行（結算）日，YYYY-MM-DD | `issueDate`（前 10 碼） |
| auction_date | 標售日，YYYY-MM-DD | `competitiveAuctionCloseDate`（前 10 碼）；缺值時用 `noncompetitiveAuctionCloseDate`。本次所有列皆有 competitive 值。API 回應中沒有 `auctionDate` 欄位 |
| security_type | Bill / Note / Bond，照來源 | `securityType` |
| security_term | 期限，照來源（如 `2-Year`、`13-Week`） | `securityTerm` |
| cusip | CUSIP | `cusip` |
| offering_amount_bn | 公布發行金額，**十億美元** | `offeringAmount`（美元）÷ 1e9，保留至小數 3 位，去除末尾 0 |

分類注意：
- `securityType` 沒有 TIPS 與 FRN 值。TIPS 以 `Note`/`Bond` 出現，`inflationProtected=Yes`；FRN 以 `Note`，`floatingRate=Yes`。CSV 依 prompt 保留原始 `securityType`，未拆分。原始紀錄統計：`Note` 且 `floatingRate=Yes` 46 筆，`Note` 且 `inflationProtected=Yes` 38 筆，`Bond` 且 `inflationProtected=Yes` 8 筆。

## 公布時間

- **Buyback**：操作時間為 ET 13:40–14:00（樣本 2025-04-24 操作；2024-08-21 有 13:20 與 13:40 兩個 TIPS 操作，2025-01-09 為 12:40，2026-01-16 為 10:40）。樣本結果 XML 的 `announcementDTM` 為操作當日 11:00 ET，即預告與操作同日。結果檔名以操作開始時間的 GMT 命名（如 `BBR_20250424174000.xml`）。結果實際公布的分鐘數本次未驗證。
- **標售（auction）**：`competitiveAuctionCloseDate` 為標售截止日，結果於標售當日公布。
- **發行（settlement）**：`issueDate` 通常晚於標售數日（例：2026-10-26 標售的 2 年期，發行日 2026-11-02）。CSV 的 `date` 是發行日，`auction_date` 是標售日，兩者不同。

## 實測結果

### treasury_buybacks.csv

- 列數：170
- 起訖日（date）：2024-05-29 至 2026-11-05
- 最新 5 筆：

```
date       settle_date bucket      par_submitted_bn par_accepted_bn
2026-10-15 2026-10-16  10Y to 20Y  40.836           6
2026-10-21 2026-10-22  1Y to 10Y   4.751            0.75
2026-10-27 2026-10-28  20Y to 30Y  10.746           6
2026-11-04 2026-11-05  10Y to 20Y  39.636           6
2026-11-05 2026-11-06  1Mo to 2Y   47.319           4
```

### auction_settlements.csv

- 列數：1683
- 起訖日（date）：2023-01-03 至 2026-11-05
- 最新 5 筆（依 date, cusip, security_term 升冪）：

```
date       auction_date security_type security_term cusip     offering_amount_bn
2026-11-03 2026-10-29   Bill          8-Week        912797WH6   110
2026-11-03 2026-10-28   Bill          17-Week       912797XB8   75
2026-11-05 2026-11-03   Bill          6-Week        912797VH7   100
2026-11-05 2026-11-02   Bill          13-Week       912797VV6   95
2026-11-05 2026-11-02   Bill          26-Week       912797WX1   82
```

### 2026-10 與 2026-11 的 2 年期、5 年期票據（依 prompt 要求列出）

| 標售日 | 發行日 | 期限 | CUSIP | 發行金額（十億美元） | 類型註記 |
|---|---|---|---|---|---|
| 2026-10-22 | 2026-10-30 | 5-Year | 91282CRR4 | 26 | TIPS（inflationProtected=Yes） |
| 2026-10-26 | 2026-11-02 | 2-Year | 91282CRU7 | 69 | 一般 Note |
| 2026-10-27 | 2026-11-02 | 5-Year | 91282CRT0 | 70 | 一般 Note |
| 2026-10-28 | 2026-11-02 | 2-Year | 91282CRS2 | 30 | FRN（floatingRate=Yes） |

2026-09 的參考列：2026-09-22 標售 / 2026-09-30 發行的 2 年期 91282CRP8（69）；2026-09-23 標售 / 2026-09-30 發行的 5 年期 91282CRN3（70）。

2026-11 月內的 2 年期與 5 年期標售：來源中目前沒有資料列（最新發行紀錄為 2026-11-05），未取得，也未推估。

### verify.py treasury-ops 完整輸出

```
ok   欄位前段為 ['date', 'settle_date', 'bucket', 'par_submitted_bn', 'par_accepted_bn']（實際 ['date', 'settle_date', 'bucket', 'par_submitted_bn', 'par_accepted_bn']）
ok   主鍵 ['date', 'bucket'] 不重複
ok   依 ['date', 'bucket'] 升冪
ok   buybacks 起始 <= 2024-06-30（2024-05-29）
ok   buybacks 最新 >= 2026-10-01（2026-11-05）
ok   par_accepted_bn 非負
info buybacks 近期：
      date settle_date     bucket  par_submitted_bn  par_accepted_bn
2026-10-08  2026-10-09 20Y to 30Y            14.886             6.00
2026-10-15  2026-10-16 10Y to 20Y            40.836             6.00
2026-10-21  2026-10-22  1Y to 10Y             4.751             0.75
2026-10-27  2026-10-28 20Y to 30Y            10.746             6.00
2026-11-04  2026-11-05 10Y to 20Y            39.636             6.00
2026-11-05  2026-11-06  1Mo to 2Y            47.319             4.00
ok   欄位前段為 ['date', 'auction_date', 'security_type', 'security_term', 'cusip', 'offering_amount_bn']（實際 ['date', 'auction_date', 'security_type', 'security_term', 'cusip', 'offering_amount_bn']）
ok   主鍵 ['date', 'cusip'] 不重複
ok   依 ['date', 'cusip'] 升冪
ok   auctions 起始 <= 2023-01-31（2023-01-03）
ok   auctions 最新 issue >= 2026-11-03（2026-11-05）
ok   含 Bill/Note/Bond（['Bill', 'Bond', 'Note']）
ok   2-Year Note 至少 30 筆（63）
info auctions 近期：
      date auction_date security_type security_term     cusip  offering_amount_bn
2026-11-03   2026-10-29          Bill        4-Week 912797VZ7               115.0
2026-11-03   2026-10-29          Bill        8-Week 912797WH6               110.0
2026-11-03   2026-10-28          Bill       17-Week 912797XB8                75.0
2026-11-05   2026-11-03          Bill        6-Week 912797VH7               100.0
2026-11-05   2026-11-02          Bill       13-Week 912797VV6                95.0
2026-11-05   2026-11-02          Bill       26-Week 912797WX1                82.0
PASS treasury-ops
```

## 缺口與異常

1. **同鍵排除（buybacks）**：2024-08-21 的 `1Y to 7.5Y`（TIPS）有兩筆操作，13:20 ET 的有成交（accepted 3.51 億美元），13:40 ET 的無成交結果（accepted 為空，offered 5 億美元）。因主鍵為 (date, bucket)，**只保留有成交結果的 13:20 那筆**，13:40 那筆（offered 500,000,000、無 accepted）已排除，程式會列印此項。若需保留，可改以 (date, bucket, 開始時間) 為主鍵。
2. **無成交結果但保留（buybacks）**：2024-07-17 `3Y to 5Y`，offered 20 億美元，accepted 為空，且 Fiscal Data 無 results 檔。保留列，`par_accepted_bn` 留空。此列的 `par_submitted_bn` 是來源提交值，未核實。
3. **bucket 名稱變更（buybacks）**：TIPS 的 bucket 名稱在 2025-07-30 前後改為 `1Y to 10Y`、`10Y to 30Y`（原為 `1Y to 7.5Y`、`7.5Y to 30Y`）。CSV 未統一命名，分析時需注意。
4. **Cash Management 與 Liquidity Support 共用 bucket**：如 `1Mo to 2Y` 同時包含兩種操作類型。CSV 未拆分，`operation_type` 未放入。
5. **auction 主鍵**：(cusip, date) 無重複。cusip 單獨為主鍵不成立（reopening 與 bill 滾動發行），已依任務補充的修正改用 (date, cusip)。
6. **TIPS/FRN 未拆分（auctions）**：見「欄位與單位」。
7. **raw 快取**：`raw/` 內含 `td_issue_YYYYMM.json`（47 個月）、`fd_buybacks_operations_from_20240501.json`、`fd_buybacks_security_details_from_20240501.json`、`odm1025.pdf`、`BBR_20250424174000.xml`（樣本）、`Tentative-Buyback-Schedule.xml`。`handle.txt`、`handle2.txt`、`out.json`、`out2.json` 為任務既有或他方產生的檔案，本次未修改。
