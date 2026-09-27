# -*- coding: utf-8 -*-
"""一次性: 只針對 series_1650.pkl 缺的日期打 CBOE daily page 補洞。

usage: venv/Scripts/python.exe _fill_pcr_gaps.py
"""
import datetime
import pickle
import random
import time
from pathlib import Path

import log_config  # noqa: F401
from loguru import logger
from get_cboe_pcr import _fetch_daily, _save_pkl, _load_pkl

START = datetime.date(2019, 10, 7)
END = datetime.date(2026, 9, 22)  # 昨天


def main():
    data = _load_pkl()
    existing = {pt[0].date() for pt in data.get("data", [])}
    missing = [
        START + datetime.timedelta(days=i)
        for i in range((END - START).days + 1)
        if (START + datetime.timedelta(days=i)) not in existing
    ]
    logger.info(f"Missing days: {len(missing)} (weekday {sum(1 for d in missing if d.weekday() < 5)})")

    new = 0
    for i, d in enumerate(missing):
        v = _fetch_daily(d)
        if v is not None:
            data["data"].append([datetime.datetime(d.year, d.month, d.day, 8, 0), v])
            new += 1
        if (i + 1) % 50 == 0:
            logger.info(f"Progress {i+1}/{len(missing)}, new={new}, at {d}")
            _save_pkl(data)  # 中途存檔, 防中斷全失
        time.sleep(random.uniform(0.3, 0.5))

    _save_pkl(data)
    logger.info(f"Done. new={new}, total={len(data['data'])}")


if __name__ == "__main__":
    main()
