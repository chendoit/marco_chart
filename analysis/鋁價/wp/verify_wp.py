# -*- coding: utf-8 -*-
"""鋁業調研 WP 的機械驗收：python verify_wp.py <task-id>（在工作區根目錄執行，檢查 .agent-run/out/）。"""
import csv
import sys
from pathlib import Path
from urllib.parse import urlparse

OUT = Path(".agent-run/out")
SRC_COLS = ["category", "series", "source", "url", "frequency", "history_start", "latest_date",
            "access", "method", "tested", "notes"]
SPEC = {  # min sources rows, min tested rows, min sample csv, need probe script
    "al-prices-inventory": dict(rows=15, tested=8, samples=5, probe=True),
    "al-premium-policy": dict(rows=15, tested=6, samples=4, probe=True),
    "al-supply-chain": dict(rows=15, tested=6, samples=4, probe=True),
    "al-claims-companies": dict(rows=6, tested=3, samples=2, probe=True),
}
HEADINGS = ["## 結論", "## 來源清單", "## 踩坑"]
VERDICTS = {"成立", "部分成立", "不成立", "無法驗證"}

sys.stdout.reconfigure(encoding="utf-8")
errs = []


def fail(msg):
    errs.append(msg)


def main(tid):
    spec = SPEC[tid]
    rep = OUT / "report.md"
    if not rep.exists() or rep.stat().st_size < 4000:
        fail(f"report.md 不存在或小於 4000 bytes")
    else:
        txt = rep.read_text("utf-8")
        for h in HEADINGS:
            if h not in txt:
                fail(f"report.md 缺標題 {h}")
    src = OUT / "sources.csv"
    if not src.exists():
        fail("sources.csv 不存在")
    else:
        with src.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        miss = [c for c in SRC_COLS if rows and c not in rows[0]]
        if not rows or miss:
            fail(f"sources.csv 空或缺欄位 {miss}")
        else:
            tested = [r for r in rows if r["tested"].strip().lower() == "yes" and r["latest_date"].strip()]
            if len(rows) < spec["rows"]:
                fail(f"sources.csv 只有 {len(rows)} 列（需 ≥{spec['rows']}）")
            if len(tested) < spec["tested"]:
                fail(f"tested=yes 且有 latest_date 的只有 {len(tested)} 列（需 ≥{spec['tested']}）")
            bad = [r["series"] for r in rows if r["access"].strip() not in {"free", "registration", "paid"}]
            if bad:
                fail(f"access 只能是 free/registration/paid：{bad[:5]}")
    samples = sorted((OUT / "samples").glob("*.csv")) if (OUT / "samples").exists() else []
    good = []
    for p in samples:
        with p.open(encoding="utf-8-sig", newline="") as f:
            n = sum(1 for _ in csv.reader(f)) - 1
        if n >= 10:
            good.append(p.name)
    if len(good) < spec["samples"]:
        fail(f"samples/ 裡 ≥10 列的 CSV 只有 {len(good)} 個（需 ≥{spec['samples']}）：{good}")
    if spec["probe"] and not list(OUT.glob("probe_*.py")):
        fail("缺 probe_*.py")
    if tid == "al-claims-companies":
        cl = OUT / "claims.csv"
        if not cl.exists():
            fail("claims.csv 不存在")
        else:
            with cl.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            ids = {r.get("claim_id", "").strip() for r in rows}
            need = {str(i) for i in range(1, 11)}
            if not need <= ids:
                fail(f"claims.csv 缺 claim_id {sorted(need - ids, key=int)}")
            bad = [r.get("claim_id") for r in rows if r.get("verdict", "").strip() not in VERDICTS
                   or not r.get("source_url", "").strip()]
            if bad:
                fail(f"claims.csv verdict 不在 {VERDICTS} 或缺 source_url：{bad}")
            shallow = [r.get("claim_id") for r in rows
                       if any(len(urlparse(u.strip()).path.strip("/")) < 3 for u in r.get("source_url", "").split(";"))]
            if shallow:
                fail(f"claims.csv source_url 只有網域首頁（要放能看到該數字的文章／文件網址）：{shallow}")
    if errs:
        print("FAIL\n- " + "\n- ".join(errs))
        sys.exit(1)
    print(f"PASS {tid}: samples={good}")


if __name__ == "__main__":
    main(sys.argv[1])
