# E3：Fed 對外國官方機構（FIMA）附買回協議餘額（fima-repo）

## 資料來源

- **主要來源（FRED，免 key fredgraph.csv）**
  - `fima_repo_wed`：`https://fred.stlouisfed.org/graph/fredgraph.csv?id=H41RESPPALGTRFNWW`
    - FRED 系列頁：`https://fred.stlouisfed.org/series/H41RESPPALGTRFNWW`
    - 系列標題：`Assets: Other: Repurchase Agreements - Foreign Official: Wednesday Level`
    - Fed 原始代碼：`RESPPALGTRF_N.WW`（H.4.1 Factors Affecting Reserve Balances）
  - `fima_repo_wavg`：`https://fred.stlouisfed.org/graph/fredgraph.csv?id=H41RESPPALGTRFXAWNWW`
    - FRED 系列頁：`https://fred.stlouisfed.org/series/H41RESPPALGTRFXAWNWW`
    - 系列標題：`Assets: Other: Repurchase Agreements - Foreign Official: Week Average`
    - Fed 原始代碼：`RESPPALGTRF_XAW_N.WW`
  - 取得方式：`fetch.py` 以 urllib 直接下載 CSV 與系列頁（UA 為 research-fetch，timeout 60 秒，請求間隔 1 秒）。原始回應快取於 `raw/`。
- **交叉核對來源（非輸出用）**：Fed Data Download Program 完整套件 `https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=zip`，存於 `raw/H41_all.zip`。內含 `H41_data.xml`，其中 `RESPPALGTRF_N.WW` 與 `RESPPALGTRF_XAW_N.WW` 的 1247 筆觀察值與 FRED 完全一致（見下）。
- **試過但不用的系列**
  - `WORAL`（Assets: Other: Repurchase Agreements: Wednesday Level）：是全部附買回餘額，不是 FIMA 分項。
  - `WREPO`（Assets: Other: Repurchase Agreements: Week Average）：同上，全部附買回，不是 FIMA 分項。
  - `WREPOFOR`、`WLRRAL`：是 FIMA 的**反向**附買回（負債端，Fed 對外國官方的逆回購），不是 Fed 放出的附買回，不採用。
  - 猜測代碼 `RPONFORDS`、`RPONFOR`、`WFORRPO`、`FORRPO`、`H41RESPPALGTRFNWA` 等在 FRED 皆為 404，不存在。
  - FRED 搜尋頁（`searchresults?st=Repurchase+Agreements+Foreign+Official`）列出 `H41RESPPALGTRFNWW` 與 `H41RESPPALGTRFXAWNWW`（後者即 week average，代碼由此確認）。
  - Fed H.4.1 release 頁（`federalreserve.gov/releases/h41/current/h41.htm`）只有最新一週數字，沒有歷史序列；頁面上 Foreign official repurchase 的最新一週值為 0，與 CSV 最後一列一致。

## 欄位與單位

| 欄位 | 說明 | 單位 | 來源代碼（FRED / Fed） |
|---|---|---|---|
| `date` | 週三日期（YYYY-MM-DD），H.4.1 的週結算日 | — | — |
| `fima_repo_wed` | 附買回協議（外國官方）餘額，週三水位（Wednesday level） | 百萬美元 | `H41RESPPALGTRFNWW` / `RESPPALGTRF_N.WW` |
| `fima_repo_wavg` | 同上，當週平均（week average，以截至該週三的一週為準） | 百萬美元 | `H41RESPPALGTRFXAWNWW` / `RESPPALGTRF_XAW_N.WW` |

- FRED 頁面單位標示為 `Millions of U.S. Dollars`，Not Seasonally Adjusted，不需換算。
- 數值保持來源原始精度（FRED 回傳為整數字串，如 `60000`），沒有做任何換算或插補。
- 資產端附買回是 Fed 放給外國官方機構的附買回（Fed 的資產），與 `reserves`、`bills` 的口徑不同。

## 公布時間

- H.4.1 通常每週四公布（美東時間下午 4:30 左右），內容為**截至該週三**的數字，即資料所屬日期（週三）比公布日（週四）早 1 天。Fed XML 套件的 `Prepared` 時間為 `2026-11-05T13:42:06Z`（週四），對應的最後觀察值為 `2026-11-04`（週三）。
- FRED 上的日期即為 H.4.1 的週三日期，無額外延遲；資料所屬日期與公布日期不同（差 1 天）。
- 需注意：Fed 的 Data Download Program 套件頁面有公告，DDP 的「Build Your Package」功能預計於 11/9 當週移除，並建議改用 FRED。本任務的主要來源是 FRED，不受影響；`raw/H41_all.zip` 是在 11/9 下載的最後備援。

