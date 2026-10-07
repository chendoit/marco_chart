# 指派文件：鋁區域溢價、政策時間線、部位與能源成本的數據調研＋實測

## 1. 背景
有一種觀點認為：英美 2024 年制裁禁止新俄鋁在 LME 交割、歐洲減產、美國 232 關稅，會讓歐洲完稅溢價與美國中西部溢價（US Midwest Premium）突破歷史區間；冶煉廠的利潤又取決於電價。這份 WP 盤點「溢價、政策、部位、能源」的數據。

## 2. 要找的序列（每項在 sources.csv 有一列；能實測的都實測）
**區域溢價**
1. 美國中西部溢價：CME 期貨 Aluminum MW US Transaction Premium Platts（代號 AUP / MWP）結算價。試 CME 公開結算頁、CME FTP（`ftp.cmegroup.com` 或 `https://www.cmegroup.com/ftp/`）、Yahoo 代號、新聞。Platts 現貨報價本身付費。
2. 歐洲鹿特丹完稅溢價（Aluminium European Duty-Paid premium，CME 代號 EDP）與未完稅溢價。
3. 日本 MJP 季度溢價（Main Japanese Ports）：找新聞歷史（Reuters、Mining.com、Alcircle），整理成季資料樣本。
4. CME 鋁期貨與溢價期貨的成交量、未平倉量（若可得）。

**政策時間線**（做成 `samples/policy_timeline.csv`：`date,region,event,detail,source_url`，至少 15 列，2018 年起）
5. 美國 232 關稅：2018 年 10%、2025 年 2 月恢復 25%、2025 年 6 月提高到 50%，以及豁免變化（加拿大等）——逐條查證日期。
6. 俄鋁制裁：2018 Rusal 制裁與解除、2024-04-12 英美禁止新俄鋁在 LME／CME 交割、2025 年起的後續（歐盟第 16 輪制裁對俄鋁進口的分階段禁令）。
7. 歐盟 CBAM（2026 年起正式收費）、中國 2024-12 取消鋁材出口退稅、中國電解鋁 4,500 萬噸產能上限的來源文件、幾內亞礦權收回事件（2025）。
8. 歐洲冶煉廠減產／復產（2021–2026），盡量量化（萬噸／年）。

**部位**
9. LME Commitments of Traders Report（COTR）鋁：確認網址、格式、是否免費。
10. CFTC COMEX 鋁：用 Socrata 查 commodity_name 含 ALUMINUM 的合約代碼，實測抓一次。

**能源成本**
11. 美國 MISO 現貨電價（Indiana / Kentucky 附近節點；Sebree 冶煉廠在 Kentucky）：MISO 公開市場報告或 EIA 批發電價。
12. 歐洲：TTF 天然氣（Yahoo `TTF=F`）、德國電價（找免費來源，例如 Energy-Charts、Ember）。
13. 中國：動力煤價格（找免費來源）。

## 3. 驗收
- `verify_wp.py al-premium-policy` 通過：sources.csv ≥15 列、實測 ≥6 列、samples/ ≥4 個 ≥10 列的 CSV（其中一個必須是 policy_timeline.csv）、有 probe_*.py。
