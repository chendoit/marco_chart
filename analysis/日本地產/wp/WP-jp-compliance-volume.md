---
id: jp-compliance-volume
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_f'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-compliance-volume'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---
# 指派文件：建築法規升級下的審查與合規量（建築確認、性能評價、長期優良、BIM）與 ERI 決算的數據來源調研＋實測

## 1. 背景
舊文件主題 T1：2025-04 4号特例縮小＋省エネ義務化，2026-04 非住宅省エネ基準再強化與 BIM 圖面審查上路。舊文件稱 ERI HD（6083）的「法規紅利」12–18 個月見頂、審查員人力是瓶頸。要用官方件數與 ERI 決算檢驗。**已有的不要重做**：`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-housing-starts\samples\building_confirmations_semimonthly.csv`（只涵蓋 2025 年前後）、`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-builders-cost\samples\policy_timeline.csv`（法規時間線，只到 2025）、`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-claims-companies\samples\stock_6083_erihd.csv`（股價）。全貌見 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\WN-2026-10-08-舊文件地產投資主題與數據指標.md` T1（唯讀，可讀）。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
**官方件數**
1. 建築確認件數長歷史（住宅／非住宅、新 2 号／新 3 号建築物、確認申請與適合判定），月或年度，目標回溯到 2015 以前或「建築基準法施行状況調査」的年度數字；國交省「円滑施行連絡会議」或「4号特例縮小に伴う審査状況」最新一期（含 2025-04 至今）。
2. 省エネ適合性判定件數、建築物省エネ法の届出件數（月／年度）。
3. 住宅性能表示：設計住宅性能評価、建設住宅性能評価 交付戶數（住宅性能評価・表示協会，月或年度；有 PDF／Excel 的歷史表）。
4. 長期優良住宅認定件數（新築、增改築；國交省，季或年度），以及 ZEH／BELS 件數（有則列）。
5. BIM：建築 BIM 普及率調查、BIM 圖面審查實施狀況與建築 GX・DX 推進事業的預算／採擇件數（國交省，年度，免費新聞稿數字即可）。
6. 建築確認審查機關的概況：指定確認検査機関數量、確認検査員（審查員）人數趨勢（國交省，年）；一級建築士登錄人數（年，日本建築士会連合会或國交省）。

**ERI HD（6083）決算（決算短信／決算說明資料 PDF，不使用 IR BANK 等二手網站）**
7. 取得 FY2023/5 至最新一期（FY2027/5 Q1，2026-06～08 若已公布，否則 FY2026/5 全年）的：營收、營業利益、營益率、確認檢查件數（若有）、審查員人數、人事費、單價（營收÷件數，自行計算）。寫成 `samples/eri_quarterly.csv`（date 欄用期末月 1 日）。
8. 同時對 NCN（7057）與日本Aqua（1429）各抓最近 8 季營收與營益，存 `samples/ncn_aqua_quarterly.csv`（公司、期間、營收、營益）。若時間不夠，至少做 ERI。

## 3. 特別要確認
- 2025 年度（2025-04～2026-03）建築確認件數、2024 年度、2023 年度，逐一算年增率；2025-03 駆け込み與其後反落的幅度。
- 4号特例縮小後新 2 号建築物（木造兩層）的確認件數佔比，以及審查期間的變化。
- ERI 營收／營益近 3 年趨勢；人事費成長率 vs 營收成長率；審查員人數成長率（舊文件說 +6.6%，營收 +27.8%，營益 +276.5%，請對照決算短信核實）。
- 舊文件預測 ERI 2026/5 期營益 45 億、配息 110 円：核對 2026-07 公布的實績。
- 各來源的歷史起點、單位（件、棟、百萬円）、年度（4 月起）與暦年的差別。

## 4. 驗收
- `verify_wp.py jp-compliance-volume` 通過：sources.csv ≥12 列、實測 ≥6 列、samples/ ≥4 個 ≥10 列的 CSV（含 `samples/eri_quarterly.csv`），其中 ≥2 個最新日期在 2025-06 以後、有 probe_*.py。report 另加 `## 公司數據` 一節（ERI 數字表，附決算短信網址與公告日）。

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
