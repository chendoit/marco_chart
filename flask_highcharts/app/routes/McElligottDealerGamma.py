from app.utils import ChartModule

_module = ChartModule(
    filename='McElligottDealerGamma',
    charts=[
        {
            "title": "SPX Gamma Flip Level vs SPX Price vs VIX",
            "ids": ["gex_spx_spot_price", "gex_spx_gamma_flip", "gex_spx_gamma_flip_ce", 355],
            "axis": [0, 0, 0, 1],
            "summary":
                "McElligott 追蹤的最重要單一水準：SPX Gamma Flip Level。<br>"
                "SPX 在 Flip 上方 = Dealer Long Gamma → 交易商買跌賣漲（'shock absorber'、均值回歸力量）"
                "→ realized vol 被壓縮 → Vol Control 機械式買入 → 良性循環。<br>"
                "SPX 跌破 Flip = Dealer Short Gamma → 交易商賣跌買漲（'accelerant'、動量放大力量）"
                "→ realized vol 爆發 → 強制賣出級聯。<br>"
                "2024/08/05 SPX 跌穿 Flip，dealer 進入 '-$2B per 1% move' 的 Short Gamma → "
                "'dreaded accelerant flow which could feed more overshoot'。"
                "CE = Conditional Expectation，更精確的估計。資料從 2024-08 起（~420 天）。",
        },
        {
            "title": "SPX Gamma 完整結構圖 — Tactical Map",
            "ids": ["gex_spx_spot_price", "gex_spx_gamma_flip_ce", "gex_spx_call_wall_ce",
                    "gex_spx_put_wall_ce", "gex_spx_gamma_field_ce"],
            "axis": [0, 0, 0, 0, 0],
            "summary":
                "McElligott 提供的 'SPX 完整戰術地形圖'：<br>"
                "Gamma Flip（體制翻轉位）、Call Wall（上方最大 Gamma 集中點 = 'pinning' 阻力）、"
                "Put Wall（下方最大 Gamma 集中點 = 加速支撐位）、Gamma Field（Gamma 引力場中心）。<br>"
                "SPX 在 Call Wall 和 Put Wall 之間 = 穩定 'pocket'；"
                "突破 Call Wall = 可能觸發上方 Short Gamma 加速帶"
                "（'Right-Tail Hedges / Upside Short Gamma accelerant'）；"
                "跌破 Put Wall = 下行加速。<br>"
                "'Dealer gamma is not uniformly distributed — it concentrates at specific levels, "
                "creating zones.'（2024/11）",
        },
        {
            "title": "SPY Gamma Flip Level vs SPY Price — ETF 級對照",
            "ids": ["gex_spy_spot_price", "gex_spy_gamma_flip", "gex_spy_gamma_flip_ce", 355],
            "axis": [0, 0, 0, 1],
            "summary":
                "SPY（ETF）的 Gamma Flip Level，與 SPX（指數）互為對照。"
                "SPY 資料從 2024-07-25 起（425 天），比 SPX 早 7 天，提供更長的歷史回看。<br>"
                "SPY 是全球交易量最大的 ETF，其選擇權市場有獨立於 SPX 的 dealer gamma 結構。"
                "McElligott 雖主要引用 SPX，但 SPY 的 gamma 結構同樣影響市場微結構——"
                "特別是 0DTE SPY 選擇權的爆炸式增長使 SPY dealer gamma 成為不可忽視的力量。<br>"
                "兩者的 Gamma Flip 位置通常接近（按比例換算），但偶爾出現偏差時可揭示選擇權市場的分歧。",
        },
        {
            "title": "SPX Gamma Environment 體制 vs VIX vs VVIX",
            "ids": ["gex_spx_spot_price", "gex_spx_gamma_env", 355, 22904],
            "axis": [0, 1, 2, 3],
            "summary":
                "SPX Gamma Environment 二元體制指標：+1 = Positive Gamma（穩定器），"
                "-1 = Negative Gamma（加速器）。<br>"
                "良性循環全程在 Positive Gamma 中運作：'Vega Supply = Dealer Long Gamma = "
                "Crunched Realized Vol = Vol Control Buying'。<br>"
                "惡性循環始於翻轉至 Negative Gamma：'SPX 跌穿 Gamma Flip → Dealer Short Gamma → "
                "加速賣壓 → Vol 爆發 → Vol Control 強制賣出 → CTA 趨勢翻空 → 槓桿 ETF EOD 再平衡賣出'。<br>"
                "搭配 VIX/VVIX 觀察：Positive Gamma + VIX 低位 + VVIX 穩定 = 安全；"
                "Negative Gamma + VIX 上升 + VVIX 飆升 = 最大危險。",
        },
        {
            "title": "VIX Gamma Flip Level vs VIX Price — VIX Dealer Gamma",
            "ids": ["gex_vix_spot_price", "gex_vix_gamma_flip", "gex_vix_gamma_flip_ce", 2],
            "axis": [0, 0, 0, 1],
            "summary":
                "McElligott 在文章 01 明確區分的 'VIX Aggregate Dealer Gamma'。"
                "VIX 有自己獨立的 dealer gamma 結構，與 SPX dealer gamma 形成雙層系統。<br>"
                "VIX 在其 Gamma Flip 下方 = VIX dealer short gamma = "
                "VIX spike 會自我加速（dealer 被迫買入 VIX 期貨避險 → 推高 VIX → 更多強制買入）。<br>"
                "McElligott 的 'VIX Option Dealer Vega Rebalance Projection' 案例："
                "VIX 從 14→20 時 ETN 須買 +48.1M Vega，VIX→25 時須 +76.1M Vega——"
                "'these hedge/rebalancing flows in the VIX space have had a historical tendency "
                "to self-fulfill thereafter'。<br>"
                "VIX 在 Flip 上方 = VIX 受壓制 = 有利於做空波動率。資料 427 天（2024-07-25~）。",
        },
        {
            "title": "VIX Gamma 完整結構圖 — VIX Tactical Map",
            "ids": ["gex_vix_spot_price", "gex_vix_gamma_flip_ce", "gex_vix_call_wall_ce",
                    "gex_vix_put_wall_ce", "gex_vix_gamma_field_ce"],
            "axis": [0, 0, 0, 0, 0],
            "summary":
                "VIX 的完整 gamma 結構圖。"
                "VIX Call Wall = 上方最大 gamma 集中點，VIX 衝破此位 = "
                "dealer 被迫大量買入 VIX 避險 → VIX 加速上漲 → SPX 加速下跌。<br>"
                "VIX Put Wall = 下方支撐，VIX 跌破此位 = VIX 被壓制、'Pin' 在低位附近。<br>"
                "McElligott 追蹤的 'Patient Zero' 案例：2024/08 VaR Shock 前，"
                "大量 VIX call spread（~360k Sep 22/30 CS）建倉 = "
                "dealer short VIX upside gamma → VIX 從 15 飆至 65（盤中）時 "
                "dealer 被擠壓的程度前所未見。Gamma Field 是 VIX 均衡價位的指引。",
        },
        {
            "title": "VIX Gamma Environment — VIX 自身的體制",
            "ids": ["gex_vix_spot_price", "gex_vix_gamma_env", 2, "cboe_VVIX"],
            "axis": [0, 1, 2, 3],
            "summary":
                "VIX Gamma Environment：+1 = VIX 在 Positive Gamma（VIX 被壓制、均值回歸）；"
                "-1 = VIX 在 Negative Gamma（VIX spike 會加速）。<br>"
                "此圖是理解 VIX spike 自我實現機制的關鍵：當 VIX 進入 Negative Gamma + "
                "VVIX 同步飆升 = VIX 選擇權 dealer 被擠壓 + VIX ETN 被迫回補 = VIX 超漲（overshoot）。<br>"
                "搭配 SPX 觀察：SPX 跌穿自己的 Gamma Flip + VIX 同時進入 Negative Gamma = "
                "'雙重加速'，是 McElligott 框架中最危險的組合。<br>"
                "注意：VIX daily_summary 從 2024-10-16 開始（361 天），gamma_env 歷史較短。",
        },
        {
            "title": "Gamma Flip Distance — SPX + VIX 緩衝/風險度量",
            "pctrank_id": "gex_spx_flip_distance",
            "ids": ["gex_spx_flip_distance", "gex_vix_flip_distance"],
            "axis": [0, 0],
            "plot_lines": [("gex_spx_flip_distance", 0), ("gex_vix_flip_distance", 0)],
            "summary":
                "SPX 和 VIX 各自距離 Gamma Flip Level 的百分比距離，合併在一張圖上。<br>"
                "SPX 正值 = 在 Positive Gamma（股市穩定）；SPX 負值 = 在 Negative Gamma（股市加速下跌風險）。<br>"
                "VIX 正值 = VIX 在 Positive Gamma（VIX 被壓制）；VIX 負值 = VIX 在 Negative Gamma（VIX spike 加速風險）。<br>"
                "McElligott 框架的終極預警：SPX 距離為負 + VIX 距離為負 = "
                "'雙重 Negative Gamma'，歷史上對應 2024/08 VaR Shock 級別事件。<br>"
                "SPX 距離為正 + VIX 距離為正 = '雙重穩定器'，最有利於 Vol Selling 和 Carry Trade。",
        },
        {
            "title": "SPX Call/Put Gamma 拆分 — Dealer GEX 量化",
            "pctrank_id": "gex_spx_net_gamma",
            "ids": ["gex_spx_call_gamma", "gex_spx_put_gamma", "gex_spx_net_gamma", 2],
            "axis": [0, 0, 0, 1],
            "plot_lines": [("gex_spx_net_gamma", 0)],
            "summary":
                "SPX Dealer GEX 的正/負拆分（$B 單位）。<br>"
                "Call Gamma（正 GEX 區域）= call-dominated 的 dealer gamma，通常為正值（dealer long gamma from put sellers）。"
                "Put Gamma（負 GEX 區域）= put-dominated 的 dealer gamma，通常為負值（dealer short gamma from call buyers）。"
                "Net Gamma = 兩者加總。<br>"
                "比 Gamma Environment（+1/-1 二元指標）更精細——可觀察量級變化："
                "Net Gamma 從 +$500M 降至 +$100M 但仍為正 = 表面安全但緩衝已大幅縮減。<br>"
                "Net Gamma 負值的量級決定「加速器」的力度：-$200M vs -$1B 的衝擊完全不同。",
        },
        {
            "title": "SPX 0DTE vs 非0DTE Net Gamma — 短期 Gamma 結構",
            "pctrank_id": "gex_spx_gamma_0dte",
            "ids": ["gex_spx_gamma_0dte", "gex_spx_gamma_non0dte", 2],
            "axis": [0, 0, 1],
            "summary":
                "SPX 0DTE（當日到期）vs 非0DTE 的 Net Gamma 拆分（$B 單位）。<br>"
                "0DTE 選擇權交易量爆炸式增長（佔 SPX 選擇權總量 40%+），"
                "使 0DTE gamma 成為盤中微結構的主導力量。<br>"
                "0DTE gamma 特性：每日歸零重建，高度集中在 ATM 附近，gamma 值極大但存續期極短。"
                "大量 0DTE 負 gamma = 盤中波動放大器；大量 0DTE 正 gamma = 盤中釘住效應（pinning）。<br>"
                "非0DTE gamma 代表較長期的結構性部位——"
                "當 0DTE 佔 total 比例偏高 = gamma 結構高度依賴當日選擇權，隔日可能完全改變。",
        },
        {
            "title": "SPX Net Gamma vs VIX — Gamma-Vol 負相關追蹤",
            "pctrank_id": "gex_spx_net_gamma",
            "ids": ["gex_spx_net_gamma", 355],
            "axis": [0, 1],
            "summary":
                "SPX Net Gamma（$B）與 VIX 的對照圖。<br>"
                "McElligott 框架的核心關係：Net Gamma 下降 → realized vol 上升 → VIX 上升。"
                "Net Gamma 急跌至負值 = VIX 噴升的前兆/同步指標。<br>"
                "歷史驗證：2024/08 VaR Shock 前 Net Gamma 從正轉負，VIX 從 15 飆至 65（盤中）。"
                "反之，Net Gamma 回到強正值 = VIX 被壓制 = 良性循環重啟。<br>"
                "此圖用量化的 Net Gamma 值（而非 +1/-1 二元指標）追蹤此關係的精細變化。",
        },
    ],
    reverse_ids=[],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
