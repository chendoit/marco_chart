# PLAN-2026-09-15-etl-refactor-m2-replacement.md

> **一句話**:在原專案 `C:/code/2025-12-05-MacroMicro-Data/` 裡,把散落的 13 支爬蟲重構成統一的 ETL 框架 `etl/`(統一設定、log、儲存契約、錯誤回報、job registry),再把「已找到免費替代源」的 M² series 以新 job 的形式接進同一條 ETL chain。**儀表板(flask_highcharts)和所有 pkl 檔名、格式完全不變。**
>
> **執行方式**:由 Claude(orchestrator)把工作包派給 Claude subagent,依 §9 的波次執行。使用者只在 Gate(G0–G4)做決策。
>
> **取代**:`C:/code/2026-09-11-fincept-terminal/PLAN-2026-09-15-m2-datasource-replacement.md`(fincept-terminal 之後**只做備查**,不再寫入、不再執行任何東西)。
>
> 產生日期:2026-09-15。

---

## 0. 需要使用者先知道的事

1. **M² series 爬蟲已經壞了**。`logs/2026-09-15.log` 裡 91 個 URL 全部回報 `No target script or base64 data found`,`series_2.pkl`、`series_854.pkl` 等檔最後寫入時間是 **2026-08-20**。原因是 orchestrator 只把「拋出例外」當成失敗,而 `get_m_square_series.py` 自己吞掉錯誤,所以 `error_history.json` 每天都是 `[]`,也就沒有發 LINE。附錄 A 那些還沒找到替代源的項目,目前**同樣停在 08-20**。本計畫把修復排成 WP-R2E。
2. **log 每行被寫 12 次**:12 個模組在 import 時各自 `logger.add` 同一個檔,單日 log 約 3.5 MB / 23,552 行。
3. **正式排程 `\get_all_series_data` 每天 08:00 和 18:00 各跑一次(約 50 分鐘),而且是在 main 工作目錄直接跑**。所以開發一律在另一個 **git worktree** 進行,切換前 main 完全不動(§4.2)。
4. **金鑰**:`EIA_API_KEY`、`CONFERENCE_BOARD_ACCOUNT`、`CONFERENCE_BOARD_PW` 目前只放在 fincept-terminal 的 `.env`。**請使用者自行加到原專案 `.env`**(G0)。加好之前,854 / 19080 / 374 / 376 先暫停,不影響其他工作。

---

## 1. 目標

### 1.1 成功定義

1. 所有資料抓取都經過 `etl` 框架:`get_all_series_data.py` 變成只呼叫 `etl` runner 的薄入口。排程器設定**不用改**。
2. **重構零回歸**:13 個既有 fetcher 移植後,輸出 pkl 與舊程式「語意相等」(§6.3)。
3. **失敗看得見**:任何 job 失敗(包含「部分 URL 失敗」)都會進 `error_history`,並依規則發 LINE。不再有吞掉錯誤、假裝成功的情況。
4. log 每行只寫一次;import 模組不會產生任何副作用。
5. 範圍內的 68 條 M² series(§7)由免費源 job 產出,M² legacy job 只剩附錄 A 與 hold 的項目。
6. 儀表板所有 route group 的 `/api/chart/<group>` 都回 200、範圍內 series 不是空的;`calc_pctrank` 的輸出正常。
7. 新增一個資料源 = 在 `etl/sources/` 加 adapter + 在 `etl/jobs/` 加 job 定義,不需要改 runner 或 orchestrator(§3.6 有範例)。
8. 切換到 main 之後,連續 7 天沒有非預期失敗。

### 1.2 不做的事

- 不改 `flask_highcharts/`(包括 `load_series_data` 寫死 `../data` 的問題;列為之後的建議)。
- 不改任何 pkl 檔名、prefix、形狀(`cru_nyme_*` 這種歷史怪名也保留)。
- 不研究附錄 A 的替代源。
- 不 push、不改 remote。

---

## 2. 現況盤點(2026-09-15 subagent 盤點結果)

### 2.1 13 個抓取模組

| 模組 | 來源 | 產出 | 失敗會 raise? | 重構要點 |
|---|---|---|---|---|
| `get_fed_series.py` | FRED(pystlouisfed, `FED_API_KEY`)、NY Fed rates API | `fed_{ID}`(15)、`sofr_/bgcr_/tgcr_{rate,volume,percentN}`、`sofrai_index` | 否(catch-all) | title 取自 `series_search().iloc[0]`(可能抓錯);值可能是 None;SOFR 固定從 2021-08-05 開始 |
| `get_m_square_chart.py` | Playwright(headed)+ Google OAuth,攔截 `data/{chart_id}` | `chart_{id}.pkl`(原始 JSON,寫到 cwd 的 `data/`)、`series_{chartId}{idx}` | 否 | 3 張 chart;`float(None)` 會被吞掉 |
| `get_m_square_series.py` | Playwright + OAuth,regex 抽 base64 | `series_{id}`(87 個不重複 id) | 否 | **目前全壞**;每次失敗都重開瀏覽器、重新 OAuth(一次 36 分鐘);值沒轉 float;`fromtimestamp` 依賴主機時區 UTC+8 |
| `get_m_square_etf.py` | Playwright,攔截 intro_main / intro_netflow | `series_etf_{T}_{close,volume,m2fundflow,m2fundflow_cum}` | 否 | 固定等 8 秒 × 2 |
| `get_ctfc_series.py` | pycot-reports(cftc.gov zip) | `{jpy,eur,aud}_cme_*`、`cru_nyme_*`、`emini_spx_cme_*`;快取 `data/cache/*_cache.pkl`(4 小時) | 報表層級會 | import 時就建資料夾;`cru_nyme` 是 mapping 沒對到 |
| `get_cboe_index.py` | CBOE CDN JSON | `series_cboe_{SYM}`(29)、`series_cboe_{SPX,VIX,VVIX}_ohlc`(`[dt,o,h,l,c]` + `ohlc: True`) | 否 | SPX/VIX/VVIX 重複下載 |
| `get_etf_csv.py` | ProShares NAV CSV | `series_etf_{T}_fundflow`(5) | 否 | 手動維護的 `SPLITS` 表 |
| `get_nyfed_termpremium.py` | NY Fed ACM `.xls`(xlrd) | `series_nyfed_acmtp{02,05,10}` | 會 | sheet 名 "ACM Daily",日期格式 `%d-%b-%Y` |
| `get_gex_series.py` | 本機 SQLite `C:\code\2026-03-24-GEX-lieta\gex_analysis.db` | `gex_{spx,spy,vix}_*` | 否(找不到 DB 只 warning) | 路徑寫死 |
| `get_cme_daily_volume.py` | CME FTP xlsx(headed browser + 人工登入 signal file) | `cme_daily_{code}_{exch}_{volume,oi}`;快取 3,197 個 xlsx(236 MB) | 會 | **import 時替換 `sys.stdout`**;日期是 pandas Timestamp;每次都重新解析全部 xlsx(約 5 分鐘) |
| `get_financial_stress.py` | Chicago Fed CSV、OFR CSV | `chicagofed_NFCI`、`ofr_FSI_US` | 會 | 第一條失敗第二條就不跑 |
| `calc_pctrank.py` | 衍生(讀其他 pkl) | `{id}_pctrank`、`expr_*_pctrank` | I/O 會 | 找不到檔就靜默跳過 |
| `notify_macromicro_blog.py` | M² blog HTML | `data/macromicro_blog_seen.json` → Gmail + LINE | — | |

