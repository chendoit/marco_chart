from flask import Flask, jsonify, render_template, send_from_directory, request, make_response
import json
import math
import os
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


def _compute_data_version():
    """掃描 data/ 下所有 pkl 的最後修改時間，產生版本 hash。"""
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
    return hashlib.md5(str(max_mtime).encode()).hexdigest()[:12]


def _refresh_data_version_if_needed():
    """定期掃描 pkl 檔案 mtime，若 data version 改變則清除所有快取。"""
    global _data_version, _last_check_time
    now = time.monotonic()
    if now - _last_check_time < _CHECK_INTERVAL:
        return
    _last_check_time = now
    new_version = _compute_data_version()
    if new_version != _data_version:
        logger.info("Data version changed: {} -> {}, clearing caches", _data_version, new_version)
        _data_version = new_version
        _api_cache.clear()
        clear_series_cache()


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
    if client_etag == _data_version:
        return "", 304

    if group_name in _api_cache:
        logger.info("Cache hit for '{}'", group_name)
        resp = make_response(_api_cache[group_name])
        resp.headers["Content-Type"] = "application/json"
        resp.headers["ETag"] = f'"{_data_version}"'
        return resp

    try:
        charts = _build_group_charts(group_name)
        json_str = jsonify({"charts": charts}).get_data(as_text=True)
        _api_cache[group_name] = json_str

        logger.info("Computed and cached chart data for '{}'", group_name)
        resp = make_response(json_str)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["ETag"] = f'"{_data_version}"'
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
    try:
        _api_cache.clear()
        clear_series_cache()
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
    app.run(debug=False, host="0.0.0.0", port=port)
