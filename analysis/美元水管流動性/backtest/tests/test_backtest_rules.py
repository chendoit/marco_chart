"""backtest_rules 的機械驗收。

執行：venv\\Scripts\\python.exe -m pytest analysis/美元水管流動性/backtest/tests -q
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backtest_rules as b  # noqa: E402

CUTS = ["2019-09-17", "2020-03-17", "2022-09-28", "2024-10-02", "2025-10-31", "2025-12-31", "2026-10-30"]
COLS = ["R1", "R3", "R4a", "R6", "funding", "light"]


@pytest.fixture(scope="module")
def cfg():
    return b.load_config()


@pytest.fixture(scope="module")
def panel():
    return b.load_panel()


@pytest.mark.parametrize("variant", ["v1_修正", "v2_R3不進燈號", "v2_全部", "v1_R6用融資面"])
def test_no_lookahead(cfg, panel, variant):
    """只給到 t 為止的資料，t 當天的判定要和用全部資料時一樣。"""
    c = b.variant_config(cfg, variant)
    full = b.evaluate(panel, c)
    for t in CUTS:
        part = b.evaluate(panel.loc[:t], c)
        assert part.loc[t, COLS].tolist() == full.loc[t, COLS].tolist(), (variant, t)


def test_r1_r3_use_previous_day(cfg, panel):
    """R1、R3 是 T+1 公布：把當天的利差改成極端值，當天的 R1、R3 不能變。"""
    c = b.variant_config(cfg, cfg["main_variant"])
    t = pd.Timestamp("2026-10-27")
    base = b.evaluate(panel, c)
    p2 = panel.copy()
    p2.loc[t, ["s_iorb", "s_tgcr"]] = 500
    hot = b.evaluate(p2, c)
    assert hot.loc[t, ["R1", "R3"]].tolist() == base.loc[t, ["R1", "R3"]].tolist()
    nxt = panel.index[panel.index.get_loc(t) + 1]
    assert hot.loc[nxt, "R1"] == 3


def test_quantile_excludes_today(cfg, panel):
    s = panel.s_iorb.copy()
    q = b.roll_q(s, 0.99, cfg["quantile"])
    s2 = s.copy()
    s2.iloc[-1] = 10_000
    assert b.roll_q(s2, 0.99, cfg["quantile"]).iloc[-1] == q.iloc[-1]


def mini(**cols):
    n = len(next(iter(cols.values())))
    idx = pd.bdate_range("2030-01-01", periods=n)
    base = dict(s_iorb=0.0, s_tgcr=0.0, srf_bn=0.0, rrp_bn=0.0, month_end=False, quarter_end=False,
                tax_day=False, z_spy=0.0, z_qqq=0.0, z_gld=0.0, d10=0.0, d1m=0.0, d3m=0.0)
    base.update(cols)
    return pd.DataFrame({k: (v if np.ndim(v) else [v] * n) for k, v in base.items()}, index=idx)


def test_r4a_calendar_widen_and_rrp_guard(cfg):
    c = b.variant_config(cfg, cfg["main_variant"])
    p = mini(srf_bn=[15, 15, 15], quarter_end=[False, True, True], month_end=[False, True, True],
             rrp_bn=[0, 0, 500])
    cal, qe = b.calendar_span(p, 0)
    r = b.rule_r4a(p, c["rules"]["R4a"], cal, qe, c["calendar"])
    # 平常日 > 10 → 2 級；日曆日門檻 +10 → 15 只到 1 級；季底且 RRP > 1,000 億 → 0
    assert r.tolist() == [2, 1, 0]


def test_light_combination(cfg):
    c = b.variant_config(cfg, "v1_修正")
    c["rules"]["R1"]["avail_lag"] = 0
    c["rules"]["R3"]["avail_lag"] = 0
    n = 130
    # 前 128 天 0bp 讓分位數穩定，最後兩天看組合
    s = [0.0] * (n - 2) + [3.0, 3.0]
    z = [0.0] * (n - 1) + [-3.0]
    p = mini(s_iorb=s, z_spy=z, z_qqq=z, z_gld=z, d10=[0.0] * (n - 1) + [10.0], d3m=[0.0] * (n - 1) + [-10.0])
    c["quantile"]["min_periods"] = 100
    r = b.evaluate(p, c)
    # 最後一天：R1 1 級（連 2 日 ≥ 3bp）＋ R6 Type II → 融資面 1 級 + R6 → 橘；不是紅（紅要融資面 ≥ 2）
    assert r.R1.iloc[-1] == 1 and r.R6.iloc[-1] == 2
    assert r.light.iloc[-1] == 2


def test_r6_type2_alone_yellow(cfg, panel):
    """v3：融資面綠燈時，R6 Type II 單獨亮黃燈，不升橘。2020-03-12 是唯一的 Type II 日。"""
    c = b.variant_config(cfg, cfg["main_variant"])
    r = b.evaluate(panel, c)
    t = pd.Timestamp("2020-03-12")
    assert r.loc[t, "funding"] == 0 and r.loc[t, "R6"] == 2 and r.loc[t, "light"] == 1
    old = b.evaluate(panel, b.variant_config(cfg, "v2_R3不進燈號"))
    assert old.loc[t, "light"] == 0


def test_main_variant_passes(cfg, panel):
    c = b.variant_config(cfg, cfg["main_variant"])
    sc = b.score(b.evaluate(panel, c), c)
    assert b.passed(sc), sc["ok"]
