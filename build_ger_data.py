"""Female higher-education GER vs female LFPR, by state, 2021-22.

Joins AISHE 2021-22 female Gross Enrolment Ratio (18-23, as supplied) with
PLFS July-June 2021-22 female LFPR (15+, usual status ps+ss, rural + urban)
already pulled into raw_tiers/ by build_tier_data.py, and tags each state
with its agrarian tier from tier_flfpr.json.

Also computes Pearson and Spearman correlations and an OLS fit (FLFPR on GER)
across states/UTs, unweighted, with and without Lakshadweep.

Writes ger_flfpr.json (read by missing-pieces.html).
"""
import glob
import json
from pathlib import Path

from scipy import stats

OUT = Path(__file__).resolve().parent
YEAR = "2021-22"

# AISHE 2021-22, female GER (higher education)
AISHE_FEMALE_GER = {
    "Chandigarh": 74.8, "Puducherry": 63.3, "Himachal Pradesh": 49.9, "Delhi": 49.5,
    "Kerala": 47.0, "Tamil Nadu": 46.9, "Uttarakhand": 44.5, "Sikkim": 42.3, "Goa": 40.9,
    "Telangana": 40.5, "Arunachal Pradesh": 38.4, "Karnataka": 37.5, "Andhra Pradesh": 36.3,
    "Haryana": 36.1, "Manipur": 35.7, "Maharashtra": 34.8, "Mizoram": 33.1, "Punjab": 30.8,
    "India": 28.5, "Madhya Pradesh": 28.0, "Rajasthan": 27.7, "West Bengal": 26.5,
    "Meghalaya": 26.4, "Jammu and Kashmir": 26.1, "Uttar Pradesh": 25.2,
    "Andaman and Nicobar": 24.0, "Gujarat": 22.6, "Odisha": 21.8, "Chhattisgarh": 20.9,
    "Tripura": 19.8, "Jharkhand": 18.8, "Nagaland": 18.7, "Assam": 16.8, "Bihar": 15.9,
    "Ladakh": 13.4, "DNH and Daman and Diu": 10.5, "Lakshadweep": 1.2,
}
# AISHE name -> PLFS name, where they differ
RENAME = {
    "India": "All India",
    "Jammu and Kashmir": "Jammu & Kashmir",
    "Andaman and Nicobar": "Andaman & Nicobar Islands",
    "DNH and Daman and Diu": "Dadra & Nagar Haveli & Daman & Diu",
}


def main():
    flfpr = {}
    for f in sorted(glob.glob(str(OUT / "raw_tiers" / "plfs_Jul-Jun_page*.json"))):
        for r in json.load(open(f)).get("data") or []:
            if r["year"] == YEAR and r["sector"] == "rural + urban" and r["value"] not in (None, "", "NaN"):
                flfpr[r["state"]] = float(r["value"])

    tiers = {s["state"]: s["tier"] for s in json.load(open(OUT / "tier_flfpr.json"))["states"]}

    states, india, unmatched = [], None, []
    for name, ger in AISHE_FEMALE_GER.items():
        plfs = RENAME.get(name, name)
        if plfs not in flfpr:
            unmatched.append(name)
            continue
        row = {"state": plfs, "ger": ger, "flfpr": flfpr[plfs]}
        if plfs == "All India":
            india = row
        else:
            row["tier"] = tiers.get(plfs)
            states.append(row)

    def correlate(rows):
        x, y = [r["ger"] for r in rows], [r["flfpr"] for r in rows]
        pr, sr, fit = stats.pearsonr(x, y), stats.spearmanr(x, y), stats.linregress(x, y)
        return {
            "n": len(rows),
            "pearson_r": round(float(pr[0]), 3), "pearson_p": round(float(pr[1]), 3),
            "spearman_rho": round(float(sr[0]), 3), "spearman_p": round(float(sr[1]), 3),
            "slope": round(fit.slope, 4), "intercept": round(fit.intercept, 3),
            "r_squared": round(fit.rvalue ** 2, 4),
        }

    out = {
        "year": YEAR,
        "ger_source": "Ministry of Education, All India Survey on Higher Education (AISHE) 2021-22: female GER, age 18-23",
        "flfpr_source": "MoSPI eSankhyiki PLFS, July 2021 - June 2022: female LFPR, 15+, usual status (ps+ss), rural + urban",
        "india": india,
        "correlation": correlate(states),
        "correlation_excl_lakshadweep": correlate([r for r in states if r["state"] != "Lakshadweep"]),
        "states": sorted(states, key=lambda s: s["state"]),
    }
    (OUT / "ger_flfpr.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"{len(states)} states/UTs joined; India = {india}")
    print("Unmatched AISHE names:", unmatched or "none")
    print("No tier:", [s["state"] for s in states if not s["tier"]])
    print("All states/UTs:", out["correlation"])
    print("Excl. Lakshadweep:", out["correlation_excl_lakshadweep"])


if __name__ == "__main__":
    main()
