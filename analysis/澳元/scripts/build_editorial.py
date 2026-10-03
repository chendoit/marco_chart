"""把 scripts/aud_case_editorial.tpl.html 打包成單一檔 aud_case_editorial.html（詳解版）。

模板用 <script src> 引用 lib/d3.min.js 與 data/chart_data.js（開發時可直接開模板看）；
這裡把兩者 inline，產出零依賴、雙擊即可開啟的編輯型單頁。原版 aud_case.html 不受影響。
資料更新後：fetch_data.py → build_chart_data.py → build_editorial.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "scripts" / "aud_case_editorial.tpl.html"
OUT = ROOT / "aud_case_editorial.html"
INLINE = {
    '<script src="../lib/d3.min.js"></script>': ROOT / "lib" / "d3.min.js",
    '<script src="../data/chart_data.js"></script>': ROOT / "data" / "chart_data.js",
}


def main() -> None:
    html = TPL.read_text(encoding="utf-8")
    for tag, path in INLINE.items():
        if tag not in html:
            raise SystemExit(f"模板找不到 {tag}")
        js = path.read_text(encoding="utf-8").replace("</script", r"<\/script")
        html = html.replace(tag, "<script>\n" + js + "\n</script>")
    OUT.write_text(html, encoding="utf-8")
    print(f"{OUT.name} {len(html.encode('utf-8')) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
