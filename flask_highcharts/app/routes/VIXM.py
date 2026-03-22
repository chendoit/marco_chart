from app.utils import ChartModule

_module = ChartModule(
    filename='VIXM',
    chart_titles=[
        "VIXM Volume vs S&P 500 vs VIX",
    ],
    chart_ids=[
        ["etf_VIXM_volume", 2, 355],
    ],
    axis_config=[
        [0, 1, 2],
    ],
    summary_list=[
        "VIXM (ProShares VIX Mid-Term Futures ETF) 成交量可作為市場避險需求的觀察指標。"
        "<br>當 VIXM 成交量急升時，通常代表市場參與者正在積極佈局中期波動率避險。"
        "<br>搭配 S&P 500 走勢與 VIX 指數，可觀察恐慌情緒與實際避險行為之間的關聯。",
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
