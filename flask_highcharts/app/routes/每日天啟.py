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
    "VVIX 日圓投機空頭, 預見突發危機",
    "VVIX, PutCall, 預見突發危機, 並估算反彈",
    "市場寬度",
    "SOFR 預見流動性危機",
    "澳紐元vs.日幣 VIX",
    "信用風險利差 vs S&P500 vs VIX",
    "芝加哥聯儲當週金融狀況指數",
    "日經225 vs Vix",
    "SP500, MOVE and VIX",
    "日圓加幣, vs 油價",
]

# 注意：使用運算式時使用三元組格式 (left_id, operator, right_id)
# 例如：(385, '/', 386) 表示 385 ÷ 386
CHART_IDS = [
    [2, 22904, 355, "jpy_cme_noncommercial_short"],  # SP500, VVIX, VIX, 日圓投機空頭
    [2, 22904, 355, 1650],  # SP500, VVIX, VIX, PutCall
    [2, 18331, 22718, 355],  # 市場寬度
    [2, 40593, 19268, 6222, 6225],  # SP500, ONRRP, IORB, SOFR, SOFR75
    [7145, (7145, '*', 7146), 355, (385, '/', 386)],  # 澳幣日圓, 紐幣日圓, VIX
    [2, 3612, 355],  # 信用風險利差 vs CCC級或以下高收益債券有效殖利率
    [2, 5696],  # 芝加哥聯儲當週金融狀況指數
    [1281, 355],  # 日經225 vs VIX
    [2, 17581, 355],  # SP500, MOVE, VIX
    [486, (385, '/', 386)],  # 日圓加幣 vs 油價
]

AXIS_CONFIG = [
    None,
    None,
    None,
    [0, 1, 1, 1, 1, 1],
    [1, 1, 0, 1, 1, 1],
    None,
    None,  # 芝加哥聯儲當週金融狀況指數
    None,  # 日經225 vs Vix
    None,  # SP500, MOVE and VIX
    None,  # 日圓加幣, vs 油價
]

SUMMARY_LIST = [
    """ 日圓空頭由高點滑落, 且VVIX由底部上升到達100, 強力風險警示!! <br>
    有時VVIX領跑, 如果日圓空頭高位有機會伴隨日圓升值(避險貨幣真義)! """,
    "VVIX 100以上高位就有風險, 如果有日圓空頭下滑更好, 但是PutCall ratio為跟隨信號, 可以觀察極值(>1.2),PutCall下滑,伴隨回檔,當到達0.8一般反彈趨緩!",
    "當50Ma到達25,或200ma到達50,為低點,當50Ma到達75,或200ma到達75,為高點,",
    "當SOFR高於IORB,警示流動性危機, 伴隨短期危機, SOFR75可提前一些",

    "當AUDJPY上行，對應的是波動率下降和低波動率時代，其實就是確定性的增加，<br>"
    "當AUDJPY下行的時候，往往是不確定性的增加，對應的也是高波動率的環境<br>"
    "當CADJPY下行的時候，也類似，但是只有在日圓環流出事時會有問題，如同2024/08 多一個維度是否與日圓環流相關",

    "信用利差到達高點快速下降行為與Vix相似 <br> "
    "信用利差到達高點下降行為通常也象徵市場反轉一般有延續性<br>"
    "但是21年也有提前上升但是股市續漲的場景<br>"
    "信用利差開始上升, 市場要求更多風險溢價，表示市場擔心經濟下行，通常有延續性，此時注意市場下跌<br>",
    '<img src="https://raw.githubusercontent.com/chendoit/PicBed/main/image-20250812220738637.png" alt="圖片描述" style="width:40%; height:auto;" >'
    "有預示能力, 有提早下彎警示下跌的功能, 但是下彎後就沒有意義(like 2024/Aug之後), 但是下彎後改變趨勢, 也可以預示上漲 (每周更新 尚須確認時效性 似乎會有兩周的delay)"
    "NFCI 每週提供有關貨幣市場、債務和股票市場以及傳統和「影子」銀行體系中美國金融狀況的全面更新",
    "一般來說，如果日經指數持續上漲，但波動率拒絕下降時，就需要特別注意。 (日經軸反轉)"
    '<img src="https://raw.githubusercontent.com/chendoit/PicBed/main/image-20250829224909178.png" alt="圖片描述" style="width:40%; height:auto;" >',
    None,  # SP500, MOVE and VIX
    None,  # 日圓加幣, vs 油價
]

