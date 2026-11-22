"""CPE15 Operation Blank Map - standalone analysis build.

Run from the extracted student package directory so that `data/` resolves.
This script is the reference implementation; the notebook mirrors its cells.
"""

from __future__ import annotations

import json
import re
import sqlite3
import zipfile
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from branca.colormap import LinearColormap
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

STUDENT_ID = "24-001777"
STUDENT_NAME = "Mark Gabriel E. Susim"
SECTION = "BSCpE-3GF"
COURSE = "CPE15 Professional Elective 1: Programming for Data Science"
MEMO_DATE = "November 20, 2026"

DATA_DIR = Path("data")
OUT_DIR = Path("outputs")
FIG_DIR = Path("figures")
OUT_DIR.mkdir(exist_ok=True)
FIG_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# 0. Workspace and versions
# ---------------------------------------------------------------------------
expected = [
    "zones.geojson",
    "household_access.csv",
    "risk_index.csv",
    "service_requests.sqlite",
    "facilities.csv",
    "field_notes.txt",
]
assert all((DATA_DIR / name).exists() for name in expected), "Missing evidence file(s)."

print("Library versions")
for name, module in [
    ("pandas", pd),
    ("numpy", np),
    ("geopandas", gpd),
    ("folium", folium),
    ("matplotlib", matplotlib),
]:
    print(f"  {name}: {module.__version__}")

# ---------------------------------------------------------------------------
# 1. Evidence audit
# ---------------------------------------------------------------------------
zones = gpd.read_file(DATA_DIR / "zones.geojson")
household_raw = pd.read_csv(DATA_DIR / "household_access.csv")
risk_raw = pd.read_csv(DATA_DIR / "risk_index.csv")
facilities_raw = pd.read_csv(DATA_DIR / "facilities.csv", encoding="utf-8")
notes = (DATA_DIR / "field_notes.txt").read_text(encoding="utf-8")

print("\nRaw evidence shapes")
print("  zones:", zones.shape, "| CRS:", zones.crs)
print("  household:", household_raw.shape)
print("  risk:", risk_raw.shape)
print("  facilities:", facilities_raw.shape)

print("\nHousehold raw records")
print(household_raw.to_string(index=False))
print("\nRisk raw records")
print(risk_raw.to_string(index=False))
print("\nFacilities")
print(facilities_raw.to_string(index=False))


def normalize_zone(value: object) -> str:
    """Canonicalize zone identifiers: A-03 -> A03, whitespace stripped."""
    return str(value).strip().upper().replace("-", "")


# Native-Python parsing of the verified field notes.
verified_lines = [line.strip() for line in notes.splitlines() if "VERIFIED" in line]
print("\nVerified field-note statements")
for line in verified_lines:
    print(" ", line)

