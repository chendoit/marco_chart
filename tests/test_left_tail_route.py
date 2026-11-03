import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_DIR = os.path.join(ROOT, "flask_highcharts")
DATA_DIR = os.path.join(ROOT, "data")
GROUP = "左尾風險監控"
# 變異驗證用：指向被改壞的 route 副本（預設測真檔）
ROUTE_PATH = os.getenv("LEFT_TAIL_ROUTE_PATH") or os.path.join(FLASK_DIR, "app", "routes", f"{GROUP}.py")

# route 讀 data/ 下的真 pkl；缺任何一個核心檔（例如沒跑過 converter 的乾淨 checkout）就跳過整組
REQUIRED_PKLS = ["lieta_spx_flip_dist_pct", "lieta_qqq_p25_p50_1m", "lieta_spx_p25_p50_1m",
                 "lieta_qqq_put_skew3m_pctl1y", "lieta_vx1_vx2_spread", "complacency_ratio",
                 "series_2", "series_cboe_VXN"]
HAVE_DATA = all(os.path.exists(os.path.join(DATA_DIR, f"{n}.pkl")) for n in REQUIRED_PKLS)


def _load_route():
    """載入 route 模組（需要 flask_highcharts 在 sys.path 才找得到 app.utils）。"""
    if FLASK_DIR not in sys.path:
        sys.path.insert(0, FLASK_DIR)
    spec = importlib.util.spec_from_file_location("lefttail_route_under_test", ROUTE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(HAVE_DATA, "data/ 下缺 lieta_* / complacency_* pkl")
class LeftTailRouteLoadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._cwd = os.getcwd()
        os.chdir(FLASK_DIR)  # main.py 用相對路徑 app/routes 載入 group
        if FLASK_DIR not in sys.path:
            sys.path.insert(0, FLASK_DIR)
        import main
        cls.main = main
        cls.client = main.app.test_client()
        main._api_cache.pop(GROUP, None)
        cls.resp = cls.client.get(f"/api/chart/{GROUP}")
        cls.payload = cls.resp.get_json()

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls._cwd)

    def test_group_registered_and_pages_ok(self):
        self.assertIn(GROUP, self.main.chart_id_list)
        self.assertEqual(self.client.get(f"/charts/{GROUP}").status_code, 200)
        self.assertEqual(self.resp.status_code, 200)
        self.assertNotIn("error", self.payload)

    def test_every_chart_has_nonempty_series(self):
        charts = self.payload["charts"]
        self.assertEqual(len(charts), len(self.main.chart_id_list[GROUP]))
        for i, ch in enumerate(charts):
            series = ch["config"]["series"]
            self.assertTrue(series, f"chart {i} has no series")
            for s in series:
                self.assertTrue(s["data"], f"chart {i} series {s.get('name')!r} is empty")
            self.assertTrue(ch.get("summary"), f"chart {i} has no summary")

    def test_asof_in_subtitle_for_every_series(self):
        # 第 0 張是總覽（asof 在表格裡），其餘每張圖的每條序列都要有自己的 as-of 日期
        for i, ch in enumerate(self.payload["charts"][1:], start=1):
            sub = ch["config"]["subtitle"]["text"]
            self.assertIn("as-of：", sub, f"chart {i}")
            n_series = len(ch["config"]["series"])
            self.assertGreaterEqual(len(re.findall(r"\d{4}-\d{2}-\d{2}", sub)), n_series, f"chart {i}: {sub}")

    def test_every_time_series_chart_overlays_vix(self):
        for i, ch in enumerate(self.payload["charts"][1:], start=1):
            names = [s["name"] for s in ch["config"]["series"]]
            self.assertTrue(any("VIX" in n and "VXN" not in n or n == "VIX" for n in names), f"chart {i}: {names}")

    def test_charts_with_thresholds_have_plot_lines(self):
        titled = {c["config"]["title"]["text"][:1]: c["config"] for c in self.payload["charts"][1:]}
        for key in "①②③④⑤⑥⑦⑧⑨":
            self.assertIn(key, titled)
        for ch in self.payload["charts"][1:]:
            title = ch["config"]["title"]["text"]
            if title[0] in "①③④⑤⑥⑦⑧" or title.startswith("⑨ 科技股 skew 比 SPX 陡"):
                axes = ch["config"]["yAxis"]
                self.assertTrue(any(y.get("plotLines") for y in axes), title)

    def test_overview_has_nine_conditions_with_status_and_asof(self):
        ov = self.payload["charts"][0]
        self.assertEqual(len(ov["config"]["series"][0]["data"]), 9)
        mod = self.main._loaded_modules[GROUP]
        rows = mod.compute_status()
        self.assertEqual([r["no"] for r in rows], list(range(1, 10)))
        for r in rows:
            self.assertIn(r["status"], ("✅", "⬜", "❓"))
            self.assertTrue(r["detail"])
            self.assertTrue(r["asof"])
            self.assertTrue(all(re.search(r"\d{4}-\d{2}-\d{2}|缺資料", a) for a in r["asof"]), r["asof"])
        self.assertIn("<table", ov["summary"])

    def test_condition_9_uses_p25_p50_spread_percentile(self):
        mod = self.main._loaded_modules[GROUP]
        row = mod.compute_status()[8]
        self.assertIn("p25/p50", row["detail"])
        self.assertNotIn("p25/ATM", row["detail"])
        spread_chart = [c for c in self.payload["charts"]
                        if c["config"]["title"]["text"].startswith("⑨ 科技股 skew 比 SPX 陡（一）")][0]
        self.assertIn("為什麼不用 p25/atm", spread_chart["summary"])

    def test_barbell_aux_chart_dsi_chart_and_flow_chart_present(self):
        titles = [c["config"]["title"]["text"] for c in self.payload["charts"]]
        aux = [c for c in self.payload["charts"] if c["config"]["title"]["text"].startswith("⑦ 輔助")]
        self.assertEqual(len(aux), 1)
        self.assertEqual(len(aux[0]["config"]["series"]), 5)       # xsd／xop ivpct + xsd／xop iv + VIX
        self.assertIn("解析度 1 vol 點", aux[0]["config"]["subtitle"]["text"])
        self.assertTrue(any(t.startswith("⑦ 參考：DSI 1W") for t in titles))
        flow = [c for c in self.payload["charts"] if "深價外 put" in c["config"]["title"]["text"]]
        self.assertEqual(len(flow), 1)
        self.assertEqual({s["name"][:3] for s in flow[0]["config"]["series"]}, {"SPX", "QQQ", "VIX"})

    def test_flow_table_shows_query_date_deep_otm_marks_and_asof(self):
        flow = [c for c in self.payload["charts"] if "深價外 put" in c["config"]["title"]["text"]][0]
        html = flow["summary"]
        self.assertIn("<table", html)
        self.assertEqual(html.count("query_date <b>"), 2)           # SPX、QQQ 各一個
        self.assertRegex(html, r"query_date <b>\d{4}-\d{2}-\d{2}</b>")
        self.assertIn("當日收盤附近", html)
        self.assertEqual(html.count("<tr style='"), 40)             # 兩個 ticker 各 20 列
        with open(os.path.join(DATA_DIR, "lieta_flow_top.json"), encoding="utf-8") as f:
            meta = json.load(f)["tickers"]
        n_deep = sum(r["is_deep_otm_put"] for t in meta.values() for r in t["rows"])
        self.assertEqual(html.count("🔻是"), n_deep)

    def test_condition_7_row_has_main_and_aux_parts(self):
        mod = self.main._loaded_modules[GROUP]
        row = mod.compute_status()[6]
        self.assertIn(row["status"], ("✅", "⬜", "❓"))
        self.assertIn(row["aux"]["status"], ("✅", "⬜", "❓"))
        self.assertRegex(row["label"], r"^主\S 輔\S$")
        self.assertTrue(any("XSD IV 百分位" in a for a in row["asof"]))
        self.assertTrue(any("SMH" in a for a in row["asof"]))

    def test_derived_series_ranges(self):
        mod = self.main._loaded_modules[GROUP]
        for sid in ("lt_vxn_pctl1y", "lt_move_pctl1y", "lt_qqq_spx_p25_p50_spread_pctl1y"):
            s = mod._series(sid)
            self.assertTrue(len(s) > 0)
            self.assertTrue(((s >= 0) & (s <= 100)).all(), sid)
        flags = mod._series("lt_barbell_both_down")
        self.assertTrue(set(flags.unique()) <= {0.0, 1.0})

    def test_gex_series_shows_data_date_one_trading_day_earlier(self):
        mod = self.main._loaded_modules[GROUP]
        text = mod._asof_text("SPX 1M put skew", "gex_spx_put_skew_1m")
        ts = mod._series("gex_spx_put_skew_1m").index[-1]
        self.assertIn(f"資料日 {mod._d(mod._prev_td(ts))}", text)
        self.assertLess(mod._prev_td(ts), ts)


