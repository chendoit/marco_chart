# WN-2026-04-08 McElligott 儀表板 Vol Surface + Gamma Summary 擴充

## 起因

McElligott 儀表板已有 43 張圖（4 個 route），但 GEX-lieta 專案近期新增兩大資料來源尚未整合：

1. Vol Surface DB API（`v_skew_indicators`、`v_term_slope`、`daily_vol_reference`）
2. Daily Gamma Summary（`daily_gamma_summary`、`daily_gamma_by_expiry`）

同時希望仿照 Nomura Vol 報告風格，在圖表標題動態顯示最新值的歷史百分位（如 "SPX 3M Skew - 25dP/25dC (71%tile)"）。

## 分析

### 百分位方案選擇

評估即時計算 vs pkl 預算兩種方案：


| 方案     | 優點                    | 缺點                             |
| ------ | --------------------- | ------------------------------ |
| 即時計算   | 永遠最新、不需額外 pkl、跨資料源通用  | `get_chart_title()` 變複雜、出錯影響渲染 |
| pkl 預算 | Flask 零計算、架構不變、計算邏輯隔離 | 需額外 pkl、非 GEX 來源需另外處理          |


決定採用 **pkl 預算 + 集中式腳本**：新建 `calc_pctrank.py` 統一讀取任意 pkl → 算百分位 → 存為 `_pctrank.pkl`，不修改各抓取腳本。

### 百分位計算方法

- 滾動 percent_rank：`count(window < current) / (window_size - 1)`
- 最大 lookback 504 天（約 2 年），至少 20 天才開始計算
- 存為同格式 pkl，供 `ChartModule._append_pctrank()` 讀取最後一筆

## 修改內容

### 1. ChartModule 百分位標題機制（highcharts_utils.py）

- chart dict 新增 `pctrank_id` 欄位
- `__init_`_ 解析 `_pctrank_ids` 列表
- 新增 `_append_pctrank()` 方法：讀取 `{pctrank_id}_pctrank.pkl` 最後一筆值，附加 `(XX%tile)` 到標題
- pkl 不存在或資料為空時 graceful fallback 到原標題

### 2. 資料橋接（get_gex_series.py）

新增函式從 `gex_analysis.db` 匯出：

**Vol Surface 指標（SPX）**：

- `gex_spx_put_skew_{1m,3m}` — 25dP/ATM（每日 AVG 聚合）
- `gex_spx_call_skew_{1m,3m}` — 25dC/ATM
- `gex_spx_skew_ratio_{1m,3m}` — 25dP/25dC
- `gex_spx_term_slope` — near vs far ATM IV slope
- `gex_spx_iv30` — IV30（× 100 轉 %）
- `gex_spx_vrp_surface` — (IV30 - rvol_20d) × 100

**Daily Gamma Summary（SPX/SPY/VIX）**：

- `gex_{ticker}_call_gamma` / `put_gamma` / `net_gamma`（÷ 1e9 轉 $B）
- `gex_{ticker}_gamma_0dte` / `gamma_non0dte`（從 `daily_gamma_by_expiry` 聚合）

### 3. 集中式百分位腳本（calc_pctrank.py — 新建）

- 15 個 PCTRANK_TARGETS（vol surface 8 + gamma 5 + flip distance 2）
- 讀取 pkl → `compute_pctrank()` → 存為 `{id}_pctrank.pkl`
- 整合至 `get_all_series_data.py` tasks 尾部

### 4. 新增圖表

**Route 1 — McElligott波動率微結構（14→19，+5 張）**：


| 圖表                            | pctrank_id              | 概念                                 |
| ----------------------------- | ----------------------- | ---------------------------------- |
| SPX 3M Put Skew 25dP/ATM      | `gex_spx_put_skew_3m`   | Skew 陡峭度 = crash-down 條件           |
| SPX 3M Skew 25dP/25dC         | `gex_spx_skew_ratio_3m` | Skew Ratio 急升 = 恐慌搶進 put           |
| SPX 1M vs 3M Put Skew         | `gex_spx_put_skew_1m`   | Skew 期限結構                          |
| SPX IV Term Slope             | `gex_spx_term_slope`    | Vol surface contango/backwardation |
| SPX Surface VRP (IV30-RVol20) | `gex_spx_vrp_surface`   | Surface-based VRP vs VIX-based     |


**Route 4 — McElligottDealerGamma（8→11，+3 張）**：


| 圖表                      | pctrank_id           | 概念                 |
| ----------------------- | -------------------- | ------------------ |
| SPX Call/Put Gamma 拆分   | `gex_spx_net_gamma`  | 正/負 GEX 量級分拆       |
| SPX 0DTE vs 非0DTE Gamma | `gex_spx_gamma_0dte` | 0DTE 對 gamma 結構的影響 |
| SPX Net Gamma vs VIX    | `gex_spx_net_gamma`  | Gamma-Vol 負相關量化追蹤  |


## 驗證結果

Flask 啟動於 `http://127.0.0.1:6002`，全部 route 載入成功。

```
McElligott波動率微結構  => 200 ✓  19 charts (原 14)
McElligottDealerGamma  => 200 ✓  11 charts (原 8)
McElligott相關性與部位  => 200 ✓  11 charts (不變)
McElligott總經與利率    => 200 ✓  10 charts (不變)
```

百分位標題驗證（2026-04-08 資料）：


