# -*- coding: utf-8 -*-
"""
probe_mlit.py: 不動産情報ライブラリ（reinfolib）公開 API 測試與樣本擷取腳本
本腳本自環境設定讀取 MLIT_TOKEN，針對重點 API 進行呼叫測試，
並將各端點回應樣本（大型結果截取前 200 筆）儲存至 samples/ 目錄。
"""

import os
import sys
import json
import time
from pathlib import Path
import requests

def get_token():
    # 尋找專案根目錄的 .env 檔案
    # 依序尋找當前路徑的父目錄直到找到包含 .env 的目錄
    curr = Path(__file__).resolve().parent
    env_file = None
    for _ in range(5):
        candidate = curr / ".env"
        if candidate.exists():
            env_file = candidate
            break
        candidate2 = Path(r"C:\code\2025-12-05-MacroMicro-Data\.env")
        if candidate2.exists():
            env_file = candidate2
            break
        curr = curr.parent

    if not env_file or not env_file.exists():
        raise RuntimeError("找不到 .env 檔案")

    token = None
    with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("MLIT_TOKEN"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    token = parts[1].strip().strip("'\"")
                    break

    if not token:
        raise RuntimeError("在 .env 中找不到 MLIT_TOKEN")
    return token

def main():
    token = get_token()
    headers = {
        "Ocp-Apim-Subscription-Key": token,
        "User-Agent": "MacroMicro-Research-Probe/1.0"
    }

    out_dir = Path(__file__).parent / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    endpoints = [
        {
            "id": "XIT001",
            "filename": "sample_xit001_trade_prices.json",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT001?year=2024&quarter=1&city=13101",
            "desc": "不動産価格（取引価格・成約価格）情報取得API (東京都千代田區 2024Q1)"
        },
        {
            "id": "XIT002",
            "filename": "sample_xit002_municipalities.json",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XIT002?area=13",
            "desc": "都道府県内市区町村一覧取得API (東京都)"
        },
        {
            "id": "XCT001",
            "filename": "sample_xct001_appraisal_reports.json",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XCT001?year=2024&area=13&division=00",
            "desc": "鑑定評価書情報API (東京都 2024 住宅地)"
        },
        {
            "id": "XPT001",
            "filename": "sample_xpt001_trade_points.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XPT001?response_format=geojson&z=14&x=14624&y=6016&from=20241&to=20242",
            "desc": "不動産価格（取引価格・成約価格）情報のポイント(点) API"
        },
        {
            "id": "XPT002",
            "filename": "sample_xpt002_land_price_points.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XPT002?response_format=geojson&z=14&x=14624&y=6016&year=2024",
            "desc": "地価公示・地価調査のポイント (点) API"
        },
        {
            "id": "XKT001",
            "filename": "sample_xkt001_city_planning_areas.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT001?response_format=geojson&z=14&x=14626&y=6020",
            "desc": "都市計画決定GISデータ（都市計画区域/区域区分）API"
        },
        {
            "id": "XKT002",
            "filename": "sample_xkt002_use_areas.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT002?response_format=geojson&z=14&x=14339&y=6505",
            "desc": "都市計画決定GISデータ（用途地域）API"
        },
        {
            "id": "XKT013",
            "filename": "sample_xkt013_future_population_mesh.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT013?response_format=geojson&z=15&x=29195&y=12192",
            "desc": "国土数値情報（将来推計人口250mメッシュ）API"
        },
        {
            "id": "XKT015",
            "filename": "sample_xkt015_station_ridership.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT015?response_format=geojson&z=14&x=14547&y=6462",
            "desc": "国土数値情報（駅別乗降客数）API"
        },
        {
            "id": "XKT026",
            "filename": "sample_xkt026_flood_risk.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XKT026?response_format=geojson&z=14&x=14432&y=6392",
            "desc": "国土数値情報（洪水浸水想定区域）API"
        },
        {
            "id": "XGT001",
            "filename": "sample_xgt001_evacuation_sites.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XGT001?response_format=geojson&z=11&x=1786&y=816",
            "desc": "国土地理院GISデータ（指定緊急避難場所）API"
        },
        {
            "id": "XST001",
            "filename": "sample_xst001_disaster_history.geojson",
            "url": "https://www.reinfolib.mlit.go.jp/ex-api/external/XST001?response_format=geojson&z=14&x=14467&y=6503",
            "desc": "国土調査（災害履歴）API"
        }
    ]

    for item in endpoints:
        eid = item["id"]
        fname = item["filename"]
        target_path = out_dir / fname
        url = item["url"]

        print(f"[{eid}] 請求中: {item['desc']}...")
        try:
            resp = requests.get(url, headers=headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                # 截取前 200 筆以符合大型回應儲存規範
                if isinstance(data, dict):
                    if "data" in data and isinstance(data["data"], list):
                        raw_len = len(data["data"])
                        data["data"] = data["data"][:200]
                        data["_probe_note"] = f"Total returned: {raw_len}, truncated to first 200"
                    elif "features" in data and isinstance(data["features"], list):
                        raw_len = len(data["features"])
                        data["features"] = data["features"][:200]
                        data["_probe_note"] = f"Total returned: {raw_len}, truncated to first 200"
                elif isinstance(data, list):
                    raw_len = len(data)
                    data = data[:200]

                target_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[{eid}] 成功 (HTTP 200) -> 儲存至 {fname} (大小: {target_path.stat().st_size} bytes)")
            else:
                print(f"[{eid}] 回應非 200: HTTP {resp.status_code}")
        except Exception as e:
            print(f"[{eid}] 請求失敗: {e}")

        time.sleep(1.2)

    # 確保 trade_quarterly_summary.csv 存在
    summary_dest = out_dir / "trade_quarterly_summary.csv"
    tmp_summary = Path(__file__).resolve().parent.parent / "tmp" / "trade_quarterly_summary.csv"
    if tmp_summary.exists():
        summary_dest.write_text(tmp_summary.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        print(f"已同步季度彙總檔: trade_quarterly_summary.csv ({summary_dest.stat().st_size} bytes)")

    print("Probe 完成。")

if __name__ == "__main__":
    main()
