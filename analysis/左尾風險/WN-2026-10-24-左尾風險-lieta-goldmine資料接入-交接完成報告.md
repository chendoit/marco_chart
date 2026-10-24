# WN-2026-10-24 左尾風險：lieta-goldmine 資料接入——交接完成報告

> 規格：同資料夾 `WN-2026-10-24-左尾風險-lieta-goldmine資料接入實作.md`（各 Phase 狀態、決策、已知限制都已同步）；goldmine 端驗收彙總：`C:\code\2026-09-09-new-lieta-goldmine\research\left-tail-probe\PHASE-ALL-驗收.md`。

## 結論（先看這段）

S0～S4 全部完成，各階段 Opus 審查最後都是 PASS、沒有未處理的必修項。

- **資料層**：goldmine `fetch_eod_metrics.py` 現有 vx、screener、ivrv、skew、term、sectorvol、dsi、rrg、flow 九個抓取器，全部回補完成，`fetch_log` failed = 0；本 repo 兩支 converter 產出 133 個 `lieta_*`／`complacency_*` pkl。
- **route**「左尾風險監控」共 19 張（含總覽），確認清單 9 條都有；每條序列顯示自己的 as-of，延遲判斷扣掉結構性的一個交易日。目前總覽 6/9 成立。
- **排程**：cron-job-agent 任務 `left-tail-eod` 試跑成功（32 秒，fetch ok=5 failed=0），**已啟用**，台灣時間每天 09:00（週日、週一略過）。連續 2 個交易日全 failed 的告警已寫好，只用假 sender 測過，沒有對真實 LINE／信箱送過訊息。
- **三項外部對照最終數字**：vx 對 VIX 日變動相關 pre 0.943／post 0.890；rv1m 對本地 RMS30 吻合 252/252；screener spot 對 `series_2` 70/70。
- **有 7 件事需要你決定或確認**（見「待使用者決定／啟用」），其中最重要的是第 9 條改了公式、term 以 premarket=1 為正式值。

## 做了什麼（每階段一段）

**S0（fix3 複核）**：Opus 抓到 vx 的 as-of 位移不能按日期一刀切（2026-09-23 的回應是舊格式，被錯移）。`fix3-fetcher` 改成逐份回應判斷格式，補上 7 個到期前一交易日缺的 VX1；`vx_curve` 加 `src` 欄。as-of 2026-09-22 V6 = 17.36；as-of 2026-10-22 `lieta_vx1_vix_basis` 從 −0.79 變 +0.35（原本是假訊號）。多出的 as-of 2024-12-31（9 列 `src=prev`）經 Opus 審查確認合理。

**S1（Phase 2）**：goldmine 新增 `skew`、`term` 抓取器並回補（hist_skew 7 檔、term SPX 2022-01-03 起 1,207 日、QQQ／SMH 2025-01-02 起、TLT 2025-08-01 起，更早為 404）。as-of 用本地 VIX、報酬獨立驗證：hist_skew 與 iv_rv 同套錯位（label 前一交易日，QQQ 3m skew 對報酬 lag −1 −0.49／lag 0 +0.06）；term 的 premarket=1 快照 = D−1 收盤附近。本 repo 新增 `put_skew3m`、`skew3m`、`pctl1y`、`p25_p50_1m`、`term_slope`、本地 complacency（50dma 誤差最大 0.24%，breakdown 交集 36／聯集 37）與 route。

**S1 修正（fix4）**：見下節 Opus 審查。term 主鍵加入 `premarket`、raw 檔不再覆蓋、加 as-of 完整性檢查；第 9 條與驗收 A 改用 `p25/p50`。

**S2（Phase 3）**：先做小型探測（L6／L7 之前沒測過），再實作 `sectorvol`、`dsi`、`rrg`、`flow` 四個抓取器並回補（sector_vol 2024-06-04 起 15,381 列、dsi／rrg 2025-01-02 起各約 2.9 萬列、flow 2025-06-02 起 SPX＋QQQ 230,021 列）。as-of：sector_vol = 回應 date 前一交易日（XLE／XLK rv 對本地 RMS30 吻合 98%）；dsi／rrg／flow 不位移。本 repo 新增 `lieta_xsd_iv`、`lieta_xop_iv`、`xsd_ivpct`、`xop_ivpct`、`{t}_dsi_1w`、`{spx,qqq}_deep_otm_put_premium`；route 加第 7 條輔助條件（XSD／XOP ivpct 皆 > 0.8，與主條件分開判斷）、DSI 參考圖、SPX／QQQ 權利金前 20 大表（標深價外 put）。

**S3（排程與告警）**：見「排程狀態」。

**S4**：兩個 repo 測試全綠（goldmine 288 項、本 repo 129 項、cron 專案 111 項）；驗收彙總 `PHASE-ALL-驗收.md`；實作 WN 更新各 Phase 狀態、決策、待決與已知限制。

## 驗收數字

