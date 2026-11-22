from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
for d in (".", "outputs", "FINAL_SUBMISSION"):
    base = pkg if d == "." else pkg / d
    print("==", d)
    for f in sorted(base.iterdir()):
        nm = f.name
        marker = "-" if "24-001777" in nm else ("_" if "24_001777" in nm else "")
        print(f"  {marker:>1} len={len(nm)} {nm.encode('utf-8').hex()}")
