import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/raw/el-paso-county/current-elected-offices.csv"
MANIFEST = ROOT / "data/raw/el-paso-county/source-manifest.csv"
NORMALIZED = ROOT / "data/normalized/el_paso_county_elected_offices.csv"
PRECINCTS = ROOT / "data/geojson/el_paso_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/el_paso_county_countywide.geojson"
LAYER = "https://maps.epcounty.com/arcgis/rest/services/Website_Basemap/MapServer/10"


def test_el_paso_county_bilingual_alias_and_portal_geometry_contract() -> None:
    expected = {
        "County Judge": "Ricardo A. Samaniego",
        "County Commissioner Precinct 1": "Jacqueline Butler",
        "County Commissioner Precinct 2": "David Stout",
        "County Commissioner Precinct 3": "Iliana Holguin",
        "County Commissioner Precinct 4": "Sergio Coronado",
        "Sheriff": "Oscar Ugarte",
        "County Clerk": "Delia Briones",
        "District Clerk": "Norma Favela Barceleau",
        "Tax Assessor-Collector": "Ruben P. Gonzalez",
    }

    with EVIDENCE.open(newline="", encoding="utf-8") as handle:
        evidence = list(csv.DictReader(handle))
    assert len(evidence) == 9
    assert {row["office_name"]: row["officeholder"] for row in evidence} == expected
    assert len({row["officeholder"] for row in evidence}) == 9
    assert {row["geography_id"] for row in evidence} == {"COUNTYWIDE", "1", "2", "3", "4"}
    alias_note = next(row["notes"] for row in evidence if row["geography_id"] == "1")
    assert "Jacqueline Butler" in alias_note
    assert "Jackie Butler" in alias_note
    assert not any(row["office_name"] == "County Treasurer" for row in evidence)

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 18
    assert "Jacqueline Butler" in manifest["el-paso-commissioner-1"]["use"]
    assert "Jackie Butler" in manifest["el-paso-commissioner-1"]["use"]
    assert "English/Spanish" in manifest["el-paso-commissioner-3"]["use"]
    assert "Spanish-language" in manifest["el-paso-commissioner-maps-es"]["use"]
    assert "0b4e626d91684cecb1e35828cf52092f" in manifest["el-paso-portal-item"]["url"]
    assert "Website_Basemap/MapServer/10" in manifest["el-paso-portal-item"]["use"]
    assert manifest["el-paso-operational-layer"]["url"] == LAYER
    assert "does not list a County Treasurer" in manifest["el-paso-elected-officials"]["use"]

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_id"] == "COUNTYWIDE")
    for office in ("County Judge", "Sheriff", "County Clerk", "District Clerk", "Tax Assessor-Collector"):
        assert office in countywide["office_name"]
    assert "does not list a County Treasurer" in countywide["notes"]
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["geometry_source_url"] for row in commissioner_rows} == {LAYER}

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:el_paso:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "el-paso-county-countywide"
    assert county_props["census_geoid"] == "48141"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        precinct_id = str(props["district_id"])
        attributes = props["source_attributes"]
        assert props["district_type"] == "commissioner_precinct"
        assert props["district_name"] == f"Commissioner Precinct {precinct_id}"
        assert props["source_layer"] == LAYER
        assert props["source_district_field"] == "Precinct"
        assert str(attributes["Precinct"]) == precinct_id
        found[precinct_id] = props["geometry_id"]
    assert found == {
        "1": "el-paso-county-commissioner-precinct-1",
        "2": "el-paso-county-commissioner-precinct-2",
        "3": "el-paso-county-commissioner-precinct-3",
        "4": "el-paso-county-commissioner-precinct-4",
    }
