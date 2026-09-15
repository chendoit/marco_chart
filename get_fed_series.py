# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import os
import pickle
import datetime
import requests
import pandas as pd
from pystlouisfed import FRED
from loguru import logger

# 配置日誌記錄
logger.add("./logs/{time:YYYY-MM-DD}.log")

from dotenv import load_dotenv
load_dotenv()


# 初始化 FRED API
FED_API_KEY = os.getenv('FED_API_KEY')
fred = FRED(api_key=FED_API_KEY)

# 數據儲存目錄
DATA_DIR = os.getenv("DATA_DIR")  # 默認數據目錄
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

logger.info(f"fed log is saved to {DATA_DIR}")


def _coerce_numeric(value):
    """NY Fed API 可能回傳 'NA' 字串，FRED 缺值為 '.'。"""
    if value is None or value in ('NA', 'N/A', '.', ''):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_and_save_fred_data(series_id):
    """
    從 FRED API 獲取數據並保存為與 STLFSI4 相同的數據結構。
    """
    try:
        # 獲取系列標題
        series_info = fred.series_search(search_text=series_id)
        title = series_info.iloc[0]['title']

        # 獲取系列數據
        data = fred.series_observations(series_id=series_id)

        # 格式化數據（按日期升序）
        formatted_data = []
        for index, row in data.iterrows():
            date = index.to_pydatetime().replace(hour=8)
            value = _coerce_numeric(row['value'])
            formatted_data.append([date, value])
        formatted_data.sort(key=lambda x: x[0])

        # 創建最終的數據結構
        result = {
            'title': title,
            'data': formatted_data
        }

        # 保存為 pickle 文件
        output_file = os.path.join(DATA_DIR, f'fed_{series_id}.pkl')
        with open(output_file, 'wb') as f:
            pickle.dump(result, f)

        logger.info(f"Data saved to {output_file}")

    except Exception as e:
        logger.error(f"Error fetching or saving FRED data for {series_id}: {e}")


