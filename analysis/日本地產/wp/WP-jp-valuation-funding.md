---
id: jp-valuation-funding
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_g'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-valuation-funding'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---
# 指派文件：投資型不動產的估值與資金面（空置率、期待利回り、J-REIT、銀行放款、地價 LOOK）的數據來源調研＋實測

## 1. 背景
舊文件主題 T3：東京資產被重新定價，但 JGB 10Y 已超過 3%，cap rate 與 JGB 的利差、J-REIT P/NAV、私有化潮、銀行對不動產業的放款，是判斷這輪「資本循環」能否延續的關鍵。**已有的不要重做**：JGB 10Y、政策利率、國交省不動産価格指數（住宅）在 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-prices-rates\samples\`。全貌見 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\WN-2026-10-08-舊文件地產投資主題與數據指標.md` T3（唯讀，可讀）。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
1. 三鬼商事「オフィスマーケット」：東京都心5區（千代田、中央、港、新宿、渋谷）平均空置率與平均租金，月（新聞稿或其公開頁／PDF；歷史表若僅付費則找免費轉載或逐月新聞稿）。也找大阪、名古屋。
2. 日本不動産研究所「不動産投資家調査」：期待利回り（丸之內 A 級辦公、住宅、物流、飯店、商業），半年；以及「市街地価格指数」。找每期公開 PDF 或新聞稿的數字，建立歷史表。
3. 東證 REIT 指數與 ETF 1343（NEXT FUNDS 東証REIT）：日線，Yahoo（`1343.T`、`^TREIT` 若有）。再找 JPX／不動產證券化協會（ARES）的 J-REIT 平均分配金殖利率、NAV 倍率（P/NAV）月度資料。
4. 不動產交易額：都市未来総合研究所「不動産取引市場調査」、JLL／MSCI／CBRE 的日本投資額新聞稿（含海外資金比重），半年或季。
5. 國交省「地価LOOK」（主要都市高度利用地地価動向報告）：季，上漲／橫盤／下跌地區數與各區域變動率。
6. 國交省「不動産価格指数（商業用不動産）」：季，店舗、オフィス、マンション・アパート（一棟）；同一系列的 Excel 或 e-Stat 檔案。
7. 日銀「貸出先別貸出金」不動産業（及物品賃貸業）新規貸出與餘額，季；日銀時系列統計 API 或 Excel；也找「不動産業向け貸出」的總量。
8. 訪日客數（JNTO）月，以及観光庁「宿泊旅行統計調査」客房住用率；先確認 `C:\code\2025-12-05-MacroMicro-Data` 的 `analysis/` 與 `data/` 底下是否已有（用 Glob/Grep 看，有的只列來源）。
9. J-REIT 私有化、合併、公開收購事件：產經 REIT（2972，2026 年公開收購）等，整理成 `samples/jreit_events.csv`（date、REIT、事件、價格、結果、來源網址）。至少 8 筆（2023 年以來）。

## 3. 特別要確認
- 用抓到的資料算：丸之內 A 級辦公期待利回り − JGB 10Y 的利差，從 2015 至最新一期，並指出何時轉負（若有）。
- 東京都心5區空置率近 5 年走勢，最新值與是否低於 2%（舊文件說 A 級空置率低於 2%，請區分「全等級平均」與「A 級」口徑）。
- J-REIT 指數近 3 年走勢、最新殖利率與 P/NAV；與同期 JGB 10Y 的差。
- 銀行對不動產業新規貸出近 10 年趨勢，最新一季是否創高。
- 各來源的歷史起點、單位、頻率；半年資料的期間定義（每年 4 月與 10 月調查）。

## 4. 驗收
- `verify_wp.py jp-valuation-funding` 通過：sources.csv ≥15 列、實測 ≥7 列、samples/ ≥5 個 ≥10 列的 CSV，其中 ≥3 個最新日期在 2025-06 以後（至少要有：空置率、期待利回り、REIT 價格或殖利率、銀行放款其中之三）、有 probe_*.py。report 另加 `## 估值利差` 一節（表格：調查期、A 級辦公期待利回り、JGB 10Y、利差、出處）。

## 共通規範（四份日本地產 WP 相同）

