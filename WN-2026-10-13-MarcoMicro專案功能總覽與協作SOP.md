# WN-2026-10-13 專案功能總覽與協作 SOP

> 目的：讓其他 agent（或新加入的人）在不問作者的前提下，理解本專案在做什麼、程式與文件放在哪裡、以及如何依既有流程「規劃 → 派工 → 驗收 → 總結」協作寫出 WN。
> 讀者：後續接手的 agent。讀完本文後，先看 §7 再動手。
> 範圍：以 2026-10-13 的 repo 狀態為準（分支 `main`）。文中標註「外部」的工具或路徑不在本 repo 內，無法在此驗證。

---

## 1. 一句話定位

本 repo 是 **MacroMicro 風格的總經與市場數據平台 + 研究工作區**，包含三件事：

1. **資料抓取（ETL-ish）**：根目錄數十支 `get_*.py` 從 FRED、CFTC、CBOE、NY Fed、Yahoo、TradingView、日本官方統計等來源抓數據，存成 `data/*.pkl`。
2. **儀表板**：`flask_highcharts/` 以 Flask + Highcharts 把 `data/` 內的序列畫成互動圖表，附每張圖的文字解讀。
3. **研究案例**：`analysis/` 下按主題（澳元、紐元、匯率、石油、鋁價、日本地產…）存放分析文章、一次性抓取腳本、CSV 資料與 WN 工作筆記；研究工作可以拆成 WP 派給其他 agent 執行。

---

## 2. 功能清單

### 2.1 資料抓取層（根目錄）

| 入口 | 來源 | 產出 |
|---|---|---|
| `get_all_series_data.py` | **每日總表入口**：依序呼叫下列所有 fetcher，失敗項目寫入 `logs/error_history.json`，連續失敗會透過 LINE 通知；之後執行 NFCI 翻轉信號與 MacroMicro 部落格新文章檢查 | `data/*.pkl`（每個 series 一檔） |
| `get_fred_csv.py` | FRED CSV（免 key） | `fred_*` 系列 |
| `get_fed_series.py` | FRED API（`FED_API_KEY`）、NY Fed rates API | `fed_*`、SOFR/BGCR/TGCR、利率與流動性 |
| `get_m_square_chart_api.py` | M² chart API（curl_cffi） | M² 圖表序列（取代舊版 Playwright 方案） |
| `get_m_square_*.py` | M²（舊版 Playwright + Google OAuth） | 多數已停用，見 §5 |
| `get_yfinance_series.py`、`get_yahoo_series.py` | Yahoo Finance | ETF close/volume、裂解價差、MOVE 等 |
| `get_cboe_index.py`、`get_cboe_pcr.py` | CBOE CDN JSON | VIX/VVIX/SPX OHLC、OVX/GVZ、Put/Call ratio |
| `get_ctfc_series.py`、`get_cftc_crude_mm.py` | CFTC COT（pycot-reports、Socrata） | 各幣別、原油 managed money 淨部位 |
| `get_cme_daily_volume.py`、`get_cme_fedwatch.py` | CME 日成交量、FedWatch 結算機率 | 期貨量、降息機率（FedWatch 為備援） |
| `get_gex_series.py` | 本機 SQLite（gamma exposure） | GEX 序列 |
| `get_official_xlsx.py` | 各國官方 Excel（ISM 等） | 10 條官方序列 |
| `get_ism_pmi.py`、`get_conference_board.py` | ISM PMI、Conference Board LEI/CEI | PMI、LEI、CEI |
| `get_financial_stress.py`、`get_ofr_fsi_global.py` | OFR FSI、NFCI 相關 | 金融壓力指數 |
| `get_cds_series.py` | 信用違約交換相關 | CDS 序列（9 國） |
| `get_nyfed_termpremium.py` | NY Fed ACM 期限溢價 | ACM 10Y/5Y/2Y |
| `get_etf_csv.py` | ProShares NAV CSV | ETF 資金流 |
| `get_fiscal_data.py`、`get_eia_series.py` | 財政部 TGA、EIA | TGA、能源序列 |
| `get_jp_yield.py` | 日本 10Y、美日利差 | JP 利率序列 |
| `get_tradingview_series.py` | TradingView（備援來源） | 替補序列 |
| `get_aud_nzd_series.py` | 澳元/紐元 CFTC、匯率 | 澳元、紐元全批資料（TWSE 月報未發布時往前遞補） |
| `calc_pctrank.py` | 讀取 `data/`，計算百分位排名 | 儀表板用的 pctrank 結果 |
| `line_notify.py`、`gmail_smtp.py`、`notify_macromicro_blog.py` | LINE Notify、Gmail SMTP、MacroMicro 部落格 | 通知 |
| `macromicro_login.py`、`google_session/`、`*_storage_state.json` | 登入與 session（僅 M² / Google 相關） | 登入狀態 |

