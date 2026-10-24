import csv
import os
import pickle
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import get_complacency_series as m  # noqa: E402

REF_CSV = (r"C:\code\2026-09-09-new-lieta-goldmine\research\complacency"
           r"\complacency_20250101_20260916.csv")
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _days(n, start=date(2026, 1, 1)):
    return [start + timedelta(days=i) for i in range(n)]


def _write_pkl(path, by_date):
    data = [[datetime.combine(d, datetime.min.time()).replace(hour=8), v]
            for d, v in sorted(by_date.items())]
    with open(path, "wb") as f:
        pickle.dump({"title": "t", "data": data}, f)


class ComplacencyComputeTest(unittest.TestCase):
    def test_ratio_and_window_warmup(self):
        days = _days(60)
        vix = {d: 20.0 for d in days}
        vvix = {d: 100.0 for d in days}
        rows = m.compute_complacency(vvix, vix)
        self.assertEqual(len(rows), 60)
        self.assertAlmostEqual(rows[0][1], 5.0)
        # 前 49 天窗口未滿：ma / bands / 標記為 None
        self.assertTrue(all(r[2] is None and r[5] is None for r in rows[:49]))
        self.assertAlmostEqual(rows[49][2], 5.0)
        # 常數序列 sd=0 → 下緣=上緣=ma；ratio 不嚴格小於／大於 → 不標記
        self.assertEqual((rows[49][5], rows[49][6]), (0.0, 0.0))

    def test_breakdown_and_breakout_flags(self):
        days = _days(52)
        vix = {d: 20.0 for d in days}
        vvix = {d: 100.0 + (i % 2) for i, d in enumerate(days)}  # ratio 在 5.0 / 5.05 交替
        vvix[days[50]] = 60.0   # ratio 3.0：跌破下緣
        vvix[days[51]] = 160.0  # ratio 8.0：突破上緣
        rows = {r[0]: r for r in m.compute_complacency(vvix, vix)}
        self.assertEqual(rows[days[50]][5:], (1.0, 0.0))
        self.assertEqual(rows[days[51]][5:], (0.0, 1.0))
        self.assertEqual(rows[days[49]][5:], (0.0, 0.0))

    def test_band_formula_uses_ddof1_sd_of_ratio(self):
        days = _days(50)
        vix = {d: 10.0 for d in days}
        vvix = {d: 50.0 + i for i, d in enumerate(days)}  # ratio 5.0, 5.1, ..., 9.9
        r = m.compute_complacency(vvix, vix)[-1]
        vals = [v / 10.0 for v in vvix.values()]
        mean = sum(vals) / 50
        sd = (sum((v - mean) ** 2 for v in vals) / 49) ** 0.5
        self.assertAlmostEqual(r[2], mean)
        self.assertAlmostEqual(r[3], mean - 1.67 * sd)
        self.assertAlmostEqual(r[4], mean + 1.67 * sd)

    def test_inner_join_on_dates_and_nonpositive_vix_dropped(self):
        d = _days(4)
        vvix = {d[0]: 100.0, d[1]: 100.0, d[2]: 100.0}
        vix = {d[1]: 20.0, d[2]: 0.0, d[3]: 20.0}
        rows = m.compute_complacency(vvix, vix)
        self.assertEqual([r[0] for r in rows], [d[1]])


class ComplacencyExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = os.path.join(self.tmp.name, "data")
        self.out = os.path.join(self.tmp.name, "out")
        os.makedirs(self.data)

    def test_export_series_ids_and_format(self):
        days = _days(60)
        _write_pkl(os.path.join(self.data, "series_cboe_VIX.pkl"), {d: 20.0 for d in days})
        _write_pkl(os.path.join(self.data, "series_cboe_VVIX.pkl"),
                   {d: 100.0 + (i % 3) for i, d in enumerate(days)})
        m.fetch_complacency_series(self.out, self.data)
        names = {f[:-4] for f in os.listdir(self.out)}
        self.assertEqual(names, {"complacency_ratio", "complacency_ma50", "complacency_lower",
                                 "complacency_upper", "complacency_breakdown",
                                 "complacency_breakout"})
        with open(os.path.join(self.out, "complacency_ratio.pkl"), "rb") as f:
            obj = pickle.load(f)
        self.assertEqual(set(obj), {"title", "data"})
        self.assertEqual(len(obj["data"]), 60)
        self.assertEqual(obj["data"][0][0], datetime(2026, 1, 1, 8))
        with open(os.path.join(self.out, "complacency_ma50.pkl"), "rb") as f:
            self.assertEqual(len(pickle.load(f)["data"]), 11)  # 60 − 49
        with open(os.path.join(self.out, "complacency_breakdown.pkl"), "rb") as f:
            flags = {v for _, v in pickle.load(f)["data"]}
        self.assertTrue(flags <= {0.0, 1.0})

    def test_missing_input_pkl_is_noop(self):
        m.fetch_complacency_series(self.out, self.data)
        self.assertFalse(os.path.exists(self.out))


@unittest.skipUnless(
    os.path.exists(REF_CSV) and os.path.exists(os.path.join(DATA, "series_cboe_VVIX.pkl")),
    "goldmine reference CSV or local cboe pkl not available")
class ComplacencyVsReferenceTest(unittest.TestCase):
    """與 goldmine 參考 CSV（lieta market/complacency）比對：50dma 相對誤差 < 1%。"""

    def test_ma50_matches_reference(self):
        vvix = m._load_pkl_by_date(os.path.join(DATA, "series_cboe_VVIX.pkl"))
        vix = m._load_pkl_by_date(os.path.join(DATA, "series_cboe_VIX.pkl"))
        rows = {r[0]: r for r in m.compute_complacency(vvix, vix)}
        with open(REF_CSV, encoding="utf8") as f:
            ref = list(csv.DictReader(f))
        errs = []
        for r in ref:
            d = date.fromisoformat(r["date"])
            if d in rows and rows[d][2] is not None:
                ref_ma = float(r["complacency_50dma"])
                errs.append(abs(rows[d][2] - ref_ma) / ref_ma)
        self.assertGreater(len(errs), 300)
        self.assertLess(max(errs), 0.01)


if __name__ == "__main__":
    unittest.main()
