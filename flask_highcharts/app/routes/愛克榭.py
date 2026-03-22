from app.utils import ChartModule

_module = ChartModule(
    filename='愛克榭',
    charts=[
        {
            "title": "信用風險利差 vs S&P500 ",
            "ids": [3612, 2],
            "summary":
                "信用利差到達高點快速下降行為與Vix相似 <br> "
                "信用利差到達高點下降行為通常也象徵市場反轉一般有延續性<br>"
                "但是21年也有提前上升但是股市續漲的場景 <br>"
                "信用利差開始上升, 市場要求更多風險溢價，表示市場擔心經濟下行，通常有延續性，此時注意市場下跌",
        },
        {
            "title": "衰退指鰾(同時) vs 原油",
            "ids": [567521, 486],
            "summary": "",
        },
        {
            "title": "衰退指鰾(同時) vs 耐久財新訂單-非國防資本財 (年增率) ",
            "ids": [567521, 319],
            "summary": "耐久財出現二度支出潮,須警覺榮景即將結束",
        },
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