class _FakeSeriesCase(unittest.TestCase):
    """不依賴真資料：把 route 的 _series 換成假序列，驗證 延遲／缺資料 與 9 條條件的符號、閾值。"""

    LAST = "2026-10-23"       # series_2 與 cboe_VIX 的最後交易日（基準）
    LAGGED = "2026-10-22"     # lieta screener／vx／hist_skew 與 FRED 的最後日期（容忍 1 日）

    @classmethod
    def setUpClass(cls):
        cls._cwd = os.getcwd()
        os.chdir(FLASK_DIR)
        cls.mod = _load_route()

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls._cwd)

    def setUp(self):
        self._orig_series = self.mod._series
        self._orig_meta = self.mod._term_meta
        self.mod._term_meta = lambda: {}
        self.addCleanup(self._restore)

    def _restore(self):
        self.mod._series = self._orig_series
        self.mod._term_meta = self._orig_meta

    def _ser(self, last, val, n=300):
        """n 個交易日、值全是 val 的 Series，最後一天 = last。"""
        return pd.Series([float(val)] * n, index=pd.bdate_range(end=pd.Timestamp(last), periods=n))

    def _install(self, mapping):
        def fake(sid):
            if sid not in mapping:
                raise FileNotFoundError(sid)
            return mapping[sid]
        self.mod._series = fake


