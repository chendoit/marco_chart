import numpy as np
import pandas as pd

from app.utils import ChartModule, load_series_data


def _build_vvix_outperformance_scatter():
    """計算 VVIX vs VIX 1D change 散佈圖 + 回歸線 + outperformance percentile。

    回傳 {"config": {完整 Highcharts config}, "summary": "..."}。
    """
    vix = load_series_data("cboe_VIX")
    vvix = load_series_data("cboe_VVIX")

    df_vix = pd.DataFrame(vix["data"], columns=["Date", "VIX"])
    df_vvix = pd.DataFrame(vvix["data"], columns=["Date", "VVIX"])
    for df in (df_vix, df_vvix):
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        df.sort_index(inplace=True)

    df = df_vix.join(df_vvix, how="inner")
    df["VIX_chg"] = df["VIX"].pct_change() * 100
    df["VVIX_chg"] = df["VVIX"].pct_change() * 100
    df = df.dropna()

    two_years_ago = df.index.max() - pd.DateOffset(years=2)
    df = df[df.index >= two_years_ago]

    x = df["VIX_chg"].values
    y = df["VVIX_chg"].values

    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = np.sum((y - predicted) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    residuals = y - predicted

    dates = df.index
    today_x = float(x[-1])
    today_y = float(y[-1])
    today_residual = float(residuals[-1])
    today_pctile = float(np.sum(residuals <= today_residual) / len(residuals) * 100)

    RECENT_DAYS = 30
    n_total = len(x)
    cut = max(n_total - RECENT_DAYS, 0)

    history_data = [[round(float(xi), 4), round(float(yi), 4)]
                    for xi, yi in zip(x[:cut], y[:cut])]

    # 四象限色系：(正色 >90%tile, 中間色, 淡色 <10%tile)
    Q_COLORS = {
        "RU": ("#cc0000", "#e06666", "#f4cccc"),  # 右上 恐慌爆發 — 紅
        "LD": ("#16a34a", "#4ade80", "#bbf7d0"),  # 左下 天下太平 — 綠
        "LU": ("#2563eb", "#60a5fa", "#bfdbfe"),  # 左上 暗流湧動 — 藍
        "RD": ("#ea580c", "#fb923c", "#fed7aa"),  # 右下 跌勢衰竭 — 橙
    }

    def _point_color(vix_chg, vvix_chg, pctile):
        if vix_chg > 0 and vvix_chg > 0:
            strong, mid, light = Q_COLORS["RU"]
        elif vix_chg < 0 and vvix_chg < 0:
            strong, mid, light = Q_COLORS["LD"]
        elif vix_chg < 0 and vvix_chg > 0:
            strong, mid, light = Q_COLORS["LU"]
        else:
            strong, mid, light = Q_COLORS["RD"]
        if pctile >= 90:
            return strong
        if pctile <= 10:
            return light
        return mid

    n_recent = n_total - 1 - cut

    recent_series = []
    for j in range(n_recent):
        idx = cut + j
        xi_j, yi_j = float(x[idx]), float(y[idx])
        res_j = float(residuals[idx])
        pct_j = float(np.sum(residuals <= res_j) / len(residuals) * 100)
        color = _point_color(xi_j, yi_j, pct_j)
        dt_str = dates[idx].strftime("%m/%d")
        sign_j = "+" if res_j >= 0 else ""
        recent_series.append({
            "name": f"{dt_str} ({sign_j}{res_j:.1f}, {pct_j:.0f}%tile)",
            "type": "scatter",
            "data": [[round(xi_j, 4), round(yi_j, 4)]],
            "color": color,
            "marker": {"radius": 6, "symbol": "circle"},
        })

    today_dt_str = dates[-1].strftime("%m/%d")
    today_sign = "+" if today_residual >= 0 else ""
    today_label = (f"Today {today_dt_str} "
                   f"({today_sign}{today_residual:.1f}, {today_pctile:.0f}%tile)")

    x_min, x_max = float(np.min(x)), float(np.max(x))
    y_min, y_max = float(np.min(y)), float(np.max(y))
    margin = (x_max - x_min) * 0.05
    reg_x1, reg_x2 = x_min - margin, x_max + margin
    reg_data = [
        [round(reg_x1, 4), round(slope * reg_x1 + intercept, 4)],
        [round(reg_x2, 4), round(slope * reg_x2 + intercept, 4)],
    ]

    if today_x > 0 and today_y > 0:
        quadrant = "恐慌爆發 (VIX↑ VVIX↑)"
    elif today_x < 0 and today_y < 0:
        quadrant = "天下太平 (VIX↓ VVIX↓)"
    elif today_x < 0 and today_y > 0:
        quadrant = "暗流湧動 (VIX↓ VVIX↑)"
    else:
        quadrant = "跌勢衰竭 (VIX↑ VVIX↓)"

    eq_text = f"y = {slope:.4f}x + {intercept:.4f}"
    r2_text = f"R2 = {r2 * 100:.1f}%"
    outperf_text = (f"Today's Outperformance {today_sign}{today_residual:.1f} "
                    f"{today_pctile:.1f}%tile")

    config = {
        "chart": {"type": "scatter", "zoomType": "xy"},
        "title": {"text": f"VVIX OUTPERFORMANCE VS VIX ({today_pctile:.1f}%tile)",
                  "style": {"fontWeight": "bold"}},
        "xAxis": {
            "title": {"text": "VIX 1D Change (%)"},
            "gridLineWidth": 1,
            "labels": {"enabled": True, "format": "{value}"},
            "plotLines": [{
                "value": 0, "color": "#333", "width": 2,
                "zIndex": 3,
            }],
        },
        "yAxis": {
            "title": {"text": "VVIX 1D Change (%)"},
            "gridLineWidth": 1,
            "labels": {"enabled": True, "format": "{value}"},
            "plotLines": [{
                "value": 0, "color": "#333", "width": 2,
                "zIndex": 3,
            }],
        },
        "legend": {
            "enabled": True,
            "layout": "horizontal",
            "align": "center",
            "verticalAlign": "top",
        },
        "tooltip": {"valueDecimals": 2},
        "annotations": [
            {
                "draggable": "",
                "labelOptions": {
                    "backgroundColor": "rgba(255,255,200,0.85)",
                    "borderColor": "#999",
                    "shape": "rect",
                    "style": {"fontSize": "12px"},
                },
                "labels": [{
                    "point": {"x": 300, "y": 350},
                    "useHTML": True,
                    "text": (
                        f"{eq_text}<br>{r2_text}<br>"
                        f"<span style='color:#cc0000;font-weight:bold'>"
                        f"{outperf_text}</span><br>"
                        f"<b>{quadrant}</b><br>"
                        f"<span style='font-size:11px'>"
                        f"<span style='color:#cc0000'>\u25cf</span> 恐慌爆發 "
                        f"<span style='color:#16a34a'>\u25cf</span> 天下太平 "
                        f"<span style='color:#2563eb'>\u25cf</span> 暗流湧動 "
                        f"<span style='color:#ea580c'>\u25cf</span> 跌勢衰竭<br>"
                        f"正色=Outperf>90% 淡色=Outperf<10%"
                        f"</span>"
                    ),
                }],
            },
            {
                "draggable": "",
                "labelOptions": {
                    "backgroundColor": "rgba(255,255,255,0)",
                    "borderWidth": 0,
                    "style": {"fontSize": "11px", "color": "#888"},
                },
                "labels": [
                    {"point": {"xAxis": 0, "yAxis": 0,
                               "x": x_max * 0.7, "y": y_max * 0.7},
                     "text": "恐慌爆發"},
                    {"point": {"xAxis": 0, "yAxis": 0,
                               "x": x_min * 0.7, "y": y_min * 0.7},
                     "text": "天下太平"},
                    {"point": {"xAxis": 0, "yAxis": 0,
                               "x": x_min * 0.7, "y": y_max * 0.7},
                     "text": "暗流湧動"},
                    {"point": {"xAxis": 0, "yAxis": 0,
                               "x": x_max * 0.7, "y": y_min * 0.7},
                     "text": "跌勢衰竭"},
                ],
            },
        ],
        "series": [
            {
                "name": "Past 2 Years",
                "type": "scatter",
                "data": history_data,
                "color": "#999999",
                "marker": {"radius": 3, "symbol": "circle"},
            },
            *recent_series,
            {
                "name": today_label,
                "type": "scatter",
                "data": [[round(today_x, 4), round(today_y, 4)]],
                "color": "#ff0000",
                "marker": {"radius": 8, "symbol": "diamond",
                           "lineWidth": 1, "lineColor": "#cc0000"},
            },
            {
                "name": "Regression",
                "type": "line",
                "data": reg_data,
                "color": "#cc0000",
                "dashStyle": "Dot",
                "lineWidth": 2,
                "marker": {"enabled": False},
                "enableMouseTracking": False,
            },
        ],
    }

    summary = (
        "VVIX vs VIX 每日百分比變動散佈圖（過去 2 年）。"
        "Outperformance = 實際 VVIX 變動 − 回歸預測值（殘差），"
        "本質上衡量「市場情緒脫離常軌的程度」。<br>"
        "Outperformance 為正 (+)：市場買保險（VIX 選擇權）的力道比歷史常態更瘋狂。"
        "Outperformance 為負 (-)：市場對風險的無感程度比歷史常態更鬆懈（或該買保險的人都買完了）。"
        "Percentile：這個脫軌現象有多罕見——"
        "99% = 極度異常的正脫軌；1% = 極度異常的負脫軌。<br><br>"

        "<b>四象限解讀框架：</b><br>"

        "<b>右上：恐慌爆發 (VIX↑ VVIX↑)</b> — 散戶與法人同步恐慌，瘋狂搶買避險。"
        "正常情境，迴歸預測值為正。"
        "極端正 Outperformance (>99%tile)：非理性恐慌頂部 (Climax)——"
        "VVIX 漲得比預期誇張太多，恐慌情緒已耗盡，短線隨時報復性反彈。"
        "負 Outperformance (<10%tile)：虛假恐慌——"
        "VIX 雖大漲但大戶未瘋狂搶保險，暗示下跌殺傷力有限、不會持久。<br>"

        "<b>左下：天下太平 (VIX↓ VVIX↓)</b> — 市場樂觀，風險偏好高，不需要保險。"
        "正常情境，迴歸預測值為負。"
        "極端負 Outperformance (<5%tile)：極度自滿——"
        "大家瘋狂拋售保險，常見於重大事件落地後（選舉、FED 降息），"
        "短期利多但過度自滿可能埋下波動種子。"
        "正 Outperformance (>80%tile)：黏滯的恐懼——"
        "大盤大漲但法人死抱保險不放，暗示上漲可能是假突破（誘多）。<br>"

        "<b>左上：暗流湧動 (VIX↓ VVIX↑)</b> — 大盤還在漲，但大戶趁便宜偷偷買保險。"
        "VIX↓ 預測值為負 + 實際 VVIX↑ 為正 → 必然巨大正 Outperformance。"
        "極端正 Outperformance (>95%tile)：<b>最強烈空頭預警</b>——"
        "聰明錢 (Smart Money) 砸重金急迫買保險，預示接下來幾天可能出現巨大市場修正。<br>"

        "<b>右下：跌勢衰竭 (VIX↑ VVIX↓)</b> — 大盤還在跌，但恐慌情緒不再蔓延。"
        "VIX↑ 預測值為正 + 實際 VVIX↓ 為負 → 必然巨大負 Outperformance。"
        "極端負 Outperformance (<5%tile)：<b>極佳底部訊號</b>——"
        "已無人願花高價買保險，恐慌擴散徹底衰竭 (exhaustion)，大盤隨時見底反轉。<br><br>"

        "<b>三大極端交易機會：</b><br>"
        "1. VIX↑ VVIX↑ + Outperf >99%tile → 恐慌極致，尋找 VIX 做空點或大盤抄底點（左側交易）。<br>"
        "2. VIX↓ VVIX↑ + Outperf >95%tile → 籌碼背離，佈局大盤空單或買入 VIX Call（避險預警）。<br>"
        "3. VIX↑ VVIX↓ + Outperf <5%tile → 恐慌衰竭，佈局大盤多單或賣出 VIX Call（尋找底部）。"
    )

    return {"config": config, "summary": summary}


_module = ChartModule(
    filename='McElligott波動率微結構',
    charts=[
        {
            "title": "VVIX/VIX 凸性比率 — VVIX Never Lies",
            "pctrank_id": "expr_vvix_div_vix",
            "ids": [2, (22904, '/', 355), 355],
            "axis": [0, 1, 2],
            "plot_lines": [((22904, '/', 355), [5, 6, 7])],
            "summary":
                "VVIX/VIX 比率量化選擇權交易商的凸性壓力。"
                "McElligott 反覆強調 'VVIX never lies'——VVIX 捕捉了 VIX 本身無法反映的東西："
                "系統中嵌入的凸性風險與交易商在 VIX 選擇權市場的壓力程度。<br>"
                "比率 > 6 代表 VIX 選擇權交易商被擠壓（short upside convexity），"
                "歷史上僅在極端事件出現（如 2024/08 VaR Shock 時 VVIX 1d outperformance vs SPX 達 99.9th %ile）。<br>"
                "比率持續偏低 = 市場穩定、凸性風險被壓制。",
        },
        {
            "title": "VIX Spot Beta — 波動率-現貨敏感度",
            "pctrank_id": "expr_vix_div_spx",
            "ids": [2, (355, '/', 2)],
            "axis": [0, 1],
            "summary":
                "VIX/SPX 比率作為 VIX Spot Beta 的長期趨勢代理。"
                "McElligott 追蹤 VIX 對 SPX 每 1% 變動的反應強度。"
                "2024/08/05 所有時間間隔均達 100th %ile = 'VIX 以前所未有的強度回應 SPX 波動'"
                "——這是 dealer 被 short VIX call 擠壓的直接量化指紋。<br>"
                "高 beta = 隱藏壓力；低 beta = options complex 平靜。",
        },
        {
            "title": "Spot-Vol 相關性體制 — Crash-Up vs Crash-Down",
            "ids": [2, 355, 22904],
            "axis": [0, 1, 2],
            "summary":
                "SPX + VIX + VVIX 三者同框觀察 Spot-Vol 相關性體制。"
                "正常市場 = 負相關（Spot Up, Vol Down）；"
                "危險市場 = 正相關（Spot Up, Vol Up），由投機性 call 追逐推動。<br>"
                "McElligott 的 'Crash-Up' 前兆：SPX 上漲但 VIX 和 VVIX 也上漲 = "
                "'即使只是溫和的獲利了結也可能瀑布式演變成更大的反轉衝擊'。<br>"
                "負相關 = 傳統體制，Crash-Down 風險需由 Skew 判斷。",
        },
        {
            "title": "VIX 完整期限結構 — 1D/9D/30D/3M/6M/1Y",
            "ids": ["cboe_VIX1D", "cboe_VIX9D", "cboe_VIX", "cboe_VIX3M", "cboe_VIX6M", "cboe_VIX1Y"],
            "axis": [0, 0, 0, 0, 0, 0],
            "summary":
                "VIX 六個期限（1D/9D/30D/3M/6M/1Y）的完整期限結構。"
                "正常 = Contango（長期 > 短期），支持做空 VIX 的 Carry Trade。<br>"
                "Backwardation（短期 > 長期）= 急性壓力，市場定價近期不確定性高於遠期。"
                "2024/08 shock 期間出現極端 Backwardation。<br>"
                "前端 iVol 在事件風險清除後崩跌（post-election vol crush）會觸發 'Vanna tailwind'——推動 SPX 機械式上漲。",
        },
        {
            "title": "VIX 期限結構斜率 — Contango/Backwardation 量化",
            "pctrank_id": "expr_vix_div_vix3m",
            "ids": [2, ("cboe_VIX", '/', "cboe_VIX3M"), ("cboe_VIX", '/', "cboe_VIX6M"), ("cboe_VIX1D", '/', "cboe_VIX")],
            "axis": [0, 1, 1, 1],
            "plot_lines": [(("cboe_VIX", '/', "cboe_VIX3M"), 1)],
            "summary":
                "VIX/VIX3M 比率是最常用的期限結構量化指標。"
                "> 1 = Backwardation（短期恐慌高於中期，市場處於壓力中）；< 1 = Contango（正常）。<br>"
                "VIX1D/VIX 捕捉當日極端恐慌。"
                "歷史上 VIX/VIX3M 突破 1.5 通常對應重大市場事件。<br>"
                "McElligott 用此判斷 Carry Trade 環境：steep contango = vol selling 有利可圖 = "
                "'Perpetual Vega Supply' 生態系運作良好。",
        },
        {
            "title": "CBOE SKEW + GAMMA + SMILE — 市場結構三指標",
            "pctrank_id": "series_cboe_SKEW",
            "ids": [2, "cboe_SKEW", "cboe_GAMMA", "cboe_SMILE"],
            "axis": [0, 1, 2, 3],
            "plot_lines": [("cboe_SKEW", [120, 130, 140])],
            "summary":
                "三個 CBOE 官方市場結構指標：<br>"
                "(1) SKEW = S&P 500 偏態，量化 Put Skew 陡峭度。"
                "McElligott：'要出現 crash-down，你需要陡峭的 Skew'——flat Skew = crash-down 結構性不可能。"
                "SKEW > 140 = 條件成熟；SKEW < 120 = 自滿。<br>"
                "(2) GAMMA = S&P 500 Gamma 指數，量化 dealer gamma 曝險。<br>"
                "(3) SMILE = S&P 500 波動率微笑形狀。三者結合提供波動率曲面的完整快照。",
        },
        {
            "title": "VRP 策略基準健康度 — BXM / PUT / VPD / CNDR vs SPX",
            "ids": [2, "cboe_BXM", "cboe_PUT", "cboe_VPD", "cboe_CNDR"],
            "axis": [0, 1, 1, 1, 1],
            "summary":
                "CBOE 四大 Vol-Selling 策略基準指數：BXM（BuyWrite/Covered Call）、PUT（PutWrite）、"
                "VPD（VIX Premium）、CNDR（Iron Condor）。<br>"
                "這些是 McElligott 所稱 '$260B Perpetual Vega Supply 生態系' 的官方追蹤指標。<br>"
                "四個指數同步回撤 = VRP trade 全面受創 = Vol selling 停擺 = 良性循環可能反轉。<br>"
                "持續跑贏或持平 SPX = Vol selling Sharpe 吸引更多資本 = 迴路自我強化。",
        },
        {
            "title": "SHORTVOL vs LONGVOL — Vol-Selling 直接損益",
            "ids": [2, "cboe_SHORTVOL", "cboe_LONGVOL", ("cboe_SHORTVOL", '/', "cboe_LONGVOL")],
            "axis": [0, 1, 1, 2],
            "summary":
                "SHORTVOL（做空 VIX 期貨指數）vs LONGVOL（做多 VIX 期貨指數）。<br>"
                "SHORTVOL 長期因 Contango 上漲（年化 ~36%），急跌代表 VIX 期貨暴漲。<br>"
                "SHORTVOL/LONGVOL 比率是最直接的 VRP 策略健康度指標。"
                "比率持續上升 = 做空波動率獲利 = 良性循環；比率急跌 = '惡性循環啟動'。",
        },
        {
            "title": "VIX ETF 資金流向 — 尾部避險需求",
            "ids": [2, 355, ({"ZSUM": ["etf_UVXY_fundflow", "etf_VIXY_fundflow"]}, '-', {"ZSUM": ["etf_SVXY_fundflow"]})],
            "axis": [0, 1, 2],
            "summary":
                "做多 VIX ETF（UVXY+VIXY）vs 做空 VIX ETF（SVXY）的 Z-score 正規化淨資金流。<br>"
                "正值 = 市場整體買入恐慌避險（尾部避險需求飆升）；負值 = 賣出波動率/看好市場。<br>"
                "McElligott 追蹤 VIX ETN 部位作為 'Slide Risk' 指標——"
                "當 short VIX 部位累積到極端，一次 VIX spike 會觸發 ETN 被迫回補 → 自我實現的 VIX 擠壓。",
        },
        {
            "title": "VIX ETF 成交量異常 — 投機活動暴增偵測",
            "ids": ["etf_UVXY_volume", "etf_SVXY_volume", 2],
            "axis": [0, 0, 1],
            "summary":
                "VIX ETF 成交量急升通常先於或伴隨市場劇烈波動。<br>"
                "UVXY 成交量暴增 = 恐慌避險買入或投機做多波動率；"
                "SVXY 成交量暴增 = 'Short the Vol Rip' 反射性行為。<br>"
                "McElligott 觀察到即使在 2024/08 最恐慌時，"
                "'multi-year conditioning of Short the Vol Rip / Buy the Spot Dip was in full-effect'——"
                "可從成交量模式判斷投資者的反射性 vol selling 行為是否能在下一次壓力中存活。",
        },
        {
            "title": "CBOE Put/Call Ratio vs SPX vs VIX — 選擇權情緒風向標",
            "ids": [2, 1650, 355],
            "axis": [0, 1, 2],
            "plot_lines": [(1650, [1.2, 1, 0.75])],
            "summary":
                "CBOE Total Put/Call Ratio（MacroMicro series 1650）。<br>"
                "比率 > 1.2 = 極度恐慌避險（Put 買入遠超 Call）= 'Scar Tissue' 效應。<br>"
                "比率 < 0.75 = 極度樂觀/投機（Call 買入主導）= 可能的 'Crash-Up' 前兆。<br>"
                "McElligott：當 Put Skew 百分位極高但 iVol 已回落時，Put/Call Ratio 仍偏高 = "
                "'market is still trading like it is short, when in fact it is over-hedged'——"
                "這是 Pain Trade 向上的經典設置。",
        },
        {
            "title": "iVol vs Realized Vol — VRP 代理指標",
            "ids": [2, ("cboe_VIX", '-', "cboe_SPX.RVOL20"), "cboe_VIX", "cboe_SPX.RVOL20"],
            "axis": [0, 1, 2, 2],
            "plot_lines": [(("cboe_VIX", '-', "cboe_SPX.RVOL20"), 0)],
            "summary":
                "VIX（隱含波動率）減去 SPX 20 日已實現波動率 = Variance Risk Premium (VRP) 代理。<br>"
                "正值 = 隱含波動率高於已實現波動率（市場為恐懼付出溢價）= vol selling 有利可圖。<br>"
                "McElligott 的 '$260B Perpetual Vega Supply' 生態系依賴正 VRP 運作："
                "只要 iVol > rVol，做空波動率就持續獲利 → 更多資本湧入 → 壓制 vol → 自我強化。<br>"
                "VRP 崩跌至零或負值 = vol selling 停擺 = 良性循環反轉為惡性循環。"
                "2024/08 shock 期間 rVol 急速飆升超過 iVol。",
        },
        {
            "title": "SPX 3M Put Skew — 25dP/ATM",
            "pctrank_id": "gex_spx_put_skew_3m",
            "ids": [2, "gex_spx_put_skew_3m"],
            "axis": [0, 1],
            "summary":
                "SPX 3 個月 25-delta Put / ATM IV 比率（Nomura Vol 報告核心圖表）。<br>"
                "McElligott 的關鍵判斷框架：'要出現 crash-down，你需要陡峭的 Skew'。"
                "Put Skew 高 = 市場對下行避險的需求強烈，dealer 累積了 short downside gamma/vega → "
                "一旦現貨下跌，dealer 被迫在期貨市場加速賣出避險。<br>"
                "Put Skew 平坦（低百分位）= crash-down 結構性不可能，因為 dealer 沒有需要避險的下行曝險。<br>"
                "與 CBOE SKEW 指標互為參照，但此指標直接來自 vol surface 的 25-delta 點位，更精確。"
                "資料範圍：2025-10 起（~110 天），來自 Lieta term structure。",
        },
        {
            "title": "SPX 3M Skew — 25dP/25dC",
            "pctrank_id": "gex_spx_skew_ratio_3m",
            "ids": [2, "gex_spx_skew_ratio_3m"],
            "axis": [0, 1],
            "summary":
                "SPX 3 個月 25-delta Put / 25-delta Call IV 比率（Skew Ratio）。<br>"
                "此比率量化 put 偏斜相對 call 偏斜的「不對稱程度」——"
                "比率 > 1.4 = put 明顯比 call 貴，市場「恐慌搶進下行保護」。<br>"
                "McElligott 文章 09（Skew Change）的核心指標：Skew Ratio 從極低百分位快速急升 = "
                "市場體制從「自滿」轉為「恐慌」，歷史上僅觸發 ~10 次（含 2008/2015/2020）。<br>"
                "高百分位 = 買 put 的人多；低百分位 = call 偏斜主導（Crash-Up 前兆）。",
        },
        {
            "title": "SPX 1M vs 3M Put Skew — Skew 期限結構",
            "pctrank_id": "gex_spx_put_skew_1m",
            "ids": ["gex_spx_put_skew_1m", "gex_spx_put_skew_3m"],
            "axis": [0, 0],
            "summary":
                "SPX 1 個月 vs 3 個月的 Put Skew（25dP/ATM），觀察「偏斜的期限結構」。<br>"
                "正常：3M > 1M（遠期 skew 較陡，反映長期尾部風險定價）。<br>"
                "異常：1M 急速超過 3M = 短期恐慌事件正在發生（如 CPI surprise、地緣危機）。"
                "此時 dealer 在短期被大量買 put，短期 skew 被抬高。<br>"
                "兩者同步急升 = 全面恐慌；僅 1M 急升而 3M 穩定 = 事件性恐慌（通常可逢低買）。",
        },
        {
            "title": "SPX IV Term Slope — Vol Surface Contango/Backwardation",
            "pctrank_id": "gex_spx_term_slope",
            "ids": [2, "gex_spx_term_slope"],
            "axis": [0, 1],
            "plot_lines": [("gex_spx_term_slope", 0)],
            "summary":
                "SPX 選擇權 vol surface 的期限結構斜率（遠端 ATM IV − 近端 ATM IV）。<br>"
                "正值 = Contango（遠期 vol > 近期 vol）= 正常市場，Carry Trade 有利；"
                "負值 = Backwardation = 近期 vol 高於遠期 = 急性壓力。<br>"
                "與 VIX/VIX3M 比率互為參照，但此指標直接來自 SPX 選擇權 surface："
                "更精確，且包含近端 0-10 DTE vs 遠端 55-95 DTE 的具體 IV 差異。<br>"
                "Backwardation 的強度（負值越大）直接量化「市場認為近期比遠期更危險多少」。",
        },
        {
            "title": "SPX Surface VRP — IV30 vs RVol20",
            "pctrank_id": "gex_spx_vrp_surface",
            "ids": [2, "gex_spx_vrp_surface", "gex_spx_iv30"],
            "axis": [0, 1, 2],
            "plot_lines": [("gex_spx_vrp_surface", 0)],
            "summary":
                "SPX 選擇權 surface 的 Variance Risk Premium：IV30 − RVol20（均年化 %）。<br>"
                "與 Chart 1-12（VIX − SPX RVol20）互為參照，但此版本使用 vol surface 的 IV30 而非 VIX。"
                "兩者差異：VIX 受 VIX 期貨/ETN 生態系影響，IV30 是 SPX 選擇權 surface 的直接讀數。<br>"
                "正值 = vol selling 有利；零或負值 = vol selling 停擺。<br>"
                "搭配 IV30 的絕對水位觀察：IV30 高百分位 + VRP 正 = 「恐懼溢價高但做空 vol 仍有利」；"
                "IV30 高 + VRP 負 = 「已實現波動率追上隱含 → 惡性循環啟動」。",
        },
        {
            "title": "股票型槓桿 ETF 成交量 — Synthetic Short Gamma",
            "ids": ["etf_TQQQ_volume", "etf_SQQQ_volume", "etf_SOXL_volume", "etf_SOXS_volume", 2],
            "axis": [0, 0, 0, 0, 1],
            "summary":
                "TQQQ/SQQQ（Nasdaq 3x）和 SOXL/SOXS（半導體 3x）的成交量。<br>"
                "McElligott 稱槓桿 ETF 為 'Synthetic Short Gamma'——"
                "AUM $129B 歷史最高，日再平衡流量 = 機械式追漲殺跌。<br>"
                "成交量暴增 = 投機活動加劇 + 再平衡衝擊放大。"
                "SQQQ 成交量飆升 = 市場恐慌避險需求；"
                "TQQQ 成交量飆升 = 投機做多熱情。<br>"
                "做多/做空成交量比的變化 = 市場情緒風向標。",
        },
        {
            "title": "TQQQ/SQQQ Fund Flow — Nasdaq 槓桿資金方向",
            "ids": [2, "etf_TQQQ_fundflow", "etf_SQQQ_fundflow"],
            "axis": [0, 1, 1],
            "summary":
                "ProShares TQQQ/SQQQ 的每日 fund flow（基於 Shares Outstanding 變化 × NAV）。<br>"
                "TQQQ 淨流入 = 散戶看多 Nasdaq（追逐動能）；"
                "SQQQ 淨流入 = 散戶避險或做空。<br>"
                "McElligott 追蹤槓桿 ETF 資金流作為 'Retail Animal Spirits' 的代理："
                "持續流入做多槓桿 = 風險偏好高位；突然轉向做空槓桿 = 恐慌避險。<br>"
                "拆股日期間 fund flow 被排除（Shares Outstanding 劇變但非資金流）。",
        },
        {
            "title": "VIX Call/Put/Net Gamma 歷史百分位",
            "ids": [2, 355, 22904,
                    "gex_vix_call_gamma_pctrank",
                    "gex_vix_put_gamma_pctrank",
                    "gex_vix_net_gamma_pctrank"],
            "axis": [0, 1, 2, 3, 3, 3],
            "summary":
                "VIX 選擇權 Dealer Gamma 的 Call / Put / Net 三條線各自 2 年滾動歷史百分位（5 日均線平滑）。<br>"
                "VIX 的 dealer gamma 結構與 SPX 獨立，是理解 VIX spike 自我加速機制的關鍵量化指標。<br>"
                "Net Gamma 百分位極低 = VIX dealer 的 negative gamma 處於歷史罕見水位，VIX spike 加速風險最高；"
                "Call Gamma 百分位急升 = 大量 VIX call 買入（投機或避險）正在改變 dealer 曝險結構。<br>"
                "搭配 VIX / VVIX 價格背景觀察：百分位急跌 + VVIX 飆升 = 'VIX 選擇權 dealer 被擠壓' 的量化確認。",
        },
        {
            "custom_config": _build_vvix_outperformance_scatter,
        },
    ],
    reverse_ids=[],
)

CHART_IDS = _module.CHART_IDS
SUMMARY_LIST = _module.SUMMARY_LIST
generate_chart_data = _module.generate_chart_data
get_chart_config = _module.get_chart_config
get_custom_config = _module.get_custom_config
