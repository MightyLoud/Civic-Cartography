import re


SCHEMA_VERSION = "atlas-representation-provider/0.1"
PASS = "PASS"
NO_APPLICABLE = "NO_APPLICABLE_REPRESENTATION"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ORG_ID_RE = re.compile(
    r"^org-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)
PERSON_ID_RE = re.compile(
    r"^per-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)


def _error(status, *errors):
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "errors": [str(error) for error in errors if str(error)],
        "canonical_writes": 0,
    }


def _valid_certification(value):
    if not isinstance(value, dict):
        return False
    return (
        value.get("status") == "certified"
        and value.get("raw_complete") is True
        and value.get("normalized_complete") is True
        and value.get("qa_passed") is True
        and value.get("parity_ok") is True
    )


def validate_provider_response(payload):
    errors = []
    if not isinstance(payload, dict):
        return ["RESPONSE_NOT_OBJECT"]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("SCHEMA_VERSION_UNSUPPORTED")
    if payload.get("canonical_writes") != 0:
        errors.append("CANONICAL_WRITES_FORBIDDEN")

    status = payload.get("status")
    if status not in {PASS, NO_APPLICABLE}:
        errors.append("STATUS_INVALID")
        return sorted(set(errors))
    if status == NO_APPLICABLE:
        return sorted(set(errors))

    source_system = payload.get("source_system")
    if not isinstance(source_system, str) or not source_system.strip():
        errors.append("SOURCE_SYSTEM_REQUIRED")

    manifest_hash = payload.get("snapshot_manifest_sha256")
    if not isinstance(manifest_hash, str) or not SHA256_RE.fullmatch(manifest_hash):
        errors.append("SNAPSHOT_MANIFEST_SHA256_INVALID")

    jurisdiction = payload.get("jurisdiction_ocdid")
    if not isinstance(jurisdiction, str) or not jurisdiction.startswith("ocd-jurisdiction/"):
        errors.append("JURISDICTION_OCDID_INVALID")

    divisions = payload.get("division_ocdids")
    if (
        not isinstance(divisions, list)
        or len(divisions) != len(set(divisions))
        or any(not isinstance(item, str) or not item.startswith("ocd-division/") for item in divisions)
    ):
        errors.append("DIVISION_OCDIDS_INVALID")
        divisions = []

    if not _valid_certification(payload.get("certification")):
        errors.append("CERTIFICATION_INVALID")

    offices = payload.get("offices")
    if not isinstance(offices, list):
        errors.append("OFFICES_INVALID")
        return sorted(set(errors))

    post_ids = set()
    for office in offices:
        if not isinstance(office, dict):
            errors.append("OFFICE_INVALID")
            continue
        post_id = office.get("post_id")
        if not isinstance(post_id, str) or not post_id:
            errors.append("POST_ID_REQUIRED")
        elif post_id in post_ids:
            errors.append("POST_ID_DUPLICATE")
        else:
            post_ids.add(post_id)

        role_id = office.get("role_id")
        office_name = office.get("office_name")
        division = office.get("division_ocdid")
        if not isinstance(role_id, str) or not role_id:
            errors.append("ROLE_ID_REQUIRED")
        if not isinstance(office_name, str) or not office_name:
            errors.append("OFFICE_NAME_REQUIRED")
        if not isinstance(division, str) or not division.startswith("ocd-division/"):
            errors.append("OFFICE_DIVISION_INVALID")
        elif divisions and division not in divisions:
            errors.append("OFFICE_DIVISION_OUT_OF_SCOPE")

        shared_org = office.get("shared_organization_id")
        if shared_org is not None and (
            not isinstance(shared_org, str) or not ORG_ID_RE.fullmatch(shared_org)
        ):
            errors.append("SHARED_ORGANIZATION_ID_INVALID")

        capacity = office.get("seat_capacity")
        vacancies = office.get("vacancy_count")
        holders = office.get("holders")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            errors.append("SEAT_CAPACITY_INVALID")
            capacity = None
        if isinstance(vacancies, bool) or not isinstance(vacancies, int) or vacancies < 0:
            errors.append("VACANCY_COUNT_INVALID")
            vacancies = None
        if not isinstance(holders, list):
            errors.append("HOLDERS_INVALID")
            holders = []

        holder_ids = set()
        for holder in holders:
            if not isinstance(holder, dict):
                errors.append("HOLDER_INVALID")
                continue
            person_id = holder.get("person_id")
            name = holder.get("name")
            if not isinstance(person_id, str) or not person_id:
                errors.append("HOLDER_PERSON_ID_REQUIRED")
            elif person_id in holder_ids:
                errors.append("HOLDER_PERSON_ID_DUPLICATE")
            else:
                holder_ids.add(person_id)
            if not isinstance(name, str) or not name:
                errors.append("HOLDER_NAME_REQUIRED")
            shared_person = holder.get("shared_person_id")
            if shared_person is not None and (
                not isinstance(shared_person, str) or not PERSON_ID_RE.fullmatch(shared_person)
            ):
                errors.append("SHARED_PERSON_ID_INVALID")

        if capacity is not None and vacancies is not None:
            if len(holders) + vacancies != capacity:
                errors.append("SEAT_PARITY_INVALID")

    return sorted(set(errors))


def resolve_representation(spatial_result, provider_url, fetch_json, timeout=10):
    if not provider_url:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "DISABLED",
            "canonical_writes": 0,
        }

    latitude = spatial_result.get("latitude")
    longitude = spatial_result.get("longitude")
    if latitude is None or longitude is None:
        return _error("NEEDS_LOCATION", "LATITUDE_LONGITUDE_REQUIRED")

    try:
        payload = fetch_json(
            provider_url,
            {
                "lat": latitude,
                "lon": longitude,
            },
            timeout=timeout,
        )
    except Exception as exc:
        return _error(
            "UNAVAILABLE",
            f"{type(exc).__name__}:{str(exc)[:160]}",
        )

    errors = validate_provider_response(payload)
    if errors:
        return _error("INVALID_RESPONSE", *errors)

    # Copy only the provider contract. It remains read-only enrichment and does
    # not alter Atlas provider/action routing state.
    return payload
