---
id: mlit-api-survey
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\_ws'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium]
priority: 2
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py'
handoff:
  why: 想知道國交省 reinfolib API 能提供哪些資料，需上網讀文件並實測多支端點，耗時且唯讀
  ref: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\wp\WP-mlit-api-survey.md'
  after_accept: 寫 WN 彙整 API 能力，評估可做的日本地產指標，必要時再派第二輪追問
outputs: [.agent-run/out/report.md, .agent-run/out/endpoints.csv, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：日本國交省「不動產資訊庫 API」（reinfolib）能做什麼

## 1. 背景
我們（MacroMicro 資料專案）拿到日本國土交通省「不動産情報ライブラリ」API 的金鑰，想知道它**實際能提供哪些資料、能不能拿來做日本地產的總經／市場序列**。這是「調研＋實測」：上網讀官方文件、實際打每個端點一次、把結果整理成報告。

- 官方 API 手冊：https://www.reinfolib.mlit.go.jp/help/apiManual/
- 利用規約：https://www.reinfolib.mlit.go.jp/help/termsOfUse/（請讀，摘要可否商用、是否要標示出處、請求頻率限制）
- API 基底網址通常為 `https://www.reinfolib.mlit.go.jp/ex-api/external/<API代號>`（例：XIT001 取引価格・成約価格情報、XIT002 都道府縣內市區町村一覽、XPT001 不動產價格點、XKT 系列地圖圖層 tile 等）。**以官方手冊為準**，請把手冊列出的每一個 API 都列入 endpoints.csv。
- 認證：金鑰放在 request header（通常是 `Ocp-Apim-Subscription-Key`），請以手冊為準並實測確認。

## 2. 金鑰（重要）
- 金鑰在 `C:\code\2025-12-05-MacroMicro-Data\.env` 的 `MLIT_TOKEN`。程式內用讀檔方式取得（逐行解析 `MLIT_TOKEN=...`，去掉引號與空白），**不要把金鑰值印出、寫進 report / csv / samples / probe 腳本 / 日誌**。驗收會掃描 `.agent-run/out/` 是否含金鑰字串，含就失敗。
- 官方提醒：不要把金鑰放進對 AI 的詢問內容。你只在本機程式裡讀取使用即可。

## 3. 要回答的問題
1. 官方手冊共有幾支 API？各自的：代號、日文名、中文名、請求參數（必填／選填）、回傳格式（JSON／GeoJSON／PBF tile）、回傳欄位、空間／時間粒度、資料起始年、更新頻率。
2. 重點 API 實測（至少 6 支回 HTTP 200）：特別是「不動產取引價格（成交價）」、「地價公示／地價調查」、都道府縣／市區町村代碼、人口、鄰近設施、災害風險等圖層。每支記錄請求網址（不含金鑰）、回應狀態、筆數、欄位、樣本。
3. 成交價資料（取引価格情報）能回溯到哪一年？能否依都道府縣／市區町村／用途（住宅地、商業地、中古マンション等）聚合成**季度中位數單價、成交件數**序列？請實際抓東京都（13）或全國的近 5 年資料，算出一份季度彙總 CSV 當示範。
4. 地價公示（公示地価／基準地価）能抓到嗎？欄位、年份範圍？能否做成年度序列？
5. 配額與限制：請求頻率、單次回傳上限、是否需分頁、tile 的 zoom 範圍、有無每日上限、錯誤碼意義。
6. 利用規約重點：可否二次加工與商用、出處標示格式、禁止事項。
7. 與我們已知的免費來源（e-Stat、日本不動産研究所 REIC、國交省建築着工統計）相比，這個 API 的**獨特價值與不足**。
8. 「對 MacroMicro 的用途」：列出 5–10 個可以做成圖表／指標的點子（序列名、來源 API、頻率、計算方式、預估難度）。

## 4. 產出（寫到工作目錄 `.agent-run/out/`，全部 UTF-8，不要在其他位置寫檔）
1. `report.md`：繁體中文，≥5000 bytes，必須有這些二級標題：`## 結論`（5–8 點）、`## API 一覽`（表格，內容同 endpoints.csv）、`## 實測`（每支實測 API：請求網址（不含金鑰）、狀態、筆數、欄位、起訖年月）、`## 踩坑`（認證、編碼、tile 格式、單位、限流）、`## 利用規約重點`、`## 對 MacroMicro 的用途`。
2. `endpoints.csv`：欄位依序 `endpoint,name_ja,name_zh,params,returns,granularity,history_start,tested,http_status,notes`；`tested` 為 yes/no，未實測 http_status 留空。
3. `samples/`：實測回應的樣本（JSON／CSV，每檔 >200 bytes，≥6 檔），含一份 `trade_quarterly_summary.csv`（季度彙總示範，第一欄 `quarter`）。大型回應只存前 200 筆。
4. `probe_mlit.py`：可重跑的抓取腳本，輸出到 `Path(__file__).parent / "samples"`；每個請求 `timeout=60`；單一端點失敗只印錯誤、不中斷其他；請求間隔 ≥1 秒。

## 5. 規範
- Python 一律用 `C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe`（已有 requests、pandas、openpyxl、curl_cffi、bs4、lxml、pypdf）。**不要 pip install**。執行時設 `PYTHONUTF8=1`。
- 可上網讀官方文件、可呼叫該 API。**禁止**：批量爬取（總請求數預算 ≤300 次，避免占用公共服務與觸發封鎖）、登入或註冊其他網站、繞過驗證碼、修改工作目錄以外的檔案、推送 git。
- 數字要有出處（網址＋日期）；推測要標明是推測。
- 今天是 2026-10-15。

## 6. 驗收
`verify_wp.py` 通過：report.md ≥5000 bytes 且有必要標題、endpoints.csv 欄位齊全且 ≥6 列 tested=yes 且 http_status=200、samples ≥6 檔、有 probe_*.py、輸出中不含金鑰。
