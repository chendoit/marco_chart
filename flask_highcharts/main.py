from flask import Flask, jsonify, render_template, send_from_directory, request, make_response
import ctypes
import gzip
import json
import math
import os
import threading
import time
import hashlib
import importlib.util
from loguru import logger

from app.utils import clear_series_cache

app = Flask(__name__)

logger.add("app.log", rotation="10 MB", level="INFO")

GROUPS_DIR = os.path.join("app", "routes")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# 快取已載入的模組，避免每次 API 請求都重新 exec_module
_loaded_modules = {}
chart_id_list = {}

# --- data version & API cache ---
_data_version = ""
_last_check_time = 0.0
_CHECK_INTERVAL = 60  # 每 60 秒最多重掃一次 pkl mtime
_api_cache = {}
_gzip_cache = {}  # (path, etag) -> gzip bytes
_cache_generation = 0  # 每次清快取 +1；計算途中若改變，結果就是舊資料，不可寫入快取
_code_token = format(time.time_ns(), "x")  # 重啟或熱更新就換，讓瀏覽器不會用 304 留住舊圖表設定
_version_lock = threading.Lock()
_group_locks = {}  # group -> Lock，同一群組同時間只算一次

# --- 預熱：資料批次更新完後，先算好常開的重頁面 ---
_WARM_GROUPS = ("左尾風險監控", "每日天啟", "McElligott波動率微結構")
_WARM_QUIET_SECONDS = 300  # pkl 連續這麼久沒變動，才視為批次更新結束
_WARM_POLL_SECONDS = 30
_WARM_MIN_AVAILABLE_MB = 800  # 可用記憶體低於此值就暫停預熱，下一輪再試
_warm_low_memory_warned = False


@app.after_request
def _gzip_response(resp):
    """對 JSON/HTML 做 gzip（7.8MB 的圖表 JSON 可壓到 1MB 內）；API 壓縮結果依 ETag 快取。"""
    if (
        resp.status_code != 200
        or resp.direct_passthrough
        or "Content-Encoding" in resp.headers
        or "gzip" not in request.headers.get("Accept-Encoding", "")
        or resp.mimetype not in ("application/json", "text/html")
    ):
        return resp
    data = resp.get_data()
    if len(data) < 1024:
        return resp
    etag = resp.headers.get("ETag")
    key = (request.path, etag) if etag else None
    gz = _gzip_cache.get(key) if key else None
    if gz is None:
        gz = gzip.compress(data, compresslevel=6)
        if key:
            if len(_gzip_cache) > 64:
                _gzip_cache.clear()
            _gzip_cache[key] = gz
    resp.set_data(gz)
    resp.headers["Content-Encoding"] = "gzip"
    resp.headers["Content-Length"] = str(len(gz))
    resp.headers.add("Vary", "Accept-Encoding")
    return resp


def _latest_pkl_mtime():
    """data/ 下所有 pkl 中最新的修改時間（epoch 秒）。"""
    max_mtime = 0.0
    try:
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".pkl"):
                fpath = os.path.join(DATA_DIR, fname)
                mt = os.path.getmtime(fpath)
                if mt > max_mtime:
                    max_mtime = mt
    except OSError:
        pass
    return max_mtime


def _compute_data_version():
    """掃描 data/ 下所有 pkl 的最後修改時間，產生版本 hash。"""
    return hashlib.md5(str(_latest_pkl_mtime()).encode()).hexdigest()[:12]


def _current_etag():
    return f"{_data_version}-{_code_token}"


def _clear_caches():
    """清除所有快取。呼叫端須持有 _version_lock。"""
    global _cache_generation
    _cache_generation += 1
    _api_cache.clear()
    _gzip_cache.clear()
    clear_series_cache()


