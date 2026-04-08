# WN-2026-04-03 CME FTP daily_volume 抓取修復

## 起因

執行 `python get_cme_daily_volume.py` 時收到 403 錯誤：

```
requests.exceptions.HTTPError: 403 Client Error: Forbidden for url: https://www.cmegroup.com/ftp/daily_volume/
```

原本 `list_remote_dates()` 用 `requests.get()` 抓取 FTP 目錄列表頁，CME 現已將目錄頁面也納入反爬蟲保護，不再允許非瀏覽器存取。

## 分析

### 問題 1：目錄列表被 403

- 舊設計：standalone 模式先用 `requests` 抓目錄列表 → 計算缺少日期 → 再開 Playwright 下載
- `requests` 被擋後 standalone 直接 crash（`__main__` 無 try/except）
- Orchestrator (`fetch_cme_daily_volume`) 有 try/except 但 fallback 只是 rebuild pkl，不會嘗試下載

### 問題 2：xlsx 格式變更

下載成功後發現 `parse_xlsx` 無法解析，所有欄位都找不到。CME 改了 xlsx 格式：
- 資料改在第二個工作表「CME Group Vol and OI by Product」
- 產品代碼改用 clearing codes（J1/EC/AD）而非 Globex codes（6J/6E/6A）
- 交易所名稱改為全名（"Chicago Mercantile Exchange (STATS)"）而非代碼（XCME）
- Future/Option 標識改為 "F"/"O" 而非 "FUT"/"FUTURE"
- Trade Date 在 header 區域而非每行欄位
- 欄位名稱含換行符（如 `Open\nInterest ②`）

### 問題 3：缺少 openpyxl

pandas `read_excel(engine="openpyxl")` 需要 openpyxl 套件，venv 中未安裝。

## 修改內容

### `get_cme_daily_volume.py`

**目錄列表改走 Playwright：**
- 新增 `_list_dates_from_page(page)` — 從 Playwright 頁面 content 解析可用日期
- 修改 `_check_session_valid(page)` — 回傳 `(can_download, dates)` tuple
- 重構 `download_dates()` — 當 `dates_to_download=None` 時自動從 Playwright 頁面取得日期列表
- `__main__` 不再呼叫 `list_remote_dates()`，全程使用 Playwright

**Orchestrator fallback：**
- `fetch_cme_daily_volume()` 仍先嘗試 `requests`（快速檢查），失敗時 fallback 到 Playwright
- Playwright 使用 persistent browser context（`.cme_browser_profile/`）復用 cookies

**xlsx parser 重寫：**
- 自動選擇含 "by product" 的工作表
- 動態偵測 header 行與 trade date
- 用 clearing code + exchange 名稱模式比對產品
- PRODUCTS dict 新增 `clearing_code`、`exchange_pat`、`exchange_code` 欄位
- pkl 檔名保持向後相容（`cme_daily_6j_xcme_volume.pkl` 等）

**錯誤處理與通知：**
- `download_dates()` 回傳 `(success, fail, skip_reason)` tuple
- `_wait_for_login()` 加入 try/except + 詳細 logging
- Session 過期時**立即發送 LINE 通知**（不等連續 3 天）
- 下載失敗時 raise `RuntimeError`，整合進 orchestrator 既有的連續失敗追蹤機制

**安裝 openpyxl：**
- `pip install openpyxl`（3.1.5）

### Clearing Code 對照表

| 產品 | Globex Code | Clearing Code | Exchange Pattern |
|------|-------------|---------------|------------------|
| 日圓 | 6J | J1 | Chicago Mercantile Exchange |
| 歐元 | 6E | EC | Chicago Mercantile Exchange |
| 澳幣 | 6A | AD | Chicago Mercantile Exchange |
| 原油 | CL | CL | NYMEX |
| E-mini S&P 500 | ES | ES | Chicago Mercantile Exchange |
| E-mini Nasdaq 100 | NQ | NQ | Chicago Mercantile Exchange |

## 驗證結果

```
CME FTP (browser): 3085 files (20140102~20260401)
Missing dates (since 20260327): 4
[1/4] Fetching 20260327... Downloaded daily_volume_20260327.xlsx (96,449 bytes)
[2/4] Fetching 20260330... Downloaded daily_volume_20260330.xlsx (99,433 bytes)
[3/4] Fetching 20260331... Downloaded daily_volume_20260331.xlsx (100,162 bytes)
[4/4] Fetching 20260401... Downloaded daily_volume_20260401.xlsx (92,071 bytes)
CME download complete: 4 ok, 0 failed
Rebuilding pkl from 4 xlsx files...
Built 12 pkl files from 4 xlsx
```

- 4 個 xlsx 下載成功（20260327~20260401）
- 12 個 pkl 產出（6 產品 × volume + oi）
- Persistent cookies 有效：第二次執行不需重新登入
- pkl 格式符合專案慣例：`{"title": str, "data": [[Timestamp(08:00), float], ...]}`

## 注意事項

- CME session cookies 會過期，過期時 LINE 會立即通知，需手動跑 `python get_cme_daily_volume.py` 重新登入
- 目前 `cme_daily_*` pkl 尚未接上任何 Flask route，資料已收集但無圖表顯示
- 抓取頻率：每檔間隔 `DOWNLOAD_DELAY_SEC = 2.0` 秒，避免觸發 rate limit