另外還有:`get_all_series_data.py`(整份都是 top-level 程式碼)、`line_notify.py`(用 stdlib logging,錯誤全吞)、`gmail_smtp.py`、`google_session/`(**未進 git,但被 3 個 tracked 檔 import**)、`logger.py`(沒人用)、`macromicro_login.py`(實質上沒用)。

### 2.2 下游耦合(一定要保留)

- `highcharts_utils.load_series_data(id)`:用 `(?:^|_){id}\.pkl$` 比對,取**檔名最短**的那個。`.OHLC` → `{id}_ohlc.pkl`;`pctrank_id` → `{id}_pctrank.pkl`。
- `calc_pctrank` 和儀表板 expression 用 **datetime 完全相等**做 inner join → 一律 08:00。
- `title` 會顯示在圖例和軸標題上。
- NFCI REV 訊號邏輯在 `get_all_series_data.py` 和 `highcharts_utils.process_rev` 各有一份。

### 2.3 環境

- venv:`venv/`,CPython 3.12.7;playwright 1.56.0、requests 2.32.5、pandas 2.3.3、openpyxl、xlrd、pystlouisfed 3.0.0、pycot_reports 0.1.2、loguru 0.7.3、line_bot_sdk 3.22.0、flask 3.1.2、curl_cffi 0.16.3(已裝但沒人用)。**沒有 requirements 檔,沒有測試。**
- git:branch `main`,tracked 檔乾淨,有 `origin` remote(**不准 push**)。`.gitignore` 已排除 `data/`、`*.json`、`.env`、`*.log`。
- 磁碟:C: 剩約 49 GB(95% 已用),worktree 不要複製 xlsx 快取。

---

## 3. 目標架構

### 3.1 目錄

```
C:/code/2025-12-05-MacroMicro-Data/
├─ etl/
│  ├─ __init__.py
│  ├─ __main__.py              ← python -m etl ...
│  ├─ cli.py                   ← run / list / catalog / check / smoke
│  ├─ core/
│  │  ├─ settings.py           ← 唯一讀 .env 和路徑的地方(REPO_ROOT、DATA_DIR、LOGS_DIR、STATE_DIR、ENV_FILE)
│  │  ├─ logging.py            ← setup_logging():只由 CLI 呼叫一次
│  │  ├─ types.py              ← Output / Job / JobContext / JobResult
│  │  ├─ storage.py            ← 儲存契約:save_outputs / load_pkl / merge_rows / atomic write / 驗證
│  │  ├─ http.py               ← requests Session(timeout、retry、UA)+ curl_cffi 版本
│  │  ├─ browser.py            ← Playwright context 工廠(M² OAuth、CME profile),全專案唯一一份
│  │  ├─ notify.py             ← LINE / Gmail;ETL_NOTIFY=off 時只寫 log
│  │  ├─ runner.py             ← 選 job、拓撲排序、執行、收集 JobResult、寫 run summary
│  │  ├─ alerts.py             ← error_history.json + 連續失敗告警(沿用舊規則)
│  │  └─ registry.py           ← 收集 etl/jobs/*.py 的 JOBS
│  ├─ sources/                 ← 只負責「從外部拿資料」,回傳 rows,不寫檔
│  │  ├─ fred.py  nyfed_rates.py  nyfed_acm.py  chicagofed.py  ofr.py
│  │  ├─ cboe.py  proshares.py  cftc_pycot.py  cftc_socrata.py  gex_sqlite.py  cme_ftp.py
│  │  ├─ macromicro.py         ← series / chart / etf 三種抓法(legacy)
│  │  ├─ yahoo.py  eia.py  fiscaldata.py  mof_jp.py  ecb.py  cb_esf.py  fedwatch.py
│  │  └─ wsts.py  cier.py  twse.py  nyfed_hhdc.py  boj.py  econdb.py  ism.py  cboe_putcall.py
│  ├─ jobs/                    ← 宣告式 job 定義(每個檔輸出 JOBS: list[Job])
│  │  ├─ fed.py  cboe.py  cftc.py  etf_flows.py  nyfed.py  gex.py  cme.py  stress.py
│  │  ├─ macromicro_legacy.py  ← 仍由 M² 抓的清單(附錄 A + hold)
│  │  └─ m2_replacement/       ← 取代 M² 的 job,依來源分檔
│  │     ├─ yahoo.py  fred.py  cboe_cftc_fiscal.py  eia_mof_ecb.py  cb_esf.py  fedwatch.py
│  │     └─ agent_sources.py  ism.py  derived.py
│  ├─ derived/
│  │  ├─ transforms.py         ← yoy / diff12 / spread / ratio / splice / rev_signal
│  │  └─ pctrank.py            ← calc_pctrank 的邏輯(targets 清單原樣搬過來)
│  ├─ post/                    ← run 結束後的動作
│  │  ├─ nfci_signal.py
│  │  └─ blog_notify.py
│  └─ checks/
│     ├─ regress.py            ← 舊輸出 vs 新輸出語意比對(§6.3)
│     ├─ compat.py             ← 儀表板相容契約(§6.2)
│     ├─ verify.py             ← 對 M² snapshot 驗證替代源(§6.4)
│     └─ smoke.py              ← 打 /api/chart/<group> 煙霧測試
├─ tests/                      ← pytest(core 單元測試 + sources 的離線 fixture 測試)
│  └─ fixtures/                ← 存下來的 HTML / JSON / CSV 樣本
├─ docs/
│  ├─ DATA_CATALOG.md          ← 由 `python -m etl catalog` 自動產生:檔案 → job → 來源 → 頻率
│  └─ ADDING_A_SOURCE.md       ← 新增資料源的步驟
├─ requirements.txt            ← 固定版本
├─ get_all_series_data.py      ← 切換後:薄入口 → etl.cli.main(["run","--profile","daily"])
└─ get_*.py / calc_pctrank.py  ← 過渡期變成 shim(import etl 並呼叫),WP-R6 刪除
```

