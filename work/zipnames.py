import zipfile
from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
sub = pkg / "FINAL_SUBMISSION"
zp = sub / "CPE15_24-001777_SUPPORTING.zip"
with zipfile.ZipFile(zp) as z:
    entries = z.namelist()
print("N", len(entries))
for e in entries:
    print(repr(e), len(e), e.encode("utf-8").hex())
expected = ["CPE15_24_001777_FINAL_MAP.html", "CPE15_24_001777_PROCESSED.csv"]
for e, x in zip(entries, expected):
    print("EQ", e == x)
    if e != x:
        for i, (a, b) in enumerate(zip(e, x)):
            if a != b:
                print("DIFF at", i, hex(ord(a)), hex(ord(b)))
        print("len", len(e), len(x))
