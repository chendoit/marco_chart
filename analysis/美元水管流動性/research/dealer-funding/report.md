# dealer-funding 報告（2026-11-10 取得）

## 資料來源
- **F1 `pd_financing.csv`**：NY Fed Primary Dealer Statistics，Markets API `https://markets.newyorkfed.org/api/pd/get/<keyid>.json`（清單 `/api/pd/list/timeseries.json`）。逐系列抓取，快取於 `raw/pd_*.json`。
- **F2 `repo_haircuts.csv`**：找不到逐日或逐筆的公開 haircut 序列（見下方「試過但不用」），改用 OFR Hedge Fund Monitor（SEC Form PF 彙總）的過度擔保率（over-collateralization rate），並附 SCOOS 擔保品條件調查。API：`https://data.financialresearch.gov/hf/v1/series/full?mnemonic=<mnemonic>`，快取於 `raw/hf_*.json`。
- **F4 `hedge_fund_leverage.csv`**：同一個 OFR Hedge Fund Monitor API（FPF-* 與 SCOOS-NET_HF_LEVERAGEUSE）。

試過但不用：
- OFR 主 API `https://data.financialresearch.gov/v1/`：只有 nypd、mmf、repo、fnyr、tyld 五個資料集；repo 資料集（164 個系列）只含利率與成交量（DVP、Tri-Party、GCF），名稱沒有 haircut／margin，因此不用於 F2。FPF 系列不在此 API，在 `/hf/v1/`。
- 未嘗試 SEC Private Funds Statistics 與 NY Fed 其他頁面（OFR 已涵蓋 Form PF 彙總，且預算有限）。
- 因此 F2 **沒有直接的 repo haircut 序列**；FPF 過度擔保率是「對沖基金所提供擔保品總值超出借款的百分比」，口徑與交易層級的 haircut 不同，僅為最接近的公開近似。

選了哪些、沒選哪些：
- F1 選：美債（不含 TIPS）淨部位與其中短票、各類擔保品的附買回（PDSORA）與附賣回（PDSIRRA）合計、美債證券借入／借出。沒選：各到期區間部位、轉手交易（PDTRAB）、依交易對手／期限（隔夜、定期、清算類型）拆分的子系列（清單共 1539 個）——超出主題需求，且會把整個資料集全抓。
- F4 選：GAV、GNE、NAV、依規模分組的槓桿比率、借款（repo、prime broker、其他有擔保）、Treasury 多空曝險、repo／reverse repo 資產類別金額、Macro／RV／Multi 策略槓桿。沒選：信用、股票、事件等其他策略槓桿、流動性期限分布、壓力測試、對手方集中度等。

## 欄位與單位
統一長表：`date,series_key,description,value,unit`。`description`、`unit` 取自來源（PD 的 API 未提供單位欄，來源資料說明為百萬美元，故標 `Millions of USD`；OFR 取 metadata 的 `unit.name`），未換算。

