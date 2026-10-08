---
id: jp-builders-cost
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_c'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 3
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-builders-cost'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：工務店倒產、建築成本與法規變化的數據來源調研＋實測

## 1. 背景
素材的第三條推力：2025-04 改正建築基準法（4号特例縮小、省エネ基準適合義務化）＋工料雙漲 → 地方小工務店倒閉潮，飯田 GHD 這類標準化大廠受惠。要找能量化「供給側出清」與「成本壓力」的數據。最後會寫一支不進 ETL 的一次性抓取腳本，所以重點是**找到免費、可程式化、有長歷史**的來源，並實測。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
**倒產與業者數**
1. 建設業倒産件数，月與年（東京商工リサーチ TSR「全国企業倒産状況」、帝国データバンク TDB「全国企業倒産集計」）；**木造建築工事業／工務店**的細分（TSR、TDB 都出過「工務店倒産」「住宅関連倒産」專題）。完整資料付費，但新聞稿通常免費——把數字從新聞稿整理成時間序列（至少 2015 起的年數字＋2024–2026 的月數字），每個數字附網址。
2. 建設業許可業者数（國交省，年）、「休廃業・解散」件數（TSR／TDB）。
3. 中小企業倒産的官方序列（中小企業庁／TSR 轉載）作為對照。

**成本**
4. 建設工事費デフレーター（國交省，月，住宅・木造／非木造），官方 Excel。
5. 日銀企業物価指数（PPI）：木材・木製品、製材、合板、セメント、鉄鋼建材（月，日銀時系列）。
6. 農林水産省「木材価格統計」：製材品（スギ正角、ヒノキ正角、輸入材 米マツ／ホワイトウッド集成管柱）、合板，月（ウッドショック 2021 的高峰與現在）。
7. 建設労働：國交省「建設労働需給調査」（8 職種過不足率，月）、公共工事設計労務単価（年）、建設業就業者数（労働力調査，月或年）、建設業有効求人倍率。
8. 建築費指数（建設物価調査会，付費？）——只列，找免費替代。

**法規時間線**
9. 2025-04-01 施行的改正建築基準法與建築物省エネ法：4号特例縮小（新 2 号／新 3 号建築物）、省エネ基準適合義務化、構造計算要件變化；過渡措置與後續修正（若有）。整理成 `samples/policy_timeline.csv`（欄位：`date,event,detail,source_url`，≥10 列，涵蓋 2022 年法案通過到最新）。
10. 2025-04 前後建築確認審查期間延長的官方或業界調查數字（國交省、日本建築行政会議、住宅生産団体連合会「住団連」景況感調查）。

**業界景況**
11. 住宅生産団体連合会「住宅景況感調査」（季，受注棟數・金額指數），國交省「住宅市場動向調査」（年：購入者的世帯年収、自己資金比率、借入金）。

## 3. 特別要確認
- 用你整理出的倒產序列：2024、2025 年建設業倒產件數與年增率，是否為近 10 年最高；工務店（木造建築工事業）的細分數字與出處。
- 建設工事費デフレーター（住宅木造）從 2020 到最新漲了多少 %；木材價格目前相對 2021 高峰與 2019 水準的位置。
- 4号特例縮小後，小工務店需要的額外成本（構造計算外包、審查期間）有沒有具體數字出處；沒有就寫「無法找到可量化出處」。

## 4. 驗收
- `verify_wp.py jp-builders-cost` 通過：sources.csv ≥12 列、實測 ≥6 列、samples/ ≥4 個 ≥10 列的 CSV（其中 ≥2 個最新日期在 2025-06 以後；至少要有：倒產序列、建設工事費デフレーター或 PPI 建材、木材價格、`policy_timeline.csv`）、有 probe_*.py。

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
