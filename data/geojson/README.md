# GeoJSON Outputs

Store generated, map-ready GeoJSON here.

## Publication rules

- Generate outputs from validated normalized records and authoritative geometry sources.
- Use `geometry_id` as the documented join key.
- Preserve source attribution in feature properties or an adjacent manifest.
- Do not publish features with unresolved joins, duplicate identifiers, failed QA, or `parity_ok` other than `TRUE`.
- Prefer reproducible simplification and coordinate-precision settings over manual geometry edits.