### pd_financing.csv（週頻，週三）
| series_key | 來源名稱 | 起訖 | 最新值 | 單位 |
|---|---|---|---|---|
| `PDPOSGS-B` | U.S. TREASURY SECURITIES (EXCLUDING TREASURY INFLATION-PROTECTED SECURITIES (TIPS)) BILLS: | 2018-01-03 ~ 2026-10-28 | 99857 | Millions of USD |
| `PDPOSGST-TOT` | Total - U.S. TREASURY SECURITIES (EXCLUDING TREASURY INFLATION-PROTECTED SECURITIES (TIPS) | 2018-01-03 ~ 2026-10-28 | 452759 | Millions of USD |
| `PDSIOSB-UTSETTOT` | Total - U.S. TREASURY SECURITIES (EXCLUDING TREASURY INFLATION-PROTECTED SECURITIES (TIPS) | 2018-01-03 ~ 2026-10-28 | 425849 | Millions of USD |
| `PDSIRRA-ABSTOT` | Total - Reverse Repurchase Agreements: Asset-backed securities | 2018-01-03 ~ 2026-10-28 | 8427 | Millions of USD |
| `PDSIRRA-CDTOT` | Total - Other Financing Activity, Securities Borrowed: Federal Agency and GSE Residential  | 2018-01-03 ~ 2026-10-28 | 51509 | Millions of USD |
| `PDSIRRA-ETOT` | Total - Reverse Repurchase Agreements: Equities | 2018-10-24 ~ 2026-07-08 | 0 | Millions of USD |
| `PDSIRRA-FGCMTOT` | Total - Reverse Repurchase Agreements: Federal Agency and GSE CMBS | 2022-01-12 ~ 2026-10-28 | 3043 | Millions of USD |
| `PDSIRRA-FGEMTOT` | Total - Reverse Repurchase Agreements: Federal Agency and GSE Securities (excluding MBS)  | 2018-01-03 ~ 2026-10-28 | 10829 | Millions of USD |
| `PDSIRRA-FGMTOT` | Total - Reverse Repurchase Agreements: Federal Agency and GSE Residential MBS | 2018-01-03 ~ 2026-10-28 | 391040 | Millions of USD |
| `PDSIRRA-OTOT` | Total - Reverse Repurchase Agreements: Other  | 2018-01-03 ~ 2026-10-21 | 30421 | Millions of USD |
| `PDSIRRA-UTSETTOT` | Total - Reverse Repurchase Agreements: U.S. Treasury securities (excluding TIPS) | 2018-01-03 ~ 2026-10-28 | 2.77552e+06 | Millions of USD |
| `PDSIRRA-UTSTTOT` | Total - Reverse Repurchase Agreements: U.S. Treasury Inflation-Protected Securities (TIPS) | 2018-01-03 ~ 2026-10-28 | 225842 | Millions of USD |
| `PDSOOS-UTSETTOT` | Total - U.S. TREASURY SECURITIES (EXCLUDING TREASURY INFLATION-PROTECTED SECURITIES (TIPS) | 2018-01-03 ~ 2026-10-21 | 138658 | Millions of USD |
| `PDSORA-ABSTOT` | Total - Repurchase Agreements: Asset-backed securities - Triparty (excluding GCF) | 2018-01-03 ~ 2026-10-28 | 18956 | Millions of USD |
| `PDSORA-CDTOT` | Total - Repurchase Agreements: Corporate Debt - Triparty (excluding GCF) | 2018-01-03 ~ 2026-10-28 | 170624 | Millions of USD |
| `PDSORA-ETOT` | Total - Repurchase Agreements: Equities - Triparty (excluding GCF) | 2018-01-10 ~ 2026-10-28 | 213261 | Millions of USD |
| `PDSORA-FGCMTOT` | Total - Repurchase Agreements: Federal Agency and GSE CMBS | 2022-01-05 ~ 2026-10-28 | 11637 | Millions of USD |
| `PDSORA-FGEMTOT` | Total - Repurchase Agreements: Federal Agency and GSE Securities (excluding MBS) | 2018-01-03 ~ 2026-10-28 | 30704 | Millions of USD |
| `PDSORA-FGMTOT` | Total - Repurchase Agreements: Federal Agency and GSE Residential MBS | 2018-01-03 ~ 2026-10-28 | 864398 | Millions of USD |
| `PDSORA-OTOT` | Total - Repurchase Agreements: Other  | 2018-01-03 ~ 2026-10-28 | 53915 | Millions of USD |
| `PDSORA-UTSETTOT` | Total - Repurchase Agreements: U.S. Treasury securities (excluding TIPS) | 2018-01-03 ~ 2026-10-28 | 3.06396e+06 | Millions of USD |
| `PDSORA-UTSTTOT` | Total - Repurchase Agreements: U.S. Treasury Inflation-Protected Securities (TIPS) | 2018-01-03 ~ 2026-10-28 | 275664 | Millions of USD |

註：`PDPOSGST-TOT` 為「多頭 − 空頭」淨部位。`PDSORA-*` 為附買回（repo，融資取得），`PDSIRRA-*` 為附賣回（reverse repo，融資提供）。

### repo_haircuts.csv（季頻）
| series_key | 來源名稱 | 起訖 | 最新值 | 單位 |
|---|---|---|---|---|
| `FPF-GAVN10_OCRATEALL_PERCENT` | Top 10 largest funds: over-collateralization rate (percent) | 2018-03-31 ~ 2026-06-30 | 0 | Percent |
| `FPF-GAVN10_OCRATEEXOTHER_PERCENT` | Top 10 largest funds: over-collateralization rate excluding other collateral (percent) | 2018-03-31 ~ 2026-06-30 | 0 | Percent |
| `FPF-GAVN11TO50_OCRATEALL_PERCENT` | Top 11-50 largest funds: over-collateralization rate (percent) | 2018-03-31 ~ 2026-06-30 | 7.6 | Percent |
| `FPF-GAVN11TO50_OCRATEEXOTHER_PERCENT` | Top 11-50 largest funds: over-collateralization rate excluding other collateral (percent) | 2018-03-31 ~ 2026-06-30 | 7.1 | Percent |
| `FPF-GAVN51_OCRATEALL_PERCENT` | Top 51+ largest funds: over-collateralization rate (percent) | 2018-03-31 ~ 2026-06-30 | 37.3 | Percent |
| `FPF-GAVN51_OCRATEEXOTHER_PERCENT` | Top 51+ largest funds: over-collateralization rate excluding other collateral (percent) | 2018-03-31 ~ 2026-06-30 | 22.9 | Percent |
| `FPF-OCRATEALL_PERCENT` | Qualifying Hedge Funds: over-collateralization rate for all collateral types (percent) | 2018-03-31 ~ 2026-06-30 | 15.3 | Percent |
| `FPF-OCRATECASHSEC_PERCENT` | Qualifying Hedge Funds: over-collateralization rate for cash and securities collateral (pe | 2018-03-31 ~ 2026-06-30 | 10.2 | Percent |
| `SCOOS-NET_COLLATTERMS` | Survey: collateral terms as most important reason for a change in credit terms (net count  | 2018-03-31 ~ 2026-09-30 | 0 | Net count of respondents |

註：`FPF-OCRATEALL_PERCENT` 為所有擔保品類型；`OCRATEEXOTHER` 排除其他擔保品；`GAVN10/11TO50/51` 為依總資產／淨資產比分組（≤10、11–50、≥51 倍）。`SCOOS-NET_COLLATTERMS` 為調查淨計數，非 haircut。

### hedge_fund_leverage.csv（季頻）
| series_key | 來源名稱 | 起訖 | 最新值 | 單位 |
|---|---|---|---|---|
| `FPF-ALLQHF_GAVN10_BORROWING_PERCENT` | Top 10 largest funds: share of borrowing (percent of total) | 2018-03-31 ~ 2026-06-30 | 32.1 | Percent of total |
| `FPF-ALLQHF_GAVN10_LEVERAGERATIO_AVERAGE` | Top 10 largest funds: leverage (equal-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 19.249 | Equal-weighted average ratio |
| `FPF-ALLQHF_GAVN11TO50_LEVERAGERATIO_AVERAGE` | Top 11-50 largest funds: leverage (equal-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 11.76 | Equal-weighted average ratio |
| `FPF-ALLQHF_GAVN51_LEVERAGERATIO_AVERAGE` | Top 51+ largest funds: leverage (equal-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 1.792 | Equal-weighted average ratio |
| `FPF-ALLQHF_GAV_SUM` | Qualifying Hedge Funds: gross assets (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 1.3863e+13 | U.S. dollars |
| `FPF-ALLQHF_GNE_SUM` | Qualifying Hedge Funds: gross notional exposure (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 4.5193e+13 | U.S. dollars |
| `FPF-ALLQHF_NAV_SUM` | Qualifying Hedge Funds: net assets (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 5.511e+12 | U.S. dollars |
| `FPF-ASSETCLASS_IRD_GNE_SUM` | Qualifying Hedge Funds: gross notional exposure to interest rate derivatives (U.S. dollars | 2018-03-31 ~ 2026-06-30 | 1.3902e+13 | U.S. dollars |
| `FPF-ASSETCLASS_LTREASURY_SUM` | Qualifying Hedge Funds: long U.S. Treasury exposure (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 2.362e+12 | U.S. dollars |
| `FPF-ASSETCLASS_REPO_REPO_SUM` | Qualifying Hedge Funds: repo exposure (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 3.283e+12 | U.S. dollars |
| `FPF-ASSETCLASS_REPO_REVERSEREPO_SUM` | Qualifying Hedge Funds: reverse repo exposure (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 1.32e+12 | U.S. dollars |
| `FPF-ASSETCLASS_STREASURY_SUM` | Qualifying Hedge Funds: short U.S. Treasury exposure (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 1.498e+12 | U.S. dollars |
| `FPF-ASSETCLASS_USGOV_GNE_SUM` | Qualifying Hedge Funds: gross notional exposure to U.S. government debt (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 3.964e+12 | U.S. dollars |
| `FPF-ASSETCLASS_USGOV_LGNE_SUM` | Qualifying Hedge Funds: long notional exposure to U.S. government debt (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 2.435e+12 | U.S. dollars |
| `FPF-ASSETCLASS_USGOV_SGNE_SUM` | Qualifying Hedge Funds: short notional exposure to U.S. government debt (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 1.529e+12 | U.S. dollars |
| `FPF-BORROW_OTHERSECURED_SUM` | Qualifying Hedge Funds: other secured borrowing (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 8.82e+11 | U.S. dollars |
| `FPF-BORROW_PRIMEBROKER_SUM` | Qualifying Hedge Funds: prime brokerage borrowing (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 3.688e+12 | U.S. dollars |
| `FPF-BORROW_REPO_GAVN10_PERCENT` | Top 10 largest funds: share of repo borrowing (percent of total) | 2018-03-31 ~ 2026-06-30 | 48.4 | Percent of total |
| `FPF-BORROW_REPO_GAVN11TO50_PERCENT` | Top 11-50 largest funds: share of repo borrowing (percent of total) | 2018-03-31 ~ 2026-06-30 | 35.9 | Percent of total |
| `FPF-BORROW_REPO_GAVN51_PERCENT` | Top 51+ largest funds: share of repo borrowing (percent of total) | 2018-03-31 ~ 2026-06-30 | 15.8 | Percent of total |
| `FPF-BORROW_REPO_SUM` | Qualifying Hedge Funds: repo borrowing (U.S. dollars) | 2018-03-31 ~ 2026-06-30 | 3.382e+12 | U.S. dollars |
| `FPF-STRATEGY_MACRO_LEVERAGERATIO_GAVWMEAN` | Macro strategy funds: leverage (gross asset-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 12.719 | Gross asset-weighted average ratio |
| `FPF-STRATEGY_MACRO_LEVERAGERATIO_NAVWMEAN` | Macro strategy funds: leverage (net asset-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 6.816 | Net asset-weighted average ratio |
| `FPF-STRATEGY_MULTI_LEVERAGERATIO_GAVWMEAN` | Multi strategy funds: leverage (gross asset-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 12.291 | Gross asset-weighted average ratio |
| `FPF-STRATEGY_MULTI_LEVERAGERATIO_NAVWMEAN` | Multi strategy funds: leverage (net asset-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 4.462 | Net asset-weighted average ratio |
| `FPF-STRATEGY_RV_LEVERAGERATIO_GAVWMEAN` | Relative value strategy funds: leverage (gross asset-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 23.305 | Gross asset-weighted average ratio |
| `FPF-STRATEGY_RV_LEVERAGERATIO_NAVWMEAN` | Relative value strategy funds: leverage (net asset-weighted average ratio) | 2018-03-31 ~ 2026-06-30 | 8.102 | Net asset-weighted average ratio |
| `SCOOS-NET_HF_LEVERAGEUSE` | Survey: use of leverage offered to hedge funds (net percent of respondents reporting a cha | 2018-03-31 ~ 2026-09-30 | 0 | Net percent of respondents reporting a change |

## 公布時間
- PD：NY Fed 週頻公布，資料所屬日為週三（API 的 `asofdate`），公布日晚於所屬日（公布時點未在本次查證）。資料清單中最新 as-of 為 2026-10-28。
- OFR Form PF 彙總：季頻，落後約一個季度以上。本次最新 Form PF 為 2026-06-30（API metadata 的 last_update 為 2026-09-16）。SCOOS 為季頻調查，本次到 2026-09-30。

## 實測結果
| 檔案 | 列數 | 起訖 | 系列數 |
|---|---|---|---|
| pd_financing.csv | 8320 | 2018-01-03 ~ 2026-10-28 | 22 |
| repo_haircuts.csv | 307 | 2018-03-31 ~ 2026-09-30 | 9 |
| hedge_fund_leverage.csv | 953 | 2018-03-31 ~ 2026-09-30 | 28 |

最新 5 筆：

pd_financing.csv
```
      date      series_key                              description     value            unit
2026-10-28  PDSORA-FGEMTOT Total - Repurchase Agreements: Federal A   30704.0 Millions of USD
2026-10-28   PDSORA-FGMTOT Total - Repurchase Agreements: Federal A  864398.0 Millions of USD
2026-10-28     PDSORA-OTOT    Total - Repurchase Agreements: Other    53915.0 Millions of USD
2026-10-28 PDSORA-UTSETTOT Total - Repurchase Agreements: U.S. Trea 3063959.0 Millions of USD
2026-10-28  PDSORA-UTSTTOT Total - Repurchase Agreements: U.S. Trea  275664.0 Millions of USD
```

repo_haircuts.csv
```
      date                       series_key                              description  value                     unit
2026-06-30 FPF-GAVN51_OCRATEEXOTHER_PERCENT Top 51+ largest funds: over-collateraliz   22.9                  Percent
2026-06-30            FPF-OCRATEALL_PERCENT Qualifying Hedge Funds: over-collaterali   15.3                  Percent
2026-06-30        FPF-OCRATECASHSEC_PERCENT Qualifying Hedge Funds: over-collaterali   10.2                  Percent
2026-06-30            SCOOS-NET_COLLATTERMS Survey: collateral terms as most importa    0.0 Net count of respondents
2026-09-30            SCOOS-NET_COLLATTERMS Survey: collateral terms as most importa    0.0 Net count of respondents
```

hedge_fund_leverage.csv
```
      date                                series_key                              description  value                                          unit
2026-06-30 FPF-STRATEGY_MULTI_LEVERAGERATIO_NAVWMEAN Multi strategy funds: leverage (net asse  4.462              Net asset-weighted average ratio
2026-06-30    FPF-STRATEGY_RV_LEVERAGERATIO_GAVWMEAN Relative value strategy funds: leverage  23.305            Gross asset-weighted average ratio
2026-06-30    FPF-STRATEGY_RV_LEVERAGERATIO_NAVWMEAN Relative value strategy funds: leverage   8.102              Net asset-weighted average ratio
2026-06-30                  SCOOS-NET_HF_LEVERAGEUSE Survey: use of leverage offered to hedge  0.000 Net percent of respondents reporting a change
2026-09-30                  SCOOS-NET_HF_LEVERAGEUSE Survey: use of leverage offered to hedge  0.000 Net percent of respondents reporting a change
```

verify.py 完整輸出：
```
ok   欄位前段為 ['date', 'series_key', 'description', 'value', 'unit']（實際 ['date', 'series_key', 'description', 'value', 'unit']）
ok   主鍵 ['date', 'series_key'] 不重複
ok   依 ['date', 'series_key'] 升冪
ok   pd_financing.csv 起始 <= 2018-01-31（2018-01-03）
ok   pd_financing.csv 最新 >= 2026-10-14（2026-10-28）
ok   pd_financing.csv 至少 2 個系列（22）
ok   pd_financing.csv value 非空比例 > 95%
info pd_financing.csv: 8320 列、系列 22 個
                         最新          值
series_key                            
PDPOSGS-B        2026-10-28    99857.0
PDPOSGST-TOT     2026-10-28   452759.0
PDSIOSB-UTSETTOT 2026-10-28   425849.0
PDSIRRA-ABSTOT   2026-10-28     8427.0
PDSIRRA-CDTOT    2026-10-28    51509.0
PDSIRRA-ETOT     2026-07-08        0.0
PDSIRRA-FGCMTOT  2026-10-28     3043.0
PDSIRRA-FGEMTOT  2026-10-28    10829.0
PDSIRRA-FGMTOT   2026-10-28   391040.0
PDSIRRA-OTOT     2026-10-21    30421.0
PDSIRRA-UTSETTOT 2026-10-28  2775521.0
PDSIRRA-UTSTTOT  2026-10-28   225842.0
ok   欄位前段為 ['date', 'series_key', 'description', 'value', 'unit']（實際 ['date', 'series_key', 'description', 'value', 'unit']）
ok   主鍵 ['date', 'series_key'] 不重複
ok   依 ['date', 'series_key'] 升冪
ok   repo_haircuts.csv 起始 <= 2022-12-31（2018-03-31）
ok   repo_haircuts.csv 最新 >= 2026-06-30（2026-09-30）
ok   repo_haircuts.csv 至少 2 個系列（9）
ok   repo_haircuts.csv value 非空比例 > 95%
info repo_haircuts.csv: 307 列、系列 9 個
                                             最新     值
series_key                                           
FPF-GAVN10_OCRATEALL_PERCENT         2026-06-30   0.0
FPF-GAVN10_OCRATEEXOTHER_PERCENT     2026-06-30   0.0
FPF-GAVN11TO50_OCRATEALL_PERCENT     2026-06-30   7.6
FPF-GAVN11TO50_OCRATEEXOTHER_PERCENT 2026-06-30   7.1
FPF-GAVN51_OCRATEALL_PERCENT         2026-06-30  37.3
FPF-GAVN51_OCRATEEXOTHER_PERCENT     2026-06-30  22.9
FPF-OCRATEALL_PERCENT                2026-06-30  15.3
FPF-OCRATECASHSEC_PERCENT            2026-06-30  10.2
SCOOS-NET_COLLATTERMS                2026-09-30   0.0
ok   欄位前段為 ['date', 'series_key', 'description', 'value', 'unit']（實際 ['date', 'series_key', 'description', 'value', 'unit']）
ok   主鍵 ['date', 'series_key'] 不重複
ok   依 ['date', 'series_key'] 升冪
ok   hedge_fund_leverage.csv 起始 <= 2018-12-31（2018-03-31）
ok   hedge_fund_leverage.csv 最新 >= 2025-06-30（2026-09-30）
ok   hedge_fund_leverage.csv 至少 2 個系列（28）
ok   hedge_fund_leverage.csv value 非空比例 > 95%
info hedge_fund_leverage.csv: 953 列、系列 28 個
                                                    最新             值
series_key                                                          
FPF-ALLQHF_GAVN10_BORROWING_PERCENT         2026-06-30  3.210000e+01
FPF-ALLQHF_GAVN10_LEVERAGERATIO_AVERAGE     2026-06-30  1.924900e+01
FPF-ALLQHF_GAVN11TO50_LEVERAGERATIO_AVERAGE 2026-06-30  1.176000e+01
FPF-ALLQHF_GAVN51_LEVERAGERATIO_AVERAGE     2026-06-30  1.792000e+00
FPF-ALLQHF_GAV_SUM                          2026-06-30  1.386300e+13
FPF-ALLQHF_GNE_SUM                          2026-06-30  4.519300e+13
FPF-ALLQHF_NAV_SUM                          2026-06-30  5.511000e+12
FPF-ASSETCLASS_IRD_GNE_SUM                  2026-06-30  1.390200e+13
FPF-ASSETCLASS_LTREASURY_SUM                2026-06-30  2.362000e+12
FPF-ASSETCLASS_REPO_REPO_SUM                2026-06-30  3.283000e+12
FPF-ASSETCLASS_REPO_REVERSEREPO_SUM         2026-06-30  1.320000e+12
FPF-ASSETCLASS_STREASURY_SUM                2026-06-30  1.498000e+12
PASS dealer-funding
```

## 缺口與異常
- PD：各系列起始日不同（PDSORA-FGCMTOT、PDSIRRA-FGCMTOT 自 2022-01 起；PDSIRRA-ETOT 自 2018-10-24 起、至 2026-07-08 止）。多數系列列數少於 461 週（如 PDSORA-UTSETTOT 356 列、PDSIRRA-UTSETTOT 367 列、PDSOOS-UTSETTOT 173 列），表示 API 在部分週別沒有該系列的值，未補值，保持空缺（未逐一查證原因）；各系列內日期最大間隔 518 天。
- PD 清單中所有系列的 seriesbreak 均為 SBN2024；2018 年起的值依 API 回傳，未查證歷史口徑變更，也未驗證前後可比性。
- 來源 `list/timeseries.json` 中 `PDSIRRA-CDTOT`（公司債附賣回）的 description 文字為「Other Financing Activity, Securities Borrowed: Federal Agency and GSE Residential MBS」，與代碼不符，照抄來源未修改。
- F2 沒有真正的 haircut 序列（見上）。FPF 過度擔保率的取樣為合格對沖基金（Qualifying Hedge Funds），部分分組最新為 0.0（GAVN10 分組），為來源值。
- F4 最新到 2026-06-30（落後約四個多月）；SCOOS 到 2026-09-30。`unit` 為來源原值，數量級差異大（美元 vs 比率），未換算。
- FPF 部分序列在來源中可能因保密而為空值，本次所選系列自 2018-03-31 起每季皆有值。
