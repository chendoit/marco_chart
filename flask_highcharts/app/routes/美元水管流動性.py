"""美元水管流動性：把「美元融資擠壓 → 資產同跌」的邏輯鏈拆成 11 張圖，一張圖回答一個問題（⑩⑪ 為分鐘級，直接讀 research 資料夾的 5 分鐘 CSV，其餘走 pkl）。

依據：WN-2026-11-09-美元水管流動性擠壓-邏輯鏈與指標拆解.md
資料來源（①～⑨ 走 data/*.pkl，由每日 ETL get_all_series_data.py 更新；⑩⑪ 讀 research 資料夾 CSV）：
  ① ②   SOFR `sofr_rate`、IORB `fed_IORB`（get_fed_series.py：NY Fed secured rates API／FRED IORB）；
        ① 右軸 id 2 = S&P 500（舊 M² 序列）
  ③     SOFR P99 `sofr_percent99`、成交量 `sofr_volume`（get_fed_series.py）；
        SRF 利率 96003（FRED DFEDTARU，get_fred_csv.py）
  ④ ⑤   準備金 7449（FRED WLODLL，get_fred_csv.py）、ON RRP `fed_RRPONTSYD`（get_fed_series.py）、
        TGA 29123（Fiscal Data API，get_fiscal_data.py）
  ⑥     Fed T-bill 96001（FRED WSHOBL，週三）；近 4 週變化由 96001 現算
  ⑦     SRF 用量 96002（FRED RPTTLD，get_fred_csv.py）
  ⑧     槓桿基金美債期貨淨部位 `cftc_tff_lev_net_{2Y,5Y,10Y}`（CFTC TFF，get_cftc_treasury.py，週資料）
  ⑨     QQQ `etf_QQQ_close`、GLD `etf_GLD_close`（Yahoo chart API，get_yfinance_series.py）、
        美元指數 483（Yahoo DX-Y.NYB，同上；週日假日點已濾掉）
  ⑩ ⑪   research/tv-gld-1m/gld_5m.csv、research/xauusd-tv/xauusd_oanda_5m.csv（5 分鐘線，只有 10/29~11/06）
  備用   `fed_DFII10` 10 年實質利率（已定義 wp_real_yield_10y，目前沒有圖使用）
需要現算的序列以 `wp_` 為前綴，注入 highcharts_utils 的 series cache（不落地 pkl；cache 被清掉後下次請求重建）。
"""
import os

import pandas as pd

from app.utils import ChartModule, highcharts_utils as _hu, load_series_data

START = "2018-01-01"   # 研究資料從 2018 起，圖表也統一從這裡開始
# 分鐘線（⑩⑪）沒有進 pkl ETL，直接讀研究資料夾的 CSV；檔案不在時該圖顯示說明而非報錯
RESEARCH_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "analysis", "美元水管流動性", "research")


# ============================================================
# 讀資料的小工具
# ============================================================

def _pkl(sid):
    d = load_series_data(sid)
    s = pd.Series({pd.Timestamp(t).normalize(): float(v) for t, v in d["data"]
                   if v is not None and not pd.isna(v)})
    return s.sort_index()


SRF_START = "2021-07-28"   # SRF 首次操作日；RPTTLD 更早的值是舊式臨時 OMO，不算 SRF


def _price_ret(pkl_id):
    """日報酬 (%)，用收盤價。"""
    return _pkl(pkl_id).pct_change().dropna() * 100


def _lev_net(label):
    """槓桿基金（對沖基金）在該期限美債期貨的淨部位（千口）；負數 = 淨空單。"""
    return _pkl(f"cftc_tff_lev_net_{label}") / 1000


def _srf_usage():
    s = _pkl(96002)
    return s[s.index >= SRF_START]


# ============================================================
# 衍生序列（id → (圖上顯示的名稱, 計算函式)）
# ============================================================

def _sofr_iorb_bp():
    j = pd.concat([_pkl("sofr_rate"), _pkl("fed_IORB")], axis=1, join="inner").dropna()
    return (j.iloc[:, 0] - j.iloc[:, 1]) * 100


def _p99_minus_srf_bp():
    srf = _pkl(96003)   # SRF 利率 = 目標區間上限
    j = pd.concat([_pkl("sofr_percent99"), srf], axis=1, join="inner").dropna()
    return (j.iloc[:, 0] - j.iloc[:, 1]) * 100


