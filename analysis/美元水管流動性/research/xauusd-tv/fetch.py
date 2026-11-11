"""取得 TradingView 圖表上指定 symbol 的 K 線（經 CDP 9222 讀 TradingView Desktop 已載入的 bars）。
由 tv-gld-1m/fetch.py 複製改寫：SYMBOL 改為 --symbol 參數，輸出檔名依來源 exchange 命名。

用法（在本任務資料夾執行）：
    PYTHONUTF8=1 C:/code/2026-04-05-tradingview-control/venv/Scripts/python.exe -I fetch.py --symbol OANDA:XAUUSD --from-date 2026-10-29 --to-date 2026-11-06 --timeframe 5
輸出：xauusd_<exchange小寫>_<timeframe>m.csv（例如 xauusd_oanda_5m.csv），原始回應存 raw/。

做法：
1. 記下目前圖表 symbol/timeframe；切到 AMEX:GLD、timeframe 1。
2. TradingView 初始只載入約 300 根 bars。用 timeScale().zoomToBarsRange() 把可視範圍往左推，
   觸發歷史載入，直到 bars 涵蓋 --from-date 或載入不再增加。
   （專案 wrapper 的 scroll_to_date / set_range 只能對應已載入的 bars，無法觸發歷史載入。）
3. 讀取已載入的全部 bars（time 為 UTC epoch 秒，即 K 線開始時間），轉美東時間，篩選日期區間，寫 gld_1m.csv。
4. 不論成功或失敗，最後都用 set_symbol / set_timeframe 還原原圖表。
"""
import argparse
import csv
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

TASK = Path(__file__).resolve().parent
TV_DIR = Path("C:/code/2026-04-05-tradingview-control")
TV_MCP = TV_DIR / "tradingview-mcp"
TV_CLI = TV_MCP / "src" / "cli" / "index.js"
sys.path.insert(0, str(TV_DIR))
import tv_client as tv  # noqa: E402

DEFAULT_TF = "5"    # TradingView timeframe 代碼，分鐘數（"1" = 1 分鐘，"5" = 5 分鐘）
SETTLE = 4          # 切換 symbol/timeframe 後等待秒數（同專案 fetch_ohlcv 的 SYMBOL_SETTLE_SECONDS）
LOAD_WAIT = 8       # 每次推動可視範圍後等待歷史載入秒數
MAX_ITER = 40
STALE_LIMIT = 3     # 連續幾次 firstIndex 沒有進展就停止
ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

CHART = "window.TradingViewApi._activeChartWidgetWV.value()._chartWidget.model()"
BARS = CHART + ".mainSeries().bars()"


def ui_eval(expr: str) -> str:
    """透過專案 CLI 的 `ui eval` 在 TradingView 頁面執行 JS，回傳 result 字串。"""
    env = {**os.environ, "NODE_NO_WARNINGS": "1"}
    r = subprocess.run(["node", str(TV_CLI), "ui", "eval", expr], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=90, cwd=str(TV_MCP), env=env)
    try:
        resp = json.loads(r.stdout.strip())
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"ui eval 回應無法解析: {r.stdout[:300]} {r.stderr[:300]}") from e
    if not resp.get("success"):
        raise RuntimeError(f"ui eval 失敗: {resp}")
    return resp["result"]


def bar_span() -> dict:
    expr = ("(function(){var b=" + BARS + ";var f=b.firstIndex(),l=b.lastIndex();"
            "var vf=b.valueAt(f),vl=b.valueAt(l);"
            "return JSON.stringify({first:f,last:l,size:b.size(),tf:vf?vf[0]:null,tl:vl?vl[0]:null});})()")
    return json.loads(ui_eval(expr))


def backfill(from_ts: int) -> None:
    """往左推可視範圍，直到已載入 bars 的最早時間 <= from_ts 或不再進展。"""
    last_first = None
    stale = 0
    for it in range(MAX_ITER):
        ui_eval("(function(){var m=" + CHART + ";var b=m.mainSeries().bars();var f=b.firstIndex();"
                "m.timeScale().zoomToBarsRange(f-3000, b.lastIndex());return 'ok';})()")
        time.sleep(LOAD_WAIT)
        span = bar_span()
        first_ts = span["tf"]
        print(f"BACKFILL it={it} bars={span['size']} earliest_utc="
              f"{dt.datetime.fromtimestamp(first_ts, UTC).isoformat() if first_ts else None}", flush=True)
        if first_ts and first_ts <= from_ts:
            print("BACKFILL reached from-date", flush=True)
            return
        stale = stale + 1 if first_ts == last_first else 0
        last_first = first_ts
        if stale >= STALE_LIMIT:
            print("BACKFILL no progress; stop", flush=True)
            return


