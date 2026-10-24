# WN-2026-10-24 左尾風險：lieta-goldmine 端點接入實作

> 前置：`WN-2026-10-23-左尾風險快速重新定價-指標盤點.md`（下稱「盤點 WN」）
> 素材：`C:\code\2026-09-09-new-lieta-goldmine\research\*\RESEARCH-*.md`（2026-09-16～09-19 研究，vix-term、hv 在 10-01 複驗過，UI 和 schema 都沒變）
> 目的：從 goldmine 研究過的 25 個分頁端點裡，挑出能補盤點 WN 缺口的端點，定下抓取、落地和接進本 repo 的做法。

---

## 0. 現況：盤點 WN 的 P0 進度（2026-10-24 工作區，尚未 commit）

| P0 項目 | 狀態 | 位置 |
|---|---|---|
| 1. `get_gex_series.py` 擴充 qqq/smh/xlk/xle/tlt/ZN/ZF | 已改 | `NO_SPOT_TICKERS`，只匯出不依賴 spot 的序列 |
| 2. `.CORR` 衍生表達式 | 已改 | `highcharts_utils.py:554` `process_corr`；`McElligott波動率微結構.py:321` 已用 `2:ret~cboe_TNX.CORR20` |
| 3. yfinance 加 QQQ/SMH/XLK/XLE/IGV/TLT/HYG/LQD | 已改 | `get_yfinance_series.py:144` |
| 4. FRED 加 HY OAS、損益兩平 | 已改 | `get_fred_csv.py:301` 起（sid 95001～） |

所以本 WN 只處理 P0 之後剩下的缺口，以及 goldmine 能補的兩個資料品質問題（盤點 WN §5 的 1、2）。

### Phase 0 / 階段 1 審查結論（2026-10-24）

- 探測報告：`C:\code\2026-09-09-new-lieta-goldmine\research\left-tail-probe\RESEARCH-left-tail-probe.md`（§6 欄位名、§7 日期語意、§8 對實作的影響）。本 WN 下列各節已依它的實測結果更新。
- 階段 1 審查報告（Opus，唯讀）：`C:\Users\chendoit\AppData\Local\Temp\claude\C--code-2025-12-05-MacroMicro-Data\f29296e3-e15a-464a-a122-8b62a9640254\scratchpad\orca-sub\rv-stage1\review.md`。探測結論都有 raw 檔支持，可進下一階段。
- 已修正（`get_lieta_eod_series.py`）：iv/rv/vrp 改 vol 點（×100）；`lieta_vx_contango_30d` 在 VX1 dte>30 時用 VIX 現貨內插；VX1／VX2 排除 dte<1；VIX 比 vx 晚時寫 warning；title 補單位與正負號。
- 日期主鍵一律是資料所屬交易日（as-of）；screener 列日期 D 的 spot 是 D 前一個 NYSE 交易日的收盤，落地時的 `date` 已換成 as-of。

### 階段 2 審查結論（2026-10-24）

- 審查報告（Opus，唯讀）：`C:\Users\chendoit\AppData\Local\Temp\claude\C--code-2025-12-05-MacroMicro-Data\f29296e3-e15a-464a-a122-8b62a9640254\scratchpad\orca-sub\rv-stage2\review.md`。三項必修：(1) `vx_curve` 從 2026-04-06 起 settlement 是前一交易日的結算價，整段晚標一天；(2) `iv_rv` 的 label 是前一交易日收盤的資料，iv、rv 都要 as-of = 前一交易日；(3) 每日排程只抓一天，延遲或失敗的那天會永久缺資料，改抓最近 5 個交易日。
- 驗收會漏掉錯位的根因：階段 1 只拿 lieta 回應驗 lieta，沒對照外部市場資料，而且 vx 對 VIX 全期相關 0.949 被 pre 區間蓋過去。已改成固定三項外部對照驗收（見 §4 Phase 1）。
- S0 複核（Opus，fix2）結論：其他複核項全過；一項必修——vx 的 as-of 位移不能按日期一刀切，lieta 的快照格式逐日會變（2026-09-23 的回應是舊格式，被錯移到 as-of 09-22）。已由 fix3 改成逐份回應判斷格式（`vx_format`，fetch_log note 記 `fmt=prev` / `fmt=same`），並用統一規則（回應 D 的 prev_settlement ＝ 前一交易日的結算價）補 as-of D−1，順便補上 7 個到期前一交易日缺的 VX1（J6 18.60、K6 17.62、M6 16.12、N6 17.04、Q6 15.87、U6 17.03、V6 17.22）。`vx_curve` 加 `src` 欄。
- 1m RV 口徑確認為 30 日 RMS（不是 `RVOL20`）；goldmine 端的 as-of 位移與排程修正由 goldmine 那邊做，本 repo converter 只補 regime／離群值 warning 與 title。

### S1 審查結論與 fix4（2026-10-24）

- 審查報告（Opus，唯讀）：`C:\Users\chendoit\AppData\Local\Temp\claude\C--code-2025-12-05-MacroMicro-Data\f29296e3-e15a-464a-a122-8b62a9640254\scratchpad\orca-sub\rv-s1\review.md`。fix3（vx 逐份判斷格式）複核通過；hist_skew、term 的 as-of 移位方向正確；converter 序列獨立重算吻合。兩項必修：
  1. **lieta term 的 `atm_iv` 不是 ATM**：它是同到期日 50Δ IV 的 1.14～1.16 倍（VIX 型口徑，30 天內插值約等於 VIX − 1），所以 `p25/atm` 被污染，原驗收 A（對 `gex_spx_put_skew_1m` 相關 > 0.8）與第 9 條都量錯了分母。改用 `p25/p50`（50Δ put 當 ATM 代理）。
  2. **term 每日流程會產生永久缺口與遺失原始檔**（`--force` 覆蓋 EOD 原始檔、as-of 缺口是結構性的、SPX EOD 快照品質差）。goldmine 端的修正（`term_iv` 主鍵加 `premarket`、原始檔命名加回應日期與快照類型、as-of 完整性檢查）由 `fix4-fetcher` 處理，見 goldmine 端文件。