DERIVED = {
    "wp_sofr_iorb_bp": ("SOFR − IORB（bp）｜>0 = 回購市場利率高過銀行存 Fed 的利率", _sofr_iorb_bp),
    "wp_p99_srf_bp": ("SOFR 最貴 1% 的成交 − SRF 利率（bp）｜>0 = 市場上有人付得比 Fed 貸款還貴", _p99_minus_srf_bp),
    "wp_sofr_volume_tn": ("SOFR 回購成交量（兆美元）", lambda: _pkl("sofr_volume") / 1000),
    "wp_rrp_bn": ("ON RRP 餘額（十億美元）｜貨幣基金存在 Fed 的隔夜錢", lambda: _pkl("fed_RRPONTSYD")),
    "wp_tga_tn": ("TGA 財政部帳戶（兆美元）", lambda: _pkl(29123) / 1e6),
    "wp_reserves_tn": ("銀行準備金（兆美元，週三）", lambda: _pkl(7449) / 1e6),
    "wp_fed_bills_bn": ("Fed 持有 T-bill（十億美元，週三）", lambda: _pkl(96001) / 1000),
    "wp_fed_bills_chg4w_bn": ("Fed T-bill 近 4 週變化（十億美元）｜>0 = Fed 在補水", lambda: _pkl(96001).div(1000).diff(4)),
    "wp_srf_usage_bn": ("SRF 單日用量（十億美元）", _srf_usage),
    "wp_lev_net_2y": ("槓桿基金 2 年期美債期貨淨部位（千口）", lambda: _lev_net("2Y")),
    "wp_lev_net_5y": ("槓桿基金 5 年期美債期貨淨部位（千口）", lambda: _lev_net("5Y")),
    "wp_lev_net_10y": ("槓桿基金 10 年期美債期貨淨部位（千口）", lambda: _lev_net("10Y")),
    "wp_qqq_ret": ("QQQ 單日報酬（%）", lambda: _price_ret("etf_QQQ_close")),
    "wp_gld_ret": ("黃金 GLD 單日報酬（%）", lambda: _price_ret("etf_GLD_close")),
    "wp_dxy_ret": ("美元指數單日報酬（%）", lambda: _pkl(483).pipe(lambda s: s[s.index.dayofweek < 5]).pct_change().dropna() * 100),   # 濾掉週日假日點
    "wp_real_yield_10y": ("10 年期實質利率（%）", lambda: _pkl("fed_DFII10")),
}


def _ensure_derived():
    """把 wp_* 序列放進 highcharts_utils 的 series cache（cache 被清掉後會重建）。"""
    for sid, (title, fn) in DERIVED.items():
        key = (sid, None)
        if key in _hu._series_cache:
            continue
        s = fn().dropna()
        s = s[s.index >= START]
        _hu._series_cache[key] = {
            "title": title,
            "data": [[t.to_pydatetime(), float(v)] for t, v in s.items()],
        }


# ============================================================
# 分鐘級（5 分鐘線）：只有 2026-10-29 ~ 11-06 約一週，走 custom_config，不走日頻管線
# （標準管線會把日期轉成 YYYY-MM-DD 並補成工作日，會丟掉時間）
# ============================================================
EVENT_DAY = "2026-10-30"      # 影片主張的重挫日
EVENT_CLOCK = "15:45"         # 影片說的「追繳保證金」時點（美東）
RED = "rgba(192,75,75,1)"


def _et_ms(date, clock):
    """美東時間 → 毫秒。故意當成 UTC 傳給 Highcharts，軸上顯示的就是美東鐘點，不隨瀏覽器時區位移。"""
    return int(pd.Timestamp(f"{date} {clock}").timestamp() * 1000)


