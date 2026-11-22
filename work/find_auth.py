import json
from pathlib import Path

nb = json.loads(Path(r"C:\Users\Haacha\Cpe-15 Finals Project\work\Operation Blank Map - STUDENT PACKAGE\FINAL_SUBMISSION\CPE15_24-001777_ANALYSIS.ipynb").read_text(encoding="utf-8"))
for i, cell in enumerate(nb["cells"]):
    text = "".join(cell.get("source", []))
    if "authorized by the instructor" in text or "authoriz" in text.lower():
        print(f"--- CELL {i} ({cell['cell_type']}) ---")
        for line in text.splitlines():
            if "authoriz" in line.lower():
                print(repr(line))