### 3.2 核心型別(`etl/core/types.py`,所有 subagent 都必須照這個介面)

```python
from dataclasses import dataclass, field
from typing import Callable, Literal

Shape = Literal["series", "ohlc", "raw"]
Kind = Literal["level", "pct", "prob", "count", "other"]
Cadence = Literal["daily", "weekly", "monthly", "quarterly", "irregular"]
Policy = Literal["replace", "append", "splice"]

@dataclass(frozen=True)
class Output:
    file: str                   # 不含 .pkl,例如 "series_854"、"fed_DGS10"、"series_cboe_SPX_ohlc"
    title: str                  # 與舊檔完全相同的 title
    shape: Shape = "series"
    kind: Kind = "level"
    cadence: Cadence = "daily"
    allow_none: bool = False    # 舊檔本來就有 None 值的(例如 FRED)才開
    allow_future: bool = False  # 例如 17586 EPS 預估值
    extra_keys: tuple = ()      # 舊 pkl 除了 title/data 以外的 key,例如 ("ohlc",)

@dataclass(frozen=True)
class Job:
    name: str                   # 唯一,例如 "fed.DGS10"、"cboe.indices"、"m2r.854"、"m2legacy.series"
    group: str                  # "fed" | "cboe" | "cftc" | ... | "m2_replacement" | "macromicro_legacy" | "derived"
    fetch: Callable[["JobContext"], dict]   # 回傳 {output.file: rows}
    outputs: tuple[Output, ...]
    policy: Policy = "replace"
    depends_on: tuple[str, ...] = ()        # 其他 job name
    requires: tuple[str, ...] = ()          # env key 名、"browser"、"cme_login"、"gex_db"
    profiles: tuple[str, ...] = ("daily",)
    replaces_m2: str | None = None          # 取代的 M² sid
    quality: Literal["ok", "approx", "partial"] = "ok"
    tol: dict = field(default_factory=dict) # {"rel": 0.02} 或 {"abs": 0.1}
    notes: str = ""
```

- `fetch` **只抓資料、只回傳 rows**,不寫檔、不發通知、不 `logger.add`。
- 一個 job 可以有多個 output(CBOE 一次產 close + ohlc、CFTC 一份報表產很多欄、SOFR 產很多百分位)。
- **部分失敗**:fetch 可以回傳部分成功的 outputs,同時拋 `PartialFailure(errors=[...])`;runner 會寫入成功的部分,並把 job 標成 `partial`(**算失敗,要進告警**)。
- `JobContext` 提供:`settings`、`out_dir`、`read(file)`(先讀 out_dir,讀不到再讀 `read_fallback_dir`)、`http`、`browser()`、`log`(已綁 job name 的 logger)、`state_dir`、`snapshot_dir`、`full`、`dry_run`。

### 3.3 儲存契約(`etl/core/storage.py`)

| shape | 格式 | 驗證 |
|---|---|---|
| series | `{"title": str, "data": [[datetime, float], ...]}` + `extra_keys` | naive datetime、時間 08:00:00;遞增、不重複;值是有限 float(`allow_none` 時可為 None);月頻是 1 日 |
| ohlc | `{"title", "data": [[datetime, o, h, l, c]], "ohlc": True}` | 同上,每列 5 個元素 |
| raw | 任意 pickle(只有 `chart_{id}.pkl` 這類中間檔) | 不驗證 |

- 寫入前把 pandas `Timestamp` 轉成 `datetime.datetime`,numpy 數字轉成 Python float(語意等價)。
- 安全閥:**不倒退**(新資料最後日期早於既有檔 → 不寫,報 `REGRESSION`);**不縮水**(policy 不是 replace,而且點數 < 既有 × 0.8 → 不寫,報 `SHRINK`)。
- 原子寫入:先寫 `.tmp` 再 `os.replace`。
- 來源、抓取時間、點數寫到 sidecar `state/meta/<file>.json`,**不寫進 pkl**。

