from app.utils import ChartModule

_module = ChartModule(
    filename='AAII情緒',
    charts=[
        {
            "title": "AAII bearish, neutral, bullish ",
            "ids": [2, 6785, 6784, 6783],
            "axis": [0, 1, 1, 1],
            "summary": "AAII 情緒<br>",
            "plot_lines": [(6785, 50)],
        },
        {
            "title": "AAII bearish, bearish MA ",
            "ids": [2, 6785, "6785.MA20"],
            "axis": [0, 1, 1, 1],
            "plot_lines": [(6785, 50)],
        },
    ],
    reverse_ids=[385],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
