"""美元水管流動性：日層 Shock 規則回測（R1、R3、R4a、R6 → 綜合燈號）。

輸入：panel.csv（build_panel.py 產生）、rules.yaml
輸出：backtest_report.md、backtest_daily.csv（主版本（rules.yaml 的 main_variant）的逐日燈號）

無前視：
- 分位數用前 window 個交易日（shift 1），不含當日
- R1、R3 依 avail_lag 往後移一個交易日（SOFR、TGCR 是 T+1 公布）
- z 值的波動率在 build_panel 已用 shift(1)
tests/test_backtest_rules.py 用「截斷資料後結果不變」檢查。

用法：venv\\Scripts\\python.exe backtest_rules.py [--variant v1_修正] [-q]
"""
import copy
import os
import sys

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
LIGHT = {0: "綠", 1: "黃", 2: "橘", 3: "紅"}


# ---------- 設定 ----------

def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(path=os.path.join(HERE, "rules.yaml")):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def variant_config(cfg, name):
    base = {k: v for k, v in cfg.items() if k != "variants"}
    return deep_merge(base, cfg["variants"][name])


def load_panel(path=os.path.join(HERE, "panel.csv")):
    p = pd.read_csv(path, parse_dates=["date"], index_col="date")
    return p.drop(columns=[c for c in p.columns if c[:1] == "R" and c[1:2].isdigit()])


# ---------- 規則 ----------

def day15(idx, months):
    """指定月份的 15 日（遇假日順延到下一個交易日）。"""
    f = pd.Series(False, index=idx)
    for y in range(idx.year.min(), idx.year.max() + 1):
        for m in months:
            d = pd.Timestamp(y, m, 15)
            nxt = idx[idx >= d]
            if len(nxt) and (nxt[0] - d).days <= 4:
                f[nxt[0]] = True
    return f


def calendar_span(p, after_days, refunding_months=()):
    """日曆日本身，加上之後 after_days 個交易日。回傳（日曆日, 季底）。"""
    base = p.month_end.astype(bool) | p.tax_day.astype(bool)
    if refunding_months:
        base |= day15(p.index, refunding_months)
    q0 = p.quarter_end.astype(bool)
    cal, qe = base.copy(), q0.copy()
    for k in range(1, after_days + 1):
        cal |= base.shift(k, fill_value=False)
        qe |= q0.shift(k, fill_value=False)
    return cal, qe


def roll_q(s, q, qc, exclude=None):
    x = s.where(~exclude) if exclude is not None else s
    return x.rolling(qc["window"], min_periods=qc["min_periods"]).quantile(q).shift(1)


def threshold(s, lv, qc, exclude):
    t = roll_q(s, lv["q"], qc, exclude)
    if lv.get("floor") is not None:
        t = np.maximum(t, lv["floor"])
    if lv.get("cap") is not None:
        t = np.minimum(t, lv["cap"])
    return t


def rule_r1(p, c, qc, cal, cal_cfg):
    s = p.s_iorb
    lv = c["levels"]
    excl = cal if c.get("quantile_exclude_calendar") else None
    w = cal_cfg["widen"]["R1_bp"]
    cal5 = cal.astype(int).rolling(lv[2]["mean_days"], min_periods=1).max().astype(bool)
    th1 = threshold(s, lv[1], qc, excl) + w * cal
    th2 = threshold(s, lv[2], qc, excl) + w * cal5
    th3 = threshold(s, lv[3], qc, excl) + w * cal
    l1 = s >= th1
    for k in range(1, lv[1].get("consecutive", 1)):
        l1 &= s.shift(k) >= th1.shift(k)
    l2 = s.rolling(lv[2]["mean_days"]).mean() >= th2
    l3 = s >= th3
    r = pd.Series(np.select([l3, l2, l1], [3, 2, 1], 0), index=s.index)
    if cal_cfg.get("t2_check"):
        # 日曆日當天利差達 1 級門檻；2 個交易日後還在 1 級下限以上且沒回落一半 → 強制 2 級
        hot = cal & (s >= th1)
        stuck = hot.shift(2, fill_value=False) & (s > 0.5 * s.shift(2)) & (s >= lv[1]["floor"])
        r = r.where(~stuck, np.maximum(r, 2))
    g = c.get("rrp_guard")
    if g:
        # 日曆日且 RRP 還有緩衝：屬於窗飾，不算壓力
        r = r.where(~(cal & (p.rrp_bn > g["rrp_bn_gt"])), 0)
    return r


