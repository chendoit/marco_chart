# 任務：抓港股四大龍頭每日成交額

先讀 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/_common.md 並遵守。你的任務資料夾：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-giants-turnover/

## 目標
四檔港股的每日成交額（港幣），盡量從 2018-01-01 起到最新交易日：
騰訊 0700.HK、阿里巴巴 9988.HK（2019-11-26 上市）、美團 3690.HK（2018-09-20 上市）、中國移動 0941.HK。

## 步驟
1. 用 Yahoo Finance（yfinance 或 query1/query2 chart API）抓日 K（close、volume）。成交額先以 close × volume 近似，並說明是近似值。
2. 試著找「真實成交額（turnover, HKD）」的免費來源做比對，例如 AASTOCKS、Investing、新浪港股（stock.finance.sina.com.cn / hq.sinajs.cn）、東方財富（push2his.eastmoney.com 的 kline API 有 成交額 欄位，secid 港股為 116.00700 這種格式）。找到的話用它當主來源，Yahoo 近似當備援；並抽 5 個日期比對兩者差距（%）。
3. 檢查拆股、停牌、缺值。

## 產出（全部在任務資料夾）
- fetch.py
- giants_turnover.csv：欄位 date,t0700,t9988,t3690,t0941,giants_total（單位：港幣元；某檔尚未上市留空，giants_total 只加總有值者）
- report.md

## 收尾（最後一步，照順序）
- 成功：三行摘要寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-giants-turnover/task.done
- 卡住：原因寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-giants-turnover/task.blocked 後停止
