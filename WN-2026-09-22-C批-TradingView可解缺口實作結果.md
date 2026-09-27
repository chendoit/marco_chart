# WN-C批: TradingView 管線可解缺口 — 實作結果 (2026-09-22)

> 承接 `WN-2026-09-22-B批-16條缺口review清單.md`。針對「TV 能不能解決這 16 條」做了逐條
> symbol 查證與實測,可解的 4 條已經落地(新增 `get_tradingview_series.py`,照本專案
> 2026-09-22 起的慣例——舊版 `get_*.py` 腳本風格、掛進 `get_all_series_data.py` 的
> `tasks` list、逐日期 merge + `assert not lost` 防呆——已實跑寫回 production pkl),
> 其餘結論(含一條「查了但反而更差,不採用」的重要負向結果)回補進 B 批文件。
>
> 前置:`C:/code/2026-04-05-tradingview-control/tv_daily_export.py`
> (見 `WN-2026-04-05-TradingView-Daily-Data-Export.md`),TradingView Desktop + CDP 9222。
> **注意**:這是另一個獨立專案,不在本 repo 裡,要先手動在那邊跑過一次才會有
> `tv_export/*.pkl` 可讀。`C:/code/2026-09-11-fincept-terminal/` 只作參考(裡面
> `migration/fetch_mapped.py` 的 ECB 代打版 dispatch 本次**沒有**改動,維持原樣)。

## 結論總覽

| sid | 項目 | 結果 | TV symbol | 重疊誤差 |
|---|---|---|---|---|
| 1916 | germany-bond-10-year | ✅ 已上線 | `TVC:DE10Y` | 中位 0.18% |
| 4448 | de-us-10y-spread | ✅ 已上線 | `TVC:US10Y − TVC:DE10Y` | 中位 2.14% |
| 18331 | sp500-50ma-breadth | ✅ 已上線 | `INDEX:S5FI` | **0.000%** |
| 22718 | sp-500-200ma-breadth | ✅ 已上線 | `INDEX:S5TH` | **0.000%** |
| 8219 | WTI 現貨 | ❌ 測了不採用 | `TVC:USOIL` | 中位 2.13%(比現有 CL=F 的 1.78% 差) |
| 3776 | CRB 指數 | ⛔ 卡資料訂閱 | `FTSE:TRJEFFCRB` | 抓不到 OHLCV(帳號無 FTSE 訂閱) |
| 484/1645 | Fed 升息/降息機率 | ⛔ 卡資料訂閱 | `CBOT:ZQ` | 抓不到 OHLCV(帳號無 CBOT 訂閱) |

其餘 9 條(44/131/75/7359/254/3612/414/31742,以及 3776/484/1645 之外的說明)TV 幫不上忙,
原因與建議已回補進 B 批文件,不重複列在這裡。

---

## ✅ 已落地的 4 條

### 1916 — germany-bond-10-year(德國 10Y 殖利率)

- **舊狀況**:`fetch_ecb_ea10y()` 用 ECB 歐元區整體 10Y 代打,`mapped_status.json` 標
  `approx 11.5%(ECB EA vs 德國Bund基準差)`——方法論本身不對,歐元區整體 ≠ 德國一國。
- **新作法**:`tv_daily_export.py` 的 `de10y` job(`TVC:DE10Y` close)產出
  `tv_export/tv_TVC-DE10Y_D.pkl`,本專案新增 `get_tradingview_series.py` 讀這份 pkl,
  merge 進 `series_1916.pkl`(舊資料保留,重疊日期用 TV 覆蓋,新日期 append)。
- **驗證**:與舊 production pkl(`data/series_1916.pkl`,M² 原始資料)重疊 9 天比對,
  中位差 **0.18%**、最大 0.494% — 這裡的「舊 pkl」本身就是真正的德國 10Y(不是
  `migration/fetch_mapped.py` 那份 ECB 代打版),兩者這麼接近印證 TV 給的也是真正德國 10Y。
- **落地**:`get_tradingview_series.py` 的 `JOBS[1916]`,已掛進
  `get_all_series_data.py` 的 `tasks`,已實跑,`data/series_1916.pkl`
  n=611(1979-12-25 ~ 2026-09-22,深歷史為 M² 原始資料,近一年用 TV 補上/更新)。

### 4448 — de-10-year-yield-spread-germany-us(美德 10Y 利差)

