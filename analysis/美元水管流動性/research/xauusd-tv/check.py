"""自我檢查 xauusd_*_5m.csv（不依賴 verify.py）。

用法（在本任務資料夾執行）：
    PYTHONUTF8=1 C:/code/2025-12-05-MacroMicro-Data/venv/Scripts/python.exe -I check.py

檢查項目：
1. (date, time_et) 主鍵不重複
2. 依 (date, time_et) 升冪排序
3. high >= max(open, close)
4. low <= min(open, close)
5. 日期範圍涵蓋 2026-10-29 ～ 2026-11-06
"""
import csv
import glob
import sys
from pathlib import Path

TASK = Path(__file__).resolve().parent
NEED_FROM = "2026-10-29"
NEED_TO = "2026-11-06"
FIELDS = ["date", "time_et", "open", "high", "low", "close", "volume"]


def check_file(path: Path) -> list[tuple[str, bool, str]]:
    results = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = list(reader)

    results.append(("欄位", header == FIELDS, f"header={header}"))
    if not rows:
        results.append(("列數>0", False, "沒有資料列"))
        return results

    keys = [(r["date"], r["time_et"]) for r in rows]
    results.append(("主鍵不重複", len(keys) == len(set(keys)),
                    f"rows={len(keys)} unique={len(set(keys))}"))
    results.append(("升冪", keys == sorted(keys), "依 (date, time_et) 比較"))

    bad_high = [r for r in rows if float(r["high"]) < max(float(r["open"]), float(r["close"]))]
    results.append(("high>=max(open,close)", not bad_high,
                    f"違反列數={len(bad_high)}" + (f" 第一筆={bad_high[0]['date']} {bad_high[0]['time_et']}" if bad_high else "")))
    bad_low = [r for r in rows if float(r["low"]) > min(float(r["open"]), float(r["close"]))]
    results.append(("low<=min(open,close)", not bad_low,
                    f"違反列數={len(bad_low)}" + (f" 第一筆={bad_low[0]['date']} {bad_low[0]['time_et']}" if bad_low else "")))

    first_d, last_d = rows[0]["date"], rows[-1]["date"]
    covers = first_d <= NEED_FROM and last_d >= NEED_TO
    results.append((f"涵蓋 {NEED_FROM}～{NEED_TO}", covers, f"起={first_d} 訖={last_d}"))
    return results


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # -I 會忽略 PYTHONUTF8，這裡強制 UTF-8 輸出
    files = sorted(glob.glob(str(TASK / "xauusd_*_5m.csv")))
    if not files:
        print("FAIL 找不到 xauusd_*_5m.csv")
        return 1
    all_ok = True
    for fp in files:
        p = Path(fp)
        print(f"== {p.name}")
        for name, ok, detail in check_file(p):
            print(f"  {'PASS' if ok else 'FAIL'} {name} | {detail}")
            all_ok &= ok
    print("RESULT", "ALL PASS" if all_ok else "SOME FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
