# 任務：抓港股全市場每日成交額

先讀 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/_common.md 並遵守。你的任務資料夾：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-market-turnover/

## 目標
香港交易所（HKEX）主板＋GEM 證券市場的每日總成交額（港幣），盡量從 2018-01-01 起到最新交易日。這是最難找的序列，請多試幾個來源。

## 候選來源（逐一實測，記下哪些可行）
1. 東方財富 push2his.eastmoney.com kline API：恒生指數 secid=100.HSI 的 成交額 欄位（注意：這可能只是指數成分股成交額，不是全市場，要分辨並寫清楚）。
2. HKEX 官網：每日行情報告 Daily Quotations（https://www.hkex.com.hk/eng/stat/smstat/dayquot/d<yymmdd>e.htm，內含 "TOTAL TURNOVER" 或市場成交額）、Market Statistics / 歷史日成交額檔案。
3. 新浪財經、AASTOCKS「大市成交」、etnet、Investing 等任何有「大市成交額」歷史的頁面或 API。
4. 南向資金相關（港股通成交）可順帶記錄，但不是主目標。

## 要求
- 分辨清楚：全市場成交額 vs 恒指成分股成交額 vs 只含主板。拿 HKEX 官方公布數字抽 3–5 個日期核對（例如 HKEX 新聞稿常提的某日成交額）。
- 若只有 HKEX 每日行情檔可用，fetch.py 要能逐日抓（有快取、跳過假日、可增量），先抓最近 400 個交易日證明可行，全歷史回補留給之後（在 report 寫預估時間）。

## 產出（全部在任務資料夾）
- fetch.py
- market_turnover.csv：欄位 date,market_turnover（港幣元），另可加 source 欄
- report.md（多一章 ：來源、涵蓋範圍、起始日、是否全市場、可行性）

## 收尾（最後一步，照順序）
- 成功：三行摘要寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-market-turnover/task.done
- 卡住：原因寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-market-turnover/task.blocked 後停止
