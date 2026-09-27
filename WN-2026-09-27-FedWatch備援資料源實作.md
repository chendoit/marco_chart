# WN: FedWatch 備援資料源實作 — `cme-fedwatch`（2026-09-27）

> 對應 `WN-2026-09-23-M2失敗19條-現況與提案.md` 的「FedWatch 追加調查」段落（選項 d）。
> sid 484/1645（升息/降息機率）目前**已經**由 M² chart 77 供應（09-27 完成，見該文件），
> 這條是文件裡說的「仍然依賴 M²，Yahoo + `cme-fedwatch` 可以當 M² 掛掉時的備援」——
> 現在開始每天累積，這樣哪天 chart 77 的兩段式 token 抓取掛了，備援序列已經有一段歷史可以接手，
> 不用從零開始等 CME 免費 feed 的 5 天回補上限。

## 一句話結論

- 專案 venv 裝了 `cme-fedwatch==0.2.1`（≥ 0.2.0，避開 0.1.x 的 75bp 偏移 bug）。
- 新增 `get_cme_fedwatch.py`，每天打 CME 官方結算 API（免費、不需瀏覽器）算下次 FOMC 的 hike/cut 機率，
  寫進 `data/fedwatch_cme_hike.pkl` / `fedwatch_cme_cut.pkl`。
- **完全獨立於 M²、不動 `series_484/1645.pkl`、不接儀表板**——單純累積，供未來比對或接手用。
- 已排進 `get_all_series_data.py`，每日跟其他任務一起跑；跑過一次驗證：09-25 結算 hike=64.2% / cut=0.0%，
  跟 WN 文件裡的驗證表（CME 官方結算 64.2/35.8）一致。

## 為什麼還要備援（chart 77 不是已經解決了嗎）

chart 77 是 M² 自家 API，抓法跟 484/1645 的其他資料一樣依賴 M² 的 Cloudflare 兩段式 token
（`get_m_square_chart_api.py` 裡的 `_fetch_chart_series`）。這條 token 機制過去已經因為 M² 改版掛過一次
（就是 08-20 起 19 條全部抓不到的起因）。`cme-fedwatch` 打的是 CME 自己的公開結算 API + FRED，
跟 M² 完全無關，兩者同時掛的機率很低。**現在就開始每天存一筆**，是因為 CME 免費 feed
本身只留約 5 個營業日（見下方），太晚才想到要備援會補不回中間的空窗——這正是 08-19 那次踩到的坑。

## 資料源細節

| | 內容 |
|---|---|
| 套件 | PyPI `cme-fedwatch` 0.2.1（= GitHub `tjdwls101010/CME-FedWatch`），MIT license，唯一依賴 `curl_cffi` |
| 抓法 | `get_probabilities("next")`：① CME 30-Day Fed Funds Futures(ZQ) 結算價 `cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/305/FUT`（公開 JSON，免 key）② FRED `EFFR`/`DFEDTARL`/`DFEDTARU`（目前利率）③ 套件內建 FOMC 會期表（來源 federalreserve.gov，寫死在套件裡） |
| 計算引擎 | 0.2.x：用「沒有會議的月份」bootstrap 出每場會議前後的隱含利率，25bp 步進機率再做卷積；修掉 0.1.x「連續兩個月有 FOMC 時 label 偏移 75bp」的 bug |
| 歷史深度限制 | **CME 免費 feed 只留約 5 個營業日**，`get_settlements()` 對太舊的日期直接 raise，補不了歷史——所以只能「從今天起累積」 |
| 版本注意 | 專案另一個 repo `2026-09-11-fincept-terminal` 的 venv 裝的是舊版 0.1.3（有 bug），這個專案裝的是獨立的 0.2.1，兩邊互不影響 |

## hike/cut 定義（對齊 chart 77）

套件 `get_probabilities("next")` 回傳的是「下次會議各目標區間的機率分布」（例如
`{"3.75%-4.00%": 35.8, "4.00%-4.25%": 64.2}`），不是直接的 hike/cut 兩個數字。
`get_cme_fedwatch.py` 依 `get_m_square_chart_api.py` 對 chart 77 的口徑換算：

- **hike** = 目標區間下緣 > 目前下緣 的機率加總
- **cut** = 目標區間下緣 < 目前下緣 的機率加總
- 下緣 = 目前下緣（維持不變）算 hold，不計入兩者

09-25 驗證：目前區間 3.75%-4.00%，分布只有 `{3.75%-4.00%: 35.8, 4.00%-4.25%: 64.2}`，
換算後 hike=64.2%、cut=0.0%（沒有降息情境被定價），跟 WN-2026-09-23 文件的驗證表一致。

## 實作

**新增檔案**：`get_cme_fedwatch.py`

- `fetch_cme_fedwatch_daily()`：呼叫 `get_probabilities("next")`，換算 hike/cut，用套件回傳的**實際結算日**
  （`result["trade_date"]`，不是 `today()`）當時間戳，避免長週末連續好幾天重複記錄同一個結算日；
  同一天已存在就跳過（幂等，排程重跑安全）。
- 寫入格式沿用專案慣例：`{"title": ..., "data": [[datetime(08:00), float], ...]}`，
  存檔前套 50% 防呆（新點數掉到舊點數一半以下就拒寫，防止 API 異常污染歷史）。
- 檔名刻意不用 `series_` 前綴、不含 484/1645：`flask_highcharts/.../highcharts_utils.py` 的
  `load_series_data()` 是用正則 `(?:^|_){sid}\.pkl$` 抓檔案，`fedwatch_cme_hike/cut.pkl` 確認不會被
  誤配對到任何 sid，不會意外混進儀表板。
- 模組頂層檢查 `cme_fedwatch.__version__ < 0.2.0` 直接 raise，避免未來環境重建時不小心裝回舊版。

**排程**：`get_all_series_data.py` 加一行

```python
from get_cme_fedwatch import fetch_cme_fedwatch_main
...
("CME FedWatch 官方結算 hike/cut (chart 77 備援, ex-M², 不接儀表板)", fetch_cme_fedwatch_main),
```

失敗只會記進當天的 `failed`/`failed_reasons`（跟其他任務一樣，不會讓整個 orchestrator 掛掉）。

**已測試**：`venv/Scripts/python.exe get_cme_fedwatch.py` 跑兩次，第一次寫入 n=1（09-25），
第二次正確判斷「已記錄過」跳過，未重複寫入。

## 之後要接手時怎麼做

如果哪天 chart 77 抓取開始失敗，`fedwatch_cme_hike/cut.pkl` 已經有從 09-27 起的每日資料可以接。
把 `get_m_square_series.py`／`get_m_square_chart_api.py` 的 484/1645 產出改指到這兩個檔案即可，
中間不會有空窗（前提是備援排程有持續在跑，沒斷過）。文件裡也留了 `batches/fedwatch_backfill/` 的
Yahoo ZQ 月合約回填腳本（`zq_backfill.py`），真的兩邊都斷、又需要回補更早歷史時可以再拿出來用，
但那批資料受合約下市限制，越晚做越補不回去。
