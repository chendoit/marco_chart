# WN-2026-04-08 M平方 ETF 資金淨流量 API 攔截

## 起因

在 M平方 UVXY ETF 頁面（https://www.macromicro.me/etf/us/intro/UVXY）的「資金淨流量」tab 看到有完整的週頻資金淨流量圖表（每週淨流量 + 累計淨流量 + 市價），但我們的 `get_m_square_etf.py` 只攔截了 `intro_main` API 取 close/volume，從未抓過這個資金流資料。

現有的 ETF fund flow 由 `get_etf_csv.py` 從 ProShares 官方 CSV 自算（日頻），想補齊 M平方這個獨立資料源。

## 分析

### API 探測結果

用 Playwright 攔截 UVXY 頁面所有 `/api/etf/` 開頭的 response，點擊「資金淨流量」tab 後發現：

| 順序 | API endpoint | 用途 |
|------|-------------|------|
| 1 | `/api/etf/us/timeseries/intro_main/UVXY` | 頁面載入時觸發，含 close/volume（已有攔截） |
| 2 | `/api/etf/us/get_returns?date_range=all&tickers=UVXY&detail=1` | 績效表現 |
| 3 | `/api/etf/us/analysis/UVXY?tags=149,336` | 相關圖表/文章 |
| 4 | `/api/etf/us/related/netflow/UVXY/149,336` | 同類 ETF 資金流排名（非時間序列） |
| 5 | **`/api/etf/us/timeseries/intro_netflow/UVXY?date_range=all`** | **點擊 tab 後觸發，週頻資金淨流量時間序列** |

### intro_netflow API JSON 結構

```json
{
  "success": true,
  "data": {
    "series": [
      {"date": "2011-10-23", "val": 1730420, "accu_val": 1730420},
      ...
      {"date": "2026-04-05", "val": 24265000, "accu_val": 7929849119.18}
    ],
    "start_date": "2011-10-23",
    "end_date": "2026-04-05"
  }
}
```

- `date`：週日（Sunday），代表該週的標記日期
- `val`：當週資金淨流量（美元）
- `accu_val`：累計資金淨流量（美元）
- UVXY 共 755 筆，涵蓋 2011-10-23 ~ 2026-04-05

### M平方 vs ProShares 自算 fund flow 比對

兩個資料源差異顯著，**不是**同一份資料的不同聚合方式：

| 特性 | M平方 (intro_netflow) | ProShares CSV 自算 |
|------|----------------------|-------------------|
| 頻率 | 週頻（Sunday label） | 日頻（交易日） |
| 資料量 (UVXY) | 755 筆 | 3,582 筆 |
| 拆股處理 | 2025-11-16 出現 -28 億異常值 | 跳過拆股日（±3天窗口） |
| 近期可用性 | 2025-12 ~ 2026-03 大量為 0 | 持續有值 |
| 來源 | M平方計算（可能基於 AUM 變化） | ProShares NAV CSV (Δshares × nav) |

結論：兩者是**互補的獨立信號源**，不能互相替代。

## 修改內容

### `get_m_square_etf.py`

1. **新增 `fetch_etf_fundflow(page, ticker)`**：在已載入的 ETF 頁面上點擊「資金淨流量」tab，攔截 `intro_netflow` API，解析 `val` 和 `accu_val` 存成 pkl
2. **新增 `_launch_browser(p)`**：抽取重複的 browser 啟動邏輯為共用函數
3. **修改 `fetch_m_square_etfs()`**：每個 ticker 取完 close/volume 後，接著呼叫 `fetch_etf_fundflow()`

### 新增 pkl 檔案（每個 ticker 兩個）

- `series_etf_{ticker}_m2fundflow.pkl` — 週淨流量，title: `{ticker}-m2fundflow`
- `series_etf_{ticker}_m2fundflow_cum.pkl` — 累計淨流量，title: `{ticker}-m2fundflow-cumulative`

後綴用 `m2fundflow` 以區隔 ProShares 版本的 `fundflow`。

### 未改動

- `get_etf_csv.py`：ProShares 日頻 fund flow 獨立運作不受影響
- `get_all_series_data.py`：`fetch_m_square_etfs()` 已在 tasks 中，新的 fund flow 抓取自動包含
- 現有圖表（每日天啟、McElligott）：仍使用 ProShares 版本的 `etf_*_fundflow`

## 驗證結果

以 UVXY 單一 ticker 實測：

```
UVXY: 3647 close records (intro_main)
UVXY: 3647 volume records (intro_main)
UVXY: 755 weekly net flow records (intro_netflow)
UVXY: 755 cumulative flow records (intro_netflow)
```

pkl 內容驗證：
```
series_etf_UVXY_m2fundflow.pkl
  title: UVXY-m2fundflow
  records: 755
  first: [2011-10-23 08:00, 1730420.0]
  last:  [2026-04-05 08:00, 24265000.0]

series_etf_UVXY_m2fundflow_cum.pkl
  title: UVXY-m2fundflow-cumulative
  records: 755
  first: [2011-10-23 08:00, 1730420.0]
  last:  [2026-04-05 08:00, 7929849119.18]
```

時間戳符合 08:00 UTC+8 規範，與其他 pkl 一致。
