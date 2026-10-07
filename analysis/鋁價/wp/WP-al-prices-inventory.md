---
id: al-prices-inventory
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\鋁價\_ws_b'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium]
priority: 2
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-prices-inventory'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：鋁價、期限結構與庫存的數據來源調研＋實測

## 1. 背景
要研究鋁價（付鵬的「上游傳導」框架＋「LME 低庫存 → 現貨逆價差」論點），先盤點價格、期限結構與庫存數據的可得性。最後會寫一支不進 ETL 的一次性抓取腳本，所以重點是**找到免費、可程式化、有長歷史**的來源，並實測。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
**價格與期限結構**
1. LME 鋁 Cash（現貨）結算價、3M 價、Cash–3M 價差（逆價差／升水），日資料。候選：westmetall.com（Market data → LME Aluminium，有歷史表）、LME 官網、investing.com。
2. IMF 全球鋁價月均（FRED `PALUMUSDM`），另找 FRED 上的氧化鋁、美國鋁 PPI 等相關序列（搜尋 FRED 關鍵字 aluminum / alumina）。
3. SHFE 滬鋁主力或連續合約收盤，日；以及 SHFE 氧化鋁期貨（2023 年上市）。候選：上期所官網日行情、新浪財經期貨 API（`hq.sinajs.cn` / `stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol=AL0`）、東方財富。
4. COMEX 鋁期貨（Yahoo `ALI=F`），以及 Yahoo 上其他鋁相關代號（實測哪些有資料）。
5. 鋁業股票作輔助：AA、CENX、NHY.OL（Hydro）、2600.HK（中鋁）、601600.SS、1378.HK（中國宏橋）、RIO。只需確認 Yahoo 可抓。

**庫存**
6. LME 鋁庫存總量、註銷倉單（cancelled warrants）、在冊倉單（on-warrant），日。候選：westmetall（有 stock 表）、LME 每日庫存報告。
7. LME 庫存分地區／分產地（俄國金屬占比）：LME 每月發布 "Stocks breakdown by origin / brand"，確認網址與格式（xlsx？PDF？是否免費）。
8. SHFE 鋁週庫存（上期所週報，每週五）與 SHFE 氧化鋁倉單。
9. COMEX 鋁庫存（CME 每日倉單報告 `Aluminum_Stocks.xls` 一類的檔案，確認現行網址）。
10. 中國鋁錠社會庫存（SMM／Mysteel，多半付費）：找有無免費轉載或替代（例如新聞每週數字）。

## 3. 特別要確認
- LME 庫存目前大約多少噸（最新日期），近 25 年最低是何時、多少；用你抓到的資料算，不要只抄新聞。
- Cash–3M 價差目前是正（backwardation）還是負（contango），近 3 年的區間。
- 各來源歷史起點，以及單位（公噸、短噸、美元／噸、人民幣／噸）。

## 4. 驗收
- `verify_wp.py al-prices-inventory` 通過：sources.csv ≥15 列、實測 ≥8 列、samples/ ≥5 個 ≥10 列的 CSV（至少要有 LME 價格、LME 庫存、SHFE 鋁、COMEX/Yahoo、FRED 各一）、有 probe_*.py。

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