class LeftTailLogicTest(_FakeSeriesCase):
    """衍生計算與 延遲／缺資料 判斷。"""

    def test_rolling_pctl_definition(self):
        s = pd.Series(range(1, 11), index=pd.date_range("2026-01-01", periods=10), dtype=float)
        out = self.mod._rolling_pctl(s, window=5, min_points=3)
        self.assertTrue(pd.isna(out.iloc[0]) and pd.isna(out.iloc[1]))
        self.assertAlmostEqual(out.iloc[2], 100.0)   # 遞增：永遠是視窗內最大
        s2 = pd.Series([5, 1, 3, 2.0], index=pd.date_range("2026-01-01", periods=4))
        self.assertAlmostEqual(self.mod._rolling_pctl(s2, window=4, min_points=4).iloc[3], 50.0)  # 2 ≤ {1,2} → 2/4

    def _cond_status(self, mapping, sid, builder_result=(True, "d"), no=3):
        self._install(mapping)
        return self.mod._cond(no, "t", [("x", sid)], lambda: builder_result)

    def test_lieta_screener_one_day_behind_is_structural_not_delayed(self):
        # series_2 到 10-23；screener 到 10-22（結構性落後 1 日，容忍 1）→ 依值判斷
        row = self._cond_status({2: self._ser(self.LAST, 7600.0, 5),
                                 "lieta_spx_flip_dist_pct": self._ser(self.LAGGED, -1.0)},
                                "lieta_spx_flip_dist_pct")
        self.assertEqual(row["status"], "✅")
        self.assertNotIn("延遲", row["asof"][0])

    def test_lieta_screener_two_days_behind_is_delayed_unknown(self):
        row = self._cond_status({2: self._ser(self.LAST, 7600.0, 5),
                                 "lieta_spx_flip_dist_pct": self._ser("2026-10-21", -1.0)},
                                "lieta_spx_flip_dist_pct", (False, "d"))
        self.assertEqual(row["status"], "❓")   # 延遲不能當成未觸發
        self.assertIn("延遲", row["detail"])
        self.assertIn("⚠延遲", row["asof"][0])

    def test_other_series_tolerance_is_zero(self):
        # VIX 與 series_2 都是基準來源之一；VXN 落後基準 1 日 → 非 lieta/FRED 組，容忍 0 → 延遲
        row = self._cond_status({2: self._ser(self.LAST, 7600.0, 5), "cboe_VXN": self._ser(self.LAGGED, 20.0)},
                                "cboe_VXN", (True, "d"), no=1)
        self.assertEqual(row["status"], "❓")
        self.assertIn("⚠延遲1日", row["asof"][0])

    def test_fred_tolerance_is_one(self):
        ok = self._cond_status({2: self._ser(self.LAST, 7600.0, 5), 95001: self._ser(self.LAGGED, 3.0)},
                               95001, (True, "d"), no=6)
        self.assertEqual(ok["status"], "✅")
        late = self._cond_status({2: self._ser(self.LAST, 7600.0, 5), 95001: self._ser("2026-10-21", 3.0)},
                                 95001, (True, "d"), no=6)
        self.assertEqual(late["status"], "❓")

    def test_baseline_is_newer_of_series_2_and_vix(self):
        # series_2 停在 10-22、VIX 到 10-23 → 基準是 10-23，lieta screener 10-21 落後 2 日 → 延遲
        row = self._cond_status({2: self._ser("2026-10-22", 7600.0, 5), "cboe_VIX": self._ser(self.LAST, 19.0, 5),
                                 "lieta_spx_flip_dist_pct": self._ser("2026-10-21", -1.0)},
                                "lieta_spx_flip_dist_pct", (True, "d"))
        self.assertEqual(row["status"], "❓")
        # 反過來 VIX 比 series_2 舊 → 基準仍是 series_2
        row2 = self._cond_status({2: self._ser(self.LAST, 7600.0, 5), "cboe_VIX": self._ser("2026-10-20", 19.0, 5),
                                  "lieta_spx_flip_dist_pct": self._ser(self.LAGGED, -1.0)},
                                 "lieta_spx_flip_dist_pct", (True, "d"))
        self.assertEqual(row2["status"], "✅")

    def test_expression_tolerance_uses_stricter_component(self):
        self._install({})
        self.assertEqual(self.mod._lag_tol(("cboe_VXN", "-", "cboe_VIX")), 0)
        self.assertEqual(self.mod._lag_tol(("lieta_vx1", "-", "lieta_vx2")), 1)
        self.assertEqual(self.mod._lag_tol(("lieta_vx1", "-", "cboe_VIX")), 0)
        self.assertEqual(self.mod._lag_tol("lieta_qqq_put_skew3m_pctl1y"), 1)
        self.assertEqual(self.mod._lag_tol("lieta_qqq_p25_p50_1m"), 0)       # term：EOD 暫定點 = 當日
        self.assertEqual(self.mod._lag_tol("gex_spx_put_skew_1m"), 0)
        self.assertEqual(self.mod._lag_tol("lt_hy_oas_chg20"), 1)
        # Phase 3：L6 sector_vol 屬前一日收盤組（容忍 1）；dsi、flow 是當日（容忍 0）
        for sid in ("lieta_xsd_iv", "lieta_xop_iv", "lieta_xsd_ivpct", "lieta_xop_ivpct"):
            self.assertEqual(self.mod._lag_tol(sid), 1, sid)
        for sid in ("lieta_smh_dsi_1w", "lieta_xle_dsi_1w", "lieta_igv_dsi_1w",
                    "lieta_spx_deep_otm_put_premium", "lieta_qqq_deep_otm_put_premium"):
            self.assertEqual(self.mod._lag_tol(sid), 0, sid)

    def test_missing_series_is_unknown_with_name(self):
        row = self._cond_status({2: self._ser(self.LAST, 7600.0, 5)}, "lieta_xsd_ivpct", no=7)
        self.assertEqual(row["status"], "❓")
        self.assertIn("缺資料", row["detail"])
        self.assertEqual(row["asof"], ["x 缺資料"])

    def test_gex_asof_shows_data_date_minus_one_trading_day(self):
        self._install({2: self._ser(self.LAST, 7600.0, 10), "gex_spx_put_skew_1m": self._ser(self.LAST, 1.2, 10)})
        text = self.mod._asof_text("SPX 1M put skew", "gex_spx_put_skew_1m")
        self.assertEqual(text, "SPX 1M put skew 2026-10-23（資料日 2026-10-22）")
        # 週一的 gex 序列日期 → 資料日是上週五
        self._install({2: self._ser("2026-10-26", 7600.0, 10), "gex_spx_put_skew_1m": self._ser("2026-10-26", 1.2, 10)})
        self.assertIn("資料日 2026-10-23", self.mod._asof_text("g", "gex_spx_put_skew_1m"))

    def test_eod_provisional_tag_from_sidecar(self):
        self._install({2: self._ser(self.LAST, 7600.0, 10),
                       "lieta_spx_p25_p50_1m": self._ser(self.LAST, 1.2, 10),
                       "lieta_qqq_p25_p50_1m": self._ser(self.LAST, 1.2, 10)})
        self.assertNotIn("EOD暫定", self.mod._asof_text("SPX", "lieta_spx_p25_p50_1m"))   # 沒有 sidecar → 不標
        self.mod._term_meta = lambda: {"SPX": {self.LAST}}
        self.assertIn("⚠EOD暫定", self.mod._asof_text("SPX", "lieta_spx_p25_p50_1m"))
        self.assertNotIn("EOD暫定", self.mod._asof_text("QQQ", "lieta_qqq_p25_p50_1m"))

    def test_term_meta_reads_sidecar_file_and_degrades_without_it(self):
        with tempfile.TemporaryDirectory() as d:
            old_dir = self.mod.DATA_DIR
            self.mod.DATA_DIR = d
            self.addCleanup(setattr, self.mod, "DATA_DIR", old_dir)
            self.mod._term_meta = self._orig_meta
            self.assertEqual(self.mod._term_meta(), {})
            self.assertNotIn("EOD 暫定", self.mod._term_snapshot_note())
            self.assertIn("SPX 含夜盤變動", self.mod._term_snapshot_note())
            with open(os.path.join(d, self.mod.TERM_META), "w", encoding="utf-8") as f:
                json.dump({"tickers": {"SPX": {"last_date": "2026-10-23", "last_provisional": True,
                                               "provisional_dates": ["2026-10-23"]},
                                       "QQQ": {"last_date": "2026-10-23", "last_provisional": False,
                                               "provisional_dates": []}}}, f)
            self.assertEqual(self.mod._term_meta(), {"SPX": {"2026-10-23"}, "QQQ": set()})
            note = self.mod._term_snapshot_note()
            self.assertIn("EOD 暫定", note)
            self.assertIn("SPX 2026-10-23", note)
            self.assertNotIn("QQQ 2026-10-23", note)


