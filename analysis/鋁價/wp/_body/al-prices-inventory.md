# 指派文件：鋁價、期限結構與庫存的數據來源調研＋實測

## 1. 背景
要研究鋁價（付鵬的「上游傳導」框架＋「LME 低庫存 → 現貨逆價差」論點），先盤點價格、期限結構與庫存數據的可得性。最後會寫一支不進 ETL 的一次性抓取腳本，所以重點是**找到免費、可程式化、有長歷史**的來源，並實測。

## 2. 要找的序列（每項都要在 sources.csv 有一列；能實測的都實測）
**價格與期限結構**
1. LME 鋁 Cash（現貨）結算價、3M 價、Cash–3M 價差（逆價差／升水），日資料。候選：westmetall.com（Market data → LME Aluminium，有歷史表）、LME 官網、investing.com。
2. IMF 全球鋁價月均（FRED `PALUMUSDM`），另找 FRED 上的氧化鋁、美國鋁 PPI 等相關序列（搜尋 FRED 關鍵字 aluminum / alumina）。
3. SHFE 滬鋁主力或連續合約收盤，日；以及 SHFE 氧化鋁期貨（2023 年上市）。候選：上期所官網日行情、新浪財經期貨 API（`hq.sinajs.cn` / `stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine?symbol=AL0`）、東方財富。
4. COMEX 鋁期貨（Yahoo `ALI=F`），以及 Yahoo 上其他鋁相關代號（實測哪些有資料）。
5. 鋁業股票作輔助：AA、CENX、NHY.OL（Hydro）、2600.HK（中鋁）、601600.SS、1378.HK（中國宏橋）、RIO。只需確認 Yahoo 可抓。

**庫存**
6. LME 鋁庫存總量、註銷倉單（cancelled warrants）、在冊倉單（on-warrant），日。候選：westmetall（有 stock 表）、LME 每日庫存報告。
7. LME 庫存分地區／分產地（俄國金屬占比）：LME 每月發布 "Stocks breakdown by origin / brand"，確認網址與格式（xlsx？PDF？是否免費）。
8. SHFE 鋁週庫存（上期所週報，每週五）與 SHFE 氧化鋁倉單。
9. COMEX 鋁庫存（CME 每日倉單報告 `Aluminum_Stocks.xls` 一類的檔案，確認現行網址）。
10. 中國鋁錠社會庫存（SMM／Mysteel，多半付費）：找有無免費轉載或替代（例如新聞每週數字）。

## 3. 特別要確認
- LME 庫存目前大約多少噸（最新日期），近 25 年最低是何時、多少；用你抓到的資料算，不要只抄新聞。
- Cash–3M 價差目前是正（backwardation）還是負（contango），近 3 年的區間。
- 各來源歷史起點，以及單位（公噸、短噸、美元／噸、人民幣／噸）。

## 4. 驗收
- `verify_wp.py al-prices-inventory` 通過：sources.csv ≥15 列、實測 ≥8 列、samples/ ≥5 個 ≥10 列的 CSV（至少要有 LME 價格、LME 庫存、SHFE 鋁、COMEX/Yahoo、FRED 各一）、有 probe_*.py。