- **舊狀況**:`fetch_ecb_ea10y_spread()` = `DGS10 − ECB EA`,跟 1916 同樣的代打問題,
  `mapped_status.json` 只標 `approx (ECB EA)`,沒有精確數字。
- **新作法**:`de_us_spread` job(`TVC:US10Y − TVC:DE10Y`)→ `get_tradingview_series.py` 同法
  merge 進 `series_4448.pkl`。
- **驗證**:重疊 9 天中位差 **2.14%**,最大 5.75% — 比 1916 本身雜訊大一些(兩腳殖利率
  相減會放大誤差),但已經是有精確數字可查、方法論正確(兩個真實 10Y 相減)的版本,
  不再是「歐元區代打」這種結構性錯誤。
- **落地**:`get_tradingview_series.py` 的 `JOBS[4448]`,實跑後 `data/series_4448.pkl`
  n=539(1979-12-26 ~ 2026-09-21)。

### 18331 — sp500-50ma-breadth(S&P500 站上 50 日均線比例)

- **舊狀況**:B 批文件判定這條「口徑完全不同要重做」——舊版用 `^SPX` 指數層級的
  close/MA50(99-107% 窄幅震盪),不是成分股 breadth(舊 pkl 是 51-64%)。
- **新作法**:TradingView symbol search 找到 `INDEX:S5FI`
  ("S&P 500 Stocks Above 50-Day Average"),就是官方成分股 breadth 指數本身,不用自己爬
  500 檔算。`sp500_50ma_breadth` job(`INDEX:S5FI` close)→ merge 進 `series_18331.pkl`。
- **驗證**:與舊 pkl 重疊 9 天比對,**中位差 0.000%**(2026-07-30: 63.61=63.61,
  2026-08-18: 59.56=59.56,2026-08-19: 59.76=59.76 完全一致)——這代表舊 M² pkl 原本用的
  資料源本來就是同一份官方指數,現在直接接上 TV 版本零誤差。
- **落地**:`get_tradingview_series.py` 的 `JOBS[18331]`,實跑後 `data/series_18331.pkl`
  n=523(1990-03-13 ~ 2026-09-21,深歷史沿用 M² 原始 pkl,近一年用 TV 補上/更新)。

### 22718 — sp-500-200ma-breadth(S&P500 站上 200 日均線比例)

- **舊狀況**:B 批文件說方法論對(真的抓 500 檔成分股用 curl_cffi 算 breadth)但有
  6.85% 系統性偏高,懷疑是成分股清單版本或複權方式跟 M² 不一致。
- **新作法**:`INDEX:S5TH`("S&P 500 Stocks Above 200-Day Average")同樣是官方指數,
  `sp500_200ma_breadth` job → merge 進 `series_22718.pkl`。
- **驗證**:重疊 9 天**中位差 0.000%**(2026-07-16: 69.38=69.38,2026-08-18: 68.12=68.12,
  2026-08-19: 72.11=72.11)——完全取代掉原本 6.85% 偏差的 curl_cffi 爬蟲版,不用再猜是
  成分股清單還是複權方式的問題。
- **落地**:`get_tradingview_series.py` 的 `JOBS[22718]`,實跑後 `data/series_22718.pkl`
  n=519(1990-10-15 ~ 2026-09-21)。

---

## ❌ 測了但不採用:8219(WTI 現貨)

- 原本判斷「`TVC:USOIL` 是真正 spot/CFD 報價,理論上該比 yfinance 近月期貨 `CL=F` 更貼近
  現貨定義」,實測結果相反:
  - `TVC:USOIL` vs 舊 pkl 重疊 6 天中位差 **2.13%**(最大 7.74%)
  - 現行 `CL=F` 方案 `mapped_status.json` 已測得 **1.78%**
- `CL=F` 反而比 `USOIL` 更貼近舊 pkl 的口徑,大概是 `TVC:USOIL` 這種券商 CFD 報價本身
  跟不同 broker 的點差/結算時間有關,不保證比近月期貨更「現貨」。
- **決定:維持現行 `get_yfinance_series.py` 的 `CL=F` 方案,不換成 TV。** 測試結果記在這份
  文件與 B 批文件裡,避免之後重複嘗試同一個死路;`tv_daily_export.py` 的 `wti_spot` job
  保留(已能正常抓到 `TVC:USOIL`),只是沒有接進 `get_tradingview_series.py` 的 `JOBS`。

