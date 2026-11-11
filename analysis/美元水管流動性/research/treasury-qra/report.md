# treasury-qra：財政部季度再融資 TGA 季末現金餘額假設 報告

產出：`qra_tga_targets.csv`（64 列，32 次公告，2019-01-28 ～ 2026-11-02）
抓取程式：`fetch.py`（可重跑，`--start` 指定公告日下限，預設 2019-01-01；`--refresh` 強制重抓）
原始快取：`raw/`（索引頁與各 press release 的 HTML）

## 資料來源

- **索引頁**：`https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/quarterly-refunding-archives/quarterly-refunding-financing-estimates-by-calendar-year`
  依年份列出各季 press release 連結，程式由此取得 2019–2026 共 32 個連結。
- **欄位 `tga_assumption_bn`、`date`、`quarter_end`**：來源為各次 press release「Treasury Announces Marketable Borrowing Estimates」，例如 `https://home.treasury.gov/news/press-releases/sb0675`（2026-11-02）。
  - 取得方式：以 Python `urllib` 直接下載 HTML（User-Agent 為 `Mozilla/5.0 research-fetch`，timeout 30 秒，每次請求間隔 1.5 秒），以正規表示式從正文抓出
    「During the <季> quarter, Treasury expects to borrow/pay down … assuming an end-of-<月> cash balance of $X billion/trillion」。
  - 每次公告有兩句此類敘述（本季、下季），各成一列。`trillion` 乘以 1000 換算為十億美元（例：`$1.000 trillion` → 1000）。
  - `quarter_end` 由「end-of-<月>」與季度年份推得，為該月月底（例：end-of-December 2026 → 2026-12-31）。程式另檢查 end-of-<月> 是否等於季度結束月，本次 32 次公告皆一致。
- **`source_url`**：該次公告的 press release 網址。
- **`date`**：press release 標題下方所列的公告日（所有公告日皆為星期一）。

### 試過但未使用的來源

- `https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding`（主頁）與 `.../most-recent-quarterly-refunding-documents`：列出 2026 Q4 的各項 PDF（TBAC 簡報、拍賣時程、買回時程等），其中沒有本任務所需的季末現金餘額假設；未解析。
- `.../quarterly-refunding-archives`：只是各類歸檔的目錄頁，連到 financing estimates 索引，未直接解析。
- 2015 Q3 等較早年份的 PDF（`/system/files/221/fe-*.pdf`）：不在 2019 起的範圍內，未抓。
- Quarterly Refunding Statement（11/04 的完整聲明）：本任務指定的來源是「Marketable Borrowing Estimates」新聞稿，故未採用 statement。

## 欄位與單位

| 欄位 | 說明 | 單位 | 來源原始名稱 |
|---|---|---|---|
| `date` | 公告日（YYYY-MM-DD），即 press release 標題下的日期 | 日期 | "Treasury Announces Marketable Borrowing Estimates" 下方的日期行 |
| `quarter_end` | 該假設所對應的季末日（YYYY-MM-DD，為月底） | 日期 | 新聞稿句型 "assuming an end-of-<月> cash balance of …" |
| `tga_assumption_bn` | 季末 TGA（財政部現金餘額）假設值 | 十億美元（billion） | "assuming an end-of-<月> cash balance of $X billion" |
| `source_url` | 該次公告的 press release 網址 | — | — |

- 數值保持來源口徑：整數十億美元，無四捨五入；來源原文為 trillion 者（僅 2026-11-02 的 `$1.000 trillion`）換算為 1000。
- 注意：新聞稿中的「cash balance」是財政部公告的季末現金餘額假設（一般指 TGA），本任務只取該假設值，未重新定義。

## 公布時間

- 所有 32 次公告皆為**星期一**發布（程式檢查），集中在每季季初：1 月底／2 月初、4 月底／5 月初、7 月底／8 月初、10 月底／11 月初。
- 例：2026-11-02（週一）發布，同一週三（2026-11-04）8:30 發布 Quarterly Refunding 完整細節（新聞稿內文已載明）。
- **資料所屬日期與公布日期不同**：`date` 是公告日；`quarter_end` 是假設所指的季末日，通常為公告日之後 1–2 個月（本季末）或 4–5 個月（下季末）。這是設計上的差異，不是錯誤。

## 實測結果