## 實測結果

- CSV：`fima_repo.csv`，UTF-8，主鍵 `date`，升冪。
- 列數：**462 列**（週三，2018-01-03 至 2026-11-04，無重複、無缺列）。
- 起訖日：`2018-01-03` ～ `2026-11-04`。
- 最新 5 筆：

| date | fima_repo_wed | fima_repo_wavg |
|---|---|---|
| 2026-10-07 | 0 | 0 |
| 2026-10-14 | 0 | 0 |
| 2026-10-21 | 0 | 0 |
| 2026-10-28 | 0 | 0 |
| 2026-11-04 | 0 | 0 |

- 2026-09 到 2026-11-04 逐週：

| date | fima_repo_wed | fima_repo_wavg |
|---|---|---|
| 2026-09-02 | 0 | 0 |
| 2026-09-09 | 1 | 0 |
| 2026-09-16 | 1 | 1 |
| 2026-09-23 | 0 | 0 |
| 2026-09-30 | 0 | 0 |
| 2026-10-07 | 0 | 0 |
| 2026-10-14 | 0 | 0 |
| 2026-10-21 | 0 | 0 |
| 2026-10-28 | 0 | 0 |
| 2026-11-04 | 0 | 0 |

- 歷史最大值（以 FRED 全部可得資料，2002-12-18 起，計算）：
  - `fima_repo_wed`：**60000**（百萬美元，約 600 億）於 **2023-03-22**
  - `fima_repo_wavg`：**59286**（百萬美元）於 **2023-03-29**
  - CSV 區間（2018 起）內，任一欄非零的週數為 117 週；首筆非零為 2020-04-08，末筆非零為 2026-09-16。
- 交叉核對（FRED vs Fed 套件 `H41_data.xml`，全部 1247 筆，2002-12-18 至 2026-11-04）：兩欄皆 0 筆差異。

- `verify.py fima-repo` 完整輸出（`raw/verify_output.txt`）：

```
ok   欄位前段為 ['date', 'fima_repo_wed', 'fima_repo_wavg']（實際 ['date', 'fima_repo_wed', 'fima_repo_wavg']）
ok   主鍵 ['date'] 不重複
ok   依 ['date'] 升冪
ok   日期都是週三
ok   起始 <= 2018-01-03（2018-01-03）
ok   最新 >= 2026-11-04（2026-11-04）
ok   fima_repo_wed 無空值且非負
ok   fima_repo_wavg 無空值且非負
ok   每週都有列
info 近期：
      date  fima_repo_wed  fima_repo_wavg
2026-09-16              1               1
2026-09-23              0               0
2026-09-30              0               0
2026-10-07              0               0
2026-10-14              0               0
2026-10-21              0               0
2026-10-28              0               0
2026-11-04              0               0
PASS fima-repo
```

## 缺口與異常

- **無缺值**：FRED 回傳的 1247 筆（2002 起）中沒有 `.`（缺值標記）；2018 起的 462 列兩欄皆有值。
- **0 值保留**：依任務要求，FIMA 沒動用的週為 0，保留為 0，未當作缺值。2018 起大部分週為 0；2026-09-02 到 2026-11-04 之間只有 2026-09-09（wed=1）與 2026-09-16（wed=1、wavg=1）非零，其餘皆 0。
- **單位與值的量級**：值以百萬美元計，`1` 即 100 萬美元，非常小，屬 H.4.1 原始小額口徑，不是誤植。
- **口徑變更**：本任務未發現 H.4.1 對此系列的口徑變更註記（以 FRED 系列頁與 Fed XML 的 `Short Description` 核對，標題無 "Discontinued" 字樣）。
- **商品上市日**：不適用（H.4.1 系列，自 2002-12-18 起有資料）。
- **未處理的範圍**：`fetch.py` 預設 `--start 2018-01-03`；FRED 原始資料完整保留於 `raw/`，可用 `--start` 改為更早起點。
- **週日期定義**：`fima_repo_wavg` 的日期為該週的週三（週結算日），即當週平均的結束日。
