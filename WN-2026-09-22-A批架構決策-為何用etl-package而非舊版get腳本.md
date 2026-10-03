# WN-A 架構決策：40 條缺口用 `etl/` package 做，不照 WN 計畫字面上的舊版 `get_*.py` 風格 (2026-09-22)

> 寫給：不熟悉 `etl/` package 內部設計的人（例如你本人 review 用）。
> 目的：用最少的術語，說明「為什麼改用新框架比較好」，同時證明這不是過度工程——
> 是在用已經寫好、已經驗證過的東西，不是又發明一套新機制。

## 0. 一句話結論

`WN-2026-09-22-A批-40條乾淨缺口實作計畫.md` 這份文件，**分組方式（哪 40 條、怎麼分成 10 個 WP、
先做哪個後做哪個）完全照用**——這部分是對的，不用改。

**要改的只有「動手寫程式的地方」**：不要照 WN 文件字面上寫的去擴充 `get_fred_csv.py`／新開
`get_yfinance_series.py`／改 `get_all_series_data.py` 的 `tasks`，而是寫進
`C:/code/2025-12-05-MacroMicro-Data-wt/etl/etl/sources/*.py` 和
`etl/etl/jobs/m2_replacement/*.py`（這個資料夾目前是空的，就是留給這 40 條用的）。

理由：你在 2026-09-15 已經做過一次架構決策——把 13 支舊爬蟲重構進 `etl/` package，理由是
「要可維護、可擴充的單一 ETL 鏈」。這份 09-22 的 WN 計畫，是在那個決策**之前**的舊思路下寫的，
字面上會叫你把 40 條新的塞回舊架構，等於繞了一圈又要重做一次。

## 1. 為什麼新框架比較好？三個具體機制，不是空泛的「架構比較新」

### 1.1 存檔／防呆：不用自己寫，框架已經做好而且更嚴謹

WN 計畫 §1.2 要你自己寫一個 `_save_merged()` function，邏輯是：

```python
def _save_merged(sid, title, new_data):
    old_data = ...  # 讀舊檔
    merged = {...}  # 用 dict 合併，新值覆蓋舊值
    lost = set(舊日期) - set(merged)
    assert not lost, "資料倒退！"   # 手寫防呆
    ...pickle.dump(...)            # 手寫寫檔
```

這段邏輯**新框架已經有了**，而且做得更完整（`etl/core/storage.py` 的 `save_output()`）：

| 步驟 | WN 計畫要你自己寫 | 新框架已經有 |
|---|---|---|
| 合併新舊資料，新值覆蓋舊值 | 手寫 dict merge | `merge_rows()`，同樣邏輯 |
| 防止資料倒退 | 一行 `assert` | `check_guards()`：偵測到「新資料最後日期 < 舊資料最後日期」直接 raise `StorageGuardError`，不會讓壞資料寫進去 |
| 防止資料量暴跌（例如 API 突然只回一小段） | 沒有處理 | `check_guards()` 額外檢查：新資料筆數 < 舊資料的 80% 也會擋下來（WN 文件提到的「5683/17586/267 無腦覆寫」那次教訓，這裡是系統性防呆，不是靠人記得） |
| 寫檔 | `pickle.dump()` | 「先寫暫存檔、成功才 rename」的 atomic write，程式中途當機不會留下半份壞檔 |
| 記錄這次寫了什麼 | 沒有 | 自動寫一份 `state/meta/<file>.json`（誰寫的、幾筆、最新日期），方便之後追查 |

**意思是**：你不用重寫、也不用維護 `_save_merged()`，只要呼叫 `save_output(...)`，上面五件事全部自動做。
少寫一個函式，還多了三個防呆機制。這不是「多做事」，是「少做事、但更安全」。

### 1.2 執行順序：宣告依賴就好，不用自己排

WN 計畫 §2 WP-A6 特別註明「4456（美日利差）必須排在 2018（日本10Y）之後跑」，
這種「先後順序」在舊架構裡要靠**人工記住、寫在文件裡提醒自己**。

新框架裡，`Job` 直接宣告依賴關係：

```python
Job(name="jp_yield.spread_4456", depends_on=("jp_yield.10y",), ...)
```

寫完這一行，`etl/core/registry.py` 的 `order()` 會自動排序（拓撲排序），保證 `jp_yield.10y`
一定先跑完。就算之後有人不小心把兩個 job 順序寫反，系統也會自動排對，不會因為人手滑就出錯。

### 1.3 「這條抓的是哪個 M² sid」：資料結構本身記得住，不用查文件

舊架構裡，「這支爬蟲對應哪個 M² sid」這件事，只存在於：
- `get_m_square_series.py` 的 `url_list` 裡那一行被註解掉的紀錄
- 或者 WN 文件裡的表格

換句話說，要知道「sid 7148 現在誰在維護」，得去翻文件或翻註解，是**人工對照**。