class LeftTailConditionsTest(_FakeSeriesCase):
    """9 條條件的符號與閾值：每條至少一個 ✅ 與一個 ⬜ 案例（預設全部 ⬜，案例只改該條的輸入）。"""

    def _defaults(self):
        L, T = self.LAST, self.LAGGED   # L: 基準日；T: lieta／FRED 的最後日期（容忍 1 日）
        m = {
            2: self._ser(L, 7600.0, 10), "cboe_VIX": self._ser(L, 19.0, 10),
            # 1 VXN−VIX、VXN 百分位
            ("cboe_VXN", "-", "cboe_VIX"): self._ser(L, 3.0), "lt_vxn_pctl1y": self._ser(L, 50),
            "cboe_VXN": self._ser(L, 22.0),
            # 2 VVIX 單日變動、SPX 1M put skew vs 前 20 日高點
            "lt_vvix_d1": self._ser(L, 1.0), "cboe_VVIX": self._ser(L, 95.0),
            "gex_spx_put_skew_1m": self._ser(L, 1.20), "lt_putskew1m_prior_high20": self._ser(L, 1.30),
            # 3 flip 距離（>0 在 flip 之上）、regime
            "lieta_spx_flip_dist_pct": self._ser(T, 1.0), "lieta_qqq_flip_dist_pct": self._ser(T, 1.0),
            "lieta_spx_regime": self._ser(T, 1.0), "lieta_qqq_regime": self._ser(T, 1.0),
            # 4 MOVE
            "lt_move_pctl1y": self._ser(L, 50), 17581: self._ser(L, 90.0),
            # 5 股債相關
            "2:ret~cboe_TNX.CORR20": self._ser(L, -0.3), "cboe_TNX": self._ser(L, 4.0),
            # 6 信用
            "lt_hy_oas_chg20": self._ser(T, 0.2), "lt_ccc_spread_chg20": self._ser(T, 0.3),
            "lt_bbb_spread_chg20": self._ser(T, 0.1), 95001: self._ser(T, 3.0), 3612: self._ser(T, 9.0),
            # 7 槓鈴
            "lt_smh_ret1d": self._ser(L, 1.0), "lt_xle_ret1d": self._ser(L, 1.0),
            "etf_SMH_close": self._ser(L, 300.0), "etf_XLE_close": self._ser(L, 90.0),
            "lieta_xsd_ivpct": self._ser(T, 0.5), "lieta_xop_ivpct": self._ser(T, 0.5),
            # 8 VIX 期貨
            "lieta_vx1_vx2_spread": self._ser(T, -1.0), "lieta_vx1_vix_basis": self._ser(T, 1.0),
            "lieta_vx_contango_30d": self._ser(T, 8.0),
            # 9 skew 比 SPX 陡
            "lt_qqq_spx_p25_p50_spread": self._ser(L, -0.04), "lt_qqq_spx_p25_p50_spread_pctl1y": self._ser(L, 50),
            "lieta_qqq_put_skew3m_pctl1y": self._ser(T, 50),
        }
        return m

    def _status(self, no, **over):
        """over: {series id: 值}；值為 float 時整條序列改成該常數（沿用原最後日期）。"""
        m = self._defaults()
        for sid, v in over.items():
            sid = {"VXN_VIX": ("cboe_VXN", "-", "cboe_VIX"), "MOVE": 17581, "HY": 95001}.get(sid, sid)
            m[sid] = self._ser(m[sid].index[-1], v)
        self._install(m)
        return self.mod.compute_status()[no - 1]["status"]

    def test_defaults_are_all_not_triggered(self):
        self._install(self._defaults())
        rows = self.mod.compute_status()
        self.assertEqual([r["status"] for r in rows], ["⬜"] * 9, [r["detail"] for r in rows])

    def test_c1_vxn_vix_gap_and_percentile(self):
        self.assertEqual(self._status(1, VXN_VIX=7.5, lt_vxn_pctl1y=86), "✅")
        self.assertEqual(self._status(1, VXN_VIX=6.9, lt_vxn_pctl1y=86), "⬜")    # 差不夠
        self.assertEqual(self._status(1, VXN_VIX=7.5, lt_vxn_pctl1y=84), "⬜")    # 百分位不夠

    def test_c2_vvix_jump_or_new_high(self):
        self.assertEqual(self._status(2, lt_vvix_d1=10.0), "✅")
        self.assertEqual(self._status(2, lt_vvix_d1=9.9), "⬜")
        self.assertEqual(self._status(2, gex_spx_put_skew_1m=1.31), "✅")        # > 前 20 日高點 1.30
        self.assertEqual(self._status(2, gex_spx_put_skew_1m=1.29), "⬜")

    def test_c3_flip_distance_negative_means_below_flip(self):
        self.assertEqual(self._status(3, lieta_spx_flip_dist_pct=-1.0, lieta_qqq_flip_dist_pct=-2.0), "✅")
        self.assertEqual(self._status(3, lieta_spx_flip_dist_pct=1.0, lieta_qqq_flip_dist_pct=-2.0), "⬜")
        self.assertEqual(self._status(3, lieta_spx_flip_dist_pct=-1.0, lieta_qqq_flip_dist_pct=2.0), "⬜")

    def test_c4_move_percentile(self):
        self.assertEqual(self._status(4, lt_move_pctl1y=91), "✅")
        self.assertEqual(self._status(4, lt_move_pctl1y=89), "⬜")

    def test_c5_stock_bond_correlation_positive(self):
        self.assertEqual(self._status(5, **{"2:ret~cboe_TNX.CORR20": 0.1}), "✅")
        self.assertEqual(self._status(5, **{"2:ret~cboe_TNX.CORR20": -0.1}), "⬜")

    def test_c6_credit_hy_or_ccc_widening_over_one_pp(self):
        self.assertEqual(self._status(6, lt_hy_oas_chg20=1.1), "✅")
        self.assertEqual(self._status(6, lt_ccc_spread_chg20=1.1), "✅")
        self.assertEqual(self._status(6, lt_hy_oas_chg20=0.9, lt_ccc_spread_chg20=0.9), "⬜")
        self.assertEqual(self._status(6, lt_bbb_spread_chg20=2.0), "⬜")          # BBB 只供參考

    def test_c7_both_barbell_legs_down_over_threshold(self):
        self.assertEqual(self._status(7, lt_smh_ret1d=-2.0, lt_xle_ret1d=-2.0), "✅")
        self.assertEqual(self._status(7, lt_smh_ret1d=-2.0, lt_xle_ret1d=1.0), "⬜")     # 只有一腿
        self.assertEqual(self._status(7, lt_smh_ret1d=-1.4, lt_xle_ret1d=-1.4), "⬜")    # 跌幅不夠

    def _c7(self, aux=None, **over):
        """回第 7 條的 (status, aux status, label)；aux = {id: 值 或 Series}，None 值表示移除該序列。"""
        m = self._defaults()
        for sid, v in over.items():
            m[sid] = self._ser(m[sid].index[-1], v)
        for sid, v in (aux or {}).items():
            if v is None:
                m.pop(sid, None)
            elif isinstance(v, pd.Series):
                m[sid] = v
            else:
                m[sid] = self._ser(m[sid].index[-1], v)
        self._install(m)
        row = self.mod.compute_status()[6]
        return row["status"], row["aux"]["status"], row["label"]

    def test_c7_aux_both_percentiles_above_0_8_marks_aux_only(self):
        # 主 ⬜ ＋ 輔助 ✅：輔助成立不會把主條件變成 ✅
        self.assertEqual(self._c7({"lieta_xsd_ivpct": 0.85, "lieta_xop_ivpct": 0.9})[:2], ("⬜", "✅"))
        # 主 ✅ ＋ 輔助 ⬜
        self.assertEqual(self._c7({"lieta_xsd_ivpct": 0.5, "lieta_xop_ivpct": 0.9},
                                  lt_smh_ret1d=-2.0, lt_xle_ret1d=-2.0)[:2], ("✅", "⬜"))
        # 兩者都成立：主 ✅ ＋ 輔助 ✅
        self.assertEqual(self._c7({"lieta_xsd_ivpct": 0.85, "lieta_xop_ivpct": 0.9},
                                  lt_smh_ret1d=-2.0, lt_xle_ret1d=-2.0)[:2], ("✅", "✅"))

    def test_c7_aux_threshold_is_strictly_greater_than_0_8_and_needs_both(self):
        self.assertEqual(self._c7({"lieta_xsd_ivpct": 0.8, "lieta_xop_ivpct": 0.9})[1], "⬜")
        self.assertEqual(self._c7({"lieta_xsd_ivpct": 0.9, "lieta_xop_ivpct": 0.8})[1], "⬜")
        self.assertEqual(self._c7({"lieta_xsd_ivpct": 0.81, "lieta_xop_ivpct": 0.81})[1], "✅")

    def test_c7_aux_missing_is_unknown_and_does_not_change_main(self):
        both_down = dict(lt_smh_ret1d=-2.0, lt_xle_ret1d=-2.0)
        for gone in ("lieta_xsd_ivpct", "lieta_xop_ivpct"):
            self.assertEqual(self._c7({gone: None}, **both_down)[:2], ("✅", "❓"), gone)
            self.assertEqual(self._c7({gone: None})[:2], ("⬜", "❓"), gone)

    def test_c7_aux_delayed_is_unknown_with_last_value_judgement(self):
        late = {"lieta_xsd_ivpct": self._ser("2026-10-21", 0.9), "lieta_xop_ivpct": self._ser(self.LAGGED, 0.9)}
        status, aux, label = self._c7(late, lt_smh_ret1d=-2.0, lt_xle_ret1d=-2.0)
        self.assertEqual((status, aux), ("✅", "❓"))             # 主條件不受輔助延遲影響
        self.assertEqual(label, "主✅ 輔❓")
        row = self.mod.compute_status()[6]
        self.assertIn("延遲", row["aux"]["detail"])
        self.assertIn("最後值判斷：成立", row["aux"]["detail"])
        self.assertTrue(any("⚠延遲" in a for a in row["asof"]))
        # 落後 1 日（L6 容忍 1）不算延遲
        ok = {"lieta_xsd_ivpct": self._ser(self.LAGGED, 0.9), "lieta_xop_ivpct": self._ser(self.LAGGED, 0.9)}
        self.assertEqual(self._c7(ok)[1], "✅")

    def test_c7_main_delay_does_not_depend_on_aux_and_vice_versa(self):
        # 主條件延遲（SMH 收盤落後）→ 主 ❓，輔助照常 ✅
        m = self._defaults()
        m["etf_SMH_close"] = self._ser(self.LAGGED, 300.0)
        m["lt_smh_ret1d"] = self._ser(self.LAGGED, -2.0)
        m["lieta_xsd_ivpct"] = self._ser(self.LAGGED, 0.9)
        m["lieta_xop_ivpct"] = self._ser(self.LAGGED, 0.9)
        self._install(m)
        row = self.mod.compute_status()[6]
        self.assertEqual((row["status"], row["aux"]["status"]), ("❓", "✅"))

    def test_c7_row_shows_main_and_aux_asof_separately(self):
        m = self._defaults()
        self._install(m)
        row = self.mod.compute_status()[6]
        self.assertEqual(row["label"], "主⬜ 輔⬜")
        self.assertEqual(len(row["asof"]), 4)                                  # SMH、XLE、XSD、XOP
        self.assertIn(self.LAGGED, row["asof"][2])
        self.assertIn("輔助 ⬜", row["detail"])

    def test_overview_counts_only_main_condition_for_c7(self):
        m = self._defaults()
        m["lieta_xsd_ivpct"] = self._ser(self.LAGGED, 0.9)
        m["lieta_xop_ivpct"] = self._ser(self.LAGGED, 0.9)
        self._install(m)
        self.assertEqual([r["status"] for r in self.mod.compute_status()].count("✅"), 0)   # 輔助 ✅ 不算 n_ok
        ov = self.mod._overview()
        self.assertIn("0/9 成立", ov["config"]["title"]["text"])
        self.assertEqual(ov["config"]["series"][0]["data"][6]["label"], "主⬜ 輔✅")
        self.assertIn("主⬜ 輔✅", ov["summary"])

    def test_c8_vx_inversion_spread_positive_or_basis_negative(self):
        self.assertEqual(self._status(8, lieta_vx1_vx2_spread=0.1, lieta_vx1_vix_basis=0.3), "✅")   # 只有 spread > 0
        self.assertEqual(self._status(8, lieta_vx1_vx2_spread=-0.1, lieta_vx1_vix_basis=-0.3), "✅")  # 只有 basis < 0
        self.assertEqual(self._status(8, lieta_vx1_vx2_spread=-0.1, lieta_vx1_vix_basis=0.3), "⬜")

    def test_c9_spread_percentile_and_qqq_put_skew_percentile_both_required(self):
        self.assertEqual(self._status(9, lt_qqq_spx_p25_p50_spread_pctl1y=90, lieta_qqq_put_skew3m_pctl1y=90), "✅")
        # 9a 為真、9b 為假
        self.assertEqual(self._status(9, lt_qqq_spx_p25_p50_spread_pctl1y=90, lieta_qqq_put_skew3m_pctl1y=50), "⬜")
        # 9a 為假、9b 為真
        self.assertEqual(self._status(9, lt_qqq_spx_p25_p50_spread_pctl1y=50, lieta_qqq_put_skew3m_pctl1y=90), "⬜")
        # 閾值 > 85（嚴格大於）
        self.assertEqual(self._status(9, lt_qqq_spx_p25_p50_spread_pctl1y=85, lieta_qqq_put_skew3m_pctl1y=90), "⬜")

    def test_c9_ignores_sign_of_spread_level(self):
        # 差本身為負（QQQ 仍比 SPX 平）但百分位高 → 成立：用相對門檻，不是 > 0
        self.assertEqual(self._status(9, lt_qqq_spx_p25_p50_spread=-0.03,
                                      lt_qqq_spx_p25_p50_spread_pctl1y=90, lieta_qqq_put_skew3m_pctl1y=90), "✅")

    def test_c9_marks_provisional_eod_point(self):
        m = self._defaults()
        self._install(m)
        self.mod._term_meta = lambda: {"QQQ": {self.LAST}, "SPX": {self.LAST}}
        row = self.mod.compute_status()[8]
        self.assertIn("⚠EOD暫定", row["detail"])
        self.assertTrue(any("EOD暫定" in a for a in row["asof"]), row["asof"])

    def test_overview_counts_follow_conditions(self):
        m = self._defaults()
        m["lieta_spx_flip_dist_pct"] = self._ser(self.LAGGED, -1.0)
        m["lieta_qqq_flip_dist_pct"] = self._ser(self.LAGGED, -2.0)
        m["lt_move_pctl1y"] = self._ser(self.LAST, 95)
        self._install(m)
        rows = self.mod.compute_status()
        self.assertEqual([r["status"] for r in rows].count("✅"), 2)


