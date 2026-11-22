from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
out = pkg / "outputs"
print("PKG EXISTS", pkg.exists())
print("OUT EXISTS", out.exists())
for p in sorted(out.iterdir()):
    print(repr(p.name), p.is_file(), p.stat().st_size if p.is_file() else "-")
