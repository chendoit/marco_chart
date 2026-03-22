from app.utils import ChartModule

_module = ChartModule(
    filename='澳元',
    charts=[
        {
            "title": "澳元CFTC持倉",
            "ids": [745, 'aud_cme_noncommercial_short', "aud_cme_noncommercial_long"],
            "summary": "",
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
