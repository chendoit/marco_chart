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

CHART_IDS = [2, 'STLFSI4']

SUMMARY_LIST = [
    "S&P500和SOFR99!!"
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_y_axis_config(chart_id_list):
    """根據 chart_id_list 獲取 Y 軸配置"""
    return [0, 1, 2, 2, 2, 2, 2, 2][:len(chart_id_list)]


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

        # 特殊的 plot lines 配置
        if chart_id_list == CHART_IDS[0] and 6225 in (chart_id_list if isinstance(chart_id_list, list) else [chart_id_list]):
            y_axis["plotLines"] = [{
                "value": 0.12,
                "color": "#f28703",
                "dashStyle": "shortdash",
                "width": 3,
                "label": {
                    "text": "0.12",
                    "align": "right",
                    "style": {"color": "#f28703"}
                }
            }]

        y_axes.append(y_axis)

    return {
        "chart": {
            "type": "line",
            "zoomType": "x",
            "height": "100%",
            "aspectRatio": 1,
            "className": 'aspect-square'
        },
        "title": {"text": current_filename},
        "xAxis": {
            "type": "datetime",
            "range": 6 * 30 * 24 * 3600 * 1000,
        },
        "yAxis": y_axes,
        "tooltip": {"valueDecimals": 2},
        "legend": {"enabled": True},
        "rangeSelector": {
            "enabled": True,
            "buttons": [
                {"type": "month", "count": 6, "text": "6m"},
                {"type": "year", "count": 1, "text": "1y"},
                {"type": "year", "count": 2, "text": "2y"},
                {"type": "all", "text": "Max"}
            ],
            "selected": 0
        },
        "navigator": {"enabled": True},
        "scrollbar": {"enabled": True},
        "series": []
    }
