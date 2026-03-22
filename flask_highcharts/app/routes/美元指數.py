from app.utils import ChartModule

_module = ChartModule(
    filename='美元指數',
    charts=[
        {
            "title": "美德利差與DXY",
            "ids": [4448, 562, 483],
            "summary":
                """
    美元指數基本與美德匯差有正向關係<br>
    歐元/美元匯率基本與美德匯差成反向關係<br>
    美德匯差 2.2, 1.1 後反轉, 1.5趨勢確立, 基本是2023年後經驗法則<br>
    這兩年, 美德匯差有提前反應的趨勢, 但是這個指標應該是一個驗證(慢)指標 <br>
    驗證(慢)指標, 用來發現趨勢反轉 反轉後仍可有一個很長趨勢!!<br>
    誰先誰後不重要, 當趨勢不相合時就是要注意的時候 <br>
    美元指數基本與美德利差同向,除了1986-1989布靈頓森林會議,2000後網路泡沫危機,美元為避險貨幣,美元強勢。
    """,
            "plot_lines": [(4448, [1.1, 1.5, 2.2])],
        },
        {
            "title": "日圓/美元, DXY與SOFR IORB spread, 美日利差",
            "ids": [4456, 385, 483, (6225, '-', 19268)],
            "summary":
                "當美日利差小於3就需要注意是否會發生<mark>日圓反轉</mark> <br> "
                "當SOFR75-IORB>0.07 <mark>日圓反轉 DXY反轉 2023Mar, 2023Dec 2024Oct 2024Dec 都有這個趨勢</mark><br> "
                "2024/3月開始 美日匯率與利差背離 就預示了一種趨勢 當反轉到 7/9, <br>"
                "轉成同向,此時持續出現美元流動性不足,這就會出現重大波動"
                "<mark>也就是如果再出現, 日圓持續上漲, 流動性不足 就是一種徵兆!</mark>",
            "plot_lines": [((6225, '-', 19268), 0.07), (4456, 3)],
        },
        {
            "title": "日圓/美元與SOFR IORB spread, 美日利差",
            "ids": [4456, 385, (6225, '-', 19268)],
            "summary":
                "當美日利差小於3就需要注意是否會發生<mark>日圓反轉</mark> <br> "
                "當SOFR75-IORB>0.07 <mark>日圓反轉 DXY反轉 2023Mar, 2023Dec 2024Oct 2024Dec 都有這個趨勢</mark><br> "
                "2024/3月開始 美日匯率與利差背離 就預示了一種趨勢 當反轉到 7/9, <br>"
                "轉成同向,此時持續出現美元流動性不足,這就會出現重大波動"
                "<mark>也就是如果再出現, 日圓持續上漲, 流動性不足 就是一種徵兆!</mark>",
            "plot_lines": [((6225, '-', 19268), 0.07)],
        },
        {
            "title": "日圓/美元與SOFR IORB spread",
            "ids": [(6222, '-', 19268), 385, (6225, '-', 19268)],
            "summary": "單看SOFR7和IORB拉大, 日圓反轉",
        },
        {
            "title": "美日利差與Fedwatch升降息機率",
            "ids": [356, 354, 1645, 484, 4456, 385],
            "axis": [3, 3, 2, 2, 3, 5],
            "summary": "注意升降息, 機率急遽變化",
            "plot_lines": [(4456, 3)],
        },
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
