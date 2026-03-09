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

CHART_IDS = [[486, 4934]]

SUMMARY_LIST = [
    "Crack spread會領先油價!"
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_y_axis_config(chart_id_list):
    """根據 chart_id_list 獲取 Y 軸配置"""
    return list(range(len(chart_id_list)))


# ============================================================
# 圖表生成函數
# ============================================================

def generate_chart_data(chart_id_list, months=600):
    """Generate chart data for Highcharts."""
    chart_data = {"series": []}

    for i, chart_id in enumerate(chart_id_list):
        data = load_series_data(chart_id)
        import pandas as pd
        df = pd.DataFrame(data['data'], columns=['Date', 'Value'])
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).set_index('Date').sort_index()

        max_date = df.index.max()
        if not months:
            min_date = df.index.min()
        else:
            min_date = max_date - pd.DateOffset(months=months)
        df = df[df.index >= min_date]

        date_range = pd.date_range(start=df.index.min(), end=df.index.max(), freq='B')
        df_filled = df.reindex(date_range)
        df_filled['Value'] = df_filled['Value'].interpolate(method='linear')

        data_dict = df_filled[['Value']].to_dict(orient='index')
        data_dict = {str(k.date()): v['Value'] for k, v in data_dict.items()}

        chart_data["series"].append({
            "name": data['title'],
            "data": data_dict,
            "yAxis": 0 if i == 0 else 1,
            "color": colors[0] if i == 0 else colors[1],
            "visible": True
        })

    return chart_data


def get_chart_config(chart_id_list):
    """Get Highcharts configuration for the group."""
    titles = []
    for chart_id in chart_id_list:
        data = load_series_data(chart_id)
        titles.append(data['title'])

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
        "yAxis": [
            {
                "title": {"text": titles[0]},
                "opposite": False,
                "labels": {"format": "{value}"}
            },
            {
                "title": {"text": titles[1]},
                "opposite": True,
                "labels": {"format": "{value}"}
            }
        ],
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
