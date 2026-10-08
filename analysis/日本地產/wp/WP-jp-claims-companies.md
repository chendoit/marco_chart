---
id: jp-claims-companies
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\_ws_d'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py jp-claims-companies'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：逐條查證日本地產論點＋飯田 GHD／Open House 等上市公司數據

## 1. 背景
收到一段分析文字（下稱「貼文」，全文見共通規範的背景素材），要逐條查證，並把相關上市公司的業績、估值數據找出原始出處。

## 2. 待查證論點（claim_id 1–15）
1. 2025 年（暦年）日本新設住宅着工約 74 萬戸，62 年來新低，低於 2009 年。
2. 首都圏新築マンション平均價格超過 9,000 萬日圓、逼近 9,500 萬；首都圏建売戸建約 4,500 萬。
3. 日銀政策利率升到 0.75%（查升息時點，以及到 2026-10 為止是否已再調整）。
4. 2025-04 改正建築基準法縮小「4号特例」，木造 2 層建築不再免審構造；小工務店因缺一級建築士須外包，成本上升。
5. 工務店（木造建築工事業）倒產潮：查 2024–2026 年的倒產件數與是否創新高。
6. 飯田 GHD 最新季度：販売棟数減少、平均單價年增約 175 萬至 3,297 萬日圓、毛利率由 14% 升至 16.2%、營業利益率 6.8%、單季純益年增 89.2%。（先確認「最新季度」是哪一季；戶建分讓事業的數字通常在決算説明資料。）
7. 飯田 GHD：PBR 0.57–0.61 倍、自己資本比率 50.8%、預估年配息 92 日圓、殖利率約 4.35%；目標價約 16% 修復空間。
8. Open House：第 3 季累計營業利益年增 18.3%，全年營業利益上修至 1,800 億日圓；マンション事業轉虧為盈、營收翻倍。（Open House 會計年度 9 月底結束，確認是哪個年度。）
9. 販管費率：Open House 約 7.5%、飯田約 13.5%。
10. Open House：ROE 20.1%、PER 6.8–7.0 倍、有利子負債倍率（D/E）133.93%、支付利息 47 億日圓。
11. Open House：配息上調至 200–205 日圓（殖利率約 2.8%）、實施自社株買；分析師平均目標價約 10,466 日圓、隱含逾 40% 上漲空間。
12. Open House 主力商品是都心 6,000–7,000 萬日圓、15–20 坪狹小地的 3 層木造戶建。
13. 2040 年度新設住宅着工預估僅約 61 萬戸（找預測機構與原始發布）。
14. ERI Holdings（6083）因 4 号特例縮小審查業務爆滿；Star Mica（2975）受惠中古翻新需求。查兩家最新決算的確認檢查／翻新業務營收、受託件數變化。
15. Tama Home（1419）、永大産業（7822）、Nichiha（7943）業績因首購預算被壓縮／工務店通路萎縮而惡化：查三家最新決算營收、營業利益年增率與公司自己對原因的說明。

**證據要求**：`source_url` 必須是能直接看到該數字的網址（決算短信／決算説明資料 PDF、有価証券報告書、TDnet 公告、官方統計頁、新聞文章頁），不可只放網域首頁；同一條有多個出處用 `;` 分隔。公司數字優先引用公司自己的決算短信／説明資料 PDF，並在 evidence 寫頁碼或表名。估值類（PBR、PER、殖利率、目標價）會隨股價變動：用你抓到的股價＋公司公告的 BPS／EPS／配息自己重算一次，註明股價日期；分析師目標價找得到公開來源就引用，找不到就標「無法驗證」。推測要標明是推測並給理由。

每條給出 `verdict`（成立／部分成立／不成立／無法驗證）、證據摘要、原始出處網址、資料日期。

## 3. 公司數據（實測）
- Yahoo 抓日股價（≥10 年或上市以來）：`3291.T` 飯田 GHD、`3288.T` Open House、`1419.T` Tama Home、`7822.T` 永大産業、`7943.T` Nichiha、`6083.T` ERI HD、`2975.T` Star Mica HD；對照組 `1928.T` 積水ハウス、`1925.T` 大和ハウス、`1306.T`（TOPIX ETF）。每檔一個 samples CSV。
- 飯田 GHD 與 Open House 的季度（或半期）業績，至少近 5 年：營收、毛利、營業利益、純益、毛利率；飯田另抓戶建分讓的販売棟数與平均單價，Open House 另抓戶建関連事業的引渡棟数與平均單價（若公開）。來源候選：公司 IR 的決算短信／決算説明資料 PDF（用 pypdf 抽表）、TDnet、IR BANK（`irbank.net`）、株探（`kabutan.jp`）。EDINET API v2 要 key → 只列 `registration`。寫成 `samples/iida_quarterly.csv`、`samples/openhouse_quarterly.csv`。
- 用股價與公告數字算目前 PBR、PER、殖利率（兩家），寫進 report。

## 4. 產出（除共通規範外，另加）
- `.agent-run/out/claims.csv`：欄位 `claim_id,claim,verdict,evidence,source_url,as_of`，claim_id 1–15 都要有，verdict 只能是 成立／部分成立／不成立／無法驗證，source_url 不可空、不可只是網域首頁。
- report.md 的 `## 結論` 要寫：貼文整體可信度、哪幾條數字錯或過時、正確的數字。另加 `## 公司數據` 一節，整理成表（公司、指標、數值、期間、出處）。

## 5. 驗收
- `verify_wp.py jp-claims-companies` 通過：claims.csv 1–15 齊全；sources.csv ≥8 列、實測 ≥4；samples/ ≥6 個 ≥10 列 CSV（其中 ≥4 個最新日期在 2025-06 以後）；有 `iida_quarterly.csv`、`openhouse_quarterly.csv`；有 probe_*.py。

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
