from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
out = pkg / "outputs"
print("ITERDIR")
for p in out.iterdir():
    nm = p.name
    print(repr(nm), len(nm), "exists=", p.exists(), "file=", p.is_file())
    if nm.endswith(".zip"):
        print("  bytes:", nm.encode("utf-8").hex())
        target = out / nm
        print("  target exists:", target.exists(), "same?", target == p)
