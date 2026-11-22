import shutil
from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
out = pkg / "outputs"
sub = pkg / "FINAL_SUBMISSION"
src = out / "CPE15_24_001777_SUPPORTING.zip"
dst = sub / "CPE15_24-001777_SUPPORTING.zip"
print("PKG", repr(str(pkg)))
print("OUT", repr(str(out)), out.exists())
print("SRC", repr(str(src)), src.exists())
print("DST", repr(str(dst)))
try:
    shutil.copy2(src, dst)
    print("COPY_OK", dst.exists(), dst.stat().st_size)
except Exception as e:
    print("COPY_ERR", type(e).__name__, e)
