from app.utils import ChartModule

_module = ChartModule(
    filename='美國股市經濟總覽',
    chart_titles=[
        "WEI, real GDP",
        "儲蓄, 支出, 可支配所得",
        "成屋銷售, 新屋銷售, 新屋房價, S&P前20大城市房價",
        "薩姆規則, 非農就業, 失業率, 初次申請, 連續申請",
        "銅金比 領先 SP500 EPS成長率 幾個月",
    ],
    chart_ids=[
        [7249, 4],
        [75, 7359, 560],
        [246, 254, 255, 261],
        [22910, 44, 37, 34, 36],
        [4481, "17586.YOY", 17586, 356],
    ],
    axis_config=[
        [0, 0, 0],
        [0, 0, 2, 3],
        [0, 1, 2, 3, 3],
        None,
        None,
    ],
    summary_list=[
        "投機性空頭低點至24000,油價就有機會反轉向下,也有可能由低向高穿越油價才向下<br>"
        "投機性空頭高點向下就有機會上漲,也可以用來確認低點(當空頭高點反轉), 相對不准! <br>"
        "OVX反轉和油價反轉可能同向也可能反向! 可以在投機性空頭鈍化時確認方向!",
        "Crack Spread有預示未來油價的能力",
        None,
    ],
    reverse_ids=[385],
    plot_lines_config=[
        (0, 8298, 24000),
    ],
    range_selector_override={
        "extra_buttons": [{"type": "year", "count": 25, "text": "25y"}],
        "selected": 4,
    },
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
