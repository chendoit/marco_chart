from app.utils import ChartModule

_module = ChartModule(
    filename='日圓',
    charts=[
        {
            "title": "日圓, 投機多空持倉",
            "ids": [385, 4456, 'jpy_cme_noncommercial_long', "jpy_cme_noncommercial_short"],
            "summary": "",
        },
        {
            "title": "日圓, VIX, SP500共振",
            "ids": [385, 2, 355],
            "summary": "",
        },
        {
            "title": "日圓匯率 vs 日圓波動率",
            "ids": [385, 32377],
            "summary":
                "USD/JPY 與 JPY VIX 呈負相關：日圓貶值(USD/JPY↑)時波動率低，carry trade環境穩定；<br>"
                "日圓急升(USD/JPY↓)時 JPY VIX 飆升，反映避險需求與carry trade平倉潮。<br>"
                "<b>關鍵觀察：JPY VIX 頂點領先 USD/JPY 低點</b> — 波動率先反映市場恐慌與避險預期升溫，匯率隨後跟跌。<br>"
                "JPY VIX 從低檔急升突破12-14 → 警示日圓急速升值風險；<br>"
                "JPY VIX 持續低檔(8以下) → carry trade環境良好，但需留意波動率壓縮後的反撲",
        },
        {
            "title": "澳幣日圓, 紐幣日圓, VIX",
            "ids": [7145, (7145, '/', 7146), 355],
            "axis": [0, 0, 1],
            "summary":
                "當AUDJPY上行，對應的是波動率下降和低波動率時代，其實就是確定性的增加，<br>"
                "當AUDJPY下行的時候，往往是不確定性的增加，對應的也是高波動率的環境",
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
