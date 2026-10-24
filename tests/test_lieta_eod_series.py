import json
import os
import pickle
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

# LIETA_CONVERTER_DIR：變異驗證時指向被改壞的 converter 副本
sys.path.insert(0, os.getenv("LIETA_CONVERTER_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import get_lieta_eod_series as m  # noqa: E402

D1, D2, D3 = "2026-10-20", "2026-10-21", "2026-10-22"


def _dt(s):
    return datetime.strptime(s, "%Y-%m-%d").replace(hour=8)


class LietaEodSeriesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "eod_metrics.db")
        self.out = os.path.join(self.tmp.name, "out")
        self.vix_pkl = os.path.join(self.tmp.name, "vix.pkl")
        conn = sqlite3.connect(self.db)
        conn.executescript("""
            CREATE TABLE vx_curve (date TEXT, symbol TEXT, expiration TEXT, dte INTEGER,
                settlement REAL, prev_settlement REAL, open REAL, high REAL, low REAL,
                PRIMARY KEY (date, symbol));
            CREATE TABLE gex_screener (
                date TEXT NOT NULL, ticker TEXT NOT NULL, spot_price REAL, net_gex REAL,
                regime_raw TEXT, gamma_flip REAL, flip_distance_pct REAL,
                flip_distance_pct_raw REAL, call_wall REAL, put_wall REAL,
                skew_pctl_1m REAL, put_skew_pctl_1m REAL, protection_cost_25_1m REAL,
                protection_cost_spread_25_10_1m REAL, rv_trend REAL,
                is_stale INTEGER NOT NULL DEFAULT 0, src_date TEXT,
                PRIMARY KEY (date, ticker));
            CREATE TABLE iv_rv (date TEXT, ticker TEXT, maturity TEXT, iv REAL, rv REAL,
                PRIMARY KEY (date, ticker, maturity));
        """)
        vx = [
            # D1：VX1 dte=10 → 20、VX2 dte=40 → 23；30 天內插 = 21.5
            (D1, "VXV1", 10, 20.0), (D1, "VXV2", 40, 23.0), (D1, "VXV3", 70, 24.0),
            # D2：只有 1 個合約 → VX2 跳過
            (D2, "VXV1", 9, 18.0),
            # D3：亂序寫入 + VX1 倒掛（VX1 > VX2）；30 天剛好等於 VX2 的 dte
            (D3, "VXV2", 30, 19.0), (D3, "VXV1", 8, 21.0),
        ]
        conn.executemany(
            "INSERT INTO vx_curve (date, symbol, dte, settlement) VALUES (?,?,?,?)", vx)
        # (date, ticker, spot, regime, flip_distance_pct, flip_distance_pct_raw, prot, is_stale)
        # flip_distance_pct 已是 WN 正負號（= −raw）；D3 SPX 為 is_stale=1 的列
        scr = [
            (D1, "SPX", 7700.5, "+GEX", 1.5, -1.5, 0.0123, 0),
            (D2, "SPX", 7650, "NEUTRAL", 0.2, -0.2, None, 0),
            (D3, "SPX", None, "-GEX", -1.3, 1.3, 0.015, 1),
            (D2, "QQQ", 715, "weird", -0.4, 0.4, "", 0),
            (D3, "QQQ", 720, "+GEX", -0.5, 0.5, 0.033, 0),
        ]
        conn.executemany(
            "INSERT INTO gex_screener (date, ticker, spot_price, regime_raw, "
            "flip_distance_pct, flip_distance_pct_raw, protection_cost_25_1m, is_stale) "
            "VALUES (?,?,?,?,?,?,?,?)", scr)
        # lieta iv_rv_series 的 iv / rv 是小數（0.16 = 16 vol 點）
        ivrv = [
            (D1, "SPX", "1m", 0.16, 0.12), (D2, "SPX", "1m", 0.17, None),
            (D3, "SPX", "1m", None, 0.14), (D1, "SPX", "3m", 0.99, 0.99),
            (D1, "QQQ", "1m", 0.22, 0.185),
        ]
        conn.executemany("INSERT INTO iv_rv VALUES (?,?,?,?,?)", ivrv)
        conn.commit()
        conn.close()
        with open(self.vix_pkl, "wb") as f:
            pickle.dump({"title": "CBOE VIX", "data": [
                [_dt(D1), 16.0], [_dt(D2), 17.5], [_dt(D3), 20.0]]}, f)

    def _run(self):
        m.fetch_lieta_eod_series(self.db, self.out, self.vix_pkl)

    def _load(self, name):
        with open(os.path.join(self.out, f"{name}.pkl"), "rb") as f:
            obj = pickle.load(f)
        self.assertIn("title", obj)
        return {d: v for d, v in obj["data"]}

    def test_series_ids_complete(self):
        self._run()
        names = {f[:-4] for f in os.listdir(self.out) if f.endswith(".pkl")}
        expected = {"lieta_vx1", "lieta_vx2", "lieta_vx1_vx2_spread",
                    "lieta_vx1_vix_basis", "lieta_vx_contango_30d"}
        for t in ("spx", "qqq"):
            expected |= {f"lieta_{t}_spot", f"lieta_{t}_flip_dist_pct",
                         f"lieta_{t}_regime", f"lieta_{t}_protection_cost_1m",
                         f"lieta_{t}_iv1m", f"lieta_{t}_rv1m", f"lieta_{t}_vrp"}
        self.assertTrue(expected <= names, expected - names)
        # 沒資料的 ticker 不產空 pkl
        self.assertNotIn("lieta_smh_spot", names)

    def test_vx_levels_and_vx2_skipped_when_single_contract(self):
        self._run()
        self.assertEqual(self._load("lieta_vx1"),
                         {_dt(D1): 20.0, _dt(D2): 18.0, _dt(D3): 21.0})
        # D2 只有 1 個合約 → 無 VX2
        self.assertEqual(self._load("lieta_vx2"), {_dt(D1): 23.0, _dt(D3): 19.0})

    def test_vx_spread_basis_contango(self):
        self._run()
        spread = self._load("lieta_vx1_vx2_spread")
        self.assertEqual(set(spread), {_dt(D1), _dt(D3)})
        self.assertAlmostEqual(spread[_dt(D1)], -3.0)
        self.assertAlmostEqual(spread[_dt(D3)], 2.0)  # > 0 = 前端倒掛

        basis = self._load("lieta_vx1_vix_basis")
        self.assertAlmostEqual(basis[_dt(D1)], 4.0)
        self.assertAlmostEqual(basis[_dt(D2)], 0.5)
        self.assertAlmostEqual(basis[_dt(D3)], 1.0)

        ct = self._load("lieta_vx_contango_30d")
        # D1：20 + (23−20)*(30−10)/(40−10) = 22.0；22/16 − 1 = 37.5%
        self.assertAlmostEqual(ct[_dt(D1)], (22.0 / 16.0 - 1) * 100)
        # D2：只有 1 個合約，無法內插 → 跳過
        self.assertNotIn(_dt(D2), ct)
        # D3：30 天剛好是 VX2 → 19/20 − 1 = −5%
        self.assertAlmostEqual(ct[_dt(D3)], -5.0)

    def test_regime_mapping_and_missing_values(self):
        self._run()
        regime = self._load("lieta_spx_regime")
        self.assertEqual(regime, {_dt(D1): 1.0, _dt(D2): 0.0, _dt(D3): -1.0})
        # 未知字串不補 0
        self.assertEqual(self._load("lieta_qqq_regime"), {_dt(D3): 1.0})
        # spot NULL → 該點跳過
        spot = self._load("lieta_spx_spot")
        self.assertEqual(spot, {_dt(D1): 7700.5, _dt(D2): 7650.0})
        # flip 照抄落地值（已是負 = 跌破），不用 flip_distance_pct_raw、不再取負；
        # D3 的列 is_stale=1 仍要輸出
        flip = self._load("lieta_spx_flip_dist_pct")
        self.assertEqual(flip, {_dt(D1): 1.5, _dt(D2): 0.2, _dt(D3): -1.3})
        # 保護成本 None / 空字串 → 跳過
        prot = self._load("lieta_spx_protection_cost_1m")
        self.assertEqual(prot, {_dt(D1): 0.0123, _dt(D3): 0.015})
        self.assertEqual(self._load("lieta_qqq_protection_cost_1m"), {_dt(D3): 0.033})

    def test_stale_screener_rows_still_exported(self):
        self._run()
        self.assertEqual(self._load("lieta_spx_regime")[_dt(D3)], -1.0)
        self.assertEqual(self._load("lieta_spx_flip_dist_pct")[_dt(D3)], -1.3)

    def _assert_series(self, name, expected):
        got = self._load(name)
        self.assertEqual(set(got), set(expected))
        for d, v in expected.items():
            self.assertAlmostEqual(got[d], v, places=9)

    def test_ivrv_only_1m_and_missing_skipped(self):
        self._run()
        # 小數 → vol 點（×100）
        self._assert_series("lieta_spx_iv1m", {_dt(D1): 16.0, _dt(D2): 17.0})
        self._assert_series("lieta_spx_rv1m", {_dt(D1): 12.0, _dt(D3): 14.0})
        # vrp 只在 iv、rv 都有時才有點；maturity=3m 的 0.99 不應混入
        self._assert_series("lieta_spx_vrp", {_dt(D1): 4.0})
        self._assert_series("lieta_qqq_vrp", {_dt(D1): 3.5})

    def test_missing_vix_pkl_skips_basis_and_contango(self):
        m.fetch_lieta_eod_series(self.db, self.out, os.path.join(self.tmp.name, "nope.pkl"))
        names = set(os.listdir(self.out))
        self.assertIn("lieta_vx1.pkl", names)
        self.assertNotIn("lieta_vx1_vix_basis.pkl", names)
        self.assertNotIn("lieta_vx_contango_30d.pkl", names)

    def test_missing_db_is_noop(self):
        m.fetch_lieta_eod_series(os.path.join(self.tmp.name, "none.db"), self.out, self.vix_pkl)
        self.assertFalse(os.path.exists(self.out))


class LietaVxEdgeCasesTest(unittest.TestCase):
    """VX1/VX2 選取與 30 天內插的邊界案例；每個案例一個日期。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "eod_metrics.db")
        self.out = os.path.join(self.tmp.name, "out")
        self.vix_pkl = os.path.join(self.tmp.name, "vix.pkl")

    def _build(self, vx, vix):
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE vx_curve (date TEXT, symbol TEXT, expiration TEXT, "
                     "dte INTEGER, settlement REAL, PRIMARY KEY (date, symbol))")
        conn.executemany(
            "INSERT INTO vx_curve (date, symbol, dte, settlement) VALUES (?,?,?,?)", vx)
        conn.commit()
        conn.close()
        with open(self.vix_pkl, "wb") as f:
            pickle.dump({"title": "CBOE VIX", "data": [[_dt(d), v] for d, v in vix]}, f)
        m.fetch_lieta_eod_series(self.db, self.out, self.vix_pkl)

    def _load(self, name):
        path = os.path.join(self.out, f"{name}.pkl")
        if not os.path.exists(path):
            return {}
        with open(path, "rb") as f:
            return {d: v for d, v in pickle.load(f)["data"]}

    def test_contango_uses_vix_spot_when_vx1_dte_over_30(self):
        # VX1 dte=40 → F30 = 20 + (22−20)*30/40 = 21.5；21.5/20 − 1 = 7.5%
        self._build([(D1, "A", 40, 22.0), (D1, "B", 70, 23.0)], [(D1, 20.0)])
        ct = self._load("lieta_vx_contango_30d")
        self.assertAlmostEqual(ct[_dt(D1)], 7.5)

    def test_contango_not_extrapolated_when_all_dte_below_30(self):
        self._build([(D1, "A", 5, 18.0), (D1, "B", 20, 19.0)], [(D1, 17.0)])
        self.assertEqual(self._load("lieta_vx_contango_30d"), {})
        # 其他序列照常輸出
        self.assertEqual(self._load("lieta_vx1"), {_dt(D1): 18.0})
        self.assertAlmostEqual(self._load("lieta_vx1_vix_basis")[_dt(D1)], 1.0)

    def test_expiring_contract_excluded_from_vx1_vx2(self):
        # 到期日當天 dte=0 的合約不當 VX1；VX1 = dte 28、VX2 = dte 56
        self._build([(D1, "A", 0, 15.0), (D1, "B", 28, 19.0), (D1, "C", 56, 20.0)],
                    [(D1, 18.0)])
        self.assertEqual(self._load("lieta_vx1"), {_dt(D1): 19.0})
        self.assertEqual(self._load("lieta_vx2"), {_dt(D1): 20.0})
        self.assertAlmostEqual(self._load("lieta_vx1_vx2_spread")[_dt(D1)], -1.0)
        self.assertAlmostEqual(self._load("lieta_vx1_vix_basis")[_dt(D1)], 1.0)

    def test_null_or_zero_vx1_not_replaced_by_vx2(self):
        vx = []
        for d, p1 in ((D1, None), (D2, 0.0)):
            vx += [(d, "A", 10, p1), (d, "B", 40, 23.0), (d, "C", 70, 24.0)]
        self._build(vx, [(D1, 16.0), (D2, 16.0)])
        # VX1 缺價 → 當日 vx1 / spread / basis 無點；VX2 仍是第二個合約（23，不是 VX3 的 24）
        self.assertEqual(self._load("lieta_vx1"), {})
        self.assertEqual(self._load("lieta_vx1_vx2_spread"), {})
        self.assertEqual(self._load("lieta_vx1_vix_basis"), {})
        self.assertEqual(self._load("lieta_vx2"), {_dt(D1): 23.0, _dt(D2): 23.0})

    def test_warns_when_vix_older_than_vx(self):
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level="WARNING")
        try:
            self._build([(D1, "A", 10, 20.0), (D2, "A", 9, 21.0)], [(D1, 16.0)])
        finally:
            m.logger.remove(sink_id)
        self.assertTrue(any("VIX last date" in s for s in msgs), msgs)

    def test_no_warning_when_vix_up_to_date(self):
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level="WARNING")
        try:
            self._build([(D1, "A", 10, 20.0), (D2, "A", 9, 21.0)], [(D1, 16.0), (D2, 17.0)])
        finally:
            m.logger.remove(sink_id)
        self.assertFalse(any("VIX last date" in s for s in msgs), msgs)


class LietaWarningsTest(unittest.TestCase):
    """未知 regime 值、iv_rv 單日尖刺只寫 warning，不改動資料。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "eod_metrics.db")
        self.out = os.path.join(self.tmp.name, "out")
        self.vix_pkl = os.path.join(self.tmp.name, "vix.pkl")

    def _run(self, scr=(), ivrv=()):
        conn = sqlite3.connect(self.db)
        conn.executescript("""
            CREATE TABLE gex_screener (date TEXT, ticker TEXT, spot_price REAL,
                regime_raw TEXT, flip_distance_pct REAL, protection_cost_25_1m REAL);
            CREATE TABLE iv_rv (date TEXT, ticker TEXT, maturity TEXT, iv REAL, rv REAL);
        """)
        conn.executemany("INSERT INTO gex_screener (date, ticker, regime_raw) VALUES (?,?,?)",
                         scr)
        conn.executemany("INSERT INTO iv_rv VALUES (?,?,'1m',?,?)", ivrv)
        conn.commit()
        conn.close()
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level="WARNING")
        try:
            m.fetch_lieta_eod_series(self.db, self.out, self.vix_pkl)
        finally:
            m.logger.remove(sink_id)
        return msgs

    def _load(self, name):
        with open(os.path.join(self.out, f"{name}.pkl"), "rb") as f:
            return {d: v for d, v in pickle.load(f)["data"]}

    def test_unknown_regime_warns_once_with_counts(self):
        msgs = self._run(scr=[
            (D1, "SPX", "+GEX"), (D2, "SPX", "SUPER"), (D3, "SPX", "SUPER"),
            (D1, "QQQ", "weird"), (D2, "QQQ", None), (D3, "QQQ", "  "),
        ])
        hits = [s for s in msgs if "Unknown regime_raw" in s]
        self.assertEqual(len(hits), 1, msgs)
        self.assertIn("'SUPER' x2", hits[0])
        self.assertIn("'weird' x1", hits[0])
        # 未知值仍不補 0
        self.assertEqual(self._load("lieta_spx_regime"), {_dt(D1): 1.0})

    def test_known_regimes_no_warning(self):
        msgs = self._run(scr=[(D1, "SPX", "+GEX"), (D2, "SPX", "NEUTRAL"), (D3, "SPX", "-GEX")])
        self.assertFalse(any("Unknown regime_raw" in s for s in msgs), msgs)

    def test_ivrv_outlier_warns_but_keeps_point(self):
        # HYG iv：7 → 27 → 7，偏離鄰日中位數 3.9 倍且差 20 vol 點
        days = ["2026-10-14", "2026-10-15", "2026-10-16", "2026-10-19"]
        rows = [(d, "HYG", iv, 0.05) for d, iv in zip(days, (0.07, 0.07, 0.27, 0.07))]
        msgs = self._run(ivrv=rows)
        hits = [s for s in msgs if "outlier" in s]
        self.assertEqual(len(hits), 1, msgs)
        self.assertIn("lieta_hyg_iv1m", hits[0])
        self.assertIn("2026-10-16", hits[0])
        # 只警告不刪點
        self.assertEqual(len(self._load("lieta_hyg_iv1m")), 4)

    def test_ivrv_small_swings_not_flagged(self):
        # 倍數 > 3 但絕對差 ≤ 3 vol 點（2 → 5）；以及絕對差大但倍數不到 3（20 → 30）
        days = ["2026-10-14", "2026-10-15", "2026-10-16"]
        rows = [(d, "TLT", iv, 0.02) for d, iv in zip(days, (0.02, 0.05, 0.02))]
        rows += [(d, "SPX", iv, 0.02) for d, iv in zip(days, (0.20, 0.30, 0.20))]
        msgs = self._run(ivrv=rows)
        self.assertFalse(any("outlier" in s for s in msgs), msgs)