def _intraday_config(rel_path, title, line_name, y_lines):
    path = os.path.join(RESEARCH_DIR, rel_path)
    if not os.path.exists(path):
        return {"chart": {"type": "line"}, "title": {"text": title},
                "subtitle": {"text": f"找不到分鐘線資料 {rel_path}（research 資料夾未部署）"}, "series": []}
    df = pd.read_csv(path, dtype={"time_et": str})
    ts = [_et_ms(d, t) for d, t in zip(df["date"], df["time_et"])]
    event_x = _et_ms(EVENT_DAY, EVENT_CLOCK)
    x_lines = [{"value": event_x, "color": RED, "width": 2, "dashStyle": "ShortDash", "zIndex": 5,
                "label": {"text": f"{EVENT_DAY[5:]} {EVENT_CLOCK} 追繳保證金？", "rotation": 0,
                          "style": {"color": RED, "fontSize": "11px"}}}]
    x_band = [{"from": _et_ms(EVENT_DAY, "00:00"), "to": _et_ms(EVENT_DAY, "23:59"),
               "color": "rgba(192,75,75,0.06)", "label": {"text": "10/30 重挫日", "style": {"fontSize": "11px"}}}]
    y_plot = [{"value": v, "color": "#888888", "width": 1, "dashStyle": "Dot",
               "label": {"text": lb, "align": "left", "style": {"fontSize": "11px"}}} for v, lb in y_lines]
    return {
        "chart": {"zoomType": "x"},
        "title": {"text": title},
        "subtitle": {"text": f"時間軸為美東時間；資料 {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}，共 {len(df)} 根 5 分鐘線；"
                             "休市時段在軸上被略過", "style": {"fontSize": "11px"}},
        "xAxis": {"type": "datetime", "plotLines": x_lines, "plotBands": x_band},
        "yAxis": [{"title": {"text": line_name}, "height": "70%", "plotLines": y_plot},
                  {"title": {"text": "成交量"}, "top": "75%", "height": "25%", "offset": 0}],
        "tooltip": {"shared": True, "valueDecimals": 2, "xDateFormat": "%m/%d %H:%M（美東）"},
        "legend": {"enabled": True},
        "credits": {"enabled": False},
        "rangeSelector": {"enabled": True, "selected": 2, "buttons": [
            {"type": "day", "count": 1, "text": "1d"}, {"type": "day", "count": 3, "text": "3d"},
            {"type": "all", "text": "全部"}]},
        "navigator": {"enabled": True},
        "plotOptions": {"series": {"dataGrouping": {"enabled": False}}},
        "series": [
            {"name": line_name, "type": "line", "yAxis": 0, "color": "rgba(255,165,0,1)",
             "data": [[t, float(v)] for t, v in zip(ts, df["close"])]},
            {"name": "成交量", "type": "column", "yAxis": 1, "color": "rgba(150,150,150,0.5)",
             "data": [[t, float(v)] for t, v in zip(ts, df["volume"])]},
        ],
    }


def _gld_intraday():
    cfg = _intraday_config("tv-gld-1m/gld_5m.csv", "⑩ 分鐘級：GLD 5 分鐘線，10/30 日內怎麼跌的",
                           "GLD 收盤價（美元）", [(368.57, "10/29 收盤 368.57"), (354.67, "10/30 日低 354.67")])
    summary = _note(
        "影片說 10/30 賣壓有時間規律：開盤降槓桿、倫敦定盤、15:45 追繳保證金，GLD 呈三段下殺。這張圖用 5 分鐘線檢查這個說法。",
        "紅色虛線是 15:45；灰色點線是前一日收盤與當日低點。重點看：<b>跌幅在哪個時段發生</b>、有沒有單點急殺。",
        "<b>只有一天樣本，不能證明因果。</b>日低 354.67 確實出在 15:45，與影片相同；"
        "但開盤就跳空（368.57 → 361.5，已佔全日跌幅一半以上），也就是「開盤降槓桿」發生在美股開盤前，"
        "這張圖看不到；單根 5 分鐘線最大跌幅只有 −0.25%，沒有劇烈急殺。"
        "資料限制：1 分鐘線 10/30 取不到所以用 5 分鐘線；11/2 缺 14:25–14:45 共 5 根；沒有盤前盤後。")
    return {"config": cfg, "summary": summary}


def _xau_intraday():
    cfg = _intraday_config("xauusd-tv/xauusd_oanda_5m.csv",
                           "⑪ 分鐘級：黃金現貨 XAUUSD（OANDA）5 分鐘線，含亞洲與倫敦時段",
                           "XAUUSD 收盤價（美元）", [])
    summary = _note(
        "GLD 只有美股交易時段。黃金現貨近 24 小時交易，可以補上 GLD 看不到的亞洲、倫敦時段，檢查「開盤降槓桿、倫敦定盤」前後有沒有賣壓。",
        "同樣看紅色虛線（15:45）與 10/30 淡紅色底色；<b>跌幅主要落在哪一段時間</b>，決定影片「開盤降槓桿」的說法站不站得住。",
        "影片的 −3.62% 用的是現貨，本地日線只有 GLD −3.47%、GC=F −3.29%，現貨分鐘線可補這個缺口。"
        "資料限制：只有 10/29 02:25 ET ~ 11/06 16:55 ET 約一週；OANDA 與 TVC:GOLD 中位差約 0.15 美元，"
        "FX_IDC 資料不完整未採用；<b>黃金殘差（−2.86σ）尚未以現貨重算</b>。")
    return {"config": cfg, "summary": summary}


