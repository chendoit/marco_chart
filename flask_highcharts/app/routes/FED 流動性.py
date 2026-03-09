from app.utils import ChartModule

_module = ChartModule(
    filename='FED 流動性',
    chart_titles=[
        "S&P, ONRRP, IORB, SOFR, FED fund rate, SOFR 75",
        "S&P, SOFR 75, 聖路易斯金融壓力指數, SOFR IORB spread,OFR FSI",
        " 美國國債1年期, 美國國債1年期, SOFR, IORB, 美債波動率, onrrp vol",
    ],
    chart_ids=[
        [2, 40593, 19268, 6222, 356, 6225],
        [2, 6225, 'STLFSI4', (6225, '-', 19268), 4869],
        [5549, 354, 6222, 19268, 17581, 17449],
    ],
    axis_config=[
        [0, 1, 0, 1, 1, 1],
        None,
        [0, 0, 1, 1, 2, 2],
    ],
    summary_list=[
        """當SOFR超過ONRRP, 表示流動性吃緊, 市場可能恐慌下跌!"""
        "比較Fed fune rate 與金融壓力指數",
        "SOFR75 1/22後開始攀升!!",
        "OIS 利率預期。1/30後又開始有降息期望",
        "9/18降息兩碼後,債劵波動性開始攀升,10年公債殖利率升高,流動性開始吃緊。<br>"
        "11/6後債劵下跌,但是公債殖利率不回頭<br>"
        "ONRRP 交易量開始吃緊!!",
    ],
    reverse_ids=[
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
    ],
    plot_lines_config=[
        (0, 8298, 24000),
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
