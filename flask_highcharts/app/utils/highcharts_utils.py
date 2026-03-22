"""
Highcharts Utility Functions
共用的圖表處理函數，供所有 route 模組使用
"""
import os
import re
import pickle
import numpy as np
import pandas as pd

# 顏色列表常數
colors = [
    "rgba(75, 192, 192, 1)",   # 藍綠色
    "rgba(192, 75, 75, 1)",    # 紅色
    "rgba(255, 215, 0, 1)",    # 金色
    "rgba(0, 128, 0, 1)",      # 綠色
    "rgba(128, 0, 128, 1)",    # 紫色
    "rgba(0, 0, 255, 1)",      # 藍色
    "rgba(255, 165, 0, 1)",    # 橘色
    "rgba(139, 69, 19, 1)",    # 棕色
    "rgba(255, 0, 0, 1)",      # 大紅色
    "rgba(0, 255, 255, 1)",    # 青色
]


_series_cache = {}


def clear_series_cache():
    _series_cache.clear()


def load_series_data(chart_id, category=None):
    """Load series data from the pickle file(s) that contain the chart_id in their filename.
    If multiple files are found, further filter by the category if provided.
    Results are cached in memory to avoid redundant disk I/O.
    """
    cache_key = (chart_id, category)
    if cache_key in _series_cache:
        return _series_cache[cache_key]

    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
    escaped_id = re.escape(str(chart_id))
    pattern = re.compile(rf'(?:^|_){escaped_id}\.pkl$')
    matching_files = [f for f in os.listdir(data_dir) if pattern.search(f)]
    matching_files.sort(key=len)

    if not matching_files:
        raise FileNotFoundError(f"No files containing 'series_{chart_id}' found in {data_dir}")

    if category:
        matching_files = [f for f in matching_files if category in f]
        if not matching_files:
            raise FileNotFoundError(
                f"No files containing 'series_{chart_id}' and category '{category}' found in {data_dir}")

    file_path = os.path.join(data_dir, matching_files[0])
    with open(file_path, 'rb') as f:
        data = pickle.load(f)

    _series_cache[cache_key] = data
    return data


def _parse_op_string(op_string, operators):
    """從運算式字串（如 "385/386"）解析出 id1, operator, id2。"""
    op = None
    for operator in operators:
        if operator in op_string:
            op = operator
            break
    if op is None:
        raise ValueError(f"不支援的運算: {op_string}")
    parts = op_string.split(op)
    try:
        return int(parts[0]), op, int(parts[1])
    except (ValueError, IndexError):
        raise ValueError(f"無法將操作字符串的部分轉換為整數: {op_string}")


def process_expression(expr):
    """處理運算式，返回處理後的數據

    支援兩種格式：
    1. 三元組格式（新）: (left_id, operator, right_id) 例如 (385, '/', 386)
    2. 字串格式（舊，向後相容）: ("385/386",) 或 "385/386"

    支援的運算符：+, -, *, /
    """
    operators = {
        '-': lambda x, y: x - y,
        '+': lambda x, y: x + y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y
    }
    operator_symbols = {'-': '-', '+': '+', '*': '×', '/': '÷'}

    if isinstance(expr, tuple) and len(expr) == 3:
        id1, op, id2 = expr
        if op not in operators:
            raise ValueError(f"不支援的運算符: {op}")
    elif isinstance(expr, tuple) and len(expr) == 1 and isinstance(expr[0], str):
        id1, op, id2 = _parse_op_string(expr[0], operators)
    elif isinstance(expr, str):
        id1, op, id2 = _parse_op_string(expr, operators)
    else:
        raise ValueError(f"不支援的運算式格式: {expr}")

    data1 = _resolve_operand(id1)
    data2 = _resolve_operand(id2)

    df1 = pd.DataFrame(data1['data'], columns=['Date', 'Value'])
    df2 = pd.DataFrame(data2['data'], columns=['Date', 'Value'])
    df1['Date'] = pd.to_datetime(df1['Date'])
    df2['Date'] = pd.to_datetime(df2['Date'])
    df1.set_index('Date', inplace=True)
    df2.set_index('Date', inplace=True)

    df = df1.join(df2, lsuffix='_1', rsuffix='_2', how='inner')
    df['Value'] = operators[op](df['Value_1'], df['Value_2'])

    return {
        'data': df.reset_index()[['Date', 'Value']].values.tolist(),
        'title': f"{data1['title']} {operator_symbols[op]} {data2['title']}"
    }


