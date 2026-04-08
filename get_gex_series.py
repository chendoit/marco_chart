# [時間戳規範] 所有寫入 pkl 的 datetime 時間部分統一為 08:00:00 (UTC+8)
# 以與 MacroMicro series 的 fromtimestamp() 產出一致。新增抓取腳本時請遵循此規範。
import os
import pickle
import sqlite3
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

load_dotenv()

logger.add("./logs/{time:YYYY-MM-DD}.log", enqueue=True)

DATA_DIR = os.getenv("DATA_DIR")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

GEX_DB_PATH = r"C:\code\2026-03-24-GEX-lieta\gex_analysis.db"

TICKERS = ["spx", "spy", "vix"]

LEVEL_COLS = {
    "gamma_flip":     ("daily_levels", "gamma_flip"),
    "gamma_flip_ce":  ("daily_levels", "gamma_flip_ce"),
    "call_wall_ce":   ("daily_levels", "call_wall_ce"),
    "put_wall_ce":    ("daily_levels", "put_wall_ce"),
    "gamma_field_ce": ("daily_levels", "gamma_field_ce"),
}


def _save_pkl(name, title, data):
    pkl_path = os.path.join(DATA_DIR, f"{name}.pkl")
    with open(pkl_path, "wb") as f:
        pickle.dump({"title": title, "data": data}, f)
    logger.info(f"Saved {len(data)} records -> {pkl_path}")


def _extract_level_series(conn, ticker, col_name, table):
    """Extract a single column from daily_levels as [[datetime, float], ...]."""
    rows = conn.execute(
        f"SELECT date, {col_name} FROM {table} "
        f"WHERE ticker=? AND {col_name} IS NOT NULL ORDER BY date",
        (ticker,),
    ).fetchall()
    data = []
    for row in rows:
        dt = datetime.strptime(row[0], "%Y-%m-%d").replace(hour=8)
        data.append([dt, float(row[1])])
    return data


def _extract_spot_price(conn, ticker):
    """Extract spot_price from gamma_snapshot."""
    rows = conn.execute(
        "SELECT date, spot_price FROM gamma_snapshot "
        "WHERE ticker=? AND spot_price IS NOT NULL ORDER BY date",
        (ticker,),
    ).fetchall()
    data = []
    for row in rows:
        dt = datetime.strptime(row[0], "%Y-%m-%d").replace(hour=8)
        data.append([dt, float(row[1])])
    return data


def _extract_gamma_env(conn, ticker):
    """Extract gamma_env_ce from daily_summary as numeric: positive=1, negative=-1."""
    rows = conn.execute(
        "SELECT date, gamma_env_ce FROM daily_summary "
        "WHERE ticker=? AND gamma_env_ce IS NOT NULL ORDER BY date",
        (ticker,),
    ).fetchall()
    data = []
    for row in rows:
        dt = datetime.strptime(row[0], "%Y-%m-%d").replace(hour=8)
        env_str = row[1].strip().lower() if row[1] else ""
        if env_str == "positive":
            val = 1.0
        elif env_str == "negative":
            val = -1.0
        else:
            continue
        data.append([dt, val])
    return data


def _export_flip_distance(conn, ticker):
    """Compute (spot - gamma_flip_ce) / spot * 100 and save as pkl."""
    rows = conn.execute(
        "SELECT dl.date, gs.spot_price, dl.gamma_flip_ce "
        "FROM daily_levels dl "
        "JOIN gamma_snapshot gs ON dl.date = gs.date AND dl.ticker = gs.ticker "
        "WHERE dl.ticker = ? AND dl.gamma_flip_ce IS NOT NULL AND gs.spot_price IS NOT NULL "
        "ORDER BY dl.date",
        (ticker,),
    ).fetchall()
    data = []
    for row in rows:
        dt = datetime.strptime(row[0], "%Y-%m-%d").replace(hour=8)
        spot, flip = float(row[1]), float(row[2])
        if spot != 0:
            data.append([dt, (spot - flip) / spot * 100])
    _save_pkl(
        f"gex_{ticker}_flip_distance",
        f"GEX {ticker.upper()} Gamma Flip Distance %",
        data,
    )


