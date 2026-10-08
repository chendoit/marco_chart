---
id: jp-used-vs-new
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_e'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-used-vs-new'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---
# 指派文件：首都圏中古與新築住宅供需對照（REINS、既存住宅販売量指数、不動産経済研究所月度）的數據來源調研＋實測

## 1. 背景
舊文件主題 T2：新築買不起 → 需求溢出到中古與翻新。要驗證「中古成約件數連年超過新築發售戶數」「新舊價差」「中古在庫是否開始堆積」。**已有的不要重做**：`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-prices-rates\samples\`（國交省不動産価格指数、REINS Market Watch 只有約 13 個月、不動産経済研究所只有手抄年度數字）、`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-housing-starts\`（著工）。本 WP 專補缺口：**長歷史、月度、可程式化**。背景與全貌見 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\WN-2026-10-08-舊文件地產投資主題與數據指標.md` 的 T2 與 §3 表格（唯讀，可讀）。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
1. 東日本不動産流通機構（REINS）：首都圏中古マンション／中古戸建／新築戸建的成約件數、成約㎡單價（或成約價格）、**在庫件數**、新規登録件數，月。月例速報 Market Watch 的 PDF 逐月存檔、年報、Market Watch 歷史資料頁，目標回溯到 2010 年以前或至少 2015。也看近畿圏、中部圏有沒有同格式資料。
2. 國交省「既存住宅販売量指数」（試験運用），月，戸建與マンション，全國與地區。
3. 不動産経済研究所：首都圏新築分譲マンション月度（發售戶數、平均價格、㎡單價、初月契約率、在庫戶數），免費新聞稿 PDF 裡的數字；要的是**月度時間序列**，不是年度。同時找首都圏建売住宅月度（若有）。完整資料庫付費則列 paid 並註明免費替代。
4. 東京カンテイ：中古マンション 70㎡ 價格（都區部、首都圏、近畿圏）月度新聞稿，看有沒有可抓的歷史表；以及新築與中古的價差新聞稿。
5. 國交省「不動産価格指数」中古マンション／戸建的子序列確認（已有主序列，只確認有無地區別、有無東京都區部）。
6. 中古流通比重的長期數字：住宅・土地統計調査「中古住宅流通シェア」、國交省「既存住宅流通量」推計（年）。
7. 買取再販：矢野經濟研究所新聞稿的戶數與市場規模、住宅リフォーム・紛争処理支援センター的リフォーム市場規模（年），免費新聞稿數字即可。

## 3. 特別要確認
- 用抓到的資料算：首都圏中古マンション成約件數 vs 新築發售戶數，歷年（至少 2015 至今）逐年比值；說明「連續多年中古超過新築」是哪一年起、口徑為何（REINS 成約件數 vs 不動産経済研究所發售戶數，一個是成交、一個是供給）。
- 中古／新築 ㎡單價比值（同一年度，首都圏）；最新月份的數字。
- REINS 中古マンション在庫件數與「在庫月數」（在庫 ÷ 月成約）的趨勢：2024 至今是否上升。
- 各來源的歷史起點、單位（件、戶、万円、万円/㎡）、是否為東日本レインズ管轄的「首都圏」口徑（東京、神奈川、埼玉、千葉）。

## 4. 驗收
- `verify_wp.py jp-used-vs-new` 通過：sources.csv ≥12 列、實測 ≥6 列、samples/ ≥4 個 ≥10 列的 CSV，其中 ≥2 個最新日期在 2025-06 以後（至少要有：REINS 中古成約或在庫月度長歷史、不動産経済研究所新築月度其中之一）、有 probe_*.py。report 另加 `## 中古與新築對照` 一節（表格：年度、中古成約件數、新築發售戶數、比值、中古／新築單價比、出處）。

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
