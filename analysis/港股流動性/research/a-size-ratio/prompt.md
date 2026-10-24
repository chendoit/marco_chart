# 任務：A 股大小盤分化、全 A 成交額與兩融餘額日序列

先讀 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/_common.md 並遵守。你的任務資料夾：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-size-ratio/
參考既有的東財 kline 抓法：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-indexes/fetch.py（URL、headers、重試）。

## 目標（2018-01-01 起到最新交易日，日頻）
1. 收盤：滬深300（東財 secid 可能是 1.000300）、中證1000（1.000852）、中證A500（1.000510，2024 年底才發布，之前留空）、中證2000（可能 2.932000，要實測）、上證綜指（1.000001）。代號都要實測確認名稱正確（kline 回傳的 name 欄）。
2. 全 A 成交額：上證綜指（1.000001）與深證成指或深證綜指（0.399001 / 0.399106）的「額」欄。先實測判斷這些「額」是否為全交易所成交額（用 2024-10-08 全 A 約 3.48 萬億元這類新聞紀錄日比對），選出加總後最接近全 A 成交額的組合，並在 report 說明。若有北交所也一併說明是否包含。
3. 兩融餘額（融資融券餘額，全市場）：東財 datacenter-web API（例如 reportName=RPTA_RZRQ_LSHJ 之類，要實測），或其他免費來源。
4. 衍生：ratio_csi1000_hs300 = csi1000/hs300；ret20_spread = 中證1000 20 日報酬 − 滬深300 20 日報酬（對應原文說的「紅柱」：小盤相對大盤的落差）；csi1000 自 2024-10-01 以來高點的回撤%、hs300 同上。

## 產出（全部在任務資料夾）
- fetch.py
- a_size_ratio.csv：date,hs300,csi1000,csia500,csi2000,sh_comp,a_turnover,margin_balance,ratio_csi1000_hs300,ret20_spread（缺的留空；成交額與餘額單位寫在 report）
- report.md：除共通章節外，加「## 最新讀數」：最新一天滬深300、中證1000 收盤，中證1000/滬深300 各自自 2024-10 以來高點的回撤%，ret20_spread 最新值與其 2018 年以來百分位，兩融餘額最新值與 60 日變化。

## 收尾（最後一步，照順序）
- 成功：三行摘要寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-size-ratio/task.done
- 卡住：原因寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-size-ratio/task.blocked 後停止