### 3.4 Runner 與告警

```bash
venv/Scripts/python.exe -m etl run --profile daily                     # 取代 get_all_series_data.py 的內容
venv/Scripts/python.exe -m etl run --group cboe --out <dir> --dry-run
venv/Scripts/python.exe -m etl run --job m2r.854 --job m2r.19080
venv/Scripts/python.exe -m etl run --m2-sid "854 19080"
venv/Scripts/python.exe -m etl list [--group ..]  /  catalog  /  check compat|regress|verify  /  smoke --base URL
```

- 順序:沿用舊 orchestrator 的群組順序(fed → macromicro_legacy → cftc → cboe → etf_flows → nyfed → gex → cme → stress → **m2_replacement** → derived(pctrank)→ post(nfci、blog))。群組內再依 `depends_on` 拓撲排序。
- 每次 run 寫 `logs/etl_runs/YYYY-MM-DD_HHMMSS.json`:`{job: {status, outputs, rows, last_date, seconds, error}}`。
- `alerts.py`:`error_history.json` 格式沿用舊的(`{date: [job names]}`,保留 7 天,最近 3 筆紀錄都出現同一個 job 就發 LINE)。記錄的從「task name」改成「job name 或 group」;`partial` 也算失敗。
- **行為改變(G1 要確認)**:以前被吞掉的失敗現在會發 LINE。可以用 `ETL_ALERT_MIN_DAYS` 調整門檻。
- `requires` 不滿足(沒有 key、GEX DB 不存在、CME 沒登入)→ 標成 `skipped`,**同樣會記錄**;要不要算失敗,由 job 設定 `skip_is_failure` 決定(CME / GEX 預設 false,其他 true)。
- 結束碼:0 = 全部 ok 或 skipped;1 = 有 failed / partial;2 = 設定錯誤。

### 3.5 設定與環境

- `settings.py` 解析順序:環境變數 → `ETL_ENV_FILE`(預設 `<REPO_ROOT>/.env`)。
- 路徑:`DATA_DIR`(預設 `<REPO_ROOT>/data`);`--out` 可以覆寫。`LOGS_DIR = <REPO_ROOT>/logs`;`STATE_DIR = <REPO_ROOT>/state`(加進 .gitignore)。
- `ETL_NOTIFY=off`:開發與測試**一律**設定,LINE / Gmail 只寫 log。
- 其他檔案**不准**直接 `os.getenv` 或 `load_dotenv`。

### 3.6 新增資料源的範例(會寫進 `docs/ADDING_A_SOURCE.md`)

```python
# etl/sources/eia.py
def fetch_series(ctx, series_id: str) -> list[list]:
    key = ctx.settings.require("EIA_API_KEY")
    r = ctx.http.get("https://api.eia.gov/v2/seriesid/" + series_id, params={"api_key": key})
    ...
    return rows  # [[datetime(08:00), float], ...]

# etl/jobs/m2_replacement/eia_mof_ecb.py
JOBS = [
    Job(name="m2r.854", group="m2_replacement", replaces_m2="854",
        fetch=lambda ctx: {"series_854": eia.fetch_series(ctx, "PET.WCESTUS1.W")},
        outputs=(Output("series_854", title="us-oil-inventory", cadence="weekly"),),
        requires=("EIA_API_KEY",), notes="excl SPR"),
]
```

---

## 4. 鐵律與工作環境

### 4.1 鐵律

1. **切換(WP-C1)之前,main 工作目錄 `C:/code/2025-12-05-MacroMicro-Data/` 的程式碼一律不動**。只允許:讀取;G0 由使用者自己改 `.env`;WP-R0 修改 `.gitignore` 並追蹤 `google_session/*.py`(這一步在 main 上 commit,不影響執行)。
2. **正式資料 `data/` 在切換前唯讀**(只能複製出去)。
3. 開發只在 worktree `C:/code/2025-12-05-MacroMicro-Data-wt/etl`(branch `etl-refactor`)進行。
4. `fincept-terminal` **只讀**(拿 `migration/fetch_mapped.py`、`migration/agent_results/*.json` 當參考)。
5. 所有開發和測試都要設 `ETL_NOTIFY=off`。舊程式在跑 golden 時,要在 subprocess 環境清掉 `CHANNEL_ACCESS_TOKEN`、`MAIL_TOKEN`、`APP_PASSWORD`,避免真的發出通知。
6. 金鑰不准印出、不准寫進報告或 fixture。fixture 裡如果有 key,要先遮蔽再存。
7. 新程式碼(M² legacy 的 `sources/macromicro.py`、`jobs/macromicro_legacy.py`、`post/blog_notify.py` 除外)**禁止**出現 `macromicro` 字串。
8. **不准 push**;只在 `etl-refactor` branch commit(由 orchestrator 在每一波結束後統一 commit)。
9. subagent **只能改自己被分配的檔案**(§9 表格);需要改共用檔(`etl/core/*`)時,寫進回報,由 orchestrator 處理。
10. 不准輸入密碼、不准處理 CAPTCHA。M² 或 CME 的 session 失效需要登入時 → STOP。
11. 不准建立或修改 Windows 排程,除非經過 G2 / G3。
12. 移植既有邏輯**不改行為**;發現的 bug 記進回報的「建議」,由 G1 決定要不要修。

### 4.2 Worktree 與暫存資料

```bash
cd "C:/code/2025-12-05-MacroMicro-Data"
git worktree add -b etl-refactor "C:/code/2025-12-05-MacroMicro-Data-wt/etl" main
```

