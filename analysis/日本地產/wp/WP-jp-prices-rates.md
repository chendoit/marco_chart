---
id: jp-prices-rates
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_b'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-prices-rates'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：日本住宅價格、房貸利率與購買力的數據來源調研＋實測

## 1. 背景
要驗證素材裡的兩條推力：(1) 都市新建マンション價格飆過 9,000 萬日圓，中產轉向都會狹小透天（建売）；(2) 日銀升息推高房貸利率，壓低購買力天花板，買盤向 3,500–4,500 萬的標準化建売沉澱。需要價格（新建／中古、マンション／戸建、首都圏／全國）、利率、所得與負擔能力的數據。最後會寫一支不進 ETL 的一次性抓取腳本，所以重點是**找到免費、可程式化、有長歷史**的來源，並實測。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
**價格**
1. 首都圏新築分譲マンション平均価格、㎡単価、発売戸数、初月契約率，月與年（不動産経済研究所；完整資料庫付費，但每月新聞稿／PDF 有數字，找可程式化抓取的頁面或轉載）。也要東京 23 区。
2. 首都圏建売住宅（新築戸建）平均価格與発売戸数（不動産経済研究所「首都圏建売住宅市場動向」，或其他來源）。
3. 國交省「不動産価格指数（住宅）」，月：住宅総合、住宅地、戸建住宅、マンション（区分所有）；全國與南関東圏／東京都。官方有 Excel。
4. 東日本不動産流通機構（REINS）「月例速報 Market Watch」：首都圏中古マンション成約㎡単価、成約件數；中古戸建成約価格；新築戸建成約価格。
5. 地價：公示地価／都道府県地価調査（年），住宅地全國與東京圏變動率。
6. 東京カンテイ「マンション価格の年収倍率」（看有無免費新聞稿數字）。

**利率與信用**
7. 日銀政策金利（無擔保コール O/N 誘導目標），從 BIS 與日銀兩邊各抓一次對照；整理升息時間線（2024-03 解除負利率起每次決策的日期與水準，到今天為止）。
8. 10 年期 JGB 殖利率，日（財務省 CSV）。
9. 房貸利率：フラット35 最低／最頻金利（住宅金融支援機構，月，有歷史表）、主要銀行変動金利（店頭基準金利、短期プライムレート——日銀有短プラ序列）、日銀「貸出約定平均金利」（新規・住宅ローン若有）。
10. 住宅ローン新規貸出額（住宅金融支援機構「業態別住宅ローンの新規貸出額及び貸出残高」，或日銀 貸出先別貸出金 住宅資金）。
11. 所得：毎月勤労統計 實質賃金指數或家計調査 勤労者世帯實收入（只需確認來源、抓一個序列），用來算價格年収倍率。

## 3. 特別要確認
- 用你抓到的資料算：首都圏新築マンション 2024、2025 年平均價格與 2026 年最新月份；建売戸建同期平均價格；兩者比值。檢查素材說的「逼近 9,500 萬 vs 約 4,500 萬」是哪個口徑、哪個期間。
- 日銀政策利率目前水準（2026-10）與每次調整日期；素材寫 0.75%，查是不是已經過時。
- フラット35 與変動金利從 2024-03 到最新的變化幅度（bp）；用 3,500 萬、4,500 萬、35 年、元利均等，算每月還款在兩個時點的差額（寫在 report）。
- 各來源的歷史起點、單位（万円、円/㎡、%）。

## 4. 驗收
- `verify_wp.py jp-prices-rates` 通過：sources.csv ≥15 列、實測 ≥8 列、samples/ ≥5 個 ≥10 列的 CSV，其中 ≥3 個最新日期在 2025-06 以後（至少要有：不動産価格指数、政策利率、JGB 10Y、フラット35 或其他房貸利率、REINS 或不動産経済研究所其中之一）、有 probe_*.py。report 另加 `## 利率時間線` 一節（表格：日期、政策利率、フラット35、変動金利代表值、出處）。

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
