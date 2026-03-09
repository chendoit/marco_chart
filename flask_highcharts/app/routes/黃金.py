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
    "黃金 GVZ vs 黃金",
]

# 注意：使用運算式時使用三元組格式 (left_id, operator, right_id)
CHART_IDS = [
    [7147, 485],  # 黃金 GVZ vs 黃金
]

AXIS_CONFIG = [
    None,
    None,
]

SUMMARY_LIST = [
    """ 之前的低波動率、橫盤震盪收斂三角形末端，我們採用了「夾板」的 straddle 策略來捕捉波動率的放大。一般投資者當時也可以透過「多空雙開（破位平一腿）」的方式來獲取相應收益。價格加速上行的背後，其實也是波動率持續擴大走高的結果。
        <br> 策略：「Staddle」（跨式策略）或「多空雙開」是一種選擇權或期貨的交易策略。它的核心邏輯是，當你預期市場將有大波動，但不確定是向上還是向下的時候，你可以同時建立多頭和空頭部位。
        <br> 執行：當價格最終選擇方向（例如圖中的向上突破）時，平掉虧損的那一邊（空頭部位），保留盈利的那一邊（多頭部位），從而抓住價格大幅波動帶來的利潤。這就是文中「破位平一腿」的意思。
        <br>
        <br>現在則應該思考在高波動的情況下該怎麼操作。高波動意味著成本上升，因此應該以落袋為安為主，接著觀察市場走勢。
        <br>如果市場繼續橫盤、波動率下降，那仍然屬於上行趨勢的特徵，可能還會有下一次低波動再啟動的機會。
        <br>但若波動率很高、調整劇烈，且波動率沒有下降，則要留意是否出現趨勢轉向的波動率特徵。
    '<img src="https://raw.githubusercontent.com/chendoit/PicBed/main/image-20251018162303929.png" alt="黃金波動率" style="width:40%; height:auto;" >'
        <br> 當波動率放大伴隨價格向下突破，隨後轉為低波動率陰跌，可視為熊市特徵。
-       <br> 當波動率放大推動價格向上突破，隨後進入低波動率緩漲階段，可視為牛市特徵。""",
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
    reverse_ids = [
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
        5696,
        "NFCI",
        1281,
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
    return get_base_chart_config(y_axes, chart_title)
