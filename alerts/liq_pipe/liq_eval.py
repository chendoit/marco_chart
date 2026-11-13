"""美元水管流動性：日層判定（第 1 階段，影子模式）。

每次執行：
1. 依 lane 和美東時間決定要抓哪些來源（liq_fetch），不相關的時段直接結束、不打 API
2. 從 cache 組 panel → rules.derive → rules.evaluate，得到逐日燈號
3. 寫 state/alerts.jsonl（每次判定一筆 eval；某日燈號第一次出現或改變時一筆 light_change）
   和 state/state.json
4. R9 資料健康：任一序列超過預期公布時間加寬限仍沒有新資料、或抓取失敗 → 推播（新出現與恢復各一次）

兩階推播（v2）：
- 行動級：橘燈以上連續 2 日且有跨資產傳導（R6 >= 1，或 R1/R3/R4a 任一達 3 級）→ 每個 episode 首次發一次，
  橘升紅再發一次升級通知；降回綠燈並連續維持 3 天 → 解除通知。
- 資訊級：只有融資面異常、沒傳導 → 不推播，只進 alerts.jsonl 與每日摘要。
episode 狀態由 rules.replay_episodes 從頭重播（事件用 key 去重，state.json 的 events_seen 記已處理的）。

影子模式（預設）：行動級與解除只記 [WOULD_NOTIFY_ACTION]／[WOULD_NOTIFY_RECOVERY]，不發。
--live-notify 才真的發（liq_notify：有 Telegram 金鑰直接發，否則放進 cron result.json 讓排程器代發）。
R9 資料健康不受影響：任何模式下新出現與恢復都會讓 cron 回 done。

cron 契約：有 CRON_RESULT_PATH 就寫 result.json（status / summary / message），沒有就印在 stdout。

用法：
  venv\\Scripts\\python.exe alerts\\liq_pipe\\liq_eval.py --lane hourly|daily [--force] [--no-fetch] [--shadow | --live-notify]
"""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime, time as dtime

import numpy as np
import pandas as pd
from pandas.tseries.holiday import AbstractHolidayCalendar, GoodFriday, USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import liq_fetch  # noqa: E402
import liq_notify  # noqa: E402
import rules as R  # noqa: E402

STATE = os.path.join(HERE, "state")
NY = "America/New_York"
SHADOW = True          # 預設影子模式；--live-notify 在 main() 裡改成 False

# hourly lane：美東時段 → 要抓的來源群組
HOURLY_PLAN = [
    ((8, 0), (10, 59), ["nyfed_rates", "nyfed_ops"]),    # SOFR、TGCR（T+1 約 08:00）、SRF 早盤（約 08:45）
    ((13, 0), (15, 59), ["nyfed_ops"]),                   # ON RRP（約 13:15）、SRF 午盤（約 14:00）
]
DAILY_GROUPS = list(liq_fetch.GROUPS)


class HealthCal(AbstractHolidayCalendar):
    """聯邦假日 + 耶穌受難日（債市和股市都休）。"""
    rules = USFederalHolidayCalendar.rules + [GoodFriday]


HBDAY = CustomBusinessDay(calendar=HealthCal())

# R9：序列 → (第幾個營業日後公布, 美東公布時刻, 寬限小時)
HEALTH = {
    "sofr": (1, (8, 0), 3), "tgcr": (1, (8, 0), 3),
    "srf_bn": (0, (14, 0), 3), "rrp_bn": (0, (13, 30), 3),
    "dgs10": (1, (16, 30), 6), "dgs1mo": (1, (16, 30), 6), "dtb3": (1, (16, 30), 6),
    "spy": (0, (16, 15), 3), "qqq": (0, (16, 15), 3), "gld": (0, (16, 15), 3),
    "smh": (0, (16, 15), 3), "rsp": (0, (16, 15), 3), "dxy": (0, (17, 30), 3),
    "iorb": (1, (17, 0), 24),
}
VALUE_COLS = ["s_iorb", "s_tgcr", "srf_bn", "rrp_bn", "z_spy", "z_qqq", "z_gld", "r_spy", "r_qqq", "r_gld",
              "d10", "d3m", "sector"]


# ---------- 小工具 ----------

def now_ny():
    return pd.Timestamp.now(tz=NY)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def append_log(rec):
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "alerts.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=_jsonable) + "\n")


