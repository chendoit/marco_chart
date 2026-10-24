# 任務：A 股 AI 概念板塊成交額佔全 A 成交額比例

先讀 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/_common.md 並遵守。你的任務資料夾：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-ai-boards/
參考既有的東財 kline 抓法：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-indexes/fetch.py。

## 目標
驗證「A 股流動性集中到 AI 題材」：算 AI 相關概念板塊成交額佔全 A 成交額比例的日序列（盡量從 2023-01-01 起）。

## 步驟
1. 找東財概念板塊代號（secid 形如 90.BKxxxx）。可用板塊列表 API（push2.eastmoney.com/api/qt/clist/get，fs=m:90+t:3 是概念板塊）列出全部概念板塊名稱與代號。挑出：算力（算力概念/東數西算）、CPO/光模組（共封裝光學、光通信模塊）、液冷、先進封裝（Chiplet/先進封裝）、人工智慧（AI 相關總板塊）、AIGC、半導體設備/國產晶片相關、端側 AI（AI PC/AI 手機）。名稱以實際查到的為準，在 report 列出採用的代號與名稱。
2. 每個板塊用 kline（klt=101）抓日成交額。
3. 全 A 成交額：上證綜指 1.000001 加深證成指 0.399001 的「額」（若不確定請說明；另一個子 agent 正在確認口徑，你只要說明你用了哪個）。
4. 衍生：每個板塊佔比；並構造一個「AI 籃子」：因成分股重疊，不能直接加總。優先做法：取 人工智慧 總板塊 + CPO + 算力 三者中最大者作為下限，再另外報告加總值作為上限（明確標註有重疊）。若能取得板塊成分股清單，則改用成分股聯集去重，以個股成交額加總（但請求數不得超過 600 次）。
5. 非 AI 對照：挑幾個傳統板塊（例如 工程機械、化學原料/基礎化工、零售、中藥）的成交額佔比。

## 產出（任務資料夾）
- fetch.py
- ai_boards.csv：date, 各板塊成交額佔比欄（欄名用拼音或英文，並在 report 對照中文）, ai_share_low, ai_share_high, a_turnover
- report.md：除共通章節外，加「## 最新讀數」：AI 籃子佔比最新值、20 日均、2025 年以來高低點與日期；傳統板塊佔比的同樣數字。

## 收尾（最後一步，照順序）
- 成功：三行摘要寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-ai-boards/task.done
- 卡住：原因寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-ai-boards/task.blocked 後停止