| 項目 | 結果 |
|---|---|
| (a) VX1 日變動 vs `cboe_VIX`（排除換月日） | pre 0.943／post 0.890 |
| (b) SPX rv1m vs 本地 RMS30 | 252/252 |
| (c) screener spot vs `series_2` | 70/70 |
| 驗收 A（改寫後）lieta p25/p50 vs gex，gex 移 1 日 | 水準 0.980／日變動 0.941 |
| 原 `p25/atm` vs `gex_spx_put_skew_1m` | 0.21–0.59（失敗，原因見下） |
| XOP／XSD IV 日變動 vs 本地 ETF 報酬 | lag 0 最強，無錯位 |

## 每次 Opus 審查抓到的問題與處理

| 審查 | 抓到的 | 處理 |
|---|---|---|
| 階段 1、階段 2（前任） | vx 與 iv_rv 各晚一天、排程只抓一天會永久缺資料 | fix1／fix2 已修；之後固定跑三項外部對照 |
| S0 複核 | vx 位移要逐份判斷格式（必修）；建議補到期前一天 VX1 | fix3 修好並 reparse |
| **S1 審查（rv-s1）** | **必修-1**：lieta term 的 `atm_iv` 不是 ATM（約 50Δ IV 的 1.15 倍），`p25/atm` 與第 9 條分母錯，route 當時顯示的「QQQ−SPX +0.016」是假訊號；**必修-2**：term 每日流程會永久缺 as-of、`--force` 會覆蓋 EOD 原始檔、SPX EOD 快照品質差（15% 到期日 p25 < atm）。建議：route 條件符號沒有測試保護（變異驗證 3 個沒抓到）、term 壞值未過濾、延遲基準、文件同步 | fix4 兩邊全修（見下）；route 補每條邏輯測試，13 個變異全變紅 |
| fix4 複核 | PASS，無必修。提醒：快照層壞值過濾只套 SPX 可接受（套全部會誤刪 TLT 正常快照）；as-of 10-22 term 缺一天待補 | 記為待決 |
| S2＋S3 審查 | PASS，無必修。獨立驗證 sector_vol 與 flow 的 as-of、深價外 put 標記、第 7 條符號、cron 星期判斷都正確。建議：log 清理排序、登入過期盲點、第 7 條「連續多日」 | log 清理改依 mtime（已修）；其餘列入待決 |

fix4 的修法：term_iv 主鍵含 `premarket`、兩版並存；raw 檔名含請求日／回應日／快照型、不覆蓋；`premarket=0` 不算完成，隔日重抓；as-of 完整性檢查（缺口自動補抓、SUMMARY `asof_gaps=`）；converter 對每個 (as-of, ticker) 優先 premarket=1，EOD 標「暫定」並寫 sidecar `data/lieta_term_meta.json`；新增 `p25_p50_1m`；到期日層＋快照層壞值過濾。

## 排程狀態

- 任務：`C:\code\2026-10-01-cron-job-agent\tasks\left-tail-eod.yaml`，**已啟用**，下次執行 2026-10-25 09:00（台灣時間；當天是週日，腳本會略過，實際首次抓取是 10-27 週二）。
- 09:00 而非 WN 的 08:30：調度器只在整點醒。
- 9333 被占用（Chrome 或 `capture_multi.py`）時直接失敗、寫 log、不關 Chrome；失敗由任務 `notify.on_error`（Telegram）通知。要停用把 yaml 的 `enabled` 改回 false。
- 試跑只用 `--force --no-notify`；試跑時 9333 空閒，沒有動到你的 Chrome。

## 待使用者決定／啟用

1. **term 正式值 = premarket=1 快照，EOD 為暫定最新點**（S1 審查建議；兩版並存，可回復）。理由：1206 份 SPX 歷史全是 premarket=1，同一條線才前後一致；SPX EOD 快照品質較差。
2. **第 9 條新公式**：`pctl1y(QQQ−SPX 的 p25/p50) > 85` 且 `QQQ put_skew3m 百分位 > 85`。今天 ⬜（差 −0.047，百分位 39；put skew 百分位 54）。原公式 `p25/atm − gex > 0` 因分母口徑錯已不用。
3. **第 7 條主條件**：目前只判最近一日 SMH、XLE 同日 < −1.5%，盤點 WN 寫「連續多日」。今天 ⬜（SMH +0.74%、XLE +2.60%），輔助也 ⬜（XSD 0.53、XOP 0.83）。是否改成近 N 日內達標 ≥ 2 天？
4. term 快照層壞值過濾只套 SPX（要全套改 `TERM_SNAPSHOT_FILTER_TICKERS`）；到期日層 `>1.0` 會丟掉 2025-04 關稅期 dte 1–4 的真實高 IV，只影響 `term_slope`。
5. **告警盲點**：JWT／登入過期、Chrome 起不來時 `fetch_eod_metrics.py` 不寫 `fetch_log`，`lieta_fetch_alert` 看不到；目前靠任務 `notify.on_error` 每天通知。若要連續失敗升級，需要 goldmine 補寫 `fetch_log`（endpoint=`session`）。
6. **2026-10-26／10-27 之後複驗**：term as-of 2026-10-22 缺一天（lieta 週末沒給，SUMMARY 目前 `asof_gaps=4`，預期下次排程自然補上；**不要用 `--force` 重抓**）；sector_vol 最新一點是未來日標籤（20261026）的 provisional 值，10-27 重抓後重跑 converter 並複核第 7 條輔助值；探測報告 §6.5 的其餘待驗項。
7. flow 早期 2025-01-23～06-01 沒補（探測下限是 2025-01-23）；vx／screener 的 raw 檔名仍會被同請求日重抓覆蓋（term 已改）。
8. 所有變更都**沒有 commit**，由你決定如何 commit。

