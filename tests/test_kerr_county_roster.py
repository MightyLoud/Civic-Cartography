import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data/raw/kerr-county/current-elected-offices.csv"
TRANSITION = ROOT / "data/raw/kerr-county/district-clerk-transition.csv"
NON_SCOPE = ROOT / "data/raw/kerr-county/non-scope-offices.csv"
MANIFEST = ROOT / "data/raw/kerr-county/source-manifest.csv"
CONTRACT = ROOT / "data/raw/kerr-county/gis-source-contract.json"
NORMALIZED = ROOT / "data/normalized/kerr_county_elected_offices.csv"
PRECINCTS = ROOT / "data/geojson/kerr_county_commissioner_precincts.geojson"
COUNTY = ROOT / "data/geojson/kerr_county_countywide.geojson"


def test_kerr_county_judicial_appointment_and_geometry_contract() -> None:
    expected = {
        "County Judge": "Rob Kelly",
        "County Commissioner Precinct 1": "Tom Jones",
        "County Commissioner Precinct 2": "Rich Paces",
        "County Commissioner Precinct 3": "Jeff Holt",
        "County Commissioner Precinct 4": "Don Harris",
        "Sheriff": "Larry L. Leitha Jr.",
        "County Clerk": "Nadene Alford",
        "District Clerk": "Eunavae Baublit Tonroy",
        "Tax Assessor-Collector": "Bob Reeves",
        "County Treasurer": "Tracy Soldan",
    }
    with ROSTER.open(newline="", encoding="utf-8") as handle:
        roster = list(csv.DictReader(handle))
    assert len(roster) == 10
    assert {row["office_name"]: row["officeholder"] for row in roster} == expected
    assert len({row["officeholder"] for row in roster}) == 10
    assert [row["selection_method"] for row in roster].count("election") == 9
    assert [row["selection_method"] for row in roster].count("judicial_appointment") == 1
    appointed = next(row for row in roster if row["selection_method"] == "judicial_appointment")
    assert appointed["office_name"] == "District Clerk"
    assert appointed["officeholder"] == "Eunavae Baublit Tonroy"
    assert "Dawn Lantz" in appointed["notes"]
    assert "M. Patrick Maguire" in appointed["notes"]
    assert "Albert D. Pattillo III" in appointed["notes"]
    assert sum(row["office_name"] == "District Clerk" for row in roster) == 1

    with TRANSITION.open(newline="", encoding="utf-8") as handle:
        transition = list(csv.DictReader(handle))
    assert len(transition) == 1
    row = transition[0]
    assert row["office_status"] == "elected_office"
    assert row["selection_method"] == "judicial_appointment"
    assert row["predecessor"] == "Dawn Lantz"
    assert row["predecessor_last_day"] == "2026-03-31"
    assert row["appointment_announced_date"] == "2026-03-16"
    assert row["current_service_start"] == "2026-04-01"
    assert row["statutory_authority"] == "Texas Government Code § 51.301"

    with NON_SCOPE.open(newline="", encoding="utf-8") as handle:
        non_scope = list(csv.DictReader(handle))
    surveyor = next(row for row in non_scope if row["office_name"] == "County Surveyor")
    assert surveyor["current_officeholder"] == "Lee C. Voelkel"
    assert "bounded county release" in surveyor["exclusion_reason"]
    assert "County Surveyor" not in expected

    with NORMALIZED.open(newline="", encoding="utf-8") as handle:
        normalized = list(csv.DictReader(handle))
    assert len(normalized) == 5
    assert {row["qa_status"] for row in normalized} == {"approved"}
    assert {row["parity_ok"] for row in normalized} == {"TRUE"}
    assert {row["district_id"] for row in normalized} == {"COUNTYWIDE", "1", "2", "3", "4"}
    assert len({row["geometry_id"] for row in normalized}) == 5
    countywide = next(row for row in normalized if row["district_type"] == "countywide")
    assert countywide["office_name"] == (
        "County Judge + Sheriff + County Clerk + District Clerk + "
        "Tax Assessor-Collector + County Treasurer"
    )
    assert "joint judicial appointment" in countywide["notes"]
    for officeholder in (
        "Rob Kelly",
        "Larry L. Leitha Jr.",
        "Nadene Alford",
        "Eunavae Baublit Tonroy",
        "Bob Reeves",
        "Tracy Soldan",
    ):
        assert officeholder in countywide["notes"]
    commissioner_rows = [row for row in normalized if row["district_type"] == "commissioner_precinct"]
    assert len(commissioner_rows) == 4
    assert {row["geometry_source_url"] for row in commissioner_rows} == {
        "https://services1.arcgis.com/Ijqs2ihddUy84otW/ArcGIS/rest/services/"
        "Kerr_County_Commissioner_Precincts_2022/FeatureServer/0"
    }
    assert all("Court Order 39047" in row["notes"] for row in commissioner_rows)
    assert all("January 1, 2022" in row["notes"] for row in commissioner_rows)

    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        manifest = {row["source_id"]: row for row in csv.DictReader(handle)}
    assert len(manifest) == 18
    required = {
        "kerr-commissioners-court",
        "kerr-elections-current-officeholders",
        "kerr-sheriff-biography",
        "kerr-county-clerk",
        "kerr-county-clerk-2024-appointment-expiry",
        "kerr-district-clerk-current",
        "kerr-district-clerk-appointment",
        "kerr-bail-bond-board",
        "texas-government-code-51-301",
        "texas-sos-2026-office-qualifications",
        "kerr-tax-assessor",
        "kerr-treasurer",
        "kerr-county-surveyor",
        "kerr-arcgis-service-item",
        "kerr-arcgis-precinct-layer",
        "census-kerr-county",
    }
    assert required.issubset(manifest)
    assert "Dawn Lantz" in manifest["kerr-elections-current-officeholders"]["use"]
    assert "December 31, 2024" in manifest["kerr-county-clerk-2024-appointment-expiry"]["use"]
    assert "joint selection" in manifest["kerr-district-clerk-appointment"]["use"]
    assert "outside the bounded ten-office release" in manifest["kerr-county-surveyor"]["use"]

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["service_item_id"] == "de7c8e02045a4981a752998bb6406538"
    assert contract["operational_layer_id"] == 0
    assert contract["district_field"] == "precinct"
    assert contract["district_values"] == ["1", "2", "3", "4"]
    assert contract["resolved_from_county_elections_page"] is True
    assert {str(row["order_num"]) for row in contract["source_rows"]} == {"39047"}
    assert {row["order_date"] for row in contract["source_rows"]} == {1635919200000}
    assert {row["effective_date"] for row in contract["source_rows"]} == {1641016800000}

    county = json.loads(COUNTY.read_text(encoding="utf-8"))
    assert len(county["features"]) == 1
    county_props = county["features"][0]["properties"]
    assert county_props["record_id"] == "TX:county:kerr:countywide:COUNTYWIDE"
    assert county_props["geometry_id"] == "kerr-county-countywide"
    assert county_props["census_geoid"] == "48265"

    precincts = json.loads(PRECINCTS.read_text(encoding="utf-8"))
    assert len(precincts["features"]) == 4
    found = {}
    for feature in precincts["features"]:
        props = feature["properties"]
        district_id = str(props["district_id"])
        attrs = props["source_attributes"]
        assert props["source_district_field"] == "precinct"
        assert str(attrs["precinct"]) == district_id
        assert attrs["order_num"] == "39047"
        assert attrs["order_date"] == 1635919200000
        assert attrs["effective_date"] == 1641016800000
        found[district_id] = props["geometry_id"]
    assert found == {
        "1": "kerr-county-commissioner-precinct-1",
        "2": "kerr-county-commissioner-precinct-2",
        "3": "kerr-county-commissioner-precinct-3",
        "4": "kerr-county-commissioner-precinct-4",
    }

    digest = hashlib.sha256()
    for path in sorted((COUNTY, PRECINCTS), key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    assert digest.hexdigest() == "c55276bef1b02f6f0de42f000e20f0218a7ee83b4ea95f0304ea921ddbfa5a4c"
