# 任務：財政部季度再融資公告的 TGA 現金餘額假設（treasury-qra）

先讀共通規則並遵守：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/_common.md`

## 目標
取得 E4：美國財政部每次 Quarterly Refunding／財務估計公告中，對季末 TGA（財政部現金餘額）的假設值，事件型資料。

## 產出
任務資料夾：`C:/code/2025-12-05-MacroMicro-Data/analysis/美元水管流動性/research/treasury-qra/`

`qra_tga_targets.csv`，主鍵 (`date`, `quarter_end`)，依 date、quarter_end 升冪，單位十億美元：
`date,quarter_end,tga_assumption_bn,source_url`
- `date`：公告日；`quarter_end`：該假設對應的季末日（例如 2026-12-31）；一次公告通常有「本季末」和「下季末」兩個假設，各一列。
- 來源：財政部 Quarterly Refunding 頁面（`home.treasury.gov` 的 Quarterly Refunding 公告、「Marketable Borrowing Estimates」新聞稿），每列附上來源網址。
- 範圍：2019 年起到最新一次（預期 2026-11-02～11-04 前後有一次）。
- 重點確認：最新一次公告的年底（2026-12-31）假設，以及前一次的年底假設。影片說「8,500 億 → 7,000 億」，你只需如實取得資料，不要驗證這個說法。
- 如果抓不到最新一次公告，把原因與網址寫進報告和 task.blocked，已取得的資料照常保留。

## 驗收
`verify.py treasury-qra`