def rule_r3(p, c, qc, cal):
    s = p.s_tgcr
    excl = cal if c.get("quantile_exclude_calendar") else None
    lv = c["levels"]
    l1 = s >= threshold(s, lv[1], qc, excl)
    l2 = s >= threshold(s, lv[2], qc, excl)
    return pd.Series(np.select([l2, l1], [2, 1], 0), index=s.index)


def rule_r4a(p, c, cal, qe, cal_cfg):
    srf = p.srf_bn.fillna(0)
    w = cal_cfg["widen"]["R4a_bn"] * cal
    l1 = srf > c["levels"][1]["gt"] + w
    l2 = srf > c["levels"][2]["gt"] + w
    if c.get("quarter_end_l1_off"):          # 初版：季底不算 1 級
        l1 &= ~p.quarter_end.astype(bool)
    r = pd.Series(np.select([l2, l1], [2, 1], 0), index=srf.index)
    g = c.get("rrp_guard")
    if g:
        mask = (qe if g.get("quarter_end_only") else cal) & (p.rrp_bn > g["rrp_bn_gt"])
        r = r.where(~mask, 0)
    return r


def rule_r6(p, c, funding_prev):
    pre = (np.minimum(p.z_spy, p.z_qqq) < c["pre"]["z_equity"]) & (p.z_gld < c["pre"]["z_gold"])
    t = c["type2"]
    up = p.d10 >= t["d10_bp_ge"]
    if t["mode"] == "loose":
        t2 = up & ((p.d1m <= 0) | (p.d3m <= 0))
    elif t["mode"] == "dtb3":
        t2 = up & (p.d3m <= t["d3m_bp_le"])
    elif t["mode"] == "funding":
        t2 = up & (funding_prev >= 1)
    else:
        raise ValueError(t["mode"])
    return pd.Series(np.select([pre & t2, pre], [2, 1], 0), index=p.index)


def evaluate(p, cfg):
    """回傳逐日規則等級與燈號。所有欄位都已依 avail_lag 對齊到「可得日」。"""
    qc, cal_cfg, rc = cfg["quantile"], cfg["calendar"], cfg["rules"]
    cal, qe = calendar_span(p, cal_cfg.get("after_days", 0), cal_cfg.get("refunding_months") or ())
    out = pd.DataFrame(index=p.index)
    raw = {
        "R1": rule_r1(p, rc["R1"], qc, cal, cal_cfg),
        "R3": rule_r3(p, rc["R3"], qc, cal),
        "R4a": rule_r4a(p, rc["R4a"], cal, qe, cal_cfg),
    }
    for k, r in raw.items():
        r = r.shift(rc[k]["avail_lag"], fill_value=0) if rc[k]["avail_lag"] else r
        out[k] = (r if rc[k].get("enabled", True) else r * 0).astype(int)
    fr = [k for k in cfg["light"]["funding_rules"] if rc[k].get("enabled", True)]
    funding = out[fr].max(axis=1) if fr else pd.Series(0, index=p.index)
    r6 = rule_r6(p, rc["R6"], funding)
    out["R6"] = (r6 if rc["R6"].get("enabled", True) else r6 * 0).astype(int)
    r6 = out.R6
    anymax = out[fr + ["R6"]].max(axis=1)
    out["funding"] = funding
    out["light"] = np.select(
        [((funding >= 2) & (r6 == 2)) | (anymax >= 3),
         (funding >= 2) | ((funding >= 1) & (r6 >= 1)),
         funding >= 1],
        [3, 2, 1], 0)
    # R6 Type II 單獨出現時的燈號（0 = 不單獨升燈）。T+0 的跨資產訊號不必等 T+1 的融資面
    alone = cfg["light"].get("r6_type2_alone", 0)
    if alone:
        out["light"] = np.where(r6 == 2, np.maximum(out["light"], alone), out["light"])
    out["calendar"] = cal
    # 只給事後分類誤報用，不進規則
    out["s_iorb_5d"] = p.s_iorb.rolling(5, min_periods=3).mean()
    return out


# ---------- 評估 ----------

def window(idx, ev, buffer):
    a, b = pd.Timestamp(ev["start"]), pd.Timestamp(ev["end"])
    pos = idx.searchsorted(b, side="right") - 1 + buffer
    b2 = idx[min(pos, len(idx) - 1)]
    return (idx >= a) & (idx <= b2)