**共同規則**（從現有程式與 commit 歸納）：

- 每支 fetcher 寫入 `data/<prefix>_*.pkl`，檔名與格式是下游儀表板的契約，**不可隨意改名**。
- 單一來源失敗只記錄、不中斷其他來源（`get_all_series_data.run_tasks` 的設計）。
- 日誌使用 `loguru`（`log_config.py` / `logger.py`）。
- 排程與程式都在本機 Windows 上跑，路徑以 `C:\code\2025-12-05-MacroMicro-Data` 為準。

### 2.2 儀表板（`flask_highcharts/`）

- **進入點**：`main.py`。開發 port **6002**（`FLASK_ENV=development`，自動跳過 Turnstile），正式 port **5002**（`production`，啟用 Cloudflare Turnstile）。啟停用 `restart_dev.bat` / `stop_dev.bat`，正式版用 `*_prod.bat`。
- **路由群組**：`app/routes/*.py` 每個檔案是一個 group（約 25 個，例如 `原油.py`、`流動性.py`、`McElligott*.py`、`CFTC.py`、`VIXM.py`、`FED 流動性.py`）。啟動時 `main.py` 會自動載入全部 group。
- **圖表定義**：各 group 使用 `app/utils/highcharts_utils.py` 的 `ChartModule`，宣告 `title`、`ids`（series id 清單）、`axis`、`summary`（解讀文字），`pctrank_id` 可選。
- **資料來源**：`data/` 內的 `.pkl`，依 mtime 偵測變更（60 秒一次），變動時清快取。
- **API**：`/api/chart/<group>`，回傳該 group 所有圖表資料與設定。
- **前端**：`templates/` + `static/js/`（Highstock 與 navigator）。
- **已知限制**：`load_series_data` 寫死 `../data`，搬移目錄會壞（見 PLAN §1.2 之後的建議）。

### 2.3 研究工作區（`analysis/`）

目前主題（追蹤檔案數以 `git ls-files` 為準）：

| 主題資料夾 | 狀態 | 內容概要 |
|---|---|---|
| `日本地產/` | 最新、最大（~139 檔） | 日本住宅市場（工務店退場、飯田 GHD / Open House 定價權）。含 `scripts/`、`data/`、`research/`、`wp/`、`WN-2026-10-08-*` 三份 WN |
| `鋁價/` | 完整（~77 檔） | 鋁業供需與價格。含 `scripts/fetch_data.py`、`wp/`、`research/`、兩份 WN（10-07） |
| `石油/` | 進行中（~11 檔） | 冬季能源極端路徑推演；有 `資料清單.md`、`scripts/`、`data/` |
| `澳元/` | 完成 | CFTC 持倉系列文章、`aud_case.html`、`scripts/`、`lib/` |
| `紐元/` | 完成（~18 檔） | 同澳元結構 |
| `匯率/` | 進行中（~24 檔） | 匯率與 CFTC |
| `愛謝客/` | 空（僅資料夾） | 尚無追蹤檔 |
| `日本地產舊文件/` | 未追蹤 | 舊版地產文件，已被 `日本地產/` 的 WN-10-08 盤點吸收 |

每個主題的常見結構：

```
analysis/<主題>/
  WN-<日期>-<主題>數據收集規劃.md      # 規劃 WN（先做）
  WN-<日期>-<主題>...研究總結.md        # 總結 WN（收件後）
  scripts/fetch_data.py               # 一次性抓取，輸出 data/*.csv（不進 ETL）
  data/*.csv
  wp/                                 # 工作包（WP-*.md、verify_wp.py；部分主題另有 _common.md、_body/）
  research/<task-id>/                 # 收件的 report.md、sources.csv、samples/、probe_*.py
  research/_agent-tasks/<task-id>/    # 歸檔的 WP.md 與 DELIVERY.md
  素材/                               # 外部貼文、原始素材（未經查證）
```

---

## 3. 資料流（一張圖）

```
外部來源（FRED / CFTC / CBOE / Yahoo / 官方統計…）
   │
   ├─ 根目錄 get_*.py ──(get_all_series_data.py 每日排程)──► data/*.pkl ──► calc_pctrank ──► flask_highcharts
   │                                                                   │                       │
   │                                                                   └─ 失敗 → logs/error_history.json → LINE
   │
   └─ analysis/<主題>/scripts/fetch_data.py ──► analysis/<主題>/data/*.csv ──► 圖表 / case html ──► WN 結論
```

