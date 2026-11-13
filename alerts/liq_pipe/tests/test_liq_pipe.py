"""alerts/liq_pipe 的測試。

執行：venv\\Scripts\\python.exe -m pytest alerts/liq_pipe/tests -q
"""
import os
import sys

import pandas as pd
import pytest
import yaml

LIQ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.abspath(os.path.join(LIQ, "..", ".."))
BT = os.path.join(ROOT, "analysis", "美元水管流動性", "backtest")
sys.path.insert(0, LIQ)
sys.path.insert(0, BT)
import liq_eval as E  # noqa: E402
import liq_fetch as F  # noqa: E402
import rules as R  # noqa: E402

KEYS = ["quantile", "calendar", "rules", "light"]


def test_prod_rules_match_backtest_main_variant():
    """線上 rules.yaml 必須等於回測主版本展開後的設定，避免兩份規則分岔。"""
    import backtest_rules as b
    cfg = b.load_config()
    main = b.variant_config(cfg, cfg["main_variant"])
    prod = R.load_rules()
    assert prod["source_variant"] == cfg["main_variant"]
    for k in KEYS:
        assert prod[k] == main[k], k


@pytest.mark.skipif(not os.path.exists(F.cache_path("sofr")), reason="沒有 cache，先跑 liq_fetch.py")
def test_live_matches_backtest():
    """線上 panel（2024 起的 cache）和回測 panel，累積滿 250 日後燈號要一樣。"""
    p, _ = E.build_panel(pd.Timestamp("2026-11-09"))
    live = R.evaluate(p, R.load_rules())
    bt = pd.read_csv(os.path.join(BT, "backtest_daily.csv"), parse_dates=["date"], index_col="date")
    j = live.join(bt, rsuffix="_bt", how="inner").loc["2025-03-01":"2026-11-09"]
    assert len(j) > 300
    for c in ["R1", "R3", "R4a", "R6", "light"]:
        assert (j[c] == j[c + "_bt"]).all(), c


def ny(s):
    return pd.Timestamp(s, tz="America/New_York")


def test_hourly_plan():
    assert E.plan("hourly", ny("2026-11-12 08:30"), False) == ["nyfed_rates", "nyfed_ops"]
    assert E.plan("hourly", ny("2026-11-12 14:00"), False) == ["nyfed_ops"]
    assert E.plan("hourly", ny("2026-11-12 11:30"), False) == []
    assert E.plan("hourly", ny("2026-11-14 09:00"), False) == []          # 週六
    assert E.plan("daily", ny("2026-11-12 20:00"), False) == E.DAILY_GROUPS


def test_expected_last():
    # SOFR：T+1 08:00 公布、寬限 3 小時。11/11 是假日，11/10 的值 11/12 08:00 才公布，
    # 所以 11/12 10:00 只要求到 11/09，11:00 之後才要求 11/10
    assert E.expected_last(ny("2026-11-12 10:00"), 1, (8, 0), 3) == pd.Timestamp("2026-11-09")
    assert E.expected_last(ny("2026-11-12 11:30"), 1, (8, 0), 3) == pd.Timestamp("2026-11-10")
    # 平常週：週五 11:30 要求週四的值
    assert E.expected_last(ny("2026-11-20 11:30"), 1, (8, 0), 3) == pd.Timestamp("2026-11-19")
    # 11/11 退伍軍人節（聯邦假日）：11/10 的 SOFR 要到 11/12 才公布
    assert E.expected_last(ny("2026-11-11 15:00"), 1, (8, 0), 3) == pd.Timestamp("2026-11-09")
    # 收盤價：當天 16:15 + 3 小時
    assert E.expected_last(ny("2026-11-13 18:00"), 0, (16, 15), 3) == pd.Timestamp("2026-11-12")
    assert E.expected_last(ny("2026-11-13 20:00"), 0, (16, 15), 3) == pd.Timestamp("2026-11-13")