- 這是「調研＋實測」任務：上網搜尋，找出可以用程式抓的來源，**實際抓一次**，把結果寫到 `.agent-run/out/`。工作目錄本身是空的工作區，不要在 `.agent-run/` 以外寫任何檔案（暫存檔、`__pycache__` 也一樣；執行 Python 加 `-B`）。
- Python 一律用 `C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe`（已有 requests、pandas、openpyxl、xlrd、curl_cffi、yfinance、bs4、lxml、pypdf、playwright）。**不要 pip install**。執行時設 `PYTHONUTF8=1`。
- 產出（全部 UTF-8）：
  1. `.agent-run/out/report.md`：繁體中文，≥4000 bytes，必須有這些二級標題：`## 結論`（5–8 點：哪些序列可免費日／週／月更新、建議主來源與備援、哪些只能付費）、`## 來源清單`（表格，內容同 sources.csv）、`## 實測`（每個實測來源：請求網址、回應狀態、筆數、起訖日期）、`## 踩坑`（403、反爬、編碼、和暦、年度 vs 暦年、單位換算）、`## 建議抓法`（給之後寫 `fetch_data.py` 的人：每個序列一行，端點＋解析方式）。
  2. `.agent-run/out/sources.csv`：欄位依序 `category,series,source,url,frequency,history_start,latest_date,access,method,tested,notes`。`access` 只能是 `free` / `registration` / `paid`；`tested` 是 `yes` / `no`；`latest_date` 填實測抓到的最新資料日期（YYYY-MM-DD，月資料填該月 1 日），沒實測就留空；`method` 寫 csv-api / json-api / html-table / xlsx / pdf / manual。
  3. `.agent-run/out/samples/<序列名>.csv`：實測抓到的資料，第一欄 `date`（ISO 格式：`YYYY-MM-DD`；月資料用該月 1 日；年度資料用 `YYYY-04-01` 並在欄名或 report 註明是年度），每檔 ≥10 列，盡量抓完整歷史。數值欄名要帶單位（例：`starts_units`、`price_jpy_10k`、`rate_pct`）。
  4. `.agent-run/out/probe_<主題>.py`：可重跑的抓取腳本，輸出到 `Path(__file__).parent / "samples"`；每個請求 timeout=60；單一來源失敗只印錯誤、不中斷其他來源。
- 付費來源（不動産経済研究所的完整資料庫、東京カンテイ有料データ、矢野経済、建設物価調査会、QUICK、日経 NEEDS、Bloomberg、帝国データバンク／東京商工リサーチ的有料レポート）只列不抓，`access=paid`，並在 notes 寫有沒有免費替代（例如新聞稿、プレスリリース PDF 裡的數字）。
- 不登入、不註冊、不繞過驗證碼或 Cloudflare；遇到 403 就記錄在踩坑，換來源。需要 appId／API key 的（e-Stat API、EDINET API v2、J-Quants）標 `registration`，不要申請，改找同一份資料的免費檔案下載。
- 數字要有出處：report 裡引用的每個數字附網址與資料日期。
- 已知事實（直接用；標「待驗」的請實測確認）：
  - FRED：`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`，不需 key。
  - Yahoo：`https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?range=10y&interval=1d`，要帶 `User-Agent: Mozilla/5.0`；東證代號加 `.T`（例：`3291.T`）。
  - BIS 政策利率：`https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.JP?format=csv`。
  - 財務省 JGB 利回り（待驗）：`https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv`（歷史）＋ `.../interest_rate/jgbcm.csv`（當月），Shift_JIS，日期是和暦（例：`R7.4.1`）。
  - e-Stat 檔案下載不需 key：統計表頁面上的 Excel／CSV 連結形如 `https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=0`（fileKind 0=Excel，1=CSV，待驗）。e-Stat API 需要 appId → `registration`。
  - 日銀時系列統計データ検索サイト：`https://www.stat-search.boj.or.jp/`；2026 年起可能有官方 API（待驗，搜尋「日本銀行 時系列統計データ API」）。
  - 日本政府與業界統計常見陷阱：Shift_JIS / cp932 編碼、和暦（昭和／平成／令和）、年度（4 月–翌年 3 月）與暦年混用、「戸」與「棟」不同、「万円」單位、季節調整年率（年率換算値）與原數混用。
  - 大型官網偶爾擋 403，可以試 `curl_cffi`（`impersonate="chrome"`），還是不行就放棄。
  - 既有寫法參考（唯讀）：`C:\code\2025-12-05-MacroMicro-Data\analysis\澳元\scripts\fetch_data.py`、`C:\code\2025-12-05-MacroMicro-Data\analysis\鋁價\scripts\fetch_data.py`。
- 背景素材（唯讀，可讀）：`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\素材\2026-10-08 工務店退場與飯田・Open House 定價權（貼文）.md`。
- 今天是 2026-10-08。