**注意**：兩條線是分開的。`analysis/` 的 CSV 不會自動進入儀表板；要進入儀表板，必須走根目錄的 fetcher 與 `data/*.pkl`。

---

## 4. 文件體系：WN / WP / DELIVERY / verify

這是本 repo 的協作語言，請先理解：

| 類型 | 命名 | 用途 | 誰寫 |
|---|---|---|---|
| **WN**（工作筆記，本 SOP 採此解讀，repo 內未見正式定義） | `WN-YYYY-MM-DD-<主題>.md` | 規劃、盤點、決策、總結。WN 負責「要什麼、為什麼、結論是什麼」 | 主 agent 或人 |
| **PLAN** | `PLAN-YYYY-MM-DD-<主題>.md` | 較大的工程改造計畫，含波次、Gate（需人決策的點） | 主 agent |
| **WP**（工作包 / 指派文件） | `wp/WP-<id>.md` 或 `research/_agent-tasks/<日期>-<id>/WP.md` | 交給外部 agent 執行的任務書：背景、要找的序列、驗收條件、共通規範 | 主 agent |
| **DELIVERY**（交件） | `research/_agent-tasks/<日期>-<id>/DELIVERY.md` | 執行 agent 交件的摘要、產出檔案 sha256、驗收結果 | 派工系統產生 |
| **verify_wp.py** | `wp/verify_wp.py <id>` | 機械驗收：檢查標題、欄位、列數、日期新舊、claims 出處 | 人寫一次，之後共用 |

### 4.1 WP frontmatter（必填欄位）

```yaml
---
id: jp-used-vs-new                 # 任務 id，verify_wp.py 的 SPEC 用它當 key
workdir: '...\_ws_e'               # 執行 agent 的工作區（readonly 模式下只能寫這裡）
mode: readonly                     # readonly：不得改主 repo
agent: agy:gemini-3.8-flash-high   # 執行模型（外部派工系統）
fallback: [agy:gemini-3.8-flash-medium, agy:claude-sonnet-4-6]
priority: 2
timeout_min: 50
max_attempts: 5
verify: '<venv python> verify_wp.py <id>'
outputs: [.agent-run/out/report.md, .agent-run/out/sources.csv, ...]
---
```

WP 本文的固定章節：`1. 背景`、`2. 要找的序列`、`3. 特別要確認`、`4. 驗收`、`共通規範`（已知事實與陷阱）。

### 4.2 驗收標準（以 `日本地產/wp/verify_wp.py` 為例）

- `report.md` ≥ 4000 bytes，含必備二級標題（結論、來源清單、實測、踩坑、建議抓法 + 各 WP 自訂）。
- `sources.csv` 欄位固定：`category,series,source,url,frequency,history_start,latest_date,access,method,tested,notes`；`access` ∈ {free, registration, paid}。
- `samples/*.csv` 第一欄必為 `date`，≥10 列，且 ≥2 個（視 WP）的最新日期 ≥ 2025-06，防止只抓到舊資料。
- `probe_*.py` 存在（可重跑）。
- 有 claims 的 WP：`claims.csv` 的 `verdict` ∈ {成立, 部分成立, 不成立, 無法驗證}，且 `source_url` 不能是網域首頁。

---

## 5. 已知狀態與未完成事項（2026-10-13）

- **M² 資料源**：Playwright / OAuth 方案已壞（PLAN-2026-09-15 記錄；已有多個 commit 改接 FRED、Yahoo、CBOE、curl_cffi chart API）。`get_m_square_series` 與 `get_m_square_etf` 在 `get_all_series_data.py` 已註解停用。仍需登入的剩餘依賴見 `WN-2026-09-28-M2仍需登入的剩餘依賴盤點.md`。
- **ETL 重構**：`PLAN-2026-09-15-etl-refactor-m2-replacement.md` 規劃建立 `etl/` 框架（統一設定、job registry、錯誤回報）。**repo 內目前沒有 `etl/` 目錄**，計畫仍未執行。接手前先確認是否已在別處完成。
- **派工系統**：`taskq`（accept / reject）與 `agy:` 模型是**外部工具**，不在本 repo。repo 內只留下 WP、DELIVERY 與 verify 腳本。
- **`analysis/愛謝客/`** 無追蹤檔；**`analysis/日本地產舊文件/`** 未追蹤。

