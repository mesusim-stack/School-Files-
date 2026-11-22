import time
from pathlib import Path

pkg = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE")
out = pkg / "outputs"
for i in range(8):
    target = out / "CPE15_24_001777_SUPPORTING.zip"
    exists = target.exists()
    size = None
    err = None
    try:
        size = target.stat().st_size
    except Exception as e:
        err = type(e).__name__
    print(i, "exists=", exists, "size=", size, "err=", err)
    time.sleep(1)