def test_health_flags_stale_and_fetch_error():
    t = ny("2026-11-13 20:00")
    last = {n: "2026-11-13" for n in E.HEALTH}
    last["sofr"] = "2026-11-10"
    issues = E.health(t, last, {"yahoo": "HTTPError"})
    assert set(issues) == {"stale:sofr", "fetch:yahoo"}


def test_calendar_flags_last_row_month_end():
    """線上最後一列就是月底時也要標出來（回測面板靠「這個月最後一列」判斷，線上不行）。"""
    idx = pd.bdate_range("2026-10-01", "2026-10-30")
    f = R.calendar_flags(idx)
    assert f.month_end.iloc[-1]
    idx2 = pd.bdate_range("2026-10-01", "2026-10-29")
    assert not R.calendar_flags(idx2).month_end.iloc[-1]


def test_rules_yaml_has_no_backtest_only_keys():
    with open(os.path.join(LIQ, "rules.yaml"), encoding="utf-8") as f:
        y = yaml.safe_load(f)
    assert not {"variants", "events", "acceptance", "periods"} & set(y)


# ---------- v2：分類器、episode 狀態機 ----------

def mk(lights, r6=None, r1=None):
    idx = pd.bdate_range("2026-03-02", periods=len(lights))
    r6 = r6 or [0] * len(lights)
    r1 = r1 or [0] * len(lights)
    return pd.DataFrame({"light": lights, "R6": r6, "R1": r1, "R3": 0, "R4a": 0}, index=idx)


def test_classify_stress():
    assert R.classify_stress({"light": 0, "R6": 1})["category"] == "NORMAL_OR_MACRO_ONLY"
    assert R.classify_stress({"light": 2, "R6": 0})["category"] == "UPSTREAM_FUNDING_ONLY"
    assert R.classify_stress({"light": 2, "R6": 1})["category"] == "FUNDING_LIQUIDATION_TYPE1"
    assert R.classify_stress({"light": 3, "R6": 2})["category"] == "FUNDING_CRISIS_TYPE2"
    assert R.classify_stress({"light": 2, "R6": 0})["tier"] == "info"
    assert R.classify_stress({"light": 2, "R6": 1})["tier"] == "action"


def test_check_recovery_needs_cooldown():
    st = {"max_light_in_episode": 2, "green_days": 0}
    r = R.check_recovery(st, 0, 3)
    assert not r["recovered"] and r["green_days"] == 1
    assert R.check_recovery({"max_light_in_episode": 2, "green_days": 2}, 0, 3)["recovered"]
    assert R.check_recovery({"max_light_in_episode": 2, "green_days": 2}, 1, 3)["green_days"] == 0
    assert not R.check_recovery({"max_light_in_episode": 1, "green_days": 5}, 0, 3)["recovered"]


def kinds(ev, tier=None):
    return [e["kind"] for e in ev if tier is None or e["tier"] == tier]


def test_single_day_spike_does_not_trigger_action():
    cfg = R.load_rules()
    ev, _ = R.replay_episodes(mk([0, 2, 0, 0, 0, 0], r6=[0, 1, 0, 0, 0, 0]), cfg)
    assert "action" not in kinds(ev)          # 只亮 1 天，連續 2 日過濾擋下
    assert "recovery" in kinds(ev) and [e for e in ev if e["kind"] == "recovery"][0]["tier"] == "info"


def test_pure_funding_never_action_without_severe():
    cfg = R.load_rules()
    ev, st = R.replay_episodes(mk([2, 2, 2, 2, 2], r6=[0] * 5, r1=[2] * 5), cfg)
    assert kinds(ev, "action") == []
    assert st["active_episode"]["is_active"] and st["consecutive_light_days"] == 5


def test_severe_rule_bypasses_r6_requirement():
    cfg = R.load_rules()
    ev, _ = R.replay_episodes(mk([3, 3, 3], r6=[0] * 3, r1=[3] * 3), cfg)
    assert kinds(ev, "action") == ["action"]
    cfg2 = R.deep_merge(cfg, {"notification": {"action_level": {"severe_rule_level": None}}})
    ev2, _ = R.replay_episodes(mk([3, 3, 3], r6=[0] * 3, r1=[3] * 3), cfg2)
    assert kinds(ev2, "action") == []