def read_all_bars() -> list:
    expr = ("(function(){var b=" + BARS + ";var out=[];for(var i=b.firstIndex();i<=b.lastIndex();i++){"
            "var v=b.valueAt(i);if(v)out.push([v[0],v[1],v[2],v[3],v[4],v[5]||0]);}"
            "return JSON.stringify(out);})()")
    return json.loads(ui_eval(expr))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True, help="TradingView symbol，例如 OANDA:XAUUSD")
    ap.add_argument("--from-date", required=True, help="起始日 YYYY-MM-DD（美東）")
    ap.add_argument("--to-date", default="2026-11-06", help="結束日 YYYY-MM-DD（美東，含）")
    ap.add_argument("--timeframe", default=DEFAULT_TF, help="TradingView timeframe 代碼（分鐘數），預設 5")
    ap.add_argument("--reload", action="store_true", help="回補前先切 1 分鐘再切回目標 timeframe（強制重載序列）")
    ap.add_argument("--load-wait", type=int, default=8,help="每次推動可視範圍後等待秒數，預設 8（即 LOAD_WAIT）")
    args = ap.parse_args()
    global LOAD_WAIT
    LOAD_WAIT = args.load_wait
    TF = str(args.timeframe)
    SYMBOL = args.symbol
    SLUG = SYMBOL.split(":", 1)[0].lower()  # 來源 exchange，例如 oanda / fx_idc / tvc
    from_d = dt.date.fromisoformat(args.from_date)
    to_d = dt.date.fromisoformat(args.to_date)
    from_ts = int(dt.datetime.combine(from_d, dt.time(0), tzinfo=ET).timestamp())

    raw_dir = TASK / "raw"
    raw_dir.mkdir(exist_ok=True)

    orig = tv.state()
    if not orig.get("success"):
        raise RuntimeError(f"無法讀取目前圖表狀態: {orig}")
    print("ORIG", json.dumps({"symbol": orig.get("symbol"), "resolution": orig.get("resolution")},
                             ensure_ascii=False), flush=True)
    try:
        r1 = tv.set_symbol(SYMBOL)
        print("SET_SYMBOL", r1, flush=True)
        time.sleep(SETTLE)
        r2 = tv.set_timeframe(TF)
        print("SET_TF", r2, flush=True)
        time.sleep(SETTLE)
        if args.reload:  # 方式 2：切到 1 分鐘再切回目標 timeframe，強制重新載入序列後再回補
            print("RELOAD", tv.set_timeframe("1"), flush=True)
            time.sleep(SETTLE)
            print("RELOAD", tv.set_timeframe(TF), flush=True)
            time.sleep(SETTLE)
        st = tv.state()
        got = st.get("symbol", "")
        print("CHART_STATE", json.dumps({"symbol": got, "resolution": st.get("resolution")}, ensure_ascii=False),
              flush=True)
        if st.get("resolution") != TF or got.upper() != SYMBOL.upper():
            raise RuntimeError(f"圖表未切到 {SYMBOL} {TF} 分鐘: {got} {st.get('resolution')}")

        backfill(from_ts)

        span = bar_span()
        print("SPAN", json.dumps(span, ensure_ascii=False), flush=True)
        bars = read_all_bars()
        stamp = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        raw_path = raw_dir / f"tv_{SLUG}_{TF}m_bars_{stamp}.json"
        raw_path.write_text(json.dumps({"chart_symbol": got, "resolution": TF, "fetched_utc": stamp,
                                        "bars": bars}, ensure_ascii=False), encoding="utf-8")
        print("RAW_SAVED", raw_path.name, "n_bars", len(bars), flush=True)
    finally:
        restore_sym = orig.get("symbol")
        restore_tf = str(orig.get("resolution"))
        try:
            print("RESTORE_SYMBOL", tv.set_symbol(restore_sym), flush=True)
            time.sleep(SETTLE)
            print("RESTORE_TF", tv.set_timeframe(restore_tf), flush=True)
            time.sleep(SETTLE)
        finally:
            fin = tv.state()
            print("FINAL_STATE", json.dumps({"symbol": fin.get("symbol"), "resolution": fin.get("resolution")},
                                            ensure_ascii=False), flush=True)

    # 轉美東並篩選
    rows = {}
    for t, o, h, l, c, v in bars:
        d_et = dt.datetime.fromtimestamp(t, UTC).astimezone(ET)
        d = d_et.date()
        if d < from_d or d > to_d:
            continue
        key = (d.isoformat(), d_et.strftime("%H:%M"))
        rows[key] = {"date": key[0], "time_et": key[1], "open": o, "high": h, "low": l, "close": c,
                     "volume": int(v)}
    out_rows = [rows[k] for k in sorted(rows)]
    out_path = TASK / f"xauusd_{SLUG}_{TF}m.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "time_et", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(out_rows)
    print("CSV_WRITTEN", out_path.name, "rows", len(out_rows), flush=True)
    print("TIMEFRAME", TF, flush=True)
    if out_rows:
        print("CSV_RANGE", out_rows[0]["date"], out_rows[0]["time_et"], "->",
              out_rows[-1]["date"], out_rows[-1]["time_et"], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
