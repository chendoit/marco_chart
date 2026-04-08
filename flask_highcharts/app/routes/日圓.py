from app.utils import ChartModule

_module = ChartModule(
    filename='日圓',
    charts=[
        {
            "title": "日圓, 投機多空持倉",
            "ids": [385, 4456, 'jpy_cme_noncommercial_long', "jpy_cme_noncommercial_short", "jpy_cme_net_position_large_spec"],
            "summary":
                "CFTC COT 週報（週二截止→週五公布）的大型投機者持倉。<br>"
                "Noncommercial Long/Short 為投機性多空部位，Net Position = Long - Short。<br>"
                "淨持倉極端值（正或負）代表部位擁擠，均值回歸風險高。<br>"
                "搭配美日利差觀察：利差擴大通常伴隨日圓空頭累積（carry trade），利差收窄則觸發空頭回補。",
        },
        {
            "title": "日圓匯率與 CME 未平倉量",
            "ids": [385, 4456, "jpy_cme_open_interest"],
            "summary":
                "日圓期貨 Open Interest 反映市場整體部位規模。<br>"
                "OI 上升 + 日圓貶值 = 新空頭進場（carry trade 累積）；<br>"
                "OI 下降 + 日圓升值 = 部位平倉（carry trade 解除）。<br>"
                "OI 急降通常對應快速去槓桿事件。",
        },
        {
            "title": "日圓投機空頭 vs VIX — 風險預警",
            "ids": [385, "jpy_cme_noncommercial_short", 355],
            "summary":
                "1. 日圓空頭高點向下快速滑落, VIX 隨後升高<br>"
                "2. 或 VIX 先發生危機, 觸發日圓空頭滑落, 引起日圓升值（避險貨幣）<br>"
                "日圓空頭（反轉軸）由高位滑落是系統性風險的領先信號。",
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
        {
            "title": "日圓匯率 vs CME 日頻未平倉量",
            "ids": [385, "cme_daily_6j_xcme_oi"],
            "summary":
                "CME 日頻 OI 比 CFTC 週報更即時，可捕捉週內部位變化拐點。<br>"
                "<b>判讀方式同週頻 OI，但解析度更高：</b><br>"
                "OI 連日攀升 + 日圓貶值 → 新空頭持續進場，carry trade 正在累積；<br>"
                "OI 單日急降 + 日圓升值 → 部位快速平倉，可能是去槓桿事件的早期信號；<br>"
                "OI 上升但匯率不動 → 多空同步增倉，市場對方向分歧加大，留意即將到來的突破。",
        },
        {
            "title": "日圓匯率 vs CME 日頻成交量",
            "ids": [385, "cme_daily_6j_xcme_volume"],
            "summary":
                "日頻成交量反映市場即時關注度與資金活躍程度。<br>"
                "<b>量價配合判讀：</b><br>"
                "放量 + 日圓貶值（USD/JPY↑）→ carry trade 資金湧入，趨勢可能延續；<br>"
                "放量 + 日圓升值（USD/JPY↓）→ 恐慌性平倉或避險買盤，留意反轉風險；<br>"
                "縮量 + 趨勢持續 → 動能減弱，趨勢可能接近尾聲；<br>"
                "Volume spike（量能突然放大 2-3 倍）通常對應重大事件或政策轉折。",
        },
        {
            "title": "CME 日頻 OI vs CFTC 投機淨持倉",
            "ids": ["cme_daily_6j_xcme_oi", "jpy_cme_net_position_large_spec"],
            "axis": [0, 0],
            "summary":
                "日頻 OI 看「何時」部位變化，CFTC 週報看「誰」在動。兩者搭配判讀：<br>"
                "<b>OI 日頻上升 + CFTC 淨空增加</b> → 確認新空頭（投機者）進場；<br>"
                "<b>OI 日頻上升 + CFTC 淨空不變</b> → 商業避險盤活動，非投機驅動；<br>"
                "<b>OI 日頻下降 + CFTC 淨空減少</b> → 投機空頭正在平倉（carry trade 解除）；<br>"
                "<b>OI 日頻下降 + CFTC 淨空不變</b> → 多頭離場，投機空頭維持但市場縮量。<br>"
                "注意：CFTC 資料延遲約 3 天（週二截止→週五公布），日頻 OI 可提前捕捉變化方向。",
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
