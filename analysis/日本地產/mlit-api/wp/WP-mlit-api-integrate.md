---
id: mlit-api-integrate
workdir: 'C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\_ws3'
mode: readonly
agent: agy:gemini-3.8-flash-high
fallback: [agy:gemini-3.8-flash-medium]
priority: 2
timeout_min: 50
max_attempts: 3
verify: 'C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe verify_wp.py'
handoff:
  why: 要把 MLIT reinfolib 資料對進三份日本地產 WN 的缺口，需驗證四個可用性假設並產出各 WN 的補充段落
  ref: 'C:\code\2025-12-05-MacroMicro-Data\WN-2026-10-15-MLIT-API第二輪-落後期地價指數對照與屋齡控制.md'
  after_accept: 我（Claude）審閱 wn_patches 後把補充段落插入三份 WN
outputs: [.agent-run/out/report.md, .agent-run/out/wn_patches/, .agent-run/out/samples/, .agent-run/out/probe_*.py]
---

# 指派文件：把 MLIT API 資料整理進日本地產三份 WN（驗證＋產出補充段落）

## 1. 背景
我們已調研 MLIT 不動產資訊庫 API（reinfolib），兩輪成果（唯讀，請先讀）：
- 第一輪 WN：`C:\code\2025-12-05-MacroMicro-Data\WN-2026-10-15-MLIT不動產資訊庫API能力調查.md`
- 第二輪 WN：`C:\code\2025-12-05-MacroMicro-Data\WN-2026-10-15-MLIT-API第二輪-落後期地價指數對照與屋齡控制.md`
- 原始成果與腳本：`C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\mlit-api\research\mlit-api-survey\`、`...\mlit-api-survey-2\`（`probe_mlit.py`、`probe_mlit2.py` 可改寫重用）

現在要把這些資料「對進」既有的三份日本地產 WN。三份 WN（唯讀，路徑都在 `C:\code\2025-12-05-MacroMicro-Data\analysis\日本地產\`）：
- `WN-2026-10-08-日本地產數據收集規劃.md`（下稱 **規劃 WN**）
- `WN-2026-10-08-舊文件地產投資主題與數據指標.md`（下稱 **主題 WN**）
- `WN-2026-10-08-日本地產研究總結與追蹤.md`（下稱 **總結 WN**）

這三份已有的資料樣本在 `...\日本地產\data\*.csv` 與 `...\日本地產\research\<id>\samples\`（例如 `jp-used-vs-new\samples\reins_used_condo_monthly.csv`，**REINS 中古月度其實從 2015-07 起有**，不是只有 13 個月；`jp-prices-rates\samples\` 有價格指數、手抄的不動産経済研究所與東京カンテイ樣本）。

## 2. 金鑰
`C:\code\2025-12-05-MacroMicro-Data\.env` 的 `MLIT_TOKEN`，程式內讀取，**不得印出或寫進任何產出**（驗收會掃描）。

## 3. 要驗證的四件事（report.md 的 `## V1`…`## V4`）

**V1 建売代理序列**：規劃 WN 與總結 WN 的「首都圏建売平均價」是手抄的。用 XIT001 查東京(13)、神奈川(14)、埼玉(11)、千葉(12) 2021–2026 的「宅地（土地と建物）」類成交，以 `BuildingYear` 與成交年判斷「屋齡 ≤1 年」當新建建売代理（先看 `Type`、`PriceCategory` 欄位實際值，必要時調整篩選並說明），算各縣與首都圏合計的季度成交筆數與總價中位數，輸出 `samples/shutoken_kenuri_proxy_quarterly.csv`（欄位：`quarter,prefecture,transactions,median_total_price_10k_yen`；首都圏合計用 `prefecture=ALL4`）。與兩份 WN 手抄的建賣價（總結 WN 提到建売 4,825 萬、規劃 WN 約 4,500 萬）對照，說明是否同一口徑、差多少、為什麼；此代理是否可靠，直接下結論。

**V2 與 REINS 中古月度的重疊對照**：讀 `...\日本地產\research\jp-used-vs-new\samples\reins_used_condo_monthly.csv`（月，2015-07 起，含成約件數與 ㎡單價），用 XIT001 首都圏（東京、神奈川、埼玉、千葉）中古マンション等，算 2021–2025 同期季度成交筆數與每㎡中位數，輸出 `samples/reins_vs_xit001_overlap.csv`（欄位：`quarter,reins_contracts,reins_sqm_price_10k,xit001_transactions,xit001_median_sqm_10k,ratio_contracts`；REINS 月資料彙成季：筆數加總、單價取季內中位或筆數加權，註明作法）。報告相關係數（水準與 YoY）、XIT001 筆數占 REINS 的比例是否穩定、價格水準差多少。結論：XIT001 能否當 REINS 長歷史的替代，或只能當趨勢補充？

