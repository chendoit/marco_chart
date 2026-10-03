# -*- coding: utf-8 -*-
"""冬季能源框架：衍生指標（一次性計算，不進 ETL）
輸入：analysis/石油/data/prices_daily.csv（fetch_prices.py 產出）
      analysis/石油/data/lng_freight.csv（fetch_lng_freight.py，若存在；需 spark30s_usd_mmbtu 欄）
輸出：analysis/石油/data/derived_daily.csv

欄位與公式（單位）：
- ttf_usd_mmbtu     = TTF(EUR/MWh) × EURUSD / 3.412                        ($/MMBtu；1 MWh = 3.412 MMBtu)
- ttf_hh_spread     = ttf_usd_mmbtu − HH                                    ($/MMBtu；HH 用 NG=F，缺值補 DHHNGSP)
- us_lng_fob        = 1.15 × HH + LIQ_FEE                                   ($/MMBtu；美灣 FOB 成本慣用公式)
- freight_usd_mmbtu = Spark30S Atlantic $/MMBtu（USG→NWE；lng_freight.csv 有此欄時。注意原文的 Spark25 實為 Pacific），否則 FREIGHT_ASSUMED 固定假設
- lng_arb_nwe       = ttf_usd_mmbtu − us_lng_fob − freight_usd_mmbtu        ($/MMBtu；>0 美氣往歐洲有利)
- freight_is_assumed= 1 表示運費用固定假設
- blng2_174_usd_day = Baltic BLNG2-174 週五值（USD/day，前向補值 ≤7 日），只供對照運費緊張度；
                      未換算成 $/MMBtu（需航程/燃料/港口費模型），所以不進 lng_arb_nwe
- ho_crack          = HO($/gal) × 42 − WTI 期貨                             ($/bbl)
- gasoil_usd_bbl    = Gasoil($/mt) / 7.45                                   ($/bbl；柴油約 7.45 bbl/mt)
- gasoil_crack      = gasoil_usd_bbl − Brent 期貨                           ($/bbl；歐洲柴油裂解)
- gasoil_usd_gal    = gasoil_usd_bbl / 42                                   ($/gal)
- ho_gasoil_spread  = HO − gasoil_usd_gal                                   ($/gal；<0 歐洲比美東貴 → 美灣柴油往歐洲流)
- crack_321         = (2×RBOB×42 + HO×42 − 3×WTI) / 3                        ($/bbl)

注意：
- Yahoo 期貨為近月連續，換月日有跳空；TTF 與 EURUSD 日期不齊時 EURUSD 前向補值（最多 5 日）。
- LIQ_FEE、FREIGHT_ASSUMED 為粗略假設，只用來看套利方向與變化，不是精確成本。
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
LIQ_FEE = 2.75          # 美灣液化 tolling fee，$/MMBtu
FREIGHT_ASSUMED = 1.0   # USG→NWE 運費假設，$/MMBtu
MWH_TO_MMBTU = 3.412
BBL_PER_MT_GASOIL = 7.45


def main():
    p = pd.read_csv(DATA / "prices_daily.csv", index_col="date", parse_dates=True)
    p = p[p.index >= "2000-01-01"]
    eurusd = p["eurusd"].ffill(limit=5)
    hh = p["ng_fut"].fillna(p["hh_spot"])

    d = pd.DataFrame(index=p.index)
    d["ttf_usd_mmbtu"] = p["ttf_eur_mwh"] * eurusd / MWH_TO_MMBTU
    d["ttf_hh_spread"] = d["ttf_usd_mmbtu"] - hh
    d["us_lng_fob"] = 1.15 * hh + LIQ_FEE

    freight = pd.Series(FREIGHT_ASSUMED, index=p.index)
    assumed = pd.Series(1, index=p.index)
    blng = None
    fpath = DATA / "lng_freight.csv"
    if fpath.exists():
        f = pd.read_csv(fpath, index_col="date", parse_dates=True)
        if "spark30s_usd_mmbtu" in f:
            s = f["spark30s_usd_mmbtu"].dropna().reindex(p.index).ffill(limit=7)
            freight = s.fillna(freight)
            assumed = s.isna().astype(int)
        if "blng2_174_usd_day" in f:
            blng = f["blng2_174_usd_day"].dropna()
            blng = blng.reindex(blng.index.union(p.index)).ffill(limit=7).reindex(p.index)
    d["freight_usd_mmbtu"] = freight
    d["freight_is_assumed"] = assumed
    d["lng_arb_nwe"] = d["ttf_usd_mmbtu"] - d["us_lng_fob"] - d["freight_usd_mmbtu"]
    if blng is not None:
        d["blng2_174_usd_day"] = blng

    d["ho_crack"] = p["ho_fut"] * 42 - p["wti_fut"]
    d["gasoil_usd_bbl"] = p["gasoil_usd_mt"] / BBL_PER_MT_GASOIL
    d["gasoil_crack"] = d["gasoil_usd_bbl"] - p["brent_fut"]
    d["gasoil_usd_gal"] = d["gasoil_usd_bbl"] / 42
    d["ho_gasoil_spread"] = p["ho_fut"] - d["gasoil_usd_gal"]
    d["crack_321"] = (2 * p["rb_fut"] * 42 + p["ho_fut"] * 42 - 3 * p["wti_fut"]) / 3

    # 公式欄位才判斷全空列（freight 與 flag 永遠有值）
    calc = d.drop(columns=["freight_usd_mmbtu", "freight_is_assumed", "us_lng_fob", "blng2_174_usd_day"],
                  errors="ignore")
    d = d[calc.notna().any(axis=1)].round(4)
    d.to_csv(DATA / "derived_daily.csv", index_label="date", date_format="%Y-%m-%d")
    print(f"derived_daily  rows={len(d):6d}  {d.index[0].date()} → {d.index[-1].date()}")
    print(d.dropna(how="all", axis=1).tail(5).T.to_string())


if __name__ == "__main__":
    main()
