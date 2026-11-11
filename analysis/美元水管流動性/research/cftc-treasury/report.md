# 美債期貨 TFF 部位（cftc-treasury）抓取報告

抓取日：2026-11-09。只取得資料，未做分析。

## 資料來源

- 來源：CFTC Public Reporting（Socrata API），資料集 `gpe5-46if`（Traders in Financial Futures，Futures Only）。
  - 基底網址：`https://publicreporting.cftc.gov/resource/gpe5-46if.json`
  - 取得方式：`fetch.py` 以 `cftc_contract_market_code` 逐一查詢 6 個合約，條件為 `futonly_or_combined='FutOnly'` 且 `report_date_as_yyyy_mm_dd >= --start`，依報告日升冪，單次 `$limit=50000`（各合約實際筆數皆遠低於上限）。
  - 每個合約的來源原始回應另存於 `raw/{代碼}.json`。
  - 每列都檢查 `futonly_or_combined == "FutOnly"`，非 FutOnly 會中止。
- 欄位對應（來源欄位名稱）：
  - `open_interest` ← `open_interest_all`
  - `lev_long` ← `lev_money_positions_long`；`lev_short` ← `lev_money_positions_short`
  - `lev_net` = `lev_long - lev_short`（唯一衍生欄位）
  - `asset_mgr_long` ← `asset_mgr_positions_long`；`asset_mgr_short` ← `asset_mgr_positions_short`
  - `dealer_long` ← `dealer_positions_long_all`；`dealer_short` ← `dealer_positions_short_all`
- 未使用的來源：
  - 同一 Socrata 平台的 Legacy 報告（`6dca-aqww`，`get_aud_nzd_series.py` 用的那個）：Legacy 不含 TFF 的槓桿基金、資產管理、交易商分類，故不用於本任務（僅參考該檔的程式，未查詢此資料集）。
  - 同一資料集中 `futonly_or_combined = Combined` 的列：依 prompt 要求不用，抓取條件已限定 FutOnly。
  - CFTC 歷史 txt/zip 檔：未嘗試，因 Socrata 已可取得完整欄位。
- 參考：`get_aud_nzd_series.py` 第 197–283 行的 TFF 抓法（同一資料集、同一欄位的 `lev_money`、`asset_mgr`、`dealer` 命名）。本任務未修改該檔。

## 欄位與單位

| 欄位 | 說明 | 單位 | 來源原始名稱 |
|---|---|---|---|
| date | 報告日（as-of 日，通常週二） | YYYY-MM-DD | `report_date_as_yyyy_mm_dd` |
| contract | 合約（照 prompt 寫） | — | — |
| open_interest | 總持倉 | 口 | `open_interest_all` |
| lev_long | 槓桿基金多頭 | 口 | `lev_money_positions_long` |
| lev_short | 槓桿基金空頭 | 口 | `lev_money_positions_short` |
| lev_net | lev_long − lev_short | 口 | 衍生 |
| asset_mgr_long | 資產管理多頭 | 口 | `asset_mgr_positions_long` |
| asset_mgr_short | 資產管理空頭 | 口 | `asset_mgr_positions_short` |
| dealer_long | 交易商多頭 | 口 | `dealer_positions_long_all` |
| dealer_short | 交易商空頭 | 口 | `dealer_positions_short_all` |

合約代碼與來源商品名稱（已於資料內確認，6 個代碼皆正確，未更換）：

| contract | CFTC 代碼 | 來源 contract_market_name |
|---|---|---|
| 2Y | 042601 | UST 2Y NOTE |
| 5Y | 044601 | UST 5Y NOTE |
| 10Y | 043602 | UST 10Y NOTE |
| ULTRA10Y | 043607 | ULTRA UST 10Y |
| TBOND | 020601 | UST BOND |
| ULTRABOND | 020604 | ULTRA UST BOND（另有 2025-09-09、2025-09-16 兩列寫作 `ULTRA US T BOND`，代碼相同，視為同一合約） |

CSV 排序：先依 contract 字串升冪（10Y, 2Y, 5Y, TBOND, ULTRA10Y, ULTRABOND），再依 date 升冪。主鍵 (contract, date) 無重複。

## 公布時間