| 圖表                       | 百分位     | 解讀                              |
| ------------------------ | ------- | ------------------------------- |
| SPX 3M Put Skew 25dP/ATM | 88%tile | Put Skew 高位 — crash-down 條件已具備  |
| SPX 3M Skew 25dP/25dC    | 71%tile | Skew Ratio 中偏高                  |
| SPX 1M Put Skew          | 77%tile | 短期恐慌偏高                          |
| SPX IV Term Slope        | 26%tile | 近端 vol > 遠端 vol，偏 backwardation |
| SPX IV30                 | 91%tile | 隱含波動率極高位                        |
| SPX Surface VRP          | 36%tile | VRP 偏低 — vol selling 吸引力下降      |
| SPX Net Gamma            | 15%tile | Gamma 偏低 — 接近 negative gamma    |
| SPX 0DTE Gamma           | 5%tile  | 0DTE gamma 極低 — put-heavy       |
| SPX Flip Distance        | 83%tile | SPX 仍在 Flip 上方有緩衝               |
| VIX Flip Distance        | 88%tile | VIX 被壓制（positive gamma）         |


共 51 張圖（原 43 + 新增 8），8 張帶 Nomura 風格百分位標題。

## Phase 3：既有圖表加百分位標題

從原有 43 張圖表中篩選出 8 張適合的（排除多指標觀察型、期限結構型、體制指標、expression 型）：

| Route | 圖表 | pctrank_id | %tile | 解讀 |
|-------|------|-----------|-------|------|
| Route 1 | CBOE SKEW + GAMMA + SMILE | `series_cboe_SKEW` | 56%tile | SKEW 中性 |
| Route 2 | 隱含相關性 COR1M/COR3M | `series_cboe_COR1M` | 85%tile | 相關性偏高，Dispersion 獲利空間收窄 |
| Route 2 | 跨資產波動率 VIX/RVX/VXN | `series_cboe_VIX` | 94%tile | VIX 極高位 |
| Route 2 | E-mini AM vs LF 淨部位 | `emini_spx_cme_net_position_asset_mgr` | 2%tile | AM 持倉極低——歷史底部 |
| Route 2 | E-mini % of OI | `emini_spx_cme_net_pct_of_oi_asset_mgr` | 2%tile | 擁擠度極低 |
| Route 3 | 跨市場壓力 MOVE | `series_17581` | 30%tile | MOVE 偏低，利率波動溫和 |
| Route 3 | 10Y 實質殖利率 DFII10 | `fed_DFII10` | 56%tile | 中性 |
| Route 3 | ACM Term Premium | `series_nyfed_acmtp10` | 73%tile | 偏高，McElligott 的「2025 催化劑」|
| Route 4 | Gamma Flip Distance | `gex_spx_flip_distance` | 83%tile | SPX 仍有正 gamma 緩衝 |

修改：`calc_pctrank.py` PCTRANK_TARGETS 15→23 項，修正 `NaT` 值處理（新增 `_is_valid_number` 過濾）。

## Phase 4：Expression 百分位支援

`calc_pctrank.py` 原本只支援單一 pkl，無法處理 expression tuple（如 VVIX/VIX ratio）。

新增功能：
- `_compute_expression(pkl1, op, pkl2)` — 載入兩個 pkl，日期 inner join 後做二元運算
- `PCTRANK_TARGETS` 支援 dict 格式：`{"id": "expr_xxx", "expr": ("pkl1", "/", "pkl2")}`
- `calc_pctrank_for_expr()` — expression 專用百分位計算

5 個 expression targets：

| pctrank_id | Expression | %tile | 用於圖表 |
|-----------|-----------|-------|---------|
| `expr_vvix_div_vix` | VVIX ÷ VIX | 7%tile | VVIX/VIX 凸性比率 |
| `expr_vix_div_spx` | VIX ÷ SPX | 89%tile | VIX Spot Beta |
| `expr_vix_div_vix3m` | VIX ÷ VIX3M | 92%tile | VIX 期限結構斜率 |
| `expr_bxm_div_spx` | BXM ÷ SPX | 59%tile | VRP vs SPX 相對表現 |
| `expr_put_div_spx` | PUT ÷ SPX | 45%tile | 備用（未掛圖表） |

未支援：`("cboe_VIX", '-', "cboe_SPX.RVOL20")` — `.RVOL20` 是 `highcharts_utils.py` 的衍生序列，無獨立 pkl。

## 修改檔案清單

| 檔案 | 動作 |
|------|------|
| `flask_highcharts/app/utils/highcharts_utils.py` | 修改 — `ChartModule` 新增 `pctrank_id` 支援 + `_append_pctrank()` |
| `get_gex_series.py` | 修改 — 新增 vol surface / gamma summary / 0DTE 匯出 |
| `calc_pctrank.py` | **新建** — 集中式百分位計算（28 targets：23 simple + 5 expression） |
| `get_all_series_data.py` | 修改 — tasks 尾部加 `calc_pctrank` |
| `flask_highcharts/app/routes/McElligott波動率微結構.py` | 修改 — +5 張新圖 + 3 張既有圖加 pctrank_id |
| `flask_highcharts/app/routes/McElligottDealerGamma.py` | 修改 — +3 張新圖 + 1 張既有圖加 pctrank_id |
| `flask_highcharts/app/routes/McElligott相關性與部位.py` | 修改 — 5 張既有圖加 pctrank_id |
| `flask_highcharts/app/routes/McElligott總經與利率.py` | 修改 — 3 張既有圖加 pctrank_id |

## 最終驗證結果

Flask 啟動於 `http://127.0.0.1:6002`，全部 route 載入成功。

```
McElligott波動率微結構  => 200 ✓  19 charts (原 14)
McElligottDealerGamma  => 200 ✓  11 charts (原 8)
McElligott相關性與部位  => 200 ✓  11 charts (不變)
McElligott總經與利率    => 200 ✓  10 charts (不變)
Total: 51 charts, 21 with Nomura-style %tile titles
```

百分位分佈：Phase 2 新增圖表 8 張 + Phase 3 既有圖表 8 張 + Phase 4 expression 5 張 = **21 張**帶百分位標題。