## 新增／修改檔案清單

**本 repo `C:\code\2025-12-05-MacroMicro-Data`（全是新增，未 commit）**
- `get_lieta_eod_series.py`、`get_complacency_series.py`、`lieta_fetch_alert.py`
- `flask_highcharts/app/routes/左尾風險監控.py`
- `tests/test_lieta_eod_series.py`、`tests/test_complacency.py`、`tests/test_left_tail_route.py`、`tests/test_lieta_fetch_alert.py`
- `analysis/左尾風險/WN-2026-10-24-左尾風險-lieta-goldmine資料接入實作.md`（本檔與實作 WN；WN 自 S1 起持續更新）
- `data/lieta_*.pkl`、`data/complacency_*.pkl`（133 個）、`data/lieta_term_meta.json`、`data/lieta_flow_top.json`
- 沒有改 `get_all_series_data.py`：complacency 與 lieta converter 由排程任務執行。

**goldmine `C:\code\2026-09-09-new-lieta-goldmine`（未 commit）**
- `fetch_eod_metrics.py`、`test_fetch_eod_metrics.py`
- `research/left-tail-probe/`：`RESEARCH-left-tail-probe.md`、`PHASE1-驗收.md`、`PHASE2-驗收.md`、`PHASE3-驗收.md`、`PHASE-ALL-驗收.md`、`probe_left_tail.py`、`probe2/`（Phase 3 探測與 raw）
- `impulse/eod_metrics.db`（含備份 `.bak-pre-fix2／fix3／fix4／s1／s1-reparse／s2`）、`impulse/eod_raw/`、`impulse/fetch_eod_metrics_*.log`（`impulse/` 不在 git 追蹤內）
- 既有的 `SOP-agy-dispatch.md`、`research/legacy-analytics/` 修改不是這項工作的。

**cron-job-agent `C:\code\2026-10-01-cron-job-agent`（未 commit）**
- `tasks/left-tail-eod.yaml`、`jobs/left_tail_eod.py`、`tests/test_left_tail_eod.py`
- （`jobs/alpha_picks_watch.py`、`tasks/alpha-picks-watch.yaml` 不是這項工作的。）

## 已知風險

- **term 最新一點是暫定**：EOD（premarket=0）快照品質不如 premarket=1（SPX 尤其），route 已標「EOD 暫定」，但判斷第 9 條時要留意最後一點。SPX 的 premarket 快照含夜盤變動，QQQ／SMH／TLT 不含，兩者比較（第 9 條）有語意差異。
- **lieta 資料洞**：vx 缺 as-of 2025-04-23、2026-07-31；sector_vol 2025-07 多日殘缺；dsi 2026-08-12 無；flow 2025-12-29／30 為空。重抓仍同，接受並記錄。
- **L6 ticker 集合不穩**（15↔27 檔，SMH 從未出現），輔助條件因此用 XSD／XOP；解析度只有 2 位小數（1 vol 點）。
- **登入／JWT 依賴**：session 過期整條斷掉（見待決 5）；排程與你的 9333 Chrome 互斥。
- **口徑差異**：lieta 的 atm_iv 是 VIX 型口徑；gamma flip 與野村不同，只看方向和相對距離；gex 序列日期比 as-of 晚一個交易日（route 已標）。
- **前任留下的殘餘**：工作階段中有數個舊的 `tail -F` 監看程序（前任 session 的 Monitor 遺留）還在背景，我沒有權限判斷能不能殺，沒有動；不影響資料。

## 決策紀錄（我自己決定的，保守且可回復）

1. term 正式值用 premarket=1、EOD 暫定（待決 1）。
2. 快照層壞值過濾維持只套 SPX（fix4 複核同意）。
3. 啟用排程：依交接 prompt「試跑成功再啟用」，試跑成功後啟用；可改 `enabled: false` 回復。
4. 排程取 09:00（調度器限制）。
5. 告警盲點不改 goldmine，先靠任務自身通知。
6. vx／screener 的 raw 檔名不動（本次只改 term，避免重蹈 fix2 的覆蓋風險）。
7. 後段審查依你的指示改用 Opus low effort＋只讀 diff／測試輸出的 `review-input.md`，並且修正一律續接原 worker 或小改自己做，以省額度。
