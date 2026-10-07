## 共通規範（四份鋁業 WP 相同）

- 這是「調研＋實測」任務：上網搜尋，找出可以用程式抓的來源，**實際抓一次**，把結果寫到 `.agent-run/out/`。工作目錄本身是空的工作區，不要在 `.agent-run/` 以外寫任何檔案。
- Python 一律用 `C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe`（已有 requests、pandas、openpyxl、xlrd、curl_cffi、yfinance、bs4、lxml、pypdf、playwright）。**不要 pip install**。執行時設 `PYTHONUTF8=1`。
- 產出（全部 UTF-8）：
  1. `.agent-run/out/report.md`：繁體中文，≥4000 bytes，必須有這些二級標題：`## 結論`（5–8 點：哪些序列可免費日／週／月更新、建議主來源與備援、哪些只能付費）、`## 來源清單`（表格，內容同 sources.csv）、`## 實測`（每個實測來源：請求網址、回應狀態、筆數、起訖日期）、`## 踩坑`（403、反爬、格式陷阱、單位換算）、`## 建議抓法`（給之後寫 `fetch_data.py` 的人：每個序列一行，端點＋解析方式）。
  2. `.agent-run/out/sources.csv`：欄位依序 `category,series,source,url,frequency,history_start,latest_date,access,method,tested,notes`。`access` 只能是 `free` / `registration` / `paid`；`tested` 是 `yes` / `no`；`latest_date` 填實測抓到的最新資料日期（YYYY-MM-DD），沒實測就留空；`method` 寫 csv-api / json-api / html-table / xlsx / pdf / manual。
  3. `.agent-run/out/samples/<序列名>.csv`：實測抓到的資料，第一欄 `date`，每檔 ≥10 列，盡量抓完整歷史。
  4. `.agent-run/out/probe_<主題>.py`：可重跑的抓取腳本，輸出到 `Path(__file__).parent / "samples"`；每個請求 timeout=60；單一來源失敗只印錯誤、不中斷其他來源。
- 付費來源（Fastmarkets、CRU、S&P Platts、Argus、SMM 付費、Bloomberg、LME 官方完整資料）只列不抓，`access=paid`，並在 notes 寫有沒有免費替代。
- 不登入、不註冊、不繞過驗證碼或 Cloudflare；遇到 403 就記錄在踩坑，換來源。
- 數字要有出處：report 裡引用的每個數字附網址與資料日期。
- 已知事實（實測過，直接用）：
  - FRED：`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`，不需 key。
  - Yahoo：`https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>?range=10y&interval=1d`，要帶 `User-Agent: Mozilla/5.0`。
  - CFTC Socrata：`https://publicreporting.cftc.gov/resource/6dca-aqww.json`（Legacy），參數 `cftc_contract_market_code`、`$limit`、`$order`。
  - DBnomics：`https://api.db.nomics.world/v22/series/<provider>/<dataset>/<series>`，有轉載中國國家統計局（NBS）月資料。
  - 大型官網（例如 RBA）曾被 Akamai 擋 403，可以試 `curl_cffi`（`impersonate="chrome"`），還是不行就放棄。
  - 既有寫法參考（唯讀）：`C:\code\2025-12-05-MacroMicro-Data\analysis\澳元\scripts\fetch_data.py`。
- 今天是 2026-10-07。
