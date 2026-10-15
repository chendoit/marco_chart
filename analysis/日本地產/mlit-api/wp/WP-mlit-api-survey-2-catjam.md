---
id: mlit-api-survey-2-catjam
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\_ws2c'
mode: readonly
agent: opencode:oc-free-cat-jam
priority: 2
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py'
handoff:
  why: 同題對照實驗——以 opencode:oc-free-cat-jam 重跑 mlit-api-survey-2（該題已由 agy:gemini-3.8-flash-high 完成並收件），比較免費 cat jam 與 agy gemini flash 3.8 的產出差距
  ref: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\research\mlit-api-survey-2\report.md'
  after_accept: 逐題比對兩份 report 與 samples 的數字、網址與結論差異，寫成比較 WN
outputs: [.agent-run/out/report.md, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：reinfolib API 第二輪——資料落後期、地價取得、指數對照與屋齡控制

## 1. 背景
第一輪（`mlit-api-survey`）已確認：reinfolib 共 35 支 API，核心是 XIT001（成交價明細，2005Q3 起；房仲簽約價 2021Q1 起），認證用 header `Ocp-Apim-Subscription-Key`，基底 `https://www.reinfolib.mlit.go.jp/ex-api/external/<代號>`；無資料時屬性 API 回 **404**、瓦片 API 回 200＋空 features；瓦片 zoom 有限制（XPT002 僅 13–15）。第一輪成果（唯讀，可讀）：
- 報告：`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\research\mlit-api-survey\report.md`
- 可重跑腳本：`...\research\mlit-api-survey\probe_mlit.py`（含 XIT001 抓取與季度彙總，可參考改寫）
- 總結 WN（含我們的保留意見）：`C:\code\2025-12-05-MacroMicro-Data\WN-2026-10-15-MLIT不動產資訊庫API能力調查.md`

第一輪的季度彙總顯示：東京 23 區中古公寓每㎡中位數 2021Q1 86.7 萬圓 → 2025Q4 111.4 萬圓（+28.6%）；但 **2026Q1 只有 11,993 筆（2025Q4 為 16,401）、純土地僅 358 筆**，疑似申報落後。本輪要把這些疑問弄清楚。

## 2. 金鑰
在 `C:\code\2025-12-05-MacroMicro-Data\.env` 的 `MLIT_TOKEN`。程式內逐行解析讀取（去引號空白），**不得印出或寫進 report／samples／probe／日誌**；驗收會掃描輸出。

## 3. 要回答的問題（對應 report 的 `## Q1`…`## Q5`）

**Q1 申報涵蓋率與落後期（XIT001）**
- 官方更新時程：reinfolib 哪一頁說明各季成交資料的公開時間（例如「お知らせ」、更新履歴、API 手冊註記）？每季何時公開、是否之後回補修訂？附網址與日期。
- 實測：取東京都（area=13）最近 12 季（約 2023Q2–2026Q1）的總筆數、中古マンション等筆數，輸出 `samples/xit001_quarter_counts.csv`（欄位：`quarter,total,mansion,land_building,land_only,snapshot_date`；`snapshot_date` 填今天，以後重跑可比對回補量）。
- 找出最近一季相對前一季的筆數比，並**判斷哪幾季應視為暫定**；若官方有說明審查／公開延遲就引用。
- 問題：XIT001 的資料是問卷抽樣還是全數？官方說明涵蓋率（網頁或統計說明）怎麼寫？

**Q2 地價公示／地價調查的取得（XPT002、XCT001 與替代來源）**
- XCT001 的 `division` 代碼各是什麼（住宅地、商業地、工業地等）？各查東京都 2024 年，記錄筆數。
- XPT002 要覆蓋東京都或全國需要多少瓦片（z=13 與 z=14 各估），給出請求量估算與建議作法。
- 有無**整檔下載**的免費替代：國土數值情報「地価公示」（L01）、「都道府県地価調査」（L02）、國交省土地総合情報システム地價公示頁等；查下載網址、格式、涵蓋年份、座標系與欄位，實測下載一個小檔（不要全站抓）。
- 結論：要做「全國主要都市公示地價年增率」最佳作法是哪個？

**Q3 與官方不動產價格指數對照**
- 國交省「不動産価格指数（住宅）」是用同一批取引價格資料編製的月／季指數（2008 起，含マンション、戸建、住宅地，分全國／三大都市圈／南関東／東京都等）。找免費可程式化取得的來源（國交省頁面或 e-Stat 檔案下載，不要申請 appId），實測下載，輸出該指數的東京都（或南関東）マンション序列。
- 與第一輪的東京 23 區中古公寓季度中位數單價做對照，輸出 `samples/index_comparison.csv`（欄位：`quarter,reinfolib_median_sqm_yen,official_index,reinfolib_yoy,official_index_yoy`，至少 12 季），並寫出相關係數、走勢是否一致、差異來源。
- 若有 REIC（日本不動産研究所）等免費的住宅價格指數頁，列出但不必抓。

**Q4 屋齡控制**
- 用 XIT001 抓東京都 2021Q1–2026Q1 中古マンション等（每年 1 次請求即可，`year=<Y>&area=13`；2026 只取到有資料的季），以 `BuildingYear` 算出屋齡，分 ≤10、11–20、21–30、>30 年四層，計算每層的季度中位數每㎡單價與筆數。輸出 `samples/age_controlled_tokyo_condo.csv`（欄位：`quarter,age_bucket,transactions,median_sqm_yen`）。
- 另算「固定權重」指數：以 2021 年全年各屋齡層的成交占比為權重，加權各層中位單價，得到屋齡結構固定的季度單價；與未控制的整體中位數比較，**第一輪的 +28.6% 有多少是結構變化造成**？（務必誠實揭露，數字有出處就是這份 CSV。）
- 建築年為和曆（昭和／平成／令和）字串，需轉西曆；缺值或無法解析要列出比例。

**Q5 全國抓取請求量與限流**
- 估算「全國 47 都道府縣 × 2005Q3 至今」若以 XIT001 按「年×都道府縣」抓取，需要多少請求、預估總耗時（間隔 1.5 秒）與資料量；若改按季或按市區町村有何差別；有無單次回傳過大導致逾時的案例（記錄實測的最大一次回應大小與耗時）。輸出 `samples/request_budget.csv`（欄位：`scenario,requests,interval_s,est_hours,est_rows,note`，≥4 種情境）。
- 限流實測：對 XIT002（輕量）連續請求 20 次、間隔 1 秒，記錄狀態碼與延遲；**不要用更快的速度壓測**。官方文件或 Q&A 對限流與連續失效的說法也列出網址。

## 4. 產出（寫到 `.agent-run/out/`，UTF-8；工作區其他位置不得寫檔，執行 Python 加 `-B`）
1. `report.md`：繁體中文，≥5000 bytes，二級標題：`## 結論`（5–8 點，先講答案）、`## Q1`…`## Q5`（各回答上述問題，附請求網址（不含金鑰）、狀態、筆數、資料日期與官方頁面網址）、`## 踩坑`、`## 建議下一步`（寫正式抓取腳本前還缺什麼，給出具體順序）。
2. `samples/`：`xit001_quarter_counts.csv`、`index_comparison.csv`、`age_controlled_tokyo_condo.csv`、`request_budget.csv`（欄位如上，各 ≥4 資料列）；另可放 Q2、Q3 下載的小檔樣本。
3. `probe_mlit2.py`：可重跑，輸出到 `Path(__file__).parent / "samples"`；每個請求 `timeout=60`；單一來源失敗只印錯誤、不中斷其他；請求間隔 ≥1 秒。

## 5. 規範
- Python 用 `C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe`（有 requests、pandas、openpyxl、xlrd、curl_cffi、bs4、lxml、pypdf、shapely 若無就不用）。**不要 pip install**，設 `PYTHONUTF8=1`。
- 可上網讀文件、可呼叫 reinfolib 與官方下載頁。**禁止**（理由：避免占用公共服務與觸發金鑰封鎖）：總請求超過 400 次、以快於 1 秒的間隔連續請求、批量爬取、登入／註冊其他網站、申請 e-Stat appId、繞過驗證碼、修改工作區外檔案、git 推送。
- 數字要有出處（網址＋日期）；推測要標明。若某題做不到，直接寫明原因與已試過的方法，不要編造。
- 今天是 2026-10-15。

## 6. 驗收
`verify_wp.py` 通過：report.md ≥5000 bytes 且有必要標題、四份 samples CSV 各 ≥4 資料列、有 probe_*.py、輸出無金鑰。
