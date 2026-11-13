"""美元水管流動性：日層 Shock 規則（R1、R3、R4a、R6 → 綜合燈號）。

回測（analysis/美元水管流動性/backtest/backtest_rules.py）和線上判定（liq_eval.py）共用這份程式。
規則設定見同目錄 rules.yaml；回測的版本比較在 backtest/rules.yaml。

輸入的 panel（以交易日為列）需要的欄位：
  s_iorb、s_tgcr（bp）、srf_bn、rrp_bn（十億美元）、month_end、quarter_end、tax_day（bool）、
  z_spy、z_qqq、z_gld（20 日波動率標準化的日報酬）、d10、d1m、d3m（bp 日變化）
derive() 從原始序列算出這些欄位。

無前視：分位數用前 window 個交易日（shift 1）；R1、R3 依 avail_lag 往後移（SOFR、TGCR 是 T+1 公布）；
z 值的波動率用 shift(1)。
"""
import copy
import os

import numpy as np
import pandas as pd
import yaml
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

HERE = os.path.dirname(os.path.abspath(__file__))
LIGHT = {0: "綠", 1: "黃", 2: "橘", 3: "紅"}
BDAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())


def load_rules(path=os.path.join(HERE, "rules.yaml")):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def deep_merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


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


# ---------- 日曆與衍生欄位 ----------

def calendar_flags(idx, horizon=10):
    """月底、季底、年底、稅日。月底用「之後的營業日」判斷，所以最後一列也能正確標記
    （美國聯邦假日 ≈ SIFMA 債市假日；兩者不同的日子極少）。"""
    idx = pd.DatetimeIndex(idx)
    future = pd.date_range(idx[-1] + BDAY, periods=horizon, freq=BDAY)
    full = idx.append(future)
    s = pd.Series(full, index=full)
    month_end = (s.groupby(full.to_period("M")).transform("max") == s).reindex(idx)
    quarter_end = month_end & idx.month.isin([3, 6, 9, 12])
    year_end = month_end & (idx.month == 12)
    tax = pd.Series(False, index=idx)
    for y in range(idx.year.min(), idx.year.max() + 1):
        for m in [1, 4, 6, 9, 12]:
            d = pd.Timestamp(y, m, 15)
            nxt = full[full >= d]
            if len(nxt) and (nxt[0] - d).days <= 4 and nxt[0] in tax.index:
                tax[nxt[0]] = True
    return pd.DataFrame({"month_end": month_end.values, "quarter_end": np.asarray(quarter_end),
                         "year_end": np.asarray(year_end), "tax_day": tax.values}, index=idx)


def derive(df):
    """原始序列（利率 %、價格、殖利率 %）→ 規則要的 panel 欄位。
    df 欄位：sofr、tgcr、iorb、srf_bn、rrp_bn、spy、qqq、gld、dgs10、dgs1mo、dtb3；選填 dxy、smh、rsp。"""
    o = pd.DataFrame(index=df.index)
    o["s_iorb"] = ((df.sofr - df.iorb) * 100).round(1)
    o["s_tgcr"] = ((df.sofr - df.tgcr) * 100).round(1)
    o["srf_bn"] = df.srf_bn
    o["rrp_bn"] = df.rrp_bn
    o = o.join(calendar_flags(df.index))

    def z(col):
        r = np.log(df[col]).diff() * 100
        return (r / r.rolling(20, min_periods=15).std().shift(1)).round(2), r.round(2)

    for c in ["spy", "qqq", "gld", "dxy"]:
        if c in df:
            o[f"z_{c}"], o[f"r_{c}"] = z(c)
    if "smh" in df and "rsp" in df:
        o["sector"] = ((np.log(df.smh).diff() - np.log(df.rsp).diff()) * 100).round(2)
    o["d10"] = (df.dgs10.diff() * 100).round(0)
    o["d1m"] = (df.dgs1mo.diff() * 100).round(0)
    o["d3m"] = (df.dtb3.diff() * 100).round(0)
    return o


# ---------- v2：跌勢分類與 episode 狀態機 ----------

