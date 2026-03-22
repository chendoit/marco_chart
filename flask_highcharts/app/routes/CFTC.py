from app.utils import ChartModule

_module = ChartModule(
    filename='CFTC',
    charts=[
        {
            "title": "日圓匯率, 美日利差與CME持倉",
            "ids": [385, 4456, "jpy_cme_open_interest"],
            "summary": """ 美元指數基本與美德匯差有正向關係<br>。""",
        },
        {
            "title": "日圓匯率, 投機性持倉多空",
            "ids": [385, "jpy_cme_noncommercial_long", "jpy_cme_noncommercial_short", "jpy_cme_net_position_large_spec"],
            "summary": "",
        },
        {
            "title": "歐元匯率, 美德利差與CME持倉",
            "ids": [4448, 562, "eur_cme_open_interest"],
            "summary": "",
        },
        {
            "title": "歐圓匯率, 投機性持倉多空",
            "ids": [562, "eur_cme_noncommercial_long", "eur_cme_noncommercial_short", "eur_cme_net_position_large_spec"],
            "summary": "",
        },
        {
            "title": "使用日圓投機空頭預測Vix Peak",
            "ids": [385, "jpy_cme_noncommercial_short", 355],
            "summary":
                "1. 日圓空頭高點向下快速滑落, Vix隨後升高<br>"
                "2. 或Vix先發生危機, 觸發日圓空頭滑落, 引起日圓升值(避險貨幣)",
        },
    ],
    reverse_ids=[
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