- worktree 沒有 `.env` 和 `venv`:共用 main 的 venv(`C:/code/2025-12-05-MacroMicro-Data/venv/Scripts/python.exe`),並設 `ETL_ENV_FILE=C:/code/2025-12-05-MacroMicro-Data/.env`。
- **worktree 的 `data/` 就是暫存資料目錄**:WP-R0 會複製正式 `data/*.pkl`(不含 xlsx)進去。所有新 job 預設都寫到這裡。worktree 裡的 `flask_highcharts` 讀 `../data` 剛好就是暫存資料,所以可以直接當 shadow 儀表板(port 6102)。
- golden 輸出放 `worktree/_golden/<module>/`,snapshot 放 `C:/code/2025-12-05-MacroMicro-Data-wt/_snapshots/m2_<date>/`(都不進 git)。
- 需要安裝的新套件(`cme-fedwatch`、`pytest`、`pypdf` 視需要)裝進共用 venv:只能新增,不能升級既有套件。安裝前後各做一次 `pip freeze`,差異寫進回報。**如果安裝需要升級既有套件 → STOP。**

### 4.3 STOP 條件

- 需要 `.env` 裡沒有的 key、需要登入、遇到 CAPTCHA 或付費牆。
- regression 出現非預期差異(§6.3 允許範圍以外)。
- 需要改自己被分配以外的檔案。
- 安裝套件會升級或降級既有套件。
- 儲存安全閥觸發。
- 單一指令卡住超過 30 分鐘。
- 發現正式排程正在跑,而工作需要讀取 `data/` 的一致快照。

### 4.4 Subagent 回報(`worktree/reports/<WP>.md`,同時回傳給 orchestrator)

```markdown
## <WP> 回報
- 狀態:DONE / PARTIAL / BLOCKED
- 改動檔案:(只能是被分配的)
- 驗證:(實際指令 + 輸出摘要;pytest / regress / compat 結果)
- 與舊行為的差異:(沒有差異就寫「無」)
- 發現的 bug / 建議:(不要自己修)
- 需要使用者決策:
```

---

## 5. 陷阱清單(移植時一定要保留或處理)

**既有爬蟲**
1. M² series:`fromtimestamp` 依賴主機時區 UTC+8;1970 年以前用 epoch + timedelta 並 `.replace(hour=8)`。新版要**明確**用 UTC+8 換算,結果必須和舊版相同。
2. M² 需要 headed browser + stealth.min.js + OAuth storage state;M² chart 的原始回應要點頁面才會出現;ETF netflow 要點「資金淨流量」分頁才會觸發。
3. M² 失敗時不要每個 URL 都重開瀏覽器、重新 OAuth:改成整批共用一個 context,只有 session 失效才重建一次。
4. CME:只有 headed browser + `page.evaluate(fetch(..., {credentials:'include'}))` 下載得到;要用 `domcontentloaded`(不能用 `networkidle`);登入用 signal file;xlsx 第 2 張 sheet "by Product"、clearing code J1/EC/AD、"F"/"O" 旗標;下載間隔 2 秒。**重構後改成增量解析**(只解析新的 xlsx,合併進既有 pkl),但輸出必須和全量重建相同(regression 用全量結果比對)。
5. CME 在 import 時替換 `sys.stdout` → 刪掉這個副作用,改由 CLI 設 UTF-8。
6. CFTC:`cru_nyme_*` 檔名保留;快取 4 小時保留;注意 `import datetime` 被遮蔽的問題。
7. CBOE:不支援的 symbol 回 403/404;OHLC pkl 有 `ohlc: True` key。
8. ProShares:`SPLITS` 表的前後 3 天跳過邏輯要保留(正反向分割都一樣)。
9. NY Fed ACM:要用 xlrd;sheet "ACM Daily";暫存 xls 用完要刪。
10. GEX:DB 路徑改從 settings `GEX_DB_PATH` 讀,預設值維持舊路徑;找不到 DB → `skipped`。
11. FRED:title 維持舊邏輯(`series_search().iloc[0]`)算出來的字串;為了穩定,改成**寫死舊檔現在的 title**(從 snapshot 讀出來),不要每次 search。
12. `financial_stress`:兩條分開 try,第一條失敗不影響第二條(這是行為改善,要寫進回報)。
13. log 只 setup 一次;`line_notify` 改用 loguru。

**M² 替代源(沿用 fincept 計畫的結論)**
14. 20508 / 32377 的 agent 結果還在打 M² chart API → 不算替代,留在附錄 A。
15. ISM 267/281/277/22807 的歷史來自 Wayback / GitHub,必須找到會持續更新的來源,找不到就 hold。
16. 22806 改成 590 − 595 衍生。
17. M² 舊 pkl 是採樣資料 → 只比共同日期。
18. `title` 沿用舊 pkl(例如 `saving-rate`),不要用 fetch_mapped 裡的中文 title。
19. `fetch_mapped.py` 的 DISPATCH 以最後一次 `update()` 為準(246/1916/4448/4456)。
20. 246 splice 的歷史要讀 snapshot;4456 `depends_on` 2018。
21. CB ESF 每次只回 7 筆、token 一次性 → 每天只做增量。
22. cme_fedwatch 只保留約 5 個交易日 → `append`,原始 JSON 存 `state/fedwatch/`。
23. econdb 臨時 token;BoJ 表格欄位要用表頭確認。
24. 既有正確寫法不要去「修」:Yahoo `period1=0&period2=1790000000`;CFTC Socrata `kh3c-gbw2` / `067651`;TGA `open_today_bal`;銅金比 `HG×100/GC`;crack `(2×RB×42+HO×42)/3−CL`;EIA 854 `PET.WCESTUS1.W`、19080 `PET.MCSSTUS1.M`。
25. 414 名稱是 NSA,卻用 `SPCS20RSA`(SA)→ 列入 G1。

