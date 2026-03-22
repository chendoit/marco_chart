# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
from pycot.reports import CommitmentsOfTraders #pip install pycot-reports, pydantic-settings
import pandas as pd
import datetime
import pickle
import re
import os
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from dotenv import load_dotenv
load_dotenv()

# 配置日誌記錄
def setup_data_folder():
    folder = os.getenv("DATA_DIR")
    if not os.path.exists(folder):
        os.makedirs(folder)

    logger.info(f"cftc log is saved to {folder}")
    return folder

data_folder = setup_data_folder()
logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

def get_exchange_code(report_name):
    """從報告名稱中提取交易所代碼"""
    exchange_mapping = {
        'CHICAGO MERCANTILE EXCHANGE': 'cme',
        'INTERNATIONAL MONETARY MARKET': 'imm',
        'COMMODITY EXCHANGE INC': 'comex',
        'ICE EUROPE': 'ice',
        'ICE FUTURES EUROPE': 'ice',
        'NEW YORK BOARD OF TRADE': 'nybot',
        'NEW YORK COTTON EXCHANGE': 'nyce',
        'NEW YORK MERCANTILE EXCHANGE': 'nyme',
        'NEW YORK FUTURES EXCHANGE': 'nyfe'
    }

    # 從報告名稱中提取交易所部分（最後一個破折號後的部分）
    parts = report_name.split('-')
    if len(parts) > 1:
        exchange = parts[-1].strip()
        return exchange_mapping.get(exchange, 'unknown')
    return 'unknown'


def clean_column_name(column_name):
    """清理欄位名稱，移除特殊字元並轉換格式"""
    name = column_name.lower()
    replacements = {
        '% of': 'pct_of',
        ', ': '_',
        ',': '_',
        '-': '_',
        ' ': '_',
        '.': '',
        '(': '',
        ')': '',
        '/': '_',
        '\\': '_',
        '%': 'pct'
    }
    for old, new in replacements.items():
        name = name.replace(old, new)

    name = re.sub('_+', '_', name)
    name = name.strip('_')
    return name


def get_prefix_from_name(report_name):
    """從報告名稱生成檔案前綴"""
    # 提取商品名稱（第一個破折號之前的部分）
    product_name = report_name.split('-')[0].strip()

    name_mapping = {
        'JAPANESE YEN': 'jpy',
        'U.S. DOLLAR-EURO': 'eur_usd',
        'EURO FX': 'eur',
        'BRITISH POUND': 'gbp',
        'SWISS FRANC': 'chf',
        'CANADIAN DOLLAR': 'cad',
        'AUSTRALIAN DOLLAR': 'aud',
        'NEW ZEALAND DOLLAR': 'nzd',
        '3-MO. EUROYEN': 'eur_jpy_3m',
        '3-MONTH EURODOLLARS': 'eur_usd_3m',
        'CRUDE OIL, LIGHT SWEET': 'cl',
        'EURODOLLARS': 'ed'
    }

    # 尋找匹配的前綴
    for key, value in name_mapping.items():
        if key in product_name.upper():
            return value

    # 如果沒有匹配到，清理名稱並使用前三個字母
    clean_name = clean_column_name(product_name)
    return clean_name[:3]


class COTReportCache:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.max_age_hours = 4
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_filename(self, report_name):
        safe_name = clean_column_name(report_name)
        return os.path.join(self.cache_dir, f'{safe_name}_cache.pkl')

    def _is_cache_fresh(self, cache_file):
        if not os.path.exists(cache_file):
            return False
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        age = datetime.now() - file_time
        return age.total_seconds() < (self.max_age_hours * 3600)

    def get_report(self, report_name):
        cache_file = self._get_cache_filename(report_name)

        if self._is_cache_fresh(cache_file):
            logger.info(f"Using cached report data for {report_name}...") # 使用logger
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Error reading cache: {e}") # 使用logger
                return self._fetch_and_cache_report(report_name, cache_file)
        else:
            return self._fetch_and_cache_report(report_name, cache_file)

    def _fetch_and_cache_report(self, report_name, cache_file):
        logger.info(f"Fetching fresh report data for {report_name}...") # 使用logger
        cot = CommitmentsOfTraders("legacy_fut")
        report_data = cot.report(report_name)

        logger.info("Caching report data...") # 使用logger
        with open(cache_file, 'wb') as f:
            pickle.dump(report_data, f)

        return report_data


def convert_and_save_column(df, column_name, output_dir, prefix, exchange_code):
    """將單一欄位轉換並儲存成pickle"""
    os.makedirs(output_dir, exist_ok=True)

    data = [[datetime.combine(date, datetime.min.time()).replace(hour=8), float(value)]
            for date, value in zip(df.index, df[column_name])]

    pickle_data = {
        'title': column_name,
        'data': data
    }

    # 使用清理後的欄位名稱，並加入交易所代碼
    clean_name = clean_column_name(column_name)
    filename = f"{prefix}_{exchange_code}_{clean_name}.pkl"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'wb') as f:
        pickle.dump(pickle_data, f)

    return filepath


def get_cot_data(report_name, base_dir=None):
    """主要處理函數"""
    if base_dir is None:
        base_dir = os.getenv("DATA_DIR") # 優先使用環境變數

    data_dir = base_dir # change
    cache_dir = os.path.join(base_dir, "cache")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    report_cache = COTReportCache(cache_dir)
    logger.info(f"Processing report: {report_name}") # 使用logger
    df = report_cache.get_report(report_name)

    prefix = get_prefix_from_name(report_name)
    exchange_code = get_exchange_code(report_name)

    results = {}
    for column in df.columns:
        if column != 'Contract Name':
            try:
                filepath = convert_and_save_column(df, column, data_dir, prefix, exchange_code)
                results[column] = filepath
                logger.info(f"Saved {column} to {filepath}") # 使用logger
            except Exception as e:
                logger.error(f"Error processing {column}: {str(e)}") # 使用logger

    return results

def fetch_cftc_data():

    reports = [
        "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
        "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "CRUDE OIL, LIGHT 'SWEET' - NEW YORK MERCANTILE EXCHANGE",
        "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"
        # "CRUDE OIL, LIGHT SWEET - ICE FUTURES EUROPE"
    ]

    for report in reports:
        logger.info(f"Processing: {report}") # 使用logger
        results = get_cot_data(report)
        # 顯示部分結果作為範例
        for original_name, filepath in list(results.items())[:1]:
            logger.info(f"Sample output: {os.path.basename(filepath)}") # 使用logger

# 使用範例
if __name__ == "__main__":
    # 測試幾個不同的報告
    reports = [
        "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
        "EURO FX - CHICAGO MERCANTILE EXCHANGE",
        "CRUDE OIL, LIGHT 'SWEET' - NEW YORK MERCANTILE EXCHANGE",
        "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE"
        # "CRUDE OIL, LIGHT SWEET - ICE FUTURES EUROPE"
    ]

    for report in reports:
        logger.info(f"Processing: {report}") # 使用logger
        results = get_cot_data(report)
        # 顯示部分結果作為範例
        for original_name, filepath in list(results.items())[:1]:
            logger.info(f"Sample output: {os.path.basename(filepath)}") # 使用logger