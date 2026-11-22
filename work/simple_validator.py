import hashlib
import json
import zipfile
from pathlib import Path

from pypdf import PdfReader

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
sub = pkg / "FINAL_SUBMISSION"

expected = [
    "CPE15_24-001777_ANALYSIS.ipynb",
    "CPE15_24-001777_DECISION.pdf",
    "CPE15_24-001777_SUPPORTING.zip",
]
names = sorted(p.name for p in sub.iterdir() if p.is_file())
assert names == sorted(expected), "wrong files in FINAL_SUBMISSION: %s vs %s" % (names, sorted(expected))

nb_path = sub / "CPE15_24-001777_ANALYSIS.ipynb"
nb = json.loads(nb_path.read_text(encoding="utf-8"))
src = json.dumps(nb)
assert "mesusim-stack" in src, "not using Mark Susim source URLs"
assert "RollieGarcia0031" not in src, "old source URL still present"
assert "raw.githubusercontent.com/mesusim-stack" in src
assert src.count("raw.githubusercontent.com") == 7, "raw count: %d" % src.count("raw.githubusercontent.com")
assert "urllib.request.urlretrieve" in src
# The phrase appears only inside the notebook's own anti-claim self-check;
# no actual instructor-authorization claim is made.
assert src.count("authorized by the instructor") == 1, "unexpected count of 'authorized by the instructor': %d" % src.count("authorized by the instructor")
assert "student-written simulated update" in src
assert "MANUAL_FACILITY_UPDATES = {}" in src

# ZIP contents
zip_path = sub / "CPE15_24-001777_SUPPORTING.zip"
with zipfile.ZipFile(zip_path) as archive:
    namelist = archive.namelist()
print("ZIP namelist:", namelist)
assert namelist == ["CPE15_24-001777_FINAL_MAP.html", "CPE15_24-001777_PROCESSED.csv"], namelist

# PDF
pdf = sub / "CPE15_24-001777_DECISION.pdf"
reader = PdfReader(pdf)
text = "\n".join(page.extract_text() or "" for page in reader.pages)
assert len(reader.pages) == 1
assert text.count("\ufffd") == 0
assert "Mark Gabriel E. Susim" in text
assert "Student ID 24-001777" in text
assert "Section BSCpE-3GF" in text
assert "November 20, 2026" in text
assert "Memo body word count: 308" in text

for name in expected:
    p = sub / name
    print(f"{name}: {p.stat().st_size} bytes sha256={hashlib.sha256(p.read_bytes()).hexdigest()}")

print("FINAL_SUBMISSION_VALIDATION_PASS")