新框架裡，這是 `Job` 資料結構的一個正式欄位：

```python
Job(name="cboe.ovx", replaces_m2="7148", ...)
```

好處是這件事變成**程式可以查詢、可以驗證**的東西，不是只存在文件裡：
- `etl run --m2-sid 7148` 可以直接選出「取代 sid 7148 的那個 job」來單獨跑
- `etl/checks/verify.py` 可以自動比對「所有宣告 `replaces_m2` 的 job，跟 `mapped_status.json`
  記錄的誤差 % 是否還在合理範圍」——這正是 WN §4 第 3 點想手動做的驗收，框架已經有現成工具

## 2. 這樣會不會太複雜、過度實作？

不會，理由是：

1. **這些機制不是為了這 40 條新寫的**，是 2026-09-15 開始的重構（WP-R1～WP-R2F）已經寫好、
   也已經拿 13 支舊爬蟲驗證過的東西（見 `etl/reports/WP-R1.md`、`WP-R2A.md` 等驗收紀錄）。
   我們是「重用」，不是「新增一層抽象」。
2. **實際要寫的程式碼量，兩邊差不多**：不管照舊架構還是新架構，「怎麼從 yfinance／FRED／CBOE
   API 抓資料」這段邏輯都得寫一次（WN 文件說可以直接搬 `fetch_mapped.py` 的程式碼，這點兩邊通用，
   不會因為框架不同而多寫）。差別只在於「抓到資料之後，存檔／防呆／排序／記錄」這幾件事，
   新架構是呼叫現成函式，舊架構要自己重寫一份放進每支腳本裡。
3. **新架構砍掉了 WN 計畫裡原本要手寫的三段程式**（`_save_merged()`、手動排順序、
   驗收腳本），淨結果是**寫得更少**，不是更多。

## 3. 實際會長什麼樣子？用 WP-A2（yfinance，14 條）當例子

WN 計畫說：新開 `get_yfinance_series.py`，把 `fetch_mapped.py` 的 `fetch_yf()`／
`fetch_yf_spread()` 搬過去，自己配一個 `tasks` 入口給 `get_all_series_data.py` 掛。

新架構做法：

```python
# etl/sources/yfinance_series.py —— 只管「怎麼抓資料」，抓法跟 WN 計畫一樣搬 fetch_mapped.py 的邏輯
def fetch_yf_close(ctx, ticker: str) -> list[list]:
    ...  # yfinance chart API v8，回傳 [[datetime 08:00, float], ...]

def fetch_yf_ratio(ctx, ticker_a: str, ticker_b: str, scale: float = 1.0) -> list[list]:
    ...  # 4481 銅金比用得到

# etl/jobs/m2_replacement/yfinance.py —— 只管「這條要抓什麼、存去哪、取代哪個 sid」
from etl.core.types import Job, Output
from etl.sources import yfinance_series

JOBS = [
    Job(
        name="m2.yf_2",
        group="m2_replacement",
        fetch=lambda ctx: {"m2_2": yfinance_series.fetch_yf_close(ctx, "^XYZ")},
        outputs=(Output("m2_2", title="...", kind="level"),),
        replaces_m2="2",
        policy="append",   # 存檔/防呆/排序全部交給框架
    ),
    # ... 其餘 13 條同樣寫法
]
```

抓資料的邏輯（`fetch_yf_close`）跟 WN 計畫要搬的程式碼是同一份，唯一差別是「存檔」那段
從自己寫 `_save_merged()` 改成宣告 `policy="append"` 交給框架處理。

## 4. 下一步

如果你同意這個方向，接下來我會照 WN 計畫 §3 的順序（WP-A2 → WP-A1/A1b → WP-A3 →
A4/A7 → A6 → A8 → A5 → A9，A10 卡在 WN-B 查證結果）逐一派工，每個 WP 用同一套模式：
新 `etl/sources/*.py`（如果是全新資料源）＋ `etl/jobs/m2_replacement/*.py`（宣告 `replaces_m2`），
驗收用 `etl/checks/verify.py --m2-sid <sid>` 取代 WN §4 手寫的驗收腳本。

## 檔案路徑

- 原始計畫（分組/順序沿用）：`C:/code/2025-12-05-MacroMicro-Data/WN-2026-09-22-A批-40條乾淨缺口實作計畫.md`
- 主計畫文件（09-15 架構決策出處）：`C:/code/2025-12-05-MacroMicro-Data/PLAN-2026-09-15-etl-refactor-m2-replacement.md`
- 新框架核心：`etl/core/types.py`（`Job`/`Output`）、`etl/core/storage.py`（`save_output`）、
  `etl/core/registry.py`（`select`/`order`）、`etl/checks/verify.py`（驗收）
- 可抄的原始程式碼：`C:/code/2026-09-11-fincept-terminal/migration/fetch_mapped.py`
