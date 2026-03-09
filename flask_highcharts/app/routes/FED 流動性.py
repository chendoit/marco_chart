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

CHART_TITLES = [
    "S&P, ONRRP, IORB, SOFR, FED fund rate, SOFR 75",
    "S&P, SOFR 75, 聖路易斯金融壓力指數, SOFR IORB spread,OFR FSI",
    " 美國國債1年期, 美國國債1年期, SOFR, IORB, 美債波動率, onrrp vol",
]

CHART_IDS = [
    [2, 40593, 19268, 6222, 356, 6225],  # S&P, ONRRP, IORB, SOFR, FED fund rate, SOFR 75
    [2, 6225, 'STLFSI4', (6225, '-', 19268), 4869],  # S&P, SOFR 75, 聖路易斯金融壓力指數, SOFR IORB spread,OFR FSI
    [5549, 354, 6222, 19268, 17581, 17449],  # 美國國債1年期, 美國國債1年期, SOFR, IORB, 美債波動率, onrrp vol
]

AXIS_CONFIG = [
    [0, 1, 0, 1, 1, 1],
    None,
    [0, 0, 1, 1, 2, 2],
    None,
    None,
]

SUMMARY_LIST = [
    """當SOFR超過ONRRP, 表示流動性吃緊, 市場可能恐慌下跌!"""
    "比較Fed fune rate 與金融壓力指數",
    "SOFR75 1/22後開始攀升!!",
    "OIS 利率預期。1/30後又開始有降息期望",
    "9/18降息兩碼後,債劵波動性開始攀升,10年公債殖利率升高,流動性開始吃緊。<br>"
    "11/6後債劵下跌,但是公債殖利率不回頭<br>"
    "ONRRP 交易量開始吃緊!!",
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_chart_title(chart_id_list):
    """根據 chart_id_list 查找對應的圖表標題"""
    try:
        if not chart_id_list:
            return '圖表'

        default_title = '圖表'

        for i, chart_ids in enumerate(CHART_IDS):
            if chart_id_list == chart_ids:
                if i < len(CHART_TITLES):
                    if CHART_TITLES[i] is None:
                        return default_title
                    return CHART_TITLES[i]
                else:
                    return default_title

        return default_title

    except Exception as e:
        print(f"get_chart_title 發生錯誤：{str(e)}")
        return '圖表'


def get_y_axis_config(chart_id_list):
    """根據 chart_id_list 查找對應的 Y 軸配置"""
    try:
        if not chart_id_list:
            return []

        default_config = list(range(len(chart_id_list)))

        for i, chart_ids in enumerate(CHART_IDS):
            if chart_id_list == chart_ids:
                if i < len(AXIS_CONFIG):
                    if AXIS_CONFIG[i] is None:
                        return default_config
                    return AXIS_CONFIG[i]
                else:
                    return default_config

        return default_config

    except Exception as e:
        print(f"get_y_axis_config 發生錯誤：{str(e)}")
        return list(range(len(chart_id_list)))


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


def add_plot_lines(chart_id_list, chart_id_entry, y_axis):
    """為此模組的圖表添加特定的 plot lines"""
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 0, 8298, 24000, y_axis)


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

        add_plot_lines(chart_id_list, chart_id_entry, y_axis)
        y_axes.append(y_axis)

    chart_title = get_chart_title(chart_id_list)
    return get_base_chart_config(y_axes, chart_title)