def _refresh_data_version_if_needed(force=False):
    """定期掃描 pkl 檔案 mtime，若 data version 改變則清除所有快取。"""
    global _data_version, _last_check_time
    with _version_lock:
        now = time.monotonic()
        if not force and now - _last_check_time < _CHECK_INTERVAL:
            return
        _last_check_time = now
        new_version = _compute_data_version()
        if new_version != _data_version:
            logger.info("Data version changed: {} -> {}, clearing caches", _data_version, new_version)
            _data_version = new_version
            _clear_caches()


def _init_data_version():
    global _data_version, _last_check_time
    _last_check_time = time.monotonic()
    _data_version = _compute_data_version()
    logger.info("Initial data_version: {}", _data_version)


def _load_module(group_name):
    """載入單一 group 模組並快取。"""
    module_path = os.path.join(GROUPS_DIR, f"{group_name}.py")
    spec = importlib.util.spec_from_file_location(group_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _loaded_modules[group_name] = module
    chart_id_list[group_name] = module.CHART_IDS
    return module


def _load_all_modules():
    """載入所有 group 模組。"""
    _loaded_modules.clear()
    chart_id_list.clear()
    for filename in os.listdir(GROUPS_DIR):
        if filename.endswith(".py"):
            group_name = filename[:-3]
            _load_module(group_name)


_init_data_version()
_load_all_modules()
logger.info("Loaded groups: {}", list(chart_id_list.keys()))


def _sanitize_value(v):
    """將 NaN / Infinity / 非數值 替換為 None，確保 JSON 序列化合法且 Highcharts 可用。"""
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, str):
        return None
    return v


def _build_group_charts(group_name):
    """計算一個 group 的所有 chart 資料（純運算，不含 HTTP 邏輯）。"""
    module = _loaded_modules[group_name]
    chart_ids = module.CHART_IDS
    summary_list = module.SUMMARY_LIST
    charts = []

    for i, chart_group in enumerate(chart_ids):
        custom = module.get_custom_config(i) if hasattr(module, 'get_custom_config') else None
        if custom is not None:
            charts.append(custom)
            continue

        if isinstance(chart_group, list):
            data = module.generate_chart_data(chart_group)
            config = module.get_chart_config(chart_group)
        else:
            data = module.generate_chart_data([chart_group])
            config = module.get_chart_config([chart_group])

        series_list = []
        for series_info in data["series"]:
            s = {
                "name": series_info.get("name"),
                "yAxis": series_info.get("yAxis", 0),
                "color": series_info.get("color", "rgba(75, 192, 192, 1)"),
                "visible": series_info.get("visible", True),
            }
            if series_info.get("ohlc"):
                s["data"] = series_info["data"]
                s["type"] = "candlestick"
            else:
                s["data"] = [
                    [k, _sanitize_value(v)]
                    for k, v in series_info.get("data", {}).items()
                    if _sanitize_value(v) is not None
                ]
            series_list.append(s)
        config["series"] = series_list

        summary = summary_list[i] if i < len(summary_list) else None
        charts.append({"config": config, "summary": summary})

    return charts


def _get_group_json(group_name):
    """回傳 (json 字串, ETag)。同一群組同時間只算一次，其他請求等結果。"""
    with _group_locks.setdefault(group_name, threading.Lock()):
        etag = _current_etag()
        cached = _api_cache.get(group_name)
        if cached is not None:
            logger.info("Cache hit for '{}'", group_name)
            return cached, etag

        generation = _cache_generation
        charts = _build_group_charts(group_name)
        json_str = jsonify({"charts": charts}).get_data(as_text=True)
        with _version_lock:
            if generation == _cache_generation:
                _api_cache[group_name] = json_str
                logger.info("Computed and cached chart data for '{}'", group_name)
            else:
                # 計算途中資料已更新：不存這份舊結果，並清掉這次計算可能寫回的舊序列
                clear_series_cache()
                logger.info("Discarded stale chart data for '{}'", group_name)
        return json_str, etag


def _available_memory_mb():
    """系統可用實體記憶體（MB）。"""

    class _MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong)
            for name in ("total_phys", "avail_phys", "total_page", "avail_page",
                         "total_virtual", "avail_virtual", "avail_extended")
        ]

    status = _MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError()
    return status.avail_phys / (1024 * 1024)


