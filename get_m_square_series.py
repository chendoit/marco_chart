# pip install playwright==1.43.0
# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import re
import pickle
from playwright.sync_api import sync_playwright
from loguru import logger

from datetime import datetime
import base64
import json
import os

from dotenv import load_dotenv

from google_session.auth import create_macromicro_browser_context
from line_notify import send_line_notification

load_dotenv()

import log_config  # noqa: F401
# [日誌規範] 日期檔日誌已集中設定於 log_config.py，本檔「禁止」再呼叫 logger.add()，
# 否則多個 sink 指向同一 log 檔，每筆訊息會重複寫入 N 次（2026-09 已踩過此坑）。

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
]

def save_to_pickle(data, filename):
    """Save data to a pickle file."""
    with open(filename, "wb") as f:
        pickle.dump(data, f)
    logger.info(f"Data saved to {filename}")

import re
import base64
import json
from datetime import datetime, timedelta



def extract_data_from_script(html):
    """Extract and decode base64 data from <script> tags."""
    # Use regex to parse HTML and extract <script> tags
    script_regex = r"<script[^>]*>(.*?)</script>"
    matches = re.findall(script_regex, html, re.DOTALL)

    # Look for specific script containing "isViewable"
    for match in matches:
        if "isViewable" in match:
            logger.info("Target script found, extracting data...")

            # Extract the base64-encoded data using regex
            base64_regex = r'JSON\.parse\(atob\(\"(.*?)\"\)\)}]}\)}setTimeout'
            base64_match = re.search(base64_regex, match)

            if base64_match:
                base64_data = base64_match.group(1)
                logger.info(f"Extracted base64 data: {base64_data[:50]}...")

                # Decode the base64-encoded string
                decoded_bytes = base64.b64decode(base64_data)
                decoded_string = decoded_bytes.decode('utf-8')
                data = json.loads(decoded_string)

                results = []
                for item in data:
                    try:
                        timestamp = item[0] / 1000  # Convert to seconds
                        if timestamp >= 0:
                            # Use normal datetime conversion for positive timestamps
                            datetime_object = datetime.fromtimestamp(timestamp)
                        else:
                            # Handle negative timestamps manually
                            epoch = datetime(1970, 1, 1)
                            datetime_object = (epoch + timedelta(seconds=timestamp)).replace(hour=8)

                        results.append([datetime_object, item[1]])
                    except Exception as e:
                        logger.error(f"Error processing item {item}: {e}")
                        # Option to skip or handle errors differently
                        continue  # Skip this item and move on
                return results

    logger.warning("No target script or base64 data found.")
    return None


def series_label_from_url(url: str) -> str:
    """從 series URL 抽出可讀標的（id + slug）；無法解析時截斷原 URL。"""
    match = re.search(r"/series/(\d+)/([\w-]+)", url)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return url if len(url) <= 160 else url[:157] + "..."


def process_url(page, url, output_dir):
    """Process a single URL and save the extracted data."""
    try:
        logger.info(f"Fetching data for URL: {url}")
        page.goto(url)
        page.wait_for_timeout(3000)  # Wait for data to load

        # Retrieve the entire HTML content
        html = page.content()

        # Extract and process data
        data = extract_data_from_script(html)
        if data:
            match = re.search(r'/series/(\d+)/([\w-]+)', url)
            if match:
                series_id = match.group(1)  # 提取 series_id
                title = match.group(2)  # 提取 title
                print(f"series_id: {series_id}, title: {title}")

                # 假設的資料與輸出路徑
                os.makedirs(output_dir, exist_ok=True)  # 確保目錄存在
                output_file = os.path.join(output_dir, f"series_{series_id}.pkl")

                # 準備要保存的資料
                pickle_data = {'title': title, 'data': data}
                save_to_pickle(pickle_data, output_file)
                print(f"Data saved to {output_file}")
                return True
            logger.warning(f"URL format does not match: {url}")
            return False
        logger.warning(f"No data extracted from URL: {url}")
        return False

    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        return False


