from app.utils import ChartModule

_module = ChartModule(
    filename='McElligott總經與利率',
    charts=[
        {
            "title": "跨市場壓力指標 — MOVE + VIX + 信用利差",
            "pctrank_id": "series_17581",
            "ids": [2, 17581, 355, 3612],
            "axis": [0, 1, 2, 3],
            "summary":
                "MOVE Index（利率波動率）+ VIX（股票波動率）+ 信用利差。"
                "McElligott 的跨資產傳導鏈：利率 vol 上升 → equity risk premium 壓縮 → "
                "股市更容易回撤 → vol 上升。<br>"
                "當 MOVE 和 VIX 同步飆升 = 利率-股票共振壓力，非單純的 rotation。"
                "信用利差是下游指標：利差快速擴大 = 市場要求更多風險溢價 = 'Growth Scare' 敘事成型。"
                "三者共振 = 系統性壓力最高級別。",
        },
        {
            "title": "金融條件反身性 — NFCI + OFR FSI",
            "ids": [2, 5696, 4866, 355],
            "axis": [0, 1, 1, 2],
            "summary":
                "McElligott 最強的總經概念：FCI 反身性。<br>"
                "邏輯鏈：市場預期 Fed 降息 → FCI 先行放鬆 → 經濟被刺激 → 數據轉好 → "
                "Fed 放慢降息 → FCI 收緊 → 數據轉弱 → 循環重啟。<br>"
                "'FCI Tantrum'：當 Fed 拒絕驗證市場的降息預期，等同 de facto 收緊 FCI。"
                "NFCI（芝加哥聯儲）涵蓋貨幣市場、債務、股票和影子銀行；"
                "OFR FSI（美國金融壓力指數）交叉驗證。NFCI 先行下彎有預示下跌的功能。",
        },
        {
            "title": "美國公債殖利率曲線（含 2Y）",
            "ids": ["cboe_IRX", "fed_DGS2", "cboe_FVX", "cboe_TNX", "cboe_TYX"],
            "axis": [0, 0, 0, 0, 0],
            "summary":
                "13W（IRX）/ 2Y（DGS2, FRED）/ 5Y（FVX）/ 10Y（TNX）/ 30Y（TYX）完整殖利率曲線。"
                "CBOE CDN 無 2Y 指數，故 2Y 改用 FRED DGS2。<br>"
                "McElligott 的 Fed 路徑框架：2Y 對 Fed 路徑重新定價最敏感（CTA 觸發價追蹤 2Y）；"
                "10Y 是成長/通膨的混合晴雨表和跨資產傳導中樞；30Y 受 Term Premium 和財政擔憂主導。<br>"
                "曲線形狀的變化是 CTA 債券部位翻轉的觸發器——"
                "2024/08 期間 CTA 從巨額做空債券轉為巨額做多（+$289B 名義金額），"
                "伴隨著 'Hard Landing' 敘事的成型。",
        },
        {
            "title": "殖利率曲線斜率 + 利率波動率",
            "ids": ["fed_T10Y2Y", "cboe_VXTLT", 2],
            "axis": [0, 1, 2],
            "plot_lines": [("fed_T10Y2Y", 0)],
            "summary":
                "10Y-2Y spread（T10Y2Y）量化殖利率曲線形狀：正值 = 正常（長期 > 短期）；"
                "負值 = 倒掛（衰退預期）。<br>"
                "VXTLT = 20+ 年美債 ETF 波動率，是 McElligott 追蹤的 Rate Vol 代理。"
                "高 VXTLT + T10Y2Y 急速變化 = rates regime change → "
                "CTA 債券部位大規模翻轉 → 跨資產連鎖反應。<br>"
                "2024/04 的 'No Landing' 敘事：Philly Fed 15.5 vs 估計 2.0，"
                "Prices-Paid 23.0 vs 估計 3.7 → T10Y2Y 變動 → CTA 全面做空美債 → equity vol 上升。",
        },
        {
            "title": "10Y 實質殖利率（TIPS） — FCI 收緊代理",
            "pctrank_id": "fed_DFII10",
            "ids": ["fed_DFII10", 2, 355],
            "axis": [0, 1, 2],
            "summary":
                "10Y 實質殖利率（DFII10）是 McElligott 追蹤的 'FCI 收緊代理'。"
                "實質殖利率上升 = 扣除通膨預期後的真正融資成本上升 = 金融條件實質收緊。<br>"
                "McElligott：'我一直主張 Fed 需要對真正的中性利率在哪裡保持誠實，"
                "坦白說可能在 3.5% 到 4.5%+ 之間——我們是否已經到了？'<br>"
                "Term Premium 重建的風險是 '2025 年風險資產的真正總經風險催化劑'。",
        },
        {
            "title": "SOFR 體系 + OIS 利差 — 流動性壓力",
            "ids": [2, "sofr_rate", "sofr_percent75", "sofr_percent99", (1150443, '-', 1150441)],
            "axis": [0, 1, 1, 1, 2],
            "plot_lines": [((1150443, '-', 1150441), [0.25, -0.25])],
            "summary":
                "SOFR（擔保隔夜融資利率）+ 75th/99th 百分位 = 回購市場壓力指標。"
                "SOFR 99th 超過 IORB = 流動性危機信號。<br>"
                "1Y-3M OIS 利差量化市場對 Fed 下一步行動的押注：正值 = 升息預期；"
                "負值 = 降息預期；超過 +/-0.25 = '100% price in Fed next step'。<br>"
                "McElligott 追蹤的 '流動性抽離清單'：TGA rebuild、RRP drain、"
                "bank quarter-end、buyback blackout 都透過 SOFR 體系顯現。",
        },
        {
            "title": "OIS 1Y-3M 利差 vs SPX vs VIX — Fed 路徑定價",
            "ids": [2, 356, (1150443, '-', 1150441)],
            "axis": [0, 1, 2],
            "plot_lines": [((1150443, '-', 1150441), [0.25, -0.25])],
            "summary":
                "1Y-3M OIS 利差的獨立放大圖。"
                "McElligott 的 'Landing' 概率分佈框架：Soft Landing（75-100bps cuts）/ "
                "Hard Landing（175bps+ cuts）/ No Landing（reflation）。<br>"
                "利差的變化（而非水準）驅動 repricing：'shifts in the relative probability of "
                "these scenarios — not the scenarios themselves — drive the market.'<br>"
                "2024/09 利差急速走負 = market pricing 'Left Tail' with real delta → "
                "迫使 Fed 50bps 'statement of intent' cut → 利差反彈 = "
                "'Fear of Left Tail self-fulfills the Right Tail outcome'。",
        },
        {
            "title": "跨資產波動率 — VIX vs VXTLT vs MOVE vs OVX",
            "ids": ["cboe_VIX", "cboe_VXTLT", 17581, 7148],
            "axis": [0, 1, 2, 3],
            "summary":
                "四大資產類別波動率：股票（VIX）vs 債券（VXTLT）vs 利率（MOVE）vs 原油（OVX）。<br>"
                "McElligott 的傳導地圖：Rate Vol 上升 → Equity Risk Premium 壓縮 → Equity Vol 上升；"
                "Commodity Vol 上升 → 通膨預期不穩定 → 利率路徑不確定性增加。<br>"
                "當四者同步處於高位 = '跨資產波動率共振'——幾乎必然伴隨 CTA 大規模倉位調整"
                "（'Economic regime change = Policy regime change = "
                "MAJOR Trend Signal & Positioning Reversal'）。"
                "單一市場 vol spike 通常可被吸收；多市場同步 = 系統性事件。",
        },
        {
            "title": "ACM Term Premium — 2025 年真正的總經風險催化劑",
            "pctrank_id": "series_nyfed_acmtp10",
            "ids": ["nyfed_acmtp02", "nyfed_acmtp05", "nyfed_acmtp10", "THREEFYTP10", 2],
            "axis": [0, 0, 0, 0, 1],
            "plot_lines": [("nyfed_acmtp10", 0)],
            "summary":
                "NY Fed ACM Term Premium（2Y/5Y/10Y）+ FRED Kim-Wright Term Premium（10Y, 交叉驗證）。<br>"
                "McElligott 在文章 07 中明確稱 Term Premium 為 "
                "'2025 年風險資產的真正總經風險催化劑'。<br>"
                "Term Premium = 投資者持有長期債券所要求的超額補償（相對於純利率預期）。"
                "驅動因子：財政赤字敘事（coupon vs bills 供給）、"
                "中立利率不確定性（McElligott 估 3.5%-4.5%+）、'No Landing' 情境。<br>"
                "Term Premium > 0 且上升 = 長端殖利率被結構性推高 = FCI 收緊 = 風險資產壓力。"
                "Term Premium 為負 = 市場願意以折扣持有久期 = 寬鬆信號。<br>"
                "ACM（1961 年起、五因子）vs Kim-Wright（1990 年起、三因子）的差異可揭示模型敏感度。",
        },
        {
            "title": "Money Market Fund AUM — 現金觀望度",
            "ids": [2, "MMMFFAQ027S"],
            "axis": [0, 1],
            "summary":
                "FRED Money Market Funds 總金融資產規模（季度，百萬美元）。<br>"
                "McElligott 追蹤 'MMF AUM 在 90th+ %ile = 大量現金觀望中'——"
                "這是市場 'Dry Powder' 的直接量化。<br>"
                "MMF AUM 持續攀升 = 避險情緒主導、資金從風險資產撤離到安全港。"
                "當 AUM 處於歷史高位且開始下降 = 資金從 MMF 回流到股市/債市 = "
                "'Cash on the Sidelines' 論述的實證基礎。<br>"
                "2024-2025 年 MMF AUM 持續創新高（>$8T），"
                "McElligott 認為這既是潛在的看多催化劑（大量資金等待部署），"
                "也反映了市場對利率路徑的不確定性。",
        },
    ],
    reverse_ids=[5696, 4866],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
