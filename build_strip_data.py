"""Female LFPR for every state/UT in calendar year 2025, for the strip plot on index.html.

PLFS: female, 15+, rural+urban, usual status (ps+ss), year_type_code=2 (calendar).
Writes strip_2025.json and the raw response to raw_strip/.
"""
import json
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw_strip"
YEAR = "2025"

# api.mospi.gov.in only supports legacy TLS renegotiation, which OpenSSL 3
# refuses by default. Allow it for this host; certificates are still verified.
CTX = ssl.create_default_context()
CTX.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT


def main():
    RAW.mkdir(exist_ok=True)
    params = {
        "indicator_code": 1, "frequency_code": 1, "gender_code": 2, "age_code": 1,
        "sector_code": 3, "weekly_status_code": 1, "year_type_code": 2, "year": YEAR,
        "education_code": 0, "religion_code": 1, "social_category_code": 1,
        "limit": 200, "Format": "JSON",
    }
    url = "https://api.mospi.gov.in/api/plfs/getData?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, context=CTX, timeout=90) as r:
        resp = json.loads(r.read())
    (RAW / f"plfs_female_lfpr_ru_{YEAR}.json").write_text(json.dumps(resp, ensure_ascii=False, indent=1))
    if (resp.get("meta_data") or {}).get("totalPages", 1) > 1:
        sys.exit("more than one page of results; raise the limit")

    states, missing, all_india = [], [], None
    for row in resp.get("data") or []:
        v = row["value"]
        # the API sends null or the string "NaN" for cells it has no estimate for
        if v in (None, "", "NaN"):
            missing.append(row["state"])
        elif row["state"] == "All India":
            all_india = v
        else:
            states.append({"state": row["state"], "value": v})

    out = {
        "year": YEAR,
        "measure": "Female LFPR, 15+, rural + urban, usual status (ps+ss), calendar year",
        "all_india": all_india,
        "states": sorted(states, key=lambda s: float(s["value"])),
        "missing": missing,
    }
    (OUT / "strip_2025.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    lo, hi = out["states"][0], out["states"][-1]
    kerala = next((s for s in states if s["state"] == "Kerala"), None)
    print(f"{len(states)} states/UTs with a value; All India {all_india}")
    print(f"lowest {lo['state']} {lo['value']}, highest {hi['state']} {hi['value']}, Kerala {kerala and kerala['value']}")
    print("no value:", missing or "none")


if __name__ == "__main__":
    main()
