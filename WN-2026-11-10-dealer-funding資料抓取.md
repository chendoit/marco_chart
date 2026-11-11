# WN：dealer-funding 資料抓取（2026-11-10）

## 這一輪做了什麼
- 第一輪（子 agent，Sonnet 5.5，`claude -p`，花費約 0.51 USD）抓了週頻與季頻資料，產出在 `analysis/美元水管流動性/research/dealer-funding/`。
- 驗收：`verify.py dealer-funding` 輸出 `PASS dealer-funding`（`verify_output.txt` 同步記錄）。
- 第二輪（Opus medium，`--max-budget-usd 2`，經 Orca 終端派出）嘗試補日頻資料，結果寫在 `dealer-funding/daily/`，完成後更新本 WN。

## 三個 CSV 的現況

| 檔案 | 對應 | 期間 | 頻率 | 注意 |
|---|---|---|---|---|
| `pd_financing.csv` | F1 一級交易商融資與美債部位（NY Fed） | 2018-01-03 ~ 2026-10-28 | 週 | 多數系列有缺週，未補、未查原因 |
| `repo_haircuts.csv` | F2 回購折扣率 | 2018-03-31 ~ 2026-09-30 | 季（OFR Form PF 過度擔保率）＋ SCOOS | **沒有真正的 haircut 序列**，過度擔保率只是近似 |
| `hedge_fund_leverage.csv` | F4 對沖基金槓桿（OFR／Form PF） | 2018-03-31 ~ 2026-09-30 | 季 | 最新只到 2026-06-30，落後半年以上 |

## 已知的缺口
- F2 沒有公開的逐日 repo haircut；OFR 主 API 的 repo 資料集只有利率與成交量。
- `PDSIRRA-CDTOT` 的來源描述與代碼不符，照抄未改。
- F1 的 PD 來源本身是週頻，不是日頻。
- F4 的 Form PF 是季頻，且延遲約半年。

## 第二輪：日頻資料結果（Opus medium，花費 0.46 USD）
- 日頻 **haircut 找不到公開來源**。`daily/daily_repo.csv` 的 13 個系列全部是利率／成交量／餘額的代理，不是 haircut。
- 來源：OFR repo 資料集（DVP、GCF、排除 Fed 的三方回購，Final 版）與 NY Fed SOFR／BGCR／TGCR（利率與成交量）。
- 期間 2018-01-02 ～ 2026-11-06，25,443 列，相鄰日期間隔中位數 1 天。GCF 隔夜利率稀疏（270 筆）。
- OFR Final 版只到 2026-06-30。要近期資料需改抓 Preliminary 版，這次沒抓。
- F1（PD）只有週頻，F4（Form PF）只有季頻，都沒有日頻來源。
- 驗收：`verify.py dealer-funding` 重跑 `PASS dealer-funding`（python 退出碼 0）。既有檔案未被改動。
- 詳細說明：`dealer-funding/daily/README.md`；腳本 `daily/fetch_daily.py`。

## 第三輪：替代指標的近似檢查（Opus medium，花費 0.77 USD）
- 目的：沒有日頻 haircut 時，找能近似 haircut 效果的日頻代理，並用季頻 Form PF 過度擔保率檢查同步程度。
- 結果：沒有任何單一代理可以替代 haircut。最強的是 `dvp_ov_to_tri_vol`（DVP 未平倉量／三方成交量），季末水準 r = −0.64（n = 33）。
- 三個指標的組合（SOFR−TGCR、DVP−三方利差、SOFR 四分位距，等權 z 分數）：季末水準 r = −0.59（n = 33），季變動 r = −0.39（n = 32）。
- **方向與直覺相反**：利率價差擴大、分散度上升的季，Form PF 過度擔保率反而較低。解讀是組成效應：基差交易擴張使低 haircut 部位增加，把平均值往下拉。代理量到的是「低 haircut 槓桿的規模」，不是「haircut 收緊」。
- 限制：只有 32–34 季，且做了 88 組比較，部分 |r| > 0.4 可能是偶然；分段後符號不穩定；季末 `bgcr_tgcr_bp` 常為 0，無法計算。
- 用法：日頻監控可參考組合指標，讀法是「壓力升高 ≈ 低 haircut 槓桿部位擴大」，不能當 haircut 本身。
- 詳細：`dealer-funding/substitute/README.md`、`corr.md`。

## 驗收註記
- 第一次驗收的 `EXIT=0` 取的是 `tail` 的退出碼，不是 Python 的。第二次重跑時 Python 退出碼是 0。
