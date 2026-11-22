from pathlib import Path

p = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE\outputs\CPE15_24_001777_SUPPORTING.zip")
print("exists", p.exists())
try:
    data = p.read_bytes()
    print("READ_OK", len(data))
except Exception as e:
    print("READ_ERR", type(e).__name__, e)

# Try via glob to see if the path resolves differently
parent = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE\outputs")
for cand in parent.glob("*SUPPORTING*"):
    print("GLOB", repr(cand), cand.stat().st_size)
