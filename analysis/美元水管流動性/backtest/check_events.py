"""逐一核對 WN 的已知壓力事件，以及 2025–2026 的月底／季底／稅日。輸出 events_check.md。"""
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
o = pd.read_csv(os.path.join(HERE, "panel.csv"), parse_dates=["date"], index_col="date")

EVENTS = [
    ("年底交易商資產負債表緊縮", "2018-12-24", "2019-01-03"),
    ("repo 危機", "2019-09-16", "2019-09-20"),
    ("COVID 搶現金", "2020-03-09", "2020-03-23"),
    ("英國 LDI 危機外溢", "2022-09-26", "2022-10-14"),
    ("SVB", "2023-03-09", "2023-03-22"),
    ("日圓 carry 平倉", "2024-08-02", "2024-08-06"),
]
COLS = ["s_iorb", "r1_p95", "R1", "s_tgcr", "R3", "srf_bn", "R4a", "p99_srf", "R2", "o_effr",
        "r_spy", "z_spy", "r_gld", "z_gld", "d10", "d3m", "r_dxy", "R6", "rrp_bn"]
lines = []


def md(d, index=True):
    """不依賴 tabulate 的 markdown 表格。"""
    d = d.reset_index() if index else d
    def f(v):
        if isinstance(v, (bool,)) or str(v) in ("True", "False"):
            return "✓" if str(v) == "True" else ""
        if isinstance(v, float):
            return "" if v != v else f"{v:g}"
        return str(v)
    head = "| " + " | ".join(map(str, d.columns)) + " |"
    sep = "|" + "---|" * len(d.columns)
    body = ["| " + " | ".join(f(v) for v in row) + " |" for row in d.itertuples(index=False)]
    return "\n".join([head, sep] + body)

P = lines.append


def tbl(d, cols):
    d = d[cols].copy()
    d.index = d.index.strftime("%Y-%m-%d")
    return md(d.rename_axis("date"))


P("# 回測事件清單核對（自動產生，check_events.py）\n")
P("## A. 已知事件窗口（前後各 3 個交易日）\n")
summary = []
for name, a, b in EVENTS:
    w = o.loc[pd.Timestamp(a) - pd.tseries.offsets.BDay(3): pd.Timestamp(b) + pd.tseries.offsets.BDay(3)]
    core = o.loc[a:b]
    P(f"### {name}（{a}～{b}）\n")
    P(tbl(w, COLS) + "\n")
    summary.append({
        "事件": name, "窗口": f"{a}～{b}",
        "max SOFR−IORB": core.s_iorb.max(), "max R1": core.R1.max(),
        "max SOFR−TGCR": core.s_tgcr.max(), "max R3": core.R3.max(),
        "max SRF": core.srf_bn.max(), "max R6": core.R6.max(),
        "min z_spy": core.z_spy.min(), "min z_gld": core.z_gld.min(),
    })
P("### 事件摘要\n")
P(md(pd.DataFrame(summary), index=False) + "\n")

r = o.loc["2025-01-01":]
P("## B. 2025-01 起：月底、季底、稅日（含前後 1 日的最大值）\n")
cal = r[r.month_end | r.tax_day]
rows = []
for d in cal.index:
    i = r.index.get_loc(d)
    w = r.iloc[max(i - 1, 0): i + 2]
    tag = "年底" if r.year_end[d] else "季底" if r.quarter_end[d] else "月底" if r.month_end[d] else "稅日"
    if r.tax_day[d] and r.month_end[d]:
        tag += "+稅日"
    rows.append({"日期": d.strftime("%Y-%m-%d"), "類型": tag,
                 "SOFR−IORB 當日": r.s_iorb[d], "±1日 max": w.s_iorb.max(),
                 "SOFR−TGCR max": w.s_tgcr.max(), "SRF max(億)": w.srf_bn.max() * 10,
                 "R1 max": w.R1.max(), "R3 max": w.R3.max(), "R4a max": w.R4a.max(),
                 "RRP(十億)": r.rrp_bn[d], "結算毛額(十億)": w.settle_bn.max()})
P(md(pd.DataFrame(rows), index=False) + "\n")

P("## C. 2025-01 起：任何一條規則觸發的日子\n")
hit = r[(r.R1 > 0) | (r.R3 > 0) | (r.R4a > 0) | (r.R6 > 0) | (r.srf_bn > 0.5)]
P(tbl(hit, ["s_iorb", "r1_p95", "R1", "s_tgcr", "R3", "srf_bn", "R4a", "R2", "R6", "month_end", "quarter_end", "tax_day", "rrp_bn"]) + "\n")

P("## D. 全期 SOFR−IORB 前 25 大日\n")
top = o.nlargest(25, "s_iorb")
P(tbl(top, ["s_iorb", "r1_p95", "R1", "s_tgcr", "srf_bn", "month_end", "quarter_end", "tax_day", "rrp_bn"]) + "\n")

P("## E. 每年 R1/R3/R4a/R6 觸發天數（未排除事件與日曆日）\n")
y = o.assign(year=o.index.year, cal=o.month_end | o.tax_day)
agg = y.groupby("year").agg(
    R1_ge1=("R1", lambda s: (s >= 1).sum()), R1_ge2=("R1", lambda s: (s >= 2).sum()),
    R1_3=("R1", lambda s: (s >= 3).sum()), R3_ge1=("R3", lambda s: (s >= 1).sum()),
    R4a_ge1=("R4a", lambda s: (s >= 1).sum()), R6_ge1=("R6", lambda s: (s >= 1).sum()),
    R6_2=("R6", lambda s: (s >= 2).sum()))
cal_r1 = y[y.cal & (y.R1 >= 2)].groupby("year").size().rename("R1_ge2_on_cal")
P(md(agg.join(cal_r1).fillna(0).astype(int).rename_axis("year")) + "\n")

out = os.path.join(HERE, "events_check.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(out)
if "-q" not in sys.argv:
    print("\n".join(lines[:3]))
    print(pd.DataFrame(summary).to_string())
