# WN-2026-09-16-M平方chart抓取改用curl_cffi-chartAPI.md

> **一句話**:`get_m_square_chart.py`(Playwright + Google OAuth 攔截)退役,改由 `get_m_square_chart_api.py`(curl_cffi 兩段式 token 直打 M² chart data API)供料;同時把 `get_m_square_series.py` 清單裡的 sid 20508、32377 一併摘過去。覆蓋 **13 條 pkl**,重疊期逐點比對通過。

- 日期:2026-09-16
- 專案:`C:/code/2025-12-05-MacroMicro-Data/`
- 參考程式(唯讀):`C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/02_macromicro_chart_api.py`
- 上位計畫:`PLAN-2026-09-15-etl-refactor-m2-replacement.md`(本改動=在不動 etl 重構的前提下,先摘掉附錄 A 的「chart」與「假替代」兩類)

---

## 1. 背景

- `get_m_square_chart.py` 用 Playwright(有頭)+ Google OAuth 開瀏覽器攔截 `data/{chart_id}` XHR,一次失敗重開瀏覽器重新 OAuth(約 36 分鐘)。
- `get_m_square_series.py` 自 2026-08-20 起全壞(91 個 URL 都 `No target script or base64 data found`),且自己吞錯 → `logs/error_history.json` 每天 `[]`、LINE 沒響,資料悄悄停在 08-19/20。
- 偵察已完成(見 `migration/agent_results/series_*.json`):M² 自家 `/charts/data/{chart_id}` API 可用 curl_cffi 兩段式 token(先 GET 圖表頁拿 `stk` token,再帶 `Authorization: Bearer` 打 API)直接取得,免瀏覽器。

## 2. 改動清單

| 檔案 | 改動 |
|---|---|
| `get_m_square_chart_api.py` | **新增**。包 5 個 fetcher(115044 / 71245 / 56752 / 20508 / 32377)+ `TITLE_MAP` title 對照表 + `_save_series()` 防呆(新點數 < 舊點數 50% 拒寫)+ 失敗彙整後 `raise`(不再吞錯) |
| `get_all_series_data.py` | import 與 tasks 表把 `fetch_m_square_charts` 換成 `fetch_m_square_chart_api` |
| `get_m_square_series.py` | `url_list` 移除 sid 20508、32377 兩列(加註解標記),其餘不動(仍壞,等 WP-R2E) |
| `get_m_square_chart.py` | 檔頭加「2026-09-16 退役」註解說明,程式本體未動;排程已不引用 |

排程 `\get_all_series_data`(每天 08:00 / 18:00)跑的就是 `get_all_series_data.py`,**排程設定不需改**。

## 3. 覆蓋範圍(13 條)

| chart | sid | title | 頻率 | 儀表板使用 |
|---|---|---|---|---|
| 115044 OIS | 1150440~1150446 | 美国-隔夜指数掉期[OIS]1個月…30年 | 日 | 每日天啟、FED 利率預測、McElligott、美元指數 |
| 71245 FedWatch | 712450 / 712451 | 預估利率上/下限 | FOMC 日 | (routes 目前未引用) |
| 56752 LEI/CEI | 567520 / 567521 | CB 領先/同時指標 (SA,yoy) | 月 | 愛克榭 ×2 圖 |
| 46503 s[1] | 20508 | global-pmi-leading-yoy-diffusion | 月 | (未引用) |
| 102471 s[0] | 32377 | jpy-vix | 日 | 日圓.py |

## 4. 驗證結果(2026-09-16 23:52 實跑,venv Python 3.12 + curl_cffi 0.16.3)

比對方式:執行前備份舊 pkl,執行後逐 datetime 比對重疊點。

| sid | old_n | new_n | 重疊差異 | 備註 |
|---|---|---|---|---|
| 1150440~46 | 5074/5084/5096/5097/5082/5055/4608 | 同 | **0 差異** | 完全一致 |
| 712450/51 | 48 | 48 | 3 點 | 未來 FOMC 日(2027-07-29、09-16、10-28)被 M² 重估:上限 4.75→4.50、下限 4.50→4.25;以新值為準 |
| 567520/21 | 658 | 658 | **0 差異** | 本版刻意不捨入,對齊舊 pkl 全精度(02 檔原版是 round(…,4)) |
| 20508 | 55 | **320** | 0 差異 | 舊 Playwright series 抓取只存到 2020(55 點);API 有全歷史,新增 2000-01~2026-08 |
| 32377 | 201 | **7959** | 1 點 | 舊只存 2006 起(201 點);最後一點 2026-08-18 由 7.2175 修訂為 6.945(M² 官方 revision),新到 09-15 |

title 13 條全部與舊 pkl 相同(`TITLE_MAP` 對照表由舊 pkl 直接抄錄,712450/51 與 567520/21 的舊 title 本身就是 chart_title+series_title 的字串拼接,原樣保留)。

## 5. 已知影響 / 注意

1. **`series_32377` 歷史從 201 點 → 7959 點、`series_20508` 55 → 320 點**:下次 `calc_pctrank` 會對全歷史重算,兩條的 pctrank 值會整條變(變長歷史 → 百分位更穩,但與舊值不連續)。目前 routes 對 32377 只畫原值不畫 pctrank,20508 未上圖,影響面小;但 `calc_pctrank` 之後的輸出值得目檢一次。
2. **56752/71245/115044 未來 FOMC 與月頻值可能隨 M² 重估而變**(如本次 71245 的 3 點),這是上游行為,兩種抓法皆然。
3. **token 依賴 M² 頁面結構**(`stk` regex + `data-stk`):M² 改版或 Cloudflare 收緊時會 fail;本版 fail 會 raise → 進 `error_history` → 連續 3 天發 LINE,不會再靜默壞掉。
4. `chart_115044/56752/71245.pkl`(原始 JSON)不再更新;全專案無下游消費者(`load_chart_data()` 無人呼叫),僅留檔備查。
5. **沒被這次覆蓋的 ~90 條 M² series 仍卡在 2026-08-19**(含儀表板在用的 1645、484、8298 等),`get_m_square_series.py` 依舊全壞 — 這次刻意不動,屬 PLAN 的 WP-R2E / etl 重構範圍。

## 6. 後續可做(未做)

- 觀察明日(09-17 08:00)排程跑一輪,確認 log 出現 `MacroMicro charts (curl_cffi API, 13 series)` Completed 且 `error_history.json` 正常。
- `get_m_square_chart.py` 未來若確認不再需要 fallback,可整檔刪除 + 移除 `google_session` 依賴。
- 剩餘 M² series 修復(WP-R2E)或 etl 重構時,`fetch_m_square_chart_api()` 可原樣搬進 `etl/jobs/`。
