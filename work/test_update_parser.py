import re

import pandas as pd

facilities_raw = pd.read_csv("data/facilities.csv", encoding="utf-8")


def parse(update_text):
    facility_updates = {}
    affected = []
    new = []
    clauses = re.split(r"[.;\n]", update_text)
    for clause in clauses:
        ids = set(re.findall(r"\bF\d{2}\b", clause, flags=re.I))
        for _, row in facilities_raw.iterrows():
            place = re.split(r"[-–—]", str(row["facility_name"]))[-1].strip()
            if place and place.lower() in clause.lower():
                ids.add(row["facility_id"])
        if not ids:
            continue
        low = clause.lower()
        status = None
        if re.search(
            r"non[- ]?operational|not operational|offline|closed|unavailable|suspended|withdrawn|deactivated",
            low,
        ):
            status = "non-operational"
        elif re.search(
            r"\boperational\b|\bonline\b|\bopen\b|\bavailable\b|restored|activated|reopened",
            low,
        ):
            status = "operational"
        if status:
            for fid in sorted(ids):
                facility_updates[fid] = status
                if fid not in affected:
                    affected.append(fid)
    for match in re.finditer(
        r"\b(F\d{2})\b[^.]*?longitude\s*[:=]?\s*(\d+\.\d+)[^.]*?latitude\s*[:=]?\s*(\d+\.\d+)",
        update_text,
        flags=re.I,
    ):
        fid, lon, lat = match.group(1).upper(), float(match.group(2)), float(match.group(3))
        if fid not in set(facilities_raw["facility_id"]):
            new.append(
                {
                    "facility_id": fid,
                    "facility_name": f"Scenario Assistance Hub — {fid}",
                    "longitude": lon,
                    "latitude": lat,
                    "status": facility_updates.get(fid, "operational"),
                }
            )
    return facility_updates, affected, new


samples = [
    "F03 is non-operational effective immediately.",
    "The Nagsinamo hub is offline.",
    "F04 is restored and operational.",
    "F02 is closed; F05 remains operational.",
    "F06 new hub at longitude 121.55 latitude 14.10, operational.",
]
for text in samples:
    print(text)
    print(" ", parse(text))
