import csv
import json
from pathlib import Path

from scripts.validate_geojson import validate_join


def write_normalized(path: Path, geometry_id: str = "olmos-park-citywide") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["record_id", "geometry_id"])
        writer.writeheader()
        writer.writerow(
            {
                "record_id": "TX:municipality:olmos-park:at_large:CITYWIDE",
                "geometry_id": geometry_id,
            }
        )


def write_geojson(
    path: Path,
    *,
    geometry_id: str = "olmos-park-citywide",
    record_id: str = "TX:municipality:olmos-park:at_large:CITYWIDE",
    duplicate: bool = False,
) -> None:
    feature = {
        "type": "Feature",
        "properties": {"geometry_id": geometry_id, "record_id": record_id},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[-98.49, 29.47], [-98.48, 29.47], [-98.49, 29.47]]
            ],
        },
    }
    features = [feature, feature] if duplicate else [feature]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}),
        encoding="utf-8",
    )


def test_matching_geometry_join_passes(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    geojson = tmp_path / "geojson"
    write_normalized(normalized / "olmos.csv")
    write_geojson(geojson / "olmos.geojson")

    assert validate_join(normalized, geojson) == []


def test_missing_geometry_is_reported(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    geojson = tmp_path / "geojson"
    write_normalized(normalized / "olmos.csv")

    errors = validate_join(normalized, geojson)

    assert any("missing from GeoJSON" in error for error in errors)


def test_duplicate_geometry_id_is_reported(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    geojson = tmp_path / "geojson"
    write_normalized(normalized / "olmos.csv")
    write_geojson(geojson / "olmos.geojson", duplicate=True)

    errors = validate_join(normalized, geojson)

    assert any("duplicate geometry_id" in error for error in errors)


def test_record_id_mismatch_is_reported(tmp_path: Path) -> None:
    normalized = tmp_path / "normalized"
    geojson = tmp_path / "geojson"
    write_normalized(normalized / "olmos.csv")
    write_geojson(geojson / "olmos.geojson", record_id="wrong-record")

    errors = validate_join(normalized, geojson)

    assert any("record_id mismatch" in error for error in errors)