---

## 6. 安全與禁忌（所有 agent 必讀）

1. **不要讀出、印出、commit 下列檔案的內容**：`.env`、`google_storage_state.json`、`macromicro_storage_state.json`、`*_cookies*`、任何含 key/密碼的檔案。需要金鑰時請使用者自行加入 `.env`。
2. **不登入、不註冊、不繞過驗證碼或 Cloudflare**。遇到 403 就記錄在 WN「踩坑」，換來源。
3. **不要 `pip install`**。Python 一律用 `C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe`，執行時設 `PYTHONUTF8=1`（Windows 中日文輸出需要）。
4. **不要在正式排程的工作目錄直接開發**：`get_all_series_data.py` 每天 08:00 與 18:00 會跑，改動前先評估影響（PLAN §0.3 建議用 git worktree）。
5. **不 push、不改 remote**，除非使用者明確要求。
6. **Git commit message 用繁體中文**（`.cursor/rules/commit-message-chinese.mdc`）。若使用 Claude 產生 commit，依使用者設定加上 `Co-Authored-By` 行。
7. 啟動 Flask dev 前先執行 `stop_dev.bat`，避免舊進程佔住 6002（`.cursor/rules/flask-port-cleanup.mdc`）。
8. **編輯前先讀**：不要覆寫其他 agent 或使用者正在進行的檔案；`analysis/` 下已有的 WN 是歷史紀錄，修正時請新增 WN 或在原檔註明，不要悄悄改寫結論。

---

## 7. 協作 SOP：從主題到 WN 結論

以下流程是 `日本地產`、`鋁價` 實際跑過的順序，其他主題照做即可。

### 步驟 0：建立主題資料夾與規劃 WN

1. 在 `analysis/<主題>/` 建資料夾，子目錄至少含 `scripts/`、`data/`、`wp/`、`research/`。
2. 寫 `WN-<今天>-<主題>數據收集規劃.md`，固定包含：
   - **目的**：要驗證什麼論點，論點來源（素材或使用者問題）。
   - **論點表**：每條論點對應「要驗證什麼 → 需要的數據」。
   - **數據地圖**：類別、序列、頻率、候選來源、對應 WP。
   - **WP 分工表**：每個 WP 的 id、內容、agent、工作區。
   - **待確認事項**：素材中沒有日期或來源的地方，先標成「待 WP 確認」。

### 步驟 1：拆 WP

- 一份 WP 聚焦一組相關序列（通常 4 份以內，本主題 4 份 WP 可並行）。
- 每份 WP 的「要找的序列」寫成清單，每項都必須能在 `sources.csv` 找到一列。
- 寫清楚**驗收數字**（列數、樣本數、最新日期門檻），並在 `verify_wp.py` 的 `SPEC` 加入該 id。
- 共通規範（Python 路徑、輸出格式、禁止事項、已知事實）抽到 `wp/_common.md` 或在每份 WP 尾段重複。
- 「已知事實」只寫實測過的，標「待驗」的要求執行者實測。

### 步驟 2：派工

- 用 `taskq` 派給執行 agent（外部工具）；`readonly` 模式，只在 `workdir` 寫入。
- 執行 agent 完成後會自動跑 `verify`；失敗則依 `fallback` 與 `max_attempts` 重試。
- 若派工系統不可用，可在本機手動執行 WP，但產出仍須放到 `.agent-run/out/` 的同樣結構，才能用 `verify_wp.py` 驗收。

### 步驟 3：收件

1. `taskq accept <id>`（或人工確認）。產出會放到 `research/<id>/`，WP 與 DELIVERY 歸檔到 `research/_agent-tasks/`。
2. 重新執行 `verify_wp.py <id>`，確認 PASS。**不要只看 DELIVERY 的「pass」字樣**，要看實際檔案。
3. 抽查：
   - 隨機打開 `samples/*.csv`，檢查日期欄與單位（例：`starts_units`、`price_jpy_10k`）。
   - 打開 `report.md` 的「踩坑」與「建議抓法」，這是下一步寫 `fetch_data.py` 的依據。
   - 若 WP 有 claims，抽 3 條打開 `source_url` 核對數字。

### 步驟 4：寫 `scripts/fetch_data.py`

- 依 `sources.csv` 中 `tested=yes` 的主來源，寫一次性腳本，輸出到 `analysis/<主題>/data/*.csv`。
- 腳本需可重跑、單一來源失敗不中斷、印出每個來源的筆數與最新日期。
- 參考既有寫法：`analysis/澳元/scripts/fetch_data.py`、`analysis/鋁價/scripts/fetch_data.py`。
- 一次性抓取**不進根目錄 ETL**，除非使用者另外決定。

