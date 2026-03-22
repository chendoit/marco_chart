from app.utils import ChartModule

_module = ChartModule(
    filename='原油',
    charts=[
        {
            "title": "投機性空頭, 原油期貨, ovx",
            "ids": [486, 8298, 7148],
            "axis": [0, 1, 0, 1, 1, 1],
            "summary":
                "投機性空頭低點至24000,油價就有機會反轉向下,也有可能由低向高穿越油價才向下<br>"
                "投機性空頭高點向下就有機會上漲,也可以用來確認低點(當空頭高點反轉), 相對不准! <br>"
                "OVX反轉和油價反轉可能同向也可能反向! 可以在投機性空頭鈍化時確認方向!",
            "plot_lines": [(8298, 24000)],
        },
        {
            "title": "原油期貨, crack spread, ovx",
            "ids": [486, 4934, 7148],
            "summary": "Crack Spread有預示未來油價的能力",
        },
        {
            "title": "原油庫存(不含SPR), 戰略石油儲備",
            "ids": [854, 19080],
            "axis": [0, 0, 0],
        },
        {
            "title": "原油期貨, 原油庫存(不含SPR), 投機性空頭",
            "ids": [486, 8298],
        },
        {
            "title": "S&P500, 原油期貨, 跨市場觀察",
            "ids": [2, 486],
        },
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