corrections: dict[str, dict] = {}
for line in verified_lines:
    m = re.search(
        r"zone code\s+(A-\d+)\s+is an alternate entry for\s+(A\d+)\s+in ALL source files",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        corrections["alias"] = {
            "alias": m.group(1).upper(),
            "canonical": m.group(2).upper(),
            "source": line,
        }
        continue

    m = re.search(
        r"missing households_with_access value for\s+(A\d+)\s+is\s+(\d+)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        corrections["missing_access"] = {
            "zone": m.group(1).upper(),
            "value": int(m.group(2)),
            "source": line,
        }
        continue

    m = re.search(
        r"erroneous households_with_access value\s+(\d+)\s+for\s+(A\d+)\s+is superseded by\s+(\d+)",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        corrections["erroneous_access"] = {
            "old": int(m.group(1)),
            "zone": m.group(2).upper(),
            "new": int(m.group(3)),
            "source": line,
        }
        continue

    m = re.search(
        r"For\s+(A\d+),\s+risk_score\s+(\d+)\s+is current;\s+risk_score\s+(\d+)\s+is an obsolete duplicate",
        line,
        flags=re.IGNORECASE,
    )
    if m:
        corrections["risk_duplicate"] = {
            "zone": m.group(1).upper(),
            "current": int(m.group(2)),
            "obsolete": int(m.group(3)),
            "source": line,
        }
        continue

required_keys = {"alias", "missing_access", "erroneous_access", "risk_duplicate"}
assert required_keys.issubset(corrections), f"Unparsed field note(s): {required_keys - set(corrections)}"
print("\nParsed corrections")
for key, value in corrections.items():
    print(f"  {key}: {value}")

# SQLite inspection
con = sqlite3.connect(DATA_DIR / "service_requests.sqlite")
requests_raw = pd.read_sql_query("SELECT * FROM requests", con)
status_counts = pd.read_sql_query(
    "SELECT status, COUNT(*) AS n FROM requests GROUP BY status ORDER BY status", con
)
duplicate_request_ids = pd.read_sql_query(
    "SELECT request_id, COUNT(*) AS n FROM requests GROUP BY request_id HAVING COUNT(*) > 1 ORDER BY request_id",
    con,
)
print("\nSQLite request status counts")
print(status_counts.to_string(index=False))
print("\nDuplicate request IDs (excluded by COUNT(DISTINCT))")
print(duplicate_request_ids.to_string(index=False) if len(duplicate_request_ids) else "  none")

# ---------------------------------------------------------------------------
# 2. Reconstruction
# ---------------------------------------------------------------------------
# Household access
hh = household_raw.copy()
hh["zone_id"] = hh["zone_code"].map(normalize_zone)
hh["total_households"] = pd.to_numeric(hh["total_households"], errors="coerce")
hh["households_with_access"] = pd.to_numeric(hh["households_with_access"], errors="coerce")
duplicate_household_rows = hh[hh.duplicated("zone_id", keep=False)].copy()
hh = hh.drop_duplicates("zone_id", keep="first").copy()

missing = corrections["missing_access"]
hh.loc[hh["zone_id"] == missing["zone"], "households_with_access"] = missing["value"]

err = corrections["erroneous_access"]
err_mask = (hh["zone_id"] == err["zone"]) & np.isclose(
    hh["households_with_access"], err["old"], equal_nan=False
)
hh.loc[err_mask, "households_with_access"] = err["new"]

assert hh["households_with_access"].notna().all(), "Unresolved missing access value."
assert (hh["households_with_access"] <= hh["total_households"]).all(), "Access exceeds total households."
assert hh["zone_id"].is_unique, "Household table is not one row per zone."

# Risk
risk = risk_raw.copy()
risk["zone_id"] = risk["zone_code"].map(normalize_zone)
risk["risk_score"] = pd.to_numeric(risk["risk_score"], errors="coerce")
rd = corrections["risk_duplicate"]
risk = risk[
    ~((risk["zone_id"] == rd["zone"]) & np.isclose(risk["risk_score"], rd["obsolete"]))
].copy()
risk = risk.drop_duplicates("zone_id", keep="first")
assert risk["zone_id"].is_unique, "Risk table is not one row per zone."
assert risk["risk_score"].between(0, 100).all(), "Risk score outside 0-100."

# Eligible requests, with alias normalization inside SQL
sql = """
SELECT
    CASE
        WHEN UPPER(REPLACE(TRIM(zone_code), '-', '')) = 'A03' THEN 'A03'
        ELSE UPPER(REPLACE(TRIM(zone_code), '-', ''))
    END AS zone_id,
    COUNT(DISTINCT request_id) AS valid_requests
FROM requests
WHERE LOWER(TRIM(status)) IN ('verified', 'open')
GROUP BY 1
ORDER BY 1
"""
req = pd.read_sql_query(sql, con)
con.close()
req = (
    req.set_index("zone_id")
    .reindex(zones["zone_id"].str.strip().str.upper())
    .fillna(0)
    .astype(int)
    .rename_axis("zone_id")
    .reset_index()
)
assert len(req) == 12, "Request table does not cover all 12 zones."

# Integrate
df = zones.copy()
df["zone_id"] = df["zone_id"].str.strip().str.upper()
df = df.merge(
    hh[["zone_id", "total_households", "households_with_access"]], on="zone_id", how="left"
)
df = df.merge(risk[["zone_id", "risk_score"]], on="zone_id", how="left")
df = df.merge(req, on="zone_id", how="left")

assert len(df) == 12 and df["zone_id"].is_unique, "Integrated table is not one row per zone."
assert df[["total_households", "households_with_access", "risk_score", "valid_requests"]].notna().all().all()

print("\nValidated analysis table (inputs)")
print(
    df[
        [
            "zone_id",
            "zone_name",
            "total_households",
            "households_with_access",
            "risk_score",
            "valid_requests",
        ]
    ].to_string(index=False)
)

# Correction log
correction_log = pd.DataFrame(
    [
        {
            "issue": "Zone-code alias A-03 appears alongside A03",
            "evidence": corrections["alias"]["source"],
            "action": "Normalized A-03 to A03 in household, risk and SQL joins",
            "affected_records": "A03 household, risk and request rows",
            "impact": "Prevented a false missing zone and a dropped join",
            "residual_uncertainty": "None for this exercise",
        },
        {
            "issue": "Missing households_with_access for A06",
            "evidence": corrections["missing_access"]["source"],
            "action": "Applied verified value 350",
            "affected_records": "A06",
            "impact": "A06 service gap is computable instead of missing",
            "residual_uncertainty": "Value is simulated verification evidence",
        },
        {
            "issue": "Impossible access count 1220 for A11 (total 780)",
            "evidence": corrections["erroneous_access"]["source"],
            "action": "Replaced 1220 with verified 220",
            "affected_records": "A11",
            "impact": "Corrected an impossible 156% access rate",
            "residual_uncertainty": "None for this exercise",
        },
        {
            "issue": "Duplicate household row for A07",
            "evidence": "household_access.csv: two identical A07 rows",
            "action": "Kept one row after confirming identical values",
            "affected_records": "A07",
            "impact": "Prevented double counting of households",
            "residual_uncertainty": "None",
        },
        {
            "issue": "Obsolete duplicate risk entry A09 = 96",
            "evidence": corrections["risk_duplicate"]["source"],
            "action": "Kept current A09 risk = 72 and removed 96",
            "affected_records": "A09",
            "impact": "Prevented an inflated risk component",
            "residual_uncertainty": "None for this exercise",
        },
        {
            "issue": "Duplicate request IDs",
            "evidence": "service_requests.sqlite: repeated request_id values",
            "action": "Counted COUNT(DISTINCT request_id) only",
            "affected_records": "A01, A03, A06 duplicates",
            "impact": "Prevented demand inflation",
            "residual_uncertainty": "None",
        },
        {
            "issue": "Ineligible request statuses",
            "evidence": "service_requests.sqlite status counts",
            "action": "Filtered to verified/open only",
            "affected_records": "cancelled and invalid rows",
            "impact": "Demand reflects active requests only",
            "residual_uncertainty": "None",
        },
    ]
)
print("\nCorrection log")
print(correction_log.to_string(index=False))

# ---------------------------------------------------------------------------
# 3. Spatial analysis and original ranking
# ---------------------------------------------------------------------------
assert df.crs is not None, "zones.geojson has no CRS."
zones_proj = df.to_crs(32651)  # UTM Zone 51N
centroids_proj = zones_proj.geometry.centroid
centroids_wgs84 = centroids_proj.to_crs(4326)
df["centroid_lon"] = centroids_wgs84.x.values
df["centroid_lat"] = centroids_wgs84.y.values
df["centroid_x_m"] = centroids_proj.x.values
df["centroid_y_m"] = centroids_proj.y.values

fac = facilities_raw.copy()
fac["longitude"] = pd.to_numeric(fac["longitude"], errors="coerce")
fac["latitude"] = pd.to_numeric(fac["latitude"], errors="coerce")
fac["status"] = fac["status"].str.strip().str.lower()
fac_gdf = gpd.GeoDataFrame(
    fac, geometry=gpd.points_from_xy(fac["longitude"], fac["latitude"]), crs=4326
).to_crs(32651)

operational = fac_gdf[fac_gdf["status"] == "operational"].copy()
assert len(operational) > 0, "No operational facility in the original scenario."


def nearest_facility(row, facilities: gpd.GeoDataFrame) -> pd.Series:
    distances = facilities.geometry.distance(row.geometry.centroid)
    idx = distances.idxmin()
    return pd.Series(
        {
            "nearest_facility_id": facilities.loc[idx, "facility_id"],
            "nearest_facility_name": facilities.loc[idx, "facility_name"],
            "distance_km": distances.loc[idx] / 1000.0,
        }
    )


nearest = zones_proj.apply(lambda row: nearest_facility(row, operational), axis=1)
for col in nearest.columns:
    df[col] = nearest[col].values

max_distance = df["distance_km"].max()
max_requests = df["valid_requests"].max()
df["service_gap"] = 100.0 * (1.0 - df["households_with_access"] / df["total_households"])
df["distance_score"] = (
    100.0 * df["distance_km"] / max_distance if max_distance > 0 else 0.0
)
df["demand_score"] = (
    100.0 * df["valid_requests"] / max_requests if max_requests > 0 else 0.0
)
df["priority"] = (
    0.45 * df["service_gap"]
    + 0.25 * df["risk_score"]
    + 0.20 * df["distance_score"]
    + 0.10 * df["demand_score"]
)

df = df.sort_values(["priority", "zone_id"], ascending=[False, True]).reset_index(drop=True)
df["rank"] = np.arange(1, len(df) + 1)

df["original_priority"] = df["priority"]
df["original_rank"] = df["rank"]
df["original_nearest_facility_id"] = df["nearest_facility_id"]
df["original_distance_km"] = df["distance_km"]
df["original_distance_score"] = df["distance_score"]

print("\nOriginal ranking")
print(
    df[
        [
            "rank",
            "zone_id",
            "zone_name",
            "service_gap",
            "risk_score",
            "distance_km",
            "distance_score",
            "valid_requests",
            "demand_score",
            "priority",
            "nearest_facility_id",
        ]
    ].round(3).to_string(index=False)
)

original_top3 = df.head(3)[["zone_id", "zone_name", "priority"]].copy()
print("\nOriginal top three")
print(original_top3.round(2).to_string(index=False))

# ---------------------------------------------------------------------------
# 4. Charts
# ---------------------------------------------------------------------------
sns.set_theme(style="whitegrid", context="notebook")

plot_df = df.sort_values("priority", ascending=True)
colors = ["#d62728" if r <= 3 else "#4c78a8" for r in plot_df["rank"]]
fig1, ax1 = plt.subplots(figsize=(10, 6.2))
bars = ax1.barh(
    plot_df["zone_id"] + "  " + plot_df["zone_name"],
    plot_df["priority"],
    color=colors,
    edgecolor="white",
)
for bar, value in zip(bars, plot_df["priority"]):
    ax1.text(value + 1.0, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontsize=9)
ax1.set_xlim(0, 100)
ax1.set_xlabel("Priority score (0–100)")
ax1.set_ylabel("Zone (barangay)")
ax1.set_title("Original priority ranking of the 12 synthetic study catchments")
ax1.legend(
    handles=[
        plt.Rectangle((0, 0), 1, 1, color="#d62728", label="Top three"),
        plt.Rectangle((0, 0), 1, 1, color="#4c78a8", label="Other zones"),
    ],
    loc="lower right",
    frameon=True,
)
fig1.tight_layout()
fig1.savefig(FIG_DIR / "chart1_priority_ranking.png", dpi=160)
plt.close(fig1)

fig2, ax2 = plt.subplots(figsize=(10, 6.2))
scatter = ax2.scatter(
    df["service_gap"],
    df["valid_requests"],
    s=df["total_households"] / 5.0,
    c=df["priority"],
    cmap="viridis",
    edgecolor="black",
    linewidth=0.6,
    alpha=0.85,
)
for _, row in df.iterrows():
    ax2.annotate(
        row["zone_id"],
        (row["service_gap"], row["valid_requests"]),
        xytext=(5, 4),
        textcoords="offset points",
        fontsize=9,
    )
cbar = fig2.colorbar(scatter, ax=ax2)
cbar.set_label("Priority score (0–100)")
ax2.set_xlabel("Household service gap (%)")
ax2.set_ylabel("Eligible requests (distinct request IDs)")
ax2.set_title("Service gap vs. eligible demand (marker size = total households)")
fig2.tight_layout()
fig2.savefig(FIG_DIR / "chart2_gap_vs_demand.png", dpi=160)
plt.close(fig2)

# ---------------------------------------------------------------------------
# 5. Folium map
# ---------------------------------------------------------------------------
map_df = df.to_crs(4326).copy()
geojson_data = json.loads(map_df.to_json())

vmin = float(df["priority"].min())
vmax = float(df["priority"].max())
cmap = LinearColormap(
    ["#2c7bb6", "#ffffbf", "#d7191c"],
    vmin=vmin,
    vmax=vmax,
    caption="Priority score (0–100)",
)


def style_function(feature):
    value = feature["properties"]["priority"]
    return {
        "fillColor": cmap(value),
        "color": "#333333",
        "weight": 1.0,
        "fillOpacity": 0.68,
    }


m = folium.Map(
    location=[float(df["centroid_lat"].mean()), float(df["centroid_lon"].mean())],
    zoom_start=11,
    tiles="CartoDB positron",
    control_scale=True,
)

zones_layer = folium.FeatureGroup(name="Synthetic study catchments", show=True)
folium.GeoJson(
    geojson_data,
    name="Study catchments",
    style_function=style_function,
    highlight_function=lambda feature: {"weight": 3, "color": "#111111", "fillOpacity": 0.85},
    tooltip=folium.GeoJsonTooltip(
        fields=["zone_id", "zone_name", "priority", "rank", "service_gap", "risk_score", "valid_requests", "distance_km", "nearest_facility_id"],
        aliases=[
            "Zone",
            "Barangay",
            "Priority",
            "Rank",
            "Service gap (%)",
            "Risk",
            "Eligible requests",
            "Distance to facility (km)",
            "Nearest facility",
        ],
        localize=True,
        sticky=False,
    ),
    popup=folium.GeoJsonPopup(
        fields=[
            "zone_id",
            "zone_name",
            "total_households",
            "households_with_access",
            "service_gap",
            "risk_score",
            "valid_requests",
            "distance_km",
            "distance_score",
            "demand_score",
            "priority",
            "rank",
            "nearest_facility_id",
            "nearest_facility_name",
        ],
        aliases=[
            "Zone",
            "Barangay",
            "Total households",
            "Households with access",
            "Service gap (%)",
            "Risk score",
            "Eligible requests",
            "Distance (km)",
            "Distance score",
            "Demand score",
            "Priority score",
            "Rank",
            "Nearest facility",
            "Facility name",
        ],
        localize=True,
    ),
).add_to(zones_layer)
zones_layer.add_to(m)

labels_layer = folium.FeatureGroup(name="Zone labels", show=True)
for _, row in df.iterrows():
    folium.Marker(
        location=[row["centroid_lat"], row["centroid_lon"]],
        icon=folium.DivIcon(
            html=(
                '<div style="font-size:10px;font-weight:700;color:#111;'
                'text-shadow:0 0 3px #fff,0 0 3px #fff;white-space:nowrap;">'
                f'{row["zone_id"]} {row["zone_name"]}</div>'
            ),
            icon_size=(0, 0),
            icon_anchor=(0, 0),
        ),
    ).add_to(labels_layer)
labels_layer.add_to(m)

facilities_layer = folium.FeatureGroup(name="Fictional assistance facilities", show=True)
fac_map = fac_gdf.to_crs(4326)
for _, row in fac_map.iterrows():
    status = row["status"]
    color = "green" if status == "operational" else "red"
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        tooltip=f"{row['facility_id']}: {row['facility_name']} ({status})",
        popup=folium.Popup(
            f"<b>{row['facility_id']} — {row['facility_name']}</b><br>"
            f"Status: <b>{status}</b><br>"
            "<i>Fictional assistance hub; not an actual LGU facility.</i>",
            max_width=320,
        ),
        icon=folium.Icon(color=color, icon="info-sign"),
    ).add_to(facilities_layer)
facilities_layer.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

legend_html = f"""
<div style="position: fixed; bottom: 28px; left: 28px; z-index: 9999;
            background: white; padding: 10px 12px; border: 1px solid #444;
            border-radius: 6px; font-size: 12px; line-height: 1.45; max-width: 340px;
            box-shadow: 0 1px 4px rgba(0,0,0,.25);">
  <b>Priority score</b><br>
  <div style="height: 12px; width: 220px; border: 1px solid #999;
              background: linear-gradient(to right, #2c7bb6, #ffffbf, #d7191c);"></div>
  <div style="display: flex; justify-content: space-between; width: 220px;">
    <span>{vmin:.1f}</span><span>{vmax:.1f}</span>
  </div>
  <b>Facilities</b><br>
  <span style="color: green;">&#9679;</span> Operational &nbsp;
  <span style="color: red;">&#9679;</span> Non-operational<br>
  <i>Synthetic 350 m study catchments around approximate reference points.
  These are not official barangay boundaries. All statistics and facilities
  are simulated for CPE15 teaching purposes.</i>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

title_html = """
<div style="position: fixed; top: 12px; left: 50px; z-index: 9999;
            background: white; padding: 10px 14px; border: 1px solid #444;
            border-radius: 6px; font-size: 14px; line-height: 1.35;
            box-shadow: 0 1px 4px rgba(0,0,0,.25);">
  <b>Operation Blank Map — Lucban, Quezon</b><br>
  Priority deployment screening: original scenario<br>
  <span style="font-size: 11px;">Synthetic catchments; not official barangay boundaries.</span>
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

bounds = map_df.total_bounds
m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

map_path = OUT_DIR / f"CPE15_{STUDENT_ID}_FINAL_MAP.html"
m.save(str(map_path))
print(f"\nSaved map: {map_path}")

# ---------------------------------------------------------------------------
# 6. Draft decision memo (revised section pending the sealed update)
# ---------------------------------------------------------------------------
top3 = df.head(3)
body_paragraphs = [
    (
        "This memo screens the twelve synthetic 350 m study catchments in Lucban, "
        "Quezon for three hypothetical mobile digital assistance deployments. All "
        "household, risk, request and facility values are simulated teaching data; "
        "the catchments are not official barangay boundaries."
    ),
    (
        "After validating the evidence, the original top three are "
        f"{top3.iloc[0]['zone_id']} {top3.iloc[0]['zone_name']} "
        f"(priority {top3.iloc[0]['priority']:.1f}), "
        f"{top3.iloc[1]['zone_id']} {top3.iloc[1]['zone_name']} "
        f"(priority {top3.iloc[1]['priority']:.1f}), and "
        f"{top3.iloc[2]['zone_id']} {top3.iloc[2]['zone_name']} "
        f"(priority {top3.iloc[2]['priority']:.1f}). "
        "The ranking is driven mainly by the 45% household service-gap component, "
        "with risk and distance providing the main separation between close zones."
    ),
    (
        "The sealed operational update has not yet been applied in this draft. "
        "The revised top three, the affected facility, and the recomputed distance "
        "normalization must be inserted after the official update is released."
    ),
    (
        "Limitations: distances are straight-line centroid-to-facility measurements, "
        "not road travel times; the weights are supplied examination policy, not real "
        "government policy; and the underlying statistics are fictional. Confidence "
        "in the original ranking is moderate because several zones are close in score "
        "and small data corrections can change the order. The final recommendation "
        "should be treated as a transparent screening exercise, not an operational "
        "needs assessment."
    ),
]
body_text = " ".join(body_paragraphs)
word_count = len(re.findall(r"\b\w+\b", body_text))
print(f"\nDraft memo body word count: {word_count}")

pdf_path = OUT_DIR / f"CPE15_{STUDENT_ID}_DECISION.pdf"
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="MemoTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="MemoMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor="#333333",
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="MemoBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.6,
        leading=12.6,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
)

doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=letter,
    leftMargin=0.9 * inch,
    rightMargin=0.9 * inch,
    topMargin=0.8 * inch,
    bottomMargin=0.8 * inch,
    title=f"CPE15 Decision Memo - {STUDENT_ID}",
    author=STUDENT_NAME,
)
story = [
    Paragraph("CPE15 Decision Memo — Operation Blank Map", styles["MemoTitle"]),
    Paragraph(
        f"{STUDENT_NAME} &nbsp;|&nbsp; Student ID {STUDENT_ID} &nbsp;|&nbsp; "
        f"Section {SECTION} &nbsp;|&nbsp; {COURSE} &nbsp;|&nbsp; {MEMO_DATE}",
        styles["MemoMeta"],
    ),
]
for paragraph in body_paragraphs:
    story.append(Paragraph(paragraph, styles["MemoBody"]))
story.append(Spacer(1, 8))
story.append(
    Paragraph(
        f"<i>Memo body word count: {word_count} (limit 350, excluding identification heading).</i>",
        styles["MemoMeta"],
    )
)
doc.build(story)
print(f"Saved memo: {pdf_path}")

# ---------------------------------------------------------------------------
# 7. Processed CSV and supporting ZIP
# ---------------------------------------------------------------------------
# Revised columns default to original until the sealed update is applied.
df["revised_priority"] = df["original_priority"]
df["revised_rank"] = df["original_rank"]
df["revised_nearest_facility_id"] = df["original_nearest_facility_id"]
df["revised_distance_km"] = df["original_distance_km"]
df["revised_distance_score"] = df["original_distance_score"]
df["update_affected"] = False
df["final_priority"] = df["revised_priority"]
df["final_rank"] = df["revised_rank"]

