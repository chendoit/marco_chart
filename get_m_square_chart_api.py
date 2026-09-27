# -*- coding: utf-8 -*-
# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 取代 get_m_square_chart.py(Playwright + Google OAuth 攔截)與
# get_m_square_series.py 中的 sid 20508 / 32377 兩條。
# 資料源:MacroMicro 自家 chart data API(/charts/data/{chart_id}),
# 兩段式 curl_cffi token(先 GET 圖表頁拿 stk token,再帶 Bearer 打 API)。
# 參考程式(唯讀,勿改):
#   C:/code/2026-09-11-fincept-terminal/migration/reference_fetchers/02_macromicro_chart_api.py
# 覆蓋範圍(13 條 pkl):
#   chart 115044 → series_1150440~1150446(US OIS 1M/3M/6M/1Y/2Y/10Y/30Y)
#   chart 71245  → series_712450 / 712451(FedWatch 預估利率上/下限)
#   chart 56752  → series_567520 / 567521(CB LEI / CEI yoy vs NBER)
#   chart 46503 series[1] → series_20508(全球 PMI 年變動擴散指數)
#   chart 102471 series[0] → series_32377(JPY VIX 日圓隱含波動率)
#   chart 77 series[0]/[1] → series_484 / 1645(FedWatch 下次會議升息/降息機率)
#   chart 35720 series[0] → series_17586(S&P500 EPS,含 M² 的未來預估)
import os
import re
import pickle
from datetime import datetime

from loguru import logger
from curl_cffi import requests

import log_config  # noqa: F401  # [日誌規範] 統一由 log_config 設定,本檔禁止再呼叫 logger.add()

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

# title 對照表:沿用舊 pkl 顯示名稱(儀表板圖例/軸標題用),不要留空
TITLE_MAP = {
    1150440: "美国-隔夜指数掉期[OIS]1個月",
    1150441: "美国-隔夜指数掉期[OIS]3個月",
    1150442: "美国-隔夜指数掉期[OIS]6個月",
    1150443: "美国-隔夜指数掉期[OIS]1年",
    1150444: "美国-隔夜指数掉期[OIS]2年",
    1150445: "美国-隔夜指数掉期[OIS]10年",
    1150446: "美国-隔夜指数掉期[OIS]30年",
    712450: "美国-FedWatch预估利率美國-FedWatch預估利率-上限",
    712451: "美国-FedWatch预估利率美國-FedWatch預估利率-下限",
    567520: "美國領先、同時指標年增率 vs NBER經濟衰退美國-經濟諮商局-領先指標 (SA,yoy)",
    567521: "美國領先、同時指標年增率 vs NBER經濟衰退美國-經濟諮商局-同時指標 (SA,yoy)",
    20508: "global-pmi-leading-yoy-diffusion",
    32377: "jpy-vix",
    484: "probability-fed-rate",
    1645: "probability-fed-rate-decrease",
    17586: "sp500-eps",
}

STK_RE = re.compile(r"stk[\x22\x27\s]*[:=][\x22\x27\s]*[\x22\x27]([^\x22\x27]+)")


def _fetch_chart_series(chart_id, page_slug, impersonate="chrome124"):
    """通用兩段式:GET 圖表頁拿 stk token → GET /charts/data/{chart_id} 帶 Bearer。
    回傳 payload['data'][f'c:{chart_id}']['series'](list of list)。"""
    s = requests.Session(impersonate=impersonate)  # 需 curl_cffi 繞 Cloudflare
    base = "https://en.macromicro.me"
    page_url = f"{base}/charts/{chart_id}/{page_slug}"
    s.get(base + "/", timeout=60)  # 先暖機拿 cookie
    r1 = s.get(page_url, timeout=60)
    r1.raise_for_status()
    m = STK_RE.search(r1.text)
    if not m:
        raise RuntimeError(f"chart {chart_id}: stk token not found (Cloudflare challenge?)")
    headers = {
        "Authorization": "Bearer " + m.group(1),
        "Referer": page_url,
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    }
    r2 = s.get(f"{base}/charts/data/{chart_id}", headers=headers, timeout=60)
    r2.raise_for_status()
    payload = r2.json()
    if payload.get("success") != 1:
        raise RuntimeError(f"chart {chart_id}: MacroMicro non-success: {payload!r}")
    return payload["data"][f"c:{chart_id}"]["series"]


