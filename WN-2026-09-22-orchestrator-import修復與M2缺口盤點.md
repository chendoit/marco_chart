# WN: get_all_series_data.py import bug 修復 + M² series 缺口盤點 (2026-09-22)

## 背景

用戶提問：`get_m_square_series.py` 的 `url_list` 裡，目前還有多少「失敗且沒被其他方式 cover」的 series。
追查後發現問題比這個問題本身更大：整條 orchestrator 已經連續當機多天，根本沒有「今天的失敗清單」可看。

## 根因 1：get_all_series_data.py import 遺漏（已修復）

`tasks` 清單（[get_all_series_data.py:43](get_all_series_data.py)）直接引用
`fetch_fed_treasury_yields`、`fetch_sofr_data`、`fetch_fed_liquidity_reference_rates`、`fetch_and_save_fred_data`，
但檔案開頭完全沒有 `from get_fed_series import ...`。這 4 個名字定義在 `get_fed_series.py`。

`tasks = [...]` 是 module 載入當下就要 resolve 每個元素，所以只要一執行就在 import 結束、
還沒進 for-loop 前 `NameError` 崩潰。

**證據**：
- `logs/error_history.json` 停在 2026-09-17，之後（09-18~09-22）完全沒再寫入。
- 09-18 之後每天的排程 log（如 `logs/2026-09-22.log.gz`）只有 3 行——`get_m_square_series`/
  `get_m_square_etf`/`get_ctfc_series` 三個模組在 import 當下印的初始化訊息，之後就沒了，跟崩潰點吻合。
- 上一次真正跑完全部任務是 09-17 08:47。

**修復**：在 `get_all_series_data.py` 加回：
```python
from get_fed_series import (
    fetch_and_save_fred_data,
    fetch_fed_treasury_yields,
    fetch_sofr_data,
    fetch_fed_liquidity_reference_rates,
)
```
已用 `py_compile` 驗證語法，並手動比對 tasks 清單裡全部 26 個函式名稱，確認都已 import 或定義。

## 修復後全量重跑結果（2026-09-22 16:56~17:07，`logs/manual_run_2026-09-22.log`）

26 個任務中 23 個成功，3 個標記失敗：

| 任務 | 狀態 | 備註 |
|---|---|---|
| FRED csv (261/4/7249) | OK | |
| FRED STLFSI4 / THREEFYTP10 / T10Y2Y / DFII10 / MMMFFAQ027S | OK | |
| NY Fed SOFR | OK | |
| FRED IORB + ON RRP + DFF | OK | |
| MacroMicro charts (curl_cffi API, 13 series) | OK | |
| **MacroMicro series (61 series, Playwright)** | **FAILED** | 只嘗試到第 1 條就中斷，見下 |
| **MacroMicro ETFs** | **FAILED** | 同一 session 問題連帶失敗 |
| Yahoo Finance MOVE | OK | |
| CFTC data / CFTC E-mini SPX TFF | OK | |
| CBOE indices | OK | |
| ETF fund flow (ProShares CSV) | OK | |
| NY Fed ACM Term Premium | OK | |
| GEX (SPX/SPY/VIX) | OK | |
| CME daily_volume | OK | |
| Chicago Fed NFCI + OFR FSI | OK | |
| OFR FSI global | OK | |
| CDS 9 countries | OK | |
| Percentile rank | OK | |
| **Official XLSX 10 series** | **FAILED(標記)，實際 9/10 成功** | 見下，sid 5683 防呆正常擋下 |
| ISM PMI 5 series | OK | |

## MacroMicro series / ETFs：未解決，依用戶指示不再重試

本次只嘗試到 `url_list` 第 1 條（sid 2 sp500）：第一次抓取沒抓到資料 → 觸發「換新瀏覽器重試」→
重新建立 session 時，驗證導覽 `macromicro.me` 直接 `Page.goto: net::ERR_ABORTED`，整個任務中斷。
ETF 任務緊接著也在同一個 session 建立機制上失敗（已觸發「MacroMicro 登入失敗」LINE 通知）。

**結論：這次重跑沒有拿到任何一條 M² series 的新資料**——问题發生在比實際抓資料更前面的瀏覽器/登入層，
不是個別 series 的內容問題。原本打算針對這兩個任務單獨重試以取得每條 series 的真實成敗，
但依用戶指示：**假設這 61 條這次全部視為失敗，不再重試**，直接留作後續工作項。

