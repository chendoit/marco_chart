import os
from app.utils import (
    colors,
    load_series_data,
    process_expression,
    add_plot_line,
    generate_chart_data as _generate_chart_data,
    get_base_chart_config,
    build_y_axis,
    is_expression,
)

# ============================================================
# 圖表配置常數
# ============================================================

CHART_IDS = [
    [356, 5549, (1150443, '-', 1150440), 1645],  # FED fund rate, 1年公債, OIS 1年減1個月, fedwatch 升息機率, 降息機率
    [356, 5549, (1150443, '-', 1150440)],  # FED fund rate, 1年公債,OIS 1年減1個月
    [356, 5549, 354, (1150443, '-', 1150440), 483],  # FED fund rate, 1年公債, 10年公債, OIS 1年減1個月, DXY
]

SUMMARY_LIST = [
    "OIS利率預期和Fedwatch升降息機率綜合參考<br>"
    "由5月份預計不降息, 到7月底降息1碼, <mark>到7/31機率大增, 預計降息4碼, 應對到8/5大跌!!!!</mark><br>"
    "這個也應對到美元流動性不足 SOFR75",
    "這個也應對到美元流動性不足 SOFR75",
    "2024 九月預計降4次 到2025/1月預期不降息, 但是9月之後美元指數和10年殖利率因為流動性不足一直上揚",
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_y_axis_config(chart_id_list):
    """根據 chart_id_list 獲取 Y 軸配置"""
    if chart_id_list == CHART_IDS[0]:
        y_axis_config = [0, 0, 1, 3, 3]
    elif chart_id_list == CHART_IDS[1]:
        y_axis_config = [0, 0, 2, 3, 3]
    elif chart_id_list == CHART_IDS[2]:
        y_axis_config = [0, 0, 0, 3, 4]
    else:
        y_axis_config = [0] * len(chart_id_list)
    return y_axis_config


def get_chart_title(chart_id_list):
    if chart_id_list == CHART_IDS[0]:
        return "S&P500 與Fed Rates"
    return current_filename


def add_plot_lines(chart_id_list, chart_id_entry, y_axis):
    """為此模組的圖表添加特定的 plot lines"""
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 1, (1150443, '-', 1150440), -0.25, y_axis)


# ============================================================
# 圖表生成函數
# ============================================================

def generate_chart_data(chart_id_entry, months=600):
    """生成圖表數據"""
    return _generate_chart_data(chart_id_entry, get_y_axis_config, months)


def get_chart_config(chart_id_list):
    """生成 Highcharts 配置"""
    y_axes = []

    for i, chart_id_entry in enumerate(chart_id_list):
        if is_expression(chart_id_entry):
            data = process_expression(chart_id_entry)
            title = data['title']
        elif isinstance(chart_id_entry, list):
            data = load_series_data(chart_id_entry[0])
            title = current_filename
        else:
            data = load_series_data(chart_id_entry)
            title = data['title']

        y_axis = build_y_axis(
            title=title,
            index=i,
            reversed_flag=False
        )

        add_plot_lines(chart_id_list, chart_id_entry, y_axis)
        y_axes.append(y_axis)

    chart_title = get_chart_title(chart_id_list)
    return get_base_chart_config(y_axes, chart_title)