class LietaSkewTermTest(unittest.TestCase):
    """hist_skew（put_skew3m / skew3m / pctl1y）與 term_iv（p25_atm_1m / term_slope）。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "eod_metrics.db")
        self.out = os.path.join(self.tmp.name, "out")
        self.vix_pkl = os.path.join(self.tmp.name, "vix.pkl")

    def _build(self, skew=None, term=None, level="INFO"):
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE vx_curve (date TEXT, dte INTEGER, settlement REAL)")
        if skew is not None:
            conn.execute("CREATE TABLE hist_skew (date TEXT, ticker TEXT, maturity TEXT, "
                         "skew REAL, call_skew REAL, put_skew REAL, "
                         "PRIMARY KEY (date, ticker, maturity))")
            conn.executemany("INSERT INTO hist_skew VALUES (?,?,?,?,?,?)", skew)
        if term is not None:
            conn.execute("CREATE TABLE term_iv (date TEXT, ticker TEXT, expiration TEXT, dte INTEGER, "
                         "c25_iv REAL, p25_iv REAL, c50_iv REAL, p50_iv REAL, atm_iv REAL, "
                         "premarket INTEGER, PRIMARY KEY (date, ticker, expiration))")
            conn.executemany(
                "INSERT INTO term_iv (date, ticker, expiration, dte, p25_iv, atm_iv, premarket) "
                "VALUES (?,?,?,?,?,?,?)", term)
        conn.commit()
        conn.close()
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level=level)
        try:
            m.fetch_lieta_eod_series(self.db, self.out, self.vix_pkl)
        finally:
            m.logger.remove(sink_id)
        return msgs

    def _load(self, name):
        path = os.path.join(self.out, f"{name}.pkl")
        if not os.path.exists(path):
            return {}
        with open(path, "rb") as f:
            obj = pickle.load(f)
        self.assertIn("title", obj)
        return {d: v for d, v in obj["data"]}

    def _days(self, n, start="2025-01-01"):
        d0 = datetime.strptime(start, "%Y-%m-%d")
        return [(d0 + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]

    # ---- hist_skew ----
    def test_skew_series_and_pkl_format(self):
        self._build(skew=[(D1, "SPX", "3m", 0.9, 0.8, 1.1), (D2, "SPX", "3m", None, 0.8, 1.2),
                          (D3, "SPX", "3m", 0.95, None, None),
                          (D1, "SPX", "1m", 9.9, 9.9, 9.9)])
        self.assertEqual(self._load("lieta_spx_put_skew3m"), {_dt(D1): 1.1, _dt(D2): 1.2})
        self.assertEqual(self._load("lieta_spx_skew3m"), {_dt(D1): 0.9, _dt(D3): 0.95})
        with open(os.path.join(self.out, "lieta_spx_put_skew3m.pkl"), "rb") as f:
            obj = pickle.load(f)
        self.assertEqual(set(obj), {"title", "data"})
        d, v = obj["data"][0]
        self.assertIsInstance(d, datetime)
        self.assertEqual(d.hour, 8)
        self.assertIsInstance(v, float)

    def test_pctl1y_requires_126_points_and_uses_252_window(self):
        days = self._days(300)
        up = [(d, "SPX", "3m", 1.0, 1.0, 1.0 + i * 0.001) for i, d in enumerate(days)]
        down = [(d, "TLT", "3m", 1.0, 1.0, 2.0 - i * 0.001) for i, d in enumerate(days)]
        short = [(d, "QQQ", "3m", 1.0, 1.0, 1.0 + i * 0.001) for i, d in enumerate(days[:125])]
        flat = [(d, "SMH", "3m", 1.0, 1.0, 1.5) for d in days[:130]]
        self._build(skew=up + down + short + flat)
        pctl = self._load("lieta_spx_put_skew3m_pctl1y")
        # 第 126 點（index 125）才有值，之前不輸出；遞增序列永遠是視窗最大值 → 100
        self.assertNotIn(_dt(days[124]), pctl)
        self.assertEqual(len(pctl), 300 - 125)
        self.assertAlmostEqual(pctl[_dt(days[125])], 100.0)
        self.assertAlmostEqual(pctl[_dt(days[299])], 100.0)
        # 遞減序列：當日永遠是視窗最小值 → 1/len；index 125 視窗 126 點、index 299 視窗 252 點
        down_p = self._load("lieta_tlt_put_skew3m_pctl1y")
        self.assertAlmostEqual(down_p[_dt(days[125])], 100 / 126)
        self.assertAlmostEqual(down_p[_dt(days[299])], 100 / 252)
        # 125 點不足 → 不產 pctl（put_skew3m 本身照出）
        self.assertEqual(self._load("lieta_qqq_put_skew3m_pctl1y"), {})
        self.assertEqual(len(self._load("lieta_qqq_put_skew3m")), 125)
        # 平手計入（rank ≤ 當日值）→ 100
        self.assertAlmostEqual(self._load("lieta_smh_put_skew3m_pctl1y")[_dt(days[129])], 100.0)

    def test_pctl1y_window_drops_old_points(self):
        # 前 48 點 = 10，之後 252 點 = 1 → 最後一點視窗只含 252 個 1，高值已移出視窗
        days = self._days(300)
        vals = [10.0] * 48 + [1.0] * 252
        self._build(skew=[(d, "SPX", "3m", 1.0, 1.0, v) for d, v in zip(days, vals)])
        pctl = self._load("lieta_spx_put_skew3m_pctl1y")
        self.assertAlmostEqual(pctl[_dt(days[299])], 100.0)
        # index 250 的視窗是 index 0～250（251 點）：48 個 10、203 個 1 → 當日 1 的 rank = 203/251
        self.assertAlmostEqual(pctl[_dt(days[250])], 203 / 251 * 100)

    # ---- term_iv ----
    def test_p25_atm_interpolation_and_term_slope(self):
        # atm：5→.20、20→.16、40→.14、100→.12；p25：5→.24、20→.20、40→.18、100→.15
        term = [(D1, "SPX", f"e{dte}", dte, p25, atm, 1) for dte, p25, atm in
                ((5, .24, .20), (20, .20, .16), (40, .18, .14), (100, .15, .12))]
        self._build(term=term)
        ratio = self._load("lieta_spx_p25_atm_1m")
        # 30 天跨 20～40：p25 = .19、atm = .15
        self.assertAlmostEqual(ratio[_dt(D1)], .19 / .15)
        slope = self._load("lieta_spx_term_slope")
        # atm(9) = .20 − .04×4/15；atm(90) = .14 − .02×50/60；差 ×100 = 6.6 vol 點，正 = 前端高於後端
        self.assertAlmostEqual(slope[_dt(D1)], 6.6)

    def test_bucket_series_averages_ratios_within_dte_22_to_35(self):
        # D1：dte 22、35 在範圍內 → (.20/.16 + .18/.15) / 2；dte 21、36 在範圍外
        # D2：只有 dte 5、60，30 天內插得到值但 bucket 沒有到期日 → 無點
        term = [(D1, "SPX", "a", 21, .40, .16, 1), (D1, "SPX", "b", 22, .20, .16, 1),
                (D1, "SPX", "c", 35, .18, .15, 1), (D1, "SPX", "d", 36, .60, .15, 1),
                (D2, "SPX", "e", 5, .22, .18, 1), (D2, "SPX", "f", 60, .20, .16, 1)]
        self._build(term=term)
        bucket = self._load("lieta_spx_p25_atm_1m_bucket")
        self.assertAlmostEqual(bucket[_dt(D1)], (.20 / .16 + .18 / .15) / 2)
        self.assertNotIn(_dt(D2), bucket)
        self.assertIn(_dt(D2), self._load("lieta_spx_p25_atm_1m"))

    def test_term_slope_negative_when_back_higher(self):
        self._build(term=[(D1, "SPX", "a", 9, .20, .10, 1), (D1, "SPX", "b", 90, .20, .15, 1)])
        self.assertAlmostEqual(self._load("lieta_spx_term_slope")[_dt(D1)], -5.0)

    def test_interp_at_exact_30_dte_and_zero_dte_excluded(self):
        term = [(D1, "QQQ", "x0", 0, .50, .50, 1),  # dte=0 排除
                (D1, "QQQ", "x30", 30, .21, .15, 1), (D1, "QQQ", "x60", 60, .22, .17, 1)]
        self._build(term=term)
        self.assertAlmostEqual(self._load("lieta_qqq_p25_atm_1m")[_dt(D1)], .21 / .15)

    def test_single_contract_at_exactly_30_dte(self):
        self._build(term=[(D1, "QQQ", "x30", 30, .21, .15, 1)])
        self.assertAlmostEqual(self._load("lieta_qqq_p25_atm_1m")[_dt(D1)], .21 / .15)

    def test_no_extrapolation_when_30_not_covered(self):
        term = [(D1, "SPX", "a", 5, .24, .20, 1), (D1, "SPX", "b", 20, .20, .16, 1),   # 最遠 20 天
                (D2, "SPX", "c", 35, .20, .16, 1), (D2, "SPX", "d", 60, .20, .16, 1)]  # 最近 35 天
        self._build(term=term)
        self.assertEqual(self._load("lieta_spx_p25_atm_1m"), {})
        self.assertEqual(self._load("lieta_spx_term_slope"), {})  # D1 缺 90 天、D2 缺 9 天

    def test_null_or_zero_atm_expiry_excluded(self):
        term = [(D1, "SPX", "a", 5, .24, .20, 1), (D1, "SPX", "b", 20, .20, 0.0, 1),
                (D1, "SPX", "c", 40, .18, .14, 1),
                (D2, "SPX", "a", 5, .24, .20, 1), (D2, "SPX", "b", 20, .20, None, 1),
                (D2, "SPX", "c", 40, .18, .14, 1)]
        self._build(term=term)
        # atm=0／NULL 的到期日整個排除，改用 5～40 內插：p25(30) = .24 − .06×25/35
        want = (.24 - .06 * 25 / 35) / (.20 - .06 * 25 / 35)
        ratio = self._load("lieta_spx_p25_atm_1m")
        self.assertAlmostEqual(ratio[_dt(D1)], want)
        self.assertAlmostEqual(ratio[_dt(D2)], want)

    def test_term_only_configured_tickers(self):
        term = [(D1, t, "a", 20, .20, .16, 1) for t in ("SPX", "XLE")]
        term += [(D1, t, "b", 40, .18, .14, 1) for t in ("SPX", "XLE")]
        self._build(term=term)
        names = set(os.listdir(self.out))
        self.assertIn("lieta_spx_p25_atm_1m.pkl", names)
        self.assertNotIn("lieta_xle_p25_atm_1m.pkl", names)

    def test_premarket_zero_rows_warned_once(self):
        term = [(D1, "SPX", "a", 20, .20, .16, 1), (D1, "SPX", "b", 40, .18, .14, 1),
                (D2, "SPX", "a", 20, .20, .16, 0), (D2, "SPX", "b", 40, .18, .14, 0)]
        msgs = self._build(term=term, level="WARNING")
        hits = [s for s in msgs if "premarket=0" in s]
        self.assertEqual(len(hits), 1, msgs)
        self.assertIn("rows: 2", hits[0])

    # ---- 缺表／空表 ----
    def test_missing_tables_skipped_with_info(self):
        msgs = self._build()
        self.assertTrue(any("hist_skew table not found" in s for s in msgs), msgs)
        self.assertTrue(any("term_iv table not found" in s for s in msgs), msgs)
        self.assertFalse(any("put_skew3m" in f or "p25_atm" in f
                             for f in (os.listdir(self.out) if os.path.exists(self.out) else [])))

    def test_empty_tables_skipped_with_info(self):
        msgs = self._build(skew=[], term=[])
        self.assertTrue(any("hist_skew table is empty" in s for s in msgs), msgs)
        self.assertTrue(any("term_iv table is empty" in s for s in msgs), msgs)


class LietaTermSnapshotTest(unittest.TestCase):
    """term_iv：p25_p50_1m 內插、premarket=1 優先／premarket=0 暫定、壞值過濾、新舊 schema。
    term 列格式 (date, ticker, expiration, dte, p25, p50, atm, premarket)。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "eod_metrics.db")
        self.out = os.path.join(self.tmp.name, "out")
        self.vix_pkl = os.path.join(self.tmp.name, "vix.pkl")

    def _build(self, term, schema="new", level="WARNING"):
        """schema: new = 主鍵含 premarket（兩版本並存）；old = 主鍵 (date,ticker,expiration)；
        nopm = 沒有 premarket 欄。"""
        conn = sqlite3.connect(self.db)
        conn.execute("CREATE TABLE vx_curve (date TEXT, dte INTEGER, settlement REAL)")
        pk = {"new": ", premarket INTEGER, PRIMARY KEY (date, ticker, expiration, premarket)",
              "old": ", premarket INTEGER, PRIMARY KEY (date, ticker, expiration)",
              "nopm": ", PRIMARY KEY (date, ticker, expiration)"}[schema]
        conn.execute("CREATE TABLE term_iv (date TEXT NOT NULL, ticker TEXT NOT NULL, "
                     "expiration TEXT NOT NULL, dte INTEGER, c25_iv REAL, p25_iv REAL, "
                     "c50_iv REAL, p50_iv REAL, atm_iv REAL" + pk + ")")
        if schema == "nopm":
            term = [r[:-1] for r in term]
            ins = ("INSERT INTO term_iv (date, ticker, expiration, dte, p25_iv, p50_iv, atm_iv) "
                   "VALUES (?,?,?,?,?,?,?)")
        else:
            ins = ("INSERT INTO term_iv (date, ticker, expiration, dte, p25_iv, p50_iv, atm_iv, premarket) "
                   "VALUES (?,?,?,?,?,?,?,?)")
        conn.executemany(ins, term)
        conn.commit()
        conn.close()
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level=level)
        try:
            m.fetch_lieta_eod_series(self.db, self.out, self.vix_pkl)
        finally:
            m.logger.remove(sink_id)
        return msgs

    def _load(self, name):
        path = os.path.join(self.out, f"{name}.pkl")
        if not os.path.exists(path):
            return {}
        with open(path, "rb") as f:
            return {d: v for d, v in pickle.load(f)["data"]}

    def _meta(self):
        with open(os.path.join(self.out, m.TERM_META_NAME), encoding="utf-8") as f:
            return json.load(f)["tickers"]

    @staticmethod
    def _snap(date, ticker, pm, rows):
        """rows = [(dte, p25, p50, atm)] → term 列。"""
        return [(date, ticker, f"e{int(dte)}", dte, p25, p50, atm, pm) for dte, p25, p50, atm in rows]

    # ---- p25_p50_1m 內插 ----
    def test_p25_p50_interpolated_to_30_days_then_divided(self):
        # p25：20→.20、40→.18 → 30 天 .19；p50：20→.16、40→.14 → 30 天 .15
        rows = self._snap(D1, "SPX", 1, [(5, .24, .19, .20), (20, .20, .16, .17),
                                          (40, .18, .14, .15), (100, .15, .12, .13)])
        self._build(rows)
        self.assertAlmostEqual(self._load("lieta_spx_p25_p50_1m")[_dt(D1)], .19 / .15)
        # p25_atm_1m 仍保留（分母是 lieta 原 atm_iv）
        self.assertAlmostEqual(self._load("lieta_spx_p25_atm_1m")[_dt(D1)], .19 / .16)

    def test_p25_p50_uses_same_expiries_for_numerator_and_denominator(self):
        # dte 20 的 p50 缺值 → 該到期日不進 p25_p50，改用 5～40 內插：
        # p25(30) = .24 − .06×25/35、p50(30) = .20 − .06×25/35
        rows = self._snap(D1, "SPX", 1, [(5, .24, .20, .21), (20, .20, None, .17), (40, .18, .14, .15)])
        self._build(rows)
        k = .06 * 25 / 35
        self.assertAlmostEqual(self._load("lieta_spx_p25_p50_1m")[_dt(D1)], (.24 - k) / (.20 - k))

    def test_p25_p50_no_extrapolation(self):
        rows = self._snap(D1, "SPX", 1, [(5, .24, .20, .21), (20, .20, .16, .17)])
        self._build(rows)
        self.assertEqual(self._load("lieta_spx_p25_p50_1m"), {})

    # ---- dte 0 排除（建議-3：dte 0 + dte 10 fixture，9 天 term_slope 沒有點）----
    def test_dte_zero_excluded_so_front_9_days_not_interpolated(self):
        # 只有 dte 0 和 dte 10 兩個近端點 + 遠端 100：9 天落在 dte 0～10 之間，
        # 若 dte 0 沒被排除就會內插出 term_slope；排除後最近到期日是 10 天 > 9，不外推 → 無點。
        rows = self._snap(D1, "QQQ", 1, [(0, .50, .45, .50), (10, .25, .20, .22), (100, .22, .18, .19)])
        self._build(rows)
        self.assertEqual(self._load("lieta_qqq_term_slope"), {})
        # dte 0 也不參與 p25_p50：30 天落在 10～100 之間
        want = (.25 + (.22 - .25) * 20 / 90) / (.20 + (.18 - .20) * 20 / 90)
        self.assertAlmostEqual(self._load("lieta_qqq_p25_p50_1m")[_dt(D1)], want)

    # ---- premarket=1 優先、premarket=0 暫定 ----
    def test_premarket_one_preferred_over_zero_when_both_exist(self):
        eod = self._snap(D1, "QQQ", 0, [(20, .30, .20, .21), (40, .30, .20, .21)])    # 比值 1.5
        pre = self._snap(D1, "QQQ", 1, [(20, .24, .20, .21), (40, .24, .20, .21)])    # 比值 1.2
        self._build(eod + pre)
        self.assertAlmostEqual(self._load("lieta_qqq_p25_p50_1m")[_dt(D1)], 1.2)
        meta = self._meta()["QQQ"]
        self.assertFalse(meta["last_provisional"])
        self.assertEqual(meta["provisional_dates"], [])

    def test_premarket_zero_used_only_when_no_premarket_one_and_recorded_in_meta(self):
        d1 = self._snap(D1, "SPX", 1, [(20, .24, .20, .21), (40, .24, .20, .21)])
        d2 = self._snap(D2, "SPX", 0, [(20, .27, .20, .21), (40, .27, .20, .21)])     # 只有 EOD
        msgs = self._build(d1 + d2)
        got = self._load("lieta_spx_p25_p50_1m")
        self.assertAlmostEqual(got[_dt(D1)], 1.2)
        self.assertAlmostEqual(got[_dt(D2)], 1.35)   # 暫定點仍輸出
        meta = self._meta()["SPX"]
        self.assertEqual(meta, {"last_date": D2, "last_provisional": True, "provisional_dates": [D2]})
        self.assertEqual(len([s for s in msgs if "premarket=0" in s]), 1, msgs)

    def test_later_premarket_one_replaces_provisional_point(self):
        # 同一個 as-of 日先只有 EOD，之後 premarket=1 進來（新 PK 兩版本並存）→ 改用 premarket=1，不再暫定
        self._build(self._snap(D2, "SPX", 0, [(20, .30, .20, .21), (40, .30, .20, .21)])
                    + self._snap(D2, "SPX", 1, [(20, .22, .20, .21), (40, .22, .20, .21)]))
        self.assertAlmostEqual(self._load("lieta_spx_p25_p50_1m")[_dt(D2)], 1.1)
        self.assertEqual(self._meta()["SPX"]["provisional_dates"], [])

    def test_old_pk_schema_reads_single_version(self):
        rows = self._snap(D1, "SPX", 1, [(20, .24, .20, .21), (40, .24, .20, .21)])
        self._build(rows, schema="old")
        self.assertAlmostEqual(self._load("lieta_spx_p25_p50_1m")[_dt(D1)], 1.2)

    def test_schema_without_premarket_column_treated_as_official(self):
        rows = self._snap(D1, "SPX", 1, [(20, .24, .20, .21), (40, .24, .20, .21)])
        self._build(rows, schema="nopm")
        self.assertAlmostEqual(self._load("lieta_spx_p25_p50_1m")[_dt(D1)], 1.2)
        self.assertEqual(self._meta()["SPX"]["provisional_dates"], [])

    # ---- 壞值過濾 ----
    def _good(self, date, ticker="SPX", pm=1):
        # 正常快照：p25 > p50、p25 > atm
        return self._snap(date, ticker, pm, [(7, .30, .24, .26), (14, .28, .22, .24), (30, .26, .20, .22),
                                              (45, .25, .19, .21), (90, .24, .18, .20)])

    def _series_at(self, d):
        return {n: self._load(f"lieta_spx_{n}").get(_dt(d))
                for n in ("p25_p50_1m", "p25_atm_1m", "p25_atm_1m_bucket", "term_slope")}

    def test_bad_expiry_atm_over_one_dropped_and_warned(self):
        # review：SPX as-of 2025-11-26 dte 5 的 atm 4.4184；as-of 2024-06-28 dte 40 的 atm 2.0072
        d_a, d_b, d_ok = "2025-11-26", "2024-06-28", "2025-12-01"
        rows = self._good(d_ok)
        rows += self._good(d_a) + self._snap(d_a, "SPX", 1, [(5, .30, .24, 4.4184)])
        rows += self._good(d_b) + self._snap(d_b, "SPX", 1, [(40, .26, .21, 2.0072)])
        msgs = self._build(rows)
        # 壞到期日丟掉後，4 條序列都和沒有壞點的那天完全相同；term_slope 的 9 天內插也沒被 dte 5 的 4.4 拉高
        want = self._series_at(d_ok)
        self.assertTrue(all(v is not None for v in want.values()), want)
        for d in (d_a, d_b):
            got = self._series_at(d)
            for name, v in want.items():
                self.assertAlmostEqual(got[name], v, places=9, msg=f"{name} {d}")
        hits = [s for s in msgs if "bad expiries dropped" in s]
        self.assertEqual(len(hits), 1, msgs)
        self.assertIn("2025-11-26 dte5", hits[0])
        self.assertIn("2024-06-28 dte40", hits[0])

    def test_bad_expiry_p25_over_one_or_ratio_out_of_range_dropped(self):
        d, d_ok = "2026-03-02", "2026-03-03"
        rows = self._good(d_ok)
        rows += self._good(d) + self._snap(d, "SPX", 1, [(20, 1.2, .20, .21),    # p25 > 1
                                                          (25, .50, .20, .21),    # p25/p50 = 2.5
                                                          (28, .15, .20, .21)])   # p25/p50 = 0.75
        msgs = self._build(rows)
        hits = [s for s in msgs if "bad expiries dropped" in s]
        self.assertEqual(len(hits), 1, msgs)
        for dte in ("dte20", "dte25", "dte28"):
            self.assertIn(dte, hits[0])
        # 三個壞到期日都丟掉，結果和只有好點的那天相同
        self.assertAlmostEqual(self._series_at(d)["p25_p50_1m"], self._series_at(d_ok)["p25_p50_1m"])
        self.assertAlmostEqual(self._series_at(d)["p25_atm_1m"], self._series_at(d_ok)["p25_atm_1m"])

    def test_bad_spx_snapshots_dropped_entirely_with_warning(self):
        # review 列的 SPX 壞日（20220104/06/10/11/12/14、20230828/29/30、20250428 是請求日），
        # 落地 as-of 為前一交易日：p25 < atm 的到期日 > 20% → 整份不輸出
        bad_days = ["2022-01-03", "2022-01-05", "2022-01-10", "2022-01-11", "2022-01-13",
                    "2023-08-25", "2023-08-28", "2023-08-29", "2025-04-25"]
        rows = []
        for d in bad_days:
            # dte 7–60 的 4 個到期日中 2 個 p25 < p50 且 p25 < atm（50%）
            rows += self._snap(d, "SPX", 1, [(7, .20, .24, .26), (14, .21, .22, .24), (30, .26, .20, .22),
                                              (45, .25, .19, .21), (90, .24, .18, .20)])
        rows += self._good("2025-05-01")
        msgs = self._build(rows)
        for name in ("p25_p50_1m", "p25_atm_1m", "p25_atm_1m_bucket", "term_slope"):
            got = self._load(f"lieta_spx_{name}")
            for d in bad_days:
                self.assertNotIn(_dt(d), got, f"{name} {d}")
        self.assertIn(_dt("2025-05-01"), self._load("lieta_spx_p25_p50_1m"))
        hits = [s for s in msgs if "bad snapshots dropped" in s]
        self.assertEqual(len(hits), 1, msgs)
        for d in bad_days:
            self.assertIn(d, hits[0])

    def test_snapshot_with_p25_below_p50_share_over_20_percent_dropped(self):
        d = "2026-04-01"
        # 5 個到期日 2 個 p25 < p50（40%），但 p25 都 > atm、p25/p50 在範圍內
        rows = self._snap(d, "SPX", 1, [(7, .20, .24, .19), (14, .21, .22, .19), (30, .26, .20, .19),
                                          (45, .25, .19, .18), (90, .24, .18, .17)])
        rows += self._good("2026-04-02")
        self._build(rows)
        self.assertNotIn(_dt(d), self._load("lieta_spx_p25_p50_1m"))
        self.assertIn(_dt("2026-04-02"), self._load("lieta_spx_p25_p50_1m"))

    def test_good_snapshot_and_few_bad_expiries_not_dropped(self):
        # 11 個到期日只有 1 個 p25 < p50（9% ≤ 20%）→ 整份保留
        d = "2026-04-03"
        rows = self._snap(d, "SPX", 1, [(7 + i, .26, .20, .22) for i in range(9)]
                          + [(20, .19, .20, .18), (60, .24, .19, .20)])
        msgs = self._build(rows)
        self.assertIn(_dt(d), self._load("lieta_spx_p25_p50_1m"))
        self.assertFalse(any("bad snapshots dropped" in s for s in msgs), msgs)

    def test_snapshot_filter_only_for_configured_tickers(self):
        # 同樣的 p25 < p50 形狀換成 TLT（put skew 可能本來就反向）→ 保留，只寫 warning
        d = "2025-10-16"
        rows = self._snap(d, "TLT", 1, [(7, .20, .24, .19), (14, .21, .22, .19), (30, .22, .24, .19),
                                          (45, .21, .23, .18), (90, .20, .22, .17)])
        msgs = self._build(rows)
        self.assertIn(_dt(d), self._load("lieta_tlt_p25_p50_1m"))
        self.assertTrue(any("suspicious snapshots (kept" in s and d in s for s in msgs), msgs)

    def test_bad_snapshot_choice_does_not_fall_back_to_other_version(self):
        # premarket=1 版壞掉 → 該 as-of 日不輸出（不偷偷改用 premarket=0）
        d = "2026-04-06"
        bad = self._snap(d, "SPX", 1, [(7, .20, .24, .26), (14, .21, .22, .24), (30, .22, .20, .24),
                                         (45, .25, .19, .21), (90, .24, .18, .20)])
        eod = self._good(d, pm=0)
        self._build(bad + eod)
        self.assertNotIn(_dt(d), self._load("lieta_spx_p25_p50_1m"))


