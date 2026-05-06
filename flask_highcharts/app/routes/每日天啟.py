from app.utils import ChartModule

_VIX_LONG_FLOW = ["etf_UVXY_fundflow", "etf_VIXY_fundflow"]
_VIX_SHORT_FLOW = ["etf_SVXY_fundflow"]

_module = ChartModule(
    filename='每日天啟',
    charts=[
        {
            "title": "VVIX 日圓投機空頭, 預見突發危機",
            "ids": [2, 22904, 355, "jpy_cme_noncommercial_short"],
            "summary": """ 日圓空頭由高點滑落, 且VVIX由底部上升到達100, 強力風險警示!! <br>
    有時VVIX領跑, 如果日圓空頭高位有機會伴隨日圓升值(避險貨幣真義)! """,
            "plot_lines": [(22904, 100)],
        },
        {
            "title": "VVIX, PutCall, 預見突發危機, 並估算反彈",
            "ids": [2, 22904, 355, 1650],
            "summary": "VVIX 100以上高位就有風險, 如果有日圓空頭下滑更好, 但是PutCall ratio為跟隨信號, 可以觀察極值(>1.2),PutCall下滑,伴隨回檔,當到達0.8一般反彈趨緩!",
            "plot_lines": [(22904, 100), (1650, [1.2, 1, 0.75])],
        },
        {
            "title": "市場寬度",
            "ids": [2, 18331, 22718, 355],
            "summary": "當50Ma到達25,或200ma到達50,為低點,當50Ma到達75,或200ma到達75,為高點,",
            "plot_lines": [(18331, [25, 75]), (22718, [50, 75])],
        },
        {
            "title": "SOFR 預見流動性危機",
            "ids": [2, 40593, 19268, 6222, 6225],
            "axis": [0, 1, 1, 1, 1, 1],
            "summary": "當SOFR高於IORB,警示流動性危機, 伴隨短期危機, SOFR75可提前一些",
        },
        {
            "title": "美國OIS隔夜指數掉期3M和1Y",
            "ids": [1150443, 1150441, 354, 5551],
            "axis": [2, 2, 2, 2],
            "summary":
                "USD 1Y FED FUNDS OIS、USD 3M FED FUNDS OIS 與美國 10、20 年期公債殖利率。<br>"
                "1Y和3M OIS利差隱含著對下一步FED行動的押注。",
        },
        {
            "title": "美國OIS利差 1Y-3M FED FUNDS OIS",
            "ids": [2,356, (1150443, '-', 1150441)],
            "axis": [0, 1, 2],
            "summary":
                "USD 1Y FED FUNDS OIS - USD 3M FED FUNDS OIS 利差。<br>"
                "正值代表市場預期未來升息，負值代表預期降息。<br>"
                "超過 +0.25 或低於 -0.25 代表市場高度預期下一步 FED 將行動（100% Price in FED next step）。",
            "plot_lines": [((1150443, '-', 1150441), [0.25, -0.25])],
        },
        {
            "title": "澳紐元vs.日幣 VIX",
            "ids": [7145, (7145, '*', 7146), 355, (385, '/', 386)],
            "axis": [1, 1, 0, 1, 1, 1],
            "summary":
                "當AUDJPY上行，對應的是波動率下降和低波動率時代，其實就是確定性的增加，<br>"
                "當AUDJPY下行的時候，往往是不確定性的增加，對應的也是高波動率的環境<br>"
                "當CADJPY下行的時候，也類似，但是只有在日圓環流出事時會有問題，如同2024/08 多一個維度是否與日圓環流相關",
            "plot_lines": [(7145, 95)],
        },
        {
            "title": "信用風險利差 vs S&P500 vs VIX",
            "ids": [2, 3612, 355],
            "summary":
                "信用利差到達高點快速下降行為與Vix相似 <br> "
                "信用利差到達高點下降行為通常也象徵市場反轉一般有延續性<br>"
                "但是21年也有提前上升但是股市續漲的場景<br>"
                "信用利差開始上升, 市場要求更多風險溢價，表示市場擔心經濟下行，通常有延續性，此時注意市場下跌<br>",
        },
        {
            "title": "芝加哥聯儲當週金融狀況指數 vs 美國金融壓力指數 OFR FSI",
            "ids": [2, 5696, 4866],
            "summary":
                '<img src="https://raw.githubusercontent.com/chendoit/PicBed/main/image-20250812220738637.png" alt="圖片描述" style="width:40%; height:auto;" >'
                "有預示能力, 有提早下彎警示下跌的功能, 但是下彎後就沒有意義(like 2024/Aug之後), 但是下彎後改變趨勢, 也可以預示上漲 (每周更新 尚須確認時效性 似乎會有兩周的delay)"
                "NFCI 每週提供有關貨幣市場、債務和股票市場以及傳統和「影子」銀行體系中美國金融狀況的全面更新",
        },
        {
            "title": "日經225 vs Vix",
            "ids": [1281, 355],
            "summary":
                "一般來說，如果日經指數持續上漲，但波動率拒絕下降時，就需要特別注意。 (日經軸反轉)"
                '<img src="https://raw.githubusercontent.com/chendoit/PicBed/main/image-20250829224909178.png" alt="圖片描述" style="width:40%; height:auto;" >',
        },
        {
            "title": "SP500, MOVE and VIX",
            "ids": [2, 17581, 355],
        },
        {
            "title": "日圓加幣, vs 油價",
            "ids": [486, (385, '/', 386)],
        },
        {
            "title": "SPX vs VIX 期限結構 (raw)",
            "ids": [2, 355, 28769, 7173, 7174, 7175, 7770],
            "axis": [0, 1, 1, 1, 1, 1, 1],
            "summary":
                "SPX 搭配 VIX 各期限原始數值：VIX(30D), VIX1D, VIX9D, VIX3M, VIX6M, VIX1Y。"
                "<br>可觀察各期限 VIX 的絕對水準與相對位置。",
        },
        {
            "title": "SPX vs VIX 期限結構 (ratio)",
            "ids": [2, (355, '/', 7174), (28769, '/', 7175)],
            "axis": [0, 1, 1],
            "summary":
                "VIX/VIX3M：VIX 與 3 個月期 VIX 的比率，衡量短期 vs 中期波動預期。"
                "<br>VIX1D/VIX6M：1 天期 vs 6 個月期比率，對短期恐慌更敏感。"
                "<br><b>&gt;1</b>：期限結構倒掛 (backwardation)，短期恐慌高於中長期 → 市場恐慌。"
                "<br><b>&lt;1</b>：期限結構正常 (contango)，市場穩定。"
                "<br>數值越高代表恐慌越劇烈，歷史上突破 1.5 通常對應重大市場事件。",
            "plot_lines": [((355, '/', 7174), 1)],
        },
        # {
        #     "title": "VIX ETF 淨做多資金流 vs SPX vs VIX",
        #     "ids": [({"SUM": _VIX_LONG_FLOW}, '-', {"SUM": _VIX_SHORT_FLOW}), 2, 355],
        #     "axis": [0, 1, 2],
        #     "summary":
        #         "做多VIX ETF (UVXY+VIXY) 資金淨流量減去做空VIX ETF (SVXY) 資金淨流量。<br>"
        #         "資料來源：ProShares 官方 CSV（每日 Δ Shares Outstanding × NAV）。<br>"
        #         "<b>正值</b>：市場整體偏向買入恐慌避險，資金流入做多VIX產品。<br>"
        #         "<b>負值</b>：市場整體偏向賣出波動率，資金流入做空VIX產品（看好市場）。<br>"
        #         "搭配 SPX 與 VIX 觀察資金流向是否與市場走勢背離。",
        # },
        # {
        #     "title": "VIX ETF 做多/做空資金流 vs SPX vs VIX",
        #     "ids": [{"SUM": _VIX_LONG_FLOW}, {"SUM": _VIX_SHORT_FLOW}, 2, 355],
        #     "axis": [0, 1, 2, 3],
        #     "summary":
        #         "分別顯示做多VIX ETF (UVXY+VIXY) 與做空VIX ETF (SVXY) 的資金流量。<br>"
        #         "資料來源：ProShares 官方 CSV（每日 Δ Shares Outstanding × NAV）。<br>"
        #         "可觀察兩方資金流的各自趨勢與相對強弱，搭配 SPX 與 VIX 判斷市場情緒。",
        # },
        {
            "title": "VIX ETF 正規化淨做多資金流 vs SPX vs VIX",
            "ids": [2, 355, ({"ZSUM": _VIX_LONG_FLOW}, '-', {"ZSUM": _VIX_SHORT_FLOW}) ],
            "axis": [0, 1, 2],
            "summary":
                "各ETF先做Z-score正規化後再加總，避免規模大的ETF主導信號。<br>"
                "邏輯同上，但每個ETF的信號權重相當。<br>"
                "可與原始加總對比，若兩者一致則信號更可靠。",
        },
        {
            "title": "CBOE VIX Futures Index SHORTVOL DD60 vs SPX vs VIX",
            "ids": [2, 355, 5696, "cboe_SHORTVOL", "cboe_SHORTVOL.DD60"],
            "axis": [0, 1, 2, 3, 4],
            "summary":
                "<b>【核心指標：SHORTVOL DD60（綠色虛線）】</b><br>"
                "DD60 = 距 60 日高點的回撤 %，衡量做空波動率策略的虧損深度。<br>"
                "<br>"
                "<b>三個觀察區間：</b><br>"
                "　0% ~ -20%：正常波動，不需行動。<br>"
                "　<b>-20%（黃燈）</b>：市場進入壓力區。78% 的情況會在此止住，僅 22% 繼續惡化到 -40%。<br>"
                "　<b>-40%（紅燈）</b>：極端危機（歷史 Sharpe 最高區間）。SPX 未來 20 天平均 +2.3%、勝率 72%。<br>"
                "<br>"
                "<b>如何判斷底部？</b><br>"
                "　看 DD60 是否<b>止跌回升</b> — 從 -40% 以下開始往上走，代表做空波動率的強制平倉結束，通常對應 SPX 中期底部。<br>"
                "<br>"
                "<b>REV20 翻轉信號</b>：+1 = SHORTVOL 從谷底翻上（危機結束），-1 = SHORTVOL 從峰頂翻下（開始下跌）。<br>"
                "<br>"
                "<b>背景知識：</b><br>"
                "　LONGVOL = 做多 VIX 期貨指數（UVIX 追蹤 2x），SHORTVOL = 做空 VIX 期貨指數（SVIX 追蹤 -1x）。<br>"
                "　SHORTVOL 長期因 contango 上漲（年化 ~36%），急跌代表 VIX 期貨暴漲 → 做空方被迫平倉。",
            "plot_lines": [ ("cboe_SHORTVOL.DD60", [-20, -40])],
        },
        {
            "title": "SPX vs VIX vs NFCI vs NFCI翻轉信號",
            "ids": [2, 355, 5696, "5696.REV1"],
            "axis": [0, 1, 2, 3],
            "summary":
                "SPX 搭配 VIX、芝加哥聯儲 綜合觀察。<br>"
                "NFCI 下彎代表金融環境收緊，搭配 VIX 上升。<br>"
                "<b>REV10 翻轉信號</b>：+1 = NFCI 從谷底翻上（金融環境開始收緊），-1 = NFCI 從峰頂翻下（金融環境開始放鬆）。<br>",
                # "MA10 平滑（週度數據 ≈ 2.5 個月），可換 REV5/REV20 調整靈敏度。"
            "plot_lines": [("5696.REV1", [1, -1])],
        },
        {
            "title": "SPX vs Bitcoin",
            "ids": [2, 4249],
            "axis": [0, 1],
        },
        {
            "title": "歐洲及新興市場 5-Year CDS",
            "ids": [27118, 27119, 27126, 27135, 27129, 27131, 27136, 27138, 27134],
            "visible": [True, True, True, True, False, False, False, True, False],
            "summary":
                "5年期主權CDS利差（BP），數值越高代表市場對該國違約風險評估越高。<br>"
                "義大利與土耳其通常最高，德國最低（避風港）。<br>"
                "CDS 急升通常伴隨歐債/新興市場危機。",
        },
    ],
    reverse_ids=[
        "eur_cme_noncommercial_short",
        "jpy_cme_noncommercial_short",
        5696, "NFCI", 1281, 4866,
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
