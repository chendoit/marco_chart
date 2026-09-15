# WN-2026-04-12 Scatter 圖與 ChartModule custom_config 擴展

## 起因

現有 Flask Highcharts 系統完全以時間序列（Highcharts.stockChart）為核心設計。需要在同一頁面中嵌入非時間序列圖表（scatter、heatmap、bubble 等），且不破壞既有架構。

## 架構改動總覽

改動四個檔案，核心思路：**在 ChartModule 宣告層加入 `custom_config` 概念，讓一張圖可以完全繞過標準 series 資料流程，直接提供完整 Highcharts config**。

### 1. `flask_highcharts/app/utils/highcharts_utils.py` — ChartModule class

**改動內容**：

```python
# charts list 初始化新增 custom_config 解析
self._custom_configs = [c.get("custom_config") for c in charts]
self.CHART_IDS = [c.get("ids", "__custom__") for c in charts]

# 新增 method
def get_custom_config(self, index):
    """回傳第 index 張 chart 的 custom config（支援 callable lazy eval），
    若非 custom chart 則回傳 None。"""
    if index < len(self._custom_configs):
        cfg = self._custom_configs[index]
        if cfg is None:
            return None
        if callable(cfg):
            return cfg()  # lazy evaluation — 每次 API call 重新計算
        return cfg
    return None
```

**重點**：
- `custom_config` 可以是 dict（靜態）或 callable（動態，推薦）
- callable 會在每次 API request 時被呼叫，確保資料即時
- 沒有 `custom_config` 的圖表回傳 None，走原有流程
- `ids` 設為 `"__custom__"` 作為 sentinel，避免 `generate_chart_data` 嘗試載入不存在的 series

### 2. `flask_highcharts/main.py` — `_build_group_charts()`

**改動內容**：

```python
for i, chart_group in enumerate(chart_ids):
    # 新增：custom config 優先檢查
    custom = module.get_custom_config(i) if hasattr(module, 'get_custom_config') else None
    if custom is not None:
        charts.append(custom)   # 直接跳過所有標準 series 處理
        continue

    # ... 原有 generate_chart_data / get_chart_config 流程 ...
```

**重點**：
- `hasattr` 保護確保舊模組不受影響
- custom config 回傳的 dict 必須包含 `{"config": {...}, "summary": "..."}`，與標準圖表的 API 回傳格式一致
- custom 圖表跳過 `generate_chart_data`、`get_chart_config`、series 組裝等所有標準流程

### 3. `flask_highcharts/templates/charts.html` — 前端渲染

**改動內容**：

```javascript
// 新增：判斷是否為 stockChart 類型
function isStockChartType(config) {
    const t = config.chart && config.chart.type;
    return !t || t === 'line' || t === 'candlestick';
}

function createChart(container, config) {
    // ...
    const stock = isStockChartType(config);
    const newConfig = {
        ...config,
        chart: {
            ...config.chart,
            width: containerWidth,
            height: containerWidth * (stock ? 0.5 : 0.6),  // 非 stock 圖略高
        },
    };

    if (stock) {
        newConfig.navigator = { ...config.navigator, margin: 30 };
        return Highcharts.stockChart(container, newConfig);   // 時間序列
    }
    return Highcharts.chart(container, newConfig);             // scatter 等
}
```

**重點**：
- 根據 `config.chart.type` 自動選用 `Highcharts.chart()` 或 `Highcharts.stockChart()`
- `stockChart` 有 navigator、rangeSelector 等時間序列特有功能；`chart` 沒有
- resize handler 也使用相同邏輯判斷
- 不需要 `type` 或 `type === 'line'` 或 `type === 'candlestick'` 的一律走 stockChart（向後相容）

### 4. Route 模組 — 以 `McElligott波動率微結構.py` 為範例

**如何新增一個 custom chart**：

