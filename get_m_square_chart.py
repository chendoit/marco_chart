import re
import pickle
from playwright.sync_api import sync_playwright
from loguru import logger


from datetime import datetime
import random

import os
import subprocess

from dotenv import load_dotenv
load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
]
# 數據儲存目錄
folder = os.getenv("DATA_DIR")  # 默認數據目錄
if not os.path.exists(folder):
    os.makedirs(folder)

logger.info(f"m平方 chart data is saved to {folder}")

def convert_chart_data(chart_data, chart_id, folder=folder):
    # 获取 chart title
    chart_key = f'c:{chart_id}'
    chart_info = chart_data['data'][chart_key]['info']
    chart_title = chart_info['name_sc']  # '美国-隔夜指数掉期[OIS]'

    # 获取 seriesConfigs
    series_configs = chart_info['chart_config']['seriesConfigs']

    # 获取 series 数据
    series_list = chart_data['data'][chart_key]['series']

    # 遍历 series 生成 pkl
    for idx, series_data in enumerate(series_list):
        if idx >= len(series_configs):
            break

        series_title = series_configs[idx]['name_tc']  # e.g., '1個月'
        full_title = f"{chart_title}{series_title}"

        # 转换数据格式
        series_parsed = [[datetime.strptime(date, '%Y-%m-%d'), float(value)] for date, value in series_data]

        series_dict = {
            'data': series_parsed,
            'title': full_title
        }

        series_filename = os.path.join(folder,  f'series_{chart_id}{idx}.pkl')
        with open(series_filename, 'wb') as f:
            pickle.dump(series_dict, f)
        logger.info(f'Saved: series_{chart_id}{idx}.pkl for {full_title}')

def save_response_data(response, chart_id):
    """Save response data to a pickle file and compress it to a 7z file."""
    if f'data/{chart_id}' in response.url:
        logger.info(f'{chart_id} Status {response.status}: {response.url}')
        try:
            # Parse the response JSON
            data = response.json()

            # Prepare paths for .pkl and .7z files
            # today = datetime.now().strftime('%Y_%m_%d')
            data_folder = 'data'
            history_folder = 'history'
            os.makedirs(data_folder, exist_ok=True)  # Ensure the data folder exists
            # os.makedirs(history_folder, exist_ok=True)  # Ensure the history folder exists

            # Save to pickle file in the data folder
            pkl_filename = os.path.join(data_folder, f'chart_{chart_id}.pkl')
            with open(pkl_filename, 'wb') as f:
                pickle.dump(data, f)

                # change from chart to series
                convert_chart_data(data, chart_id)
            # # Compress the pickle file using 7z
            # compressed_filename = f'{chart_id}_{today}.7z'
            # compressed_filepath = os.path.join(history_folder, compressed_filename)
            # subprocess.run([r'C:\Program Files\7-Zip\7z.exe', 'a', compressed_filepath, pkl_filename], check=True)
            #
            # logger.info(f'Compressed file saved: {compressed_filepath}')

            # Optional: Remove the original pickle file after compression
            # os.remove(pkl_filename)
            # logger.info(f'Removed original pickle file: {pkl_filename}')

        except Exception as e:
            logger.error(f"Error processing response data for {chart_id}: {e}")

def fetch_data_from_urls(urls):
    """Fetch data from a list of URLs and save them as pickle files."""
    with sync_playwright() as playwright:
        browser_args = ['--disable-blink-features=AutomationControlled']
        browser = playwright.chromium.launch(headless=False, args=browser_args)
        page = browser.new_page()

        # Load stealth.min.js or mimic stealth behavior with your custom JS
        page.add_init_script(path="stealth.min.js")  # You need to provide the path to your stealth.min.js
        page.set_viewport_size({'width': 1024, 'height': 768})

        for url in urls:
            try:
                # Extract chart ID from the URL using regex
                chart_id_match = re.search(r'\d+', url)
                if chart_id_match:
                    chart_id = chart_id_match.group()
                else:
                    logger.error(f"Invalid URL format: {url}")
                    continue

                # Pass the extracted chart ID to the response handler
                page.on('response', lambda response: save_response_data(response, chart_id))
                logger.info(f"Fetching data for URL: {url}")
                page.goto(url)
                page.wait_for_timeout(5000)  # Wait for data to load

            except Exception as e:
                logger.error(f"Error processing URL {url}: {e}")

        browser.close()



def load_chart_data(chart_id):
    """Load data from the pickle file."""
    file_path = os.path.join(folder, f"chart_{chart_id}.pkl")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File chart_{chart_id}.pkl not found in ./data")
    with open(file_path, 'rb') as f:
        return pickle.load(f)



url_list = [

    # series_1150440.pkl for 美国 - 隔夜指数掉期[OIS]1個月
    # series_1150441.pkl for 美国-隔夜指数掉期[OIS]3個月
    # series_1150442.pkl for 美国-隔夜指数掉期[OIS]6個月
    # series_1150443.pkl for 美国-隔夜指数掉期[OIS]1年
    # series_1150444.pkl for 美国-隔夜指数掉期[OIS]2年
    # series_1150445.pkl for 美国-隔夜指数掉期[OIS]10年
    # series_1150446.pkl for 美国-隔夜指数掉期[OIS]30年
    "https://www.macromicro.me/charts/115044/us-overnight-indexed-swaps",

    # series_712450.pkl 美国 - FedWatch预估利率美國 - FedWatch預估利率 - 上限
    # series_712451.pkl 美国 - FedWatch预估利率美國 - FedWatch預估利率 - 下限
    "https://www.macromicro.me/charts/71245/us-fedwatch-predicted-interest-rate",

    # 美國領先、同時指標年增率 vs NBER經濟衰退
    "https://www.macromicro.me/charts/56752/mei-guo-ling-xian-tong-shi-zhi-biao-nian-zeng-lyu-vs-NBER-jing-ji-shuai-tui",
]

def fetch_m_square_charts():
    fetch_data_from_urls(url_list)

if __name__ == "__main__":

    # 需要 特別版本的 playwright pip install playwright==1.43.0 太新的會有 http response status  = 403, 且查不出原因無法克服

    # url = "https://www.macromicro.me/charts/14921/us-dxy-us-2y-jp30y"
    # url = '"https://en.macromicro.me/charts/4376/crude-oil-cracking-spread-vs-wti"'
    #
    # fetch_data_from_url(url)

    # for url in url_list:
    fetch_data_from_urls(url_list)

    # chart_id = '115044'