**環境**
26. Windows cp950:印中文一律加 `PYTHONIOENCODING=utf-8`。
27. git-bash:路徑寫 `C:/...`;背景程序用 PID 精準結束(`taskkill //F //T //PID`)。
28. 正式排程每天 08:00、18:00 各跑一次,約 50 分鐘。**08:00–09:30、18:00–19:30 不要複製正式 `data/`。**

---

## 6. 驗證機制

### 6.1 測試分層

| 層級 | 內容 | 工具 |
|---|---|---|
| 單元 | core:storage 契約、merge、安全閥、settings、runner 排序與結果、alerts 規則 | pytest,不連網 |
| 離線 fixture | 每個 source 用存下來的回應樣本解析(M² HTML / JSON、CBOE JSON、ProShares CSV、ACM xls、CME xlsx、FRED JSON…) | pytest,不連網 |
| Regression | 舊模組 vs 新 job,同一個時段各跑一次(§6.3) | `python -m etl check regress` |
| 相容性 | 暫存資料目錄的所有 pkl 符合儀表板契約(§6.2) | `python -m etl check compat` |
| 替代源驗證 | M² 替代 job vs snapshot(§6.4) | `python -m etl check verify` |
| 端到端 | worktree 儀表板(port 6102)所有 group 的 API,和正式 5002 比對;跑 `calc_pctrank` | `python -m etl smoke` |

### 6.2 相容契約(compat)

C1 檔名唯一(不能有兩個檔同時符合 `(?:^|_){id}\.pkl$`,而且最短的那個必須是正確的檔);C2 形狀和 key(含 `extra_keys`);C3 title 和 snapshot 相同;C4 08:00;C5 遞增且不重複;C6 值的型別(依 `allow_none`);C7 月頻 1 日、季頻日期慣例和 snapshot 相同;C8 沒有未來日期(依 `allow_future`);C9 共同日期比對率 ≥ 90%;C10 新鮮度(只 WARN)。

### 6.3 Regression(重構零回歸的定義)

- **做法**:在同一個 session 裡,先用舊模組(subprocess,`DATA_DIR=_golden/<module>`,cwd = worktree,清掉通知用的 token),再用新 job(`--out _new/<module>`)各跑一次。
- **語意相等**:檔案集合相同;title 相同;extra keys 相同;`Timestamp` 和 `datetime` 視為相等;`None == None`、NaN == NaN;float 容差 1e-9。
- **允許的差異**:
  - 即時資料源:如果兩次執行之間剛好有新資料,允許最後 3 天內的值不同,或新輸出多出最後幾筆。
  - 舊版的**已知 bug**(例如 `financial_stress` 第一條失敗就不跑第二條),在回報中列出。
- **無法做 live regression 的**:
  - M²(目前壞掉):用存下來的 HTML / JSON fixture 做離線比對。
  - CME:不下載,用既有 xlsx 快取做全量重建比對。
  - GEX:DB 存在就比,不存在就 skip。

### 6.4 替代源驗證(verify)

沿用 fincept 計畫的規則:level 用 rel 2%,pct 用 abs 0.10 個百分點,prob 用 abs 5 個百分點。判定分 PASS / WARN / FAIL;另外檢查 inner join 數量(`series_2` × `series_cboe_VIX` 最近 400 天 ≥ 250 天)。報告寫到 `reports/verify_<date>.md`。

---

## 7. M² 替代範圍(68 條,明細見 fincept 計畫 §6,這裡只列分組)

| 分組 | job 檔 | sid |
|---|---|---|
| yahoo(16) | `m2_replacement/yahoo.py` | 2、486、8219、4934、483、562、385、745、7145、7146、386、621、485、4481、1281、4249 |
| fred(19) | `m2_replacement/fred.py` | 7449、131、348、75、7359、560、37、44、34、36、22910、319、246(splice)、254、255、414、3612、755、634 |
| cboe / cftc / fiscal(7) | `m2_replacement/cboe_cftc_fiscal.py` | 7148、4407、7147、8297、8298、8296、29123 |
| eia / mof / ecb(6) | `m2_replacement/eia_mof_ecb.py` | 854、19080、2018、1916、4448、4456 |
| cb_esf(2) | `m2_replacement/cb_esf.py` | 374、376 |
| fedwatch(2) | `m2_replacement/fedwatch.py` | 484、1645 |
| agent 結果(12) | `m2_replacement/agent_sources.py` + `derived.py` | 1650、17581、4869、590、595、2756、5683、31742、2752、3776、4433、22806(=590−595) |
| ISM(4) | `m2_replacement/ism.py` | 267、281、277、22807(=267−277) |

- 參考程式:`C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py`、`migration/agent_results/series_<sid>.json`、`WN-2026-09-14-*.md`、`WN-2026-09-15-*.md`(唯讀)。
- 每條要附:snapshot title、kind、cadence、tol、policy、quality、`replaces_m2`、notes。

---

## 8. 工作包

### WP-R0 基準與工作環境(orchestrator 親自做)

1. 確認正式排程沒在跑(看最新 log 的尾巴,以及 python 程序)。
2. main 上:`.gitignore` 加 `state/`、`_golden/`、`_new/`、`reports/*.tmp`、`!requirements.txt`;追蹤 `google_session/__init__.py`、`auth.py`(先確認沒有寫死的秘密)。commit。
3. 建 worktree(§4.2)。
4. 在 worktree 外建 `_snapshots/m2_<date>/data/`(複製正式 `data/*.pkl`)+ `manifest.json`(每個 pkl 的 sha256、n、first、last、title、推估 cadence)。
5. 把正式 `data/*.pkl` 複製到 worktree 的 `data/`,`data/cache/` 也要複製;CME xlsx 快取**不複製**,用 junction 連過去,並設為唯讀使用。
6. `pip freeze > reports/pip_freeze_before.txt`;產生 `requirements.txt`(只列專案實際 import 的套件,版本固定)。
7. 用舊模組跑一次「離線可跑」的 golden 基線,確認 subprocess 呼叫方式可行(例如 `get_cboe_index.fetch_cboe_indices`)。

