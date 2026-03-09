from app.utils import ChartModule

_module = ChartModule(
    filename='FED 利率預測',
    chart_titles=[
        "S&P500 與Fed Rates",
        "FED 利率預測",
        "FED 利率預測",
    ],
    chart_ids=[
        [356, 5549, (1150443, '-', 1150440), 1645],
        [356, 5549, (1150443, '-', 1150440)],
        [356, 5549, 354, (1150443, '-', 1150440), 483],
    ],
    axis_config=[
        [0, 0, 1, 3, 3],
        [0, 0, 2, 3, 3],
        [0, 0, 0, 3, 4],
    ],
    summary_list=[
        "OIS利率預期和Fedwatch升降息機率綜合參考<br>"
        "由5月份預計不降息, 到7月底降息1碼, <mark>到7/31機率大增, 預計降息4碼, 應對到8/5大跌!!!!</mark><br>"
        "這個也應對到美元流動性不足 SOFR75",
        "這個也應對到美元流動性不足 SOFR75",
        "2024 九月預計降4次 到2025/1月預期不降息, 但是9月之後美元指數和10年殖利率因為流動性不足一直上揚",
    ],
    plot_lines_config=[
        (1, (1150443, '-', 1150440), -0.25),
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
