# WN-2026-04-12 VVIX/VIX Outperformance 四象限分析框架

## 起因

McElligott 在 Nomura 報告中使用 VVIX vs VIX 1D change 散佈圖來判斷 VIX 選擇權市場的凸性壓力。需要在 `McElligott波動率微結構` 頁面實作此圖表，並建立完整的四象限解讀框架。

## 核心概念

### Outperformance 定義

```
Outperformance = 實際 VVIX 1D Change (%) − 回歸預測的 VVIX 1D Change (%)
```

本質：衡量「市場情緒脫離常軌的程度」。

- **正 (+)**：市場買保險（VIX 選擇權）的力道比歷史常態更瘋狂
- **負 (-)**：市場對風險的無感程度比歷史常態更鬆懈（或該買的都買完了）
- **Percentile**：脫軌現象的罕見度——99% = 極度異常正脫軌；1% = 極度異常負脫軌

### 回歸線計算

- 資料範圍：過去 2 年 CBOE VIX + VVIX 每日 close（`series_cboe_VIX.pkl`, `series_cboe_VVIX.pkl`）
- 計算 1D pct_change，inner join 取交集
- `numpy.polyfit(x, y, 1)` 做線性回歸
- Percentile = rank percentile（`np.sum(residuals <= today_residual) / N * 100`），不假設分佈形態

### 四象限解讀框架

| 象限 | VIX | VVIX | 現象 | 顏色 |
|------|-----|------|------|------|
| 右上 | ↑ | ↑ | 恐慌爆發 | 紅 |
| 左下 | ↓ | ↓ | 天下太平 | 綠 |
| 左上 | ↓ | ↑ | 暗流湧動（背離）| 藍 |
| 右下 | ↑ | ↓ | 跌勢衰竭（背離）| 橙 |

### 各象限 Outperformance 解讀

**右上：恐慌爆發 (VIX↑ VVIX↑)** — 常態情境，迴歸預測值為正
- 極端正 Outperf (>99%tile)：非理性恐慌頂部 (Climax)，VVIX 漲得比預期誇張太多，恐慌已耗盡，短線隨時報復性反彈
- 負 Outperf (<10%tile)：虛假恐慌——VIX 雖漲但大戶未跟進搶保險，下跌殺傷力有限

**左下：天下太平 (VIX↓ VVIX↓)** — 常態情境，迴歸預測值為負
- 極端負 Outperf (<5%tile)：極度自滿——大家瘋狂拋售保險，常見於重大事件落地後，短期利多但可能埋波動種子
- 正 Outperf (>80%tile)：黏滯的恐懼——大盤漲但法人死抱保險不放，暗示上漲可能是假突破

**左上：暗流湧動 (VIX↓ VVIX↑)** — 背離！VIX↓ 預測值負 + VVIX↑ 實際正 → 必然巨大正 Outperf
- 極端正 Outperf (>95%tile)：**最強烈空頭預警**——聰明錢砸重金急迫買保險，預示幾天內巨大修正

**右下：跌勢衰竭 (VIX↑ VVIX↓)** — 背離！VIX↑ 預測值正 + VVIX↓ 實際負 → 必然巨大負 Outperf
- 極端負 Outperf (<5%tile)：**極佳底部訊號**——無人願花高價買保險，恐慌擴散衰竭，大盤隨時反轉

### 三大極端交易機會

1. **VIX↑ VVIX↑ + Outperf >99%tile** → 恐慌極致，尋找 VIX 做空點或大盤抄底點（左側交易）
2. **VIX↓ VVIX↑ + Outperf >95%tile** → 籌碼背離，佈局大盤空單或買入 VIX Call（避險預警）
3. **VIX↑ VVIX↓ + Outperf <5%tile** → 恐慌衰竭，佈局大盤多單或賣出 VIX Call（尋找底部）

## 視覺設計

### 近 30 天獨立 series
- 每天獨立一個 Highcharts series，legend 名稱含日期 + outperformance + percentile
- 例：`04/08 (+5.6, 97%tile)`

### 顏色系統

每個象限三檔色：

| 象限 | 正色 (>90%tile) | 中間色 | 淡色 (<10%tile) |
|------|-----------------|--------|-----------------|
| 恐慌爆發（紅）| #cc0000 | #e06666 | #f4cccc |
| 天下太平（綠）| #16a34a | #4ade80 | #bbf7d0 |
| 暗流湧動（藍）| #2563eb | #60a5fa | #bfdbfe |
| 跌勢衰竭（橙）| #ea580c | #fb923c | #fed7aa |

- Today 點：紅色菱形 `#ff0000`，radius 8
- 歷史點：灰色圓點 `#999999`，radius 3
- 回歸線：紅色虛線 `#cc0000`，dashStyle Dot

### 其他元素
- 標題動態顯示 today percentile：`VVIX OUTPERFORMANCE VS VIX (86.7%tile)`
- X=0 / Y=0 plotLine 分隔四象限
- 四個角落標註象限名稱
- Annotation 含回歸方程式、R2、outperformance、象限判斷、色彩圖例

## 資料來源

- `series_cboe_VIX.pkl` / `series_cboe_VVIX.pkl`：由 `get_cboe_index.py` 每日從 CBOE CDN 抓取
- 格式：`{"title": str, "data": [[datetime, close], ...]}`
