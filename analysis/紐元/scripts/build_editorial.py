"""把 scripts/nzd_case_editorial.tpl.html 打包成單一檔 nzd_case_editorial.html。

模板用 <script src> 引用 lib/d3.min.js 與 data/chart_data.js（開發時可直接開模板看）；
這裡把兩者 inline，產出零依賴、雙擊即可開啟的編輯型單頁。資料更新後：
    build_chart_data.py → build_editorial.py
詳解版：build_editorial.py scripts/nzd_case_editorial_v2.tpl.html nzd_case_editorial_v2.html
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "scripts" / "nzd_case_editorial.tpl.html"
OUT = ROOT / "nzd_case_editorial.html"
INLINE = {
    '<script src="../lib/d3.min.js"></script>': ROOT / "lib" / "d3.min.js",
    '<script src="../data/chart_data.js"></script>': ROOT / "data" / "chart_data.js",
}


def main() -> None:
    tpl, out = (ROOT / sys.argv[1], ROOT / sys.argv[2]) if len(sys.argv) == 3 else (TPL, OUT)
    html = tpl.read_text(encoding="utf-8")
    for tag, path in INLINE.items():
        if tag not in html:
            raise SystemExit(f"模板找不到 {tag}")
        js = path.read_text(encoding="utf-8").replace("</script", "<\\/script")
        html = html.replace(tag, "<script>\n" + js + "\n</script>")
    out.write_text(html, encoding="utf-8")
    print(f"{out.name} {len(html.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
