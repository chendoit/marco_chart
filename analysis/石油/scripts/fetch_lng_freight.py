# -*- coding: utf-8 -*-
"""石油／歐洲天然氣學習案例：LNG 現貨運費（USD/day），一次性抓取（不進 ETL，不寫入專案 data/）

輸出到 analysis/石油/data/：
- lng_freight.csv          index = date（%Y-%m-%d），欄位：
    blng2_174_usd_day      Baltic Exchange BLNG2-174（US Gulf → Continent 來回航次，174k cbm 2-stroke），USD/day
                           2023-12-15 起才有正式 174 指數（之前為試編，捨棄）
    blng2_160_usd_day      Baltic Exchange BLNG2g（同航線，160k cbm TFDE），USD/day；2022-11 起
    spark30s_usd_day       Spark30S Atlantic（US Gulf/Sabine Pass ↔ NW Europe/Gate 來回，174k 2-stroke），USD/day
    spark25s_usd_day       Spark25S Pacific（Australia/Gladstone ↔ NE Asia 來回，174k 2-stroke），USD/day
                           ※ Spark 兩欄只有在 .env 有 SPARK_CLIENT_ID / SPARK_CLIENT_SECRET 時才會出現
- lng_freight_audit.csv    每一個 Baltic 數值的出處（報告日期、URL、原文句子），方便人工核對
- baltic_gas_reports.json  Baltic 週報 LNG 段落原文快取（重跑時只抓新的週報）

【注意】名稱常被搞反：Spark30S = Atlantic（美灣→西北歐），Spark25S = Pacific（澳洲→東北亞）。
ICE 上市的是以此結算的期貨（Spark30S Atlantic / Spark25S Pacific LNG Freight Futures），
這裡抓的是 Spark 的現貨評估值本身，不是期貨價。

來源與取得方式
1) Baltic Exchange 公開週報「Weekly Market Roundups → Gas」（免登入）
   https://www.balticexchange.com/en/data-services/WeeklyRoundup/Gas/News/{年}/gas-report-week-{週}.html
   - 每週五一篇，LNG 段落以「敘述文字」寫出 BLNG1/2/3 當週收盤（週五）報價；本腳本用規則式解析句子
     取 BLNG2 的「水準值」（排除 rise/fall/by $X 這類變動量），174k 與 160k 分開。
   - 官方時間序列（每日 BLNG）要付費訂閱 Baltic 資料；這裡只是週報文字裡引用的週五值 → 週頻、會有缺值。
   - 網站有 Akamai 擋一般 requests，需用 curl_cffi（impersonate="chrome"）；robots.txt 只要求 Crawl-delay: 1，
     本腳本每次請求間隔 1.2 秒。個人研究用；Baltic 指數屬其智慧財產，勿再散佈。
   - 最早可抓到 2022-11-18（再往前的 URL 不存在）。
2) Spark Commodities API（需帳號）https://api.sparkcommodities.com
   - 免費試用帳號：https://app.sparkcommodities.com/signup/ 註冊 → 登入後到
     https://app.sparkcommodities.com/data-integrations/api 建立 OAuth2 client，下載 client_credentials.csv，
     把 clientId / clientSecret 寫進 repo 根目錄 .env：
         SPARK_CLIENT_ID=xxxx
         SPARK_CLIENT_SECRET=yyyy
   - OAuth：POST /oauth/token/（grantType=clientCredentials, scopes=read:lng-freight-prices），
     再 GET /v1.0/contracts/{spark30s|spark25s}/price-releases/?limit=&offset=&vessel-type=174-2stroke
     （參考官方範例 github.com/spark-commodities/api-code-samples）
   - 文件寫「非登入可拿 N-4 舊資料」，但 2026-09-30 實測未帶 token 一律 401 → 必須有帳號。
   - 試用 / 非 Premium 帳號的歷史長度有限制（Premium 才有完整歷史）；拿到多少就存多少。
   - 沒有帳號時此段自動略過，不會失敗。

caveats（Baltic 文字解析）
- 數值是「週報文字裡寫的週五收盤」，非官方 time series；少數週文字只寫變動量、沒寫水準 → NaN。
- 原文偶有筆誤（例如把 Houston-Isle of Grain 寫成 BLNG1g、$93,00）；同一週同一欄解析出兩個不同值時
  視為模稜兩可 → NaN，並在 audit 標 ambiguous。
- 2023-12-15 以前只有 160k 指數（BLNG2g）；之後 174/160 並行；2026 起週報多半只寫 174k。
  句子沒寫船型時：2023-12-15 以前當 160；之後若整篇 LNG 段落都沒提到 160/TFDE 才當 174，否則不取。
- 2025 年初 BLNG2 報價一度跌到個位數千元甚至接近 0（Sabine–UK Continent），屬實際行情，不是解析錯誤。
- 使用前建議抽查 lng_freight_audit.csv；本腳本 2026-09-30 首次執行時已人工抽查。
"""
import base64
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)
REPO_ROOT = Path(__file__).resolve().parents[3]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CSV_OUT = OUT / "lng_freight.csv"
AUDIT_OUT = OUT / "lng_freight_audit.csv"
CACHE = OUT / "baltic_gas_reports.json"