class LeftTailFlowTest(_FakeSeriesCase):
    """flow 表（sidecar）與深價外 put 權利金趨勢圖：假 sidecar + 假序列。"""

    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        old_dir = self.mod.DATA_DIR
        self.mod.DATA_DIR = self.tmp.name
        self.addCleanup(setattr, self.mod, "DATA_DIR", old_dir)

    def _write_meta(self, spx_date=None, qqq_date=None):
        def rows(t, n_deep):
            out = []
            for i in range(20):
                deep = i < n_deep
                out.append({"ticker": t, "option_type": "P" if deep else "C", "strike": 6000 + i,
                            "expiration": "2027-01-15", "dte": 84, "otm_pct": 20.0 - i if deep else -3.0,
                            "premium": (50 - i) * 1e6, "volume": 100.0 + i, "contract_direction": "ASK",
                            "is_deep_otm_put": 1 if deep else 0})
            return out
        meta = {"top_n": 20, "tickers": {
            "SPX": {"query_date": spx_date or self.LAST, "underlying_price": 7623.68, "rows": rows("SPX", 3)},
            "QQQ": {"query_date": qqq_date or self.LAST, "underlying_price": 705.33, "rows": rows("QQQ", 1)}}}
        with open(os.path.join(self.tmp.name, self.mod.FLOW_META), "w", encoding="utf-8") as f:
            json.dump(meta, f)

    def _install_flow(self, last=None):
        last = last or self.LAST
        self._install({2: self._ser(self.LAST, 7600.0, 10),
                       "lieta_spx_deep_otm_put_premium": self._ser(last, 250.0, 200),
                       "lieta_qqq_deep_otm_put_premium": self._ser(last, 40.0, 200)})

    def test_table_has_20_rows_per_ticker_and_marks_only_deep_otm_puts(self):
        self._write_meta()
        self._install_flow()
        html = self.mod._flow_table_html(self.mod._flow_meta())
        self.assertEqual(html.count("<tr style='"), 40)
        self.assertEqual(html.count("🔻是"), 4)                               # SPX 3 + QQQ 1
        self.assertEqual(html.count("background:#fde2e2;font-weight:600"), 4)
        self.assertIn(f"query_date <b>{self.LAST}</b>", html)
        self.assertIn("當日收盤附近", html)
        self.assertIn("7,623.68", html)
        self.assertNotIn("延遲", html)

    def test_table_marks_delayed_query_date_with_zero_tolerance(self):
        self._write_meta(spx_date=self.LAGGED)                             # flow 當日資料，落後 1 日即延遲
        self._install_flow()
        html = self.mod._flow_table_html(self.mod._flow_meta())
        self.assertEqual(html.count("⚠延遲1日"), 1)                          # 只有 SPX

    def test_table_lag_ignores_time_of_day(self):
        # 真 pkl 的時間戳是 08:00，sidecar 的 query_date 是日期字串（00:00）：同一天不能算落後
        self._write_meta()
        eight = pd.bdate_range(end=pd.Timestamp(self.LAST), periods=10) + pd.Timedelta(hours=8)
        self._install({2: pd.Series(7600.0, index=eight),
                       "lieta_spx_deep_otm_put_premium": pd.Series(250.0, index=eight),
                       "lieta_qqq_deep_otm_put_premium": pd.Series(40.0, index=eight)})
        self.assertNotIn("延遲", self.mod._flow_table_html(self.mod._flow_meta()))
        self.assertNotIn("延遲", self.mod._flow_chart()["config"]["subtitle"]["text"])

    def test_table_without_sidecar_says_missing(self):
        self._install_flow()
        self.assertIn("缺資料", self.mod._flow_table_html(self.mod._flow_meta()))
        chart = self.mod._flow_chart()                                       # 沒 sidecar 也不 raise，趨勢圖仍有資料
        self.assertEqual(len(chart["config"]["series"]), 2)
        self.assertIn("缺資料", chart["summary"])

    def test_trend_chart_two_series_limited_to_recent_days_with_asof(self):
        self._write_meta()
        self._install_flow()
        chart = self.mod._flow_chart()
        names = [s["name"] for s in chart["config"]["series"]]
        self.assertEqual([n[:3] for n in names], ["SPX", "QQQ"])
        for s in chart["config"]["series"]:
            self.assertEqual(len(s["data"]), self.mod.FLOW_TREND_DAYS)
        sub = chart["config"]["subtitle"]["text"]
        self.assertIn("as-of：", sub)
        self.assertEqual(sub.count(self.LAST), 2)
        self.assertNotIn("延遲", sub)
        self.assertIn("<table", chart["summary"])

    def test_trend_chart_flags_delay(self):
        self._write_meta()
        self._install_flow(last=self.LAGGED)
        sub = self.mod._flow_chart()["config"]["subtitle"]["text"]
        self.assertEqual(sub.count("⚠延遲1日"), 2)


if __name__ == "__main__":
    unittest.main()
