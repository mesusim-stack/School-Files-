import time
from pathlib import Path

out = Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE\outputs")
a = out / "CPE15_24_001777_SUPPORTING.zip"
prev = None
for i in range(120):
    cur = a.exists()
    if cur != prev:
        try:
            st = a.stat()
            extra = f"size={st.st_size} mtime={time.strftime('%H:%M:%S', time.localtime(st.st_mtime))}"
        except Exception as e:
            extra = f"err={type(e).__name__}"
        print(f"{time.strftime('%H:%M:%S')} -> exists={cur} {extra}")
        prev = cur
    time.sleep(0.5)
print("final", a.exists())
