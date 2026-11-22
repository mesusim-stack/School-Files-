import os
from pathlib import Path

pkg = r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE"
out_dir = os.path.join(pkg, "outputs")
print("LISTDIR_REPR")
for n in os.listdir(out_dir):
    print(repr(n))
print("JOINED_EXISTS", os.path.exists(os.path.join(out_dir, "CPE15_24_001777_SUPPORTING.zip")))
try:
    st = os.stat(os.path.join(out_dir, "CPE15_24_001777_SUPPORTING.zip"))
    print("STAT_OK", st.st_size)
except Exception as e:
    print("STAT_ERR", type(e).__name__, e)
print("REALPATH_OUT", os.path.realpath(out_dir))
print("REALPATH_ZIP", os.path.realpath(os.path.join(out_dir, "CPE15_24_001777_SUPPORTING.zip")))
