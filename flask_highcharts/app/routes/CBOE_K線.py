from app.utils import ChartModule

_module = ChartModule(
    filename='CBOE_K線',
    charts=[
        {
            "title": "SPX VVIX VIX K線 + 日圓投機空頭",
            "ids": ["cboe_SPX.OHLC", "cboe_VVIX.OHLC", "cboe_VIX.OHLC",
                    "jpy_cme_noncommercial_short"],
            "axis": [0, 1, 2, 3],
            "summary":
                "S&P 500、VVIX、VIX 以 CBOE OHLC K 線顯示，搭配日圓投機空頭（line）。<br>"
                "日圓空頭由高點滑落 + VVIX 由底部上升到 100 → 強力風險警示。<br>"
                "VVIX 有時領跑，日圓空頭高位有機會伴隨日圓升值（避險貨幣真義）。",
            "plot_lines": [("cboe_VVIX.OHLC", 100)],
        },
    ],
    reverse_ids=["jpy_cme_noncommercial_short"],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
