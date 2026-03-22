from app.utils import ChartModule

_VIX_LONG_FLOW = ["etf_UVXY_fundflow", "etf_VIXY_fundflow"]
_VIX_SHORT_FLOW = ["etf_SVXY_fundflow"]

_module = ChartModule(
    filename='每日天啟',
    chart_titles=[
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
        "SPX vs VIX 期限結構 (raw)",
        "SPX vs VIX 期限結構 (ratio)",
        "VIX ETF 淨做多資金流 vs SPX vs VIX",
        "VIX ETF 正規化淨做多資金流 vs SPX vs VIX",
        "CBOE VIX Futures Index (LONGVOL vs SHORTVOL) vs SPX",
        "SPX vs VIX vs NFCI vs SHORTVOL",
    ],
    chart_ids=[
        [2, 22904, 355, "jpy_cme_noncommercial_short"],
        [2, 22904, 355, 1650],
        [2, 18331, 22718, 355],
        [2, 40593, 19268, 6222, 6225],
        [7145, (7145, '*', 7146), 355, (385, '/', 386)],
        [2, 3612, 355],
        [2, 5696],
        [1281, 355],
        [2, 17581, 355],
        [486, (385, '/', 386)],
        [2, 355, 28769, 7173, 7174, 7175, 7770],
        [2, (355, '/', 7174), (28769, '/', 7175)],
        [({"SUM": _VIX_LONG_FLOW}, '-', {"SUM": _VIX_SHORT_FLOW}), 2, 355],
        [({"ZSUM": _VIX_LONG_FLOW}, '-', {"ZSUM": _VIX_SHORT_FLOW}), 2, 355],
        [2, "cboe_LONGVOL", "cboe_SHORTVOL"],
        [2, 355, 5696, "cboe_SHORTVOL"],
    ],
    axis_config=[
        None,
        None,
        None,
        [0, 1, 1, 1, 1, 1],
        [1, 1, 0, 1, 1, 1],
        None,
        None,
        None,
        None,
        None,
        [0, 1, 1, 1, 1, 1, 1],
        [0, 1, 1],
        [0, 1, 2],
        [0, 1, 2],
        [0, 1, 2],
        [0, 1, 2, 3],
    ],
    summary_list=[
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
        None,
        None,
        "SPX 搭配 VIX 各期限原始數值：VIX(30D), VIX1D, VIX9D, VIX3M, VIX6M, VIX1Y。"
        "<br>可觀察各期限 VIX 的絕對水準與相對位置。",
        "VIX/VIX3M：VIX 與 3 個月期 VIX 的比率，衡量短期 vs 中期波動預期。"
        "<br>VIX1D/VIX6M：1 天期 vs 6 個月期比率，對短期恐慌更敏感。"
        "<br><b>&gt;1</b>：期限結構倒掛 (backwardation)，短期恐慌高於中長期 → 市場恐慌。"
        "<br><b>&lt;1</b>：期限結構正常 (contango)，市場穩定。"
        "<br>數值越高代表恐慌越劇烈，歷史上突破 1.5 通常對應重大市場事件。",
        "做多VIX ETF (UVXY+VIXY) 資金淨流量減去做空VIX ETF (SVXY) 資金淨流量。<br>"
        "資料來源：ProShares 官方 CSV（每日 Δ Shares Outstanding × NAV）。<br>"
        "<b>正值</b>：市場整體偏向買入恐慌避險，資金流入做多VIX產品。<br>"
        "<b>負值</b>：市場整體偏向賣出波動率，資金流入做空VIX產品（看好市場）。<br>"
        "搭配 SPX 與 VIX 觀察資金流向是否與市場走勢背離。",
        "各ETF先做Z-score正規化後再加總，避免規模大的ETF主導信號。<br>"
        "邏輯同上，但每個ETF的信號權重相當。<br>"
        "可與原始加總對比，若兩者一致則信號更可靠。",
        "CBOE LONGVOL：做多 VIX 期貨的指數（UVIX 追蹤 2x LONGVOL）。<br>"
        "CBOE SHORTVOL：做空 VIX 期貨的指數（SVIX 追蹤 -1x SHORTVOL）。<br>"
        "LONGVOL 持續下降反映 VIX 期貨的 contango 成本，SHORTVOL 則持續上升。<br>"
        "觀察 LONGVOL 急升 + SHORTVOL 急跌 = VIX 期貨做多方大量湧入。",
        "SPX 搭配 VIX、芝加哥聯儲 NFCI（反轉軸）、CBOE SHORTVOL 綜合觀察。<br>"
        "NFCI 下彎代表金融環境收緊，搭配 VIX 上升與 SHORTVOL 下跌可確認風險升溫。",
    ],
    reverse_ids=[
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
        5696, "NFCI", 1281,
    ],
    plot_lines_config=[
        (0, 22904, 100),
        (1, 22904, 100),
        (1, 1650, [1.2, 1, 0.75]),
        (2, 18331, [25, 75]),
        (2, 22718, [50, 75]),
        (4, 7145, 95),
        (11, (355, '/', 7174), 1),
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