def prev_day(idx, d):
    i = idx.get_loc(d)
    return idx[max(i - 1, 0)]


def episodes(flag, gap=2):
    """連續（間隔 ≤ gap 個交易日）的 True 併成一次，回傳 [(start, end)]。"""
    days = np.flatnonzero(flag.values)
    eps = []
    for i in days:
        if eps and i - eps[-1][1] <= gap + 1:
            eps[-1][1] = i
        else:
            eps.append([i, i])
    return [(flag.index[a], flag.index[b]) for a, b in eps]


def score(res, cfg):
    idx = res.index
    ev = cfg["events"]
    buf = ev["detect_buffer_days"]
    pos_mask = pd.Series(False, index=idx)
    pos = []
    for e in ev["positive"]:
        m = window(idx, e, buf)
        pos_mask |= m
        w = res[m]
        pos.append({"事件": e["name"], "最高燈號": int(w.light.max()) if len(w) else -1,
                    "首次 ≥ 黃": first(w, 1), "首次 ≥ 橘": first(w, 2),
                    "R1": int(w.R1.max()), "R3": int(w.R3.max()), "R4a": int(w.R4a.max()), "R6": int(w.R6.max())})
    neg = []
    for e in ev["negative"]:
        w = res[window(idx, e, buf)]
        neg.append({"事件": e["name"], "最高燈號": int(w.light.max()),
                    "R1": int(w.R1.max()), "R3": int(w.R3.max()), "R4a": int(w.R4a.max()), "R6": int(w.R6.max())})
    # 前奏型（事後補入）：只報告有沒有亮燈，不算召回，也不從誤報裡扣掉
    pre = []
    pre_mask = pd.Series(False, index=idx)
    for e in ev.get("precursor") or []:
        m = window(idx, e, buf)
        pre_mask |= m
        w = res[m]
        pre.append({"事件": e["name"], "最高燈號": int(w.light.max()),
                    "橘燈以上天數": int((w.light >= 2).sum()), "交易日": int(len(w)),
                    "首次 ≥ 橘": first(w, 2)})
    eps = [(a, b) for a, b in episodes(res.light >= 2) if not pos_mask[a:b].any()]
    in_pre = [bool(pre_mask[a:b].any()) for a, b in eps]
    # 誤報分兩類：期間內 SOFR−IORB 5 日均曾 ≥ real_bp，代表融資面真的偏緊，只是不在事件表裡
    acc = cfg["acceptance"]
    real_bp = acc["real_pressure_5d_bp"]
    # R1 用前一日利差，所以往前多看 1 個交易日
    real = [bool(res.s_iorb_5d[prev_day(idx, a):b].max() >= real_bp) for a, b in eps]
    years = range(idx[0].year, idx[-1].year + 1)

    def per_year(sel):
        return pd.Series([a.year for (a, _), k in zip(eps, sel) if k], dtype=int) \
            .value_counts().reindex(years, fill_value=0)

    fa_year = per_year([True] * len(eps))
    fa_spur = per_year([not r for r in real])
    recall = sum(r["最高燈號"] >= 2 for r in pos)
    lim = acc["false_alarm_episodes_per_year_max"]
    ok = {
        "召回 ≥橘": recall >= acc["recall_orange_min"],
        "負樣本 ≤黃": all(r["最高燈號"] <= acc["negative_max_light"] for r in neg),
        "假訊號每年 ≤ %d" % lim: bool((fa_spur <= lim).all()),
        "全部誤報每年 ≤ %d（參考）" % lim: bool((fa_year <= lim).all()),
    }
    return {"pos": pos, "neg": neg, "pre": pre, "fa_in_pre": in_pre, "fa_eps": eps, "fa_real": real, "fa_year": fa_year, "fa_spur": fa_spur,
            "recall": recall, "recall_yellow": sum(r["最高燈號"] >= 1 for r in pos), "ok": ok,
            "pos_mask": pos_mask}


def passed(sc):
    return all(v for k, v in sc["ok"].items() if "參考" not in k)


def first(w, lv):
    d = w.index[w.light >= lv]
    return d[0].strftime("%Y-%m-%d") if len(d) else ""