# ============================================================
# 配置相關函數
# ============================================================

current_filename = os.path.splitext(os.path.basename(__file__))[0]


def get_chart_title(chart_id_list):
    """根據 chart_id_list 查找對應的圖表標題"""
    try:
        if not chart_id_list:
            print("錯誤：輸入列表為空")
            return '圖表'

        default_title = '圖表'

        for i, chart_ids in enumerate(CHART_IDS):
            if chart_id_list == chart_ids:
                if i < len(CHART_TITLES):
                    if CHART_TITLES[i] is None:
                        return default_title
                    return CHART_TITLES[i]
                else:
                    print(f"錯誤：CHART_TITLES 中找不到索引 {i} 的標題")
                    return default_title

        print("未找到匹配的配置，使用預設標題")
        return default_title

    except Exception as e:
        print(f"發生錯誤：{str(e)}")
        return '圖表'


def get_y_axis_config(chart_id_list):
    """根據 chart_id_list 查找對應的 Y 軸配置"""
    try:
        if not chart_id_list:
            print("錯誤：輸入列表為空")
            return []

        default_config = list(range(len(chart_id_list)))

        for i, chart_ids in enumerate(CHART_IDS):
            if chart_id_list == chart_ids:
                if i < len(AXIS_CONFIG):
                    if AXIS_CONFIG[i] is None:
                        return default_config
                    return AXIS_CONFIG[i]
                else:
                    print(f"錯誤：AXIS_CONFIG 中找不到索引 {i} 的配置")
                    return default_config

        print("未找到匹配的配置，使用預設配置")
        return default_config

    except Exception as e:
        print(f"發生錯誤：{str(e)}")
        return list(range(len(chart_id_list)))


def should_reverse_axis(chart_id_entry):
    """判斷是否需要反向 Y 軸"""
    # 定義需要反向的圖表 ID 列表（此模組特有配置）
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
            # 新格式三元組，檢查運算元
            return chart_id_entry[0] in reverse_ids or chart_id_entry[2] in reverse_ids
        elif len(chart_id_entry) == 1 and isinstance(chart_id_entry[0], str):
            # 舊格式，檢查運算式中的 ID
            chart_ids = [x.strip() for x in chart_id_entry[0].split('-')]
            return any(id in reverse_ids for id in chart_ids)
    elif isinstance(chart_id_entry, list):
        return any(id in reverse_ids for id in chart_id_entry)

    return False


def add_plot_lines(chart_id_list, chart_id_entry, y_axis):
    """為此模組的圖表添加特定的 plot lines（此模組特有配置）"""
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 0, 22904, 100, y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 1, 22904, 100, y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 1, 1650, [1.2, 1, 0.75], y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 2, 18331, [25, 75], y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 2, 22718, [50, 75], y_axis)
    add_plot_line(CHART_IDS, chart_id_list, chart_id_entry, 4, 7145, 95, y_axis)


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
        # 獲取標題
        if is_expression(chart_id_entry):
            data = process_expression(chart_id_entry)
            title = data['title']
        elif isinstance(chart_id_entry, list):
            data = load_series_data(chart_id_entry[0])
            title = current_filename
        else:
            data = load_series_data(chart_id_entry)
            title = data['title']

        # 建立 Y 軸配置
        y_axis = build_y_axis(
            title=title,
            index=i,
            reversed_flag=should_reverse_axis(chart_id_entry)
        )

        # 添加 plot lines
        add_plot_lines(chart_id_list, chart_id_entry, y_axis)

        y_axes.append(y_axis)

    chart_title = get_chart_title(chart_id_list)
    return get_base_chart_config(y_axes, chart_title)
