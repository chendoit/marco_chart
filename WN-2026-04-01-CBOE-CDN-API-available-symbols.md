# WN-2026-04-01 CBOE CDN API 可用指數與使用方式

## 起因

調查 CBOE CDN API (`cdn.cboe.com/api/global/delayed_quotes/charts/historical/`) 是否有辦法知道所有可用的 symbol，以擴充 `get_cboe_index.py` 的抓取範圍。

## 分析

### API 端點格式

```
https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/_{SYMBOL}.json
```

- 這是一個靜態 CDN，每個 symbol 對應一個 JSON 檔案
- **沒有** 提供列出所有可用 symbol 的 index/listing 端點
- 不需要 API key，免費、無認證即可取得
- 資料延遲約 15 分鐘（delayed quotes）

### JSON 回傳格式

```json
{
  "timestamp": "2026-04-01 14:01:57",
  "data": [
    {
      "date": "2022-05-13",
      "volume": "0.0",
      "open": "33.630000",
      "high": "33.630000",
      "low": "33.630000",
      "close": "33.630000"
    }
  ]
}
```

欄位：`date`, `open`, `high`, `low`, `close`, `volume`（多數指數 volume 為 0）。

### 如何取得完整 Symbol 列表

雖然 CDN 本身不提供列表，但可從第三方來源取得 CBOE 指數目錄：

- **DTN IQFeed CBOE 指數清單**：https://ws1.dtn.com/IQ/Guide/indices_cboe.html
  - 約 120+ 個 CBOE 指數 symbol（去掉 `.XO` 後綴即為 CDN API 的 symbol）
- **CBOE 官方指數搜尋頁**：https://www.cboe.com/us/indices/indicessearch/
  - 450+ 個指數，但需手動瀏覽，無法直接取得完整 CSV

### 已驗證可用的 Symbol（2026-04-01 實測）

以下 symbol 均已確認可成功從 CDN API 取得歷史資料：

#### 波動率指數
| Symbol | 說明 | 資料起始 |
|--------|------|---------|
| VIX | S&P 500 波動率指數 | ~2004 |
| VVIX | VIX 的波動率 | ~2007 |
| VIX1D | 1 日波動率 | ~2022 |
| VIX9D | 9 日短期波動率 | ~2011 |
| VIX3M | 3 個月波動率 | - |
| VIX6M | 6 個月波動率 | - |
| VIX1Y | 1 年波動率 | - |
| RVX | Russell 2000 波動率 | ~2004 |
| VXN | Nasdaq 100 波動率 | - |
| OVX | 原油波動率 | ~2007 |
| GVZ | 黃金波動率 | ~2008 |

#### VIX 期貨策略指數
| Symbol | 說明 |
|--------|------|
| LONGVOL | Long VIX Futures Index |
| SHORTVOL | Short VIX Futures Index |

#### 市場結構 / 風險指標
| Symbol | 說明 |
|--------|------|
| SKEW | S&P 500 偏態指數 |
| GAMMA | S&P 500 Gamma 指數 |
| SMILE | S&P 500 Smile 指數 |

#### 隱含相關性指數
| Symbol | 說明 |
|--------|------|
| COR1M | 1 個月隱含相關性 |
| COR3M | 3 個月隱含相關性 |
| COR6M | 6 個月隱含相關性 |
| COR9M | 9 個月隱含相關性 |
| COR1Y | 1 年隱含相關性 |
| COR10D | 3 個月 10 Delta 隱含相關性 |
| COR30D | 3 個月 30 Delta 隱含相關性 |
| COR90D | 3 個月 90 Delta 隱含相關性 |

#### 策略基準指數
| Symbol | 說明 |
|--------|------|
| BXM | S&P 500 BuyWrite (Covered Call) |
| PUT | S&P 500 PutWrite |
| CLL | S&P 500 95-110 Collar |
| RXM | S&P 500 Risk Reversal |
| VPD | VIX Premium Strategy |
| CNDR | S&P 500 Iron Condor |
| MGTN | Magnificent 10 指數 |

#### 大盤指數
| Symbol | 說明 |
|--------|------|
| SPX | S&P 500 |
| DJX | 1/100 Dow Jones Industrials |
| XSP | Mini S&P 500 |

#### 個股波動率
| Symbol | 說明 |
|--------|------|
| VXAPL | Apple VIX |
| VXAZN | Amazon VIX |
| VXGS | Goldman Sachs VIX |
| VXGOG | Google VIX |
| VXIBM | IBM VIX |
| VXEEM | 新興市場 ETF 波動率 |
| VXEFA | EFA ETF 波動率 |
| VXEWZ | 巴西 ETF 波動率 |
| VXTLT | 20+ 年美債 ETF 波動率 |

#### 公債殖利率指數
| Symbol | 說明 |
|--------|------|
| IRX | 13 週美國國庫券殖利率 |
| FVX | 5 年美國公債殖利率 |
| TNX | 10 年美國公債殖利率 |
| TYX | 30 年美國公債殖利率 |

### 不可用的 Symbol

- 一般個股 ticker（如 AAPL, MSFT）→ 回傳 403/404
- 不存在的自造 symbol → 回傳 403/404

## 現有程式碼

`get_cboe_index.py` 目前抓取的 symbol 清單：

```python
CBOE_INDICES = ["LONGVOL", "SHORTVOL", "VIX"]
```

如需擴充，只要在 `CBOE_INDICES` 中加入上述已驗證的 symbol 即可。

## 備註

- DTN IQFeed 清單中的 symbol 格式為 `SYMBOL.XO`，使用時需去掉 `.XO` 後綴
- 如需系統性驗證所有 symbol，可寫探測腳本逐一嘗試 HEAD request，記錄 200 回應的 symbol
- CBOE 的 delayed_quotes 頁面有聲明禁止自動化大量下載，建議合理頻率抓取
