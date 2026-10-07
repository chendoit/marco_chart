---
id: al-supply-chain
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\鋁價\_ws_a'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium]
priority: 3
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-supply-chain'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：鋁產業鏈供給（鋁土礦→氧化鋁→原鋁）與貿易流的數據調研＋實測

## 1. 背景
付鵬看鋁用的是「上游傳導」：鋁土礦（幾內亞）→ 氧化鋁 → 電解鋁。他的判斷包括：氧化鋁漲價無法傳導到下游時，中游先崩、上游鋁土礦隨後鬆動（2025-03）；2016–2018 的電解鋁庫存下降背後是氧化鋁擠倉（2025-05）；幾內亞是關鍵（2025-07）。原文在 `C:\code\2025-12-05-MacroMicro-Data\analysis\鋁價\傅鵬\`（唯讀）。這份 WP 盤點供給端與貿易流的數據。

## 2. 要找的序列（每項在 sources.csv 有一列；能實測的都實測）
**產量**
1. IAI（international-aluminium.org）原鋁產量：全球與分區（中國、海灣、北美、西歐、俄羅斯與東歐等），月；以及冶金級氧化鋁產量。確認統計頁能否下載（CSV／xlsx／內嵌 JSON）。
2. 中國國家統計局：原鋁（電解鋁）、氧化鋁、鋁材月產量。先試 DBnomics 的 NBS 資料集（搜尋 aluminium / 鋁），再試 NBS 官方 `data.stats.gov.cn`。
3. USGS Mineral Commodity Summaries：鋁、鋁土礦與氧化鋁的分國產量與儲量（年），找最新年版的資料檔（USGS 有提供 CSV/xlsx data release）。
4. 中國電解鋁產能、運行產能、開工率：多半是 SMM／百川付費，找免費替代（官方公告、新聞）。

**價格（上游）**
5. 氧化鋁價格：澳洲 FOB（API）、中國現貨、SHFE 氧化鋁期貨；免費來源優先，付費的列出即可。
6. 鋁土礦價格：幾內亞到中國 CIF 價；可用海關「進口金額÷進口量」推算均價，說明方法。

**貿易流**
7. 中國海關：鋁土礦進口（分國別：幾內亞、澳洲、印尼等）、氧化鋁進出口、未鍛軋鋁及鋁材進出口，月。試海關總署統計查詢平台（`stats.customs.gov.cn`）、DBnomics、UN Comtrade（`comtradeapi.un.org` 公開端點，HS 2606、2818.20、7601、7604–7608）。
8. 幾內亞鋁土礦出口量與政策（礦權收回、出口限制），找官方或可信統計。
9. 美國原鋁進口（分來源國：加拿大、阿聯等），US Census 國際貿易 API（`api.census.gov/data/timeseries/intltrade/imports/hs`，不需 key 的小量查詢）。

## 3. 特別要確認
- 用你抓到的資料回答：中國原鋁年產量最近 12 個月合計多少，離 4,500 萬噸上限還有多少；中國鋁土礦進口中幾內亞的占比與趨勢。
- 各來源的延遲（資料月份 vs 發布日期）。

## 4. 驗收
- `verify_wp.py al-supply-chain` 通過：sources.csv ≥15 列、實測 ≥6 列、samples/ ≥4 個 ≥10 列的 CSV、有 probe_*.py。

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