def is_aggregate_expression(chart_id):
    """判斷是否為聚合運算式 {"SUM": [...]} 或 {"ZSUM": [...]}"""
    return isinstance(chart_id, dict) and any(k in chart_id for k in ('SUM', 'ZSUM'))


def process_aggregate(expr):
    """處理聚合運算式 SUM / ZSUM

    SUM:  載入多個 series 按日期 inner join 後逐日加總
    ZSUM: 各 series 先做 Z-score 正規化再逐日加總

    Parameters:
    expr: {"SUM": [id1, id2, ...]} 或 {"ZSUM": [id1, id2, ...]}

    Returns:
    dict: {'data': [[date, value], ...], 'title': str}
    """
    if 'SUM' in expr:
        mode, ids = 'SUM', expr['SUM']
    else:
        mode, ids = 'ZSUM', expr['ZSUM']

    frames = []
    titles = []
    for sid in ids:
        data = load_series_data(sid)
        titles.append(data['title'])
        df = pd.DataFrame(data['data'], columns=['Date', 'Value'])
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.set_index('Date').sort_index()
        frames.append(df)

    combined = frames[0].copy()
    combined.columns = ['V0']
    for i, df in enumerate(frames[1:], 1):
        df = df.copy()
        df.columns = [f'V{i}']
        combined = combined.join(df, how='inner')

    if mode == 'ZSUM':
        for col in combined.columns:
            mean = combined[col].mean()
            std = combined[col].std()
            if std > 0:
                combined[col] = (combined[col] - mean) / std
            else:
                combined[col] = 0.0

    combined['Total'] = combined.sum(axis=1)

    prefix = 'Σz' if mode == 'ZSUM' else 'Σ'
    title = f"{prefix}({', '.join(titles)})"

    return {
        'data': combined.reset_index()[['Date', 'Total']].rename(
            columns={'Total': 'Value'}).values.tolist(),
        'title': title,
    }


def _resolve_operand(operand):
    """解析運算式的操作元，支援 int/str（一般 series）和 dict（聚合運算式）。"""
    if is_aggregate_expression(operand):
        return process_aggregate(operand)
    return load_series_data(operand)


def add_plot_line(chart_ids, chart_id_list, chart_id_entry, chart_ids_index, target_chart_id, plot_values, y_axis):
    """
    為指定的 y_axis 添加多條 plot lines

    Parameters:
    chart_ids (list): 完整的 CHART_IDS 配置列表
    chart_id_list (list): 當前的圖表 ID 列表
    chart_id_entry: 當前處理的圖表 ID
    chart_ids_index (int): CHART_IDS 中的索引位置
    target_chart_id: 要添加 plot line 的圖表 ID
    plot_values (float or list): plot line 的值，可以是單一值或值的列表
    y_axis (dict): 要添加 plot line 的 y 軸配置

    Returns:
    dict: 更新後的 y_axis 配置
    """
    # 獲取目標圖表組
    if chart_ids_index >= len(chart_ids):
        return y_axis
        
    chart_group = chart_ids[chart_ids_index]

    if chart_id_list != chart_group:
        return y_axis

    if chart_id_entry != target_chart_id:
        return y_axis

    # 找出目標圖表在組內的位置
    try:
        target_index = chart_group.index(target_chart_id)
    except ValueError:
        print(f"Chart ID {target_chart_id} not found in CHART_IDS[{chart_ids_index}]")
        return y_axis

    # 確保 plot_values 是列表
    if not isinstance(plot_values, list):
        plot_values = [plot_values]

    # 使用相同的顏色邏輯
    color = colors[target_index % len(colors)]

    # 為每個值創建 plot line
    plot_lines = [{
        'value': value,
        'color': color,
        'dashStyle': 'shortdash',
        'width': 3,
        'label': {
            'text': str(value),
            'align': 'right',
            'style': {
                'color': color
            }
        }
    } for value in plot_values]

    # 直接添加 plot lines 到 y_axis
    y_axis['plotLines'] = plot_lines

    return y_axis


