"""Female LFPR for every state, by sector and year, tagged with agrarian tier.

Pulls PLFS female LFPR (15+, usual status ps+ss) for rural, urban and
rural+urban, for all states/UTs:
  July-June years 2017-18 .. 2023-24 (year_type_code=1)
  calendar years  2022 .. 2025       (year_type_code=2)
and joins each state to its agrarian tier from
../state_flfpr_gsva/state_flfpr_gsva_analysis.csv (2023-24 agri GSVA share).

Writes tier_flfpr.json (read by tiers.html) and the raw responses to raw_tiers/.
"""
import csv
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw_tiers"
TIERS_CSV = OUT.parent / "state_flfpr_gsva" / "state_flfpr_gsva_analysis.csv"
API = "https://api.mospi.gov.in/api/plfs/getData"

SERIES = [
    ("Jul-Jun", 1, ["2017-18", "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]),
    ("Calendar", 2, ["2022", "2023", "2024", "2025"]),
]
SECTORS = {"rural": "rural", "urban": "urban", "rural + urban": "ru"}

# api.mospi.gov.in only supports legacy TLS renegotiation, which OpenSSL 3
# refuses by default. Allow it for this host; certificates are still verified.
CTX = ssl.create_default_context()
CTX.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT


def get(params, retries=3):
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, context=CTX, timeout=90) as r:
                return json.loads(r.read())
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == retries - 1:
                sys.exit(f"request failed: {e}\n{url}")
            time.sleep(3 * (attempt + 1))


def main():
    RAW.mkdir(exist_ok=True)
    gsva = {r["state"]: r for r in csv.DictReader(open(TIERS_CSV))}
    tiers = {s: r["tier"] for s, r in gsva.items()}

    years, values, untiered = [], {}, set()
    for label, year_type, yrs in SERIES:
        years += [{"year": y, "series": label} for y in yrs]
        page, rows = 1, []
        while True:
            resp = get({
                "indicator_code": 1, "frequency_code": 1, "gender_code": 2, "age_code": 1,
                "sector_code": "1,2,3", "weekly_status_code": 1, "year_type_code": year_type,
                "year": ",".join(yrs), "education_code": 0, "religion_code": 1,
                "social_category_code": 1, "limit": 200, "page": page, "Format": "JSON",
            })
            (RAW / f"plfs_{label}_page{page}.json").write_text(json.dumps(resp, ensure_ascii=False, indent=1))
            rows += resp.get("data") or []
            if page >= (resp.get("meta_data") or {}).get("totalPages", 1):
                break
            page += 1
        print(f"{label}: {len(rows)} rows")
        for r in rows:
            state = r["state"]
            if state == "All India":
                continue
            if state not in tiers:
                untiered.add(state)
                continue
            cell = values.setdefault(state, {}).setdefault(r["year"], {})
            # the API sends null or the string "NaN" for cells it has no estimate for
            if r["value"] not in (None, "", "NaN"):
                cell[SECTORS[r["sector"]]] = r["value"]

    missing = [f"{s} {y['year']} {k}" for s in values for y in years for k in SECTORS.values()
               if values[s].get(y["year"], {}).get(k) is None]
    no_data = sorted(set(tiers) - set(values))

    out = {
        "source": "MoSPI eSankhyiki PLFS: female LFPR, 15+, usual status (ps+ss)",
        "tier_basis": "Agri share of GSVA, current prices, 2023-24 (High > 25%, Mid 15-25%, Low < 15%)",
        "years": years,
        "states": [{"state": s, "tier": tiers[s], "values": values[s]} for s in sorted(values)],
        # the 2023-24 classification table from ../state_flfpr_gsva, carried as-is
        "classification": [{
            "state": s,
            "gsva_rank": int(r["gsva_rank"]),
            "tier": r["tier"],
            "agri_share_cur_pct": float(r["agri_share_cur_pct"]),
            "total_gsva_cur_cr": float(r["total_gsva_cur_cr"]),
            "flfpr_pct": r["flfpr_pct"],
        } for s, r in gsva.items()],
    }
    (OUT / "tier_flfpr.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"{len(values)} tiered states with data; tiers: "
          + ", ".join(f"{t}={sum(1 for s in values if tiers[s] == t)}" for t in ("High", "Mid", "Low")))
    print("No tier (not in GSVA analysis), excluded:", sorted(untiered) or "none")
    print("Tiered but no PLFS rows:", no_data or "none")
    print(f"Missing state/year/sector cells: {len(missing)}")
    for m in missing:
        print("  ", m)


if __name__ == "__main__":
    main()
