"""取得財政部 Marketable Borrowing Estimates 新聞稿中的季末 TGA 現金餘額假設。

用法：
    venv\\Scripts\\python.exe fetch.py [--start 2019-01-01] [--refresh]

流程：
1. 抓 Quarterly Refunding Financing Estimates by Calendar Year 索引頁，列出各年各季的 press release 連結。
2. 逐一抓取 press release（每次請求間隔 1.5 秒），原始 HTML 快取於 raw/（已存在則不重抓，--refresh 強制重抓）。
3. 從新聞稿文字抓出「During the <季> quarter, Treasury expects to borrow ... assuming an end-of-<月> cash balance of $X」
   兩個假設（本季末、下季末），產出 qra_tga_targets.csv（單位十億美元，來源口徑不變）。
"""
import argparse
import calendar
import csv
import html
import os
import re
import sys
import time
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "qra_tga_targets.csv")
BASE = "https://home.treasury.gov"
ARCHIVE = (BASE + "/policy-issues/financing-the-government/quarterly-refunding"
           "/quarterly-refunding-archives/quarterly-refunding-financing-estimates-by-calendar-year")
UA = "Mozilla/5.0 research-fetch"
SLEEP = 1.5
MONTHS = {calendar.month_name[i]: i for i in range(1, 13)}
MON = r"(January|February|March|April|May|June|July|August|September|October|November|December)"
DATE_LINE = re.compile(MON + r" (\d{1,2}), (\d{4})$")
SENT = re.compile(
    r"During the " + MON + r"\s*[–-]\s*" + MON + r" (\d{4}) quarter, Treasury expects to (?:borrow|pay down)"
    r".{0,300}?assuming an end-of-" + MON + r" cash balance of \$([\d.,]+) (billion|trillion)"
)


def get(url, cache_name, refresh):
    path = os.path.join(RAW, cache_name)
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", errors="replace")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    time.sleep(SLEEP)
    return body


def html_to_lines(page):
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    page = re.sub(r"<(br|/p|/li|/h\d|/div|/tr|/td)[^>]*>", "\n", page)
    page = re.sub(r"<[^>]+>", " ", page)
    page = html.unescape(page).replace("​", "")
    return [re.sub(r"\s+", " ", ln).strip() for ln in page.split("\n") if ln.strip()]


def archive_entries(page):
    """回傳 [(year, href, label)]，year 取自索引頁上方的年份標題。"""
    page = re.sub(r"<script.*?</script>|<style.*?</style>", "", page, flags=re.S)
    page = re.sub(
        r"<a [^>]*?href=\"?([^\" >]+)\"?[^>]*>(.*?)</a>",
        lambda m: " @@" + m.group(1) + "|" + re.sub(r"<[^>]+>", "", m.group(2)) + "@@ ",
        page, flags=re.S)
    year, out = None, []
    for ln in html_to_lines(page):
        if re.fullmatch(r"(19|20)\d\d", ln):
            year = int(ln)
            continue
        for href, label in re.findall(r"@@([^|]+)\|(.*?)@@", ln):
            if year is not None:
                out.append((year, href, label.strip()))
    return out


def release_date(lines):
    for i, ln in enumerate(lines):
        if ln == "Treasury Announces Marketable Borrowing Estimates" and i + 1 < len(lines):
            m = DATE_LINE.match(lines[i + 1])
            if m:
                return date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    for ln in lines:
        m = DATE_LINE.match(ln)
        if m:
            return date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2)))
    return None


def parse_release(page, url):
    """回傳 (announce_date, [(quarter_end_date, tga_bn, quarter_text, warn)], n_sentences)。"""
    lines = html_to_lines(page)
    ann = release_date(lines)
    text = " ".join(lines)
    rows, warns = [], []
    for m in SENT.finditer(text):
        q_start, q_end, q_year, end_mon, amt, unit = m.groups()
        year = int(q_year)
        end_month = MONTHS[end_mon]
        last_day = calendar.monthrange(year, end_month)[1]
        q_end_month = MONTHS[q_end]
        if end_month != q_end_month:
            warns.append(f"end-of-{end_mon} 與季度結束月 {q_end} 不一致")
        value = float(amt.replace(",", ""))
        if unit == "trillion":
            value *= 1000
        rows.append((date(year, end_month, last_day), value, f"{q_start}–{q_end} {year}", warns[:]))
        warns.clear()
    return ann, rows


def fmt(v):
    return str(int(v)) if float(v).is_integer() else str(round(v, 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2019-01-01", help="公告日下限（YYYY-MM-DD）")
    ap.add_argument("--refresh", action="store_true", help="忽略 raw/ 快取重新抓取")
    args = ap.parse_args()
    start = date.fromisoformat(args.start)
    os.makedirs(RAW, exist_ok=True)

    idx = get(ARCHIVE, "financing_estimates_by_year.html", args.refresh)
    entries = [(y, h, lbl) for (y, h, lbl) in archive_entries(idx)
               if "/news/press-releases/" in h and y >= start.year]
    # 去除重複連結
    seen, uniq = set(), []
    for e in entries:
        if e[1] not in seen:
            seen.add(e[1])
            uniq.append(e)
    print(f"索引中 {start.year} 年起的新聞稿連結：{len(uniq)} 筆")

    out_rows, failures, anomalies = [], [], []
    for y, href, lbl in uniq:
        url = BASE + href
        name = href.rstrip("/").split("/")[-1] + ".html"
        try:
            page = get(url, name, args.refresh)
        except Exception as ex:  # 網路或 HTTP 錯誤：記錄後繼續
            failures.append(f"{url} -> {ex}")
            print(f"FAIL 抓取 {url}: {ex}")
            continue
        ann, rows = parse_release(page, url)
        if ann is None:
            failures.append(f"{url} -> 解析不到公告日")
            print(f"FAIL 無公告日 {url}")
            continue
        if ann < start:
            continue
        if len(rows) != 2:
            anomalies.append(f"{ann} {url}：解析到 {len(rows)} 個假設（預期 2）")
        for q_end, val, qtxt, warns in rows:
            for w in warns:
                anomalies.append(f"{ann} {url}：{w}")
            out_rows.append((ann.isoformat(), q_end.isoformat(), fmt(val), url, qtxt))
        print(f"ok   {ann} {href} -> " + "; ".join(f"{r[1]}={r[2]}" for r in out_rows[-len(rows):]))

    out_rows.sort(key=lambda r: (r[0], r[1]))
    keys = [(r[0], r[1]) for r in out_rows]
    if len(keys) != len(set(keys)):
        failures.append("主鍵 (date, quarter_end) 重複")
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["date", "quarter_end", "tga_assumption_bn", "source_url"])
        for r in out_rows:
            w.writerow([r[0], r[1], r[2], r[3]])
    print(f"寫入 {OUT}：{len(out_rows)} 列")
    for a in anomalies:
        print("WARN " + a)
    for x in failures:
        print("ERR  " + x)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
