# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import re
import pickle
from playwright.sync_api import sync_playwright
from loguru import logger


from datetime import datetime
import random

import os
import subprocess

from dotenv import load_dotenv

from macromicro_login import ensure_macromicro_session
from line_notify import send_line_notification

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
        series_parsed = [[datetime.strptime(date, '%Y-%m-%d').replace(hour=8), float(value)] for date, value in series_data]

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


def chart_label_from_url(url: str) -> str:
    """從 chart URL 抽出可讀標的（id + slug）；無法解析時截斷原 URL。"""
    match = re.search(r"/charts/(\d+)/([\w-]+)", url)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    match_id = re.search(r"/charts/(\d+)", url)
    if match_id:
        return match_id.group(1)
    return url if len(url) <= 160 else url[:157] + "..."


def _chart_pkl_path(chart_id: str) -> str:
    return os.path.join("data", f"chart_{chart_id}.pkl")


def process_chart_url(page, url) -> bool:
    """載入單一 chart 頁並透過 response 攔截存檔。成功時 data/chart_{id}.pkl 存在且非空。"""
    mid = re.search(r"/charts/(\d+)", url)
    if not mid:
        logger.error(f"Invalid URL format (no chart id): {url}")
        return False
    chart_id = mid.group(1)
    handler = lambda response, cid=chart_id: save_response_data(response, cid)
    page.on("response", handler)
    try:
        logger.info(f"Fetching data for URL: {url}")
        page.goto(url)
        page.wait_for_timeout(5000)
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        return False
    finally:
        page.remove_listener("response", handler)

    pkl_path = _chart_pkl_path(chart_id)
    if os.path.isfile(pkl_path) and os.path.getsize(pkl_path) > 0:
        return True
    logger.warning(f"Chart file missing or empty: {pkl_path}")
    return False


def fetch_data_from_urls(urls):
    """Fetch data from a list of URLs and save them as pickle files."""
    with sync_playwright() as playwright:
        browser_args = ['--disable-blink-features=AutomationControlled']
        browser = playwright.chromium.launch(headless=False, args=browser_args)
        page = browser.new_page()

        # Load stealth.min.js or mimic stealth behavior with your custom JS
        page.add_init_script(path="stealth.min.js")  # You need to provide the path to your stealth.min.js
        page.set_viewport_size({'width': 1024, 'height': 768})

        ensure_macromicro_session(page, "get_m_square_chart.py")

        failures: list[str] = []
        for url in urls:
            success = process_chart_url(page, url)
            if not success:
                logger.warning(f"Retrying URL {url} with a new browser instance...")
                browser.close()
                browser = playwright.chromium.launch(headless=False, args=browser_args)
                page = browser.new_page()
                page.add_init_script(path="stealth.min.js")
                page.set_viewport_size({'width': 1024, 'height': 768})
                ensure_macromicro_session(page, "get_m_square_chart.py")
                success = process_chart_url(page, url)
                if not success:
                    logger.error(f"Failed to process URL {url} after retry.")
                    label = chart_label_from_url(url)
                    failures.append(f"{label}\n{url}")

        browser.close()

        if failures:
            body = "\n\n".join(failures)
            max_len = 4500
            if len(body) > max_len:
                body = body[: max_len - 30] + f"\n...(共 {len(failures)} 筆，已截斷)"
            send_line_notification(f"[M² chart 抓取失敗 {len(failures)} 筆]\n{body}")



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
