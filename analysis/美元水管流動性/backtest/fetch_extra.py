"""補回測需要、本地 data/ 沒有的 FRED 序列：IOER（2021-07 前的準備金利率）、WTREGEN（TGA 週）。
輸出 raw/<SERIES>.csv。用 .env 的 FED_API_KEY。"""
import os, sys, requests, pandas as pd
from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", "..", "..", ".env"))
KEY = os.environ["FED_API_KEY"]

for sid in sys.argv[1:] or ["IOER", "WTREGEN"]:
    r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                     params={"series_id": sid, "api_key": KEY, "file_type": "json"}, timeout=60)
    r.raise_for_status()
    obs = r.json()["observations"]
    s = pd.to_numeric(pd.Series({o["date"]: o["value"] for o in obs}), errors="coerce").dropna()
    s.rename_axis("date").rename(sid).to_csv(os.path.join(HERE, "raw", f"{sid}.csv"))
    print(sid, s.index[0], s.index[-1], len(s))
