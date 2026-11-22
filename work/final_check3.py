import hashlib
import json
import shutil
import time
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


def read_with_retry(path: Path, attempts: int = 200) -> bytes:
    last = None
    for _ in range(attempts):
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            last = exc
            time.sleep(0.5)
    raise last


src_zip = out / "CPE15_24-001777_SUPPORTING.zip"
try:
    data = read_with_retry(src_zip, attempts=40)
    print("READ_ZIP_OK", len(data))
except Exception as exc:
    print("READ_ZIP_FAILED", type(exc).__name__, exc)
    # Rebuild the supporting archive from the two required sources.
    html_bytes = read_with_retry(out / "CPE15_24_001777_FINAL_MAP.html", attempts=40)
    csv_bytes = read_with_retry(out / "CPE15_24_001777_PROCESSED.csv", attempts=40)
    buf = Path(tempfile_target := Path(__file__).with_name("_rebuilt_support.zip"))
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("CPE15_24_001777_FINAL_MAP.html", html_bytes)
        z.writestr("CPE15_24_001777_PROCESSED.csv", csv_bytes)
    data = buf.read_bytes()
    buf.unlink(missing_ok=True)
    print("REBUILT_ZIP", len(data))

dst_zip = sub / "CPE15_24-001777_SUPPORTING.zip"
for attempt in range(40):
    try:
        dst_zip.write_bytes(data)
        assert dst_zip.exists() and dst_zip.stat().st_size == len(data)
        print("WROTE_ZIP_OK", dst_zip.stat().st_size)
        break
    except Exception as exc:
        print(f"WRITE_ZIP_RETRY {attempt}", type(exc).__name__)
        time.sleep(0.5)

names = sorted(p.name for p in sub.iterdir() if p.is_file())
assert names == sorted(expected), (names, sorted(expected))
assert len(list(sub.iterdir())) == 3, list(sub.iterdir())

nb_path = sub / "CPE15_24-001777_ANALYSIS.ipynb"
nb = json.loads(nb_path.read_text(encoding="utf-8"))
src = json.dumps(nb)
assert "mesusim-stack" in src, "not using Mark Susim source URLs"
assert "RollieGarcia0031" not in src, "old source URL still present"
assert src.count("raw.githubusercontent.com") == 7, src.count("raw.githubusercontent.com")
assert "urllib.request.urlretrieve" in src
assert "urllib.request.urlopen" not in src
assert 'DATA_DIR / "zones.geojson"' not in src
assert 'DATA_DIR / "facilities.csv"' not in src
assert "student-written simulated update" in src
assert "MANUAL_FACILITY_UPDATES = {}" in src
# The phrase appears only inside the notebook's own anti-claim self-check; no actual claim is made.
assert src.count("authorized by the instructor") == 1, src.count("authorized by the instructor")

with zipfile.ZipFile(dst_zip) as archive:
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