- CSV 列數：**64 列**（不含表頭），對應 **32 次公告**，每次 2 列。
- 起訖日：公告日 **2019-01-28 ～ 2026-11-02**；quarter_end 範圍 2019-03-31 ～ 2027-03-31。
- 最新 5 筆（依 date、quarter_end 升冪）：

| date | quarter_end | tga_assumption_bn | source_url |
|---|---|---|---|
| 2026-05-04 | 2026-09-30 | 950 | https://home.treasury.gov/news/press-releases/sb0485 |
| 2026-08-03 | 2026-09-30 | 950 | https://home.treasury.gov/news/press-releases/sb0584 |
| 2026-08-03 | 2026-12-31 | 850 | https://home.treasury.gov/news/press-releases/sb0584 |
| 2026-11-02 | 2026-12-31 | 850 | https://home.treasury.gov/news/press-releases/sb0675 |
| 2026-11-02 | 2027-03-31 | 1000 | https://home.treasury.gov/news/press-releases/sb0675 |

- 年底（2026-12-31）假設：
  - 2026-08-03 公告（前一次）：**850** 十億美元
  - 2026-11-02 公告（最新）：**850** 十億美元
- 以上為來源原文數值，本報告未對影片中的說法作任何比對或驗證。

### verify.py 完整輸出（`verify.py treasury-qra`，結束碼 1）

```
ok   欄位前段為 ['date', 'quarter_end', 'tga_assumption_bn', 'source_url']（實際 ['date', 'quarter_end', 'tga_assumption_bn', 'source_url']）
ok   主鍵 ['date', 'quarter_end'] 不重複
ok   依 ['date', 'quarter_end'] 升冪
ok   起始 <= 2019-01-31（2019-01-28）
ok   最新公告 >= 2026-10-26（2026-11-02）
ok   含 2026-12-31 年底目標
FAIL tga_assumption_bn 在 100~2000（十億美元）
ok   每列都有 source_url
info 近期：
      date quarter_end  tga_assumption_bn                                           source_url
2026-02-02  2026-03-31                850 https://home.treasury.gov/news/press-releases/sb0377
2026-02-02  2026-06-30                900 https://home.treasury.gov/news/press-releases/sb0377
2026-05-04  2026-06-30                900 https://home.treasury.gov/news/press-releases/sb0485
2026-05-04  2026-09-30                950 https://home.treasury.gov/news/press-releases/sb0485
2026-08-03  2026-09-30                950 https://home.treasury.gov/news/press-releases/sb0584
2026-08-03  2026-12-31                850 https://home.treasury.gov/news/press-releases/sb0584
2026-11-02  2026-12-31                850 https://home.treasury.gov/news/press-releases/sb0675
2026-11-02  2027-03-31               1000 https://home.treasury.gov/news/press-releases/sb0675
FAIL treasury-qra: 1 項
```

**驗收未通過**：唯一失敗項為「tga_assumption_bn 在 100~2000」。原因是 2019-04-29 公告（`sm672`）的「end-of-September 2019 cash balance of **$85 billion**」（原文已於 raw/sm672.html 確認）低於 verify.py 設定的下限 100。這是來源公布的數值，不是解析錯誤；依規定不得竄改或刪除數值，verify.py 也不在本任務可修改的範圍內。需要由 verify.py 的維護者決定是否把下限放寬（例如 0），或接受此列。

## 缺口與異常

- **無缺漏公告**：2019–2026 每年 4 次，共 32 次，全部抓到且每次都解析出 2 個假設。程式未回報任何解析警告（`WARN`）或抓取錯誤（`ERR`）。
- **低於 100 的數值**：`2019-04-29, 2019-09-30, 85`（如上所述，為來源原值，verify.py 的範圍檢查因此失敗）。
- **最新一次公告（2026-11-02）抓得到**，不需要寫入抓取失敗原因。
- **口徑**：新聞稿的假設句型在 2019–2026 間一致（"assuming an end-of-<月> cash balance of …"），未見口徑變更；個別公告以 "pay down" 取代 "borrow" 的情況（例：2022-05-02 的 April–June 2022 季）已納入。
- **未涵蓋**：Quarterly Refunding Statement 內文與 TBAC 文件中的 TGA 相關敘述未採用；2019 年以前未抓。
- **商品上市日**：不適用（本任務為事件型政策假設，無商品）。