# ---------------------------------------------------------------- Baltic 週報抓取
BALTIC = "https://www.balticexchange.com"
REPORT_PATH = "/en/data-services/WeeklyRoundup/Gas/News/{y}/gas-report-week-{w}.html"
FIRST_YEAR = 2022           # 2022-11 以前沒有這個 URL 格式的週報
BLNG174_LAUNCH = pd.Timestamp("2023-12-15")
PAUSE = 1.2


def _session():
    from curl_cffi import requests as cr
    return cr.Session(impersonate="chrome")


def _get(sess, path):
    time.sleep(PAUSE)
    try:
        r = sess.get(BALTIC + path, timeout=40)
    except Exception as e:  # noqa: BLE001
        print(f"  [warn] {path}: {e}")
        return None
    return r.text if r.status_code == 200 else None


def _parse_report(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    txt = soup.get_text("\n")
    m = re.search(r"Back to All\s*\n\s*(\d{1,2} \w+ \d{4})", txt)
    d = None
    if m:
        d = pd.to_datetime(m.group(1).replace("Sept", "Sep"), format="%d %b %Y").strftime("%Y-%m-%d")
    # LNG 段落：<p>LNG</p> 標題之後、<p>LPG</p> 標題之前
    paras, on = [], False
    for p in soup.select("p"):
        t = p.get_text(" ", strip=True)
        if t.upper() == "LNG":
            on = True
            continue
        if t.upper() in ("LPG", "VLGC") and on:
            break
        if on and t:
            paras.append(t)
    if not paras:  # 少數早期週報沒有 LNG 小標
        paras = [p.get_text(" ", strip=True) for p in soup.select("p")
                 if re.search(r"B?LNG\s?\d", p.get_text())]
    pv = soup.select_one("#prev-button")
    prev = pv.get("href") if pv is not None and pv.get("href") else None
    return {"date": d, "lng_text": paras, "prev": prev}


def crawl_baltic():
    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    sess = _session()
    today = date.today()
    n_new = 0
    for y in range(today.year, FIRST_YEAR - 1, -1):
        top = today.isocalendar()[1] + 1 if y == today.year else 53
        # 找該年最新一篇（往回試週數）
        start = None
        for w in range(top, 0, -1):
            path = REPORT_PATH.format(y=y, w=w)
            if path in cache:
                start = path
                break
            html = _get(sess, path)
            if html:
                cache[path] = _parse_report(html)
                n_new += 1
                start = path
                break
        if not start:
            print(f"  {y}: 找不到週報")
            continue
        # 沿 Previous 連結往回走；已在快取的直接用快取的 prev
        path = start
        while path:
            rec = cache.get(path)
            if rec is None:
                html = _get(sess, path)
                if not html:
                    print(f"  [warn] 抓不到 {path}")
                    break
                rec = cache[path] = _parse_report(html)
                n_new += 1
                print(f"  {rec['date']}  {path.rsplit('/', 2)[-2]}/{path.rsplit('/', 1)[-1]}")
            nxt = rec.get("prev")
            if not nxt or f"/{y}/" not in nxt:
                break
            path = nxt
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Baltic 週報：快取 {len(cache)} 篇（本次新抓 {n_new} 篇）")
    return cache


# ---------------------------------------------------------------- Baltic 文字解析
R = r"(?:[-–/]|\s+to\s+(?:the\s+)?)"
ROUTE_PATS = [
    (1, rf"\bB?LN?G\s?1(?!\d)|\bAus(?:tralia)?\s?{R}\s?(?:Japan|Tokyo)|\bGladstone"),
    (2, rf"\bB?LN?G\s?2(?!\d)|\bUS\s?Gulf\s?{R}\s?(?:UK|Cont)|\bUSG?\s?{R}\s?(?:UK|Cont)"
        rf"|\bHouston\s?{R}\s?(?:UK|Cont|CONT|Isle|Grain)|\bSabine\s?{R}\s?(?:UK|Isle)"
        rf"|\bCorpus Christi/Isle|trans-Atlantic"),
    (3, rf"\bB?LN?G\s?3(?!\d)|\b(?:US|USG|US\s?Gulf|Houston)\s?{R}\s?(?:Japan|Tokyo|East)"
        rf"|\bHouston\s?Japan|trans-Panama"),
]
SIZE_PATS = [
    (174, r"174|2.?[Ss]troke|two.stroke|_74g|\b170\s?cbm"),
    (160, r"160|TFDE|TDFE|TDFDE|\b16cbm|\b60cbm|\bB?LN?G\s?[123][gG]\b"),
]
AMT = re.compile(r"(?<![\d,])\$\s?(\d{1,3}(?:,\d{3})+|\d{3,7})(?:\.\d+)?(?:\s?k\b)?(?!\s?[-–]\s?\$?\d)(?!%)")
LEVEL_PRE = re.compile(
    r"(?:\bto|\bat|\bpublish(?:ed|ing)?|\bclos(?:e|ed|ing)|\bfinish(?:ed|ing)?|\bsettl(?:e|ed|ing)(?:\s+on)?"
    r"|\bend(?:ed|ing)?|\bprinting|\bpriced|\bassessed|\breaching|\bremain(?:ed|s)?|\bheld|\bholding"
    r"|\bsteady|\bflat|\bunchanged|\bstands?|\bbringing(?:\s+the\s+index)?(?:\s+to)?)"
    r"\s*(?:a\s+|the\s+)?(?:(?:new\s+|final\s+|closing\s+)?(?:close|closing price|finish|publication|level|peak|low"
    r"|high|round voyage (?:rate|number)|rate|price)\s+(?:of\s+)?)?(?:(?:just|only)\s+)?"
    r"(?:around|about|approximately|nearly|almost)?\s*$", re.I)
LEVEL_PRE2 = re.compile(r"(?:close|closing price|finish|publication|level|round voyage (?:rate|number)|rate)\s+of\s*$", re.I)
CHANGE_POST = re.compile(r"^\s*(?:/day|per day|PD|/d)?\s*(?:,\s*)?(?:delta|differential|premium|lower|higher|up\b|down\b"
                         r"|off\b|gained|lost|w-o-w|week.on.week|more|less|below|above|shy|increase|decrease"
                         r"|decline|drop|gain|rise|fall|loss|compared)", re.I)
PERIOD_SENT = re.compile(r"six.month|6.month|one.year|1.year|three.year|3.year|12 months|time.?charter|\bTC\b"
                         r"|\bterm\b|boil off", re.I)


def _mask_amounts(s):
    return AMT.sub(lambda m: "$" + "#" * (len(m.group(0)) - 1), s)


def _mentions(s, pats):
    """回傳 [(start, end, key)]，同 key 且距離很近的合併成一個 mention。"""
    masked = _mask_amounts(s)
    out = []
    for key, pat in pats:
        for m in re.finditer(pat, masked):
            out.append((m.start(), m.end(), key))
    out.sort()
    merged = []
    for st, en, k in out:
        if merged and merged[-1][2] == k and st - merged[-1][1] <= 15:
            merged[-1] = (merged[-1][0], max(en, merged[-1][1]), k)
        elif merged and st < merged[-1][1]:
            continue
        else:
            merged.append((st, en, k))
    return merged


def _to_num(txt):
    t = txt.replace("$", "").replace(" ", "")
    k = t.lower().endswith("k")
    t = t.rstrip("kK").split(".")[0].replace(",", "")
    return float(t) * (1000 if k else 1)


def _amounts(s):
    """每個金額：(start, end, value, kind) kind ∈ level / change / unknown。"""
    res = []
    for m in AMT.finditer(s):
        pre = s[max(0, m.start() - 70):m.start()]
        post = s[m.end():m.end() + 40]
        val = _to_num(m.group(0).replace("$", ""))
        if LEVEL_PRE.search(pre) or LEVEL_PRE2.search(pre):
            kind = "level"
        elif CHANGE_POST.search(post):
            kind = "change"
        elif res and res[-1][3] == "level" and re.fullmatch(r"\s*(?:/day|per day)?\s*,?\s*(?:and|,)\s*", s[res[-1][1]:m.start()]):
            kind = "level"
        elif re.search(r"\b(?:by|of|lost|shed|shaving|gained|gaining|added|adding|rose|fell|dropped|dropping|climbed"
                       r"|climbing|jumped|surged|surging|soared|soaring|slipped|slipping|edged|eased|easing|declined"
                       r"|declining|increased|increasing|decreased|falling|rising|losing|moving|moved|up|down|off"
                       r"|another|over|a|an|around|about|between|from)\s*$", pre, re.I):
            kind = "change"
        else:
            kind = "unknown"
        res.append((m.start(), m.end(), val, kind))
    return res


def _key_at(pos, end, mentions, s):
    """金額後緊接著的 mention 優先（如「$54,062 BLNG2g」「$X on the 174cbm」），否則取前面最近的。"""
    for st, en, k in mentions:
        if st >= end and re.fullmatch(r"\s*(?:/day|per day|PD)?\s*,?\s*(?:(?:for|on)\s+)?(?:the\s+)?(?:modern\s+|larger\s+"
                                      r"|smaller\s+)?", s[end:st]):
            return k
        if st >= end:
            break
    before = [k for st, en, k in mentions if en <= pos]
    return before[-1] if before else None


def _respectively(s, amts, rts, szs):
    """處理「$A and $B for X and Y respectively」。回傳 {amount_index: ('route'|'size', key)}。"""
    out = {}
    for m in re.finditer(r"respectively", s):
        grp = [i for i, a in enumerate(amts) if a[3] == "level" and a[1] <= m.start()]
        if len(grp) < 2:
            continue
        # 取緊鄰 respectively 之前、以 and / , 相連的一組
        chain = [grp[-1]]
        for i in reversed(grp[:-1]):
            if re.fullmatch(r"\s*(?:/day|per day)?\s*,?\s*(?:and\s+)?", s[amts[i][1]:amts[chain[0]][0]]):
                chain.insert(0, i)
            else:
                break
        k = len(chain)
        if k < 2:
            continue
        g0, g1 = amts[chain[0]][0], amts[chain[-1]][1]
        tail_end = len(s)
        nxt = [a[0] for a in amts if a[0] > m.end()]
        if nxt:
            tail_end = nxt[0]
        cands = []
        for dim, ms in (("size", szs), ("route", rts)):
            tail = [x[2] for x in ms if g1 <= x[0] < tail_end]
            cands.append((dim, tail))
        for dim, ms in (("size", szs), ("route", rts)):
            pre = [x[2] for x in ms if x[1] <= g0]
            cands.append((dim, pre[-k:] if len(pre) >= k else []))
        for dim, keys in cands:
            if len(keys) == k and len(set(keys)) == k:
                for i, key in zip(chain, keys):
                    out[i] = (dim, key)
                break
    return out


def _slash_pairs(s, rts):
    """「BLNG2/BLNG2-174 from $42,600/$56,400 to $39,500/$52,000」→ 最後一組 (160, 174)。"""
    out = []
    for m in re.finditer(r"\bB?LNG\s?([123])/B?LNG\s?\1-174", s):
        seg = s[m.end():]
        nxt = re.search(r"\bB?LNG\s?[123]/", seg)
        seg = seg[:nxt.start()] if nxt else seg
        pairs = re.findall(r"\$([\d,]+)(?:/day)?/\$([\d,]+)", seg)
        if pairs:
            a, b = pairs[-1]
            out.append((int(m.group(1)), 160, float(a.replace(",", ""))))
            out.append((int(m.group(1)), 174, float(b.replace(",", ""))))
    return out


def parse_report(rec):
    """回傳 [(route, size, value, sentence)]；size None = 句子沒寫船型。"""
    d = pd.Timestamp(rec["date"])
    text = " ".join(rec["lng_text"])
    whole_mentions_160 = bool(re.search(r"160|TFDE|TDFE", _mask_amounts(text)))
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    found = []
    ctx_route = None
    for s in sents:
        rts = _mentions(s, ROUTE_PATS)
        szs = _mentions(s, SIZE_PATS)
        if PERIOD_SENT.search(s) or re.match(r"\s*Period", s):
            if rts:
                ctx_route = rts[-1][2]
            continue
        sp = _slash_pairs(s, rts)
        if sp:
            found += [(r_, z, v, s) for r_, z, v in sp]
            ctx_route = rts[-1][2] if rts else ctx_route
            continue
        amts = _amounts(s)
        resp = _respectively(s, amts, rts, szs)
        for i, (st, en, val, kind) in enumerate(amts):
            if kind != "level":
                continue
            route = _key_at(st, en, rts, s)
            size = _key_at(st, en, szs, s)
            if i in resp:
                dim, key = resp[i]
                if dim == "route":
                    route = key
                else:
                    size = key
            if route is None:
                route = ctx_route
            # 同一句中「前面最近的 mention」如果是另一條航線且在上一個金額之前，仍以最近為準
            if size is None:
                if d < BLNG174_LAUNCH:
                    size = 160
                elif not whole_mentions_160:
                    size = 174
            found.append((route, size, val, s))
        if rts:
            ctx_route = rts[-1][2]
    return found


def extract_blng2(cache):
    rows, audit = [], []
    for path, rec in cache.items():
        if not rec.get("date"):
            continue
        d = pd.Timestamp(rec["date"])
        found = parse_report(rec)
        for size, col in ((174, "blng2_174_usd_day"), (160, "blng2_160_usd_day")):
            hits = [(v, s) for r_, z, v, s in found if r_ == 2 and z == size]
            if size == 174 and d < BLNG174_LAUNCH:
                hits = []   # 174 指數 2023-12-15 才正式發布，之前為試編
            # 段落裡「從 A 漲到 B」會在不同句子重複提到同一收盤值 → 以值去重
            vals = list(dict.fromkeys(v for v, _ in hits))
            if len(vals) == 1:
                rows.append((rec["date"], col, vals[0]))
                audit.append((rec["date"], col, vals[0], "ok", BALTIC + path, hits[0][1]))
            elif len(vals) > 1:
                audit.append((rec["date"], col, None, "ambiguous:" + "/".join(f"{v:,.0f}" for v in vals),
                              BALTIC + path, " || ".join(s for _, s in hits)))
    if not rows:
        return pd.DataFrame(), pd.DataFrame()
    df = (pd.DataFrame(rows, columns=["date", "col", "val"])
          .pivot_table(index="date", columns="col", values="val", aggfunc="first"))
    df.index = pd.to_datetime(df.index)
    aud = pd.DataFrame(audit, columns=["date", "series", "value", "status", "url", "sentence"]).sort_values(["date", "series"])
    return df.sort_index(), aud


# ---------------------------------------------------------------- Spark API（需帳號）
SPARK_API = "https://api.sparkcommodities.com"
SPARK_TICKERS = {"spark30s": "spark30s_usd_day", "spark25s": "spark25s_usd_day"}


def fetch_spark():
    load_dotenv(REPO_ROOT / ".env")
    cid = os.getenv("SPARK_CLIENT_ID", "").strip()
    sec = os.getenv("SPARK_CLIENT_SECRET", "").strip()
    if not cid or not sec:
        print("Spark：.env 沒有 SPARK_CLIENT_ID / SPARK_CLIENT_SECRET → 略過 Spark30S/Spark25S"
              "（免費試用帳號註冊方式見本檔 docstring）")
        return pd.DataFrame()
    # 依官方範例：Authorization = base64(client_id:client_secret)
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    r = requests.post(f"{SPARK_API}/oauth/token/", timeout=30,
                      headers={"Authorization": auth, "Accept": "application/json",
                               "Content-Type": "application/json"},
                      json={"grantType": "clientCredentials", "scopes": "read:lng-freight-prices"})
    if r.status_code not in (200, 201):
        print(f"Spark：取 token 失敗 HTTP {r.status_code} {r.text[:200]} → 略過")
        return pd.DataFrame()
    hdr = {"Authorization": f"Bearer {r.json()['accessToken']}", "Accept": "application/json"}
    series = {}
    for ticker, col in SPARK_TICKERS.items():
        vals, offset, limit = {}, 0, 200
        while True:
            u = (f"{SPARK_API}/v1.0/contracts/{ticker}/price-releases/"
                 f"?limit={limit}&offset={offset}&vessel-type=174-2stroke")
            x = requests.get(u, headers=hdr, timeout=60)
            if x.status_code != 200:
                print(f"  Spark {ticker}: HTTP {x.status_code} {x.text[:200]}（offset={offset}）")
                break
            data = x.json().get("data", [])
            for rel in data:
                try:
                    dp = rel["data"][0]["dataPoints"][0]
                    vals[rel["releaseDate"][:10]] = float(dp["derivedPrices"]["usdPerDay"]["spark"])
                except (KeyError, IndexError, TypeError, ValueError):
                    continue
            if len(data) < limit:
                break
            offset += limit
            time.sleep(0.5)
        if vals:
            s = pd.Series(vals, name=col)
            s.index = pd.to_datetime(s.index)
            series[col] = s.sort_index()
    return pd.DataFrame(series)


# ---------------------------------------------------------------- main
def main():
    print("== Baltic Exchange Gas weekly report（BLNG2）")
    cache = crawl_baltic()
    blng, audit = extract_blng2(cache)
    print("== Spark Commodities API")
    spark = fetch_spark()
    parts = [p for p in (blng, spark) if not p.empty]
    if not parts:
        print("沒有任何資料")
        sys.exit(1)
    df = pd.concat(parts, axis=1).sort_index()
    df.index.name = "date"
    df.to_csv(CSV_OUT, date_format="%Y-%m-%d", float_format="%.0f")
    if not audit.empty:
        audit.to_csv(AUDIT_OUT, index=False, encoding="utf-8-sig")
        n_amb = audit["status"].str.startswith("ambiguous").sum()
        print(f"audit：{len(audit)} 筆（ambiguous {n_amb} 筆）→ {AUDIT_OUT.name}")
    for c in df.columns:
        s = df[c].dropna()
        if len(s):
            print(f"{c} {len(s)} rows {s.index[0]:%Y-%m-%d} → {s.index[-1]:%Y-%m-%d}  last={s.iloc[-1]:,.0f}")
    print(f"→ {CSV_OUT}")


if __name__ == "__main__":
    main()
