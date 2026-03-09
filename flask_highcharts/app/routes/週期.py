from app.utils import ChartModule

_module = ChartModule(
    filename='週期',
    chart_titles=[
        "美國-PMI新訂單減客戶端存貨 台灣美國-PMI新訂單減客戶端存貨, 每月公布",
    ],
    chart_ids=[
        [22807, 22806],
    ],
    summary_list=[
        "投機性空頭低點至24000,油價就有機會反轉向下,也有可能由低向高穿越油價才向下<br>"
        "投機性空頭高點向下就有機會上漲,也可以用來確認低點(當空頭高點反轉), 相對不准! <br>"
        "OVX反轉和油價反轉可能同向也可能反向! 可以在投機性空頭鈍化時確認方向!",
        "Crack Spread有預示未來油價的能力",
        None,
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