def _jsonable(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.isoformat()
    return str(v)


def write_result(status, summary, message=None):
    data = {"status": status, "summary": summary, "needs_human": False}
    if message:
        data["message"] = message
    path = os.environ.get("CRON_RESULT_PATH")
    if path:
        save_json(path, data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def clean(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    return v


# ---------- 抓取計畫 ----------

def plan(lane, t, force):
    """回傳要抓的群組；空串列 = 這個時段不用做事。"""
    if lane == "daily" or force:
        return DAILY_GROUPS if lane == "daily" else sorted({g for _, _, gs in HOURLY_PLAN for g in gs})
    if t.weekday() >= 5:
        return []
    hm = (t.hour, t.minute)
    for a, b, gs in HOURLY_PLAN:
        if a <= hm <= b:
            return gs
    return []


# ---------- panel ----------

def build_panel(today):
    """以 SOFR 公布日為列，加上「最後一個 SOFR 日之後到今天」的營業日（當天的 SRF、收盤先進來）。"""
    s = {n: liq_fetch.load(n) for g in liq_fetch.GROUPS.values() for n in g}
    if s["sofr"].empty:
        raise RuntimeError("cache 沒有 SOFR，先跑 liq_fetch.py")
    idx = s["sofr"].index
    tail = pd.date_range(idx[-1] + R.BDAY, today, freq=R.BDAY)
    idx = idx.append(tail)
    df = pd.DataFrame(index=idx)
    for n, v in s.items():
        df[n] = v.reindex(idx, method="ffill") if n == "iorb" else v.reindex(idx)
    return R.derive(df), {n: (str(v.index.max().date()) if len(v) else None) for n, v in s.items()}


# ---------- R9 資料健康 ----------

def expected_last(t, lag, hm, grace_h):
    """在美東時間 t，序列最新應該到哪一個營業日。"""
    d = t.normalize().tz_localize(None)
    # 今天（若是營業日）的公布時間點
    for back in range(0, 15):
        day = d - back * HBDAY if back else (d if HBDAY.is_on_offset(d) else d - HBDAY)
        pub_day = day + lag * HBDAY if lag else day
        pub = pd.Timestamp.combine(pub_day.date(), dtime(*hm)).tz_localize(NY) + pd.Timedelta(hours=grace_h)
        if pub <= t:
            return day
    return None


def health(t, data_last, fetch_errors):
    issues = {}
    for n, (lag, hm, g) in HEALTH.items():
        exp = expected_last(t, lag, hm, g)
        last = data_last.get(n)
        if exp is not None and (last is None or pd.Timestamp(last) < exp):
            issues[f"stale:{n}"] = f"{n} 最新 {last}，應該已有 {exp.date()}"
    for g, err in fetch_errors.items():
        issues[f"fetch:{g}"] = f"{g} 抓取失敗：{err}"
    return issues


# ---------- v2：episode 事件、前瞻追蹤、推播 ----------

def values_at(panel, d):
    d = pd.Timestamp(d)
    return {c: clean(panel[c].get(d)) for c in VALUE_COLS if c in panel}


def forward_realized(name, base_date, horizons):
    """base_date（含）之前最後一個收盤為基準，已經走完的 T+k 報酬。"""
    s = liq_fetch.load(name).dropna()
    pos = s.index.searchsorted(pd.Timestamp(base_date), side="right") - 1
    if pos < 0:
        return None, {}
    return clean(s.iloc[pos]), {f"T+{k}": round(float(s.iloc[pos + k] / s.iloc[pos] - 1), 4)
                                for k in horizons if pos + k < len(s)}


def tracking(base_date, cfg):
    """state.json 的前瞻追蹤：基準日各資產收盤，以及到目前為止已經走完的 T+1/T+5/T+20 報酬。"""
    u = cfg["investment_utility"]
    out = {"base_date": base_date, "forward": {}}
    for a in u["assets"]:
        base, fw = forward_realized(a.lower(), base_date, u["horizons"])
        out[f"{a.lower()}_base"] = base
        out["forward"][a] = fw
    return out


def handle_events(events, res, panel, cfg, st, shadow, ts, lane):
    """事件去重、記 log、組行動級訊息。
    回傳 (要推播的訊息 [{key, text, tag}], 最近的資訊級事件)。資訊級事件不去重（每日摘要要看得到），log 才去重。"""
    fresh_from = res.index[-min(cfg["notification"]["fresh_days"], len(res))]
    seen = st.setdefault("events_seen", {})
    stats = liq_notify.load_utility_stats()
    messages, info = [], []
    for e in events:
        if pd.Timestamp(e["date"]) < fresh_from:
            continue
        new = e["key"] not in seen
        if e["tier"] != "action":
            info.append(e)
            if new:
                append_log({"ts": ts, "lane": lane, "kind": "info_event", "event": e})
        elif new:
            vals = values_at(panel, e["date"])
            is_rec = e["kind"] == "recovery"
            text = liq_notify.format_recovery(e, vals, stats) if is_rec else liq_notify.format_action(e, vals)
            tag = "WOULD_NOTIFY_RECOVERY" if is_rec else "WOULD_NOTIFY_ACTION"
            append_log({"ts": ts, "lane": lane, "kind": "notify_recovery" if is_rec else "notify_action",
                        "shadow": shadow, "tag": f"[{tag}]" if shadow else "[NOTIFY]", "event": e,
                        "values": vals, "text": text})
            messages.append({"key": e["key"], "text": text, "tag": tag})
        if new:
            seen[e["key"]] = e["date"]
    st["events_seen"] = dict(sorted(seen.items(), key=lambda kv: kv[1])[-300:])
    return messages, info


# ---------- 主流程 ----------

LIGHT_INFO = {
    0: ("🟢", "美元流動性正常，短端融資市場平穩，無明顯壓力訊號。",
        "維持常規觀察即可；留意月底/季底前 R1 融資利差是否提前走闊。"),
    1: ("🟡", "出現早期流動性緊縮或市場結構微幅轉弱訊號（單一維度警示）。",
        "觀察接下來 1～3 個交易日是否擴散至其他維度（例如資金利差與風險資產同步轉弱）。"),
    2: ("🟠", "多維度流動性壓力升溫，資金面與市場面開始出現連動緊縮。",
        "提高警覺：留意 SRF/ON RRP 用量變化與長短天期利差，評估降低高波動部位槓桿。"),
    3: ("🔴", "美元水管出現顯著流動性緊張，資金市場與跨資產風險訊號同步亮紅燈。",
        "高度警戒：密切關注聯準會流動性工具介入與市場劇烈波動風險，優先控管流動性與風險曝險。"),
}


def format_light_message(rec, changes, new, recovered, issues, info=(), pending=()):
    """每日摘要。info：最近的資訊級事件；pending：影子模式下本次「會」發出的行動級／解除通知。"""
    lv = rec["light"]
    emoji, meaning, next_step = LIGHT_INFO.get(lv, ("⚪", "未知燈號狀態。", "請檢查規則設定。"))
    r = rec["rules"]
    v = rec["values"]

    lines = [
        f"{emoji} 美元水管流動性：{rec['light_name']}燈（{rec['date']}）",
        f"• 規則明細：R1(資金)={r['R1']}｜R3={r['R3']}｜R4a(結構)={r['R4a']}｜R6(跨資產)={r['R6']}",
    ]
    if v.get("s_iorb") is not None:
        lines.append(f"• 關鍵指標：SOFR-IORB={v['s_iorb']} bp｜SRF={v.get('srf_bn')}B｜ON RRP={v.get('rrp_bn')}B")
    if changes:
        ch_str = "、".join(f"{c['date']} {R.LIGHT.get(c['from'], '無')}→{R.LIGHT[c['to']]}" for c in changes)
        lines.append(f"• 燈號變動：{ch_str}")
    st = R.classify_stress({"light": lv, "R6": r["R6"]})
    lines.append(f"• 跌勢分類：{st['label']}（{st['category']}）")
    lines.append(f"• 意義：{meaning}")
    lines.append(f"• 下一步可能：{next_step}")
    for e in info:
        what = {"episode_start": "進入橘燈以上 episode", "recovery": "橘燈 episode 解除"}.get(e["kind"], e["kind"])
        lines.append(f"ℹ️ 資訊級（不推播）：{e['date']} {what}｜{e.get('label', '')}")
    for m in pending:
        lines.append(f"🧪 影子模式：本次會發出「{m['tag']}」（key={m['key']}），未實際推播")

    if new or recovered or issues:
        lines.append("")
        lines.append("🩺 資料健康（R9）：")
        lines += [f"⚠️ {val}" for val in new.values()]
        lines += [f"✅ 恢復：{k.split(':', 1)[1]}" for k in recovered]
        if issues and not new:
            lines.append(f"仍有 {len(issues)} 項資料未更新")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", choices=["hourly", "daily"], required=True)
    ap.add_argument("--force", action="store_true", help="hourly 也照抓（忽略時段）")
    ap.add_argument("--no-fetch", action="store_true", help="只用 cache 判定")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--shadow", action="store_true", help="影子模式（預設）：行動級與解除只記 WOULD_NOTIFY")
    g.add_argument("--live-notify", action="store_true", help="行動級與解除真的推播")
    a = ap.parse_args()
    global SHADOW
    SHADOW = not a.live_notify
    force = a.force or os.environ.get("CRON_FORCE") == "1"

    t = now_ny()
    groups = [] if a.no_fetch else plan(a.lane, t, force)
    if not groups and not a.no_fetch:
        write_result("no_change", f"{a.lane}：美東 {t:%a %H:%M} 不是資料公布時段，略過")
        return

    fetch_errors, fetched = {}, {}
    for g in groups:
        try:
            fetched.update(liq_fetch.run([g]))
        except Exception as e:  # noqa: BLE001
            fetch_errors[g] = f"{type(e).__name__}: {str(e)[:200]}"

    cfg = R.load_rules()
    today = t.normalize().tz_localize(None)
    panel, data_last = build_panel(today)
    res = R.evaluate(panel, cfg)
    st = load_json(os.path.join(STATE, "state.json"), {"lights": {}, "health": {}})
    ts = datetime.now().astimezone().isoformat(timespec="seconds")

    # 最近 5 個交易日：燈號第一次出現或被改寫（例如隔天 DGS 進來讓 R6 改判）都記一筆
    changes = []
    for d in res.index[-5:]:
        key = d.strftime("%Y-%m-%d")
        lv = int(res.light[d])
        if st["lights"].get(key) != lv:
            changes.append({"date": key, "from": st["lights"].get(key), "to": lv})
            st["lights"][key] = lv
    st["lights"] = dict(sorted(st["lights"].items())[-400:])

    last = res.index[-1]
    row = res.loc[last]
    rec = {
        "ts": ts, "lane": a.lane, "kind": "eval", "shadow": SHADOW, "date": last.strftime("%Y-%m-%d"),
        "light": int(row.light), "light_name": R.LIGHT[int(row.light)],
        "rules": {k: int(row[k]) for k in ["R1", "R3", "R4a", "R6"]}, "funding": int(row.funding),
        "calendar": bool(row.calendar),
        # R1、R3 用前一日利差：一起記下來方便核對
        "values": {**{c: clean(panel[c].get(last)) for c in VALUE_COLS if c in panel},
                   "s_iorb_prev": clean(panel.s_iorb.shift(1).get(last))},
        "fetched": fetched, "fetch_errors": fetch_errors, "data_last": data_last,
    }
    append_log(rec)
    for ch in changes:
        r = res.loc[pd.Timestamp(ch["date"])]
        append_log({"ts": ts, "lane": a.lane, "kind": "light_change", "shadow": SHADOW, **ch,
                    "rules": {k: int(r[k]) for k in ["R1", "R3", "R4a", "R6"]}})

    # v2：episode 狀態機與兩階推播
    events, v2 = R.replay_episodes(res, cfg)
    messages, info = handle_events(events, res, panel, cfg, st, SHADOW, ts, a.lane)
    sent = liq_notify.dispatch(messages, not SHADOW)
    deferred = sent["deferred"]
    for k in sent["sent"]:
        append_log({"ts": ts, "lane": a.lane, "kind": "notify_sent", "key": k})
    for k, err in sent["errors"].items():
        append_log({"ts": ts, "lane": a.lane, "kind": "notify_error", "key": k, "error": err})
    pending = messages if SHADOW else []
    ep = v2["active_episode"]
    if ep.get("is_active"):
        ep["tracking_forward"] = tracking(ep["start_date"], cfg)
    if v2["recent_recovery"]:
        v2["recent_recovery"]["tracking_forward"] = tracking(v2["recent_recovery"]["recovery_date"], cfg)
    st.update({"last_eval_time": ts, "mode": "shadow" if SHADOW else "live", **v2})

    # R9
    issues = health(t, data_last, fetch_errors)
    old = st.get("health", {})
    new = {k: v for k, v in issues.items() if k not in old}
    recovered = [k for k in old if k not in issues]
    st["health"] = issues
    st["last_run"] = {"ts": ts, "lane": a.lane, "date": rec["date"], "light": rec["light"]}
    save_json(os.path.join(STATE, "state.json"), st)
    if new or recovered:
        append_log({"ts": ts, "lane": a.lane, "kind": "health", "new": new, "recovered": recovered})

    summary = (f"{rec['date']} {rec['light_name']}燈（R1={rec['rules']['R1']} R4a={rec['rules']['R4a']} "
               f"R6={rec['rules']['R6']}）；抓 {','.join(groups) or '無'}"
               + (f"；燈號變動 {len(changes)}" if changes else "")
               + (f"；資料問題 {len(issues)}" if issues else ""))
    summary += (f"；行動級 {len(messages)}" if messages else "") + ("（影子）" if messages and SHADOW else "")
    # 燈號變動屬資訊級，只進每日摘要；hourly 只在 R9 或需要 cron 代發的行動級／解除通知時才叫醒
    if a.lane == "daily" or new or recovered or deferred:
        msg = format_light_message(rec, changes, new, recovered, issues, info, pending)
        if deferred:
            msg = "\n\n".join([m["text"] for m in deferred] + [msg])
        write_result("done", summary, msg)
    else:
        write_result("no_change", summary)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        traceback.print_exc()
        try:
            append_log({"ts": datetime.now().astimezone().isoformat(timespec="seconds"), "kind": "error",
                        "argv": sys.argv[1:], "traceback": tb})
        except Exception:  # noqa: BLE001 — 連寫 log 都失敗時至少 stderr 已有 traceback
            pass
        sys.exit(1)