- 本 repo 端 fix4 做的事：converter 新增 `lieta_{t}_p25_p50_1m`、term 壞值過濾（到期日層＋快照層）、`premarket=1` 優先／`premarket=0` 暫定並寫 sidecar `data/lieta_term_meta.json`；route 第 9 條改新公式、gex 序列標「資料日 = 序列日期 − 1 交易日」、延遲判斷基準與分組容忍天數、term 圖註與 EOD 暫定標示；測試補每條條件的符號與閾值案例，並做變異驗證。
- **決策（協調者暫定，保守、可回復；待使用者確認）**：
  1. term 正式值 = `premarket=1` 快照；`premarket=0`（EOD）只當「暫定最新點」，圖註與總覽標「⚠EOD暫定」，隔一個交易日被 `premarket=1` 版取代。理由：歷史 1206 份 SPX 快照全是 `premarket=1`，同一條線前後一致；SPX EOD 快照品質較差（夜盤報價稀薄，近端 15% 到期日 p25 < atm）。若使用者要以 EOD 為正式值，至少要加 SPX EOD 品質閘門。
  2. 第 9 條改為 `pctl1y(lieta_qqq_p25_p50_1m − lieta_spx_p25_p50_1m) > 85` **且** `lieta_qqq_put_skew3m_pctl1y > 85`（見 §3.2）；不再用「> 0」的絕對門檻。
  3. 快照層壞值過濾只套用 SPX（見 §3.1 備註），這是對合約字面（全部 ticker）的偏離，待確認。

---

## 1. 可用端點篩選結果

全部端點都在 `https://backend.lieta.io/api/...`，要帶 `Authorization: Bearer <JWT>`（Clerk 短效 JWT，由 CDP 9333 的 Chrome 攔 app 請求取得）。

### 1.1 採用

| 優先 | 端點 | 補盤點 WN 哪一格 | 歷史回補 | 研究檔 |
|---|---|---|---|---|
| **L1** | `GET /option_vol/vx_data?date=YYYYMMDD&session_type=eod` | §3-A「VIX 期貨 VX1/VX2 期限結構」⬜ | `date` 可帶，**最早能回到哪天未測** | `vix-term/` |
| **L2** | `GET /gex_screener/screener?tickers=...&date=YYYYMMDD&sort_by=net_gex&limit=50` | §5-1 spot 停更、§3-B「現貨對 flip 的距離」🔧 | `date` 可帶，但**部分日期 rows=0**（見 §4） | `gex-screener/` |
| **L3** | `GET /option_vol/iv_rv_series?ticker=X&maturity=1m&range_param=1y` | §5-2 rvol 全 NULL；§3-A QQQ/SMH/XLK IV 🟡 | **一次給 1 年日序列**，第一次跑就有歷史 | `equity-vault-dashboard/` |
| **L4** | `GET /option_vol/hist_skew?ticker=X&maturity=3m&range_param=1y` | §3-A QQQ/SMH/XLK skew 🟡 | 一次給 1 年（skew、call_skew、put_skew） | `equity-vault-dashboard/` |
| **L5** | `GET /models/eod/term/{TICKER}?date=YYYYMMDD` | §3-A 科技股 25Δ put skew 與期限結構 | `date` 可帶，**CME 0915 / 0916 回同一份，要確認是否真能回補** | `term-smile/`、`legacy-cme/` |
| L6 | `GET /option_vol/sectors_vol_info?date=YYYYMMDD` | §3-F 槓鈴兩腿的 vol（XSD 半導體、XOP/XES 能源） | `date` 可帶，08-15 → 回 08-14，**可逐日回補** | `sector-vol/` |
| L7 | `GET /trend/dsi?date=` 、`/trend/rrg?date=&days=100` | §3-F 槓鈴兩腿同時轉弱（SMH、XLE、IGV、HYG、JNK、TLT 都在 65 檔內） | rrg `days=100` 一次 100 天 | `relative-strength/` |
| L8 | `GET /option_flow/screener?tickers=X&sort_by=total_premium&limit=200` | 盤點 WN §7「期權大單只能看文章」→ 改成自己留每日快照 | `date` 可回補，實測最早到 2025-06-02（Phase 0 探測） | `option-screener/` |

### 1.2 不採用（理由）

| 端點 | 理由 |
|---|---|
| `market/complacency/` | 就是 VVIX/VIX 加 50DMA ±1.67SD，本 repo 有 `cboe_VVIX`、`cboe_VIX`，本地算比較穩（見 §3.4） |
| `market/corr_matrix` | 只給回看視窗內的單一數字，不是時間序列；本地 `.CORR` 已經能做 |
| `equity_vault/prediction/*`（hv 頁） | 無 `date` 參數、只給最新；rolling HV 用 L3 的 rv 即可 |
| `economic-quadrants` | 月頻成長/通膨象限，和「2027 年後成長左尾」有關，但更新慢，先不接 |
| `sector_flows/*` | 週頻資金流 Z 分數，擁擠度參考價值低於 CFTC TFF（盤點 WN P1-5） |
| calendar、seasonality、index-arbitrage、metronome、monitor-*、options-calculator、oi、flow-feed | 和左尾監控無直接關係，或是盤中逐筆資料 |

---

## 2. 架構

沿用 `get_gex_series.py` 讀 `C:\code\2026-03-24-GEX-lieta\gex_analysis.db` 的模式：**抓取放在 goldmine（登入、CDP、JWT 都在那邊），本 repo 只讀它產出的 DB 轉成 pkl**。

```
goldmine（C:\code\2026-09-09-new-lieta-goldmine）
  fetch_eod_metrics.py  ← 新增
     ├─ 沿用 fetch_history.grab_auth_token / fetch_json
     ├─ 沿用 build_history_db.Client 的 token 失效重取 + 重試寫法
     ├─ 原始 JSON → impulse/eod_raw/<endpoint>/<date>_<ticker>.json.gz（保底，可重解析）；
     │    term 的檔名含請求日、回應日期、快照類型（`{請求日}_{ticker}_r{回應date}_pm{0|1}.json.gz`），不可被覆蓋，`--reparse` 讀全部版本
     └─ 解析後 upsert → eod_metrics.db（SQLite）

本 repo
  get_lieta_eod_series.py  ← 新增
     └─ 讀 eod_metrics.db → data/lieta_*.pkl（格式同 _save_pkl：{"title", "data": [[datetime, float], ...]}）
  flask_highcharts route「左尾風險監控」（盤點 WN P1-7）直接用這些 id
```

### 2.1 goldmine 端：`fetch_eod_metrics.py`