def fetch_data_from_urls(urls, output_dir=r'.\data'):
    """Fetch data from a list of URLs and save each processed data to individual files."""
    os.makedirs(output_dir, exist_ok=True)  # Ensure output directory exists

    with sync_playwright() as playwright:
        browser, context, page = create_macromicro_browser_context(
            playwright, headless=False, prefer_cached=True
        )
        page.add_init_script(path="stealth.min.js")
        page.set_viewport_size({"width": 1024, "height": 768})

        failures: list[str] = []
        for url in urls:
            success = process_url(page, url, output_dir)
            if not success:
                logger.warning(f"Retrying URL {url} with a new browser instance...")
                context.close()
                browser.close()
                browser, context, page = create_macromicro_browser_context(
                    playwright, headless=False, prefer_cached=True
                )
                page.add_init_script(path="stealth.min.js")
                page.set_viewport_size({"width": 1024, "height": 768})
                success = process_url(page, url, output_dir)
                if not success:
                    logger.error(f"Failed to process URL {url} after retry.")
                    label = series_label_from_url(url)
                    failures.append(f"{label}\n{url}")

        context.close()
        browser.close()

        if failures:
            body = "\n\n".join(failures)
            max_len = 4500
            if len(body) > max_len:
                body = body[: max_len - 30] + f"\n...(共 {len(failures)} 筆，已截斷)"
            send_line_notification(f"[M² series 抓取失敗 {len(failures)} 筆]\n{body}")


