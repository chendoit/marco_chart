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
    [4448, 562, 483],  # 美德利差10年, DXY, 歐元/美元匯率
    [4456, 385, 483, (6225, '-', 19268)],  # 美日利差-10年, 日圓/美元, DXY
    [4456, 385, (6225, '-', 19268)],  # 美日利差-10年, 日圓/美元, DXY
    [(6222, '-', 19268), 385, (6225, '-', 19268)],  # 日圓/美元, SOFR IORB spread
    [356, 354, 1645, 484, 4456, 385],  # FED fund rate, 美國10年公債, fedwatch 降息機率, 昇息, 美日利差-10年, 日圓/美元
]

SUMMARY_LIST = [
    """
    美元指數基本與美德匯差有正向關係<br>
    歐元/美元匯率基本與美德匯差成反向關係<br>
    美德匯差 2.2, 1.1 後反轉, 1.5趨勢確立, 基本是2023年後經驗法則<br>
    這兩年, 美德匯差有提前反應的趨勢, 但是這個指標應該是一個驗證(慢)指標 <br>
    驗證(慢)指標, 用來發現趨勢反轉 反轉後仍可有一個很長趨勢!!<br>
    誰先誰後不重要, 當趨勢不相合時就是要注意的時候 <br>
    美元指數基本與美德利差同向,除了1986-1989布靈頓森林會議,2000後網路泡沫危機,美元為避險貨幣,美元強勢。
    """,
    "當美日利差小於3就需要注意是否會發生<mark>日圓反轉</mark> <br> "
    "當SOFR75-IORB>0.07 <mark>日圓反轉 DXY反轉 2023Mar, 2023Dec 2024Oct 2024Dec 都有這個趨勢</mark><br> "
    "2024/3月開始 美日匯率與利差背離 就預示了一種趨勢 當反轉到 7/9, <br>"
    "轉成同向,此時持續出現美元流動性不足,這就會出現重大波動"
    "<mark>也就是如果再出現, 日圓持續上漲, 流動性不足 就是一種徵兆!</mark>",
    "當美日利差小於3就需要注意是否會發生<mark>日圓反轉</mark> <br> "
    "當SOFR75-IORB>0.07 <mark>日圓反轉 DXY反轉 2023Mar, 2023Dec 2024Oct 2024Dec 都有這個趨勢</mark><br> "
    "2024/3月開始 美日匯率與利差背離 就預示了一種趨勢 當反轉到 7/9, <br>"
    "轉成同向,此時持續出現美元流動性不足,這就會出現重大波動"
    "<mark>也就是如果再出現, 日圓持續上漲, 流動性不足 就是一種徵兆!</mark>",
    "單看SOFR7和IORB拉大, 日圓反轉",
    "注意升降息, 機率急遽變化",
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_y_axis_config(chart_id_list):
    if chart_id_list == CHART_IDS[4]:
        y_axis_config = [3, 3, 2, 2, 3, 5]
    else:
        y_axis_config = list(range(len(chart_id_list)))
    return y_axis_config


def get_chart_title(chart_id_list):
    if chart_id_list == CHART_IDS[0]:
        return '美德利差與DXY'
    elif chart_id_list == CHART_IDS[1]:
        return '日圓/美元, DXY與SOFR IORB spread, 美日利差'
    elif chart_id_list == CHART_IDS[2]:
        return '日圓/美元與SOFR IORB spread, 美日利差'
    elif chart_id_list == CHART_IDS[3]:
        return '日圓/美元與SOFR IORB spread'
    else:
        return '美日利差與Fedwatch升降息機率'


def add_plot_lines(chart_id_list, chart_id_entry, y_axis):
    """為此模組的圖表添加特定的 plot lines"""
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 0, 4448, [1.1, 1.5, 2.2], y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 1, (6225, '-', 19268), 0.07, y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 1, 4456, 3, y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 2, (6225, '-', 19268), 0.07, y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 4, 4456, 3, y_axis)


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