用法：

```
.\venv\Scripts\python.exe fetch_eod_metrics.py                 # 沒給日期：最近 5 個交易日，全部端點（已 ok 的跳過）
.\venv\Scripts\python.exe fetch_eod_metrics.py 20260901-20261023 --only vx,screener,sectorvol   # 回補有 date 參數的端點
.\venv\Scripts\python.exe fetch_eod_metrics.py --only ivrv,skew  # 一次拉 1 年
  --pause S   請求間隔（預設 0.7，同 build_history_db）
  --force     已有資料也重抓
```

- 已有 `(endpoint, date, ticker)` 就跳過，中斷後同參數重跑即可（同 build_history_db 的 catalog 邏輯）。vx 回應 resolved ≠ requested 時不算完成，下次可重抓；沒給日期抓最近 5 個交易日，補上 lieta 延遲或失敗的那天。
- 最後一行印 `SUMMARY ok=.. empty=.. failed=..`；有 failed 時 exit 1。
- 每天 log：`impulse/fetch_eod_metrics_<date>.log`。
- 回補超過幾分鐘時，依全域規則用 `launch_hidden.ps1` 起獨立程序，再用 Monitor 追 log。

### 2.2 `eod_metrics.db` 資料表

全部用長格式，主鍵包含日期，避免同一天重抓時重複寫入。

| 表 | 主鍵 | 欄位 | 來源 |
|---|---|---|---|
| `vx_curve` | date（**as-of**：**逐份回應判斷格式**——dte ≥ 1 且 settlement、prev_settlement 皆有值的列中 settlement == prev_settlement 過半 ＝ 新格式，非到期合約 = 前一交易日；否則舊格式，同日；dte=0 的 SOQ 列留在 query.date。統一規則：回應 D 的 prev_settlement ＝ 前一交易日的結算價，故任何格式都用它補 as-of 前一交易日，包含到期前一天的 VX1（dte 0 列的 prev_settlement → as-of D−1、dte 1））, symbol | expiration, dte（以 as-of 重算）, settlement, prev_settlement, open, high, low（新格式回應，as-of 那列的 OHLC 屬 query.date 盤中，存 NULL）, **src**（`same` ＝ 同日結算列、`prev` ＝ 新格式位移列或 prev_settlement 補列；`same` 永遠勝過 `prev`，與寫入順序無關） | L1（`difference`、`contango_pct` 定義不明，**不存**，改自算） |
| `gex_screener` | date（**as-of**＝回應 `resolved_date` 的前一個 NYSE 交易日）, ticker | spot_price, net_gex, regime_raw, gamma_flip, flip_distance_pct（落地值＝−原始值，**負＝現貨低於 flip**）, flip_distance_pct_raw（回應原始值，正＝現貨低於 flip，供稽核）, call_wall, put_wall, skew_pctl_1m, put_skew_pctl_1m, protection_cost_25_1m, protection_cost_spread_25_10_1m, rv_trend, is_stale（resolved_date ≠ 請求日或回傳 ticker 數 < 清單數時為 1）, src_date | L2（字串數字一律 `float()`） |
| `iv_rv` | date（**as-of**：列 label 先用 NYSE 日曆濾掉非交易日，再取 `prev_trading_day(label)`）, ticker, maturity | iv, rv（1m rv = 30 日 RMS，3m = 90 日） | L3（每次全量 upsert，後抓的覆蓋先抓的） |
| `hist_skew` | date（**as-of**：列 `label` 先用 NYSE 日曆濾掉非交易日，再取 `prev_trading_day(label)`；與 iv_rv 同一套錯位，QQQ／SPX／TLT 實測 lag −1 最強）, ticker, maturity | skew, call_skew, put_skew | L4 |
| `term_iv` | date（**as-of**：`premarket=1` 快照 = `prev_trading_day(回應 date)`；`premarket=0`（EOD）快照 = 回應 `date`，與隔天 `premarket=1` 那份同一個 as-of）, ticker, expiration, **premarket**（主鍵含 premarket，兩版本並存，不互相覆蓋） | dte（以 as-of 自算）, c25_iv, p25_iv, c50_iv, p50_iv, atm_iv。**`atm_iv` 不是 ATM**：VIX 型口徑，約為同到期日 50Δ IV 的 1.15 倍；ATM 的代理用 `p50_iv` | L5 |
| `sector_vol` | date, ticker | iv_latest, iv_percentile, rv_latest, rv_percentile, iv_minus_rv_spread | L6 |
| `trend_dsi` | date, ticker | score_1d/3d/1w/1m, trend_1d/3d/1w/1m | L7 |
| `flow_top` | date（`query.date`）, id | query_ticker, ticker, expiration, strike, option_type, dte, volume, open_interest, premium, contract_direction, otm_pct, underlying_price, iv | L8（只存 premium 前 200） |
| `fetch_log` | endpoint, date, ticker | status(ok/empty/failed), resolved_date, fetched_at | 所有端點 |

term 的 as-of 規則：converter 對每個 (as-of, ticker) **優先取 `premarket=1`，沒有才取 `premarket=0`（暫定）**；converter 查詢只用 `date,ticker,expiration,premarket` 欄，不假設主鍵，所以現行 DB（主鍵不含 premarket）與新 DB（含 premarket）都能讀；沒有 `premarket` 欄時視為 1。goldmine 端每次跑完檢查最近 5 個交易日每個 as-of 都有資料，缺 as-of A 就強制請求 next_td(A)，缺口記入 `fetch_log` 與 SUMMARY `asof_gaps=…`。

`resolved_date` 一定要存：多數端點遇到非交易日或資料未更新會自動回退（sector-vol 08-15→08-14、gex-screener 09-16→09-15），**主鍵要用 `resolved_date`，不是請求的 date**，不然同一份資料會被存成兩天。

### 2.3 Ticker 清單

| 端點 | Tickers |
|---|---|
| L2 gex_screener | SPX, QQQ, SMH, XLK, XLE, TLT, NVDA, AVGO, META, ORCL, CRWV（一次請求） |
| L3 iv_rv | SPX, QQQ, SMH, XLK, XLE, IGV, TLT, HYG（每 ticker 一次）。SMH、IGV 的歷史從 2026-01 中旬起（SMH 01-13、IGV 01-14），不是整整 1 年 |
| L4 hist_skew | SPX, QQQ, SMH, XLK, XLE, IGV, TLT（**不抓 HYG**，樣本太少沒有意義；每 ticker 一次） |
| L5 term | SPX, QQQ, SMH, TLT |
| L8 flow_top | SPX, QQQ, SMH（VIX 能不能查，Phase 0 驗） |