```python
def _build_my_scatter():
    """回傳 {"config": {完整 Highcharts config}, "summary": "..."}"""
    # 1. 載入資料
    data = load_series_data("my_series")
    
    # 2. 計算（pandas/numpy）
    # ...
    
    # 3. 組裝完整 Highcharts config
    config = {
        "chart": {"type": "scatter", "zoomType": "xy"},
        "title": {"text": "My Scatter"},
        "xAxis": {...},
        "yAxis": {...},
        "series": [...],
        "annotations": [...],   # 可選
        "legend": {...},
    }
    
    summary = "這張圖的說明文字..."
    return {"config": config, "summary": summary}

# 在 ChartModule charts list 中加入
_module = ChartModule(
    filename='我的模組',
    charts=[
        {"title": "...", "ids": [...], ...},           # 標準時間序列圖
        {"custom_config": _build_my_scatter},           # 自定義圖表
        {"title": "...", "ids": [...], ...},           # 可以混合
    ],
)
```

**關鍵約定**：
- callable 必須回傳 `{"config": {...}, "summary": "..."}`
- `config` 就是 Highcharts 原生 options 物件，前端原封不動傳入 `Highcharts.chart()`
- `summary` 用於圖表下方的說明文字區塊
- `custom_config` 圖表在 `charts` list 中不需要 `ids`、`title`、`axis` 等欄位（全部由 config 內的 Highcharts options 控制）
- 但如果也給了 `"summary"` key，它會被 `self.SUMMARY_LIST` 收錄；不過 custom_config callable 回傳的 summary 會覆蓋它（因為 `_build_group_charts` 直接用 custom dict）

## 開發注意事項

### 依賴
- 不要引入 `scipy`，伺服器 venv 沒有安裝
- 回歸用 `numpy.polyfit`，percentile 手動算 `np.sum(residuals <= val) / N * 100`

### 資料格式
- `load_series_data("cboe_VIX")` 回傳 `{"title": str, "data": [[timestamp_or_datetime, value], ...]}`
- 時間戳可能是 ms epoch 或 datetime string，用 `pd.to_datetime()` 統一處理

### Highcharts annotations
- 使用 `"annotations"` key（非 `"annotationsOptions"`）
- `"point": {"x": px, "y": py}` — pixel 座標（用於固定位置的 info box）
- `"point": {"xAxis": 0, "yAxis": 0, "x": val, "y": val}` — 資料座標（用於隨資料縮放的標記）
- `"useHTML": True` 才能在 text 中使用 HTML tag

### Python 環境
- 使用 `venv\Scripts\python.exe`
- Windows PowerShell 不支援 `&&` 串接指令，用 Shell tool 的 `working_directory` 參數
- 輸出非 Big5 字元需在 script 開頭設 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`

## 驗證方式

啟動 Flask server 後用 API 驗證：

```powershell
# 啟動 server
venv\Scripts\python.exe flask_highcharts\main.py

# 驗證 API 回傳
curl.exe http://localhost:5050/api/chart/McElligott%E6%B3%A2%E5%8B%95%E7%8E%87%E5%BE%AE%E7%B5%90%E6%A7%8B -o response.json

# 用 Python 檢查 scatter chart
venv\Scripts\python.exe _check_scatter.py
```

檢查項目：
1. `response.charts[-1].config.chart.type === "scatter"`
2. series 包含 `Past 2 Years`（灰）、近 30 天各天（四象限色）、`Today`（紅菱形）、`Regression`（紅虛線）
3. annotations 包含回歸方程式、R2、outperformance、象限判斷、色彩圖例
4. 前端實際頁面以 `Highcharts.chart()` 渲染而非 `Highcharts.stockChart()`

## 檔案清單

| 檔案 | 角色 |
|------|------|
| `flask_highcharts/app/utils/highcharts_utils.py` | ChartModule class — 核心抽象層 |
| `flask_highcharts/main.py` | API 路由 — `_build_group_charts()` |
| `flask_highcharts/templates/charts.html` | 前端 — `createChart()` + `isStockChartType()` |
| `flask_highcharts/app/routes/McElligott波動率微結構.py` | 範例 — `_build_vvix_outperformance_scatter()` |