## 本地 pkl 落後天數盤點（純讀本地檔案，不連網，2026-09-22 對照）

按落後天數排序（`lag_days` = 今天 − pkl 最後一筆日期）：

| sid | 最後日期 | 落後天數 | 名稱 | 分類 |
|---|---|---|---|---|
| 17586 | 2025-04-01 | 538 | sp500-eps | **B（假缺口，已被 get_official_xlsx.py 覆蓋，今天成功）** |
| 755 | 2026-01-01 | 263 | delinquency-rate-on-business-loans | A |
| 4433 | 2026-04-01 | 173 | us-debt-severe-delinquency-student | **B（假缺口，已被 get_official_xlsx.py 覆蓋，今天成功；n=106 沒變只是 NY Fed 季頻報告本身還沒出新一季，不是抓取失敗）** |
| 4 | 2026-04-01 | 173 | realgdp-yoy | **B（假缺口，已被 get_fred_csv.py 覆蓋，今天成功）** |
| 414 | 2026-05-01 | 143 | sp-case-shillar-20-home-price-nsa | A |
| 348/31742/374/376/75/7359/560/254/255/319 | 2026-06-01 | 112 | pce-core / M2-yoy / cb-leading / cb-coincident / saving-rate / pce-real / disposable-income / new-home-sales / price-new-houses / durable-goods | A |
| 131/246/22910/44/37 | 2026-07-01 | 82 | core-CPI / existing-home-sales / sahm-rule / nonfarm-payrolls / unemployment-rate | A |
| 36 | 2026-08-01 | 51 | continuedclaims | A |
| 34 | 2026-08-08 | 44 | initialclaims | A |
| 8297/8298/8296 | 2026-08-11 | 41 | crude-oil CFTC long/short/net | A |
| 7449 | 2026-08-12 | 40 | us-fed-excess-reserves-weekly | A |
| 854/19080 | 2026-08-14 | 38 | us-oil-inventory / us-strategic-petroleum-reserve | A |
| 8219/29123/3612/634/3776 | 2026-08-18 | 34 | wti-daily / TGA / credit-spread / CCC-yield / CRB-index | A |
| 其餘 24 條（2/4934/486/7148/483/4456/2018/4448/562/1916/385/484/1645/4407/18331/22718/7145/7146/386/1281/7147/485/4481/4249） | 2026-08-19 | 33 | sp500、原油、DXY、FX 一籃子、日德公債利差、fedwatch、skew、市場寬度、日經、GVZ、黃金、銅金比、比特幣… | A |
| 745/621 | 2026-08-20 | 32 | fx-aud-usd / fx-usd-twd | A |
| 7249 | 2026-09-12 | 9 | WEI | **B（假缺口，已被 get_fred_csv.py 覆蓋，今天成功）** |
| 1650 | 2026-09-16 | 5 | us-put-call-ratio-total | **C（已有替代腳本但沒排程）** |

**關鍵觀察**：A 類（原 57 條，扣掉誤判的 4433 後為 **56 條**）裡，絕大多數最後成功日期集中在
**2026-08-19~08-20**，代表 M² Playwright 抓取本身大約從那時候就已經停止成功——**早於** 09-18 才出現的
orchestrator NameError，是兩個獨立問題（先有瀏覽器/session 層失效，一個月後才疊加 import bug）。

## 用戶決策（2026-09-22）：M² Playwright 這條路不再修

> 使用者明確裁示：**`get_m_square_series.py` 的 Playwright 登入/瀏覽器 session 問題不再嘗試修復，
> 因為 M² 這個資料源本身已經判定不可用**（不只是這次 session 失效，是整體放棄透過 M² 網站爬蟲取得資料的
> 策略）。後續 56 條真缺口一律走「找替代資料源」路線，不回頭修 Playwright／`google_session/auth.py`。
> 這與 `PLAN-2026-09-15-etl-refactor-m2-replacement.md` 和 `C:/code/2026-09-11-fincept-terminal` 早先
> 定的「去 M² 化」大方向一致——見下方第 3 節。

## 缺口分類總結