**V3 2025Q1 筆數跳升**：第二輪發現東京都 XIT001 總筆數 2024Q4 14,443 → 2025Q1 17,447（+21%，主要在透天），原因不明。查這個跳升：用同一份資料依 `Type`、`PriceCategory`（取引価格 vs 成約価格）、市區町村、用途分組比較 2024Q4 與 2025Q1，輸出 `samples/xit001_2025q1_jump_breakdown.csv`（欄位：`dimension,value,q2024q4,q2025q1,diff,pct_change`）；也看全國或另一都府縣（例如大阪 27）有沒有同樣的階梯。給出最可能的解釋（例如成約価格新增來源、API 母體變動、申報制度調整），並到官方公告頁找依據（附網址），找不到就明說「未找到官方說明」並描述資料特徵。

**V4 L01 都市別公示地價年增率**：實測下載國土數值情報 L01（地價公示）東京(13)、大阪(27)、愛知(23)、福岡(40)、北海道(01) 最近 10 年（約 2016–2025，能到哪年算哪年）的 ZIP，解析 GeoJSON／DBF，算各縣住宅地與商業地的標準地年變動率中位數與平均，輸出 `samples/l01_city_yoy_annual.csv`（欄位：`year,prefecture,land_use,n_points,yoy_median_pct,yoy_mean_pct`）。先確認 L01 版本、欄位代號、座標與年度命名規則（不同年份檔名可能變）；若最新年份尚無，寫明最新可得年。原始 ZIP 不要保存，只存解析結果與一個小樣本。

## 4. 補充段落產出（核心交付）
在 `.agent-run/out/wn_patches/` 寫三個 Markdown：`plan.md`（給規劃 WN）、`topics.md`（給主題 WN）、`summary.md`（給總結 WN）。每個檔案要像可直接貼進 WN 的「補充段落」，格式：

```
## 插入位置：<該 WN 的章節標題與（前／後）；用原文標題>
### MLIT API 補充（2026-10-15）
<繁體中文，條列或表格，簡潔；每個數字標「已驗」（你在本輪實測得到）或「待驗」（引自前兩輪 WN 或推論），附出處網址或 CSV 檔名>
```

可有多個「插入位置」段，每段對應 WN 裡真實存在的章節（請先把三份 WN 讀完，用原文標題）。內容要點（依 WN 性質取用）：
- 規劃 WN：資料來源表裡「價／量」那幾列補上 XIT001 / L01 作為來源，並更新「REINS 只有 13 個月」「建売平均價手抄」等過時描述；補一小段「MLIT 資料的使用規則」（暫定值、出處與免責聲明、請求預算）。
- 主題 WN：T2、T3 的「要驗證」與缺口表（P1 項）加上 MLIT 可補的項目與口徑差異；標明哪些缺口 MLIT **補不上**（租金、空置率、cap rate、在庫月數）。
- 總結 WN：§1 總體背景表、§4.2 指標表可新增的列（如東京中古公寓固定屋齡權重序列、L01 地價年增率、XIT001 季度成交筆數），§5 沒回答的問題中哪些現在有解、哪些仍沒解；§6 數據可信度加一條 MLIT 資料注意事項（最新 1–2 季暫定、問卷回收約三成〔待驗〕、屋齡結構效果）。**不要改動原有結論與投資判斷。**
- 另在 `plan.md` 末尾附「下一步抓取腳本清單」（序列名、API、頻率、請求數、輸出檔名），三大都市圈起步。

## 5. 產出清單（`.agent-run/out/`）
1. `report.md`：繁中，≥4000 bytes；標題 `## 結論`、`## V1`、`## V2`、`## V3`、`## V4`、`## 踩坑`。
2. `wn_patches/plan.md`、`topics.md`、`summary.md`（各 ≥1500 bytes，含「插入位置」且有「已驗」或「待驗」標註）。
3. `samples/`：`shutoken_kenuri_proxy_quarterly.csv`、`reins_vs_xit001_overlap.csv`、`xit001_2025q1_jump_breakdown.csv`、`l01_city_yoy_annual.csv`（各 ≥4 資料列）。
4. `probe_integrate.py`：可重跑，輸出到 `Path(__file__).parent / "samples"`；每請求 `timeout=60`；單一來源失敗只印錯誤；請求間隔 ≥1 秒。

## 6. 規範
- Python：`C:\code\2025-12-05-MacroMicro-Data\venv\Scripts\python.exe`（有 requests、pandas、openpyxl、geopandas／shapely 若無則改用標準 json 解析 GeoJSON）。**不要 pip install**，設 `PYTHONUTF8=1`，執行加 `-B`，工作區其他位置不得寫檔。
- 總請求預算 ≤150 次（XIT001 約 4 縣×6 年＋對照；L01 約 50 個 ZIP 以內）、間隔 ≥1 秒；理由：避免占用公共服務與金鑰被限流。禁止：批量爬取其他來源、登入註冊、繞驗證碼、改工作區外檔案、git 推送。
- 不要編造。做不到的項目明寫原因與已試方法；有推論的標「待驗」。
- 今天 2026-10-15。

## 7. 驗收
`verify_wp.py` 通過：report.md 與三份 wn_patches 齊全、四份 samples CSV 各 ≥4 列、有 probe_*.py、輸出無金鑰。
