from app.utils import ChartModule

_module = ChartModule(
    filename='石油裂解價差',
    chart_titles=["石油裂解價差"],
    chart_ids=[[486, 4934]],
    summary_list=["Crack spread會領先油價!"],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
