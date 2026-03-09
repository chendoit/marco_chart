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
    is_yoy_expression,
    process_yoy,
)

# ============================================================
# 圖表配置常數
# ============================================================

CHART_TITLES = [
    "WEI, real GDP",
    "儲蓄, 支出, 可支配所得",
    "成屋銷售, 新屋銷售, 新屋房價, S&P前20大城市房價",
    "薩姆規則, 非農就業, 失業率, 初次申請, 連續申請",
    "銅金比 領先 SP500 EPS成長率 幾個月",
]

CHART_IDS = [
    [7249, 4],  # WEI, real GDP
    [75, 7359, 560],  # 儲蓄, 支出, 可支配所得
    [246, 254, 255, 261],  # 成屋銷售, 新屋銷售, 新屋房價, S&P前20大城市房價
    [22910, 44, 37, 34, 36],  # 薩姆規則, 非農就業, 失業率, 初次申請, 連續申請
    [4481, "17586.YOY", 17586, 356],  # 銅金比 領先 SP500 EPS成長率 幾個月
]

AXIS_CONFIG = [
    [0, 0, 0],
    [0, 0, 2, 3],
    [0, 1, 2, 3, 3],
    None,
    None,
]

SUMMARY_LIST = [
    "投機性空頭低點至24000,油價就有機會反轉向下,也有可能由低向高穿越油價才向下<br>"
    "投機性空頭高點向下就有機會上漲,也可以用來確認低點(當空頭高點反轉), 相對不准! <br>"
    "OVX反轉和油價反轉可能同向也可能反向! 可以在投機性空頭鈍化時確認方向!",
    "Crack Spread有預示未來油價的能力",
    None
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
    reverse_ids = [385]

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
        if is_yoy_expression(chart_id_entry):
            data = process_yoy(chart_id_entry)
            title = data['title']
        elif is_expression(chart_id_entry):
            data = process_expression(chart_id_entry)
            title = data['title']
        elif isinstance(chart_id_entry, list):
            data = load_series_data(chart_id_entry[0])
            title = current_filename
        else:
            data = load_series_data(chart_id_entry)
            title = data.get('title', f'Series {i}')

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
    config["rangeSelector"]["buttons"].append({"type": "year", "count": 25, "text": "25y"})
    config["rangeSelector"]["selected"] = 4
    return config
