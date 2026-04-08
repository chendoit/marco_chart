# WN-2026-04-02 NY Fed ACM Term Premium 自動抓取實作

## 起因

McElligott 框架中，ACM Term Premium 是 "07 Rates" 文章的核心指標，被稱為「2025 年風險資產的真正總經風險催化劑」。盤點 Working Note（WN-2026-04-02-McElligott-專有資料與替代方案.md）後，確認 NY Fed ACM Term Premium 是可行性最高的公開資料之一，優先實作自動抓取。

## 分析

### 資料來源調查

調查了三種 Term Premium 取得方式：

| 來源 | 模型 | 頻率 | 起點 | 取得方式 |
|------|------|------|------|---------|
| NY Fed Excel | ACM (Adrian, Crump, Moench 2013) | 每日 | 1961 | 直接 HTTP 下載 |
| FRED `THREEFYTP10` | Kim-Wright (2005) | 每日 | 1990 | FRED API |
| Fed Board HTML 表格 | Kim-Wright (2005) | 每週 | 1990 | HTML scraping |

**關鍵發現：** NY Fed 的 ACM Excel 有直接下載 URL，不需要 Playwright：
```
https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls
```

此 URL 是透過 Playwright 探索 NY Fed term-premia-tabs 頁面的 DOM 發現的（頁面上 "Download the data" 連結的 href）。

### Excel 檔案結構

- 兩個 Sheet：`ACM Monthly` 和 `ACM Daily`
- 欄位：`DATE`, `ACMY01`~`ACMY10`（yields）, `ACMTP01`~`ACMTP10`（term premium）, `ACMRNY01`~`ACMRNY10`（risk-neutral yields）
- 日期格式：`DD-Mon-YYYY`（例：`14-Jun-1961`）
- 檔案大小：約 10MB

### ACM vs Kim-Wright 差異

兩者都是 Term Premium 模型，追蹤相同概念但估計值不同：
- ACM 使用五因子無套利模型，資料回溯到 1961
- Kim-Wright 使用三因子模型，資料從 1990 開始
- McElligott 文章引用的是 ACM 模型

## 修改內容

### 新增檔案

**`get_nyfed_termpremium.py`** — NY Fed ACM Term Premium 抓取腳本
- `requests.get()` 直接下載 XLS，`pandas.read_excel()` 解析 "ACM Daily" sheet
- 儲存 3 個天期：ACMTP02（2Y）、ACMTP05（5Y）、ACMTP10（10Y）
- 暫存 XLS 在 `DATA_DIR/_acm_temp.xls`，解析完畢後自動刪除
- 新增依賴：`xlrd`（讀取 `.xls` 格式）

### 修改檔案

**`get_all_series_data.py`**
- 原 `"FRED data"` 任務重新命名為 `"FRED STLFSI4"`
- 新增任務 `"FRED THREEFYTP10 (Kim-Wright Term Premium)"`
- 新增任務 `"NY Fed ACM Term Premium"`（調用 `fetch_nyfed_acm`）
- import 新增 `from get_nyfed_termpremium import fetch_nyfed_acm`

## 驗證結果

### NY Fed ACM（`series_nyfed_acmtp10.pkl`）

```
title: NY Fed ACM 10Y Term Premium
records: 16,162
first: [datetime(1961, 6, 14, 8, 0), 0.1037]
last:  [datetime(2026, 3, 31, 8, 0), 0.6736]
datetime hour=8 ✓, value type=float ✓
```

### FRED Kim-Wright（`fed_THREEFYTP10.pkl`）

```
title: Term Premium on a 10 Year Zero Coupon Bond
records: 9,454
first: [datetime(1990, 1, 2, 8, 0), 1.8064]
last:  [datetime(2026, 3, 27, 8, 0), 0.7176]
datetime hour=8 ✓, value type=float ✓
```

### 產出 pkl 檔案一覽

| 檔案名稱 | 模型 | 筆數 | 最新日期 | 最新值 |
|----------|------|------|---------|--------|
| `series_nyfed_acmtp02.pkl` | ACM 2Y | 16,162 | 2026-03-31 | 0.120 |
| `series_nyfed_acmtp05.pkl` | ACM 5Y | 16,162 | 2026-03-31 | 0.280 |
| `series_nyfed_acmtp10.pkl` | ACM 10Y | 16,162 | 2026-03-31 | 0.674 |
| `fed_THREEFYTP10.pkl` | Kim-Wright 10Y | 9,454 | 2026-03-27 | 0.718 |

所有 pkl 格式與現有 `fed_STLFSI4.pkl` 一致（`{"title": str, "data": [[datetime(hour=8), float], ...]}`）。

## 附帶發現

- **CBOE Put/Call Ratio**：MacroMicro series 1650 已有此資料，可透過現有 MacroMicro 抓取流程取得，無需另建來源
- **SG Trend Index**：免費每日資料不可直接取得，官方網站只顯示 MTD/YTD 彙總。完整每日資料需聯繫 SG Capital Consulting 或付費存取 SG Markets Analytics 平台。替代方案為 Barclay BTOP50 Index（月度頻率）