def _save_series(sid, obs):
    """寫出 {'title', 'data': [[datetime(08:00), float], ...]} 格式 pkl,同舊格式。
    防呆:新點數少於既有 pkl 的一半時不覆寫(避免 API 異常清空歷史)。"""
    out_file = os.path.join(folder, f"series_{sid}.pkl")
    old = None
    if os.path.exists(out_file):
        with open(out_file, "rb") as f:
            old = pickle.load(f)
    old_n = len(old.get("data", [])) if isinstance(old, dict) else 0
    if old and len(obs) < old_n * 0.5:
        raise RuntimeError(
            f"series_{sid}: new data n={len(obs)} < 50% of existing n={old_n}, skip write"
        )
    data = {"title": TITLE_MAP.get(sid, str(sid)), "data": [[d, v] for d, v in obs]}
    with open(out_file, "wb") as f:
        pickle.dump(data, f)
    logger.info(
        f"Saved: series_{sid}.pkl n={len(obs)} last={obs[-1][0]:%Y-%m-%d} (old n={old_n})"
    )


# ============================================================================
# chart 115044 US OIS 7 天期 → series_1150440~1150446  [ok]
# ============================================================================
def fetch_chart_115044():
    """series[0..6] = 1M/3M/6M/1Y/2Y/10Y/30Y,pkl sid = 1150440..1150446。"""
    series = _fetch_chart_series(115044, "us-overnight-indexed-swaps")
    for idx, pts in enumerate(series[:7]):
        obs = []
        for d, v in pts:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=8)
            obs.append((dt, float(v)))
        _save_series(1150440 + idx, obs)


# ============================================================================
# chart 71245 FedWatch 預估利率上/下限 → series_712450 / 712451  [ok]
# ============================================================================
def fetch_chart_71245():
    """series[0](上限)/series[1](下限),日期 = FOMC 會議日 08:00。"""
    series = _fetch_chart_series(71245, "us-fedwatch-predicted-interest-rate")
    for idx, sid in [(0, 712450), (1, 712451)]:
        obs = []
        for d, v in series[idx]:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=8)
            obs.append((dt, float(v)))
        _save_series(sid, obs)


# ============================================================================
# chart 56752 CB LEI/CEI 年增(vs NBER 衰退) → series_567520 / 567521  [ok]
# ============================================================================
def fetch_chart_56752():
    """series[0](LEI yoy)/series[1](CEI yoy),月頻,值不捨入以對齊舊 pkl 全精度。"""
    series = _fetch_chart_series(
        56752,
        "mei-guo-ling-xian-tong-shi-zhi-biao-nian-zeng-lyu-vs-NBER-jing-ji-shuai-tui",
    )
    for idx, sid in [(0, 567520), (1, 567521)]:
        obs = []
        for d, v in series[idx]:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(day=1, hour=8)
            obs.append((dt, float(v)))
        _save_series(sid, obs)


# ============================================================================
# chart 46503 series[1] 全球 PMI 年變動擴散指數 → series_20508  [ok]
# ============================================================================
def fetch_series_20508():
    """series[0] = PMI Diffusion Index(>=50 占比);series[1] = PMI YoY Diffusion Index ← sid 20508。"""
    series = _fetch_chart_series(46503, "pmi-diffusion-index")
    obs = []
    for dt_str, v in series[1]:
        y, mo = int(dt_str[:4]), int(dt_str[5:7])
        obs.append((datetime(y, mo, 1, 8, 0), round(float(v), 4)))
    _save_series(20508, obs)


