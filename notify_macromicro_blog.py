# 定期執行：檢查 https://www.macromicro.me/blog 是否有新文章，若有則寄 Gmail 並推 LINE。
# 依賴 .env：MAIL_TOKEN、APP_PASSWORD、RECIPIENTS；CHANNEL_ACCESS_TOKEN、TO_QUEEN（LINE）；可選 DATA_DIR。
from __future__ import annotations

import io
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from loguru import logger

from gmail_smtp import send_html_email_from_env
from line_notify import send_line_notification

load_dotenv()

BLOG_URL = "https://www.macromicro.me/blog"
STATE_NAME = "macromicro_blog_seen.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HREF_RE = re.compile(
    r'href="((?:https://www\.macromicro\.me)?/blog/[^"#\s]+)"',
    re.IGNORECASE,
)


def _data_dir() -> Path:
    raw = (os.getenv("DATA_DIR") or "data").strip().strip('"')
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def _state_path() -> Path:
    return _data_dir() / STATE_NAME


def _is_article_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.netloc.lower() not in ("www.macromicro.me", "macromicro.me", ""):
        return False
    parts = [x for x in p.path.strip("/").split("/") if x]
    if len(parts) != 2 or parts[0].lower() != "blog":
        return False
    slug = parts[1]
    if slug.lower() in ("feed", "search", "page"):
        return False
    return True


def _normalize_href(href: str, base: str = BLOG_URL) -> str:
    href = href.strip()
    return urljoin(base, href)


def fetch_article_urls_ordered() -> list[str]:
    req = Request(BLOG_URL, headers={"User-Agent": USER_AGENT}, method="GET")
    with urlopen(req, timeout=60) as r:
        html = r.read().decode("utf-8", errors="replace")
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in HREF_RE.findall(html):
        u = _normalize_href(raw)
        if not _is_article_url(u):
            continue
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def _load_seen(path: Path) -> tuple[set[str], bool]:
    if not path.is_file():
        return set(), False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        urls = data.get("seen_urls") or []
        init = bool(data.get("initialized"))
        return set(str(x) for x in urls if x), init
    except Exception as e:
        logger.warning("讀取狀態檔失敗，將重新建立: {}", e)
        return set(), False


def _save_seen(path: Path, seen: set[str]) -> None:
    payload = {
        "initialized": True,
        "seen_urls": sorted(seen),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _format_line_message(new_urls: list[str]) -> str:
    """組合 LINE 文字；過長時截斷（push 訊息長度上限約 5000）。"""
    header = f"📰 MacroMicro 部落格新文章（{len(new_urls)} 篇）\n\n"
    body = "\n".join(f"• {u}" for u in new_urls)
    footer = f"\n\n{BLOG_URL}"
    text = header + body + footer
    max_len = 4800
    if len(text) <= max_len:
        return text
    keep = max_len - len(header) - len(footer) - 20
    trimmed = "\n".join(f"• {u}" for u in new_urls)[:keep].rstrip()
    return header + trimmed + "\n…（其餘請見信或部落格）" + footer


def run() -> None:
    path = _state_path()
    articles = fetch_article_urls_ordered()
    if not articles:
        logger.warning("未取得任何文章連結，請檢查頁面結構或網路")
        return

    seen, initialized = _load_seen(path)
    if not initialized:
        _save_seen(path, set(articles))
        logger.info(
            "首次執行：已記錄目前列表共 {} 篇，不寄信。之後有新網址即會通知。",
            len(articles),
        )
        return

    new_urls = [u for u in articles if u not in seen]
    if not new_urls:
        logger.debug("無新文章（目前列表 {} 篇）", len(articles))
        return

    seen.update(new_urls)
    _save_seen(path, seen)

    lines = "".join(f'<li><a href="{u}">{u}</a></li>' for u in new_urls)
    html = (
        f"<p>MacroMicro 部落格有新文章（{len(new_urls)} 篇）：</p><ul>{lines}</ul>"
        f'<p><a href="{BLOG_URL}">前往部落格</a></p>'
    )
    subject = f"[MacroMicro] 部落格新文章 {len(new_urls)} 篇"
    try:
        send_html_email_from_env(subject, html)
        logger.info("已寄出 Email 通知，新文章: {}", new_urls)
    except Exception as e:
        logger.error("部落格新文章 Email 通知失敗: {}", e)

    send_line_notification(_format_line_message(new_urls))


if __name__ == "__main__":
    if sys.platform == "win32":
        for _stream_name in ("stdout", "stderr"):
            _s = getattr(sys, _stream_name)
            if hasattr(_s, "buffer"):
                setattr(
                    sys,
                    _stream_name,
                    io.TextIOWrapper(_s.buffer, encoding="utf-8", errors="replace", line_buffering=True),
                )
    run()
