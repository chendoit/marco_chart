---
id: jp-inheritance-tax
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_h'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-inheritance-tax'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py, .agent-run/out/claims.csv]
---
# 指派文件：大繼承時代與不動產節稅商品（令和 8 年度稅制改正查證＋繼承稅統計）的調研＋實測

## 1. 背景
舊文件主題 T4：遺產稅最高稅率 55%，不動產評價遠低於市價 → 塔樓公寓與不動產小口化商品熱賣。2024-01 國稅廳導入區分所有住宅「評價乖離率」。舊文件（2026-02）結論是「商業不動產 NK 與 TK 眾籌／STO 是避風港」，標的有 A.D. Works（2982）、青山財產（8929）、Intellex（8940）、霞關（3498）。**最大的待確認點**：令和 8 年度稅制改正大綱（2025-12）是否已把「繼承前一段期間內取得的出租用不動產」與「不動產小口化商品」改按通常交易價格評價；若是，舊文件結論過時。這個查證要**先做、且做到有原文出處**。全貌見 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\WN-2026-10-08-舊文件地產投資主題與數據指標.md` T4 與 §4 論點 11、12（唯讀，可讀）。

## 2. 要做的事
**A. 稅制查證（寫在 claims.csv，逐條判定）**
1. 令和 8 年度稅制改正大綱（財務省／自民黨稅調／國稅廳）中，關於相続税・贈与税「不動産の評価」的改正內容：是否包含出租用不動產、不動產特定共同事業（小口化商品）、取得後一定期間內被繼承的不動產；施行日；經過措施。找原文網址（財務省「令和8年度税制改正の大綱」PDF、國稅庁 通達・Q&A）。法案是否已於 2026 年通過成立（所得稅法等修正案），若已通過請註明成立日。
2. 2024-01-01 起「居住用の区分所有財産の評価」（評価乖離率）內容與適用範圍；是否適用於商業用 NK、一棟收益。
3. 對上述商品（A.D. Works ARISTO、青山 Advantage Club、Intellex 資產共享、THE GLOBAL、CREAL、Loadstar OwnersBook 等）最近一期決算說明資料裡，管理層對稅改的說明或銷售額趨勢（用決算短信或說明資料 PDF，不用二手網站）。
4. 如果 1 的答案是「已改」，逐條判斷舊文件的受益／受害邏輯如何改變；若「未改」也要說明依據與日期。

**B. 統計數據**
5. 國稅庁「相続税の申告の実績」：死亡者數、被相続人數、課稅件數、課稅比例、課稅價格、納稅額、遺產構成（土地、家屋、現金等）；年度表，目標回溯到 2010 年或更早。
6. 國稅庁「財産評価基本通達」改正履歷、路線價與倍率表（只確認來源與格式，不必抓全部）。
7. 不動產特定共同事業：國交省「不動産証券化の実態調査」中的出資規模與件數（年）、「不動産特定共同事業の許可件數」。
8. 不動產 STO／眾籌：發行額與件數（ODX、各發行商、日本STO協會或業界統計；找免費新聞稿數字），列來源與已知數字。

## 3. 特別要確認
- 查證的每一條都要在 claims.csv 有 `source_url`（能看到該段文字的文件網址，不能是網域首頁），`verdict` ∈ 成立／部分成立／不成立／無法驗證。
- 算出：最新年度課稅比例與課稅件數；團塊世代（1947–49 年生）進入 75 歲後死亡者數的趨勢（用厚勞省人口動態統計「死亡數」年資料，確認來源後抓一個序列）。
- 各來源的歷史起點、單位（件、億円）、年度定義。

## 4. 驗收
- `verify_wp.py jp-inheritance-tax` 通過：sources.csv ≥8 列、實測 ≥3 列、samples/ ≥2 個 ≥10 列的 CSV（至少有繼承稅統計與死亡數年資料），其中 ≥1 個最新日期在 2025-06 以後、有 probe_*.py。另需 `claims.csv`（欄位 `claim_id,claim,verdict,evidence,source_url`），`claim_id` 1–4 對應上面 A 區 1–4 項，各項 `verdict` 與 `source_url` 齊全。report 另加 `## 稅制結論` 一節（先給結論：舊文件結論是否過時、施行日、影響標的）。

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