---

## 3. 本 repo 端：序列 id 與衍生指標

### 3.1 `get_lieta_eod_series.py` 產出

| 序列 id | 定義 | 盤點 WN 對應 |
|---|---|---|
| `lieta_vx1`、`lieta_vx2` | 依 dte 排序取第 1、2 個合約的 settlement（每日換月，不連續合約） | §3-A |
| `lieta_vx1_vx2_spread` | VX1 − VX2；**> 0 = 前端倒掛** | §3-A |
| `lieta_vx1_vix_basis` | VX1 − `cboe_VIX`（現貨高於期貨 = 恐慌在現貨） | §3-A |
| `lieta_vx_contango_30d` | **百分比**：(30 天期貨價 ÷ VIX − 1) × 100。30 天期貨價以 dte 線性內插；VX1 dte > 30 時改用 VIX 現貨（dte=0）和 VX1 內插：F30 = VIX + (VX1 − VIX) × 30 / dte1；全部合約 dte < 30 時不外推（該日無點） | §3-A |
| `lieta_{t}_spot`、`lieta_{t}_flip_dist_pct` | gex_screener 的 spot_price、flip_distance_pct；日期為 as-of。`flip_dist_pct` 單位 %，**<0 ＝ 現貨跌破 flip**（lieta 原始值正負相反，fetcher 已取負） | **§5-1 停更問題的替代來源** |
| `lieta_{t}_regime` | +GEX=1、NEUTRAL=0、−GEX=−1 | §3-B |
| `lieta_{t}_protection_cost_1m` | 25Δ put 保護成本；單位是**占現貨比例**（SPX 0.0115 ＝ 1.15%），不是 % 數字 | §3-A 翼部需求（價格面） |
| `lieta_{t}_iv1m`、`lieta_{t}_rv1m`、`lieta_{t}_vrp` | iv、rv、iv − rv；單位 **vol 點**（lieta 原始值是小數，converter 已 ×100，同 `gex_*_iv30`）；日期為 as-of（label 前一交易日）；rv1m = **30 日 RMS**（log 報酬、不去均值、×√252），解析度約 1 vol 點，單日尖刺 converter 只寫 warning 不刪點 | **§5-2 rvol NULL 的替代來源** |
| `lieta_{t}_put_skew3m`、`lieta_{t}_skew3m` | hist_skew | §3-A 科技股 skew |
| `lieta_{t}_p25_p50_1m`（`{t}` = spx qqq smh tlt） | term 表 dte 線性內插到 30 天的 `p25_iv` ÷ `p50_iv`（不外推；排除 dte < 1 與缺值，同一組到期日）。**50Δ put 當 ATM 代理**；與 gex `put_25d_iv / ((put_50d_iv + call_50d_iv)/2)` 的 1m bucket 同方向，SPX 水準相關 0.980 | 第 9 條的量；SPX vs QQQ 可直接比 |
| `lieta_{t}_p25_atm_1m` | 同上但分母用 lieta 原 `atm_iv`。**不是 ATM**（VIX 型口徑），與 `gex_spx_put_skew_1m` 口徑不同（lieta 約 1.05、gex 約 1.21，水準相關 0.2～0.6），不可互比；僅供參考 | 舊版第 9 條的量（已停用） |
| `lieta_{t}_p25_atm_1m_bucket` | dte 22–35 各到期日 p25/atm 先相除再平均（gex 的 bucket 口徑），驗收對照用 | – |
| `lieta_{t}_term_slope` | ATM IV（~9 天）− ATM IV（~90 天），vol 點；atm 用 lieta 原值（VIX 型口徑，title 已註明） | 前端恐慌 |
| `lieta_xsd_iv`、`lieta_xop_iv` | sector_vol 的 iv_latest（XSD = 半導體、XOP = 油氣探勘，以 ETF 發行商定義為準），單位 **vol 點**（lieta 小數 ×100）。lieta 只給 2 位小數（0.43 = 43 vol 點），**解析度 1 vol 點**，title 已註明；date 為 as-of（回應 date 的前一交易日，converter 照抄） | §3-F 槓鈴兩腿 vol |
| `lieta_xsd_ivpct`、`lieta_xop_ivpct` | sector_vol 的 iv_percentile，**0–1 原值**（不是 0–100）。原稿的單一序列 `lieta_xsd_xop_ivpct` 拆成這兩條，第 7 條輔助條件為**兩者皆 > 0.8** | §3-F |
| `lieta_{t}_dsi_1w`（`{t}` = smh xle xlk igv hyg jnk tlt spy qqq） | trend_dsi 的 score_1w（0–10，量化成幾個檔位，多為 0 或 10；方向在 `trend_1w` 欄，這裡只畫強度）。date 不位移（當日）。SPX 不在 DSI 清單，用 `spy`。route 只畫 SMH／XLE／IGV 當參考圖，不納入條件 | §3-F |
| `lieta_{spx,qqq}_deep_otm_put_premium` | flow_top 每個 query_date 的**深價外 put 權利金合計**（`is_deep_otm_put=1`，即 option_type P 且 OTM > 10%；SPX 含 SPXW），單位百萬美元；date = query_date（當日，不位移）。舊 schema 沒有 `is_deep_otm_put` 欄時退回 P 且 `otm_pct > 10` | §3-A 翼部需求（flow 面） |
| `data/lieta_flow_top.json`（sidecar） | 各 ticker（SPX、QQQ）最新 query_date 的 premium 前 20 大：ticker、option_type、strike、expiration、dte、otm_pct、premium、volume、contract_direction、is_deep_otm_put，加 query_date 與 underlying_price（前 20 大列的中位數）。route 用它畫表格 | – |

`{t}` 小寫，例如 `lieta_qqq_flip_dist_pct`。

