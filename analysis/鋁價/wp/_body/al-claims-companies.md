# 指派文件：逐條查證鋁市場論點＋ Alcoa／Century 財務敏感度

## 1. 背景
收到一段分析文字（下稱「貼文」），要逐條查證，並把美系兩家鋁業公司的敏感度數據找出原始出處。

## 2. 待查證論點（claim_id 1–10）
1. LME 鋁庫存跌至約 24.5 萬噸，本世紀新低；消費天數約 50 天。
2. 英美 2024 年制裁禁止交割新俄鋁；42.5 萬噸缺口將引發劇烈現貨逆價差（backwardation）。
3. 歐洲在能源危機後已減產 50% 原鋁。
4. 歐洲完稅溢價與美國中西部溢價（US Midwest Premium）將同步突破歷史區間（查證目前水準與歷史高點）。
5. 中國 4,500 萬噸產能上限；「鋁水直接合金化」使可出口的實體純鋁錠極為緊缺。
6. Alcoa（AA）垂直整合、100% 控股 AWAC；LME 鋁價每變動 $10/t，淨利變動約 $1,100 萬美元。
7. Century（CENX）滿載出貨 63 萬噸；LME＋溢價每漲 $400/t，EBITDA 增加 $2.52 億美元。
8. Alcoa 是氧化鋁淨賣方，API 上漲擴大精煉毛利；Century 外購氧化鋁，高價侵蝕冶煉價差。
9. Alcoa 水電長約＋Massena 廠電價與 LME 收益共享；Century Sebree 廠曝露於 MISO 現貨尖峰電價。
10. Alcoa 的 ELYSIS 無碳冶煉技術；Century 受惠 IRA 45X 稅收抵免，每噸約 $90 EBITDA。

每條給出 `verdict`（成立／部分成立／不成立／無法驗證）、證據摘要、原始出處網址、資料日期。數字類一定要找到原始數據（公司 10-K／10-Q／法說簡報、LME、官方統計），新聞只能當輔助。已知線索：Alcoa 原持有 AWAC 60%，2024 年 8 月完成收購 Alumina Ltd 後持有 100%——請查證並寫入。

## 3. 公司數據（實測）
- SEC EDGAR XBRL companyfacts：`https://data.sec.gov/api/xbrl/companyfacts/CIK<10位>.json`，**必須帶 `User-Agent: aluminum-research chunpin.chen@gmail.com`**（SEC 規定要有可識別 UA）。Alcoa CIK 0001675149、Century CIK 0000949157（請自行確認）。
- 抽出近 10 年季度：營收、淨利、EBITDA 若無則用營業利益＋折舊攤銷、出貨量（若在 XBRL 中）。寫成 `samples/aa_quarterly.csv`、`samples/cenx_quarterly.csv`。
- 從最新 10-K／法說簡報找官方敏感度表（Alcoa 年度展望簡報通常有「$100/t LME 變動對 EBITDA 影響」；Century 有 LME／Midwest 溢價敏感度），把原文數字與頁面網址寫進 report。
- Yahoo 抓 AA、CENX 日股價（≥10 年），存 samples。

## 4. 產出（除共通規範外，另加）
- `.agent-run/out/claims.csv`：欄位 `claim_id,claim,verdict,evidence,source_url,as_of`，claim_id 1–10 都要有，verdict 只能是 成立／部分成立／不成立／無法驗證，source_url 不可空。
- report.md 的 `## 結論` 要寫：貼文整體可信度、哪幾條數字錯或過時、正確的數字。另加 `## 公司敏感度` 一節，整理成表（公司、敏感度項目、官方數字、出處、期間）。

## 5. 驗收
- `verify_wp.py al-claims-companies` 通過：claims.csv 1–10 齊全；sources.csv ≥6 列、實測 ≥3；samples/ ≥2 個 ≥10 列 CSV；有 probe_*.py。
