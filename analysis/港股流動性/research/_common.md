# 共通規則（港股流動性數據任務）

- 你是無人值守子 agent：不要問問題，卡住就照收尾規則寫 task.blocked。
- Python 一律用 `C:/code/2025-12-05-MacroMicro-Data/venv/Scripts/python.exe`（已裝 pandas、requests、curl_cffi、yfinance 1.7.0）。執行時加環境變數 PYTHONUTF8=1。
- 只能寫入你自己的任務資料夾。不要改 repo 其他檔案、不要 git 操作、不要 pip install（真的缺套件就寫進 blocked）。
- 不要捏造數字。每個數字都要來自你實際跑出來的資料。查不到就誠實寫「查不到」。
- 單次程式不要跑超過 10 分鐘；網路請求加 timeout 與 1 秒以上間隔，不要爆量請求。
- CSV：UTF-8，第一欄 `date`（YYYY-MM-DD），依日期升冪。
- report.md 用繁體中文，必備章節：`## 結論`、`## 資料來源`、`## 實測結果`（列數、起訖日、最新 5 筆）、`## 踩坑`、`## 建議日更抓法`。
- 程式寫成 `fetch.py`，可重跑、可增量（給 --start 參數，預設抓全部歷史）。
