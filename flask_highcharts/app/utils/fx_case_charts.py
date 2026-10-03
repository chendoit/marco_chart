"""
澳元／紐元頁共用的自訂圖（custom_config）：價格 × 持倉四象限、賽馬排序表。
資料由 get_aud_nzd_series.py 每日產生（cot_* / rate_pol_* / ccy_usdfx_*）。
"""
import pandas as pd

from .highcharts_utils import load_series_data, process_expression

REGIMES = [  # (代碼, 標籤, 顏色)；代碼定義見 get_aud_nzd_series.REGIME_CODE
    (1, "價跌 + OI 增 = 新空頭進場", "rgba(192, 57, 43, 0.9)"),
    (2, "價跌 + OI 減 = 多頭平倉", "rgba(230, 126, 34, 0.9)"),
    (3, "價漲 + OI 減 = 空頭回補", "rgba(130, 200, 140, 0.9)"),
    (4, "價漲 + OI 增 = 新多頭進場", "rgba(0, 128, 0, 0.9)"),
    (0, "換月／交割週（不判讀）", "rgba(160, 160, 160, 0.6)"),
]

AREAS = [("US", "美國"), ("AU", "澳洲"), ("NZ", "紐西蘭"), ("CA", "加拿大"), ("GB", "英國"),
         ("XM", "歐元區"), ("JP", "日本"), ("CH", "瑞士")]


def _series(sid):
    d = load_series_data(sid)["data"]
    return pd.Series([v for _, v in d], index=pd.to_datetime([k for k, _ in d]).normalize()).sort_index()


def _ms(ts):
    return int(pd.Timestamp(ts).timestamp() * 1000)


def median_since(expr, start="2004-01-01"):
    """運算式序列自 start 起的中位數，給 plot line 用；資料缺就回 None。"""
    try:
        d = process_expression(expr)["data"]
        s = pd.Series([v for _, v in d], index=pd.to_datetime([k for k, _ in d]))
        return round(float(s.loc[start:].median()), 2)
    except Exception:
        return None


def regime_chart(ccy, fx_id, fx_label, title, summary):
    """每週 ΔOI 柱狀圖依四象限上色，疊上匯率線。回傳 callable（每次 API 請求重算）。"""
    def build():
        code = _series(f"cot_{ccy}_regime")
        doi = _series(f"cot_{ccy}_oi").diff()
        fx = _series(fx_id)
        series = []
        for c, label, color in REGIMES:
            dates = code.index[code == c]
            pts = [[_ms(d), float(doi[d])] for d in dates if d in doi.index and pd.notna(doi[d])]
            series.append({"name": label, "type": "column", "data": pts, "color": color,
                           "yAxis": 0, "pointRange": 7 * 86400000, "pointPadding": 0.1,
                           "groupPadding": 0, "grouping": False, "borderWidth": 0})
        series.append({"name": fx_label, "type": "line", "yAxis": 1, "color": "rgba(40, 40, 40, 1)",
                       "data": [[_ms(d), float(v)] for d, v in fx.loc["2004":].items()]})
        config = {
            "chart": {"zoomType": "x"},
            "title": {"text": title},
            "xAxis": {"type": "datetime"},
            "yAxis": [{"title": {"text": "每週 OI 變化（口）"}, "opposite": False},
                      {"title": {"text": fx_label}, "opposite": True}],
            "tooltip": {"shared": True, "valueDecimals": 4},
            "legend": {"enabled": True},
            "plotOptions": {"series": {"dataGrouping": {"enabled": False}}},
            "rangeSelector": {"enabled": True, "selected": 1, "buttons": [
                {"type": "month", "count": 6, "text": "6m"}, {"type": "year", "count": 1, "text": "1y"},
                {"type": "year", "count": 3, "text": "3y"}, {"type": "all", "text": "Max"}]},
            "navigator": {"enabled": True},
            "scrollbar": {"enabled": True},
            "series": series,
        }
        return {"config": config, "summary": summary}
    return build


def race_table(highlight, summary_head):
    """賽馬排序：各央行政策利率 12／24 個月變化 vs 同期對美元匯率變化。
    summary 內附完整表格，圖為 12 個月變化的橫條圖。"""
    def build():
        pol = pd.DataFrame({a: _series(f"rate_pol_{a.lower()}") for a, _ in AREAS}).dropna(how="all")
        t = pol.index[-1]
        rows = []
        for a, name in AREAS:
            p = pol[a].dropna()
            r = {"name": name, "area": a, "rate": p.iloc[-1],
                 "ch12": p.iloc[-1] - p.asof(t - pd.DateOffset(months=12)),
                 "ch24": p.iloc[-1] - p.asof(t - pd.DateOffset(months=24)), "fx12": None, "fx24": None}
            if a != "US":
                fx = _series(f"ccy_usdfx_{a.lower()}").resample("ME").last()
                fx.index = fx.index.to_period("M").to_timestamp()
                fx = fx.ffill()
                r["fx12"] = (fx.asof(t) / fx.asof(t - pd.DateOffset(months=12)) - 1) * 100
                r["fx24"] = (fx.asof(t) / fx.asof(t - pd.DateOffset(months=24)) - 1) * 100
            rows.append(r)
        rows.sort(key=lambda r: -r["ch12"])

        f = lambda v, fmt, unit="": "—" if v is None or pd.isna(v) else format(v, fmt) + unit
        trs = "".join(
            f"<tr style='{'background:#fff3cd;font-weight:600' if r['area'] in highlight else ''}'>"
            f"<td>{r['name']}</td><td>{f(r['rate'], '.2f', '%')}</td><td>{f(r['ch12'], '+.2f')}</td>"
            f"<td>{f(r['ch24'], '+.2f')}</td><td>{f(r['fx12'], '+.1f', '%')}</td><td>{f(r['fx24'], '+.1f', '%')}</td></tr>"
            for r in rows)
        th = "".join(f"<th style='padding:2px 10px'>{h}</th>" for h in
                     ["央行", "政策利率", "12M 變化(pp)", "24M 變化(pp)", "12M 對美元", "24M 對美元"])
        table = (f"<table style='margin-top:8px;border-collapse:collapse;text-align:right'>"
                 f"<thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"
                 f"<div style='color:#666;font-size:0.85em'>BIS 月底政策利率，截至 {t:%Y-%m}；匯率為 FRED 月底值"
                 f"（1 單位外幣＝?美元，正值＝該貨幣對美元升值）。</div>")

        config = {
            "chart": {"type": "bar"},
            "title": {"text": f"賽馬排序：各央行 12 個月政策利率變化 vs 同期對美元匯率（{t:%Y-%m}）"},
            "xAxis": {"categories": [r["name"] for r in rows]},
            "yAxis": {"title": {"text": "政策利率變化 (pp)／匯率變化 (%)"},
                      "plotLines": [{"value": 0, "color": "#333", "width": 1}]},
            "tooltip": {"shared": True, "valueDecimals": 2},
            "legend": {"enabled": True},
            "series": [
                {"name": "政策利率 12M 變化 (pp)", "color": "rgba(0, 90, 70, 0.85)",
                 "data": [round(r["ch12"], 3) for r in rows]},
                {"name": "對美元 12M 變化 (%)", "color": "rgba(200, 150, 30, 0.85)",
                 "data": [None if r["fx12"] is None else round(r["fx12"], 2) for r in rows]},
            ],
        }
        return {"config": config, "summary": summary_head + table}
    return build
