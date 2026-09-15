from app.utils import ChartModule

_module = ChartModule(
    filename='FED 流動性',
    charts=[
        {
            "title": "S&P, ONRRP, IORB, SOFR, FED fund rate, SOFR 75",
            "ids": [2, "fed_RRPONTSYAWARD", "fed_IORB", "sofr_rate", "fed_DFF", "sofr_percent75"],
            "axis": [0, 1, 0, 1, 1, 1],
            "summary":
                """當SOFR超過ONRRP, 表示流動性吃緊, 市場可能恐慌下跌!"""
                "比較Fed fune rate 與金融壓力指數",
            "plot_lines": [(8298, 24000)],
        },
        {
            "title": "S&P, SOFR 75, 聖路易斯金融壓力指數, SOFR IORB spread,OFR FSI",
            "ids": [2, "sofr_percent75", 'STLFSI4', ("sofr_percent75", '-', "fed_IORB"), 4869],
            "summary": "SOFR75 1/22後開始攀升!!",
        },
        {
            "title": " 美國國債1年期, 美國國債1年期, SOFR, IORB, 美債波動率, onrrp vol",
            "ids": ["fed_DGS1", "fed_DGS10", "sofr_rate", "fed_IORB", 17581, "fed_RRPONTSYD"],
            "axis": [0, 0, 1, 1, 2, 2],
            "summary":
                "OIS 利率預期。1/30後又開始有降息期望",
        },
    ],
    reverse_ids=[
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
