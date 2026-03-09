from app.utils import ChartModule

_module = ChartModule(
    filename='日圓',
    chart_titles=[
        "日圓, 投機多空持倉",
        "日圓, VIX, SP500共振",
        "澳幣日圓, 紐幣日圓, VIX",
    ],
    chart_ids=[
        [385, 4456, 'jpy_cme_noncommercial_long', "jpy_cme_noncommercial_short"],
        [385, 2, 355],
        [7145, (7145, '/', 7146), 355],
    ],
    axis_config=[
        None,
        None,
        [0, 0, 1],
    ],
    summary_list=[
        "",
        "",
        "當AUDJPY上行，對應的是波動率下降和低波動率時代，其實就是確定性的增加，<br>"
        "當AUDJPY下行的時候，往往是不確定性的增加，對應的也是高波動率的環境",
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
