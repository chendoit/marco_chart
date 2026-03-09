from app.utils import ChartModule

_module = ChartModule(
    filename='AAII情緒',
    chart_titles=[
        "AAII bearish, neutral, bullish ",
        "AAII bearish, bearish MA ",
    ],
    chart_ids=[
        [2, 6785, 6784, 6783],
        [2, 6785, "6785.MA20"],
    ],
    axis_config=[
        [0, 1, 1, 1],
        [0, 1, 1, 1],
    ],
    summary_list=[
        "AAII 情緒<br>",
        None,
    ],
    reverse_ids=[385],
    plot_lines_config=[
        (0, 6785, 50),
        (1, 6785, 50),
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
