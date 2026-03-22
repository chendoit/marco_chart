from app.utils import ChartModule

_module = ChartModule(
    filename='黃金',
    charts=[
        {
            "title": "黃金 GVZ vs 黃金",
            "ids": [7147, 485],
            "summary":
                """ 之前的低波動率、橫盤震盪收斂三角形末端，我們採用了「夾板」的 straddle 策略來捕捉波動率的放大。一般投資者當時也可以透過「多空雙開（破位平一腿）」的方式來獲取相應收益。價格加速上行的背後，其實也是波動率持續擴大走高的結果。
        <br> 策略：「Staddle」（跨式策略）或「多空雙開」是一種選擇權或期貨的交易策略。它的核心邏輯是，當你預期市場將有大波動，但不確定是向上還是向下的時候，你可以同時建立多頭和空頭部位。
        <br> 執行：當價格最終選擇方向（例如圖中的向上突破）時，平掉虧損的那一邊（空頭部位），保留盈利的那一邊（多頭部位），從而抓住價格大幅波動帶來的利潤。這就是文中「破位平一腿」的意思。
        <br>
        <br>現在則應該思考在高波動的情況下該怎麼操作。高波動意味著成本上升，因此應該以落袋為安為主，接著觀察市場走勢。
        <br>如果市場繼續橫盤、波動率下降，那仍然屬於上行趨勢的特徵，可能還會有下一次低波動再啟動的機會。
        <br>但若波動率很高、調整劇烈，且波動率沒有下降，則要留意是否出現趨勢轉向的波動率特徵。
    '<img src="https://raw.githubusercontent.com/chendoit/PicBed/main/image-20251018162303929.png" alt="黃金波動率" style="width:40%; height:auto;" >'
        <br> 當波動率放大伴隨價格向下突破，隨後轉為低波動率陰跌，可視為熊市特徵。
-       <br> 當波動率放大推動價格向上突破，隨後進入低波動率緩漲階段，可視為牛市特徵。""",
        },
    ],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
