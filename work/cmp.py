import os
from pathlib import Path

base = r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE\outputs"
out = Path(base)
a = out / "CPE15_24-001777_SUPPORTING.zip"
cands = [p for p in out.iterdir() if p.name.endswith(".zip")]
print("NCANDS", len(cands))
for b in cands:
    print("A==B", a == b)
    print("A_STR", str(a))
    print("B_STR", str(b))
    print("A_NAME_REPR", repr(a.name), "B_NAME_REPR", repr(b.name))
    print("A_EXISTS", a.exists(), "B_EXISTS", b.exists())
    try:
        print("A_STAT", a.stat().st_size)
    except Exception as e:
        print("A_STAT_ERR", type(e).__name__, e)
    try:
        print("B_STAT", b.stat().st_size)
    except Exception as e:
        print("B_STAT_ERR", type(e).__name__, e)
    try:
        with open(b, "rb") as fh:
            head = fh.read(4)
        print("B_OPEN_OK", head)
    except Exception as e:
        print("B_OPEN_ERR", type(e).__name__, e)
