import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lieta_fetch_alert as m  # noqa: E402

SCHEMA = """CREATE TABLE fetch_log (
    endpoint TEXT NOT NULL, date TEXT NOT NULL, ticker TEXT NOT NULL,
    status TEXT NOT NULL, resolved_date TEXT, fetched_at TEXT, rows INTEGER, note TEXT,
    PRIMARY KEY (endpoint, date, ticker))"""
TODAY = date(2026, 10, 26)


class FakeSender:
    def __init__(self, exc=None):
        self.calls, self.exc = [], exc
        self.__name__ = "fake"

    def __call__(self, subject, body):
        self.calls.append((subject, body))
        if self.exc:
            raise self.exc


class AlertTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "eod.db"
        self.state = Path(self.tmp.name) / "sub" / "alert_state.json"
        con = sqlite3.connect(self.db)
        con.execute(SCHEMA)
        con.commit()
        con.close()

    def add(self, day, status, endpoint="vx", ticker="ALL", note=None, at=None):
        con = sqlite3.connect(self.db)
        con.execute("INSERT OR REPLACE INTO fetch_log VALUES (?,?,?,?,?,?,?,?)",
                    (endpoint, day, ticker, status, None, at or f"{day}T09:00:00", 0, note))
        con.commit()
        con.close()

    def run_check(self, sender=None, today=TODAY):
        sender = sender if sender is not None else FakeSender()
        return m.check_and_alert(self.db, self.state, [sender], today), sender

    def fail_days(self, *days):
        for d in days:
            self.add(d, "failed", "vx", note=f"boom {d}")
            self.add(d, "failed", "term", "SPX", note=f"term boom {d}", at=f"{d}T09:05:00")

    # --- 該發
    def test_two_consecutive_failed_days_alerts(self):
        self.fail_days("20261022", "20261023")
        r, s = self.run_check()
        self.assertEqual((r["status"], r["streak"], r["event"]), ("alerted", 2, "20261022"))
        self.assertEqual(len(s.calls), 1)
        subject, body = s.calls[0]
        self.assertIn("20261022", body)
        self.assertIn("20261023", body)
        self.assertIn("vx", body)
        self.assertIn("term/SPX", body)
        self.assertIn("term boom 20261023", body)  # 最近一筆 note
        self.assertEqual(json.loads(self.state.read_text("utf-8"))["notified_day"], "2026-10-26")

    def test_three_day_streak_is_same_event(self):
        self.fail_days("20261021", "20261022")
        r1, _ = self.run_check()
        self.fail_days("20261023")
        r2, s2 = self.run_check()
        self.assertEqual((r1["event"], r2["event"]), ("20261021", "20261021"))
        self.assertEqual((r2["status"], s2.calls), ("already_alerted", []))

    # --- 不該發
    def test_single_failed_day_does_not_alert(self):
        self.add("20261022", "ok")
        self.fail_days("20261023")
        r, s = self.run_check()
        self.assertEqual((r["status"], r["streak"], s.calls), ("ok", 1, []))

    def test_ok_in_between_does_not_alert(self):
        self.fail_days("20261021")
        self.add("20261022", "ok")
        self.fail_days("20261023")
        r, s = self.run_check()
        self.assertEqual((r["status"], s.calls), ("ok", []))

    def test_ok_row_inside_failed_day_does_not_alert(self):
        self.fail_days("20261022", "20261023")
        self.add("20261023", "ok", "gex", "SPX")  # 該日不是「全部」failed
        r, s = self.run_check()
        self.assertEqual((r["status"], s.calls), ("ok", []))

    def test_empty_is_not_failure(self):
        self.fail_days("20261022")
        self.add("20261023", "empty", "vx")
        self.add("20261023", "failed", "term", "SPX")  # failed + empty 混合：不算全失敗
        r, s = self.run_check()
        self.assertEqual((r["status"], s.calls), ("ok", []))

    def test_asof_gap_rows_are_ignored(self):
        self.fail_days("20261022", "20261023")
        self.add("20261023", "empty", "term_asof", "SPX", note="asof_gap")
        self.add("20261024", "empty", "sectorvol_asof", "ALL", note="asof_gap")
        r, s = self.run_check()
        self.assertEqual((r["status"], r["streak"]), ("alerted", 2))

    def test_days_without_records_are_not_counted_or_filled(self):
        self.fail_days("20261020", "20261023")  # 中間 10-21、10-22 沒紀錄：只看有紀錄的日子
        r, _ = self.run_check()
        self.assertEqual((r["status"], r["streak"]), ("alerted", 2))
        self.assertEqual(m.failed_streak(m.load_days(self.db))[-1]["date"], "20261020")

    # --- 去重
    def test_same_day_not_repeated_but_next_day_again(self):
        self.fail_days("20261022", "20261023")
        _, s1 = self.run_check()
        r2, s2 = self.run_check()
        r3, s3 = self.run_check(today=date(2026, 10, 27))
        self.assertEqual((len(s1.calls), r2["status"], len(s2.calls)), (1, "already_alerted", 0))
        self.assertEqual((r3["status"], len(s3.calls)), ("alerted", 1))

    def test_new_event_same_day_alerts_again(self):
        self.fail_days("20261022", "20261023")
        self.run_check()
        self.add("20261024", "ok")
        self.fail_days("20261027", "20261028")
        r, s = self.run_check()
        self.assertEqual((r["status"], r["event"], len(s.calls)), ("alerted", "20261027", 1))

    # --- 資料庫異常
    def test_missing_db_and_empty_table_do_not_raise(self):
        r = m.check_and_alert(Path(self.tmp.name) / "nope.db", self.state, [FakeSender()], TODAY)
        self.assertEqual(r["status"], "no_data")
        r, s = self.run_check()  # setUp 建的空表
        self.assertEqual((r["status"], s.calls), ("no_data", []))

    def test_no_fetch_log_table_and_corrupt_db(self):
        other = Path(self.tmp.name) / "other.db"
        sqlite3.connect(other).close()
        self.assertEqual(m.check_and_alert(other, self.state, [FakeSender()], TODAY)["status"], "no_data")
        bad = Path(self.tmp.name) / "bad.db"
        bad.write_bytes(b"not a sqlite file" * 100)
        self.assertEqual(m.check_and_alert(bad, self.state, [FakeSender()], TODAY)["status"], "db_error")

    def test_db_opened_read_only(self):
        self.fail_days("20261022", "20261023")
        before = self.db.read_bytes()
        self.run_check()
        self.assertEqual(self.db.read_bytes(), before)

    # --- sender
    def test_sender_exception_does_not_raise_and_state_not_written(self):
        self.fail_days("20261022", "20261023")
        with self.assertLogs("lieta_fetch_alert", "ERROR"):
            r, _ = self.run_check(FakeSender(RuntimeError("smtp down")))
        self.assertEqual(r["status"], "send_failed")
        self.assertFalse(self.state.exists())
        r2, s2 = self.run_check()  # 下次還會再試
        self.assertEqual((r2["status"], len(s2.calls)), ("alerted", 1))

    def test_one_sender_failing_other_still_counts(self):
        self.fail_days("20261022", "20261023")
        good = FakeSender()
        with self.assertLogs("lieta_fetch_alert", "ERROR"):
            r = m.check_and_alert(self.db, self.state, [FakeSender(RuntimeError("x")), good], TODAY)
        self.assertEqual((r["status"], len(good.calls)), ("alerted", 1))

    def test_main_prints_alert_line_and_exits_zero(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = m.main(["--db", str(Path(self.tmp.name) / "nope.db"), "--state", str(self.state)])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().strip().splitlines()[-1], "ALERT status=no_data streak=0 event=None")


if __name__ == "__main__":
    unittest.main()
