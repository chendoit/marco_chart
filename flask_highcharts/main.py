from flask import Flask, jsonify, render_template, send_from_directory
import os
import importlib.util
from loguru import logger

app = Flask(__name__)

logger.add("app.log", rotation="10 MB", level="INFO")

GROUPS_DIR = os.path.join("app", "routes")

# 快取已載入的模組，避免每次 API 請求都重新 exec_module
_loaded_modules = {}
chart_id_list = {}


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


_load_all_modules()
logger.info("Loaded groups: {}", list(chart_id_list.keys()))


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

    try:
        module = _loaded_modules[group_name]
        chart_ids = module.CHART_IDS
        summary_list = module.SUMMARY_LIST
        charts = []

        for i, chart_group in enumerate(chart_ids):
            try:
                if isinstance(chart_group, list):
                    data = module.generate_chart_data(chart_group)
                    config = module.get_chart_config(chart_group)
                else:
                    data = module.generate_chart_data([chart_group])
                    config = module.get_chart_config([chart_group])

                config["series"] = [
                    {
                        "name": series_info.get("name"),
                        "data": list(series_info.get("data", {}).items()),
                        "yAxis": series_info.get("yAxis", 0),
                        "color": series_info.get("color", "rgba(75, 192, 192, 1)")
                    }
                    for series_info in data["series"]
                ]

                summary = summary_list[i] if i < len(summary_list) else None
                charts.append({"config": config, "summary": summary})
            except Exception as e:
                logger.error("Error generating chart data for '{}': {}", group_name, e)
                return jsonify({"error": f"Failed to generate chart data for group {group_name}"}), 500

        logger.info("Successfully retrieved chart data for '{}'.", group_name)
        return jsonify({"charts": charts})
    except Exception as e:
        logger.exception("Unexpected error in get_chart_data for '{}': {}", group_name, e)
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
    """重新載入所有 group 模組（熱更新）。"""
    try:
        _load_all_modules()
        logger.info("Updated chart_id_list: {}", list(chart_id_list.keys()))
        return jsonify({"success": True, "chart_id_list": list(chart_id_list.keys())})
    except Exception as e:
        logger.error("Error updating groups: {}", e)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    is_dev = os.environ.get('FLASK_ENV') != 'production'
    port = 6002 if is_dev else 5002

    logger.info(f"Starting Flask app chart dev: {is_dev} port {port} ")
    app.run(debug=False, port=port)
