import gzip
import json
import os
import sys
import threading
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLASK_DIR = os.path.join(ROOT, "flask_highcharts")
GROUP = "左尾風險監控"


class FlaskCacheWarmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._cwd = os.getcwd()
        os.chdir(FLASK_DIR)  # main.py 用相對路徑 app/routes 載入 group
        if FLASK_DIR not in sys.path:
            sys.path.insert(0, FLASK_DIR)
        import main
        cls.main = main

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls._cwd)

    def setUp(self):
        self._clear()
        self.client = self.main.app.test_client()
        self.url = f"/api/chart/{GROUP}"
        self.addCleanup(self._clear)

    def _clear(self):
        with self.main._version_lock:
            self.main._clear_caches()

    def _build(self, value):
        # 內容要超過 1KB 才會觸發 gzip
        return mock.patch.object(self.main, "_build_group_charts", return_value=[value, "x" * 2048])

    def _get_gz(self, **headers):
        return self.client.get(self.url, headers={"Accept-Encoding": "gzip", **headers})

    @staticmethod
    def _charts(resp):
        return json.loads(gzip.decompress(resp.get_data()))["charts"]

    def test_hot_reload_serves_new_content_and_changes_etag(self):
        with self._build("old"):
            first = self._get_gz()
            self.assertEqual(self._charts(first)[0], "old")
        self.assertEqual(self.client.get("/api/update_groups").status_code, 200)
        with self._build("new"):
            second = self._get_gz(**{"If-None-Match": first.headers["ETag"]})
        self.assertEqual(second.status_code, 200, "熱更新後舊 ETag 不可再得到 304")
        self.assertEqual(self._charts(second)[0], "new")

    def test_same_etag_returns_304_when_nothing_changed(self):
        with self._build("v"):
            first = self._get_gz()
            second = self._get_gz(**{"If-None-Match": first.headers["ETag"]})
        self.assertEqual(second.status_code, 304)

    def test_data_version_change_clears_all_caches(self):
        with self._build("old"):
            self._get_gz()
        self.assertTrue(self.main._gzip_cache)
        self.assertTrue(self.main._api_cache)
        self.addCleanup(self.main._init_data_version)
        with mock.patch.object(self.main, "_compute_data_version", return_value="changed-version"):
            self.main._refresh_data_version_if_needed(force=True)
        self.assertFalse(self.main._gzip_cache)
        self.assertFalse(self.main._api_cache)

    def test_result_computed_before_cache_clear_is_not_cached(self):
        def build_then_data_changes(_group):
            with self.main._version_lock:
                self.main._clear_caches()
            return ["stale", "x" * 2048]

        with mock.patch.object(self.main, "_build_group_charts", side_effect=build_then_data_changes), \
                mock.patch.object(self.main, "clear_series_cache") as clear_series:
            resp = self._get_gz()
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(GROUP, self.main._api_cache)
        self.assertEqual(clear_series.call_count, 2, "捨棄舊結果時要再清一次序列快取")

    def test_concurrent_requests_compute_group_once(self):
        calls = []

        def slow_build(_group):
            calls.append(1)
            time.sleep(0.2)
            return ["v", "x" * 2048]

        with mock.patch.object(self.main, "_build_group_charts", side_effect=slow_build):
            threads = [threading.Thread(target=self.main.app.test_client().get, args=(self.url,))
                       for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual(len(calls), 1)

    def test_warm_fills_json_and_gzip_cache_for_real_request_key(self):
        with self._build("warm"), mock.patch.object(self.main, "_WARM_GROUPS", (GROUP,)), \
                mock.patch.object(self.main, "_available_memory_mb", return_value=10_000):
            self.main._warm_groups()
        self.assertIn(GROUP, self.main._api_cache)
        with mock.patch.object(self.main, "_build_group_charts", side_effect=AssertionError("不應重算")), \
                mock.patch.object(self.main.gzip, "compress", side_effect=AssertionError("不應重壓")):
            resp = self._get_gz()
        self.assertEqual(self._charts(resp)[0], "warm")

    def test_warm_skipped_when_memory_is_low(self):
        with mock.patch.object(self.main, "_available_memory_mb", return_value=1), \
                mock.patch.object(self.main, "_build_group_charts") as build:
            self.main._warm_groups()
        build.assert_not_called()

    def test_tick_retries_after_low_memory_and_warns_once(self):
        main = self.main
        self.addCleanup(setattr, main, "_warm_low_memory_warned", False)
        with self._build("v"), mock.patch.object(main, "_WARM_GROUPS", (GROUP,)), \
                mock.patch.object(main, "_refresh_data_version_if_needed"), \
                mock.patch.object(main, "_latest_pkl_mtime", return_value=0.0), \
                mock.patch.object(main.logger, "warning") as warning:
            with mock.patch.object(main, "_available_memory_mb", return_value=1):
                self.assertIsNone(main._warm_tick(None))
                self.assertIsNone(main._warm_tick(None))
            self.assertEqual(warning.call_count, 1, "記憶體不足只警告一次")
            self.assertNotIn(GROUP, main._api_cache)

            with mock.patch.object(main, "_available_memory_mb", return_value=10_000):
                self.assertEqual(main._warm_tick(None), main._cache_generation)
            self.assertIn(GROUP, main._api_cache, "記憶體恢復後要補做預熱")

    def test_available_memory_is_positive(self):
        self.assertGreater(self.main._available_memory_mb(), 0)

    def test_tick_waits_for_quiet_data_and_warms_once_per_generation(self):
        main = self.main
        with mock.patch.object(main, "_warm_groups") as warm, \
                mock.patch.object(main, "_refresh_data_version_if_needed"):
            with mock.patch.object(main, "_latest_pkl_mtime", return_value=time.time()):
                self.assertIsNone(main._warm_tick(None))
            warm.assert_not_called()

            with mock.patch.object(main, "_latest_pkl_mtime", return_value=0.0):
                generation = main._warm_tick(None)
                self.assertEqual(generation, main._cache_generation)
                self.assertEqual(warm.call_count, 1)

                self.assertEqual(main._warm_tick(generation), generation)
                self.assertEqual(warm.call_count, 1, "同一世代不重複預熱")

                self._clear()
                main._warm_tick(generation)
                self.assertEqual(warm.call_count, 2, "快取被清後要再預熱")

    def test_warm_groups_exist(self):
        self.assertLessEqual(set(self.main._WARM_GROUPS), set(self.main.chart_id_list))


if __name__ == "__main__":
    unittest.main()
