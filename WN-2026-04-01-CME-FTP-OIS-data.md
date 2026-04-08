# WN-2026-04-01 CME FTP OIS 資料取得測試

## 起因

MacroMicro 的 OIS（隔夜指數掉期）數據（series 1150441, 1150443）只更新到 2026-03-20，導致「美國OIS利差 1Y-3M FED FUNDS OIS」圖表的利差線落後其他 series（SP500 到 3/31、Fed Funds Rate 到 3/30）約 10 天。調查後確認是 MacroMicro 資料來源端延遲，非程式碼問題。因此嘗試從 CME Group FTP 取得替代資料。

## 分析

### CME FTP 目錄結構
- URL: `https://www.cmegroup.com/ftp/irs/`
- 檔案命名: `irs_close_quotes_OISUSD_YYYYMMDD.csv`
- 保留期: 約 6 個交易日（rolling window），無長期歷史
- 更新到: 2026-03-31（比 MacroMicro 多 11 天）

### 反爬蟲機制
- 直接 HTTP 請求（curl、Invoke-WebRequest、playwright `page.request.get`）全部被擋：
  - `curl.exe` → timeout
  - `Invoke-WebRequest` → 403 JSON 回應：「This IP address is blocked due to suspected web scraping activity」
  - `page.request.get` → HTTP 403
  - `page.goto` 直接導航到 CSV → HTTP 400
- **成功方法**: 用 Playwright 開啟真實瀏覽器，手動登入 CME 帳號後，在已登入的頁面 context 中用 `page.evaluate(fetch(...))` 取得 CSV 內容

### Playwright 踩坑記錄
1. 背景執行（Shell `block_until_ms=0`）不支援 `input()`，會直接 `EOFError` → 改用信號檔（`_cme_login_done.txt`）偵測機制
2. CME 首頁 `page.wait_for_load_state("networkidle")` 會 timeout（首頁持續載入廣告/追蹤資源）→ 直接刪除此等待
3. 導航到 FTP 頁面可能被 SSO 重定向中斷（`Page.goto: Navigation interrupted by another navigation to auth.cmegroup.com`）→ 改用 `wait_until="domcontentloaded"` 並加重試迴圈

### 最終可行流程
```
Playwright launch(headless=False) 
  → page.goto("https://www.cmegroup.com/") 
  → 使用者手動登入 
  → 信號檔觸發 
  → page.goto(FTP_URL, wait_until="domcontentloaded")
  → page.evaluate("fetch(csv_url, {credentials: 'include'})") 
  → 儲存 CSV
```

## 結果

成功下載 6 個 OISUSD CSV（3/24~3/31），CSV 格式：

```csv
CURVE_NAME,TENOR,RATE
USD FEDFUNDS 1D,1 Year,3.657723
USD FEDFUNDS 1D,2 Years,3.560841
USD FEDFUNDS 1D,5 Years,3.555482
USD FEDFUNDS 1D,10 Years,3.813434
USD FEDFUNDS 1D,30 Years,4.05584
```

**可用期限**: 1Y, 2Y, 5Y, 10Y, 30Y  
**缺少期限**: 1M, 3M, 6M（無短期限數據）

### 與 MacroMicro 數值比較（3/20）
| 來源 | OIS 1Y |
|------|--------|
| MacroMicro (3/20) | 3.7386 |
| CME FTP (3/24) | 3.7640 |

數值接近但不完全一致，可能因定價時間點或 Fed Funds vs SOFR 基準差異。

## 結論

- CME FTP **有 1Y 但沒有 3M**，無法完整替代 MacroMicro 計算 1Y-3M 利差
- CME FTP 只保留最近 ~6 天，不適合作為歷史資料來源
- 下載需要 CME 帳號登入 + Playwright 瀏覽器 session，無法全自動化
- MacroMicro OIS 延遲為資料來源端問題，建議等待自動追上
- 如需更即時的 3M OIS，可嘗試 Chatham Financial 免費帳號或 BlueGamma API