def is_yoy_expression(chart_id):
    """判斷是否為 YOY (Year over Year) 年增率格式
    
    支援格式: "17586.YOY" 或 "17586.yoy"
    """
    if isinstance(chart_id, str) and '.YOY' in chart_id.upper():
        return True
    return False


def is_ma_expression(chart_id):
    """判斷是否為 MA (Moving Average) 移動平均線格式
    
    支援格式: "6785.MA20" 表示 20 期移動平均線
    """
    if isinstance(chart_id, str) and re.search(r'\.MA\d+', chart_id.upper()):
        return True
    return False


def process_ma(expr):
    """處理 MA (Moving Average) 移動平均線計算
    
    Parameters:
    expr: 格式為 "series_id.MAn"，例如 "6785.MA20" 表示 20 期移動平均
    
    Returns:
    dict: 包含 'data' 和 'title' 的字典
    """
    match = re.match(r'(\d+)\.MA(\d+)', expr.upper())
    if not match:
        raise ValueError(f"無效的 MA 格式: {expr}")
    
    series_id = int(match.group(1))
    periods = int(match.group(2))
    
    # 載入原始數據
    data = load_series_data(series_id)
    
    # 轉換為 DataFrame
    df = pd.DataFrame(data['data'], columns=['Date', 'Value'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').set_index('Date')
    
    # 計算移動平均
    df['Value_MA'] = df['Value'].rolling(window=periods).mean()
    
    # 移除 NaN 值
    df = df.dropna(subset=['Value_MA'])
    
    # 構建結果
    result = {
        'data': [[idx, row['Value_MA']] for idx, row in df.iterrows()],
        'title': f"{data['title']} MA{periods}"
    }
    return result


def process_yoy(expr):
    """處理 YOY (Year over Year) 年增率計算
    
    YOY = (當期值 - 去年同期值) / 去年同期值 * 100
    
    Parameters:
    expr: 格式為 "series_id.YOY"，例如 "17586.YOY"
    
    Returns:
    dict: 包含 'data' 和 'title' 的字典
    """
    # 解析 series_id
    parts = expr.upper().split('.YOY')
    series_id = int(parts[0])
    
    # 載入原始數據
    data = load_series_data(series_id)
    
    # 轉換為 DataFrame
    df = pd.DataFrame(data['data'], columns=['Date', 'Value'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').set_index('Date')
    
    # 自動偵測數據頻率並計算 YOY
    # 根據平均間隔天數判斷頻率
    if len(df) >= 2:
        avg_days = (df.index[-1] - df.index[0]).days / (len(df) - 1)
        if avg_days > 300:  # 年度數據 (~365天)
            periods = 1
        elif avg_days > 80:  # 季度數據 (~90天)
            periods = 4
        else:  # 月度數據 (~30天)
            periods = 12
    else:
        periods = 12  # 預設月度
    
    # 計算 YOY：與去年同期比較
    df['Value_YOY'] = df['Value'].pct_change(periods=periods) * 100
    
    # 移除 NaN 值
    df = df.dropna(subset=['Value_YOY'])
    
    # 構建結果
    result = {
        'data': [[idx, row['Value_YOY']] for idx, row in df.iterrows()],
        'title': f"{data['title']} YOY%"
    }
    return result


def is_expression(chart_id):
    """判斷是否為運算式（含聚合運算式間的二元運算）"""
    if isinstance(chart_id, tuple):
        if len(chart_id) == 3:
            return True
        if len(chart_id) == 1 and isinstance(chart_id[0], str):
            return True
    elif isinstance(chart_id, str) and any(op in chart_id for op in ['+', '-', '*', '/']):
        return True
    return False


def generate_chart_data(chart_id_entry, get_y_axis_config_func, months=600):
    """生成圖表數據
    
    Parameters:
    chart_id_entry: 圖表 ID 配置（可以是 list, str, int, tuple）
    get_y_axis_config_func: 獲取 Y 軸配置的函數
    months: 要顯示的月份數
    """
    chart_data = {"series": []}

    # 處理新舊格式
    if isinstance(chart_id_entry, (list, str, int, tuple)):
        chart_id_list = chart_id_entry if isinstance(chart_id_entry, list) else [chart_id_entry]
    else:
        chart_id_list = chart_id_entry['charts'] if isinstance(chart_id_entry['charts'], list) else [
            chart_id_entry['charts']]

    for i, chart_id in enumerate(chart_id_list):
        # 處理聚合運算式 {"SUM": [...]} / {"ZSUM": [...]}
        if is_aggregate_expression(chart_id):
            data = process_aggregate(chart_id)
        # 處理 YOY 年增率
        elif is_yoy_expression(chart_id):
            data = process_yoy(chart_id)
        # 處理 MA 移動平均線
        elif is_ma_expression(chart_id):
            data = process_ma(chart_id)
        # 處理運算式
        elif is_expression(chart_id):
            data = process_expression(chart_id)
        else:
            data = load_series_data(chart_id)

        # 數據處理邏輯
        df = pd.DataFrame(data['data'], columns=['Date', 'Value'])
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).set_index('Date').sort_index()

        max_date = df.index.max()
        if not months:
            min_date = df.index.min()
        else:
            min_date = max_date - pd.DateOffset(months=months)
        df = df[df.index >= min_date]

        biz_dates = pd.date_range(start=df.index.min(), end=df.index.max(), freq='B')
        all_dates = biz_dates.union(df.index)
        df_filled = df.reindex(all_dates)
        df_filled['Value'] = df_filled['Value'].interpolate(method='linear')

        data_dict = df_filled[['Value']].to_dict(orient='index')
        # 過濾掉 NaN 值，避免 JSON 解析錯誤
        data_dict = {str(k.date()): v['Value'] for k, v in data_dict.items() if pd.notna(v['Value'])}

        color = colors[i % len(colors)]

        # 根據 y_axis_config 設定 yAxis
        y_axis_config = get_y_axis_config_func(chart_id_list)
        y_axis = y_axis_config[i]

        chart_data["series"].append({
            "name": data['title'],
            "data": data_dict,
            "yAxis": y_axis,
            "color": color,
            "visible": True
        })

    return chart_data


def get_base_chart_config(y_axes, chart_title):
    """生成基礎 Highcharts 配置
    
    Parameters:
    y_axes: Y 軸配置列表
    chart_title: 圖表標題
    """
    return {
        "chart": {
            "type": "line",
            "zoomType": "x"
        },
        "title": {"text": chart_title},
        "xAxis": {
            "type": "datetime",
            "range": 6 * 30 * 24 * 3600 * 1000,
        },
        "yAxis": y_axes,
        "tooltip": {
            "valueDecimals": 2,
            "shared": True
        },
        "legend": {
            "enabled": True,
            "layout": "horizontal",
            "align": "center",
            "verticalAlign": "bottom",
            "borderWidth": 0,
            "itemStyle": {
                "fontWeight": "normal"
            },
            "itemHoverStyle": {
                "color": "#666666"
            }
        },
        "plotOptions": {
            "series": {
                "showInLegend": True,
                "events": {
                    "legendItemClick": None
                }
            }
        },
        "rangeSelector": {
            "enabled": True,
            "buttons": [
                {"type": "month", "count": 2, "text": "2m"},
                {"type": "month", "count": 6, "text": "6m"},
                {"type": "year", "count": 1, "text": "1y"},
                {"type": "year", "count": 2, "text": "2y"},
                {"type": "all", "text": "Max"}
            ],
            "selected": 3
        },
        "navigator": {"enabled": True},
        "scrollbar": {"enabled": True},
        "series": []
    }


def build_y_axis(title, index, reversed_flag=False, plot_lines=None):
    """建立 Y 軸配置
    
    Parameters:
    title: Y 軸標題
    index: Y 軸索引（用於決定 opposite）
    reversed_flag: 是否反向顯示
    plot_lines: plot line 配置列表
    """
    y_axis = {
        "title": {"text": title},
        "opposite": index > 0,
        "labels": {
            "format": "{value}",
            "enabled": True
        },
        "gridLineWidth": 1,
        "showEmpty": False,
        "min": None,
        "max": None,
        "startOnTick": True,
        "endOnTick": True
    }
    
    if reversed_flag:
        y_axis["reversed"] = True
        
    if plot_lines:
        y_axis["plotLines"] = plot_lines
        
    return y_axis


# ============================================================
# ChartModule — 宣告式圖表群組模組
# ============================================================

def resolve_series_title(chart_id_entry, fallback_title=''):
    """根據單一 series entry 取得顯示標題。"""
    if is_aggregate_expression(chart_id_entry):
        return process_aggregate(chart_id_entry)['title']
    if is_yoy_expression(chart_id_entry):
        return process_yoy(chart_id_entry)['title']
    if is_ma_expression(chart_id_entry):
        return process_ma(chart_id_entry)['title']
    if is_expression(chart_id_entry):
        return process_expression(chart_id_entry)['title']
    if isinstance(chart_id_entry, list):
        return fallback_title
    data = load_series_data(chart_id_entry)
    return data.get('title', fallback_title)


class ChartModule:
    """宣告式圖表群組配置。

    將 route 模組的重複邏輯統一於此，各模組只需傳入資料常數：
      chart_ids, summary_list, chart_titles, axis_config,
      reverse_ids, plot_lines_config, range_selector_override, filename
    """

    def __init__(self, *, chart_ids, summary_list, chart_titles=None,
                 axis_config=None, reverse_ids=None, plot_lines_config=None,
                 range_selector_override=None, filename=''):
        self.CHART_IDS = chart_ids
        self.SUMMARY_LIST = summary_list
        self._chart_titles = chart_titles or []
        self._axis_config = axis_config or []
        self._reverse_ids = reverse_ids or []
        self._plot_lines_config = plot_lines_config or []
        self._range_selector_override = range_selector_override
        self._filename = filename

    # -- 標題查詢 --
    def get_chart_title(self, chart_id_list):
        for i, ids in enumerate(self.CHART_IDS):
            if chart_id_list == ids:
                if i < len(self._chart_titles) and self._chart_titles[i] is not None:
                    return self._chart_titles[i]
                return '圖表'
        return '圖表'

    # -- Y 軸分配 --
    def get_y_axis_config(self, chart_id_list):
        default = list(range(len(chart_id_list)))
        for i, ids in enumerate(self.CHART_IDS):
            if chart_id_list == ids:
                if i < len(self._axis_config) and self._axis_config[i] is not None:
                    return self._axis_config[i]
                return default
        return default

    # -- 反向 Y 軸 --
    def should_reverse_axis(self, chart_id_entry):
        if not self._reverse_ids:
            return False
        if isinstance(chart_id_entry, (str, int)):
            return chart_id_entry in self._reverse_ids
        if isinstance(chart_id_entry, tuple) and len(chart_id_entry) == 3:
            return (chart_id_entry[0] in self._reverse_ids
                    or chart_id_entry[2] in self._reverse_ids)
        if isinstance(chart_id_entry, list):
            return any(cid in self._reverse_ids for cid in chart_id_entry)
        return False

    # -- Plot lines --
    def _apply_plot_lines(self, chart_id_list, chart_id_entry, y_axis):
        for group_idx, target_id, values in self._plot_lines_config:
            add_plot_line(self.CHART_IDS, chart_id_list, chart_id_entry,
                          group_idx, target_id, values, y_axis)

    # -- 生成圖表資料 --
    def generate_chart_data(self, chart_id_entry, months=600):
        return generate_chart_data(chart_id_entry, self.get_y_axis_config, months)

    # -- 生成 Highcharts 配置 --
    def get_chart_config(self, chart_id_list):
        y_axes = []
        for i, entry in enumerate(chart_id_list):
            title = resolve_series_title(entry, self._filename)
            y_axis = build_y_axis(
                title=title, index=i,
                reversed_flag=self.should_reverse_axis(entry),
            )
            self._apply_plot_lines(chart_id_list, entry, y_axis)
            y_axes.append(y_axis)

        config = get_base_chart_config(y_axes, self.get_chart_title(chart_id_list))
        if self._range_selector_override:
            rs = config["rangeSelector"]
            if "extra_buttons" in self._range_selector_override:
                rs["buttons"].extend(self._range_selector_override["extra_buttons"])
            if "selected" in self._range_selector_override:
                rs["selected"] = self._range_selector_override["selected"]
        return config


