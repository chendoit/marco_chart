"""dealer-funding 資料抓取（可重跑）：python fetch.py [--start 2018-01-01]
F1 pd_financing.csv      ：NY Fed Primary Dealer Statistics（週頻）
F2 repo_haircuts.csv     ：OFR Hedge Fund Monitor / SEC Form PF 過度擔保率（haircut 的近似口徑）與 SCOOS 擔保品條件
F4 hedge_fund_leverage.csv：OFR Hedge Fund Monitor / SEC Form PF 槓桿、借款、Treasury 曝險（季頻）
只取得資料，不做衍生計算。原始回應快取在 raw/。
"""
import argparse
import json
import os
import time

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)
NYF = "https://markets.newyorkfed.org/api/pd"
HF = "https://data.financialresearch.gov/hf/v1"

PD_KEYS = [
    "PDPOSGST-TOT", "PDPOSGS-B",
    "PDSORA-UTSETTOT", "PDSIRRA-UTSETTOT", "PDSORA-UTSTTOT", "PDSIRRA-UTSTTOT",
    "PDSORA-FGEMTOT", "PDSIRRA-FGEMTOT", "PDSORA-FGMTOT", "PDSIRRA-FGMTOT",
    "PDSORA-FGCMTOT", "PDSIRRA-FGCMTOT", "PDSORA-CDTOT", "PDSIRRA-CDTOT",
    "PDSORA-ETOT", "PDSIRRA-ETOT", "PDSORA-ABSTOT", "PDSIRRA-ABSTOT",
    "PDSORA-OTOT", "PDSIRRA-OTOT",
    "PDSIOSB-UTSETTOT", "PDSOOS-UTSETTOT",
]
HAIRCUT_KEYS = [
    "FPF-OCRATEALL_PERCENT", "FPF-OCRATECASHSEC_PERCENT",
    "FPF-GAVN10_OCRATEALL_PERCENT", "FPF-GAVN11TO50_OCRATEALL_PERCENT", "FPF-GAVN51_OCRATEALL_PERCENT",
    "FPF-GAVN10_OCRATEEXOTHER_PERCENT", "FPF-GAVN11TO50_OCRATEEXOTHER_PERCENT", "FPF-GAVN51_OCRATEEXOTHER_PERCENT",
    "SCOOS-NET_COLLATTERMS",
]
LEV_KEYS = [
    "FPF-ALLQHF_GAV_SUM", "FPF-ALLQHF_GNE_SUM", "FPF-ALLQHF_NAV_SUM",
    "FPF-ALLQHF_GAVN10_LEVERAGERATIO_AVERAGE", "FPF-ALLQHF_GAVN11TO50_LEVERAGERATIO_AVERAGE",
    "FPF-ALLQHF_GAVN51_LEVERAGERATIO_AVERAGE", "FPF-ALLQHF_GAVN10_BORROWING_PERCENT",
    "FPF-BORROW_REPO_SUM", "FPF-BORROW_PRIMEBROKER_SUM", "FPF-BORROW_OTHERSECURED_SUM",
    "FPF-BORROW_REPO_GAVN10_PERCENT", "FPF-BORROW_REPO_GAVN11TO50_PERCENT", "FPF-BORROW_REPO_GAVN51_PERCENT",
    "FPF-ASSETCLASS_LTREASURY_SUM", "FPF-ASSETCLASS_STREASURY_SUM",
    "FPF-ASSETCLASS_REPO_REPO_SUM", "FPF-ASSETCLASS_REPO_REVERSEREPO_SUM",
    "FPF-ASSETCLASS_USGOV_GNE_SUM", "FPF-ASSETCLASS_USGOV_LGNE_SUM", "FPF-ASSETCLASS_USGOV_SGNE_SUM",
    "FPF-ASSETCLASS_IRD_GNE_SUM",
    "FPF-STRATEGY_MACRO_LEVERAGERATIO_GAVWMEAN", "FPF-STRATEGY_MACRO_LEVERAGERATIO_NAVWMEAN",
    "FPF-STRATEGY_RV_LEVERAGERATIO_GAVWMEAN", "FPF-STRATEGY_RV_LEVERAGERATIO_NAVWMEAN",
    "FPF-STRATEGY_MULTI_LEVERAGERATIO_GAVWMEAN", "FPF-STRATEGY_MULTI_LEVERAGERATIO_NAVWMEAN",
    "SCOOS-NET_HF_LEVERAGEUSE",
]

S = requests.Session()


def get(url, cache, as_json=True):
    path = os.path.join(RAW, cache)
    if os.path.exists(path) and os.environ.get("REFRESH") != "1":
        txt = open(path, encoding="utf-8").read()
    else:
        for i in range(3):
            try:
                r = S.get(url, timeout=60)
                r.raise_for_status()
                txt = r.text
                break
            except Exception as e:
                if i == 2:
                    raise
                time.sleep(2)
        open(path, "w", encoding="utf-8").write(txt)
        time.sleep(0.3)
    return json.loads(txt) if as_json else txt


def pd_part(start):
    lst = get(f"{NYF}/list/timeseries.json", "pd_list.json")["pd"]["timeseries"]
    desc = {x["keyid"]: x["description"] for x in lst}
    rows = []
    for k in PD_KEYS:
        d = get(f"{NYF}/get/{k}.json", f"pd_{k}.json")["pd"]["timeseries"]
        for x in d:
            if x["asofdate"] >= start and x["value"] not in ("", "*", None):
                try:
                    v = float(x["value"])
                except ValueError:
                    continue
                rows.append((x["asofdate"], k, desc.get(k, k), v, "Millions of USD"))
    return rows


def hf_part(keys, start):
    rows = []
    for k in keys:
        try:
            j = get(f"{HF}/series/full?mnemonic={k}", f"hf_{k}.json")[k]
        except Exception as e:
            print("SKIP", k, e)
            continue
        md = j["metadata"]
        name = md["description"]["name"]
        unit = md.get("unit", {}).get("name", "")
        for d, v in j["timeseries"]["aggregation"]:
            if d >= start and v is not None:
                rows.append((d, k, name, v, unit))
    return rows


def write(rows, name):
    df = pd.DataFrame(rows, columns=["date", "series_key", "description", "value", "unit"])
    df = df.drop_duplicates(["date", "series_key"]).sort_values(["date", "series_key"])
    df.to_csv(os.path.join(HERE, name), index=False, encoding="utf-8")
    print(name, len(df), df.date.min(), df.date.max(), df.series_key.nunique())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    a = ap.parse_args()
    write(pd_part(a.start), "pd_financing.csv")
    write(hf_part(HAIRCUT_KEYS, a.start), "repo_haircuts.csv")
    write(hf_part(LEV_KEYS, a.start), "hedge_fund_leverage.csv")
