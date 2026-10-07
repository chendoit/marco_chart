---
id: al-premium-policy
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\鋁價\_ws_b'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium]
priority: 3
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-premium-policy'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：鋁區域溢價、政策時間線、部位與能源成本的數據調研＋實測

## 1. 背景
有一種觀點認為：英美 2024 年制裁禁止新俄鋁在 LME 交割、歐洲減產、美國 232 關稅，會讓歐洲完稅溢價與美國中西部溢價（US Midwest Premium）突破歷史區間；冶煉廠的利潤又取決於電價。這份 WP 盤點「溢價、政策、部位、能源」的數據。

## 2. 要找的序列（每項在 sources.csv 有一列；能實測的都實測）
**區域溢價**
1. 美國中西部溢價：CME 期貨 Aluminum MW US Transaction Premium Platts（代號 AUP / MWP）結算價。試 CME 公開結算頁、CME FTP（`ftp.cmegroup.com` 或 `https://www.cmegroup.com/ftp/`）、Yahoo 代號、新聞。Platts 現貨報價本身付費。
2. 歐洲鹿特丹完稅溢價（Aluminium European Duty-Paid premium，CME 代號 EDP）與未完稅溢價。
3. 日本 MJP 季度溢價（Main Japanese Ports）：找新聞歷史（Reuters、Mining.com、Alcircle），整理成季資料樣本。
4. CME 鋁期貨與溢價期貨的成交量、未平倉量（若可得）。

**政策時間線**（做成 `samples/policy_timeline.csv`：`date,region,event,detail,source_url`，至少 15 列，2018 年起）
5. 美國 232 關稅：2018 年 10%、2025 年 2 月恢復 25%、2025 年 6 月提高到 50%，以及豁免變化（加拿大等）——逐條查證日期。
6. 俄鋁制裁：2018 Rusal 制裁與解除、2024-04-12 英美禁止新俄鋁在 LME／CME 交割、2025 年起的後續（歐盟第 16 輪制裁對俄鋁進口的分階段禁令）。
7. 歐盟 CBAM（2026 年起正式收費）、中國 2024-12 取消鋁材出口退稅、中國電解鋁 4,500 萬噸產能上限的來源文件、幾內亞礦權收回事件（2025）。
8. 歐洲冶煉廠減產／復產（2021–2026），盡量量化（萬噸／年）。

**部位**
9. LME Commitments of Traders Report（COTR）鋁：確認網址、格式、是否免費。
10. CFTC COMEX 鋁：用 Socrata 查 commodity_name 含 ALUMINUM 的合約代碼，實測抓一次。

**能源成本**
11. 美國 MISO 現貨電價（Indiana / Kentucky 附近節點；Sebree 冶煉廠在 Kentucky）：MISO 公開市場報告或 EIA 批發電價。
12. 歐洲：TTF 天然氣（Yahoo `TTF=F`）、德國電價（找免費來源，例如 Energy-Charts、Ember）。
13. 中國：動力煤價格（找免費來源）。

## 3. 驗收
- `verify_wp.py al-premium-policy` 通過：sources.csv ≥15 列、實測 ≥6 列、samples/ ≥4 個 ≥10 列的 CSV（其中一個必須是 policy_timeline.csv）、有 probe_*.py。

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
