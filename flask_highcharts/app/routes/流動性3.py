from app.utils import ChartModule

_module = ChartModule(
    filename='流動性3',
    charts=[
        {
            "title": "流動性3",
            "ids": [2],
            "summary": "S&P500和SOFR99!!",
        },
        {
            "title": "流動性3",
            "ids": ['STLFSI4'],
        },
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