url_list = [
    # [2026-09-16] sid 20508、32377 已改由 get_m_square_chart_api.py(M2 chart API, curl_cffi)抓取,自此清單移除
    # [2026-09-22] sid 2 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/2/sp500", # S&P500

    # 原油
    "https://www.macromicro.me/series/4934/crude-oil-cracking-spread",
    # [2026-09-22] sid 486 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/486/crude-oil-futures",
    "https://www.macromicro.me/series/7148/ovx",  # 石油ETF波動率
    "https://www.macromicro.me/series/8219/us-wti-crude-oil-spot-price-daily",
    "https://www.macromicro.me/series/854/us-oil-inventory", # 美國-原油庫存
    "https://www.macromicro.me/series/19080/us-strategic-petroleum-reserve", # 美國-戰略石油儲備[SPR]

    # [2026-09-22] sid 483 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/483/us-dollar-index",
    "https://www.macromicro.me/series/4456/jp-10-year-yield-spread-japan-us",
    "https://www.macromicro.me/series/2018/japan-bond-10-year",
    "https://www.macromicro.me/series/29123/us-treasury-general-account-daily", # 政部帳戶(TGA)餘額
    # [2026-09-22] sid 7449/348 改由 get_fred_csv.py 抓取(WN-A WP-A1)
    # "https://www.macromicro.me/series/7449/us-fed-excess-reserves-weekly", # 商業銀行在聯邦儲備系統超額準備金
    "https://www.macromicro.me/series/131/core-consumer-price-index-sa-yoy", # 美國-核心消費者物價指數(Core PCI) 年增
    # "https://www.macromicro.me/series/348/pce-core-price-yoy", # 美國-核心個人消費支出物價指數[PCE](年增率)

    # 差值 是景氣循環的基礎 台灣比美國領先 zavy 和台灣指數比對一下
    # [2026-09-17] sid 590/595 改由 get_ism_pmi.py 處理(透過 05 檔已寫入的 pkl 合成)
    # "https://www.macromicro.me/series/590/tw-pmi-new-orders", #台灣-製造業採購經理人指數[PMI]-新增訂單
    # "https://www.macromicro.me/series/595/tw-pmi-customers-invertories", # 台灣-製造業採購經理人指數[PMI]-客戶存貨
    # 流動性 落後指標 但是很值得參考的指標
    "https://www.macromicro.me/series/31742/global-money-supply-m2-yoy", # 全球-四大央行貨幣供給[M2](年增率)

    # 和 S&P 500 比較一下 景氣循環 zavy
    # [2026-09-17] sid 267/277/281 改由 get_ism_pmi.py 抓取
    # "https://www.macromicro.me/series/281/ism-manufacturing-backlogoforders", # 美國-ISM製造業指數[PMI]-未完成訂單
    # "https://www.macromicro.me/series/267/ism-manufacturing-neworders", # 美國-ISM製造業指數[PMI]-新訂單
    # "https://www.macromicro.me/series/277/ism-manufacturing-customersinventories", # 美國-ISM製造業指數[PMI]-客戶端存貨
    # "https://www.macromicro.me/series/22807/us-pmi-new-orders-minus-customers-invertories", # 美國-PMI新訂單減客戶端存貨

    #
    # 全球-PMI年變動擴散指數是一個衡量全球製造業活動變化的指標。PMI代表採購經理人指數，它通常用來衡量製造業的活動水平。
    # 年變動擴散指數則是指過去一年中全球各地的PMI變動情況。當這個指數上升時，表示全球製造業活動正在擴散增長；
    # 當指數下降時，表示全球製造業活動正在收縮。這個指數可以幫助我們了解全球製造業的整體趨勢和變化。
    # [2026-09-16] sid 20508 改由 get_m_square_chart_api.py 抓取


    # 流動性 FED 利率 / 公債殖利率 → 改由 get_fed_series.py（FRED + NY Fed SOFR API）


    # 全球金融壓力指數（OFR）
    # 全球金融壓力指數（OFR）是一個衡量全球金融體系穩定性的指標。它通常根據市場價格、波動性和流動性等數據來評估金融市場的風險水平。
    # 當OFR指數上升時，表示金融市場面臨著更大的壓力和風險，可能預示著金融危機的可能性增加。
    # [2026-09-17] 改由 get_ofr_fsi_global.py 抓取
    # "https://www.macromicro.me/series/4869/global-ofr-fsi", # 全球金融壓力指數(OFR)
    # 美國金融壓力指數(OFR) → 改由 get_financial_stress.py（OFR 官方 CSV）
    # "https://www.macromicro.me/series/4866/us-ofr-fsi",

    # 美德利差 DXY 歐元匯率
    "https://www.macromicro.me/series/4448/de-10-year-yield-spread-germany-us", # 美德-10年期公債利差
    # [2026-09-22] sid 562/483 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/562/fx-eur-usd", # 歐元/美元
    # "https://www.macromicro.me/series/483/us-dollar-index", # DXY 美元指數
    "https://www.macromicro.me/series/1916/germany-bond-10-year", # 德國-10年期公債殖利率


    "https://www.macromicro.me/series/4456/jp-10-year-yield-spread-japan-us", # 美日-10年期公債利差
    # [2026-09-22] sid 385 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/385/fx-usd-jpy", #美元/日圓
    # [2026-09-16] sid 32377 改由 get_m_square_chart_api.py 抓取(chart 102471 series[0])


    # fedwatch 升降息
    "https://www.macromicro.me/series/484/probability-fed-rate", #生息
    "https://www.macromicro.me/series/1645/probability-fed-rate-decrease", #降息
    # "",
    # "",
    # "",

    # vix 與黑天鵝
    # VIX 30D、VVIX、VIX 期限結構 皆改由 get_cboe_index.py（CBOE CDN）→ series_cboe_*.pkl
    "https://www.macromicro.me/series/4407/cboe-skew", # 黑天鵝
    "https://www.macromicro.me/series/1650/us-put-call-ratio-total", # put call ratio

    # VIX 期限結構（M² 28769/7173/7174/7175/7770）已改 CBOE：cboe_VIX1D…VIX1Y
    #
    # 美債波動率(MOVE) → 改由 get_yahoo_series.py（Yahoo Finance ^MOVE，2026-09-16）
    # "https://www.macromicro.me/series/17581/us-treasury-move-index",

    # 原油CFTC
    "https://www.macromicro.me/series/8297/crude-oil-futures-and-options-manage-money-long-position",
    "https://www.macromicro.me/series/8298/crude-oil-futures-and-options-manage-money-short-position",
    "https://www.macromicro.me/series/8296/crude-oil-futures-and-options-manage-money-net-position",

    # 市場寬度
    "https://www.macromicro.me/series/18331/sp500-50ma-breadth",
    "https://www.macromicro.me/series/22718/sp-500-200ma-breadth",
    # "",

    # 週期
    # [2026-09-17] sid 22807/22806 改由 get_ism_pmi.py 抓取
    # "https://www.macromicro.me/series/22807/us-pmi-new-orders-minus-customers-invertories",
    # "https://www.macromicro.me/series/22806/tw-pmi-new-orders-minus-customers-invertories",

    # AAII 情緒
    # [2026-09-17] sid 6783/6784/6785 改由 get_official_xlsx.py 抓取
    # "https://en.macromicro.me/series/6785/aaii-sentiment-survey-bearish",
    # "https://en.macromicro.me/series/6784/aaii-sentiment-survey-neutral",
    # "https://en.macromicro.me/series/6783/aaii-sentiment-survey-bullish"

    # 澳元日幣,
    # [2026-09-22] sid 7145/7146/745 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/7145/fx-aud-jpy",
    # "https://www.macromicro.me/series/7146/fx-aud-nzd", # 澳幣/紐必
    # "https://www.macromicro.me/series/745/fx-aud-usd",

    # 台股 台幣
    # [2026-09-17] sid 2752/2756 改由 get_official_xlsx.py 抓取(WSTS)
    # "https://www.macromicro.me/series/2752/americas-semiconductor-billings-yoy",
    # "https://www.macromicro.me/series/2756/global-semiconductor-billings-yoy"
    # [2026-09-22] sid 621 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/621/fx-usd-twd",  # 台幣匯率
    # [2026-09-17] sid 5683 改由 get_official_xlsx.py 抓取(TWSE)
    # "https://www.macromicro.me/series/5683/taiwan-stock-price-to-earnings-ratio"

    # 愛克榭 CCC 信用利差
    "https://www.macromicro.me/series/3612/us-credit-spread",  # 信用風險利差
    # [2026-09-22] sid 755/634 改由 get_fred_csv.py 抓取(WN-A WP-A1)
    # "https://www.macromicro.me/series/755/delinquency-rate-on-business-loans",  # 商銀貸款拖欠率-企業
    # "https://www.macromicro.me/series/634/bofa-merrill-lynch-us-corporate-ccc",  # CCC級或以下高收益債券有效殖利率

    # 愛克榭 CBR vs 10年
    "https://www.macromicro.me/series/3776/crb-index",

    # 就學貸款違約率  影響消費意願
    "https://www.macromicro.me/series/4433/us-debt-severe-delinquency-student",

    # 衰退指鰾 領先
    "https://www.macromicro.me/series/374/cb-leading-index",  # 經濟諮商局-領先指標
    "https://www.macromicro.me/series/376/cb-coincident-index",  # 衰退指鰾  同時指標

    # 美國-芝加哥聯儲當週金融狀況指數
    # 芝加哥聯儲 NFCI → 改由 get_financial_stress.py（Chicago Fed 官方 CSV）
    # "https://www.macromicro.me/series/5696/united-states-chicago-fed-national-financial-conditions-index",

    # 油價共振
    # [2026-09-22] sid 386 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/386/fx-usd-cad",

    # Nikkei 225
    # [2026-09-22] sid 1281 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/1281/japan-nikkei225",

    # 美元/加幣 (重複行,同 sid 386 已於上方移除)
    # "https://www.macromicro.me/series/386/fx-usd-cad",

    # 黃金 ETF 波動率指數
    "https://www.macromicro.me/series/7147/gvz", # 黃金 GVZ 波動率指數
    # [2026-09-22] sid 485 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/485/gold-futures", # 黃金 GVZ 波動率指數

    # 5-Year CDS (主權信用違約交換)
    # [2026-09-17] 9 條 CDS 改由 get_cds_series.py 抓取(investing.com + WGB)
    #"https://www.macromicro.me/series/27118/uk-5year-cds",       # 英國
    #"https://www.macromicro.me/series/27119/germany-5year-cds",  # 德國
    #"https://www.macromicro.me/series/27126/france-5year-cds",   # 法國
    #"https://www.macromicro.me/series/27135/italy-5year-cds",    # 義大利
    #"https://www.macromicro.me/series/27129/portugal-5year-cds", # 葡萄牙
    #"https://www.macromicro.me/series/27131/spain-5year-cds",    # 西班牙
    #"https://www.macromicro.me/series/27136/brazil-5year-cds",   # 巴西
    #"https://www.macromicro.me/series/27138/turkey-5year-cds",   # 土耳其
    #"https://www.macromicro.me/series/27134/mexico-5year-cds",   # 墨西哥

    # 美國股市經濟總覽
    # [2026-09-16 遺漏補清] sid 7249/4 其實 09-16/17 那批就已經改由 get_fred_csv.py 抓取,漏了清 url_list
    # "https://www.macromicro.me/series/7249/fereral-reserve-bank-of-new-york-weekly-economic-index",  # WEI
    # "https://www.macromicro.me/series/4/realgdp-yoy",  # 美國實質GDP
    "https://www.macromicro.me/series/75/saving-rate",  # 儲蓄率
    "https://www.macromicro.me/series/7359/pce-real-yoy",  # 個人消費支出
    # [2026-09-22] sid 560/246 改由 get_fred_csv.py 抓取(WN-A WP-A1/A1b)
    # "https://www.macromicro.me/series/560/real-disposable-personal-income-yoy",  # 可支配所得
    # "https://www.macromicro.me/series/246/existing-home-sales-yoy",  # 成屋銷售
    "https://www.macromicro.me/series/254/new-home-sales-yoy",  # 新屋銷售
    # [2026-09-22] sid 255 改由 get_fred_csv.py 抓取(WN-A WP-A1)
    # "https://www.macromicro.me/series/255/price-new-houses",  # 新屋房價中位數
    # https://www.macromicro.me/series/261/us-case-shiller-home-price  # S&P/Case-Shiller 前20大城市房價
    # [2026-09-17] sid 261 改由 get_fred_csv.py 抓取(FRED SPCS20RSA)
    "https://www.macromicro.me/series/414/sp-case-shillar-20-home-price-nsa",  # S&P/Case-Shiller 前20大城市房價 NSA
    # [2026-09-22] sid 22910 改由 get_fred_csv.py 抓取(WN-A WP-A1)
    # "https://www.macromicro.me/series/22910/sahm-rule-recession-indicator",  # 薩姆規則
    "https://www.macromicro.me/series/44/nonfarm-payrolls-yearlychange",  # 非農就業
    # [2026-09-22] sid 37/34/36 改由 get_fred_csv.py 抓取(WN-A WP-A1)
    # "https://www.macromicro.me/series/37/unemployment-rate",  # 失業率
    # "https://www.macromicro.me/series/34/initialclaims",  # 初次申請失業金
    # "https://www.macromicro.me/series/36/continuedclaims",  # 連續申請失業金
    # [2026-09-22] sid 4481 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/4481/coppergold",  # 銅金比
    "https://www.macromicro.me/series/17586/sp500-eps",  # S&P 500 EPS 成長率

    # 愛克榭
    # [2026-09-22] sid 319 改由 get_fred_csv.py 抓取(WN-A WP-A1)
    # "https://www.macromicro.me/series/319/durable-goods",  # 耐久財新訂單-非國防資本財

    # [2026-09-22] sid 4249 改由 get_yfinance_series.py 抓取(WN-A WP-A2)
    # "https://www.macromicro.me/series/4249/bitcoin-usd", # 比特幣
]




local_url_list = [
    # "https://www.macromicro.me/series/7054/consumer-confidence", # 美國-經濟諮商局消費者信心指數
    # "https://www.macromicro.me/series/72/michigan-consumer-confidence",
    # "https://www.macromicro.me/series/363/2year-bond-yield", # 美國 2年期 # 美國-密大消費者信心指數。
    "https://www.macromicro.me/series/4249/bitcoin-usd",
    # VIX 改 CBOE，本地測試勿再用 M² 355
]

folder = os.getenv("DATA_DIR")  # 默認數據目錄
if not os.path.exists(folder):
    os.makedirs(folder)

logger.info(f"m平方 chart log is saved to {folder}")

def fetch_m_square_series():
    fetch_data_from_urls(url_list, folder)

if __name__ == "__main__":

    if 1:
        # output_directory = "./output"
        fetch_data_from_urls(local_url_list, folder)
    else:
        fetch_data_from_urls(url_list, folder)