term 序列的附加行為（`get_lieta_eod_series.py`）：
- **壞值過濾**（合約補充 #3 第 6 點）：到期日層——`atm` 或 `p25` > 1.0，或 `p25/p50` 不在 [0.8, 2.0]，該到期日整個丟掉；快照層——dte 7–60 的到期日中 `p25 < p50`（或 `p25 < atm`）的比例 > 20%，整份快照不輸出（四條序列都沒有該日的點，不改用另一個版本）。兩層都寫 warning（`bad expiries dropped` / `bad snapshots dropped`）。測試覆蓋 review 列的壞日：SPX as-of 2025-11-26 dte 5 atm 4.4184、as-of 2024-06-28 dte 40 atm 2.0072，以及 SPX 2022-01、2023-08、2025-04 的壞快照（review 列的是請求日 20220104/06/10/11/12/14、20230828/29/30、20250428，落地 as-of 為前一交易日；本 DB 實測濾掉 9 份）。
- **快照層只套用 SPX**（`TERM_SNAPSHOT_FILTER_TICKERS`）：偏離合約字面，原因是實測合約的 `p25 < p50` 規則抓不到 SPX 的壞快照（它們 p25 < **atm**），反而會誤刪 TLT 的正常快照（TLT put skew 本來就可能反向，14～20 份）；QQQ／SMH 的 `p25 < atm` 是 lieta atm 口徑造成，不是壞資料。其他 ticker 只寫 warning（`suspicious snapshots (kept …)`）。要照字面全套，把常數改成 `TERM_TICKERS`。待使用者確認。
- **sidecar** `data/lieta_term_meta.json`：記每個 ticker 最後一個 as-of 日與哪些日期是 `premarket=0` 暫定點；route 讀它標「⚠EOD暫定」，沒有 sidecar 時 route 退化為不標。

### 3.2 盤點 WN §4 確認清單的更新

| # | 原條件 | 改用／新增 |
|---|---|---|
| 3 | 跌破 gamma flip | 改用 `lieta_spx_flip_dist_pct < 0` 且 `lieta_qqq_flip_dist_pct < 0`（落地時已取負，負 = 跌破；screener 原始值正負相反，fetcher 已取負），不再依賴停更的 `gex_*_spot_price` |
| 7 | 槓鈴兩腿同跌 | **主條件**不變：yfinance SMH/XLE 同日皆 < −1.5%。**輔助條件**（Phase 3 上線）：`lieta_xsd_ivpct` 與 `lieta_xop_ivpct` **都 > 0.8**（嚴格大於）。總覽顯示「主 ✅/⬜ ＋ 輔助 ✅/⬜/❓」，**兩者分開判斷**：狀態與「n/9 成立」計數只看主條件；輔助缺資料或延遲（L6 容忍 1 個交易日）標 ❓，不影響主條件；兩者各顯示自己的 as-of。DSI 圖（SMH、XLE、IGV 的 `dsi_1w`）只當參考圖，不納入條件 |
| **8（新增）** | VIX 期貨前端倒掛 | `lieta_vx1_vx2_spread > 0` 或 `lieta_vx1_vix_basis < 0`；文章的 VIX 11 月 25C 大單應該會反映在這裡 |
| **9（新增）** | 科技股 skew 比 SPX 陡 | **（S1 審查後改寫，待使用者確認）** `pctl1y(lieta_qqq_p25_p50_1m − lieta_spx_p25_p50_1m) > 85`，**且** `lieta_qqq_put_skew3m_pctl1y > 85`。百分位 = 過去 252 個觀測含當日內 ≤ 當日值的比例（樣本 < 126 不輸出）。原公式 `lieta_qqq_p25_atm_1m − gex_spx_put_skew_1m > 0` 不用：(1) lieta 的 atm_iv 是 VIX 型口徑，不是 ATM，分母錯；(2) lieta 與 gex 口徑差約 0.16，字面公式幾乎永遠 < 0；(3) 換成 p25/p50 以後 QQQ 只有 0.9% 的日子比 SPX 陡，「> 0」的絕對門檻沒有意義，要抓的是 QQQ 相對 SPX「異常地」變陡，所以用差的百分位。實測 > 85 的天數約 14%，觸發頻率合理 |

新增的證偽訊號：VX 曲線在 2–3 天內回到正價差（contango > 5%）。

route 判斷「延遲」的規則（S1 建議-4）：基準 = 最近一個已收盤的交易日（本 repo 沒有 NYSE 日曆工具，用 `series_2` 與 `cboe_VIX` 兩者較新的最後日期；兩者都停更時偵測不到）；容忍天數：lieta 的 screener／vx／iv_rv／hist_skew／**sector_vol（L6，前一日收盤組）** 與 FRED = 1，其他（含 lieta term、**dsi、flow**、gex_*、CBOE、ETF）= 0；落後超過容忍天數的條件顯示 ❓，不當成未觸發。第 2 條與第 9 條對照用到的 `gex_*` 序列，日期是 lieta 原始 date，as-of 顯示「資料日 = 序列日期 − 1 交易日」。term 圖註：「SPX 含夜盤變動，ETF 不含」（SPX 指數選擇權有夜盤，QQQ 等 ETF 選擇權沒有）。

### 3.3 資料品質替代

- `gex_*_spot_price` 停更：route 裡依賴 spot 的圖（`gex_spx_flip_distance`、`gex_spx_gamma_env`）改讀 `lieta_spx_flip_dist_pct`。**舊序列先不刪**，等 lieta DB 那邊修好再決定。
- `daily_vol_reference.rvol_*` 全 NULL：改用 `lieta_{t}_rv1m`；SPX 再用本地 RMS30（30 日 log 報酬、不去均值、×√252，label 前移一日）交叉比對口徑；route 要同口徑比較可用 `cboe_SPX.RVOL30`（不是 `.RVOL20`，lieta 的 1m RV 是 30 日窗口）。

### 3.4 本地自算：Complacency（取代 L 端點）

`cboe_VVIX / cboe_VIX`，50 日均線 ±1.67 個標準差（標準差取 ratio 本身 50 日）。跌破下緣標成 breakdown。上線前和 goldmine 的 `complacency_20250101_20260916.csv` 比對：50dma 誤差 < 1%、breakdown 日期大致相同，才算口徑一致。

---

## 4. 實作步驟

### Phase 0：探測（先做，決定後面能不能回補）

> 狀態：✅ 完成（`RESEARCH-left-tail-probe.md`，階段 1 審查通過）

用一支 `research/left-tail-probe/probe_left_tail.py`（goldmine 內）驗下列問題，結果寫 `RESEARCH-left-tail-probe.md`：