VOL_SURFACE_TICKERS = ["spx"]

SKEW_CONFIGS = [
    ("1m", "1M"),
    ("3m", "3M"),
]


def _export_skew_series(conn, ticker):
    """Export put_skew, call_skew, skew_ratio per tenor_bucket."""
    tk_upper = ticker.upper()
    for bucket, label in SKEW_CONFIGS:
        rows = conn.execute(
            "SELECT date, AVG(put_skew), AVG(call_skew), AVG(skew_ratio) "
            "FROM v_skew_indicators "
            "WHERE ticker=? AND tenor_bucket=? AND put_skew IS NOT NULL "
            "GROUP BY date ORDER BY date",
            (ticker, bucket),
        ).fetchall()
        put_skew, call_skew, skew_ratio = [], [], []
        for r in rows:
            dt = datetime.strptime(r[0], "%Y-%m-%d").replace(hour=8)
            if r[1] is not None:
                put_skew.append([dt, float(r[1])])
            if r[2] is not None:
                call_skew.append([dt, float(r[2])])
            if r[3] is not None:
                skew_ratio.append([dt, float(r[3])])
        _save_pkl(f"gex_{ticker}_put_skew_{bucket}",
                  f"{tk_upper} {label} Put Skew 25dP/ATM", put_skew)
        _save_pkl(f"gex_{ticker}_call_skew_{bucket}",
                  f"{tk_upper} {label} Call Skew 25dC/ATM", call_skew)
        _save_pkl(f"gex_{ticker}_skew_ratio_{bucket}",
                  f"{tk_upper} {label} Skew 25dP/25dC", skew_ratio)


def _export_term_slope(conn, ticker):
    """Export term structure slope (far ATM IV - near ATM IV)."""
    rows = conn.execute(
        "SELECT date, term_slope_atm FROM v_term_slope "
        "WHERE ticker=? ORDER BY date",
        (ticker,),
    ).fetchall()
    data = []
    for r in rows:
        if r[1] is not None:
            dt = datetime.strptime(r[0], "%Y-%m-%d").replace(hour=8)
            data.append([dt, float(r[1])])
    _save_pkl(f"gex_{ticker}_term_slope",
              f"{ticker.upper()} IV Term Slope", data)


def _export_vol_reference(conn, ticker):
    """Export iv30, vrp_surface (iv30 - rvol_20d) from daily_vol_reference."""
    rows = conn.execute(
        "SELECT date, iv30, rvol_20d FROM daily_vol_reference "
        "WHERE ticker=? ORDER BY date",
        (ticker,),
    ).fetchall()
    iv30_data, vrp_data = [], []
    for r in rows:
        dt = datetime.strptime(r[0], "%Y-%m-%d").replace(hour=8)
        if r[1] is not None:
            iv30_data.append([dt, float(r[1]) * 100])
        if r[1] is not None and r[2] is not None:
            vrp_data.append([dt, (float(r[1]) - float(r[2])) * 100])
    tk_upper = ticker.upper()
    _save_pkl(f"gex_{ticker}_iv30", f"{tk_upper} IV30", iv30_data)
    _save_pkl(f"gex_{ticker}_vrp_surface",
              f"{tk_upper} Surface VRP (IV30-RVol20)", vrp_data)


