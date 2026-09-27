# -*- coding: utf-8 -*-
"""One-off patch: switch yield curve chart to MacroMicro series."""
import pathlib

routes = pathlib.Path("flask_highcharts/app/routes")
target = None
for p in routes.glob("McElligott*.py"):
    text = p.read_text(encoding="utf-8")
    if '"title": "美國公��殖利率曲線（含 2Y）"' in text and "cboe_IRX" in text:
        target = p
        break

if not target:
    raise SystemExit("target file not found")

old = '''        {
            "title": "美國公��殖利率曲線（含 2Y）",
            "ids": [356, "cboe_IRX", "fed_DGS2", "cboe_FVX", "cboe_TNX", "cboe_TYX"],
            "axis": [0, 0, 0, 0, 0, 0],
            "summary":
                "Fed Fund Rate / 13W（IRX）/ 2Y（DGS2, FRED）/ 5Y（FVX）/ 10Y（TNX）/ 30Y（TYX）完整殖利率曲線。"
                "CBOE CDN 無 2Y 指數，故 2Y 改用 FRED DGS2。<br>"
                "Fed Fund Rate 是��準會的政策利率下限，殖利率曲線的����——"
                "所有天期殖利率相對於 FFR 的利差反映市場�前景���。<br>"
                "McElligott 的�框架：2Y 對 Fed 路��重新定��最敏感（CTA ��發��追�� 2Y）；"
                "10Y 是成長/通膨的混合晴雨表和跨���中��；30Y 受 Term Premium 和���主��。<br>"
                "曲線形��的��化是 CTA ��券部位翻��的��發器——"
                "2024/08 期間 CTA ��巨��做空�做多（+$289B 名義金��），"
                "伴��著 'Hard Landing' ��事的成型。",
        },'''

new = '''        {
            "title": "�殖利率曲線（m平方）",
            "ids": [356, 5547, 5549, 363, 354, 5551, 5551],
            "axis": [0, 0, 0, 0, 0, 0, 0],
            "summary":
                "Fed Fund Rate（356）+ m平方 美�殖利率：1M（5547）/ 1Y（5549）/ 2Y（363）/ 10Y（354）/ 20Y（5551）/ 30Y（5551）。"
                "資料來源統一為� CBOE/FRED 混用版本相比更易對��更新�奏。<br>"
                "Fed Fund Rate 是政策�；短端反映流動性��近端�，長端反映成長、�期�� Term Premium。<br>"
                "McElligott 框架：2Y 對 Fed 路��重新定��敏感；10Y �中��；"
                "曲線�化常伴�� CTA ��券部位大規模翻��。",
        },'''

text = target.read_text(encoding="utf-8")
if old not in text:
    raise SystemExit("old block not found — file may differ")
target.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched:", target)