### A. 真正尚未被其他方式覆蓋（56 條，且不再靠 Playwright 補）
唯一入口原本是 `get_m_square_series.py` 的 Playwright 抓取，現已判定該路徑不再修復。
這 56 條全部需要另尋替代資料源——第 3 節整理了 `C:/code/2026-09-11-fincept-terminal` 裡現成可用的成果。

### B. 已有替代來源，但 `url_list` 忘記清掉的「假缺口」（4 條）
會被重複嘗試、浪費一次 Playwright 請求，但不影響最終資料，因為替代腳本今天都成功了：
- `sid 4` realgdp-yoy → `get_fred_csv.py`
- `sid 7249` WEI → `get_fred_csv.py`
- `sid 17586` sp500-eps → `get_official_xlsx.py`（今天成功，但上游 S&P archive 本身卡在 2025-04-01，這是資料源問題不是我們的抓取問題）
- `sid 4433` us-debt-severe-delinquency-student → `get_official_xlsx.py`（今天成功，n=106 沒變是因為 NY Fed 季頻報告本身還沒發布新一季，不是抓取問題；先前誤判成 A 類已修正）

### C. 已有替代腳本、但沒掛進 orchestrator、`url_list` 也沒清掉（1 條）
- `sid 1650` us-put-call-ratio-total → `get_cboe_pcr.py`（雙源管線，09-17 手動驗證 82 天 overlap 0% diff，
  見 `logs/pcr_*.log`）。目前只被手動跑過，**沒有掛進 `get_all_series_data.py` 的 `tasks`**，所以平常排程
  不會更新它；同時 `get_m_square_series.py` 的 `url_list` 也沒把它註解掉，會繼續徒勞嘗試 Playwright。

## 3. fincept-terminal 現有成果比對：56 條真缺口裡哪些已有現成方案

`C:/code/2026-09-11-fincept-terminal/` 是先前一輪「M² 去依賴化」偵察專案的成果庫（唯讀參考區，不在那裡寫
fetcher／不執行）。裡面已經把 M² 主批次 80 項＋附錄 A 22 項（合計 102 項，覆蓋今天盤點出的 56 條真缺口全部）
都做過資料源偵察與部分驗證，核心產出：

- **`migration/fetch_mapped.py`**（581 行）：`DISPATCH` dict，**50 個 sid 的完整可執行 fetcher**，已用
  `verify_mapped.py` 做過同日期尾值比對驗證（容差 2%）。
- **`migration/reference_fetchers/01_yahoo_finance.py`**：另外 5 個 sid（含 3 條在缺口清單內）的 Yahoo
  Finance chart API 抓法。
- **`migration/reference_fetchers/09_global_m2_composite.py`**：`sid 31742` 的四源合成草稿（FRED+ECB+BOJ+
  econdb），**尚未派工驗證**（`WN-2026-09-17-reference_fetchers派工落地-03至09波次進度.md` §4 明確標示
  「09 未派工」）。
- **`WN-2026-09-14-mapped-52-series-free-source-migration.md`**：`sid 484/1645`（Fed 升/降息機率）的研究
  結論是改用 PyPI `cme_fedwatch` 套件+FRED，**已實測成功但程式碼沒有寫進 `fetch_mapped.py`**，需要照 WN
  §4d 重新實作。
- `.env` 已經有 `EIA_API_KEY`、`CONFERENCE_BOARD_ACCOUNT`、`CONFERENCE_BOARD_PW`（本專案 `.env` 已確認存在
  這些 key，值未檢查）——代表 854/19080（EIA）、374/376（Conference Board ESF API）需要的憑證已經到位，
  不需要再跟使用者要一輪。

### 3.1 56 條缺口逐一比對結果

