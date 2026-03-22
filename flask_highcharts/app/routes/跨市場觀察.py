from app.utils import ChartModule

_module = ChartModule(
    filename='跨市場觀察',
    charts=[
        {
            "title": "VVIX 日圓投機空頭, 預見突發危機",
            "ids": [2, 22904, 355, "jpy_cme_noncommercial_short"],
            "summary": """ 日圓空頭由高點滑落, 且VVIX由底部上升到達100, 強力風險警示!! <br>
    有時VVIX領跑, 如果日圓空頭高位有機會伴隨日圓升值(避險貨幣真義)! """,
        },
        {
            "title": "日圓, VIX VVIX, SP500共振",
            "ids": [385, 2, 355, 22904],
            "summary": "VVIX 100以上高位就有風險, 如果有日圓空頭下滑更好, 但是PutCall ratio為跟隨信號, 可以觀察極值(>1.2),PutCall下滑,伴隨回檔,當到達0.8一般反彈趨緩!",
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