def test_action_once_then_escalation_then_recovery_with_debounce():
    cfg = R.load_rules()
    #            橘   橘   橘   紅   綠   橘(反彈) 橘   綠   綠   綠
    lights = [2, 2, 2, 3, 0, 2, 2, 0, 0, 0]
    r6 = [1] * 10
    ev, st = R.replay_episodes(mk(lights, r6=r6), cfg)
    assert kinds(ev) == ["episode_start", "action", "escalation", "recovery"]
    rec = [e for e in ev if e["kind"] == "recovery"][0]
    assert rec["tier"] == "action" and rec["prior_max_light"] == 3
    assert rec["episode_days"] == 10             # 綠一天又回橘，不算解除，仍是同一個 episode
    assert not st["active_episode"]["is_active"] and st["recent_recovery"]["prior_max_light"] == 3


def test_new_episode_after_recovery():
    cfg = R.load_rules()
    ev, st = R.replay_episodes(mk([2, 2, 0, 0, 0, 2, 2], r6=[1] * 7), cfg)
    assert kinds(ev) == ["episode_start", "action", "recovery", "episode_start", "action"]
    assert len({e["key"] for e in ev}) == len(ev)   # key 不重複，重播可去重
    assert st["active_episode"]["is_active"]


def test_prod_rules_has_v2_sections():
    cfg = R.load_rules()
    assert cfg["notification"]["action_level"]["consecutive_days"] == 2
    assert cfg["investment_utility"]["horizons"] == [1, 5, 20]


# ---------- v2：歷史事件重播、推播派發 ----------

@pytest.fixture(scope="module")
def hist_events():
    import backtest_rules as b
    cfg = b.load_config()
    res = b.evaluate(b.load_panel(), b.variant_config(cfg, cfg["main_variant"]))
    return R.replay_episodes(res, R.load_rules())[0]


def _ev(ev, kind, a, b):
    return [e for e in ev if e["kind"] == kind and a <= e["date"] <= b]


def test_replay_2019_09_action_and_recovery(hist_events):
    assert [e["date"] for e in _ev(hist_events, "action", "2019-09-01", "2019-09-30")] == ["2019-09-18"]
    assert [e["date"] for e in _ev(hist_events, "recovery", "2019-10-01", "2019-10-15")] == ["2019-10-10"]


def test_replay_2020_03_action_before_recovery(hist_events):
    a = _ev(hist_events, "action", "2020-03-01", "2020-03-31")
    r = _ev(hist_events, "recovery", "2020-03-01", "2020-04-30")
    assert [e["date"] for e in a] == ["2020-03-18"] and a[0]["light"] == 3
    assert r and r[0]["date"] > a[0]["date"] and r[0]["tier"] == "action"


def test_replay_2025q4_actions(hist_events):
    a = _ev(hist_events, "action", "2025-10-01", "2025-12-31")
    assert [e["date"] for e in a] == ["2025-10-17", "2025-11-28"]
    # 2025-09 的橘燈沒有行動級（沒傳導），解除只算資訊級
    assert _ev(hist_events, "action", "2025-09-01", "2025-09-30") == []
    assert [e["tier"] for e in _ev(hist_events, "recovery", "2025-09-01", "2025-10-10")] == ["info", "info"]


def test_no_action_event_without_two_consecutive_days(hist_events):
    for e in hist_events:
        if e["kind"] in ("action", "escalation"):
            assert e["consecutive_days"] >= 2
            assert e["category"] != "NORMAL_OR_MACRO_ONLY"