| 分類 | 條數 | sid 清單 | 備註 |
|---|---|---|---|
| **① 現成可執行、已驗證，可直接搬** | 46 | 2, 4934, 486, 7148, 8219, 854, 19080, 483, 4456, 2018, 29123, 7449, 131, 348, 562, 385, 745, 621, 755, 634, 386, 1281, 7147, 485, 75, 7359, 560, 246, 254, 255, 22910, 44, 37, 34, 36, 4481, 319, 4249, 7145, 7146, 8297, 8298, 8296, 4407 | 來源見 §3.2；多數是 FRED `fredgraph.csv`／yfinance 一行接入 |
| **② 現成可執行，但標記 approx（口徑/精度有落差，要在 pkl metadata 標註）** | 6 | 4448, 1916, 3612, 18331, 22718, 3776 | 見 §3.3，實作時不能當 ok 用 |
| **③ 現成可執行，但 fred_id 有疑義，上線前要自己驗證** | 1 | 414 | `fetch_mapped.py` 目前寫 `SPCS20RSA`（SA 版，錯），應為 NSA 版，但兩份原始偵察文件對到底是 `SPCS20RNSA` 還是 `SPCS20NSA` 意見不一致，需自己打 FRED 查證 |
| **④ 有已驗證的可行方案，但程式碼還沒寫（只有研究結論）** | 2 | 484, 1645 | `cme_fedwatch` 套件+FRED，見 `WN-2026-09-14-mapped-52-series-free-source-migration.md` §4d |
| **⑤ 有草稿程式碼，但未派工驗證，需要先實跑確認** | 1 | 31742 | `09_global_m2_composite.py`，checklist 標 approx，程式碼內部註解卻寫 `[ok]`，兩者矛盾，需親自驗證再定案 |

46 + 6 + 1 + 2 + 1 = 56，剛好對上第 2 節盤點出的 56 條真缺口，逐一分類無遺漏。

換句話說：**56 條真缺口裡，53 條（① 46 + ② 6 + ③ 1）已經有現成、可執行、多數已驗證過的程式碼可以直接搬進
`get_m_square_series.py` 的後繼者；只有 484/1645（2 條）方向已知但要重寫、31742（1 條）要先跑一次驗證**。這是
一份非常扎實的存量成果，之前完全沒人把它跟 `get_m_square_series.py` 的實際缺口對起來過。

### 3.2 ① 直接可搬清單（46 條，來源檔案）

| 來源檔案 | 涵蓋的缺口 sid |
|---|---|
| `fetch_mapped.py`（FRED 一般型 `fetch_fred()`） | 75, 37, 34, 36, 22910, 254, 255, 755, 634, 319, 7449, 131, 348, 7359, 560, 44 |
| `fetch_mapped.py`（`fetch_246_splice()` 特殊拼接） | 246 |
| `fetch_mapped.py`（yfinance `fetch_yf()`） | 2, 486, 483, 562, 385, 745, 386, 621, 485, 1281, 4249, 7145, 7146 |
| `fetch_mapped.py`（CBOE CDN `fetch_cboe()`） | 7148, 4407, 7147 |
| `fetch_mapped.py`（Fiscal Data `fetch_tga()`） | 29123 |
| `fetch_mapped.py`（CFTC COT `fetch_cftc()`） | 8297, 8298, 8296 |
| `fetch_mapped.py`（`fetch_jpy10y()` 財務省 CSV） | 2018 |
| `fetch_mapped.py`（`fetch_jp_spread()` 美日10Y利差，依賴已抓的 2018 pkl） | 4456 |
| `fetch_mapped.py`（`fetch_eia()`，.env 已有 `EIA_API_KEY`） | 854, 19080 |
| `fetch_mapped.py`（`fetch_crack321()` 裂解價差公式） | 4934 |
| `fetch_mapped.py`（`fetch_cb_bci()` Conference Board ESF API，.env 已有帳密） | 374, 376 |
| `fetch_mapped.py`（`fetch_yf()` 近似 WTI 現貨） | 8219（用 `CL=F` 近似，非真正現貨價） |
| `fetch_mapped.py`（`fetch_yf_spread()` 銅金比） | 4481 |

### 3.3 ② approx 清單（6 條，實作時要標註差異，不能當 ok）

| sid | 名稱 | 近似方式 | 已知落差 |
|---|---|---|---|
| 4448 | 美德 10Y 利差 | FRED DGS10 − ECB 歐元區 10Y | ECB 歐元區整體 ≠ 德國單一國公債，口徑近似 |
| 1916 | 德國 10Y 公債殖利率 | ECB 歐元區 10Y 代打 | 同上，非真正德國 series |
| 3612 | 美國信用利差 | FRED `BAMLH0A3HYC`（CCC OAS）代打 | 口徑與 M² 原始「信用風險利差」定義可能不同 |
| 18331 | S&P500 站上 50MA 比例 | yfinance `^SPX` 指數層級 close/MA50 | 口徑差非同一指標：新值是指數本身 vs 50MA（99-107%），舊 pkl 是成分股 breadth（51-64%） |
| 22718 | S&P500 站上 200MA 比例 | 500 檔成分股批次算 breadth | 中位差 6.85%，系統性偏高 |
| 3776 | CRB 指數 | yfinance `DJP`（iPath BCOM ETN）代打 | CRB 免費源已死；DJP 走勢同籃子但量級完全不同（$50 vs 397） |

