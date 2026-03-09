from app.utils import ChartModule

_module = ChartModule(
    filename='流動性',
    chart_titles=["流動性"],
    chart_ids=[['STLFSI4', '4456']],
    axis_config=[[0, 1]],
    summary_list=["S&P500和SOFR99!!"],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