1. `vx_data` 往回最早到哪天：試 20260101、20250101、20240101。
2. `term/{TICKER}`：同一 ticker 帶 20260901、20261001、20261023，回應內容是否不同（研究時 CME 0915/0916 一樣，可能只回最新）。
3. `gex_screener`：
   - tickers 能不能放 SMH、XLK、XLE、ORCL、CRWV（研究時只測了 8 檔）；
   - 連續 20 個交易日逐日請求，算 rows=0 的比例；
   - 研究時 09-15 / 09-16 是空的、09-14 才有，要確認是「資料延遲一天」還是「隨機缺」。
4. `iv_rv_series` / `hist_skew`：`range_param` 能不能用 2y、5y；`maturity` 3m 有沒有；ticker 給 SMH/XLE/TLT/HYG 是否 200。
5. `option_flow/screener`：`tickers=VIX` 是否有資料。

驗收：每題都有實際 HTTP 狀態和列數，不用推測。

### Phase 1：L1 + L2 + L3（最值錢的三個）

> 狀態：✅ 完成（階段 2 審查三項必修、fix2／fix3 已修；vx 逐份判斷格式；S1 複核通過）

1. 寫 `fetch_eod_metrics.py` 骨架、`eod_metrics.db` schema、`fetch_log`。
2. 實作 vx、screener、ivrv 三個抓取器。
3. 依 Phase 0 結果回補：vx 能回補多遠就補多遠；screener 至少補到 2026-07-17（spot 停更起點）。
4. 本 repo 新增 `get_lieta_eod_series.py`，產出 §3.1 前三組序列。

驗收（階段 2 審查後，合約補充 #2 第 5 點；用外部市場資料對照，之後每個 Phase 都要跑）：
- (a) vx 日變動 vs `cboe_VIX` 同日日變動，相關 > 0.8；分 pre／post 2026-04-06 兩段各報一次。vx 的 as-of：query.date ≥ 2026-04-06 的非到期合約 = 前一交易日，OHLC 不寫進 as-of 那列。
- (b) `lieta_{t}_rv1m` vs 本地 RMS30（30 日 log 報酬、不去均值、×√252，label 前移一日）四捨五入到 2 位小數後吻合率 ≥ 95%。iv_rv 的 as-of = `prev_trading_day(label)`。
- (c) `lieta_spx_spot` vs `series_2`（SPX 收盤）同 as-of 日。
- 另：`vx_curve` 每個交易日 ≥ 7 個合約；dte 遞增；前端 4 個合約 settlement > 0。
- 日期語意用 as-of：screener 列日期 20261023 ＝ 10-22 收盤，`lieta_spx_flip_dist_pct` 在 as-of 2026-10-22 這一點為負，約 −1.13%（量級接近盤點 WN 的 (7663 − 7765) / 7765 ≈ −1.3%）。

### Phase 2：L4 + L5 + 確認清單上線

> 狀態：🔧 本 repo 端完成（converter、route、測試、變異驗證）；goldmine 端 `term_iv` 主鍵加 `premarket`／原始檔不覆蓋／as-of 完整性檢查由 `fix4-fetcher` 處理，完成後需重跑 `get_lieta_eod_series.py`、`accA.py`。

1. 實作 skew、term 抓取器與 §3.1 對應序列。
2. 「左尾風險監控」route（盤點 WN P1-7）納入 §3.2 的 9 條。
3. 本地 complacency（§3.4）。

驗收 A（S1 審查後改寫，合約補充 #3 第 4 點）：lieta `p25/p50` 的 dte 22–35 bucket（各到期日 p25/p50 再平均，DB 到期日列）vs gex `put_25d_iv / ((put_50d_iv + call_50d_iv)/2)` 的 1m bucket，**gex 日期往前移 1 個交易日**（gex 日期 = lieta 原始 date = as-of + 1）；水準相關 ≥ 0.95、日變動相關 ≥ 0.9。腳本 `accA.py`（唯讀、可重跑；scratchpad `orca-sub/fix4-repo/work/accA.py`）。
- **SPX 實測（2026-10-24，n = 547，2024-07-31～2026-10-21）：水準 0.980／日變動 0.941，通過**（converter 壞值過濾後 n = 546，一樣 0.980／0.941）。未移位只有 0.734／−0.233、移 2 日 0.748／−0.213，同時證明 as-of 移位方向正確。
- 原本拿 `p25/atm` 對 `gex_spx_put_skew_1m` 驗只有 0.21（同日）～0.59（最佳 lag）：不是內插或日期問題，是分母口徑（lieta atm_iv 是 VIX 型）。
- QQQ 同法（附帶，非驗收項）：水準 0.938／日變動 0.523。QQQ 的 dte 22–35 每天只有 1～2 個到期日，bucket 平均雜訊大；水準仍高度一致（gex 未移位 0.883、移 1 日 0.938、移 2 日 0.857），日期方向也對。
- 其他 Phase 2 驗收：test 全綠；route 載入 200、每張圖每條序列有資料；9 條逐條符號／閾值有假序列測試；13 個變異（route 8、converter 5）全部讓測試變紅。

### Phase 3：L6 + L7 + L8

> 狀態：✅ goldmine 端完成（S2：四個抓取器 + 回補，`PHASE3-驗收.md`）；✅ 本 repo 端完成（S2-repo：converter、route、測試、變異驗證，見下）

1. sector_vol 逐日回補 1 年、DSI 每日、rrg `days=100` 一次。
2. flow_top 每日快照；route 加一張表：當日 SPX/QQQ 權利金前 20 大，標出深價外 put（OTM > 10%）。

