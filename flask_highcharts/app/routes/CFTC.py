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
    [385, 4456, "jpy_cme_open_interest"],  # 日圓匯率, 美日利差
    [385, "jpy_cme_noncommercial_long", "jpy_cme_noncommercial_short", "jpy_cme_net_position_large_spec"],
    [4448, 562, "eur_cme_open_interest"],  # 歐元匯率, 美德利差
    [562, "eur_cme_noncommercial_long", "eur_cme_noncommercial_short", "eur_cme_net_position_large_spec"],  # 歐元匯率
    [385, "jpy_cme_noncommercial_short", 355],  # 日圓匯率, 非商業投機空頭
]

SUMMARY_LIST = [
    """ 美元指數基本與美德匯差有正向關係<br>。""",
    "",
    "",
    "",
    "1. 日圓空頭高點向下快速滑落, Vix隨後升高<br>"
    "2. 或Vix先發生危機, 觸發日圓空頭滑落, 引起日圓升值(避險貨幣)",
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_y_axis_config(chart_id_list):
    if chart_id_list == CHART_IDS[0]:
        y_axis_config = list(range(len(chart_id_list)))
    elif chart_id_list == CHART_IDS[1]:
        y_axis_config = list(range(len(chart_id_list)))
    elif chart_id_list == CHART_IDS[4]:
        y_axis_config = [0, 1, 2]
    else:
        y_axis_config = list(range(len(chart_id_list)))
    return y_axis_config


def get_chart_title(chart_id_list):
    if chart_id_list == CHART_IDS[0]:
        return '日圓匯率, 美日利差與CME持倉'
    elif chart_id_list == CHART_IDS[1]:
        return '日圓匯率, 投機性持倉多空'
    elif chart_id_list == CHART_IDS[2]:
        return '歐元匯率, 美德利差與CME持倉'
    elif chart_id_list == CHART_IDS[3]:
        return '歐圓匯率, 投機性持倉多空'
    elif chart_id_list == CHART_IDS[4]:
        return '使用日圓投機空頭預測Vix Peak'
    else:
        return '匯率'


def should_reverse_axis(chart_id_entry):
    """判斷是否需要反向 Y 軸"""
    reverse_ids = [
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
    ]

    if isinstance(chart_id_entry, (str, int)):
        return chart_id_entry in reverse_ids
    elif isinstance(chart_id_entry, tuple):
        if len(chart_id_entry) == 3:
            return chart_id_entry[0] in reverse_ids or chart_id_entry[2] in reverse_ids
        elif len(chart_id_entry) == 1 and isinstance(chart_id_entry[0], str):
            chart_ids = [x.strip() for x in chart_id_entry[0].split('-')]
            return any(id in reverse_ids for id in chart_ids)
    elif isinstance(chart_id_entry, list):
        return any(id in reverse_ids for id in chart_id_entry)

    return False


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
            reversed_flag=should_reverse_axis(chart_id_entry)
        )

        y_axes.append(y_axis)

    chart_title = get_chart_title(chart_id_list)
    return get_base_chart_config(y_axes, chart_title)