## 4. 後續工作建議（按優先序，取代原本的「修 Playwright」路線）

1. **把 `fetch_mapped.py` 的 46 條①類 fetcher 搬進 `C:/code/2025-12-05-MacroMicro-Data`**，比照
   `get_fred_csv.py`／`get_official_xlsx.py` 的既有風格拆成新的 `get_*.py`（或直接複用其中已有的
   `fetch_fred`／`fetch_yf` 型態的 helper），寫完後掛進 `get_all_series_data.py` 的 `tasks`，並把
   `get_m_square_series.py` 的 `url_list` 裡對應 sid 註解掉。**注意**：`fetch_mapped.py` 裡的
   `_save_series`／`save()` 邏輯要換成本專案既有的「merge 不覆寫」防呆模式（07 CBOE PCR 那次已經因為
   「無腦覆寫」造成 5683/17586/267 資料倒退兩次，見 §1 踩坑紀錄）。
2. **6 條②類 approx** 同批搬，但要在 pkl 或 registry metadata 標 `approx=true` 並附差異說明，不能跟 ok
   的資料混為一談。
3. **`sid 414`** 上線前先自己打一次
   `https://fred.stlouisfed.org/graph/fredgraph.csv?id=SPCS20RNSA` 和 `...id=SPCS20NSA`，確認哪個是真的
   有資料的 series，不要照抄任一份矛盾的舊文件。
4. **`sid 484/1645`**：照 `WN-2026-09-14-mapped-52-series-free-source-migration.md` §4d 的結論重新實作
   `cme_fedwatch` + FRED 版本（免費結算 feed 只留約 5 個交易日，需要每日累積長序列）。
5. **`sid 31742`**：`09_global_m2_composite.py` 先實跑一次驗證（四源：FRED M2SL / ECB BSI / BOJ 統計検索 /
   EconDB M3CN），確認是否真的達到 ok，而不是照搬 checklist 表格裡的 approx 標記或程式碼註解的 `[ok]`——
   兩者互相矛盾，要自己跑一次才能下結論。
6. 把 `get_cboe_pcr.py` 的 `fetch_cboe_pcr_main` 掛進 `get_all_series_data.py` 的 `tasks`，讓 `sid 1650` 走
   排程而非手動跑。
7. 清理 `get_m_square_series.py` 的 `url_list`：註解/移除 `sid 4`、`7249`、`17586`、`4433`、`1650`（已有
   替代來源，留著只是白跑 Playwright；而 Playwright 這條路本身已經不再修，所以這些殘留條目遲早都要清）。
8. （非阻塞）`sid 5683` TWSE PE ratio：本月報表視窗（~17 點）沒有比既有 pkl（70 點）更新的日期，防呆機制
   正確擋下覆寫，不是 bug。如果希望每月自動累積歷史，`_fetch_5683` 需要改成「merge 進舊資料」而不是
   現在的「整批覆寫」邏輯。

## 檔案路徑

- orchestrator（已修復 import）：`C:/code/2025-12-05-MacroMicro-Data/get_all_series_data.py`
- M² series 清單：`C:/code/2025-12-05-MacroMicro-Data/get_m_square_series.py`
- CBOE PCR 替代管線（尚未排程）：`C:/code/2025-12-05-MacroMicro-Data/get_cboe_pcr.py`
- fincept-terminal 主檢查清單：`C:/code/2026-09-11-fincept-terminal/migration/M2_REPLACEMENT_PREP_CHECKLIST.md`
- 50 sid 完整可執行 fetcher：`C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py`
- 分組參考程式碼（9 檔）：`C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/`
- 484/1645 研究結論：`C:/code/2026-09-11-fincept-terminal/WN-2026-09-14-mapped-52-series-free-source-migration.md`
- 本次完整重跑 log：`C:/code/2025-12-05-MacroMicro-Data/logs/manual_run_2026-09-22.log`
- error 歷史：`C:/code/2025-12-05-MacroMicro-Data/logs/error_history.json`
