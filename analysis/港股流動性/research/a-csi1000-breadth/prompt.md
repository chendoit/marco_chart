# 任務：中證1000 成分股自高點跌幅分布（驗證「80% 小票腰斬」）

先讀 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/_common.md 並遵守。你的任務資料夾：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-csi1000-breadth/
參考既有的東財 kline 抓法：C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/hk-indexes/fetch.py。

## 背景
外部論述稱中證1000 平均自高點回撤約 25%，但「80% 的小票跌幅超過 50%」。這兩個數字看起來互相矛盾，請用實際資料驗證。

## 步驟
1. 取得中證1000（000852）最新成分股清單：中證指數官網 csindex.com.cn 有成分股 Excel（例如 https://csi-web-dev.oss-cn-shanghai-finance-1-pub.aliyuncs.com/static/html/csindex/public/uploads/file/autofile/cons/000852cons.xls 之類，要實測），或東財/其他來源。
2. 對每檔成分股抓日 K（前復權 fqt=1，從 2024-06-01 起；上海 secid 前綴 1.、深圳 0.）。請求間隔 0.4 秒以上；總數約 1000 次。若單次執行會超過 10 分鐘，fetch.py 要支援分批與快取（每檔存一個 csv 在 cache/），分幾次跑完。
3. 對每檔計算：(a) 最新收盤相對近 120 個交易日最高收盤的跌幅；(b) 相對近 250 個交易日最高的跌幅；(c) 相對 2024-10-08 以來最高的跌幅；(d) 近 20 日日均成交額相對前 120 日日均的比值（量能是否枯竭）。
4. 分布：各口徑下跌幅 >50%、30–50%、10–30%、<10%、創新高（距高點 <2%）的檔數與比例；中位數。
5. 若能取得東財個股所屬概念（例如 push2 的個股 f100 行業欄，或 datacenter 的概念板塊成員），把成分股分成「AI 相關」（算力、CPO/光模組、液冷、先進封裝、半導體、人工智慧、AI PC/手機 等概念或行業：電子、通信、計算機）與「其他」，分別給出上述分布。分類方法要在 report 說明；做不到就只用申萬或東財一級行業（電子/通信/計算機 = 科技）粗分並註明。
6. 同時用同樣方法算中證1000 指數本身的 (a)(b)(c) 跌幅，作為比較基準。

## 產出（任務資料夾）
- fetch.py（含 cache/ 與分批）
- breadth_latest.csv：code,name,group,dd_120,dd_250,dd_since_20241008,vol_ratio_20_120
- report.md：除共通章節外，加「## 最新讀數」：上述分布表（全體／AI 相關／其他）、與指數跌幅比較，並明確判定「80% 小票跌幅超過 50%」在中證1000 成分股是否成立。

## 收尾（最後一步，照順序）
- 成功：三行摘要寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-csi1000-breadth/task.done
- 卡住：原因寫進 C:/code/2025-12-05-MacroMicro-Data/analysis/港股流動性/research/a-csi1000-breadth/task.blocked 後停止