**本 repo 端實作（2026-10-24）**
- converter（`get_lieta_eod_series.py`）：`lieta_xsd_iv`、`lieta_xop_iv`、`lieta_xsd_ivpct`、`lieta_xop_ivpct`、`lieta_{smh,xle,xlk,igv,hyg,jnk,tlt,spy,qqq}_dsi_1w`、`lieta_{spx,qqq}_deep_otm_put_premium`、sidecar `data/lieta_flow_top.json`（§3.1）。表不存在或為空 → log info 略過；iv 壞值照 `_warn_outliers` 慣例只警告不刪。**date 照抄 DB（DB 已是 as-of），不再位移**。converter 改用 `mode=ro` 開 goldmine 的 DB。
- route（「左尾風險監控」，由 16 張變 19 張（含總覽））：
  - **⑦ 輔助圖**：XSD／XOP IV 百分位（plotLine 0.8）＋ IV（vol 點）；title 與圖註註明 XSD = 半導體、XOP = 油氣探勘、2 位小數 = 1 vol 點解析度。
  - **⑦ 參考：DSI 1W**（SMH、XLE、IGV，不納入條件）。
  - **② 翼部需求（三）參考：flow**（custom 圖）：折線 = SPX／QQQ 最近 120 個 query_date 的深價外 put 權利金合計；summary 內附 **SPX、QQQ 各一張權利金前 20 大表**（深價外 put 整列粉紅底粗體並標「🔻是」），表頭顯示 query_date 與「underlying 為該日收盤附近」的 as-of 說明（flow 是當日成交，不位移；與 screener／iv_rv 的前一日收盤不同族）。flow query_date 落後基準（容忍 0）標 ⚠延遲。表格放在 summary 區塊（沿用總覽與 `fx_case_charts.race_table` 的慣例，沒有表格型 chart 元件）。
  - **第 7 條**：主條件 + 輔助條件分開（§3.2）。原本的 `OPTIONAL_MISSING_CHECK`（輔助缺資料標註）機制移除，改由輔助條件自己判斷缺資料／延遲。
  - 順手修正 `_lag_td`：比較前先 normalize 日期（pkl 時間戳是 08:00，sidecar 的 query_date 是 00:00，不 normalize 會把同一天誤判成落後 1 日）。
- 今日（as-of 2026-10-23）第 7 條：**主 ⬜**（SMH +0.74%、XLE +2.60%）＋ **輔助 ⬜**（XSD 百分位 0.53、XOP 0.83；XOP 單腿 > 0.8，XSD 沒到，所以輔助不成立）。
- 測試：`venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider` → 129 項全綠（原 88）；新增四組新序列的轉換與 as-of、flow 表選取與深價外標記（假 DB，含舊 schema）、第 7 條主／輔助 ✅/⬜/❓ 各案例與延遲組別、flow 表／圖的延遲與缺 sidecar；16 個變異（route 9、converter 7：輔助 and→or、延遲不標 ❓、缺資料標 ⬜、閾值 >→>=、L6 容忍改 0、flow 不標深價外、`_lag_td` 不 normalize、輔助影響主狀態、趨勢不截 N 日、iv 不 ×100、sector_vol/dsi 日期位移、深價外判斷放寬、前 20 升冪、權利金單位、舊 schema OTM 門檻）全部讓測試變紅（`work/mutate.out`）。
- 驗收（pkl 層，`work/accept.out`；三項固定驗收重跑）：(a) VX1 日變動 vs `cboe_VIX`（跳過換月日）pre 0.943／post 0.890；(b) SPX rv1m vs 本地 RMS30 252/252 = 100%；(c) screener spot vs `series_2` 70/70；另 XOP／XSD IV 日變動 vs 本地 ETF（XLE／SMH 代，本地沒有 XOP、XSD）報酬：lag 0 最強（帶方向 −0.314／−0.464，lag −1／+1 只有 +0.015／+0.109、+0.141／+0.122），確認 pkl 層 as-of 沒錯位。

**已知限制（本 repo 端）**
- **L6 ticker 集合不穩**：sector_vol 在 15／26／27 檔間變動（XLK、XLE 只在 27 檔那組；2026-08-03～08-17 由 27 變 15、10-21 又出現 27 檔），**SMH 從未出現在 L6**，所以輔助條件用 XSD／XOP 而不是 SMH／XLE 本身；XSD／XOP 在兩組都有，缺漏的日子該點跳過。
- **來源洞**：sector_vol 2025-07-03 缺、2025-07-31～08-06 只有 1 檔（XTN）、2025-07-11／2026-08-04 不完整；dsi 2026-08-12 沒有資料；flow 2025-12-29 QQQ、2025-12-30 SPX／QQQ 為 0 列，2025-12-24 SPX（324 列）、2025-12-29 SPX（790 列）、2025-11-28 QQQ（1789 列）不足 2000，這幾天深價外 put 合計偏低。
- **2 位小數解析度**：`lieta_xsd_iv`／`lieta_xop_iv` 與 ivpct 都只有 2 位小數（iv ±0.5 vol 點），不適合細門檻；ivpct 的 0.8 門檻在 0.01 的格子上判斷。
- **sector_vol 最新一點是 provisional**：goldmine 取到的未來日標籤（20261026，as-of 2026-10-23）要等下一次排程（10-27）重抓，內容可能被改寫；之後要重跑 converter。
- **flow 合計的口徑**：只含 fetcher 留存的深價外 put（回應 premium 前 2000 筆內），不是全市場；`otm_pct` 正 = 價外、負 = 價內（遠期深價內 put 如 20000P 多半是合成部位，不是保護需求）。flow 回補從 2025-06-02 起（goldmine 未補 2025-01-23～06-01）。
- DSI `trend_1d` 約 3 根 K 棒平滑，不是單日報酬；各 ticker 檔數隨時間 63 → 65 變動。
- 本地沒有 XOP、XSD 收盤，as-of 驗證用 XLE、SMH 代理（相關偏低，但 lag 結構一致）。

### 排程

- 時間：台灣時間每週二到週六 08:30（美東前一交易日收盤後，避開晚上 `capture_multi.py` 用 9333 埠的時段）。
- 用 cron-job-agent 的 command 任務：先跑 goldmine 的 `fetch_eod_metrics.py`，成功才跑本 repo 的 `get_lieta_eod_series.py`。
- 9333 被占用（例如盤中擷取還沒關）時，腳本直接失敗並寫進 log，不要強行關 Chrome。

