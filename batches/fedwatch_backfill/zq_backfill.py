"""Prototype: rebuild FedWatch next-meeting hike/cut probabilities from Yahoo per-contract ZQ closes."""
import sys, warnings, datetime as dt, io, urllib.request
warnings.filterwarnings("ignore")
sys.path.insert(0, sys.argv[1])
import pandas as pd, yfinance as yf
from cme_fedwatch.calc import calculate, _MONTH_NAMES
from cme_fedwatch.fomc import FOMC_MEETINGS, schedule_horizon
from cme_fedwatch import get_probabilities
import socket; socket.setdefaulttimeout(30)

START = pd.Timestamp(sys.argv[2] if len(sys.argv) > 2 else "2026-07-01")
CODES = "FGHJKMNQUVXZ"

def fred(sid):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={(START-pd.Timedelta(days=10)).date()}"
    df = pd.read_csv(io.BytesIO(__import__("curl_cffi.requests").requests.get(url, impersonate="chrome", timeout=30).content), index_col=0, parse_dates=True)
    return pd.to_numeric(df.iloc[:, 0], errors="coerce").ffill()
lo, hi = fred("DFEDTARL"), fred("DFEDTARU")

# contracts from month before START through +14 months
months = pd.period_range(START.to_period("M") - 1, periods=16, freq="M")
closes = {}
for p in months:
    t = f"ZQ{CODES[p.month-1]}{p.year%100:02d}.CBT"
    h = yf.Ticker(t).history(start=str(START.date() - dt.timedelta(days=5)), auto_adjust=False)
    if len(h):
        closes[(p.year, p.month)] = h["Close"].tz_localize(None)
    print(t, len(h), file=sys.stderr, flush=True)
px = pd.DataFrame(closes)
px = px[px.index >= START]

rows = []
for d, r in px.iterrows():
    sett = [{"month": f"{_MONTH_NAMES[m]} {y%100}", "settle": float(v)} for (y, m), v in r.items() if pd.notna(v)]
    upcoming = [m for m in FOMC_MEETINGS if m > d.date()]   # FedWatch drops meeting on its own day? use > d
    rng = (float(lo.asof(d)), float(hi.asof(d)))
    res = calculate(sett, upcoming, rng, schedule_horizon())
    if not res: continue
    nxt = res[0]; cur = f"{rng[0]:.2f}%-{rng[1]:.2f}%"
    hike = sum(v for k, v in nxt["probabilities"].items() if float(k.split("%")[0]) > rng[0])
    cut = sum(v for k, v in nxt["probabilities"].items() if float(k.split("%")[0]) < rng[0])
    rows.append(dict(date=d.date(), meeting=nxt["date"], target=cur, hike=round(hike,1), cut=round(cut,1), hold=nxt["probabilities"].get(cur, 0.0)))
out = pd.DataFrame(rows).set_index("date")
print(out.to_string())
print("\nCME official (latest settlement) via cme_fedwatch.get_probabilities('next'):")
print(get_probabilities("next"))
import os
od = sys.argv[3]; os.makedirs(od, exist_ok=True)
px.to_csv(os.path.join(od, "zq_yahoo_closes.csv"))
out.to_csv(os.path.join(od, "fedwatch_next_meeting_from_yahoo.csv"))
print("saved to", od)
