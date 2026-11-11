# -*- coding: utf-8 -*-
"""CFTC TFF Futures Only 美債期貨（2Y/5Y/10Y）槓桿基金淨部位，給「美元水管流動性」頁 ⑧ 用。

來源：CFTC Public Reporting（Socrata）資料集 gpe5-46if，免 key，週資料（報告日週二）。
輸出：data/cftc_tff_lev_net_{2Y,5Y,10Y}.pkl，單位口（lev_long - lev_short），逐日期 merge 存檔。
（原本是 analysis/美元水管流動性/research/cftc-treasury/fetch.py 的一次性 CSV。）
"""
import os
import pickle
from datetime import datetime

import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 本檔「禁止」再呼叫 logger.add()（見 get_fiscal_data.py）。

DATA_DIR = os.getenv("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
CONTRACTS = {"2Y": "042601", "5Y": "044601", "10Y": "043602"}
START = "2018-01-01"


def _fetch_lev_net(code: str) -> list:
    params = {
        "$where": f"cftc_contract_market_code='{code}' AND futonly_or_combined='FutOnly' "
                  f"AND report_date_as_yyyy_mm_dd >= '{START}T00:00:00.000'",
        "$order": "report_date_as_yyyy_mm_dd ASC",
        "$limit": "50000",
    }
    r = requests.get(URL, params=params, headers={"User-Agent": "research-fetch/1.0"}, timeout=60)
    r.raise_for_status()
    out = []
    for x in r.json():
        lo, sh = x.get("lev_money_positions_long"), x.get("lev_money_positions_short")
        if lo in (None, "") or sh in (None, ""):
            continue
        d = datetime.strptime(x["report_date_as_yyyy_mm_dd"][:10], "%Y-%m-%d").replace(hour=8)
        out.append((d, float(round(float(lo)) - round(float(sh)))))
    if not out:
        raise RuntimeError(f"CFTC {code} 無資料")
    return out


def _save(name: str, obs: list):
    out_file = os.path.join(DATA_DIR, f"{name}.pkl")
    old = []
    if os.path.exists(out_file):
        try:
            with open(out_file, "rb") as f:
                old = pickle.load(f).get("data", [])
        except Exception:
            old = []
    merged = {d.date(): (d, v) for d, v in old}
    merged.update({d.date(): (d, v) for d, v in obs})
    assert not (set(d.date() for d, _ in old) - set(merged)), f"{name}: 資料倒退"
    rows = sorted(merged.values(), key=lambda x: x[0])
    with open(out_file, "wb") as f:
        pickle.dump({"title": name, "data": [[d, v] for d, v in rows]}, f)
    logger.info(f"Saved: {name}.pkl n={len(rows)} last={rows[-1][0]:%Y-%m-%d}")


def fetch_cftc_treasury():
    """供 get_all_series_data.py 呼叫的入口。任一合約失敗會彙整後 raise。"""
    failures = []
    for label, code in CONTRACTS.items():
        try:
            _save(f"cftc_tff_lev_net_{label}", _fetch_lev_net(code))
        except Exception as e:
            logger.error(f"Failed: CFTC TFF {label} — {e}")
            failures.append(f"{label}: {e}")
    if failures:
        raise RuntimeError("CFTC 美債期貨抓取失敗:\n" + "\n".join(failures))


if __name__ == "__main__":
    fetch_cftc_treasury()