def _warm_groups():
    """走完整 API 路徑預熱，讓 JSON 與 gzip 快取都就緒。記憶體不足時回傳 False，稍後再試。"""
    global _warm_low_memory_warned
    client = app.test_client()
    for group_name in _WARM_GROUPS:
        if group_name not in chart_id_list:
            continue
        available_mb = _available_memory_mb()
        if available_mb < _WARM_MIN_AVAILABLE_MB:
            if not _warm_low_memory_warned:
                logger.warning("Pause chart warm-up: available memory {:.0f} MB", available_mb)
                _warm_low_memory_warned = True
            return False
        started = time.monotonic()
        resp = client.get(f"/api/chart/{group_name}", headers={"Accept-Encoding": "gzip"})
        logger.info("Warmed '{}': HTTP {} in {:.1f}s", group_name, resp.status_code,
                    time.monotonic() - started)
    _warm_low_memory_warned = False
    return True


def _warm_tick(warmed_generation):
    """資料穩定且快取世代未預熱過時預熱一次，回傳最後預熱完成的世代。"""
    if time.time() - _latest_pkl_mtime() < _WARM_QUIET_SECONDS:
        return warmed_generation
    _refresh_data_version_if_needed(force=True)
    generation = _cache_generation
    if generation == warmed_generation:
        return warmed_generation
    return generation if _warm_groups() else warmed_generation


def _warm_loop():
    warmed_generation = None
    while True:
        try:
            warmed_generation = _warm_tick(warmed_generation)
        except Exception as e:
            logger.exception("Chart warm-up failed: {}", e)
        time.sleep(_WARM_POLL_SECONDS)


@app.route('/favicon.ico')
def favicon():
    logger.info(f"Accessed favicon {app.root_path}")
    return send_from_directory(os.path.join(app.root_path, 'static'),
                              'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/")
def index():
    logger.info("Accessed index page")
    return render_template("index.html", chart_id_list=chart_id_list.keys())


@app.route("/api/chart/<group_name>")
def get_chart_data(group_name):
    if group_name not in chart_id_list:
        logger.warning("Group '{}' not found", group_name)
        return jsonify({"error": f"Group {group_name} not found"}), 404

    _refresh_data_version_if_needed()

    client_etag = request.headers.get("If-None-Match", "").strip('" ')
    if client_etag == _current_etag():
        return "", 304

    try:
        json_str, etag = _get_group_json(group_name)
        resp = make_response(json_str)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["ETag"] = f'"{etag}"'
        return resp
    except Exception as e:
        logger.exception("Error in get_chart_data for '{}': {}", group_name, e)
        return jsonify({"error": str(e)}), 500


@app.route("/charts/<group_name>")
def show_charts(group_name):
    if group_name not in chart_id_list:
        logger.warning("Chart group '{}' not found", group_name)
        return "Group not found", 404

    logger.info("Accessed charts page for group '{}'.", group_name)
    return render_template("charts.html", group_name=group_name, group_list=list(chart_id_list.keys()))


@app.route("/api/update_groups", methods=["GET"])
def update_groups():
    """重新載入所有 group 模組（熱更新），同時清除快取。"""
    global _code_token
    try:
        with _version_lock:
            _clear_caches()
            _code_token = format(time.time_ns(), "x")
        _load_all_modules()
        _init_data_version()
        logger.info("Updated chart_id_list: {}", list(chart_id_list.keys()))
        return jsonify({"success": True, "chart_id_list": list(chart_id_list.keys())})
    except Exception as e:
        logger.error("Error updating groups: {}", e)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    is_dev = os.environ.get('FLASK_ENV') != 'production'
    port = 6002 if is_dev else 5002

    logger.info(f"Starting Flask app chart dev: {is_dev} port {port} ")
    if not is_dev:
        threading.Thread(target=_warm_loop, name="chart-warmer", daemon=True).start()
    app.run(debug=False, host="0.0.0.0", port=port)
