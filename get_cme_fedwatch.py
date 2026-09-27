# -*- coding: utf-8 -*-
"""CME FedWatch 官方結算機率 — chart 77 的獨立備援資料源

背景：WN-2026-09-23-M2失敗19條-現況與提案.md「FedWatch 追加調查」。
目前 sid 484(升息機率)/1645(降息機率) 由 get_m_square_chart_api.py 的
fetch_chart_77() 供應(M² 自家 chart API,是主要來源，逐點跟舊 pkl 對過)。

本檔案完全獨立於 M²：用 CME 官方 30-Day Fed Funds Futures 結算價
(`cme-fedwatch` 套件, https://github.com/tjdwls101010/CME-FedWatch，
即時打 cmegroup.com 公開結算 API + FRED，不需瀏覽器/不依賴 M² 的
Cloudflare stk token) 每天累積一筆機率，供 chart 77 哪天掛掉時當備援
或比對用。**不寫 series_484/1645.pkl，不接進儀表板**，寫在獨立檔案
fedwatch_cme_hike.pkl / fedwatch_cme_cut.pkl。

hike/cut 定義沿用 chart 77 的口徑(見 get_m_square_chart_api.py 註解)：
  hike(升息) = 下次會議機率分布中，目標區間下緣 > 目前下緣 的機率加總
  cut(降息)  = 目標區間下緣 < 目前下緣 的機率加總
  (下緣 == 目前下緣 視為 hold，不計入兩者)

驗證(2026-09-27，見 WN 文件)：09-25 CME 官方結算 64.2/35.8，與 M² chart 77
同日值一致；09-18 值 57.6/42.4 與 CME 官網公布值一致。

套件版本需求：>= 0.2.0。0.1.x 的機率算法有 bug(連續兩個月都有 FOMC 時
label 會整個偏移 75bp)，安裝/升級時務必確認版本。
CME 免費結算 feed 只保留約 5 個營業日，所以只能「從今天起累積」，
補不回 08-19 之前的空窗(那段空窗已用 chart 77 解決，見 WN 文件)。
"""
import os
import re
import pickle
from datetime import date, datetime

from loguru import logger

import log_config  # noqa: F401  # [日誌規範] 統一由 log_config 設定，本檔禁止再呼叫 logger.add()

from cme_fedwatch import __version__ as CME_FEDWATCH_VERSION
from cme_fedwatch import get_probabilities

if tuple(int(x) for x in CME_FEDWATCH_VERSION.split(".")[:2]) < (0, 2):
    raise RuntimeError(
        f"cme-fedwatch {CME_FEDWATCH_VERSION} < 0.2.0：0.1.x 機率算法有 75bp 偏移 bug，"
        "請先 pip install -U cme-fedwatch"
    )

folder = os.getenv("DATA_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data"
)
if not os.path.exists(folder):
    os.makedirs(folder)

HIKE_FILE = "fedwatch_cme_hike.pkl"
CUT_FILE = "fedwatch_cme_cut.pkl"
HIKE_TITLE = "美國-FedWatch官方結算升息機率(CME備援,ex-M²)"
CUT_TITLE = "美國-FedWatch官方結算降息機率(CME備援,ex-M²)"

_RANGE_RE = re.compile(r"([\d.]+)%-([\d.]+)%")


def _range_lower(label: str) -> float:
    m = _RANGE_RE.match(label)
    if not m:
        raise ValueError(f"unexpected target range label: {label!r}")
    return float(m.group(1))


def _hike_cut(meeting: dict, current_target: str) -> tuple[float, float]:
    """依 chart 77 的口徑把機率分布拆成 hike/cut 兩個數字。"""
    cur_lower = _range_lower(current_target)
    hike = cut = 0.0
    for label, p in meeting["probabilities"].items():
        lo = _range_lower(label)
        if lo > cur_lower:
            hike += p
        elif lo < cur_lower:
            cut += p
    return round(hike, 1), round(cut, 1)


def _load(fname: str, title: str) -> dict:
    p = os.path.join(folder, fname)
    if os.path.exists(p):
        with open(p, "rb") as f:
            return pickle.load(f)
    return {"title": title, "data": []}


def _save(fname: str, data: dict):
    """merge 後排序覆寫；新點數掉到舊點數 50% 以下時拒寫(防呆，同 get_m_square_chart_api.py 慣例)。"""
    p = os.path.join(folder, fname)
    old_n = 0
    if os.path.exists(p):
        with open(p, "rb") as f:
            old_n = len(pickle.load(f).get("data", []))
    if old_n and len(data["data"]) < old_n * 0.5:
        raise RuntimeError(f"{fname}: new n={len(data['data'])} < 50% of old n={old_n}, skip write")
    data["data"] = sorted(data["data"], key=lambda x: x[0])
    with open(p, "wb") as f:
        pickle.dump(data, f)
    logger.info(f"{fname} saved: n={len(data['data'])}, last={data['data'][-1][0]:%Y-%m-%d}")


def fetch_cme_fedwatch_daily():
    """每日一筆：抓 CME 官方結算(cme-fedwatch)下次會議 hike/cut 機率，append 進兩個備援 pkl。
    用套件回傳的實際結算日(trade_date)當時間戳，而非 today()，
    避免假日/長週末連續好幾天重複記錄同一個結算日。
    """
    result = get_probabilities("next")
    if not result.get("meetings"):
        logger.warning("cme-fedwatch: no upcoming meeting returned, skip")
        return

    trade_date = date.fromisoformat(result["trade_date"])
    hike, cut = _hike_cut(result["meetings"][0], result["current_target"])
    dt = datetime(trade_date.year, trade_date.month, trade_date.day, 8, 0)

    hike_data = _load(HIKE_FILE, HIKE_TITLE)
    cut_data = _load(CUT_FILE, CUT_TITLE)
    existing_dates = {d.date() for d, _ in hike_data["data"]}

    if trade_date in existing_dates:
        logger.info(f"fedwatch_cme: {trade_date} already recorded, skip")
        return

    hike_data["data"].append([dt, hike])
    cut_data["data"].append([dt, cut])
    _save(HIKE_FILE, hike_data)
    _save(CUT_FILE, cut_data)
    logger.info(
        f"fedwatch_cme {trade_date}: hike={hike}% cut={cut}% "
        f"(meeting={result['meetings'][0]['date']}, target={result['current_target']}, "
        f"cme-fedwatch v{CME_FEDWATCH_VERSION})"
    )


JOBS = [
    ("CME FedWatch daily (backup for chart 77)", fetch_cme_fedwatch_daily),
]


def fetch_cme_fedwatch_main():
    """供 get_all_series_data.py 呼叫的入口。"""
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
        raise RuntimeError("cme-fedwatch fetch failures:\n" + "\n".join(failures))


if __name__ == "__main__":
    fetch_cme_fedwatch_daily()
