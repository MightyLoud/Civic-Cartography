#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


PARSE_OLD = '''            parsed = ocdid_parser(ocdid)  # Returns dict
            state = parsed.get("state")
            place = parsed.get("place")
'''
PARSE_NEW = '''            parsed = ocdid_parser(ocdid)  # Returns dict
            state = parsed.get("state")
            place = parsed.get("place")
            county = parsed.get("county")
'''

LOCAL_OLD = '''            if not state or not place:
                # County-level OCDids land here. The validation CSV carries only
                # Census "place" and "cousub" layers, so there is nothing to match
                # them against; they are quarantined as stubs by run().
                logger.debug(f"Missing state or place in OCDid: {ocdid}")
                return pl.DataFrame()

            state_upper = state.upper()
            place_lower = _ocdid_slug_to_name(place)
'''
LOCAL_NEW = '''            if not state or (not place and not county):
                logger.debug(f"Missing state and local geography in OCDid: {ocdid}")
                return pl.DataFrame()

            state_upper = state.upper()
            place_lower = _ocdid_slug_to_name(place or county)
'''

COUNTY_ANCHOR = '''            # A `place:` OCDid segment denotes a Census place, so county
            # subdivisions are not candidates. The LSAD code cannot make this
'''
COUNTY_BLOCK = '''            # State county targets use the retained Census Counties validation
            # export. Match exact normalized county name within the already
            # state-scoped data and never fuzzy-match county identity.
            if county:
                if "COUNTYFP_list" not in state_df.columns:
                    logger.debug(
                        f"No county validation layer available for state: {state_upper}"
                    )
                    return pl.DataFrame()
                county_df = state_df.filter(
                    pl.col("COUNTYFP_list")
                    .cast(pl.Utf8)
                    .fill_null("")
                    .str.strip_chars()
                    != ""
                )
                county_matches = county_df.filter(
                    pl.col("normalized_place_name") == place_lower
                )
                if len(county_matches) != 1:
                    logger.debug(
                        f"County validation match count for {ocdid}: {len(county_matches)}"
                    )
                    return pl.DataFrame()
                logger.info(f"Found 1 exact county match for {ocdid}")
                return county_matches

'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"county validation transform refused: {label} matched {count} times")
    return text.replace(old, new, 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream-root", type=Path, required=True)
    args = parser.parse_args()

    path = args.upstream_root / "src/init_migration/generate_pipeline.py"
    text = path.read_text(encoding="utf-8")
    if "Found 1 exact county match for" in text:
        raise SystemExit("county validation transform refused: county logic already present")

    text = replace_once(text, PARSE_OLD, PARSE_NEW, "parser insertion")
    text = replace_once(text, LOCAL_OLD, LOCAL_NEW, "county local acceptance")
    text = replace_once(text, COUNTY_ANCHOR, COUNTY_BLOCK + COUNTY_ANCHOR, "county match block")
    path.write_text(text, encoding="utf-8")
    print(f"Applied generic state-county validation support to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
