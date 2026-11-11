# fed-balance-sheet 抓取報告

抓取日：2026-11-09（任務日期）

## 資料來源

四個欄位皆取自 FRED 免 key 端點（與專案 `get_fred_csv.py` 相同抓法）：

- CSV：`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<代碼>`
- 系列頁（確認標題）：`https://fred.stlouisfed.org/series/<代碼>`

| 欄位 | FRED 代碼 | 取得方式 |
|---|---|---|
| `reserves_wed` | WRBWFRBL | fredgraph.csv 全歷史，空值（`.`）略過 |
| `reserves_wavg` | WRESBAL | 同上 |
| `bills_wed` | WSHOBL | 同上 |
| `treasuries_wed` | TREAST | 同上 |

- 四個代碼的系列頁標題都與任務指定的口徑相符（見下方「欄位與單位」）。
- 原始回應快取於 `raw/`：`<代碼>.csv`、`<代碼>.series_page.html`。
- `fetch.py` 以 `--start`（預設 `2015-01-01`）篩選輸出起日；只保留週三日期。

試過但未採用的來源：
- 聯準會官方 H.4.1 頁面（federalreserve.gov）：本次未抓取。四個系列在 FRED 上與 H.4.1 同源，且 FRED 是專案既有的抓法，因此採用 FRED。若需與官方頁面逐筆核對，需另行抓取。
- `raw/WLODLL.csv`、`raw/WLODLL.series_page.html`：為了查明 `series_7449` 的口徑，另以同樣的 fredgraph.csv 端點手動抓取（`fetch.py` 未包含此步驟；僅用於下方「series_7449 口徑比對」）。

## 欄位與單位

- 單位：百萬美元。FRED 的這四個系列原始單位即為百萬美元，**未做換算**。
- 日期：每列為週三（Wednesday）。
- 欄位說明（取自 FRED 系列頁標題）：
  - `reserves_wed`：WRBWFRBL，Liabilities and Capital: Other Factors Draining Reserve Balances: Reserve Balances with Federal Reserve Banks: **Wednesday Level**
  - `reserves_wavg`：WRESBAL，同上系列，**Week Average**
  - `bills_wed`：WSHOBL，Assets: Securities Held Outright: U.S. Treasury Securities: **Bills**: Wednesday Level
  - `treasuries_wed`：TREAST，Assets: Securities Held Outright: U.S. Treasury Securities: **All**: Wednesday Level

## 公布時間

- H.4.1（Factors Affecting Reserve Balances / Assets and Liabilities of Federal Reserve Banks）通常每週四下午公布，資料截至該週三（週三水位與週平均）。本次未從來源頁面核實此時程，屬一般性描述。
- 資料所屬日期（週三）與公布日期（通常為次日，週四）不同。遇假日時公布日可能順延。

## series_7449 口徑比對

本地 `data/series_7449.pkl`（標題 `us-fed-excess-reserves-weekly`，1297 筆，1984-01-04 ~ 2026-11-04）：

- 較接近 **`reserves_wed`**。
- verify.py 印出的差異（近 20 筆差異中位數）：
  - `reserves_wed` vs `series_7449`：**0** 百萬美元
  - `reserves_wavg` vs `series_7449`：**21049** 百萬美元
- 逐日期比對（兩者重疊 618 個週三）：
  - 與 `reserves_wed` 完全相等：467 筆；不相等 151 筆（差值中位數 1 百萬美元，最大 92 百萬美元，最早 2015-01-28、最晚 2026-10-14，符合小幅修正或快照差異）。
  - 與 `reserves_wavg` 完全相等：0 筆。
- 另見 `raw/WLODLL.csv`：`get_fred_csv.py` 中 sid 7449 的抓取代碼為 WLODLL；該代碼 1247 個重疊日期與 `series_7449` 完全相等，且與 `reserves_wed` 的相等情形相同。
- 標題不一致之處（僅記錄事實）：
  - 本地標題為「超額準備金（excess reserves）」，但數值與 `reserves_wed`（準備金週三水位）相同，量級約 2.9 兆美元。
  - FRED 上 WLODLL 的系列頁標題為「Other Deposits Held by Depository Institutions: Wednesday Level」，與其數值的對應關係同樣不一致。

## 2026-10-28 數字（僅列數字）

| 欄位 | 2026-10-28 | 2026-10-21 | 差額（10-28 減 10-21） |
|---|---|---|---|
| `reserves_wed` | 2,895,236 | 2,969,522 | -74,286 |
| `reserves_wavg` | 2,893,770 | 2,962,607 | -68,837 |

單位：百萬美元。

## 實測結果

- CSV：`fed_balance.csv`
- 列數：618（不含表頭）
- 起訖日：2015-01-07 ~ 2026-11-04（皆為週三）
- 空值：0
- 最新 5 筆：

```
date,reserves_wed,reserves_wavg,bills_wed,treasuries_wed
2026-10-07,3022066,3029659,562157,4566384
2026-10-14,3030854,3022140,566048,4570552
2026-10-21,2969522,2962607,567875,4572654
2026-10-28,2895236,2893770,571528,4576582
2026-11-04,2962804,2930088,573355,4578777
```

- verify.py 完整輸出：

```
ok   欄位前段為 ['date', 'reserves_wed', 'reserves_wavg', 'bills_wed', 'treasuries_wed']（實際 ['date', 'reserves_wed', 'reserves_wavg', 'bills_wed', 'treasuries_wed']）
ok   主鍵 ['date'] 不重複
ok   依 ['date'] 升冪
ok   日期都是週三
ok   最新 >= 2026-11-04（2026-11-04）
ok   起始 <= 2018-01-03（2015-01-07）
ok   reserves_wed 近期完整且為正
ok   reserves_wavg 近期完整且為正
ok   bills_wed 近期完整且為正
ok   treasuries_wed 近期完整且為正
ok   reserves_wed 單位為百萬美元
info reserves_wed vs series_7449 近 20 筆差異中位數 0（百萬美元）
info reserves_wavg vs series_7449 近 20 筆差異中位數 21049（百萬美元）
info 近期：
      date  reserves_wed  reserves_wavg  bills_wed  treasuries_wed
2026-10-07       3022066        3029659     562157         4566384
2026-10-14       3030854        3022140     566048         4570552
2026-10-21       2969522        2962607     567875         4572654
2026-10-28       2895236        2893770     571528         4576582
2026-11-04       2962804        2930088     573355         4578777
PASS fed-balance-sheet
```

## 缺口與異常

- 缺口：無。四個欄位在 2015-01-07 ~ 2026-11-04 的所有週三皆有值。
- 起始日：輸出起於 2015-01-07（比任務要求的 2018-01-03 更早，為預設 `--start` 的結果）。
- `bills_wed` 為 0 的情形：
  - 2015 年起至 2018-08-15 皆為 0；首個非零值為 2018-08-22。
  - 共 215 週為 0，最後一個 0 為 2019-08-14。
  - 以上為來源原始數值，未做處理。
- 口徑：四個系列皆為 FRED 現行版本；歷史數值可能經過聯準會修正，本次未比對發布時的初值快照。
- 商品上市日：不適用（H.4.1 系列）。
