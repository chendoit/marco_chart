from app.utils import ChartModule

_module = ChartModule(
    filename='McElligott相關性與部位',
    charts=[
        {
            "title": "隱含相關性 COR1M / COR3M vs SPX — Dispersion Trade 健康度",
            "pctrank_id": "series_cboe_COR1M",
            "ids": [2, "cboe_COR1M", "cboe_COR3M"],
            "axis": [0, 1, 1],
            "summary":
                "CBOE S&P 500 隱含相關性（1 月/3 月）。"
                "McElligott 框架中，低相關性 = Dispersion Trade 獲利 = 做空指數 vol 的資金持續供給 = index vol 壓制。"
                "2024/12 COR1M 降至 1st %ile = Dispersion YTD 100th %ile（有史以來最佳）。<br>"
                "但相關性是均值回歸的：McElligott 發現連續 6+ 天 'Negative Breadth'"
                "（指數漲但多數成分股跌）後，COR1M 中位數在 T+2w 從 50 飆升到 80。"
                "相關性急升 = Dispersion bleed → 做空指數 vol 的腿被迫回補 → 指數 vol 暴漲 → 觸發系統性去槓桿。",
        },
        {
            "title": "隱含相關性期限結構 — COR1M vs COR3M vs COR6M vs COR1Y",
            "ids": ["cboe_COR1M", "cboe_COR3M", "cboe_COR6M", "cboe_COR1Y"],
            "axis": [0, 0, 0, 0],
            "summary":
                "相關性期限結構：正常情況下長期 > 短期（遠期更 'macro-driven'）。"
                "COR1M 急速超過 COR3M = 短期相關性衝擊正在發生"
                "（通常伴隨 macro catalyst 如 CPI surprise、NFP miss）。<br>"
                "COR1M 遠低於 COR1Y = 短期分散度極高、集中度交易盛行。"
                "此圖與 Chart 2-1 搭配，提供相關性體制的完整時間維度。",
        },
        {
            "title": "MGTN Magnificent 10 vs 市場寬度 vs SPX — 集中度風險",
            "ids": [2, "cboe_MGTN", 18331, 22718],
            "axis": [0, 1, 2, 2],
            "summary":
                "CBOE Magnificent 10 指數（AAPL/MSFT/NVDA/AMZN/META/TSLA/AVGO/GOOGL 等）"
                "vs S&P 500 成分股在 50MA/200MA 以上的百分比。<br>"
                "McElligott 追蹤的 '集中度悖論'：指數上漲但廣度惡化 = 'Negative Breadth'。"
                "2024/12 出現史無前例的 11 天連續 Negative Breadth 但指數反而上漲 +0.8%——"
                "'dare I say unprecedented'。<br>"
                "Mag8 佔 SPY 35.9%、QQQ 51.8%。槓桿型 ETF AUM 的 89% 集中在 "
                "'Tech Leadership / Animal Spirits' 類別，使再平衡流量高度集中在少數個股。",
        },
        {
            "title": "CFTC 多貨幣投機部位多空比率 — 擁擠度量化",
            "ids": [
                ("jpy_cme_noncommercial_long", '/', "jpy_cme_noncommercial_short"),
                ("eur_cme_noncommercial_long", '/', "eur_cme_noncommercial_short"),
                ("aud_cme_noncommercial_long", '/', "aud_cme_noncommercial_short"),
                2,
            ],
            "axis": [0, 0, 0, 1],
            "summary":
                "三大貨幣（JPY/EUR/AUD）的非商業持倉多空比率。"
                "McElligott 的核心原則：'Crowding is shadow leverage'——"
                "擁擠的部位等同於隱性槓桿，因為加速性平倉資金流會放大衝擊。<br>"
                "2024/08 JPY Carry Unwind：JPY 空頭從極端高位急速回補，"
                "USDJPY 1 月跌幅 -12.2%（Lehman 以來最大，-5 z-score）。"
                "當多空比率達極值 = Pain Trade 反轉風險最高。",
        },
        {
            "title": "日圓 Carry Trade 壓力指標 — McElligott's Canary",
            "ids": [2, 355, 22904, "jpy_cme_noncommercial_short", "jpy_cme_net_position_large_spec"],
            "axis": [0, 1, 2, 3, 3],
            "plot_lines": [(22904, 100)],
            "summary":
                "McElligott 的經典組合指標：日圓投機空頭（反轉軸）+ VVIX。"
                "'日圓空頭由高點滑落 + VVIX 由底部上升到 100 = 強力風險警示'。<br>"
                "2024/08 的 VaR Shock 完美演示：BoJ 鷹派意外 + 美國勞動數據失望 → "
                "日圓急升（空頭回補）→ Carry Trade 平倉 → 全球股市暴跌。<br>"
                "G10 FX Carry 單日 -3.0%（-5.8 z-score）；日經 225 單日 -12.4%（-9.5 z-score）。"
                "日圓空頭高位 = Carry Trade 擁擠 = systemic risk。",
        },
        {
            "title": "跨資產波動率比較 — VIX vs RVX vs VXN",
            "pctrank_id": "series_cboe_VIX",
            "ids": [2, "cboe_VIX", "cboe_RVX", "cboe_VXN"],
            "axis": [0, 1, 1, 1],
            "summary":
                "三大美股指數的波動率：VIX（S&P 500）、RVX（Russell 2000）、VXN（Nasdaq 100）。<br>"
                "RVX vs VIX 的 spread 反映大小型股的相對恐慌度；VXN vs VIX 反映科技股的相對波動。"
                "當所有三者同步飆升 = 系統性壓力（非板塊輪動）。<br>"
                "2024/08 期間三者均暴漲，確認 'everything breaks at once' = 所有策略都在去槓桿。"
                "小型股 vol（RVX）超過大型股 vol（VIX）= 信用風險開始傳導。",
        },
        {
            "title": "VRP 策略 vs SPX 相對表現 — Vol-Selling Sharpe 追蹤",
            "pctrank_id": "expr_bxm_div_spx",
            "ids": [("cboe_BXM", '/', 2), ("cboe_PUT", '/', 2)],
            "axis": [0, 0],
            "plot_lines": [(("cboe_BXM", '/', 2), 1)],
            "summary":
                "BXM/SPX 和 PUT/SPX 比率追蹤 Vol-Selling 策略相對於純股票持有的超額表現。"
                "比率上升 = VRP 策略跑贏（'Sell 25d Put, Buy 25d Call Sharpe 4.2 vs Stock Sharpe 3.9'，2024/02）；"
                "比率下降 = VRP 受創。<br>"
                "McElligott：'做空波動率等於合成做多 Beta——每個收入 ETF、每個 overwriting 程式、"
                "每個 Dispersion trader 都不只是做空選擇權，他們是帶槓桿的合成做多股票。'"
                "當 Vol spike 時，他們全部同時去槓桿。",
        },
        {
            "title": "SPX Realized Vol 多窗口 — Exposure Toggle",
            "ids": ["cboe_SPX.RVOL10", "cboe_SPX.RVOL20", "cboe_SPX.RVOL60"],
            "axis": [0, 0, 0],
            "summary":
                "SPX 已實現波動率：10d / 20d / 60d 滾動窗口（年化）。"
                "McElligott 追蹤 5d/10d/20d/60d/120d realized vol，"
                "因為不同系統性策略使用不同的 rVol 窗口。<br>"
                "3 月期 trailing rVol 對 Vol Control / Target Volatility 策略最關鍵"
                "（通常取最高窗口作為約束）。"
                "2024/10 SPX 20d rVol = 9.3, 10d = 6.2, 5d = 2.1——"
                "這種壓縮觸發了 99th %ile 的 Vol Control 買入（+$45.5B/週）。<br>"
                "關鍵動態：高波動日 '退出' trailing 窗口時，rVol 機械式下降 → 觸發買入，"
                "即使市場沒有任何變化。此圖是 Vol Control 行為的最佳間接推斷。",
        },
        {
            "title": "E-mini SPX Asset Manager vs Leveraged Fund 淨部位",
            "pctrank_id": "emini_spx_cme_net_position_asset_mgr",
            "ids": [2, "emini_spx_cme_net_position_asset_mgr", "emini_spx_cme_net_position_lev_money"],
            "axis": [0, 1, 1],
            "summary":
                "CFTC TFF 報告：E-mini S&P 500 期貨的 Asset Manager 和 Leveraged Fund 淨持倉。<br>"
                "McElligott 引用 'CFTC/TFF Asset Manager Futures at 100th %ile'——"
                "這是 HF Net/Gross Exposure 的最佳公開替代。<br>"
                "AM Net 持續攀升 = 機構做多曝險極端（Crowding = Shadow Leverage）；"
                "LF Net 大幅做空 = 對沖基金看空，若急速回補 = short squeeze。<br>"
                "兩者方向背離 = 市場分歧加劇 → 波動率上升的結構性條件。"
                "歷史極值後的均值回歸 = McElligott 的 Pain Trade 框架核心。",
        },
        {
            "title": "E-mini SPX 持倉 % of OI — 擁擠度百分位",
            "pctrank_id": "emini_spx_cme_net_pct_of_oi_asset_mgr",
            "ids": [
                "emini_spx_cme_net_pct_of_oi_asset_mgr",
                "emini_spx_cme_net_pct_of_oi_lev_money",
                2,
            ],
            "axis": [0, 0, 1],
            "summary":
                "Asset Manager 和 Leveraged Fund 的淨持倉佔 Open Interest 百分比。<br>"
                "% of OI 比絕對數量更能反映 '擁擠度'——"
                "McElligott 的 Crowding = Shadow Leverage 原則：<br>"
                "AM Net > 15% of OI = 機構做多極度擁擠（潛在去槓桿風險極高）；"
                "LF Net < -15% of OI = 對沖基金做空極度擁擠（short squeeze 風險）。<br>"
                "兩者同時達極端 = 'Pain Trade 無論方向都會造成衝擊'。",
        },
        {
            "title": "SPX CTA 趨勢信號（MA 交叉計數）— Vol Control / CTA 曝險代理",
            "ids": [2, "cboe_SPX.TREND"],
            "axis": [0, 1],
            "plot_lines": [("cboe_SPX.TREND", [1, 4])],
            "summary":
                "SPX CTA 趨勢信號：計算現價高於幾條移動平均線（10/20/50/100/200 日 MA）。<br>"
                "5 = 全部 MA 看多（強勢上升趨勢，CTA 全面做多、曝險最大化）；"
                "0 = 全部 MA 看空（強勢下降趨勢，CTA 全面做空）。<br>"
                "McElligott 的系統性流量分析核心：CTA 以 rVol 和趨勢信號決定曝險。"
                "信號從 5 降至 3 = 短期 MA 被跌破 → CTA 開始減倉 → 供給壓力。<br>"
                "信號從 0 升至 2 = 短期 MA 被突破 → CTA 開始翻多 → 需求支撐。"
                "歷史上信號翻轉通常伴隨 3-5 天的集中性資金流。",
        },
    ],
    reverse_ids=["jpy_cme_noncommercial_short"],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