def period_stats(res, sc, cfg):
    rows = []
    for name, (a, b) in cfg["periods"].items():
        r = res.loc[str(a):str(b)]
        n_pos = [p for p, e in zip(sc["pos"], cfg["events"]["positive"]) if str(a) <= str(e["start"]) <= str(b)]
        sel = [str(a) <= e[0].strftime("%Y-%m-%d") <= str(b) for e in sc["fa_eps"]]
        fa = [e for e, k in zip(sc["fa_eps"], sel) if k]
        spur = sum(1 for k, r in zip(sel, sc["fa_real"]) if k and not r)
        yrs = (r.index[-1] - r.index[0]).days / 365.25
        rows.append({"期間": f"{name} {a}～{b}", "正樣本": len(n_pos),
                     "召回（≥橘）": sum(p["最高燈號"] >= 2 for p in n_pos),
                     "誤報（≥橘）": len(fa), "其中假訊號": spur, "每年假訊號": round(spur / yrs, 1),
                     "黃燈以上天數比例": f"{(r.light >= 1).mean():.1%}",
                     "橘燈以上天數比例": f"{(r.light >= 2).mean():.1%}"})
    return rows


# ---------- 報告 ----------

def md(df):
    def f(v):
        if isinstance(v, (bool, np.bool_)):
            return "✓" if v else "✗"
        if isinstance(v, float):
            return "" if v != v else f"{v:g}"
        return str(v)
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "---|" * len(df.columns)
    return "\n".join([head, sep] + ["| " + " | ".join(f(v) for v in row) + " |" for row in df.itertuples(index=False)])


def run(cfg, p, name):
    c = variant_config(cfg, name)
    res = evaluate(p, c)
    return c, res, score(res, c)