def fetch_and_save_sofr_data(start_date, end_date):
    """
    從紐約聯儲 API 獲取 SOFR 數據，並根據不同類型保存為多個 pickle 文件。
    """
    URL = "https://markets.newyorkfed.org/api/rates/secured/all/search.json"
    PARAMS = {
        "startDate": start_date,
        "endDate": end_date
    }

    try:
        response = requests.get(URL, params=PARAMS)
        response.raise_for_status()  # 檢查HTTP錯誤
        data = response.json()

        # 初始化數據容器
        bgcr_data = {
            'percent1': [],
            'percent25': [],
            'percent75': [],
            'percent99': [],
            'rate': [],
            'volume': []
        }
        tgcr_data = {
            'percent1': [],
            'percent25': [],
            'percent75': [],
            'percent99': [],
            'rate': [],
            'volume': []
        }
        sofr_data = {
            'percent1': [],
            'percent25': [],
            'percent75': [],
            'percent99': [],
            'rate': [],
            'volume': []
        }
        sofrai_data = []

        # 處理 rate 和 volume 數據
        for entry in data['refRates']:
            entry_type = entry["type"]
            entry_date = datetime.datetime.strptime(entry["effectiveDate"], "%Y-%m-%d").replace(hour=8)

            if entry_type == "BGCR":
                bgcr_data['percent1'].append([entry_date, _coerce_numeric(entry.get("percentPercentile1"))])
                bgcr_data['percent25'].append([entry_date, _coerce_numeric(entry.get("percentPercentile25"))])
                bgcr_data['percent75'].append([entry_date, _coerce_numeric(entry.get("percentPercentile75"))])
                bgcr_data['percent99'].append([entry_date, _coerce_numeric(entry.get("percentPercentile99"))])
                bgcr_data['rate'].append([entry_date, _coerce_numeric(entry.get("percentRate"))])
                bgcr_data['volume'].append([entry_date, _coerce_numeric(entry.get("volumeInBillions"))])

            elif entry_type == "TGCR":
                tgcr_data['percent1'].append([entry_date, _coerce_numeric(entry.get("percentPercentile1"))])
                tgcr_data['percent25'].append([entry_date, _coerce_numeric(entry.get("percentPercentile25"))])
                tgcr_data['percent75'].append([entry_date, _coerce_numeric(entry.get("percentPercentile75"))])
                tgcr_data['percent99'].append([entry_date, _coerce_numeric(entry.get("percentPercentile99"))])
                tgcr_data['rate'].append([entry_date, _coerce_numeric(entry.get("percentRate"))])
                tgcr_data['volume'].append([entry_date, _coerce_numeric(entry.get("volumeInBillions"))])

            elif entry_type == "SOFR":
                sofr_data['percent1'].append([entry_date, _coerce_numeric(entry.get("percentPercentile1"))])
                sofr_data['percent25'].append([entry_date, _coerce_numeric(entry.get("percentPercentile25"))])
                sofr_data['percent75'].append([entry_date, _coerce_numeric(entry.get("percentPercentile75"))])
                sofr_data['percent99'].append([entry_date, _coerce_numeric(entry.get("percentPercentile99"))])
                sofr_data['rate'].append([entry_date, _coerce_numeric(entry.get("percentRate"))])
                sofr_data['volume'].append([entry_date, _coerce_numeric(entry.get("volumeInBillions"))])

            elif entry_type == "SOFRAI":
                sofrai_data.append([entry_date, _coerce_numeric(entry.get("index"))])

        # 保存 BGCR 數據
        for key, values in bgcr_data.items():
            if values:
                result = {'title': f'BGCR {key.capitalize()}', 'data': values}
                save_to_pickle(result, f'bgcr_{key}.pkl')

        # 保存 TGCR 數據
        for key, values in tgcr_data.items():
            if values:
                result = {
                    'title': f'TGCR {key.capitalize()}',
                    'data': values
                }
                save_to_pickle(result, f'tgcr_{key}.pkl')

        # 保存 SOFR 數據
        for key, values in sofr_data.items():
            if values:
                result = {
                    'title': f'SOFR {key.capitalize()}',
                    'data': values
                }
                save_to_pickle(result, f'sofr_{key}.pkl')

        # 保存 SOFRAI 數據
        if sofrai_data:
            result = {
                'title': 'SOFRAI Index',
                'data': sofrai_data
            }
            save_to_pickle(result, 'sofrai_index.pkl')

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SOFR data: {e}")
    except Exception as e:
        logger.error(f"Error processing or saving SOFR data: {e}")


def fetch_sofr_data():
    """Orchestrator 用的無參數版本，自動抓取 2021-08-05 到今天的 SOFR 資料。"""
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    fetch_and_save_sofr_data("2021-08-05", end_date)


def fetch_fed_liquidity_reference_rates():
    """IORB、ON RRP、Fed Funds 等 FRED 系列，供 SOFR 流動性圖表使用。"""
    for series_id in ("IORB", "RRPONTSYAWARD", "RRPONTSYD", "DFF"):
        fetch_and_save_fred_data(series_id)


def fetch_fed_treasury_yields():
    """美國公債殖利率曲線（FRED DGS 系列）。"""
    for series_id in ("DGS1MO", "DGS1", "DGS2", "DGS10", "DGS20", "DGS30"):
        fetch_and_save_fred_data(series_id)


def _sort_series_data(values):
    """NY Fed API 回傳順序不固定，存檔前統一按日期升序。"""
    return sorted(values, key=lambda x: x[0])


def save_to_pickle(data, filename):
    """
    將數據保存為 pickle 文件。
    """
    if data.get('data'):
        data = {**data, 'data': _sort_series_data(data['data'])}
    output_file = os.path.join(DATA_DIR, filename)
    with open(output_file, 'wb') as f:
        pickle.dump(data, f)

    logger.info(f"Data saved to {filename}")


if __name__ == "__main__":
    # 示例使用
    fetch_and_save_sofr_data("2021-08-05", "2025-01-31")
    fetch_and_save_fred_data('STLFSI4')  # 保存 FRED 數據
    fetch_and_save_fred_data('NFCI')  # 保存 FRED 數據