def test_format_messages_and_dispatch(monkeypatch):
    import liq_notify as N
    ev = {"kind": "action", "date": "2026-11-12", "episode_start": "2026-11-11", "light": 2,
          "category": "FUNDING_LIQUIDATION_TYPE1", "label": "流動性溢出，股金同跌", "consecutive_days": 2}
    vals = {"s_iorb": 7.2, "s_tgcr": 4.8, "srf_bn": 3.0, "rrp_bn": 10.0, "z_spy": -1.8, "z_gld": -1.6, "d10": 6}
    txt = N.format_action(ev, vals, "2026-11-12T22:00:00-05:00")
    assert "行動級警報" in txt and "+7.2 bp" in txt and "FUNDING_LIQUIDATION_TYPE1" in txt
    rec = {"kind": "recovery", "date": "2026-11-20", "recovery_date": "2026-11-18", "prior_max_light": 2,
           "episode_days": 5}
    stats = {"period": "x", "groups": {"recovery_action": {"assets": {
        "SPY": {"n": 10, "n_T+20": 10, "T+20": 0.0368}, "GLD": {"n": 10, "n_T+20": 10, "T+20": 0.0333}}}}}
    t2 = N.format_recovery(rec, vals, stats, "2026-11-20T22:00:00-05:00")
    assert "危機解除" in t2 and "+3.7%" in t2 and "+3.3%" in t2
    assert "歷史統計" not in N.format_recovery(rec, vals, None, "2026-11-20T22:00:00-05:00")
    msgs = [{"key": "k1", "text": "hi"}]
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert N.dispatch(msgs, live=False)["dry"] == ["k1"]            # 影子：不發也不退回
    d = N.dispatch(msgs, live=True)                                 # live 沒金鑰：退回給 cron 代發
    assert d["deferred"] == msgs and d["sent"] == []
    monkeypatch.setattr(N, "send_telegram", lambda t: True)
    assert N.dispatch(msgs, live=True)["sent"] == ["k1"]
    monkeypatch.setattr(N, "send_telegram", lambda t: (_ for _ in ()).throw(OSError("boom")))
    d = N.dispatch(msgs, live=True)                                 # 發送丟例外：不中斷，退回並記錯誤
    assert d["deferred"] == msgs and "OSError" in d["errors"]["k1"]


def test_handle_events_dedupe_and_stale(monkeypatch, tmp_path):
    monkeypatch.setattr(E, "STATE", str(tmp_path))
    cfg = R.load_rules()
    res = mk([0, 0, 2, 2, 2, 0, 0, 0], r6=[0, 0, 1, 1, 1, 0, 0, 0])
    panel = pd.DataFrame({c: 1.0 for c in E.VALUE_COLS}, index=res.index)
    ev, _ = R.replay_episodes(res, cfg)
    st = {}
    # 最後一日是解除確認日；行動級（第 4 日）已超過 fresh_days，不再推
    m1, _ = E.handle_events(ev, res, panel, cfg, st, True, "t", "daily")
    assert [m["tag"] for m in m1] == ["WOULD_NOTIFY_RECOVERY"]
    m2, _ = E.handle_events(ev, res, panel, cfg, st, True, "t", "daily")
    assert m2 == []                                                 # 同一事件只處理一次
    cfg2 = R.deep_merge(cfg, {"notification": {"fresh_days": 6}})
    st2 = {}
    m3, _ = E.handle_events(ev, res, panel, cfg2, st2, True, "t", "daily")
    assert [m["tag"] for m in m3] == ["WOULD_NOTIFY_ACTION", "WOULD_NOTIFY_RECOVERY"]


def test_liq_eval_end_to_end_shadow_no_notify(monkeypatch, tmp_path):
    """用真 cache 跑一次 --no-fetch：影子模式要寫 state 的 v2 欄位，且不呼叫 Telegram。"""
    if not os.path.exists(F.cache_path("sofr")):
        pytest.skip("沒有 cache")
    import liq_notify as N
    monkeypatch.setattr(E, "STATE", str(tmp_path))
    monkeypatch.setattr(N, "send_telegram", lambda t: pytest.fail("影子模式不該發送"))
    monkeypatch.setattr(sys, "argv", ["liq_eval.py", "--lane", "daily", "--no-fetch"])
    E.main()
    st = E.load_json(os.path.join(str(tmp_path), "state.json"), None)
    assert st["mode"] == "shadow" and {"current_light", "consecutive_light_days", "active_episode"} <= set(st)
