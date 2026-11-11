# 日頻候選系列

## OFR Financial Research API `/v1/`（repo 資料集，日頻，皆為代理、非 haircut）
選用（Final 版，避免 Preliminary 與 Final 重複）：
| mnemonic | 內容 | 性質 |
|---|---|---|
| REPO-DVP_AR_OO-F | DVP 隔夜/開放平均利率 | 代理（利率） |
| REPO-DVP_TV_TOT-F | DVP 成交量合計 | 代理（成交量） |
| REPO-DVP_OV_TOT-F | DVP 未平倉量合計 | 代理（餘額） |
| REPO-GCF_AR_OO-F | GCF 隔夜/開放平均利率 | 代理（利率；資料稀疏） |
| REPO-GCF_TV_TOT-F | GCF 成交量合計 | 代理（成交量） |
| REPO-TRIV1_AR_OO-F | 三方回購隔夜/開放平均利率（排除 Fed） | 代理（利率） |
| REPO-TRIV1_TV_TOT-F | 三方回購成交量（排除 Fed） | 代理（成交量） |

未選：Preliminary 版（與 Final 重複）、依期限拆分（1w、2w…）與含 Fed 交易的三方系列。164 個系列的名稱都沒有 haircut／margin。

## NY Fed Markets API（`/api/rates/secured/{type}/search.json`，日頻）
| series_key | 內容 | 性質 |
|---|---|---|
| NYF-SOFR-RATE / -VOL | SOFR 利率與基礎成交量 | 代理 |
| NYF-BGCR-RATE / -VOL | 廣義一般擔保利率與成交量 | 代理 |
| NYF-TGCR-RATE / -VOL | 三方一般擔保利率與成交量 | 代理 |

其他 API 類別（rp 公開市場回購操作、pd、seclending、soma 等）依類別名稱與欄位判斷沒有 haircut 序列，未逐一抓取。
