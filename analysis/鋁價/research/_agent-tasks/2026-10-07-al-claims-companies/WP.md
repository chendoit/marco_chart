---
id: al-claims-companies
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\鋁價\_ws_c'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium]
priority: 2
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py al-claims-companies'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：逐條查證鋁市場論點＋ Alcoa／Century 財務敏感度

## 1. 背景
收到一段分析文字（下稱「貼文」），要逐條查證，並把美系兩家鋁業公司的敏感度數據找出原始出處。

## 2. 待查證論點（claim_id 1–10）
1. LME 鋁庫存跌至約 24.5 萬噸，本世紀新低；消費天數約 50 天。
2. 英美 2024 年制裁禁止交割新俄鋁；42.5 萬噸缺口將引發劇烈現貨逆價差（backwardation）。
3. 歐洲在能源危機後已減產 50% 原鋁。
4. 歐洲完稅溢價與美國中西部溢價（US Midwest Premium）將同步突破歷史區間（查證目前水準與歷史高點）。
5. 中國 4,500 萬噸產能上限；「鋁水直接合金化」使可出口的實體純鋁錠極為緊缺。
6. Alcoa（AA）垂直整合、100% 控股 AWAC；LME 鋁價每變動 $10/t，淨利變動約 $1,100 萬美元。
7. Century（CENX）滿載出貨 63 萬噸；LME＋溢價每漲 $400/t，EBITDA 增加 $2.52 億美元。
8. Alcoa 是氧化鋁淨賣方，API 上漲擴大精煉毛利；Century 外購氧化鋁，高價侵蝕冶煉價差。
9. Alcoa 水電長約＋Massena 廠電價與 LME 收益共享；Century Sebree 廠曝露於 MISO 現貨尖峰電價。
10. Alcoa 的 ELYSIS 無碳冶煉技術；Century 受惠 IRA 45X 稅收抵免，每噸約 $90 EBITDA。

**證據要求**：`source_url` 必須是能直接看到該數字的網址（新聞文章頁、公司 10-K／投資人簡報 PDF、LME 公告頁），不可只放網域首頁；同一條有多個出處用 `;` 分隔。公司數字優先引用 10-K／簡報 PDF，並在 evidence 寫頁碼或段落。推測（例如「某數字可能是誤植」）要標明是推測並給理由。

每條給出 `verdict`（成立／部分成立／不成立／無法驗證）、證據摘要、原始出處網址、資料日期。數字類一定要找到原始數據（公司 10-K／10-Q／法說簡報、LME、官方統計），新聞只能當輔助。已知線索：Alcoa 原持有 AWAC 60%，2024 年 8 月完成收購 Alumina Ltd 後持有 100%——請查證並寫入。

## 3. 公司數據（實測）
- SEC EDGAR XBRL companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK<10位>.json`，**必須帶 `User-Agent: aluminum-research chunpin.chen@gmail.com`**（SEC 規定要有可識別 UA）。Alcoa CIK 0001675149、Century CIK 0000949157（請自行確認）。
- 抽出近 10 年季度：營收、淨利、EBITDA 若無則用營業利益＋折舊攤銷、出貨量（若在 XBRL 中）。寫成 `samples/aa_quarterly.csv`、`samples/cenx_quarterly.csv`。
- 從最新 10-K／法說簡報找官方敏感度表（Alcoa 年度展望簡報通常有「$100/t LME 變動對 EBITDA 影響」；Century 有 LME／Midwest 溢價敏感度），把原文數字與頁面網址寫進 report。
- Yahoo 抓 AA、CENX 日股價（≥10 年），存 samples。

## 4. 產出（除共通規範外，另加）
- `.agent-run/out/claims.csv`：欄位 `claim_id,claim,verdict,evidence,source_url,as_of`，claim_id 1–10 都要有，verdict 只能是 成立／部分成立／不成立／無法驗證，source_url 不可空。
- report.md 的 `## 結論` 要寫：貼文整體可信度、哪幾條數字錯或過時、正確的數字。另加 `## 公司敏感度` 一節，整理成表（公司、敏感度項目、官方數字、出處、期間）。

## 5. 驗收
- `verify_wp.py al-claims-companies` 通過：claims.csv 1–10 齊全；sources.csv ≥6 列、實測 ≥3；samples/ ≥2 個 ≥10 列 CSV；有 probe_*.py。

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