def main():
    cfg = load_config()
    p = load_panel()
    L = []
    P = L.append
    P("# 日層 Shock 規則回測（自動產生，backtest_rules.py）\n")
    P(f"資料：{p.index[0].date()}～{p.index[-1].date()}，{len(p)} 個交易日。燈號 0 綠、1 黃、2 橘、3 紅。"
      "R1、R3 已往後移 1 個交易日（T+1 公布）。\n")

    # 1. 版本比較
    P("## 1. 版本比較\n")
    rows, results = [], {}
    for name in cfg["variants"]:
        c, res, sc = run(cfg, p, name)
        results[name] = (c, res, sc)
        rows.append({"版本": name, "召回 ≥橘（/6）": sc["recall"], "召回 ≥黃": sc["recall_yellow"],
                     "負樣本最高燈號": "/".join(str(r["最高燈號"]) for r in sc["neg"]),
                     "誤報": len(sc["fa_eps"]), "其中假訊號": int(sc["fa_spur"].sum()),
                     "假訊號最多一年": int(sc["fa_spur"].max()),
                     "黃燈天數": int((res.light >= 1).sum()), "R6 Type II 天數": int((res.R6 == 2).sum()),
                     "通過": passed(sc)})
    P(md(pd.DataFrame(rows)) + "\n")
    P("負樣本最高燈號依序為 LDI／SVB／日圓平倉。誤報 = 正樣本窗口以外的橘燈以上事件（間隔 ≤ 2 日併成一次）。"
      f"假訊號 = 誤報期間 SOFR−IORB 5 日均從未 ≥ {cfg['acceptance']['real_pressure_5d_bp']}bp"
      "（另一類是融資面真的偏緊、只是不在事件表裡）。\n")

    main_v = cfg["main_variant"]
    c, res, sc = results[main_v]
    P(f"## 2. 主版本 {main_v}：驗收\n")
    P("\n".join(f"- {k}：{'通過' if v else '**未通過**'}" for k, v in sc["ok"].items()) + "\n")
    P("### 正樣本\n")
    P(md(pd.DataFrame(sc["pos"])) + "\n")
    P("### 負樣本\n")
    P(md(pd.DataFrame(sc["neg"])) + "\n")
    if sc["pre"]:
        P("### 前奏型（事後補入，不算召回、不從誤報扣除）\n")
        P(md(pd.DataFrame(sc["pre"])) + "\n")
        P(f"誤報中有 {sum(sc['fa_in_pre'])} 次落在前奏型窗口內（下方明細「前奏型窗口」欄）。"
          "這個窗口是看完回測結果才加的，不能拿來證明規則更準。\n")
    P("### 分期\n")
    P(md(pd.DataFrame(period_stats(res, sc, c))) + "\n")
    P("### 每年誤報次數\n")
    P(md(pd.DataFrame({"誤報": sc["fa_year"], "其中假訊號": sc["fa_spur"]}).rename_axis("年").reset_index()) + "\n")
    P("### 誤報明細\n")
    det = []
    for (a, b), real, ip in zip(sc["fa_eps"], sc["fa_real"], sc["fa_in_pre"]):
        w = res.loc[prev_day(res.index, a):b].join(p[["s_iorb", "s_tgcr", "srf_bn", "rrp_bn", "z_spy", "z_gld", "d10", "d3m"]])
        det.append({"類型": "真實偏緊" if real else "假訊號", "前奏型窗口": ip, "起": a.strftime("%Y-%m-%d"), "迄": b.strftime("%Y-%m-%d"), "最高燈號": int(w.light.max()),
                    "R1": int(w.R1.max()), "R3": int(w.R3.max()), "R4a": int(w.R4a.max()), "R6": int(w.R6.max()),
                    "日曆": bool(w.calendar.any()), "max SOFR−IORB（含前一日）": w.s_iorb.max(),
                    "max SRF": w.srf_bn.max(), "RRP": w.rrp_bn.iloc[0]})
    P((md(pd.DataFrame(det)) if det else "（無）") + "\n")

    # 3. 消融
    P("## 3. 消融（主版本拿掉單一規則）\n")
    rows, lead = [], {"（無）": [r["首次 ≥ 橘"] for r in sc["pos"]]}
    for k in ["R1", "R3", "R4a", "R6"]:
        cc = deep_merge(c, {"rules": {k: {"enabled": False}}})
        r2 = evaluate(p, cc)
        s2 = score(r2, cc)
        lead[f"拿掉 {k}"] = [r["首次 ≥ 橘"] for r in s2["pos"]]
        rows.append({"拿掉": k, "召回 ≥橘": s2["recall"], "召回 ≥黃": s2["recall_yellow"],
                     "負樣本最高燈號": "/".join(str(r["最高燈號"]) for r in s2["neg"]),
                     "誤報": len(s2["fa_eps"]), "其中假訊號": int(s2["fa_spur"].sum()),
                     "黃燈天數": int((r2.light >= 1).sum())})
    P(md(pd.DataFrame([{"拿掉": "（無）", "召回 ≥橘": sc["recall"], "召回 ≥黃": sc["recall_yellow"],
                         "負樣本最高燈號": "/".join(str(r["最高燈號"]) for r in sc["neg"]),
                         "誤報": len(sc["fa_eps"]), "其中假訊號": int(sc["fa_spur"].sum()),
                         "黃燈天數": int((res.light >= 1).sum())}] + rows)) + "\n")
    P("### 正樣本首次亮橘燈的日期（看規則有沒有讓警報提早）\n")
    P(md(pd.DataFrame(lead, index=[r["事件"] for r in sc["pos"]]).rename_axis("事件").reset_index()) + "\n")

    # 4. 每年燈號天數
    P("## 4. 主版本每年燈號天數\n")
    y = res.assign(year=res.index.year).groupby("year").light.agg(
        黃=lambda s: (s == 1).sum(), 橘=lambda s: (s == 2).sum(), 紅=lambda s: (s == 3).sum())
    P(md(y.rename_axis("年").reset_index()) + "\n")

    # 5. 合理性檢查
    P("## 5. 合理性檢查（不是通過條件）\n")
    cols = ["s_iorb", "s_tgcr", "srf_bn", "r_spy", "z_spy", "r_gld", "z_gld", "d10", "d3m", "sector"]
    for e in c["events"]["sanity"] + c["events"]["negative"][:0]:
        w = res.loc[str(e["start"]):str(e["end"])].join(p[cols])
        w = w[["light", "R1", "R3", "R4a", "R6"] + cols].copy()
        w.insert(0, "燈", w.light.map(LIGHT))
        w.index = w.index.strftime("%Y-%m-%d")
        P(f"### {e['name']}\n")
        P(md(w.rename_axis("date").reset_index()) + "\n")
    P("s_iorb、s_tgcr 是當日利差；R1、R3 欄位是前一日利差的判定（T+1 才能用）。\n")

    out = os.path.join(HERE, "backtest_report.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    res.join(p[["s_iorb", "s_tgcr", "srf_bn", "rrp_bn"]]).rename_axis("date").to_csv(
        os.path.join(HERE, "backtest_daily.csv"))
    print(out)
    if "-q" not in sys.argv:
        print("\n".join(L[:8]))


if __name__ == "__main__":
    main()