class LietaPhase3Test(unittest.TestCase):
    """Phase 3：sector_vol（xsd／xop iv、ivpct）、trend_dsi（dsi_1w）、flow_top（深價外 put 權利金、前 20 大 sidecar）。
    DB 的 date 已是 as-of（goldmine fetcher 處理過），converter 照抄、不再位移。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = os.path.join(self.tmp.name, "eod_metrics.db")
        self.out = os.path.join(self.tmp.name, "out")
        self.vix_pkl = os.path.join(self.tmp.name, "vix.pkl")

    def _build(self, sector=None, dsi=None, flow=None, flow_schema="new"):
        conn = sqlite3.connect(self.db)
        if sector is not None:
            conn.execute("CREATE TABLE sector_vol (date TEXT, ticker TEXT, iv_latest REAL, "
                         "iv_percentile REAL, rv_latest REAL, PRIMARY KEY (date, ticker))")
            conn.executemany("INSERT INTO sector_vol (date, ticker, iv_latest, iv_percentile, rv_latest) "
                             "VALUES (?,?,?,?,?)", sector)
        if dsi is not None:
            conn.execute("CREATE TABLE trend_dsi (date TEXT, ticker TEXT, score_1w REAL, "
                         "PRIMARY KEY (date, ticker))")
            conn.executemany("INSERT INTO trend_dsi VALUES (?,?,?)", dsi)
        if flow is not None:
            extra = ", is_deep_otm_put INTEGER NOT NULL DEFAULT 0" if flow_schema == "new" else ""
            conn.execute("CREATE TABLE flow_top (date TEXT, id TEXT, query_ticker TEXT, ticker TEXT, "
                         "expiration TEXT, strike REAL, option_type TEXT, dte INTEGER, volume REAL, "
                         "premium REAL, contract_direction TEXT, otm_pct REAL, underlying_price REAL"
                         + extra + ", PRIMARY KEY (date, id))")
            if flow_schema == "new":
                conn.executemany("INSERT INTO flow_top (date, id, query_ticker, ticker, expiration, strike, "
                                 "option_type, dte, volume, premium, contract_direction, otm_pct, "
                                 "underlying_price, is_deep_otm_put) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", flow)
            else:
                conn.executemany("INSERT INTO flow_top (date, id, query_ticker, ticker, expiration, strike, "
                                 "option_type, dte, volume, premium, contract_direction, otm_pct, "
                                 "underlying_price) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 [r[:-1] for r in flow])
        conn.commit()
        conn.close()
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level="INFO")
        try:
            m.fetch_lieta_eod_series(self.db, self.out, self.vix_pkl)
        finally:
            m.logger.remove(sink_id)
        return msgs

    def _load(self, name):
        with open(os.path.join(self.out, f"{name}.pkl"), "rb") as f:
            obj = pickle.load(f)
        self.assertIn("title", obj)
        return {d: v for d, v in obj["data"]}

    def _title(self, name):
        with open(os.path.join(self.out, f"{name}.pkl"), "rb") as f:
            return pickle.load(f)["title"]

    def _names(self):
        return {f[:-4] for f in os.listdir(self.out) if f.endswith(".pkl")}

    # ---- sector_vol ----
    def test_sector_vol_iv_in_vol_points_pct_raw_and_asof_not_shifted(self):
        self._build(sector=[
            (D1, "XSD", 0.43, 0.53, 0.44), (D2, "XSD", 0.44, 0.62, 0.45),
            (D1, "XOP", 0.35, 0.83, 0.30), (D2, "XOP", 0.36, None, 0.31),
            (D1, "XLE", 0.25, 0.4, 0.2),   # 不在 SECTOR_TICKERS：不輸出
        ])
        self.assertEqual(self._names() & {"lieta_xsd_iv", "lieta_xop_iv", "lieta_xsd_ivpct", "lieta_xop_ivpct"},
                         {"lieta_xsd_iv", "lieta_xop_iv", "lieta_xsd_ivpct", "lieta_xop_ivpct"})
        self.assertNotIn("lieta_xle_iv", self._names())
        xsd = self._load("lieta_xsd_iv")
        self.assertEqual(set(xsd), {_dt(D1), _dt(D2)})            # 日期照抄 DB 的 as-of
        self.assertAlmostEqual(xsd[_dt(D1)], 43.0)                 # 小數 ×100 = vol 點
        self.assertAlmostEqual(self._load("lieta_xop_iv")[_dt(D2)], 36.0)
        self.assertAlmostEqual(self._load("lieta_xsd_ivpct")[_dt(D2)], 0.62)   # 百分位保持 0–1
        self.assertAlmostEqual(self._load("lieta_xop_ivpct")[_dt(D1)], 0.83)
        self.assertEqual(set(self._load("lieta_xop_ivpct")), {_dt(D1)})        # NULL 百分位跳過，不補 0

    def test_sector_vol_titles_state_resolution_and_etf_definition(self):
        self._build(sector=[(D1, "XSD", 0.43, 0.5, None), (D1, "XOP", 0.35, 0.8, None)])
        t = self._title("lieta_xsd_iv")
        self.assertIn("半導體", t)
        self.assertIn("2 位小數", t)
        self.assertIn("1 vol 點", t)
        self.assertIn("油氣探勘", self._title("lieta_xop_iv"))

    def test_sector_vol_missing_empty_or_partial_tickers_do_not_break(self):
        msgs = self._build()                       # 沒有三張表
        files = os.listdir(self.out) if os.path.isdir(self.out) else []
        self.assertFalse(any(n.startswith(("lieta_xsd", "lieta_xop", "lieta_smh_dsi", "lieta_spx_deep"))
                             for n in files))
        self.assertTrue(any("sector_vol table not found" in s for s in msgs), msgs)
        self.assertTrue(any("trend_dsi table not found" in s for s in msgs), msgs)
        self.assertTrue(any("flow_top table not found" in s for s in msgs), msgs)

    def test_sector_vol_empty_table_skipped_with_info(self):
        msgs = self._build(sector=[], dsi=[], flow=[])
        self.assertTrue(any("sector_vol table is empty" in s for s in msgs), msgs)
        self.assertTrue(any("trend_dsi table is empty" in s for s in msgs), msgs)
        self.assertTrue(any("flow_top table is empty" in s for s in msgs), msgs)
        self.assertFalse(os.path.exists(os.path.join(self.out, "lieta_xsd_iv.pkl")))

    def test_sector_vol_ticker_absent_on_some_days_leaves_gap(self):
        # L6 ticker 集合不穩（15↔27 檔）：某天只有 XOP、沒有 XSD → XSD 該日無點
        self._build(sector=[(D1, "XSD", 0.43, 0.5, None), (D1, "XOP", 0.35, 0.8, None),
                            (D2, "XOP", 0.36, 0.81, None)])
        self.assertEqual(set(self._load("lieta_xsd_iv")), {_dt(D1)})
        self.assertEqual(set(self._load("lieta_xop_iv")), {_dt(D1), _dt(D2)})

    def test_sector_vol_outlier_warns_but_keeps_point(self):
        days = [f"2026-10-{d:02d}" for d in (12, 13, 14)]
        msgs = []
        sink_id = m.logger.add(lambda msg: msgs.append(str(msg)), level="WARNING")
        try:
            self._build(sector=[(days[0], "XSD", 0.15, 0.5, None), (days[1], "XSD", 0.80, 0.5, None),
                                (days[2], "XSD", 0.16, 0.5, None)])
        finally:
            m.logger.remove(sink_id)
        self.assertTrue(any("lieta_xsd_iv outlier points (kept)" in s for s in msgs), msgs)
        self.assertAlmostEqual(self._load("lieta_xsd_iv")[_dt(days[1])], 80.0)

    # ---- trend_dsi ----
    def test_dsi_1w_score_per_ticker_not_shifted(self):
        self._build(dsi=[(D1, "SMH", 10.0), (D2, "SMH", 0.0), (D2, "XLE", 3.2), (D3, "XLE", None),
                         (D1, "SPY", 7.0), (D1, "NOTLISTED", 1.0)])
        self.assertEqual(self._load("lieta_smh_dsi_1w"), {_dt(D1): 10.0, _dt(D2): 0.0})
        self.assertEqual(self._load("lieta_xle_dsi_1w"), {_dt(D2): 3.2})     # NULL 跳過
        self.assertEqual(self._load("lieta_spy_dsi_1w"), {_dt(D1): 7.0})    # SPX 不在 DSI，用 SPY
        self.assertNotIn("lieta_notlisted_dsi_1w", self._names())

    # ---- flow_top ----
    def _flow_rows(self):
        # (date, id, query_ticker, ticker, expiration, strike, option_type, dte, volume, premium,
        #  contract_direction, otm_pct, underlying_price, is_deep_otm_put)
        return [
            (D1, "a", "SPX", "SPX", "2027-01-15", 6000, "P", 85, 100, 30e6, "ASK", 21.0, 7600, 1),
            (D1, "b", "SPX", "SPXW", "2026-11-20", 6500, "P", 30, 100, 20e6, "BID", 14.0, 7600, 1),
            (D1, "c", "SPX", "SPX", "2026-11-20", 7600, "C", 30, 100, 90e6, "ASK", 0.0, 7600, 0),
            (D1, "d", "SPX", "SPX", "2026-11-20", 7000, "P", 30, 100, 10e6, "ASK", 8.0, 7600, 0),   # OTM 8% 不算
            (D1, "e", "QQQ", "QQQ", "2026-11-20", 500, "P", 30, 100, 5e6, "ASK", 30.0, 700, 1),
            (D2, "f", "SPX", "SPX", "2026-11-20", 6000, "P", 30, 100, 40e6, "ASK", 22.0, 7650, 1),
            (D2, "g", "SPX", "SPX", "2026-11-20", 7650, "C", 30, 200, 70e6, "ASK", 0.0, 7650, 0),
            (D2, "h", "SPX", "SPX", "2026-11-20", 9000, "P", 30, 100, 60e6, "ASK", -18.0, 7650, 0),  # 深價內 put 不算
        ]

    def test_flow_deep_otm_put_premium_sum_in_millions_per_query_date(self):
        self._build(flow=self._flow_rows())
        spx = self._load("lieta_spx_deep_otm_put_premium")
        self.assertEqual(set(spx), {_dt(D1), _dt(D2)})
        self.assertAlmostEqual(spx[_dt(D1)], 50.0)       # (30 + 20) 百萬；SPXW 併入，OTM 8% 與 call 不算
        self.assertAlmostEqual(spx[_dt(D2)], 40.0)       # 深價內 put 不算
        self.assertEqual(self._load("lieta_qqq_deep_otm_put_premium"), {_dt(D1): 5.0})
        self.assertIn("OTM > 10%", self._title("lieta_spx_deep_otm_put_premium"))

    def test_flow_top_sidecar_latest_query_date_top20_by_premium_with_deep_flag(self):
        rows = self._flow_rows()
        # D2 再補 25 筆小單，總共 28 筆 SPX：只留 premium 前 20，最大的在最前面
        rows += [(D2, f"x{i:02d}", "SPX", "SPX", "2026-12-18", 5000 + i, "C", 55, 10, (i + 1) * 1e5,
                  "ASK", 1.0, 7650, 0) for i in range(25)]
        self._build(flow=rows)
        with open(os.path.join(self.out, m.FLOW_META_NAME), encoding="utf-8") as f:
            meta = json.load(f)
        spx = meta["tickers"]["SPX"]
        self.assertEqual(spx["query_date"], D2)                       # SPX 最新 query_date
        self.assertEqual(meta["tickers"]["QQQ"]["query_date"], D1)    # 各 ticker 各取自己的最新日
        self.assertEqual(len(spx["rows"]), 20)
        prem = [r["premium"] for r in spx["rows"]]
        self.assertEqual(prem, sorted(prem, reverse=True))
        self.assertEqual(prem[0], 70e6)
        self.assertEqual({r["option_type"] for r in spx["rows"] if r["is_deep_otm_put"]}, {"P"})
        deep = [r for r in spx["rows"] if r["is_deep_otm_put"]]
        self.assertEqual([(r["strike"], r["otm_pct"]) for r in deep], [(6000, 22.0)])   # 深價內 9000P 不是
        self.assertEqual(spx["underlying_price"], 7650)
        for key in ("ticker", "option_type", "strike", "expiration", "dte", "otm_pct", "premium",
                    "volume", "contract_direction", "is_deep_otm_put"):
            self.assertIn(key, spx["rows"][0])

    def test_flow_old_schema_without_is_deep_column_falls_back_to_p_and_otm_over_10(self):
        self._build(flow=self._flow_rows(), flow_schema="old")
        self.assertAlmostEqual(self._load("lieta_spx_deep_otm_put_premium")[_dt(D1)], 50.0)
        with open(os.path.join(self.out, m.FLOW_META_NAME), encoding="utf-8") as f:
            rows = json.load(f)["tickers"]["SPX"]["rows"]
        self.assertEqual([r["strike"] for r in rows if r["is_deep_otm_put"]], [6000])


if __name__ == "__main__":
    unittest.main()