def _export_gamma_summary(conn, ticker):
    """Export call_gamma, put_gamma, net_gamma from daily_gamma_summary."""
    rows = conn.execute(
        "SELECT date, call_gamma, put_gamma, net_gamma "
        "FROM daily_gamma_summary WHERE ticker=? ORDER BY date",
        (ticker,),
    ).fetchall()
    call_data, put_data, net_data = [], [], []
    tk_upper = ticker.upper()
    for r in rows:
        dt = datetime.strptime(r[0], "%Y-%m-%d").replace(hour=8)
        if r[1] is not None:
            call_data.append([dt, float(r[1]) / 1e9])
        if r[2] is not None:
            put_data.append([dt, float(r[2]) / 1e9])
        if r[3] is not None:
            net_data.append([dt, float(r[3]) / 1e9])
    _save_pkl(f"gex_{ticker}_call_gamma",
              f"{tk_upper} Call Gamma ($B)", call_data)
    _save_pkl(f"gex_{ticker}_put_gamma",
              f"{tk_upper} Put Gamma ($B)", put_data)
    _save_pkl(f"gex_{ticker}_net_gamma",
              f"{tk_upper} Net Gamma ($B)", net_data)


def _export_gamma_0dte(conn, ticker):
    """Export 0DTE vs non-0DTE net gamma from daily_gamma_by_expiry."""
    rows = conn.execute(
        "SELECT date, dte, net_gamma FROM daily_gamma_by_expiry "
        "WHERE ticker=? ORDER BY date, dte",
        (ticker,),
    ).fetchall()
    by_date = {}
    for r in rows:
        date_str, dte, net_g = r[0], r[1], r[2]
        if net_g is None:
            continue
        if date_str not in by_date:
            by_date[date_str] = {"0dte": 0.0, "non0dte": 0.0}
        if dte == 0:
            by_date[date_str]["0dte"] += float(net_g)
        else:
            by_date[date_str]["non0dte"] += float(net_g)

    dte0_data, non0_data = [], []
    tk_upper = ticker.upper()
    for date_str in sorted(by_date):
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=8)
        dte0_data.append([dt, by_date[date_str]["0dte"] / 1e9])
        non0_data.append([dt, by_date[date_str]["non0dte"] / 1e9])
    _save_pkl(f"gex_{ticker}_gamma_0dte",
              f"{tk_upper} 0DTE Net Gamma ($B)", dte0_data)
    _save_pkl(f"gex_{ticker}_gamma_non0dte",
              f"{tk_upper} Non-0DTE Net Gamma ($B)", non0_data)


def fetch_gex_series():
    """Read GEX-lieta gex_analysis.db and export SPX/SPY/VIX series as pkl."""
    if not os.path.exists(GEX_DB_PATH):
        logger.warning(f"GEX DB not found: {GEX_DB_PATH}")
        return

    conn = sqlite3.connect(GEX_DB_PATH)
    logger.info(f"Connected to {GEX_DB_PATH}")

    for ticker in TICKERS:
        logger.info(f"Exporting GEX series for {ticker.upper()}")

        for series_suffix, (table, col) in LEVEL_COLS.items():
            data = _extract_level_series(conn, ticker, col, table)
            name = f"gex_{ticker}_{series_suffix}"
            title = f"GEX {ticker.upper()} {series_suffix}"
            _save_pkl(name, title, data)

        data = _extract_spot_price(conn, ticker)
        _save_pkl(
            f"gex_{ticker}_spot_price",
            f"GEX {ticker.upper()} Spot Price",
            data,
        )

        data = _extract_gamma_env(conn, ticker)
        _save_pkl(
            f"gex_{ticker}_gamma_env",
            f"GEX {ticker.upper()} Gamma Environment",
            data,
        )

        _export_flip_distance(conn, ticker)
        _export_gamma_summary(conn, ticker)
        _export_gamma_0dte(conn, ticker)

    for ticker in VOL_SURFACE_TICKERS:
        logger.info(f"Exporting vol surface series for {ticker.upper()}")
        _export_skew_series(conn, ticker)
        _export_term_slope(conn, ticker)
        _export_vol_reference(conn, ticker)

    conn.close()
    logger.info("GEX series export complete")


if __name__ == "__main__":
    fetch_gex_series()