> 狀態（2026-10-24）：✅ 已建置、試跑成功、**已啟用**。cron-job-agent 任務 `left-tail-eod`（`tasks/left-tail-eod.yaml`、`jobs/left_tail_eod.py`）：`every: 24h`、`at: "09:00"`（調度器只在整點醒，WN 的 08:30 取下一個整點 09:00 台灣時間，仍在美東收盤後、晚上 `capture_multi.py` 時段之外）；台灣週日、週一略過；9333 被占用即 `fail()` 並寫 log，不關 Chrome；fetch（`failed=0` 才算成功）→ `get_lieta_eod_series.py` → `get_complacency_series.py` → `lieta_fetch_alert.py`。試跑（`--force --no-notify`，32 秒）：fetch ok=5 failed=0 asof_gaps=4（as-of 10-22 的 term，待下週一自然補上）。
> 告警：`lieta_fetch_alert.py`（本 repo）讀 `fetch_log`，連續 2 個交易日「全部 failed」（empty 不算）→ LINE＋Gmail，同事件一天一次；測試全用假 sender。**盲點**：JWT／登入過期、Chrome 起不來時 `fetch_eod_metrics.py` 只印 `SUMMARY … error=` exit 1、不寫 `fetch_log`，不會觸發此告警，改由 cron 任務本身 `notify.on_error`（Telegram，每天失敗就發）涵蓋；若要連續失敗升級，需 goldmine 在這類錯誤寫一筆 `fetch_log`（endpoint=`session`, status=`failed`）。

---

## 5. 風險與注意事項

1. **JWT 依賴登入狀態**：`.pw_profile/` 的 session 過期就整條斷掉。`fetch_log` 連續 2 天全部 failed 時要通知（沿用本 repo `line_notify.py` 或 `gmail_smtp.py`）。
2. **lieta 改版**：研究在 09 月，10-01 複驗 vix-term、hv 時沒變。其他端點沒複驗過，Phase 0 等於順便複驗。
3. **gex_screener 資料可用性不穩**：研究時同一週有兩天 rows=0。確認清單第 3 條在當天缺資料時，要沿用前一個有效值並在圖上標「延遲」，不能當成「未觸發」。
4. **口徑差異**：
   - lieta 的 gamma flip 和野村不同（盤點 WN：QQQ lieta 723–725、野村 715），只能看方向和相對距離。
   - `sector-vol` 研究檔的板塊對照有錯：**XSW 是軟體、XSD 是半導體、XTL 是電信**（研究檔寫 XSW=Semiconductor、XTL=Technology Hardware、XSD=Semiconductor Equip）。實作時以 ETF 發行商的定義為準。
   - `vx_data` 的 `difference`、`contango_pct` 定義不明，不使用。
5. **請求量**：每日約 1（vx）+ 1（screener）+ 15（ivrv 8、skew 7）+ 4（term）+ 1（sector）+ 2（trend）+ 3（flow）≈ 28 次，間隔 0.7 秒，1 分鐘內跑完。回補 1 年 vx + screener + sector 約 750 次，約 10 分鐘，要用獨立程序跑。研究時 correlation 頁被 429 打斷過兩次，回補時 `--pause` 至少 1.0。
6. **lieta 資料洞與日期錯位**：
   - lieta 資料洞：請求日 2025-04-23、2026-08-03 是正常交易日卻回 200 + 0 列（補跑仍空，接受並記錄）。**as-of 語意下缺的交易日是 2025-04-23 與 2026-07-31**（請求 20260803 的 settlement 屬 7 月 31 日；DB 的 vx_curve 缺的就是這兩個 as-of 日）。2026-09-23、09-24 前 4 檔結算價重複**不是 lieta 沒更新**，是位移規則誤判造成（20260923 的回應是舊格式，被當新格式錯移一天），已修（逐份判斷格式，2026-09-22 V6 17.36、X6 18.20；全期相鄰交易日前 4 檔全同的天數 = 0）。
   - vx／iv_rv 日期錯位曾經發生（vx 從 2026-04-06 起落後一個交易日、iv_rv label 比資料晚一天），在假訊號上實際觸發過（as-of 2026-10-22 的 `lieta_vx1_vix_basis` −0.79 → 對齊後 +0.35）。之後每個 Phase 都必跑 §4 Phase 1 的三項外部對照驗收。
7. **日期落差與延遲判斷**：vx 修正為 as-of 後，最新 as-of 是 D−1，與 `cboe_VIX` 對齊，converter 的「VIX 比 vx 晚」warning 自然消失；若仍出現，代表 vx 或 VIX 其中一邊沒更新。`lieta_vx1_vix_basis`、`lieta_vx_contango_30d` 最新一點可能比 `lieta_vx1_vx2_spread` 早一天（VIX 序列更新時間差）。route 每條序列都要顯示各自的 as-of 日期，不能拿「各序列最後一點」直接一起判斷（確認清單第 8 條尤其要注意）。screener 結構性落後一個交易日（列日期 D ＝ D 前一交易日收盤），判斷「延遲」要先扣掉這一天：用 `lieta_spx_flip_dist_pct` 最後日期 < `series_2` 最後日期判斷，不要依賴 `is_stale`（pkl 沒帶 stale 資訊）。

---

## 6. 待決

- `eod_metrics.db` 放 goldmine 根目錄還是 `impulse/`：建議放 `impulse/`，和 lake 同一層，備份時一起處理。
- L8 期權大單：flow `date` 可回補，實測下限 2025-01-23；已回補 2025-06-02 起（SPX、QQQ）。2025-01-23～06-01 未補（待使用者決定）。

### 待使用者決定／啟用（2026-10-24 交接時點）

1. **term 正式值＝premarket=1 快照、EOD 為暫定**（S1 審查建議，已實作且兩版並存，可回復）。
2. **第 9 條新公式**（§3.2）與驗收 A 改寫是否接受。
3. **第 7 條主條件**目前只判最近一日 SMH、XLE 同日 < −1.5%；盤點 WN 寫「連續多日」，是否改成近 N 日內同日達標 ≥ 2 天（目前只在總覽顯示近 5 日同日達標天數）。
4. term 快照層壞值過濾只套 SPX（要照字面全套，把 `TERM_SNAPSHOT_FILTER_TICKERS` 改成 `TERM_TICKERS`）；到期日層 `>1.0` 會丟掉 2025-04 關稅期 dte 1–4 的真實高 IV（只影響 `term_slope`）。
5. 是否要 goldmine 對登入／Chrome 失敗補寫 `fetch_log`（見排程盲點）。
6. 2026-10-26／10-27 之後複驗：term as-of 10-22 缺口是否自然補上（SUMMARY `asof_gaps=0`）、sector_vol 未來日標籤 provisional 是否被改寫（之後重跑 converter）。
7. vx／screener 的 raw 檔名仍會被同請求日重抓覆蓋（term 已改）。
