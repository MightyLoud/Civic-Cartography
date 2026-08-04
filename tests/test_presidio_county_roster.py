from pathlib import Path
import csv, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
EXPECTED_DIGEST="1175c70e85f15a26b212271e5c058ed4b42bf13911dfed955af8f398631d70d6"
def csv_rows(path):return list(csv.DictReader((ROOT/path).open(encoding="utf-8")))
def test_presidio_roster_and_mixed_contract():
 rows=csv_rows("data/raw/presidio-county/current-elected-offices.csv")
 assert len(rows)==10
 assert len({r["officeholder_name"] for r in rows})==10
 names={r["office_name"]:r["officeholder_name"] for r in rows}
 assert names["Sheriff"]=="Danny Dominguez"
 assert names["Tax Assessor-Collector"]=="Nancy Valdez Arevalo"
 assert names["District Clerk and County Clerk"]=="Carolina Catano"
 assert not any("Sheriff/Tax" in name for name in names)
 assert "County Clerk" not in names and "District Clerk" not in names
def test_presidio_geometry_contract_and_joins():
 contract=json.loads((ROOT/"data/raw/presidio-county/gis-source-contract.json").read_text())
 assert contract["commissioner_assignments"]=={"1":"1","2":"1","3":"2","4":"2","5":"3","6":"3","7":"4"}
 assert contract["interdistrict_overlap_area_degrees"]==0
 assert contract["union_symmetric_difference_area_degrees"]==0
 normalized=csv_rows("data/normalized/presidio_county_elected_offices.csv")
 assert len(normalized)==5 and all(r["qa_status"]=="approved" and r["parity_ok"]=="TRUE" for r in normalized)
 features=[]
 for filename in ("presidio_county_countywide.geojson","presidio_county_commissioner_precincts.geojson"):
  features.extend(json.loads((ROOT/"data/geojson"/filename).read_text())["features"])
 assert len(features)==5
 assert {f["properties"]["record_id"] for f in features}=={r["record_id"] for r in normalized}
def test_presidio_release_digest():
 h=hashlib.sha256()
 for path in sorted([ROOT/"data/geojson/presidio_county_countywide.geojson",ROOT/"data/geojson/presidio_county_commissioner_precincts.geojson"],key=lambda p:p.name):
  h.update(path.name.encode());h.update(b"\0");h.update(path.read_bytes());h.update(b"\0")
 assert h.hexdigest()==EXPECTED_DIGEST