**DoD**:worktree 可用;snapshot 和 manifest 完成;`.gitignore` 和 `google_session` 在 main 上 commit 完;回報寫好。

### WP-R1 etl 核心框架(1 個 subagent)

實作 §3.2–§3.5:`etl/core/*`、`cli.py`、`__main__.py`、`checks/regress.py`、`checks/compat.py`、`tests/`(core 單元測試)、`docs/ADDING_A_SOURCE.md`、`docs/DATA_CATALOG.md` 產生器。

- 附一個示範 job(`jobs/stress.py` 的 Chicago Fed NFCI),從 fetch 到寫檔跑完整流程。
- **DoD**:pytest 全過;`python -m etl list` 可用;`python -m etl run --job stress.nfci --out _new/stress` 成功;對 golden 做 regress 相等;compat 可以對 worktree `data/` 跑;import `etl` 任何模組都沒有副作用(測試:import 後 `logs/` 沒有新檔、stdout 沒有被換掉)。

### WP-R2 移植既有爬蟲(並行,每個 subagent 只負責自己的檔案)

| 子包 | 負責的檔案 | 內容 | 驗證方式 |
|---|---|---|---|
| R2A | `sources/fred.py`、`sources/nyfed_rates.py`、`jobs/fed.py` | get_fed_series 全部(15 FRED + SOFR / BGCR / TGCR / SOFRAI) | live regression |
| R2B | `sources/cboe.py`、`sources/proshares.py`、`sources/nyfed_acm.py`、`sources/chicagofed.py`、`sources/ofr.py`、`jobs/cboe.py`、`jobs/etf_flows.py`、`jobs/nyfed.py`、`jobs/stress.py`(接手 R1 的示範) | CBOE 29 + OHLC、ProShares 5、ACM 3、NFCI、OFR US | live regression |
| R2C | `sources/cftc_pycot.py`、`sources/gex_sqlite.py`、`jobs/cftc.py`、`jobs/gex.py` | CFTC legacy 4 + TFF、GEX 全部 | live / DB regression |
| R2D | `sources/cme_ftp.py`、`jobs/cme.py` | CME daily volume:下載流程原樣移植(不實際執行)+ **增量解析** | 用 xlsx 快取做全量重建比對;增量結果 = 全量結果 |
| R2E | `sources/macromicro.py`、`jobs/macromicro_legacy.py`、`post/blog_notify.py`、`tests/fixtures/macromicro/` | M² series / chart / etf 三種抓法 + blog;**調查 91/91 失敗的原因** | fixture 離線測試;live 測試只抓 1–2 個 URL,需要重新登入就 STOP |
| R2F | `derived/pctrank.py`、`derived/transforms.py`、`post/nfci_signal.py` | calc_pctrank(targets 原樣搬)、NFCI REV 訊號、共用的 transform | 用 worktree `data/` 跑,輸出和舊 `calc_pctrank.py` regress 相等 |

**R2 共同 DoD**:負責範圍的 regress 相等(或只有 §6.3 允許的差異);fixture 測試通過;compat 通過;回報列出所有行為差異和建議。

### WP-M1 M² 替代 job(並行,§7 的分組)

| 子包 | 負責的檔案 |
|---|---|
| M1a yahoo | `sources/yahoo.py`、`jobs/m2_replacement/yahoo.py` |
| M1b fred | `jobs/m2_replacement/fred.py`(共用 R2A 的 `sources/fred.py`,需要新增函式的話寫進回報)+ `derived/transforms.py` 的 splice(**要和 R2F 協調:M1 等 R2F 完成才開始**) |
| M1c cboe / cftc / fiscal | `sources/cftc_socrata.py`、`sources/fiscaldata.py`、`jobs/m2_replacement/cboe_cftc_fiscal.py`(CBOE 共用 R2B 的 source) |
| M1d eia / mof / ecb | `sources/eia.py`、`sources/mof_jp.py`、`sources/ecb.py`、`jobs/m2_replacement/eia_mof_ecb.py`(854 / 19080 要等 G0 的 key) |
| M1e cb_esf | `sources/cb_esf.py`、`jobs/m2_replacement/cb_esf.py`(要等 G0 的 key;全量回補只跑 1 次) |
| M1f fedwatch | `sources/fedwatch.py`、`jobs/m2_replacement/fedwatch.py`(先確認口徑:今天的值 vs snapshot 最後一筆,差 ≤ 5 個百分點。**注意 M² 自 08-20 起停更,比較時要考慮時間差**;無法判斷就 STOP) |
| M1g agent 結果 | `sources/{wsts,cier,twse,nyfed_hhdc,boj,econdb,ofr(World 欄位,和 R2B 協調),cboe_putcall}.py`、`jobs/m2_replacement/agent_sources.py`、`jobs/m2_replacement/derived.py` |
| M1h ISM | `sources/ism.py`、`jobs/m2_replacement/ism.py`(先試 dbnomics live 來源,每條最多 45 分鐘,找不到就判 hold) |

- **做法**:以 fincept 的 `fetch_mapped.py` 和 agent snippet 為參考,改寫成 `sources` + `jobs`。每條實測 `--dry-run`(印最後 3 筆),再寫進 worktree `data/`。
- **DoD**:每條 job 定義完整;compat 通過;`python -m etl check verify --m2-sid <...>` 已跑並附結果;hold 的項目附上證據。

### WP-V1 整合驗證(1 個 subagent + orchestrator)

