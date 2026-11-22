from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
for d in ("outputs", "FINAL_SUBMISSION"):
    print("==", d)
    p = pkg / d
    if not p.exists():
        print("  MISSING DIR")
        continue
    for f in sorted(p.iterdir()):
        print(" ", repr(f.name), f.stat().st_size if f.is_file() else "<dir>")