---

## ⛔ 查到 symbol,但這個 TradingView 帳號抓不到資料

### 3776 — CRB 指數

- `FTSE:TRJEFFCRB`(Thomson Reuters/CoreCommodity CRB Index,量級跟文件講的 ~397 吻合)
  在 symbol search 查得到,但 `ohlcv` 一直回 `"Could not extract OHLCV data. The chart may
  still be loading."`,重試多次、切別的 symbol(如 `TVC:DE10Y`)驗證圖表本身是正常的,
  只有 `FTSE:` 這個 exchange 前綴的 symbol 卡住——判斷是這個帳號沒有 FTSE/Refinitiv 的
  付費資料權限。
- 備選 `INDEX:CRBS`("CRB Spot Index")**可以正常抓到**(數值 530 左右),但這是不同編制
  方法的舊版現貨指數(不是文件要的 TR/CoreCommodity 版),量級跟目標 397 對不上,不算
  乾淨解法,沒有比繼續用 DJP 做線性映射更好,故不採用。
- **維持 B 批原建議**:要嘛做 DJP→CRB 的線性映射,要嘛查 TradingView 付費方案能不能解鎖
  FTSE 資料。

### 484 / 1645 — Fed 升息/降息機率

- 找到 `CBOT:ZQ`(30 Day Federal Funds Futures,`cme-fedwatch` 套件內部算法用的正是這個
  合約)和 `ICEUS:ZQ1!`,兩個都一樣抓不到 OHLCV,同樣判斷是 CBOT/ICE 期貨資料權限問題。
- 這條原本最有機會解決「CME 免費 feed 只留 5 天、無法回補歷史」的限制——TV 免費帳號
  日線通常留約 500 根,遠勝 CME 的 5 天。可惜卡在資料訂閱,拿不到。
- **維持 B 批原建議**:走 `cme-fedwatch` 套件方案(接受無法回補歷史,只能上線後逐日累積),
  或評估升級 TradingView 資料訂閱(含 CBOT)划不划算。

---

## 檔案異動

| 檔案 | 異動 |
|---|---|
| `C:\code\2026-04-05-tradingview-control\tv_daily_export.py` | `JOBS` 新增 3 塊:`sp500_50ma_breadth`(`INDEX:S5FI`)、`sp500_200ma_breadth`(`INDEX:S5TH`)、`wti_spot`(`TVC:USOIL`,已產出但最終不採用) |
| `C:\code\2025-12-05-MacroMicro-Data\get_tradingview_series.py` | **新檔**。讀 `tv_export/*.pkl`,逐日期 merge(`assert not lost` 防呆)進 `series_{1916,4448,18331,22718}.pkl`,照本專案既有 `get_yfinance_series.py` 的既定模式 |
| `C:\code\2025-12-05-MacroMicro-Data\get_all_series_data.py` | import + `tasks` 新增一行,掛進每日排程 |
| `C:\code\2025-12-05-MacroMicro-Data\data\series_{1916,4448,18331,22718}.pkl` | 已實跑寫入(merge,非覆蓋;深歷史保留,近一年用 TV 更新/補上) |

`C:\code\2026-09-11-fincept-terminal\` 這次**沒有改動**——一開始誤把 `migration/fetch_mapped.py`
也改了一版,發現跟 2026-09-22 的專案決策(M² 替代工作一律在主工作樹用舊版 `get_*.py`
風格做,fincept-terminal 只作參考、不寫入不執行)衝突,已全部還原。

## 之後每日重跑順序

```powershell
# 1) TradingView Desktop 開著,CDP 9222 活的,先跑 TV 那邊的 export
cd C:\code\2026-04-05-tradingview-control
venv\Scripts\python.exe tv_daily_export.py

# 2) 已掛進 get_all_series_data.py 的每日排程,會自動 merge;
#    要手動單獨測試也可以：
cd C:\code\2025-12-05-MacroMicro-Data
venv\Scripts\python.exe get_tradingview_series.py
```

兩支腳本都是 merge 語意,可以安全重跑;`tv_daily_export.py` 的 CDP preflight 沒開會直接
失敗退出,不會自動啟動/重啟 TradingView。`get_tradingview_series.py` 若當天 TV 那邊沒重跑
(`tv_export/*.pkl` 還是舊檔),只是不會有新日期可 merge,不會報錯、也不會覆蓋壞資料。
