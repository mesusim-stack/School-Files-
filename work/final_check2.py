import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from pypdf import PdfReader

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
sub = pkg / "FINAL_SUBMISSION"
out = pkg / "outputs"

expected = [
    "CPE15_24-001777_ANALYSIS.ipynb",
    "CPE15_24-001777_DECISION.pdf",
    "CPE15_24-001777_SUPPORTING.zip",
]
shutil.copy2(out / "CPE15_24_001777_SUPPORTING.zip", sub / "CPE15_24-001777_SUPPORTING.zip")
zip_path = sub / "CPE15_24-001777_SUPPORTING.zip"
names = sorted(p.name for p in sub.iterdir() if p.is_file())
assert names == sorted(expected), (names, sorted(expected))
assert len(list(sub.iterdir())) == 3, list(sub.iterdir())

nb_path = sub / "CPE15_24-001777_ANALYSIS.ipynb"
nb = json.loads(nb_path.read_text(encoding="utf-8"))
src = json.dumps(nb)
assert "mesusim-stack" in src, "not using Mark Susim source URLs"
assert "RollieGarcia0031" not in src, "old source URL still present"
assert "raw.githubusercontent.com/mesusim-stack" in src
assert src.count("raw.githubusercontent.com") == 7, src.count("raw.githubusercontent.com")
assert "urllib.request.urlretrieve" in src
assert "urllib.request.urlopen" not in src
assert 'DATA_DIR / "zones.geojson"' not in src
assert 'DATA_DIR / "facilities.csv"' not in src
assert "authorized by the instructor" not in src
assert "student-written simulated update" in src
assert "MANUAL_FACILITY_UPDATES = {}" in src

with zipfile.ZipFile(zip_path) as archive:
    assert archive.namelist() == [
        "CPE15_24_001777_FINAL_MAP.html",
        "CPE15_24_001777_PROCESSED.csv",
    ], archive.namelist()

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
