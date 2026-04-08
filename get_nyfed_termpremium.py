# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import os
import pickle
from datetime import datetime

import requests
import pandas as pd
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

DATA_DIR = os.getenv("DATA_DIR")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

ACM_XLS_URL = (
    "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/"
    "ACMTermPremium.xls"
)

ACM_SERIES = {
    "ACMTP02": "NY Fed ACM 2Y Term Premium",
    "ACMTP05": "NY Fed ACM 5Y Term Premium",
    "ACMTP10": "NY Fed ACM 10Y Term Premium",
}


def fetch_nyfed_acm():
    """Download NY Fed ACM Term Premium Excel and save selected maturities as pkl."""
    logger.info(f"Downloading ACM Term Premium: {ACM_XLS_URL}")
    resp = requests.get(ACM_XLS_URL, timeout=120)
    resp.raise_for_status()
    logger.info(f"Downloaded {len(resp.content)} bytes")

    tmp_path = os.path.join(DATA_DIR, "_acm_temp.xls")
    with open(tmp_path, "wb") as f:
        f.write(resp.content)

    try:
        df = pd.read_excel(tmp_path, sheet_name="ACM Daily")
        logger.info(f"ACM Daily: {len(df)} rows, {df['DATE'].iloc[0]} ~ {df['DATE'].iloc[-1]}")

        df["DATE"] = pd.to_datetime(df["DATE"], format="%d-%b-%Y")

        for col, title in ACM_SERIES.items():
            series_data = []
            for _, row in df.iterrows():
                val = row[col]
                if pd.notna(val):
                    dt = row["DATE"].to_pydatetime().replace(hour=8)
                    series_data.append([dt, float(val)])

            pkl_path = os.path.join(DATA_DIR, f"series_nyfed_{col.lower()}.pkl")
            with open(pkl_path, "wb") as f:
                pickle.dump({"title": title, "data": series_data}, f)
            logger.info(f"Saved {len(series_data)} records -> {pkl_path}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    fetch_nyfed_acm()