1. 在 worktree 跑 `python -m etl run --profile daily --skip-group macromicro_legacy --skip-requires cme_login`(完整一輪,寫進 worktree `data/`)。
2. `check compat`(全部 pkl)、`check verify`(68 條)、`check regress`(R2 各模組再比一次)。
3. 用舊 venv 在 worktree 啟動 flask(**只在 worktree 內**把 port 改成 6102;這個改動不 commit,可以用環境變數或臨時 patch 處理)→ `python -m etl smoke --base http://localhost:6102 --compare http://localhost:5002`。
4. 輸出 `reports/V1_integration.md` + G1 決策清單。

### 【G1】使用者決策

- [ ] 告警行為改變(以前吞掉的失敗現在會發 LINE)的門檻
- [ ] approx 項目接受 replace?1916、4448、131、75、7359、44、254、3612、2752、4433;3776 CRB → DJP 用 replace 還是 hold?
- [ ] ISM 被判 hold 的項目
- [ ] R2 回報裡列的舊 bug 要不要修(每一項分開勾)
- [ ] R2E 對 M² 91/91 失敗的調查結論和修法
- [ ] 414 的 SA / NSA

### WP-P1 並行試跑(≥ 5 個工作日)→ 前面有【G2】

- 【G2】要不要建排程 `etl_worktree_staging`(每天 10:30 在 worktree 跑 `etl run --profile daily`,寫到 worktree `data/`,`ETL_NOTIFY=off`)?還是手動跑?
- 每天:R2 範圍的 job 和正式目錄(舊程式當天剛寫入)做 regress(這時正式目錄就是當天的 golden);m2_replacement 做 compat + 新鮮度檢查;run summary 彙總。
- **DoD**:連續 5 天沒有非預期差異、沒有 failed(除了 G1 已接受的)。

### WP-C1 切換到 main → 前面有【G3】

- 【G3】摘要 V1 + P1 的結果,**明確詢問是否 merge 到 main**。
1. 時間:正式排程跑完之後。建 `_snapshots/precutover_<date>/`(完整複製正式 `data/*.pkl`)。
2. worktree 最後整理:`get_all_series_data.py` 改成薄入口;舊的 `get_*.py` 和 `calc_pctrank.py` 改成 shim(保留函式名稱,內部呼叫 etl),確保其他地方 import 還能用;`jobs/macromicro_legacy.py` 只剩附錄 A + hold 的項目;`docs/DATA_CATALOG.md` 重新產生。
3. main:`git merge --no-ff etl-refactor`(**不 push**)。
4. 在 main 只跑不需要瀏覽器的部分,寫進正式 `data/`:`etl run --profile daily --skip-group macromicro_legacy --skip-requires cme_login`。接著 `check compat`,再 `smoke --base http://localhost:5002`。
5. 隔天 08:00 正式排程第一次跑新入口:orchestrator 檢查 run summary。
6. **回滾**:`git revert -m 1 <merge commit>`;把 precutover snapshot 裡的 pkl 複製回正式目錄。

### WP-R6 上線監控 7 天與收尾

- 每天看 run summary、error_history、compat、smoke。
- 7 天沒問題之後:刪除 shim(舊的 `get_*.py`)和 `logger.py`、`macromicro_login.py` 這類沒用的程式(先列清單給使用者確認);清掉 worktree;寫 WN 筆記;更新 `docs/DATA_CATALOG.md`。
- 【G4】給使用者:監控彙總、仍由 M² 抓的清單、下一階段建議(附錄 A 研究順序、flask `load_series_data` 路徑寫死的問題)。

---

## 9. Subagent 派工(orchestrator 執行順序)

| 波次 | 並行 | 工作包 | 前置 |
|---|---|---|---|
| 0 | orchestrator | WP-R0 | — |
| 1 | 1 | WP-R1 | R0 |
| 2 | 最多 4 | R2A、R2B、R2C、R2F → 接著 R2D、R2E | R1 |
| 3 | 最多 4 | M1a、M1c、M1f、M1g → 接著 M1b、M1d、M1e、M1h | R1 + R2A(M1b)+ R2B(M1c)+ R2F(M1b 的 splice) |
| 4 | 1 + orchestrator | WP-V1 | 2、3 |
| — | 使用者 | G1 | V1 |
| 5 | orchestrator | WP-P1(G2) | G1 |
| — | 使用者 | G3 | P1 |
| 6 | orchestrator | WP-C1、WP-R6 | G3 |

- 每一波結束後,orchestrator 檢查回報、跑 pytest + compat,再 commit(`etl-refactor` branch)。
- 發給 subagent 的任務說明包含:WP 代號、負責檔案清單、必讀章節(§3、§4、§5、§6 相關段落)、參考檔路徑、DoD、回報路徑。
- 同一個外部來源不讓兩個 subagent 同時打(Yahoo、CB ESF、M² 各自只能有 1 個)。

---

## 附錄 A — 仍依賴 M²、這次不研究替代源的項目

(明細和研究線索見 fincept 計畫附錄 A;這裡只列清單)

| 類別 | 項目 |
|---|---|
| series(17) | 18331、22718(S&P500 市場寬度);6783 / 6784 / 6785(AAII);27118 / 27119 / 27126 / 27135 / 27129 / 27131 / 27136 / 27138 / 27134(9 國 CDS);7249(WEI);4(實質 GDP 年增);17586(S&P500 EPS) |
| 陳舊 | 261(Case-Shiller SA,url 已註解,停在 2024-11) |
| 假替代 | 20508(全球 PMI 擴散)、32377(JPY VIX) |
| chart | 115044 OIS(1150440–1150446)、71245 FedWatch(712450 / 712451)、56752 LEI / CEI YoY(567520 / 567521) |
| ETF | 7 檔的 close / volume / m2fundflow / m2fundflow_cum |
| 其他 | `notify_macromicro_blog.py` 保留或移除 |

> 這些項目在重構後會由 `jobs/macromicro_legacy.py` 統一管理。R2E 修好 M² 抓取之前,它們維持停在 2026-08-20。