def classify_stress(row):
    """把一天的燈號與 R6 翻成「這是哪一種壓力」，回答跌勢是不是融資面壞掉。
    row 需要 light、R6（Series 或 dict 皆可）。tier：action = 融資擠壓且已傳導；info = 只進摘要。"""
    light, r6 = int(row["light"]), int(row["R6"])
    if light == 0:
        return {"category": "NORMAL_OR_MACRO_ONLY", "tier": "none",
                "label": "水管通暢（若市場在跌，屬於估值或總經衝擊，不是融資面）"}
    if light == 1:
        return {"category": "EARLY_WATCH", "tier": "info", "label": "單一維度早期訊號，只觀察"}
    if r6 == 0:
        return {"category": "UPSTREAM_FUNDING_ONLY", "tier": "info", "label": "上游融資吃緊，尚未傳導到股市"}
    if r6 == 1:
        return {"category": "FUNDING_LIQUIDATION_TYPE1", "tier": "action", "label": "流動性溢出，股金同跌"}
    return {"category": "FUNDING_CRISIS_TYPE2", "tier": "action", "label": "嚴重擠壓，國債同遭拋售搶現金"}


def check_recovery(prev_state, current_light, cooldown_days=3, from_min_light=2):
    """解除判定。prev_state：{"max_light_in_episode", "green_days"}（前一日收盤後的 episode 狀態）。
    回傳 {"recovered", "green_days"}：綠燈要連續 cooldown_days 天才確認，中途出現任何非綠燈就重算。"""
    green = prev_state.get("green_days", 0) + 1 if int(current_light) == 0 else 0
    ok = (prev_state.get("max_light_in_episode", 0) >= from_min_light
          and green >= cooldown_days)
    return {"recovered": bool(ok), "green_days": green}


def replay_episodes(res, cfg):
    """從頭重播逐日燈號，得出 episode 與事件。重播（而不是只往前推一天）是為了讓 DGS 隔天進來、
    R6 改判這類回頭修正也不會讓狀態錯亂；事件靠 key 去重，由呼叫端決定要不要推播。

    回傳 (events, state)。events 每筆有 key、kind（episode_start / action / escalation / recovery）、
    date、tier（action / info）。state 是最後一天收盤後的狀態，結構同 state.json 的 v2 欄位。"""
    n = cfg["notification"]
    ac, rc = n["action_level"], n["recovery_alert"]
    sev = ac.get("severe_rule_level")
    events, ep, recent = [], None, None
    consec = 0
    for d, row in res.iterrows():
        light = int(row["light"])
        ds = d.strftime("%Y-%m-%d")
        consec = consec + 1 if light >= ac["min_light"] else 0
        if ep is None and light >= ac["min_light"]:
            ep = {"is_active": True, "start_date": ds, "max_light": light, "green_days": 0,
                  "notified_action": False, "notified_light": 0, "days": 0}
            events.append({**classify_stress(row), "key": f"episode_start|{ds}", "kind": "episode_start",
                           "date": ds, "tier": "info", "light": light, "episode_start": ds})
        if ep is None:
            continue
        ep["days"] += 1
        ep["max_light"] = max(ep["max_light"], light)
        severe = sev is not None and max(int(row["R1"]), int(row["R3"]), int(row["R4a"])) >= sev
        cond = (light >= ac["min_light"] and consec >= ac["consecutive_days"]
                and (not ac["require_r6"] or int(row["R6"]) >= 1 or severe))
        if cond and light > ep["notified_light"]:
            kind = "escalation" if ep["notified_action"] else "action"
            events.append({**classify_stress(row), "key": f"{kind}|{ep['start_date']}|{light}", "kind": kind,
                           "date": ds, "tier": "action", "light": light, "episode_start": ep["start_date"],
                           "consecutive_days": consec})
            ep["notified_action"], ep["notified_light"] = True, light
        chk = check_recovery({"max_light_in_episode": ep["max_light"], "green_days": ep["green_days"]},
                             light, rc["cooldown_days"], rc["from_min_light"])
        ep["green_days"] = chk["green_days"]
        if rc["enabled"] and chk["recovered"]:
            first_green = res.index[res.index.get_loc(d) - rc["cooldown_days"] + 1].strftime("%Y-%m-%d")
            tier = "action" if (ep["notified_action"] or not rc.get("require_action_notified")) else "info"
            events.append({"key": f"recovery|{ep['start_date']}", "kind": "recovery", "date": ds,
                           "tier": tier, "light": 0, "episode_start": ep["start_date"],
                           "recovery_date": first_green, "prior_max_light": ep["max_light"],
                           "episode_days": ep["days"], "action_notified": ep["notified_action"]})
            recent = {"recovery_date": first_green, "confirmed_date": ds,
                      "prior_max_light": ep["max_light"], "episode_start": ep["start_date"]}
            ep = None
    last = res.iloc[-1]
    state = {"current_light": int(last["light"]), "consecutive_light_days": int(consec),
             "active_episode": ep or {"is_active": False}, "recent_recovery": recent}
    return events, state
