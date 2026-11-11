"""日頻 repo 代理資料（非 haircut）：OFR repo 資料集 + NY Fed 擔保回購參考利率。"""
import json, os, time
import requests
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)
START = "2018-01-01"
OFR = "https://data.financialresearch.gov/v1"
NYF = "https://markets.newyorkfed.org/api"
OFR_KEYS = [
    "REPO-DVP_AR_OO-F", "REPO-DVP_TV_TOT-F", "REPO-DVP_OV_TOT-F",
    "REPO-GCF_AR_OO-F", "REPO-GCF_TV_TOT-F",
    "REPO-TRIV1_AR_OO-F", "REPO-TRIV1_TV_TOT-F",
]
S = requests.Session()
LOG = []


def get(url, cache):
    path = os.path.join(RAW, cache)
    if os.path.exists(path) and os.environ.get("REFRESH") != "1":
        return json.load(open(path, encoding="utf-8"))
    last = None
    for i in range(3):
        try:
            r = S.get(url, timeout=60)
            r.raise_for_status()
            open(path, "w", encoding="utf-8").write(r.text)
            time.sleep(0.3)
            return r.json()
        except Exception as e:
            last = e
            time.sleep(2)
    raise last


def ofr_part():
    rows = []
    for k in OFR_KEYS:
        try:
            j = get(f"{OFR}/series/full?mnemonic={k}", f"ofr_{k}.json")[k]
        except Exception as e:
            LOG.append(f"OFR {k} FAIL {e}")
            continue
        md = j["metadata"]
        name = md["description"]["name"]
        unit = md.get("unit", {}).get("name", "")
        n = 0
        for d, v in j["timeseries"]["aggregation"]:
            if d >= START and v is not None:
                rows.append((d, k, name, v, unit)); n += 1
        LOG.append(f"OFR {k} rows={n}")
    return rows


def nyf_part():
    rows = []
    end = time.strftime("%Y-%m-%d")
    for t in ["sofr", "bgcr", "tgcr"]:
        try:
            j = get(f"{NYF}/rates/secured/{t}/search.json?startDate={START}&endDate={end}", f"nyf_{t}.json")
        except Exception as e:
            LOG.append(f"NYF {t} FAIL {e}")
            continue
        n = 0
        for x in j.get("refRates", []):
            d = x["effectiveDate"]
            if x.get("percentRate") is not None:
                rows.append((d, f"NYF-{t.upper()}-RATE", f"{t.upper()} rate", x["percentRate"], "Percent")); n += 1
            if x.get("volumeInBillions") is not None:
                rows.append((d, f"NYF-{t.upper()}-VOL", f"{t.upper()} underlying volume", x["volumeInBillions"], "Billions of USD"))
        LOG.append(f"NYF {t} days={n}")
    return rows


if __name__ == "__main__":
    rows = ofr_part() + nyf_part()
    df = pd.DataFrame(rows, columns=["date", "series_key", "description", "value", "unit"])
    df = df.drop_duplicates(["date", "series_key"]).sort_values(["date", "series_key"])
    df.to_csv(os.path.join(HERE, "daily_repo.csv"), index=False)
    print("\n".join(LOG))
    print("rows", len(df), "series", df.series_key.nunique(), df.date.min(), df.date.max())
    g = df.groupby("series_key").date.agg(["min", "max", "count"])
    print(g.to_string())
    dd = pd.to_datetime(pd.Series(sorted(df.date.unique()))).diff().dt.days.dropna()
    print("median gap days", dd.median())
