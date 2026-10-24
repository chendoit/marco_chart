# 任務：抓恒生指數與恒生中小型股指數日收盤

先讀 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/_common.md 並遵守。你的任務資料夾：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-indexes/

## 目標
從 2018-01-01 起到最新交易日的日收盤：
1. 恒生指數 HSI
2. 「恒生中小型股指數」：恒生指數公司的 Hang Seng Composite MidCap & SmallCap Index（恒生綜合中小型股指數），另外也抓 Hang Seng Composite SmallCap Index（恒生綜合小型股指數）與 MidCap Index（中型股）作為備選。先確認哪一個最符合「恒生中小型股指數」這個名稱並在 report 說明。

## 候選來源
- Yahoo：^HSI；中小型指數在 Yahoo 的代號要自己查（例如 ^HSCIMS 之類，不確定，要實測）。
- 恒生指數公司官網 hsi.com.hk 的指數表現/歷史資料 API（網頁開發者工具常見 JSON 端點，用 requests/curl_cffi 試）。
- 東方財富 push2his kline API（secid 例如 100.HSI、124.HSCSI 之類，要實測；可用 searchapi.eastmoney.com 搜尋代號）。
- Investing.com 等。

## 產出（全部在任務資料夾）
- fetch.py
- hk_indexes.csv：欄位 date,hsi,hs_midsmall,hs_small,hs_mid（缺的留空），並加一欄 ratio_midsmall_hsi = hs_midsmall/hsi（若 hs_midsmall 抓不到，用 hs_small 並在 report 說明）
- report.md

## 收尾（最後一步，照順序）
- 成功：三行摘要寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-indexes/task.done
- 卡住：原因寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-indexes/task.blocked 後停止
