# -*- coding: utf-8 -*-
"""日本地產調研 WP 的機械驗收：python verify_wp.py <task-id>（在工作區根目錄執行，檢查 .agent-run/out/）。"""
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

OUT = Path(".agent-run/out")
SRC_COLS = ["category", "series", "source", "url", "frequency", "history_start", "latest_date",
            "access", "method", "tested", "notes"]
SPEC = {  # sources 列數、實測列數、≥10 列的 sample 數、其中最新日期 ≥ RECENT 的數量、必備檔、claims 數
    "jp-housing-starts": dict(rows=15, tested=8, samples=5, recent=3),
    "jp-prices-rates": dict(rows=15, tested=8, samples=5, recent=3, headings=["## 利率時間線"]),
    "jp-builders-cost": dict(rows=12, tested=6, samples=4, recent=2, files=["samples/policy_timeline.csv"]),
    "jp-claims-companies": dict(rows=8, tested=4, samples=6, recent=4, claims=15, headings=["## 公司數據"],
                                files=["samples/iida_quarterly.csv", "samples/openhouse_quarterly.csv"]),
    # 舊文件主題補缺口（2026-10-08 第二批）
    "jp-used-vs-new": dict(rows=12, tested=6, samples=4, recent=2, headings=["## 中古與新築對照"]),
    "jp-compliance-volume": dict(rows=12, tested=6, samples=4, recent=2, headings=["## 公司數據"],
                                 files=["samples/eri_quarterly.csv"]),
    "jp-valuation-funding": dict(rows=15, tested=7, samples=5, recent=3, headings=["## 估值利差"]),
    "jp-inheritance-tax": dict(rows=8, tested=3, samples=2, recent=1, claims=4, headings=["## 稅制結論"]),
    "jp-public-works": dict(rows=12, tested=6, samples=5, recent=3, headings=["## 公司數據"]),
}
HEADINGS = ["## 結論", "## 來源清單", "## 實測", "## 踩坑", "## 建議抓法"]
RECENT = "2025-06"
VERDICTS = {"成立", "部分成立", "不成立", "無法驗證"}
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?")

sys.stdout.reconfigure(encoding="utf-8")
errs = []


def fail(msg):
    errs.append(msg)


def read_rows(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def main(tid):
    spec = SPEC[tid]
    rep = OUT / "report.md"
    if not rep.exists() or rep.stat().st_size < 4000:
        fail("report.md 不存在或小於 4000 bytes")
    else:
        txt = rep.read_text("utf-8")
        for h in HEADINGS + spec.get("headings", []):
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
            tested = [r for r in rows if (r["tested"] or "").strip().lower() == "yes" and (r["latest_date"] or "").strip()]
            if len(rows) < spec["rows"]:
                fail(f"sources.csv 只有 {len(rows)} 列（需 ≥{spec['rows']}）")
            if len(tested) < spec["tested"]:
                fail(f"tested=yes 且有 latest_date 的只有 {len(tested)} 列（需 ≥{spec['tested']}）")
            bad = [r["series"] for r in rows if (r["access"] or "").strip() not in {"free", "registration", "paid"}]
            if bad:
                fail(f"access 只能是 free/registration/paid：{bad[:5]}")
    samples = sorted((OUT / "samples").glob("*.csv")) if (OUT / "samples").exists() else []
    good, recent, nodate = [], [], []
    for p in samples:
        rows = read_rows(p)
        if len(rows) - 1 < 10:
            continue
        good.append(p.name)
        if rows[0] and rows[0][0].strip().lstrip("﻿").lower() != "date":
            nodate.append(p.name)
            continue
        dates = [r[0].strip() for r in rows[1:] if r and DATE_RE.match(r[0].strip())]
        if dates and max(dates) >= RECENT:
            recent.append(p.name)
    if len(good) < spec["samples"]:
        fail(f"samples/ 裡 ≥10 列的 CSV 只有 {len(good)} 個（需 ≥{spec['samples']}）：{good}")
    if nodate:
        fail(f"samples 第一欄必須是 date：{nodate}")
    if len(recent) < spec["recent"]:
        fail(f"最新日期 ≥ {RECENT} 的 sample 只有 {len(recent)} 個（需 ≥{spec['recent']}）：{recent}")
    for f in spec.get("files", []):
        p = OUT / f
        if not p.exists() or len(read_rows(p)) - 1 < 10:
            fail(f"缺 {f} 或不足 10 列")
    if not list(OUT.glob("probe_*.py")):
        fail("缺 probe_*.py")
    if spec.get("claims"):
        cl = OUT / "claims.csv"
        if not cl.exists():
            fail("claims.csv 不存在")
        else:
            with cl.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            ids = {(r.get("claim_id") or "").strip() for r in rows}
            need = {str(i) for i in range(1, spec["claims"] + 1)}
            if not need <= ids:
                fail(f"claims.csv 缺 claim_id {sorted(need - ids, key=int)}")
            bad = [r.get("claim_id") for r in rows if (r.get("verdict") or "").strip() not in VERDICTS
                   or not (r.get("source_url") or "").strip()]
            if bad:
                fail(f"claims.csv verdict 不在 {VERDICTS} 或缺 source_url：{bad}")
            shallow = [r.get("claim_id") for r in rows
                       if any(len(urlparse(u.strip()).path.strip("/")) < 3
                              for u in (r.get("source_url") or "").split(";") if u.strip())]
            if shallow:
                fail(f"claims.csv source_url 只有網域首頁（要放能看到該數字的文章／文件網址）：{shallow}")
    if errs:
        print("FAIL\n- " + "\n- ".join(errs))
        sys.exit(1)
    print(f"PASS {tid}: samples={good} recent={recent}")


if __name__ == "__main__":
    main(sys.argv[1])