csv_columns = [
    "zone_id",
    "zone_name",
    "psgc_code",
    "total_households",
    "households_with_access",
    "service_gap",
    "risk_score",
    "valid_requests",
    "nearest_facility_id",
    "nearest_facility_name",
    "distance_km",
    "distance_score",
    "demand_score",
    "original_priority",
    "original_rank",
    "revised_priority",
    "revised_rank",
    "revised_nearest_facility_id",
    "revised_distance_km",
    "revised_distance_score",
    "update_affected",
    "final_priority",
    "final_rank",
]
csv_path = OUT_DIR / f"CPE15_{STUDENT_ID}_PROCESSED.csv"
df[csv_columns].to_csv(csv_path, index=False, float_format="%.4f")
print(f"Saved CSV: {csv_path}")

zip_path = OUT_DIR / f"CPE15_{STUDENT_ID}_SUPPORTING.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.write(map_path, arcname=map_path.name)
    archive.write(csv_path, arcname=csv_path.name)
print(f"Saved ZIP: {zip_path}")

print("\nFinal checklist")
print("  [PASS] 12 zones in integrated table")
print("  [PASS] One row per zone")
print("  [PASS] Corrections applied and logged")
print("  [PASS] SQL DISTINCT eligible requests")
print("  [PASS] Projected CRS EPSG:32651")
print("  [PASS] Two charts generated")
print("  [PASS] Standalone Folium HTML generated")
print("  [PASS] Processed CSV generated")
print("  [PASS] Decision PDF generated")
print("  [PASS] Supporting ZIP contains HTML + CSV")
print("  [PENDING] Sealed operational update and revised ranking")