# ============================================================
# 圖表說明：固定三段「這張圖看什麼／怎麼讀／目前證據」，讀者不用懂水管也能看
# ============================================================

def _note(what, read, evidence):
    return (f"<b>這張圖在看什麼：</b>{what}<br>"
            f"<b>怎麼讀：</b>{read}<br>"
            f"<b>證據強度：</b>{evidence}")


_module = ChartModule(
    filename='美元水管流動性',
    charts=[
        {
            "title": "① 整套邏輯一句話：美元融資變貴 → 被迫賣資產 → 股金債一起跌",
            "ids": ["wp_sofr_iorb_bp", 2],
            "axis": [0, 1],
            "plot_lines": [("wp_sofr_iorb_bp", [0])],
            "summary": (
                "<b>整個故事：</b>金融體系每天要靠「回購市場」借隔夜美元周轉。"
                "當這個市場的錢變少、利率被推高，借不到錢的機構（尤其是高槓桿對沖基金）只好把手上能賣的資產先賣掉換現金，"
                "於是平常不會一起跌的股票、黃金、白銀、比特幣同時下跌。<br>"
                "<b>影片的判斷準則：</b>股金同跌時，問題不在公司賺不賺錢（分子），而在美元流動性夠不夠（分母）。<br>"
                "<b>下面 10 張圖依序驗證：</b>② 回購利率 → ③ 最貴的借款 → ④ 水位 → ⑤ 誰把錢抽走 → ⑥ Fed 有沒有補水 → "
                "⑦ 救急窗口有沒有人用 → ⑧ 對沖基金的部位 → ⑨ 股金同跌那天的美元與黃金 → ⑩⑪ 當天的分鐘級走勢。<br>"
                "<b>整體結論（截至 WN 2026-11-10）：</b>回購利率確實偏緊，但「美元荒」的證據還不夠——"
                "10/30 當天美元指數反而下跌、救急窗口沒人用、11/5 大跌時利差反而回落。這是一個<b>值得追蹤的假說，還不是定論</b>。<br>"
                "<details><summary><b>本頁的簡化與未涵蓋（點開看）</b></summary>"
                "<b>用代理指標，不是指標本身：</b>⑧ 槓桿基金期貨淨部位只是基差交易的代理；準備金用週三水位"
                "（series_7449 標題寫超額準備金，實為準備金）；「RMP 是否重啟」用 Fed T-bill 持有量代替。<br>"
                "<b>資料缺口：</b>交易商融資與折扣率（haircut）沒有日頻來源，LCLoR 沒有資料，對沖基金槓桿倍數只有季頻（落後約 4 個月）。"
                "→ 傳導鏈第 8、9 環（交易商收緊、基金砍倉）本頁<b>沒有圖，也沒有數據證明</b>。<br>"
                "<b>已有資料但本頁沒畫：</b>SPX gamma 翻轉線與淨 gamma（數字未核對）、FIMA 用量、財政部年底 TGA 目標、標售與國債回購、"
                "核心 PCE 與 12 月升息機率、TGCR／BGCR／EFFR 交叉確認。<br>"
                "<b>算過但沒畫成圖：</b>黃金殘差（−2.86σ，依視窗而定）；樣本外測試（11/3 利差 +7bp 股市沒跌、11/5 大跌）只寫在文字裡。"
                "「股金同跌」訊號（A4）與利差回測都還沒做。<br>"
                "<b>無法驗證：</b>影片的 3.34 倍乘數沒有公開係數。<br>"
                "<b>日頻管線的處理：</b>週資料（準備金、T-bill、CFTC）被線性內插成工作日資料，所以線看起來像每天更新；"
                "SOFR 系列的 pkl 只從 2021-08 起；SRF 2024-04 以前的用量混入其他隔夜操作。<br>"
                "<b>分鐘級：</b>只有 ⑩ GLD、⑪ XAUUSD 的 5 分鐘線，約一週、單一事件日，不能當統計證據。<br>"
                "<b>時效：</b>說明文字裡的數字是 WN（2026-11-10）當時的核對結果，不會隨資料更新；圖上的線才是最新資料。"
                "</details>"
            ),
        },
        {
            "title": "② 回購市場有多緊？SOFR − IORB（核心指標）",
            "ids": ["wp_sofr_iorb_bp"],
            "plot_lines": [("wp_sofr_iorb_bp", [0])],
            "summary": _note(
                "SOFR 是「拿美債抵押借隔夜錢」的利率；IORB 是銀行把多餘的錢存在 Fed 能賺到的利率。",
                "銀行有多餘的錢時，不會把錢貸出去賺比 IORB 還低的利息，所以 SOFR 正常會<b>低於或貼近 IORB</b>。"
                "若 SOFR 持續<b>高於 IORB（線在 0 以上）</b>，代表市場上缺錢、借款人願意多付利息，這就是「水管變緊」。",
                "回購數字與本地資料大致吻合（10/27 約 +5bp、連續多日為正）。但 11/3 利差最高（+7bp）時股市沒跌，"
                "11/5 利差回落到 +2bp 反而大跌，所以<b>利差與股市下跌的對應，目前沒有被樣本外資料支持</b>。"
            ),
        },
        {
            "title": "③ 最貴的借款付多少？SOFR 最高 1% 成交 − SRF 利率",
            "ids": ["wp_p99_srf_bp", "wp_sofr_volume_tn"],
            "axis": [0, 1],
            "plot_lines": [("wp_p99_srf_bp", [0])],
            "summary": _note(
                "SOFR 是平均值，會掩蓋極端情況。這裡看「最貴的那 1% 成交」的利率，有沒有碰到 Fed 常設回購工具（SRF）的利率。"
                "SRF 是 Fed 開的緊急貸款窗口，等於借款利率的天花板。",
                "線<b>接近或高於 0</b>，表示最急需錢的人付的利息已經跟向 Fed 借差不多，水管最緊的角落快要頂到天花板。"
                "右軸成交量上升，代表市場靠回購借的錢變多。",
                "影片說 P99 超過 4% 與本地資料相符（10/27 為 4.04%，只比 SRF 的 4.00% 高 4bp），事實層面可信；"
                "但這只說明「有點緊」，不能單獨證明「美元荒」。"
            ),
        },
        {
            "title": "④ 水池還剩多少？銀行準備金與 ON RRP",
            "ids": ["wp_reserves_tn", "wp_rrp_bn"],
            "axis": [0, 1],
            "summary": _note(
                "準備金是銀行放在 Fed 的錢，是整個金融體系的「水位」。ON RRP 是貨幣基金放在 Fed 的隔夜錢，過去是一大塊「備用水」。",
                "備用水（ON RRP，右軸）已經見底、接近 0，代表之後<b>任何抽水都會直接動到準備金（左軸）</b>。"
                "準備金掉得越接近 2.85 兆附近，市場越容易出現利率跳升（影片提到的警戒區，非官方門檻）。",
                "準備金 10/28 為 2.895 兆與影片一致，但到 11/4 已回升到 2.96 兆。"
                "ON RRP 見底屬實；「準備金跌穿紅線」影片前後說法不一，要看實際水位，不要只聽結論。"
            ),
        },
        {
            "title": "⑤ 誰在抽水？TGA（財政部帳戶）",
            "ids": ["wp_tga_tn", "wp_reserves_tn"],
            "axis": [0, 1],
            "summary": _note(
                "TGA 是美國財政部在 Fed 的存款戶。財政部發債收到的錢進 TGA，這筆錢就離開銀行體系；花錢時才再放回來。",
                "<b>TGA 上升 = 抽水</b>（準備金通常跟著下降），<b>TGA 下降 = 放水</b>。"
                "兩條線經常走反方向，這是最直接的人為流動性來源。",
                "TGA 10/29 為 1.04 兆與影片一致；但之後降到約 0.9 兆，等於把錢放回銀行體系，"
                "<b>這段期間沒有看到影片說的「持續抽水」</b>。財政部年底目標也沒有被下調（仍為 8,500 億）。"
            ),
        },
        {
            "title": "⑥ Fed 有沒有補水？Fed 持有的 T-bill",
            "ids": ["wp_fed_bills_bn", "wp_fed_bills_chg4w_bn"],
            "axis": [0, 1],
            "plot_lines": [("wp_fed_bills_chg4w_bn", [0])],
            "summary": _note(
                "Fed 買短期國庫券（T-bill）等於直接把錢注入銀行體系，這是「準備金管理購債（RMP）」的做法。",
                "左軸線<b>往上爬越快 = 補水越多</b>；走平 = 沒在補。右軸是<b>近 4 週變化（約等於每月增減）</b>，>0 = 補水、<0 = 縮表；影片說要每月買 300–500 億才算真正重啟，可直接對照右軸是否到 300–500。",
                "影片說「RMP 暫停、持有量停止增加」<b>不成立</b>：8/19 到 10/14 其實增加約 283 億美元，只是比之前慢。"
                "正確說法是「買債放慢」，不是「停止」。"
            ),
        },
        {
            "title": "⑦ 救急窗口有人用嗎？SRF 單日用量",
            "ids": ["wp_srf_usage_bn"],
            "summary": _note(
                "SRF 是 Fed 的緊急回購窗口，銀行拿美債去抵押就能借錢。用量大 = 市場真的借不到錢。",
                "平常幾乎是 0；出現<b>柱狀突刺（單日百億美元以上）</b>才算真正緊張。"
                "影片說單日 150–300 億才是止跌訊號。注意 2024-04 以前的數字包含其他隔夜操作，不是純 SRF。",
                "10/27 到 11/6 每天都小於 0.31 億，遠低於影片門檻。<b>這是反面證據</b>："
                "如果真的缺美元，應該有人去敲窗口；影片的解釋是銀行怕被貼上「缺錢」的標籤所以不去，但這一點沒有數據佐證。"
            ),
        },
        {
            "title": "⑧ 對沖基金押多大？槓桿基金美債期貨淨部位（基差交易代理）",
            "ids": ["wp_lev_net_2y", "wp_lev_net_5y", "wp_lev_net_10y"],
            "summary": _note(
                "「基差交易」是對沖基金買現貨美債、賣美債期貨，再靠回購借錢放大槓桿。這類部位在 CFTC 報告裡看起來就是期貨的大量淨空單。",
                "<b>淨空單越深（線越往下）= 槓桿堆得越高</b>，一旦借錢變貴或保證金被追繳，被迫平倉的力道就越大。"
                "週資料，約落後 3 天公布。",
                "這只是<b>代理指標</b>，不是基差部位本身，且影片的「6,000 億–1 兆」「槓桿 20–30 倍」本地資料對不上"
                "（Form PF 最大組約 19 倍）。傳導的中段（交易商怎麼收緊、基金怎麼砍倉）影片沒給數據，是整條邏輯最弱的一環。"
            ),
        },
        {
            "title": "⑨ 股金同跌那天：QQQ、黃金、美元的單日報酬",
            "ids": ["wp_qqq_ret", "wp_gld_ret", "wp_dxy_ret"],
            "axis": [0, 0, 1],
            "plot_lines": [("wp_qqq_ret", [0])],
            "summary": _note(
                "對照影片的主戰場：2026-10-30 股票、黃金同時重挫。若真是「美元荒」，美元通常會走強，因為大家都在搶美元。",
                "找<b>QQQ 與黃金同為大幅負值</b>的日子；再看美元指數（右軸）那天是漲還是跌。"
                "黃金下跌最合理的解釋通常是實質利率或美元走強，如果兩者都沒有，才輪到「被迫變現」的說法登場。",
                "10/30 QQQ −3.47%、GLD −3.47% 與影片相符，但<b>美元指數當天下跌 0.16%</b>，與「搶美元」相反，影片沒有解釋。"
                "此外，黃金兩因子（實質利率＋美元）只能解釋日變動約 15–18%，影片說的 80% 不成立。"
                "黃金殘差 −2.86σ 只在短視窗成立，視窗拉長後幾乎消失。"
            ),
        },
        {"custom_config": _gld_intraday},
        {"custom_config": _xau_intraday},
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
get_custom_config = _module.get_custom_config


def get_chart_config(chart_id_list):
    _ensure_derived()
    return _module.get_chart_config(chart_id_list)


def generate_chart_data(chart_id_entry, months=600):
    _ensure_derived()
    return _module.generate_chart_data(chart_id_entry, months)
