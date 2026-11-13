"""美元水管流動性：日層 Shock 規則回測（R1、R3、R4a、R6 → 綜合燈號）。

輸入：panel.csv（build_panel.py 產生）、rules.yaml
輸出：backtest_report.md、backtest_daily.csv（主版本（rules.yaml 的 main_variant）的逐日燈號）

無前視：
- 分位數用前 window 個交易日（shift 1），不含當日
- R1、R3 依 avail_lag 往後移一個交易日（SOFR、TGCR 是 T+1 公布）
- z 值的波動率在 build_panel 已用 shift(1)
tests/test_backtest_rules.py 用「截斷資料後結果不變」檢查。

用法：venv\\Scripts\\python.exe backtest_rules.py [--variant v1_修正] [-q] [--utility]
  --utility：報告附加「投資效用」章節（燈號後 T+1/T+5/T+20 前瞻報酬與 MAE），並寫 utility_stats.json
            （liq_notify 解除通知引用）。價格來自 research/market-prices/market_prices.csv，用收盤價算。
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "alerts", "liq_pipe"))
# 規則邏輯和線上判定共用 alerts/liq_pipe/rules.py
from rules import (LIGHT, calendar_span, day15, deep_merge, evaluate, load_rules,  # noqa: E402,F401
                   replay_episodes, roll_q, rule_r1, rule_r3, rule_r4a, rule_r6, threshold)

PRICES = os.path.join(HERE, "..", "research", "market-prices", "market_prices.csv")


# ---------- 設定 ----------

def load_config(path=os.path.join(HERE, "rules.yaml")):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def variant_config(cfg, name):
    base = {k: v for k, v in cfg.items() if k != "variants"}
    return deep_merge(base, cfg["variants"][name])


def load_panel(path=os.path.join(HERE, "panel.csv")):
    p = pd.read_csv(path, parse_dates=["date"], index_col="date")
    return p.drop(columns=[c for c in p.columns if c[:1] == "R" and c[1:2].isdigit()])


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


# ---------- 投資效用（--utility）----------

def load_prices(assets, idx, path=PRICES):
    """收盤價對齊到回測交易日；沒有價格的日子留 NaN（不 ffill，避免把缺資料當成沒漲跌）。"""
    m = pd.read_csv(path, parse_dates=["date"], usecols=["date", "ticker", "close"])
    return m[m.ticker.isin(assets)].pivot(index="date", columns="ticker", values="close").reindex(idx)


def forward_table(px, horizons, mae_h):
    """逐日、逐資產的前瞻報酬 {A}_T+k 與 {A}_MAE{h}（未來 h 日內相對 t 日收盤的最低報酬，不足 h 日給 NaN）。
    基準價是訊號當天收盤：R6 用當天報酬，R1／R3 已移到可得日，所以當天收盤才是可執行的最早價。"""
    out = {}
    for a in px.columns:
        s = px[a]
        for k in horizons:
            out[f"{a}_T+{k}"] = s.shift(-k) / s - 1
        path = pd.concat([s.shift(-k) / s - 1 for k in range(1, mae_h + 1)], axis=1)
        out[f"{a}_MAE{mae_h}"] = path.min(axis=1, skipna=False)
    return pd.DataFrame(out, index=px.index)


def group_stats(fw, mask, assets, horizons, mae_h, dd):
    """一組日期的前瞻統計：每個資產各一列 dict（數值為小數報酬）。"""
    out = {}
    for a in assets:
        x = fw.loc[mask]
        mae = x[f"{a}_MAE{mae_h}"].dropna()
        row = {"n": int(mask.sum()), f"n_T+{horizons[-1]}": int(x[f"{a}_T+{horizons[-1]}"].notna().sum())}
        for k in horizons:
            row[f"T+{k}"] = float(x[f"{a}_T+{k}"].mean())
        row[f"MAE{mae_h}_mean"] = float(mae.mean())
        row[f"MAE{mae_h}_median"] = float(mae.median())
        row[f"P(MAE{mae_h}<={dd:.0%})"] = float((mae <= dd).mean()) if len(mae) else float("nan")
        out[a] = row
    return out


def utility_section(res, p, ucfg, notif_cfg):
    """回傳 (報告行, stats dict)。ucfg = rules.yaml 的 investment_utility。"""
    hz, assets, bench = ucfg["horizons"], ucfg["assets"], ucfg["benchmark"]
    dd, mae_h = ucfg.get("drawdown_threshold", -0.05), max(hz)
    px = load_prices(assets, res.index)
    fw = forward_table(px, hz, mae_h)
    ev, _ = replay_episodes(res, notif_cfg)
    on = lambda d: pd.Series(res.index.isin(pd.to_datetime(d)), index=res.index)  # noqa: E731
    light2 = res.light >= 2
    start = light2 & ~light2.shift(1, fill_value=False)
    run_id = (light2 != light2.shift(1)).cumsum()
    run_len = light2.groupby(run_id).transform("sum").where(light2, 0)
    run_pos = light2.astype(int).groupby(run_id).cumsum().where(light2, 0)
    n_conf = notif_cfg["notification"]["action_level"]["consecutive_days"]
    # 通過連續過濾的 episode：訊號日取「確認日」（橘燈連續第 n 日）收盤，避免用未來資訊挑選起點日
    starts_ge2 = run_pos == n_conf
    # 事後標籤（只用來看被擋掉的單日尖刺長怎樣，不是可交易訊號）
    starts_1d = start & (run_len < n_conf)
    action = on([e["date"] for e in ev if e["kind"] == "action"])
    recov_all = on([e["date"] for e in ev if e["kind"] == "recovery"])
    recov_act = on([e["date"] for e in ev if e["kind"] == "recovery" and e["tier"] == "action"])
    groups = {
        "baseline": ("全期基準（所有交易日）", pd.Series(True, index=res.index)),
        "orange_start": ("首次亮橘燈以上（episode 第一天）", start),
        "orange_start_ge2d": ("橘燈連續第 2 日（通過連續過濾，確認日收盤）", starts_ge2),
        "orange_start_1d": ("　事後標籤：橘燈只亮 1 日（被擋掉，起點日收盤）", starts_1d),
        "action_alert": ("行動級警報日（橘燈以上連 2 日 + 傳導）", action),
        "recovery": ("解除確認日（全部 episode）", recov_all),
        "recovery_action": ("解除確認日（僅發過行動級者）", recov_act),
        "green_crash": ("綠燈但 SPY 單日 z < −2", (res.light == 0) & (p.z_spy < -2)),
    }
    stats = {k: {"label": lab, "assets": group_stats(fw, m, assets, hz, mae_h, dd)} for k, (lab, m) in groups.items()}

    pc = lambda v: "" if v != v else f"{v:+.2%}"  # noqa: E731
    L = ["## 6. 投資效用（--utility）\n",
         f"價格：{', '.join(assets)} 收盤價（research/market-prices/market_prices.csv，"
         f"{px.dropna(how='all').index[0].date()}～{px.dropna(how='all').index[-1].date()}）。"
         f"報酬 = 訊號日收盤到 T+k 個交易日後收盤；MAE{mae_h} = 之後 {mae_h} 日內相對訊號日收盤的最低報酬"
         f"（越負代表逆向走勢越大）；P(MAE) = MAE 跌到 {dd:.0%} 以下的比例。"
         "價格尾端不足 20 日的日期不計入該欄平均（見「T+20 有效 n」）。\n"
         "訊號日收盤進場是樂觀假設（實務上要看到燈號才動作，最快下一個交易日）。\n"]
    for a in assets:
        rows = []
        for k, (lab, _) in groups.items():
            s = stats[k]["assets"][a]
            rows.append({"情境": lab, "樣本天數": s["n"], f"T+{hz[-1]} 有效 n": s[f"n_T+{hz[-1]}"],
                         **{f"T+{h} 平均": pc(s[f"T+{h}"]) for h in hz},
                         f"MAE{mae_h} 平均": pc(s[f"MAE{mae_h}_mean"]),
                         f"MAE{mae_h} 中位數": pc(s[f"MAE{mae_h}_median"]),
                         f"P(MAE≤{dd:.0%})": "" if s[f"P(MAE{mae_h}<={dd:.0%})"] != s[f"P(MAE{mae_h}<={dd:.0%})"]
                         else f"{s[f'P(MAE{mae_h}<={dd:.0%})']:.0%}"})
        L.append(f"### {a} 前瞻報酬與最大不利走勢\n")
        L.append(md(pd.DataFrame(rows)) + "\n")

    # 假警報與連續過濾
    n_start, n_ge2, n_act = int(start.sum()), int(starts_ge2.sum()), int(action.sum())
    L.append("### 假警報與連續 2 日過濾成效\n")
    rows = []
    for lab, m in [("橘燈 episode 起點（過濾前）", start), ("通過連續 2 日", starts_ge2),
                   ("行動級警報（再加傳導條件）", action)]:
        r = {"層級": lab, "次數": int(m.sum()), "占起點比例": f"{m.sum() / max(n_start, 1):.0%}"}
        for a in assets:
            x = fw.loc[m]
            r[f"{a} T+{hz[-1]}"] = pc(x[f"{a}_T+{hz[-1]}"].mean())
            r[f"{a} MAE{mae_h}"] = pc(x[f"{a}_MAE{mae_h}"].mean())
        rows.append(r)
    L.append(md(pd.DataFrame(rows)) + "\n")
    L.append(f"橘燈起點 {n_start} 次，只亮 1 日 {n_start - n_ge2} 次被連續過濾擋下，行動級警報 {n_act} 次。\n")
    L.append("### 行動級警報與解除明細\n")
    det = []
    for e in ev:
        if e["kind"] in ("action", "escalation", "recovery"):
            d = pd.Timestamp(e["date"])
            r = {"日期": e["date"], "類型": e["kind"], "層級": e["tier"], "燈號": e["light"],
                 "episode 起": e["episode_start"]}
            for a in assets:
                r[f"{a} T+{hz[-1]}"] = pc(fw.loc[d, f"{a}_T+{hz[-1]}"]) if d in fw.index else ""
            det.append(r)
    L.append((md(pd.DataFrame(det)) if det else "（無）") + "\n")
    return L, stats


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

    if "--utility" in sys.argv:
        prod = load_rules()
        ul, ustats = utility_section(res, p, prod["investment_utility"], prod)
        L += ul
        with open(os.path.join(HERE, "utility_stats.json"), "w", encoding="utf-8") as f:
            json.dump({"variant": main_v, "period": f"{p.index[0].date()}～{p.index[-1].date()}",
                       "groups": ustats}, f, ensure_ascii=False, indent=2)

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