### 步驟 5：寫總結 WN

檔名：`WN-<今天>-<主題>研究總結與追蹤.md` 或 `…驗證評估.md`，建議結構：

1. **結論**（3–5 點，每點附數字與來源 URL 與資料日期）。
2. **論點驗證表**：論點 | 結果（成立 / 部分成立 / 不成立 / 無法驗證）| 證據 | 來源。
3. **修正與反例**：素材或舊文件錯誤的地方，要明確寫出原文與更正。
4. **資料缺口**：付費或無法自動抓的序列，列出替代方案。
5. **追蹤指標**：之後要定期看的序列與觸發條件。

總結 WN 要引用 WP 的 `report.md` 與 `samples/`，不要重新發明數字；若要用新數字，先在 `scripts/` 產生 CSV 再引用。

### 步驟 6：排程與儀表板（可選）

- 若序列需要長期更新並出現在儀表板，才考慮把抓取移到根目錄 `get_*.py` 並接進 `get_all_series_data.py`。
- 新增 fetcher 時：輸出 `data/<prefix>_*.pkl`，在 `flask_highcharts/app/routes/` 新增或修改 group，並重啟 dev server 驗證（`restart_dev.bat`）。
- 修改 `get_all_series_data.py` 前，先讀 `record_and_check_errors`，確認新任務的失敗會被記錄，不會被吞掉。

---

## 8. 撰寫 WN 的寫作規範（本 repo 慣例）

- 語言：繁體中文，專有名詞保留原文（FRED、CFTC、REINS、着工…）。
- 日期：檔名與內文都用 `YYYY-MM-DD`。素材沒有日期的，標「素材未標日期」。
- 數字：每個數字要有單位、資料日期與出處；年度與暦年、季調與原數要區分。
- 結論要分級：**已驗證 / 部分驗證 / 待驗 / 推測**，不要把推測寫成事實。
- 修正舊結論時，在新 WN 中寫「更正：原文 X，實際 Y，依據 Z」，不要直接改掉舊 WN。
- 引用其他 WN 用相對路徑，例如 `../日本地產/WN-2026-10-08-...md`。

---

## 9. 接手檢查清單

接手一個主題前，依序確認：

- [ ] 讀本 WN（§1–§3、§6–§7）。
- [ ] 讀該主題最新的 WN（規劃與總結）與 `_agent-tasks/` 最新的 DELIVERY。
- [ ] 跑 `git status` 與 `git log --oneline -10`，確認沒有別人未提交的變更。
- [ ] 確認要用的 Python 是 `venv\Scripts\python.exe`。
- [ ] 若要改根目錄 fetcher 或 `data/` 格式，先確認 `flask_highcharts/app/routes/` 誰在用它。
- [ ] 完成後：WN 寫完、verify 通過、commit 訊息用繁體中文；未經使用者同意不 push。

---

## 10. 相關文件索引

| 文件 | 內容 |
|---|---|
| `PLAN-2026-09-15-etl-refactor-m2-replacement.md` | ETL 重構與 M² 替代源計畫（含附錄 A 停用項目） |
| `WN-2026-09-22-A批架構決策-為何用etl-package而非舊版get腳本.md` | ETL 架構決策（檔名以 repo 內為準） |
| `WN-2026-09-22-orchestrator-import修復與M2缺口盤點.md` | 排程 import 副作用修復 |
| `WN-2026-09-23-M2失敗19條-現況與提案.md` | M² 失敗清單與提案 |
| `WN-2026-09-28-M2仍需登入的剩餘依賴盤點.md` | 仍需登入的剩餘依賴 |
| `WN-2026-09-27-FedWatch備援資料源實作.md` | FedWatch 備援實作 |
| `analysis/日本地產/WN-2026-10-08-日本地產數據收集規劃.md` | 日本地產規劃（WP 分工範例） |
| `analysis/日本地產/WN-2026-10-08-日本地產研究總結與追蹤.md` | 日本地產總結（收件後寫法範例） |
| `analysis/鋁價/WN-2026-10-07-鋁業數據收集規劃.md` | 鋁價規劃 |
| `analysis/鋁價/WN-2026-10-07-鋁業數據驗證與投資機會評估.md` | 鋁價驗證與評估 |
| `analysis/石油/資料清單.md` | 石油主題資料清單 |
