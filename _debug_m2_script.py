"""暫時除錯：檢查 MacroMicro series 頁面 script 結構"""
import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.sync_api import sync_playwright
from macromicro_login import ensure_macromicro_session

URL = "https://www.macromicro.me/series/4249/bitcoin-usd"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    page = browser.new_page()
    page.add_init_script(path="stealth.min.js")
    ensure_macromicro_session(page, "_debug_m2_script.py")
    page.goto(URL)
    page.wait_for_timeout(5000)
    html = page.content()
    browser.close()

script_regex = r"<script[^>]*>(.*?)</script>"
matches = re.findall(script_regex, html, re.DOTALL)
print(f"Total script tags: {len(matches)}")

for i, match in enumerate(matches):
    if "isViewable" in match:
        print(f"\n=== Script #{i} with isViewable (len={len(match)}) ===")
        # show context around atob / JSON.parse
        for pat in ["atob", "JSON.parse", "isViewable", "setTimeout"]:
            idx = match.find(pat)
            if idx >= 0:
                start = max(0, idx - 80)
                end = min(len(match), idx + 200)
                print(f"\n--- context for '{pat}' ---")
                print(repr(match[start:end]))

        old_regex = r'JSON\.parse\(atob\(\"(.*?)\"\)\)}]}\)}setTimeout'
        m = re.search(old_regex, match)
        print(f"\nOld regex match: {m is not None}")
        if m:
            print(f"  captured len: {len(m.group(1))}, first50: {m.group(1)[:50]!r}")

        # try broader patterns
        patterns = [
            r'JSON\.parse\(atob\("([^"]+)"\)\)',
            r'atob\("([A-Za-z0-9+/=]{100,})"\)',
            r'JSON\.parse\(atob\(\'([^\']+)\'\)\)',
        ]
        for pat in patterns:
            ms = re.findall(pat, match)
            print(f"Pattern {pat!r}: {len(ms)} matches")
            for j, s in enumerate(ms[:3]):
                print(f"  [{j}] len={len(s)}, first50={s[:50]!r}")
