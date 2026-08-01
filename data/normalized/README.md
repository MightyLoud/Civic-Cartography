# Normalized Data

Store standardized UTF-8 CSV datasets here. Files in this directory are validation inputs and should be reproducible from raw sources and transformation logic.

Each CSV must follow `docs/data-model.md` and pass `python scripts/validate.py` before publication.

Do not hand-edit generated output unless the correction is also represented in the upstream transformation or documented as an explicit reviewed exception.