# ============================================================================
# chart 102471 series[0] 日圓隱含波動率(JPY VIX) → series_32377  [ok]
# ============================================================================
def fetch_series_32377():
    """series[0] = JPY Implied Volatility(左軸),series[1] = USD/JPY(右軸)。
    舊 Playwright series 抓取只存到 2006(201 點),此 API 有全歷史(~8000 點)。
    ⚠️ 歷史變長會使 calc_pctrank 全條重算。"""
    series = _fetch_chart_series(102471, "jpy-vix", impersonate="chrome")
    obs = []
    for d, v in series[0]:
        dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=8)
        obs.append((dt, float(v)))
    _save_series(32377, obs)


# ============================================================================
# chart 77 FedWatch 升/降息機率 → series_484 / 1645  [ok]
# ============================================================================
def fetch_chart_77():
    """series[0] = 下次 FOMC 升息機率(%) ← sid 484;series[1] = 降息機率(%) ← sid 1645。
    日頻,2016-07-05 起;與舊 pkl 重疊的 81/81 點全等(2026-09-27 驗證)。
    舊 series_484 有 5 點早於 chart 起始日(2015-11~2016-06),合併時保留。"""
    series = _fetch_chart_series(77, "probability-fed-rate-hike")
    for idx, sid in [(0, 484), (1, 1645)]:
        obs = []
        for d, v in series[idx]:
            dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=8)
            obs.append((dt, float(v)))
        out_file = os.path.join(folder, f"series_{sid}.pkl")
        if os.path.exists(out_file):
            with open(out_file, "rb") as f:
                old = pickle.load(f)
            obs = [(d, v) for d, v in old["data"] if d < obs[0][0]] + obs
        _save_series(sid, obs)


# ============================================================================
# chart 35720 series[0] S&P500 EPS → series_17586  [stale]
# ============================================================================
def fetch_series_17586():
    """series[0] = S&P 500 EPS(季,2008Q1 起,含到 2027Q4 的預估);series[1] = YoY;series[2] = 指數。
    ⚠️ S&P DJI 已停發 EPS 檔,M² 自 2025Q1 起仍是舊的 S&P 預估值(非實際值),
    2008Q1~2024Q4 與 S&P 官方逐點一致(2026-09-27 驗證)。
    持續更新的替代序列見 get_official_xlsx.py 的 factset_SP500EPS。"""
    series = _fetch_chart_series(35720, "sp500-eps")
    obs = []
    for d, v in series[0]:
        dt = datetime.strptime(d, "%Y-%m-%d").replace(hour=8)
        obs.append((dt, float(v)))
    _save_series(17586, obs)


JOBS = [
    ("chart 115044 US OIS (7 series)", fetch_chart_115044),
    ("chart 71245 FedWatch (2 series)", fetch_chart_71245),
    ("chart 56752 CB LEI/CEI (2 series)", fetch_chart_56752),
    ("series 20508 global PMI diffusion", fetch_series_20508),
    ("series 32377 JPY VIX", fetch_series_32377),
    ("chart 77 FedWatch hike/cut probability (2 series)", fetch_chart_77),
    ("series 17586 S&P500 EPS", fetch_series_17586),
]


def fetch_m_square_chart_api():
    """供 get_all_series_data.py 呼叫的入口。任一 chart 失敗會彙整後 raise,
    交由 orchestrator 記入 error_history(不再像舊腳本吞錯)。"""
    failures = []
    for name, fn in JOBS:
        try:
            logger.info(f"Starting: {name}")
            fn()
            logger.info(f"Completed: {name}")
        except Exception as e:
            logger.error(f"Failed: {name} — {e}")
            failures.append(f"{name}: {e}")
    if failures:
        raise RuntimeError(
            "M2 chart API 抓取失敗 %d 項:\n%s" % (len(failures), "\n".join(failures))
        )


if __name__ == "__main__":
    fetch_m_square_chart_api()
