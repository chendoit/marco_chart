# -*- coding: utf-8 -*-
"""港股流動性「貧血」觀察：抓資料、算指標、畫圖、印判讀訊號。

來源全部是東方財富 push2his kline API（日 K、不復權），子 agent 實測見
`research/hk-*/report.md`：
- 四大龍頭成交額：116.00700 / 116.09988 / 116.03690 / 116.00941 的「額」欄位
- 全市場成交額：100.HSI 的「額」欄位。子 agent 誤判為恒指成分股成交額；
  2021-01-25、2024-09-30、2024-10-08、2025-04-07 四個紀錄日與新聞報導的大市成交額一致
  （286.9／505.8／620.4／620.9 億×10），所以是全市場（大市）成交額。
- 恒指收盤：100.HSI；恒生綜合中小型股指數：124.HSMSI（2019-08-12 起）；小型股 124.HSSI

產出：
- data/hk_liquidity.csv   原始＋衍生指標（逐日 merge，同日新值覆蓋，舊點保留）
- hk_liquidity.html       兩張圖（對應原文圖一、圖二）
- stdout                  最新讀數與判讀

用法：
    venv\\Scripts\\python.exe analysis\\港股流動性\\scripts\\fetch_data.py          # 增量（最近 30 天）
    venv\\Scripts\\python.exe analysis\\港股流動性\\scripts\\fetch_data.py --full   # 全歷史重抓
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"
CSV = DATA / "hk_liquidity.csv"
HTML = HERE / "hk_liquidity.html"

URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
GIANTS = {"t0700": "116.00700", "t9988": "116.09988", "t3690": "116.03690", "t0941": "116.00941"}
HKT = ZoneInfo("Asia/Hong_Kong")


def kline(secid, beg):
    """回傳 DataFrame(index=date, close, amount)。"""
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57",  # 日期,開,收,高,低,量,額
        "klt": 101, "fqt": 0, "beg": beg, "end": "20500101", "lmt": 100000,
    }
    # 東財偶爾直接斷線（RemoteDisconnected），逐次退避重試
    for attempt in range(6):
        try:
            r = requests.get(URL, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            rows = [k.split(",") for k in (r.json().get("data") or {}).get("klines", [])]
            break
        except (requests.RequestException, ValueError):
            if attempt == 5:
                raise
            time.sleep(2 ** attempt * 2)
    df = pd.DataFrame(rows, columns=["date", "open", "close", "high", "low", "vol", "amount"])
    df.index = pd.to_datetime(df.pop("date"))
    return df[["close", "amount"]].astype(float)


def fetch(beg):
    cols = {}
    for name, secid in GIANTS.items():
        cols[name] = kline(secid, beg)["amount"]
        time.sleep(1.1)
    hsi = kline("100.HSI", beg)
    cols["market_turnover"] = hsi["amount"]
    cols["hsi"] = hsi["close"]
    time.sleep(1.1)
    cols["hs_midsmall"] = kline("124.HSMSI", beg)["close"]
    time.sleep(1.1)
    cols["hs_small"] = kline("124.HSSI", beg)["close"]
    df = pd.DataFrame(cols)
    # 港股 16:10 收市；17:00 前的當日資料是盤中值，丟掉
    now = datetime.now(HKT)
    today = pd.Timestamp(now.date())
    if now.hour < 17 and today in df.index:
        df = df.drop(today)
    return df


def derive(df):
    out = df.copy()
    out["giants_total"] = out[list(GIANTS)].sum(axis=1, min_count=1)
    out["giants_share"] = out["giants_total"] / out["market_turnover"]
    out["giants_share_20d"] = out["giants_share"].rolling(20).mean()
    out["market_turnover_20d"] = out["market_turnover"].rolling(20).mean()
    out["ratio_midsmall_hsi"] = out["hs_midsmall"] / out["hsi"]
    out["ratio_small_hsi"] = out["hs_small"] / out["hsi"]
    return out


def chg(s, n=60):
    s = s.dropna()
    return s.iloc[-1] / s.iloc[-1 - n] - 1


def report(d):
    last = d.dropna(subset=["giants_share_20d"]).iloc[-1]
    m, sh, r = chg(d["market_turnover_20d"]), d["giants_share_20d"].dropna(), chg(d["ratio_midsmall_hsi"])
    sh_chg = sh.iloc[-1] - sh.iloc[-61]
    print(f"最新交易日 {last.name.date()}")
    print(f"  四大龍頭成交佔比 當日 {last.giants_share:.1%}｜20D {last.giants_share_20d:.1%}（60 日變動 {sh_chg:+.1%}）")
    print(f"  全市場成交額 當日 {last.market_turnover/1e8:,.0f} 億｜20D {last.market_turnover_20d/1e8:,.0f} 億（60 日 {m:+.1%}）")
    print(f"  中小型/恒指 {last.ratio_midsmall_hsi:.4f}（60 日 {r:+.1%}）｜恒指 {last.hsi:,.0f}")
    if m < 0 and sh_chg < 0 and r < 0:
        verdict = "三線同降：流動性貧血加深"
    elif m > 0 and r > 0:
        verdict = "成交放量且中小型跑贏：偏向資金輪動／回流，非貧血"
    elif m > 0 and r <= 0:
        verdict = "成交放量但中小型落後：量能未擴散，貧血未解"
    else:
        verdict = "成交縮量、中小型未跌輸：觀望"
    print(f"  判讀：{verdict}；佔比{'低於' if last.giants_share_20d < 0.30 else '高於'} 30% 關口")


def write_html(d):
    def ser(col, scale=1.0, nd=4):
        s = d[col].dropna()
        return [[int(t.value // 10**6), round(v * scale, nd)] for t, v in s.items()]

    series1 = [
        {"name": "四大龍頭成交佔比 20D (%)", "data": ser("giants_share_20d", 100, 2), "color": "#2f6fd6"},
        {"name": "恒生指數", "data": ser("hsi", 1, 0), "yAxis": 1, "color": "#222"},
    ]
    series2 = [
        {"name": "全市場成交額 20D (億港元)", "data": ser("market_turnover_20d", 1e-8, 0), "color": "#d33"},
        {"name": "四大龍頭成交佔比 20D (%)", "data": ser("giants_share_20d", 100, 2), "yAxis": 1, "color": "#2f6fd6"},
        {"name": "恒生綜合中小型股 / 恒指", "data": ser("ratio_midsmall_hsi", 1, 4), "yAxis": 2, "color": "#222"},
    ]
    page = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>港股流動性觀察</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highcharts/11.4.8/highstock.js"></script>
<style>body{{font-family:system-ui,"Microsoft JhengHei",sans-serif;margin:16px;background:#fff;color:#222}}
.c{{height:460px;margin-bottom:32px}}</style></head><body>
<h2>港股流動性觀察（更新至 {d.index[-1].date()}）</h2>
<div id="c1" class="c"></div><div id="c2" class="c"></div>
<script>
const nav={{enabled:true}}, rs={{selected:5}};
Highcharts.stockChart('c1',{{title:{{text:'四大龍頭（騰訊、阿里、美團、中移動）成交額佔全市場比 vs 恒指'}},
 rangeSelector:rs,navigator:nav,legend:{{enabled:true}},
 yAxis:[{{title:{{text:'%'}},opposite:false,plotLines:[{{value:30,color:'#999',dashStyle:'Dash',width:1}}]}},{{title:{{text:'恒指'}}}}],
 series:{json.dumps(series1)}}});
Highcharts.stockChart('c2',{{title:{{text:'全市場成交額 × 龍頭佔比 × 中小型相對強弱'}},
 rangeSelector:rs,navigator:nav,legend:{{enabled:true}},
 yAxis:[{{title:{{text:'億港元'}},opposite:false}},{{title:{{text:'%'}}}},{{title:{{text:'比值'}},offset:60}}],
 series:{json.dumps(series2)}}});
</script></body></html>"""
    HTML.write_text(page, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="從 2018-01-01 全歷史重抓")
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)

    old = pd.read_csv(CSV, index_col="date", parse_dates=True) if CSV.exists() else None
    if args.full or old is None:
        beg = "20180101"
    else:
        beg = (old.index.max() - pd.Timedelta(days=30)).strftime("%Y%m%d")
    new = fetch(beg)
    raw_cols = list(new.columns)
    if old is not None and not args.full:
        new = new.combine_first(old[raw_cols])  # 同日新值優先，舊點保留
    d = derive(new.sort_index())
    d.index.name = "date"
    d.to_csv(CSV, float_format="%.6f")
    write_html(d)
    print(f"寫入 {CSV}（{len(d)} 列，{d.index[0].date()} ~ {d.index[-1].date()}）與 {HTML.name}")
    report(d)


if __name__ == "__main__":
    main()
