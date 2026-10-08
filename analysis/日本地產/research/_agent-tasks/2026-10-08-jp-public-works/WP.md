---
id: jp-public-works
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_i'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-public-works'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---
# 指派文件：營建供給受限與公共投資先行指標（前払保証、受注、水泥／生コン、就業者）的數據來源調研＋實測

## 1. 背景
舊文件主題 T5：現場人力不足＋加班上限 → 工法往預鑄移動；公共投資（國土強靭化）、能登重建、水泥量縮價升。要找的是**誰受益**的先行與同步指標。**已有的不要重做**：建設工事費デフレーター、PPI 建材、建設勞動需給、倒產在 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-builders-cost\samples\`，著工在 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\research\jp-housing-starts\`。全貌見 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\WN-2026-10-08-舊文件地產投資主題與數據指標.md` T5（唯讀，可讀）。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
1. 公共工事前払金保証事業：東日本建設業保証、西日本建設業保証、北海道建設業信用保証的**請負金額與件數**，月（各公司公開的月次統計；三家合計；目標回溯 10 年以上）。
2. 國交省「建設工事受注動態統計調査」：受注高（公共機關、民間、元請／下請），月，大手 50 社受注（月）；e-Stat 檔案或國交省 Excel。
3. 國交省「建設総合統計」出來高，月。
4. 水泥：セメント協会「セメント需給」國內販售量、生コン：全国生コンクリート工業組合連合会（全生連）出荷量，月；並核實 2023 年國內水泥需求 3,458 萬噸（舊文件）。
5. 建機：日本建設機械工業会 出貨額（國內、輸出），季或月。
6. 勞動：總務省「労働力調査」建設業就業者數與 55 歲以上比率（年）；厚勞省「一般職業紹介状況」職業別有效求人倍率「建設・採掘」「建設躯体工事」（月）；舊文件稱「有效求人倍率超過 6」，核實是哪個職業分類。
7. 公共投資預算：國土強靭化實施中期計畫（2026 年度起）規模、國土交通省公共事業關係費、補正預算；能登復興（石川縣復興基金 1,000 億、災害廢棄物處理進度）。免費新聞稿數字即可，年度。
8. 預鑄與樁：ヤマックス（5285）、山雨（5284）、日本ヒューム（5262）近 8 季營收與營益；樁基礎市場規模（約 2,500 億、ジャパンパイル與三谷セキサン各約 25%）有無業界統計出處。公司數字從決算短信取得，不用二手網站；時間不夠先做三家預鑄。

## 3. 特別要確認
- 用抓到的資料算：前払保証請負金額的近 3 年年增率，及最新 12 個月累計；公共工事受注高 2023–2026 年度的趨勢。
- 水泥國內販售量 2015 至今的年趨勢，是否延續下滑；與生コン出荷量對照。
- 建設業就業者數與年齡結構，核實「55 歲以上超過 36%、29 歲以下約 12%」。
- 各來源的歷史起點、單位（億円、千噸、千㎥）、年度定義。

## 4. 驗收
- `verify_wp.py jp-public-works` 通過：sources.csv ≥12 列、實測 ≥6 列、samples/ ≥5 個 ≥10 列的 CSV，其中 ≥3 個最新日期在 2025-06 以後（至少要有：前払保証、建設受注、水泥或生コン、就業者或求人倍率其中之三）、有 probe_*.py。report 另加 `## 公司數據` 一節（預鑄三家數字表，附決算短信網址與公告日；若來不及，註明未做的原因）。

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