- CFTC 通常於報告日（週二）之後的週五（美東時間下午 3:30 左右）公布該週 TFF 資料。遇美國假日，報告日與公布時間會順延。這是 CFTC 的一般公布慣例，本任務未逐筆核對公布時間戳。
- 本 CSV 的 `date` 是報告日，不是公布日。
- 來源 API 只提供報告日（`report_date_as_yyyy_mm_dd`）與 `yyyy_report_week_ww`，未提供公布時間戳。

## 實測結果

- 執行：`PYTHONUTF8=1 venv/Scripts/python.exe analysis/美元水管流動性/research/cftc-treasury/fetch.py`（預設 `--start 2006-01-01`）。
- CSV 列數：5686 列資料（不含表頭）。

各合約列數與起訖日：

| contract | 列數 | 起 | 迄 |
|---|---|---|---|
| 2Y | 1065 | 2006-06-13 | 2026-11-03 |
| 5Y | 1065 | 2006-06-13 | 2026-11-03 |
| 10Y | 1065 | 2006-06-13 | 2026-11-03 |
| ULTRA10Y | 555 | 2016-03-08 | 2026-11-03 |
| TBOND | 1065 | 2006-06-13 | 2026-11-03 |
| ULTRABOND | 871 | 2010-03-02 | 2026-11-03 |

各欄位皆無缺值。

最新 5 筆（每個合約）：

```
      date contract  open_interest  lev_long  lev_short  lev_net  asset_mgr_long  asset_mgr_short  dealer_long  dealer_short
2026-10-06      10Y        5742990    510611    2650396 -2139785         3602149           774010        98637        740670
2026-10-13      10Y        5819512    489362    2695299 -2205937         3672796           774234       109711        742524
2026-10-20      10Y        5868295    567553    2674777 -2107224         3675600           750184       119383        801611
2026-10-27      10Y        5881588    506310    2733585 -2227275         3709233           709069       153034        783060
2026-11-03      10Y        5947433    585873    2848183 -2262310         3730323           700087       129667        741551
2026-10-06       2Y        4485811    693301    1950785 -1257484         2471312           792225        98563        607014
2026-10-13       2Y        4554153    715286    2082694 -1367408         2532974           737108        99693        581414
2026-10-20       2Y        4533571    771136    2056684 -1285548         2461884           738304        97565        591682
2026-10-27       2Y        4524447    764270    2121928 -1357658         2514138           676647        88702        604376
2026-11-03       2Y        4464182    667084    2117976 -1450892         2541571           664959        86226        554796
2026-10-06       5Y        6758624    541071    2668638 -2127567         4218531          1304245        83428        919320
2026-10-13       5Y        6874204    533600    2637991 -2104391         4261442          1276490        82167       1000211
2026-10-20       5Y        6715851    442604    2560148 -2117544         4252156          1324104        89747        940217
2026-10-27       5Y        6585711    466758    2544618 -2077860         4225319          1286418        86265        936808
2026-11-03       5Y        6719878    372208    2687724 -2315516         4470315          1292660        97299        930675
2026-10-06     TBOND        1898067    172246     361924  -189678         1096523           690895        44875        237552
2026-10-13     TBOND        1849727    173217     327237  -154020         1072776           681242        43520        222819
2026-10-20     TBOND        1785457    169144     331901  -162757         1087469           699462        36715        219421
2026-10-27     TBOND        1890568    197843     348236  -150393         1141449           757468        44935        263251
2026-11-03     TBOND        1930138    209524     375781  -166257         1164793           749414        45950        285264
2026-10-06  ULTRA10Y        2593056    137183     456244  -319061         1286249           505517        78514        422898
2026-10-13  ULTRA10Y        2643685    125835     461693  -335858         1342075           544581        75845        397037
2026-10-20  ULTRA10Y        2665818    158395     476872  -318477         1310503           573237        84060        393630
2026-10-27  ULTRA10Y        2607835    200203     458460  -258257         1229617           527662        80734        383739
2026-11-03  ULTRA10Y        2571983    186876     444977  -258101         1239607           524378        79447        395145
2026-10-06 ULTRABOND        2404377     58345     784602  -726257         1507861           752102        21456        110211
2026-10-13 ULTRABOND        2397995     60314     776043  -715729         1534413           757921        12577        110142
2026-10-20 ULTRABOND        2364949     66548     871356  -804808         1561446           712063        17625        111045
2026-10-27 ULTRABOND        2347429     67030     872858  -805828         1579626           721458        16188        128741
2026-11-03 ULTRABOND        2394358     85030     881259  -796229         1579929           704413        14562        163812
```

