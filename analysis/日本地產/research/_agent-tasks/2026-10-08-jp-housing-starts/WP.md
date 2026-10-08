---
id: jp-housing-starts
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_a'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-housing-starts'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：日本住宅著工、建築確認與長期需求的數據來源調研＋實測

## 1. 背景
要研究「工務店退場 → 大型建売商（飯田 GHD、Open House）取得定價權」這個論點（素材見共通規範）。第一步是量：日本新屋市場本身在縮，縮在哪一類（持家＝注文、分譲一戸建＝建売、分譲マンション、貸家），縮在哪個地區，以及 2025-04「4号特例」縮小後建築確認有沒有塞車。最後會寫一支不進 ETL 的一次性抓取腳本，所以重點是**找到免費、可程式化、有長歷史**的來源，並實測。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
**新設住宅著工（國土交通省「建築着工統計調査」）**
1. 新設住宅着工戸数，月，總數＋利用関係別（持家、貸家、給与住宅、分譲住宅；分譲再拆マンション／一戸建て）。原數與季節調整年率都要（若有）。
2. 同上的年（暦年）與年度長歷史，**至少回到 1960 年代**——要能驗證「2025 年約 74 萬戸，62 年來新低，低於 2009 年」。
3. 地區別：首都圏（東京、神奈川、埼玉、千葉）、近畿圏、中部圏、其他；至少要能拆出首都圏的持家／分譲一戸建／分譲マンション。
4. 構造別／工法別：木造比率、プレハブ、ツーバイフォー（看標準化大量生產的占比）。
5. 新設住宅床面積（一戸あたり平均床面積的趨勢：房子變小？）。
候選：e-Stat 建築着工統計（時系列表 xlsx／csv）、國交省「建築着工統計調査報告」月報 PDF／Excel（`https://www.mlit.go.jp/sogoseisaku/jouhouka/sosei_jouhouka_tk4_000002.html` 附近，待驗）、FRED 上的日本住宅著工（搜尋 Japan housing starts / dwellings started，OECD 轉載）。

**建築確認（4号特例縮小的影響）**
6. 建築確認件数（住宅、木造）月或季：國交省「建築確認等の件数」或住宅局統計；也找 2025-04 前後的「確認審査の遅延」相關官方或業界數字（申請件數駆け込み、審查期間）。
7. 民間指定確認検査機関的受託件數（如果有公開彙總；個別公司數字留給 jp-claims-companies）。

**長期需求與存量**
8. 新設住宅着工戸数的長期預測：野村総合研究所（NRI）每年 6 月左右發布的「2040 年度の新設住宅着工戸数」預測（貼文說 61 萬戸），找原始新聞稿網址並記錄各年版本的數字。
9. 世帯数推計（国立社会保障・人口問題研究所）、人口推計（總務省）——只需確認來源與格式。
10. 空き家率（住宅・土地統計調査，5 年一次，2023 年最新）與既存住宅流通量（國交省「既存住宅流通量」估計、REINS 成約件數——REINS 細節可留給 jp-prices-rates，這裡只列來源）。
11. 住宅リフォーム市場規模（住宅リフォーム・紛争処理支援センター估計，免費？）。

## 3. 特別要確認
- 用你抓到的長歷史資料算：2025 暦年新設住宅着工戸数是多少、是否為 1963 年（或更早）以來最低、和 2009 年比；也算 2025 年度（若已公布）與 2026 年 1–8 月的累計年增率。不要只抄新聞。
- 2025-2026 年持家（注文）與分譲一戸建（建売）各自的年增率，哪一類跌得多。
- 2025-03 的駆け込み（4号特例縮小、省エネ基準義務化前）與 2025-04 之後的反落幅度。
- 各來源的歷史起點、單位（戸、㎡）、是否季調。

## 4. 驗收
- `verify_wp.py jp-housing-starts` 通過：sources.csv ≥15 列、實測 ≥8 列、samples/ ≥5 個 ≥10 列的 CSV，其中 ≥3 個最新日期在 2025-06 以後（至少要有：月度利用関係別著工、暦年長歷史著工、首都圏著工、建築確認或木造／工法別其中之一）、有 probe_*.py。

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
