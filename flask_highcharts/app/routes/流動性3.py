from app.utils import ChartModule

_module = ChartModule(
    filename='流動性3',
    chart_titles=["流動性3", "流動性3"],
    chart_ids=[[2], ['STLFSI4']],
    summary_list=["S&P500和SOFR99!!"],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
