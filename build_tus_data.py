"""Women's unpaid domestic and caregiving work by state, for the strip plots on possible-theories.html.

Time Use in India 2024 (NSO, MoSPI), Statement 3.1, PDF pages 98-107: percentage of
persons participating in a day in each major activity division (major activity of
the time slot only). Takes the female, rural + urban column for two rows:
  Unpaid domestic services for household members
  Unpaid caregiving services for household members

Downloads the report to a temporary folder, keeps the extracted text of those pages
in raw_tus/, and writes tus_unpaid_female.json. Needs pdftotext (poppler-utils).
"""
import json
import re
import ssl
import subprocess
import tempfile
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw_tus"
URL = "https://mospi.gov.in/sites/default/files/publication_reports/TUS_Report_2024_28.03.2025F.pdf"
FIRST, LAST = 98, 107

ROWS = {
    "domestic": "Unpaid domestic services for household members",
    "caregiving": "Unpaid caregiving services for household members",
}
# columns: rural m/f/p, urban m/f/p, rural+urban m/f/p
FEMALE_RU = 7
# report name -> the name PLFS uses on the other pages
RENAME = {
    "A & N Islands": "Andaman & Nicobar Islands",
    "Dadra & Nagar Haveli and Daman & Diu": "Dadra & Nagar Haveli & Daman & Diu",
}

# same legacy-TLS allowance as the eSankhyiki scripts; certificates are still verified
CTX = ssl.create_default_context()
CTX.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT


def main():
    RAW.mkdir(exist_ok=True)
    txt = RAW / f"tus2024_pdf_pages_{FIRST}-{LAST}.txt"
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "tus2024.pdf"
        with urllib.request.urlopen(URL, context=CTX, timeout=180) as r:
            pdf.write_bytes(r.read())
        subprocess.run(["pdftotext", "-layout", "-f", str(FIRST), "-l", str(LAST), str(pdf), str(txt)], check=True)

    values, state = {}, None
    for line in txt.read_text().splitlines():
        s = line.strip()
        for key, label in ROWS.items():
            if s.startswith(label):
                values.setdefault(state, {})[key] = s[len(label):].split()[FEMALE_RU]
                break
        else:
            # state headings are the only centred, letters-only lines
            if (s and re.fullmatch(r"[A-Za-z&.()\- ]+", s) and "female" not in s
                    and len(line) - len(line.lstrip()) > 40):
                state = s

    india = values.pop("All India")
    out = {
        "source": "NSO, MoSPI, Time Use in India 2024 (Time Use Survey, January-December 2024), Statement 3.1",
        "url": URL,
        "measure": "Percentage of women (6+, rural + urban) who did the activity in a day, as the major activity of a time slot",
    }
    for key in ROWS:
        out[key] = {
            "label": ROWS[key],
            "all_india": india[key],
            "states": sorted(({"state": RENAME.get(s, s), "value": v[key]} for s, v in values.items()),
                             key=lambda r: float(r["value"])),
        }
    (OUT / "tus_unpaid_female.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"{len(values)} states/UTs; All India: {india}")
    for key in ROWS:
        st = out[key]["states"]
        kerala = next(r for r in st if r["state"] == "Kerala")
        print(f"{key}: low {st[0]}, high {st[-1]}, Kerala {kerala['value']}")


if __name__ == "__main__":
    main()
