import time
from pathlib import Path

base = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE\outputs")
a = base / "CPE15_24-001777_SUPPORTING.zip"
prev = None
for i in range(30):
    cur = a.exists()
    if cur != prev:
        print(f"{time.strftime('%H:%M:%S')} -> exists={cur}")
        prev = cur
    time.sleep(0.5)
print("done", a.exists())
