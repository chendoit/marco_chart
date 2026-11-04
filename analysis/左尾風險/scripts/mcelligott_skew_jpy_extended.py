"""WN-2026-10-28 補測：(1) 用較長歷史的 SPX 25Δ skew 序列重測「skew 從極平變陡」(2) 日圓升值幅度拉高後的預測力。

序列：lieta_spx_p25_p50_1m（2021-12 起）、gex_spx_put_skew_1m（2024-08 起）；USDJPY = 1 / ccy_usdfx_jp。
執行（在專案根目錄）：
    venv\Scripts\python.exe analysis/左尾風險/scripts/mcelligott_skew_jpy_extended.py

方法同 mcelligott_signal_backtest.py：事件去群聚、前瞻報酬用 SPX（series 2）。skew 轉成近 252 日百分位後，
條件 =「W 日內曾 ≤ lo 百分位，之後首次升破 hi」。注意：本檔 SPX 起點取 2006-03-06 的所有交易日，
與 mcelligott_signal_backtest.py（需 VIX／VVIX 皆有值）略有差異，z ≤ −2.5 事件數 6 vs 7。
"""
import sys, importlib
import numpy as np
import pandas as pd
sys.stdout.reconfigure(encoding="utf-8")
import os; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'flask_highcharts')))
lt=importlib.import_module("app.routes.左尾風險監控")
def S(i):
    s=lt._series(i); s.index=pd.DatetimeIndex(s.index).normalize(); return s[~s.index.duplicated(keep='last')]
spx=S(2); spx=spx[spx.index>="2006-03-06"]
def fw(d,n): 
    f=spx.shift(-n)/spx-1; return f.reindex(d)
def dec(m,gap=21):
    out=[];last=-10**9
    for i,(d,v) in enumerate(m.items()):
        if v and i-last>gap: out.append(d);last=i
    return pd.DatetimeIndex(out)
# ---- skew
for name in ["lieta_spx_p25_p50_1m","gex_spx_put_skew_1m"]:
    s=S(name).reindex(spx.index).dropna() if False else S(name)
    s=s[s.index.isin(spx.index)]
    print("\n##",name,s.index.min().date(),len(s))
    pct=s.rolling(252,min_periods=126).apply(lambda a:(a[:-1]<a[-1]).mean()*100,raw=True)
    for lo,hi,w in [(10,25,20),(15,40,20),(20,50,20),(20,60,10)]:
        m=(pct.rolling(w).min()<=lo)&(pct>=hi)&(pct.shift(1)<hi)
        d=dec(m,10); d=d[d.map(lambda t:spx.index.get_loc(t)+5<len(spx))]
        r=fw(d,5).dropna(); r21=fw(d,21).dropna()
        print(f"低≤{lo}→升破{hi}（{w}日內）：n={len(d)} 1w 中位{r.median()*100:+.2f}% 上漲{(r>0).mean()*100:.0f}% | 1m 中位{r21.median()*100:+.2f}% 上漲{(r21>0).mean()*100:.0f}%(n={len(r21)})")
        if (lo,hi,w)==(20,50,20): print("  日期:",[str(x.date()) for x in d])
    base=fw(s.index,5).dropna(); print(f"基準1w 中位{base.median()*100:+.2f}% 上漲{(base>0).mean()*100:.0f}%")
    # 2024-08 / 2025-04 around
# ---- JPY
jp=S("ccy_usdfx_jp"); u=(1/jp).reindex(spx.index).ffill()
for n in (21,5):
    chg=u.pct_change(n)
    z=(chg-chg.expanding(500).mean())/chg.expanding(500).std()
    print(f"\n## USDJPY {n}日變動")
    base=fw(spx.index,21).dropna(); 
    mx=lambda i:spx.iloc[i:i+22].min()/spx.iloc[i]-1
    allw=np.array([mx(i) for i in range(len(spx)-63)])
    print(f"基準：1w上漲{(fw(spx.index,5).dropna()>0).mean()*100:.0f}% 1m上漲{(base>0).mean()*100:.0f}% 21日內回檔>5% {(allw<-.05).mean()*100:.0f}% >10% {(allw<-.10).mean()*100:.0f}%")
    conds={f"z≤{t}":z<=t for t in (-1.5,-2,-2.5,-3,-3.5)}
    pc=[-0.03,-0.05,-0.07,-0.10] if n==21 else [-0.03,-0.04,-0.05]
    for p in pc: conds[f"變動≤{p*100:.0f}%"]=chg<=p
    for k,m in conds.items():
        d=dec(m); d=d[d.map(lambda t:spx.index.get_loc(t)+63<len(spx))]
        if len(d)==0: print(k,"n=0");continue
        r1=fw(d,5).dropna();r21=fw(d,21).dropna()
        dd=np.array([mx(spx.index.get_loc(t)) for t in d])
        print(f"{k}: n={len(d)} 1w 中位{r1.median()*100:+.1f}% 上漲{(r1>0).mean()*100:.0f}% | 1m 中位{r21.median()*100:+.1f}% 上漲{(r21>0).mean()*100:.0f}% | 21日內回檔>5% {(dd<-.05).mean()*100:.0f}% >10% {(dd<-.10).mean()*100:.0f}% 最大回撤中位{np.median(dd)*100:.1f}%")
        if n==21 and len(d)<=12: print("   日期:",[str(x.date()) for x in d])
