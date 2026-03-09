from app.utils import ChartModule

_module = ChartModule(
    filename='台幣台股',
    chart_titles=[
        "半導體產值年增率 vs 台股PE",
        "半導體產值年增率 vs 台幣匯率",
    ],
    chart_ids=[
        [2756, 5683],
        [2756, 621],
        [2756, 5683, 621],
    ],
    summary_list=[
        "台股PE 高點領先 半導體年增率 2-3Q (訂單在談 PE就開始漲)",
        "半導體年增率 領先台股匯率 2-3Q (美元匯回台灣 台幣就高) 不過這點 目前好像沒有生效 ",
    ],
    reverse_ids=[621],
    range_selector_override={
        "extra_buttons": [{"type": "year", "count": 15, "text": "15y"}],
        "selected": 4,
    },
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