verify.py 完整輸出：

```
ok   欄位前段為 ['date', 'contract', 'open_interest', 'lev_long', 'lev_short', 'lev_net', 'asset_mgr_long', 'asset_mgr_short', 'dealer_long', 'dealer_short']（實際 ['date', 'contract', 'open_interest', 'lev_long', 'lev_short', 'lev_net', 'asset_mgr_long', 'asset_mgr_short', 'dealer_long', 'dealer_short']）
ok   主鍵 ['contract', 'date'] 不重複
ok   依 ['contract', 'date'] 升冪
ok   2Y 有資料
ok   2Y 最新為 2026-11-03（2026-11-03）
ok   2Y 起始 <= 2018-01-02（2006-06-13）
ok   2Y lev_net = lev_long - lev_short
ok   5Y 有資料
ok   5Y 最新為 2026-11-03（2026-11-03）
ok   5Y 起始 <= 2018-01-02（2006-06-13）
ok   5Y lev_net = lev_long - lev_short
ok   10Y 有資料
ok   10Y 最新為 2026-11-03（2026-11-03）
ok   10Y 起始 <= 2018-01-02（2006-06-13）
ok   10Y lev_net = lev_long - lev_short
ok   ULTRA10Y 有資料
ok   ULTRA10Y 最新為 2026-11-03（2026-11-03）
ok   ULTRA10Y 起始 <= 2018-01-02（2016-03-08）
ok   ULTRA10Y lev_net = lev_long - lev_short
ok   TBOND 有資料
ok   TBOND 最新為 2026-11-03（2026-11-03）
ok   TBOND 起始 <= 2018-01-02（2006-06-13）
ok   TBOND lev_net = lev_long - lev_short
ok   ULTRABOND 有資料
ok   ULTRABOND 最新為 2026-11-03（2026-11-03）
ok   ULTRABOND 起始 <= 2018-01-02（2010-03-02）
ok   ULTRABOND lev_net = lev_long - lev_short
ok   報告日絕大多數為週二
PASS cftc-treasury
```

## 缺口與異常

- 報告日非週二（14 個日期，為假日順延；各合約於同日出現，僅限已上市合約）：
  - 週一（13 個）：2006-07-03、2007-12-24、2007-12-31、2008-12-22、2009-11-09、2012-12-24、2012-12-31、2017-07-03、2018-12-24、2018-12-31、2020-12-21、2023-07-03、2025-11-10
  - 週三（1 個）：2007-01-03（只有 10Y、2Y、5Y、TBOND 四個合約當時已上市）
  - 驗收項「報告日絕大多數為週二」已通過。
- 缺的週（週二日曆上無列，來源未提供，未插補）：
  - 10Y、2Y、5Y、TBOND：14 週，為 2006-07-04、2007-01-02、2007-12-25、2008-01-01、2008-12-23、2009-11-10、2012-12-25、2013-01-01、2017-07-04、2018-12-25、2019-01-01、2020-12-22、2023-07-04、2025-11-11。多數為美國假日週（7/4、12/25、1/1）；2025-11-11 為 Veterans Day 當週。2025-11-11 缺口是否與 2025 年秋季美國政府停擺有關，本任務未在來源中確認。
  - ULTRA10Y：8 週，為 2016-03-15、2016-03-29、2017-07-04、2018-12-25、2019-01-01、2020-12-22、2023-07-04、2025-11-11。其中 2016-03-15、2016-03-29 非假日週，來源無列原因未查明。
  - ULTRABOND：8 週，為 2012-12-25、2013-01-01、2017-07-04、2018-12-25、2019-01-01、2020-12-22、2023-07-04、2025-11-11。
- 商品上市日：ULTRA10Y 自 2016-03-08 起有資料；ULTRABOND 自 2010-03-02 起有資料。其餘四個合約最早列為 2006-06-13。
- 商品名稱：ULTRABOND 在 2025-09-09 與 2025-09-16 兩列的 `contract_market_name` 寫作 `ULTRA US T BOND`，其餘 869 列為 `ULTRA UST BOND`。代碼 020604 一致，CSV 中以 `ULTRABOND` 統一。
- 口徑：全部列都以 Futures Only 條件抓取，口徑一致。未逐欄核對 CFTC 歷次口徑調整公告，口徑變更的判讀留給後續分析。
