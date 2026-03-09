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
    "半導體產值年增率 vs 台股PE",
    "半導體產值年增率 vs 台幣匯率",
]

CHART_IDS = [
    [2756, 5683],  # 半導體產值年增率, 台股PE
    [2756, 621],  # 半導體產值年增率, 台幣匯率
    [2756, 5683, 621],  # 半導體產值年增率, 台股PE, 台幣匯率
]

AXIS_CONFIG = [
    None,
    None,
    None,
    None,
]

# 定義需要反向的圖表ID列表
reverse_ids = [621]

SUMMARY_LIST = [
    "台股PE 高點領先 半導體年增率 2-3Q (訂單在談 PE就開始漲)",
    "半導體年增率 領先台股匯率 2-3Q (美元匯回台灣 台幣就高) 不過這點 目前好像沒有生效 "
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
        print(f"發生錯誤：{str(e)}")
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
        print(f"發生錯誤：{str(e)}")
        return list(range(len(chart_id_list)))


def should_reverse_axis(chart_id_entry):
    """判斷是否需要反向 Y 軸"""
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
    pass


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
    config = get_base_chart_config(y_axes, chart_title)
    # 覆蓋 rangeSelector 預設設定
    config["rangeSelector"]["buttons"].append({"type": "year", "count": 15, "text": "15y"})
    config["rangeSelector"]["selected"] = 4
    return config
