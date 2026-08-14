from __future__ import annotations

import pytest

import scripts.validate_schleicher_live_pages_resilient as validator


def page(text: str) -> validator.PageResult:
    return validator.PageResult(
        text=text,
        request_url="https://example.test/page",
        status=200,
        content_type="text/html; charset=utf-8",
        body_sha256="a" * 64,
        body_bytes=len(text.encode("utf-8")),
    )


def civicweb_shell() -> validator.PageResult:
    return page(
        """
        <!DOCTYPE html><html><head>
        <link rel="shortcut icon" href="/runtime/images/favicon.ico" />
        </head><body><form>
        <input name="__VIEWSTATE" />
        <input name="__EVENTVALIDATION" />
        <script src="/WebResource.axd"></script>
        <script src="/ScriptResource.axd"></script>
        </form></body></html>
        """
    )


def test_treasurer_generic_shell_is_recorded_as_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(validator, "fetch_once", lambda _url, _attempt: civicweb_shell())

    status = validator.validate_contract(
        validator.TREASURER_URL,
        ("Jennifer L. Henderson",),
        attempts=3,
        sleep=lambda _seconds: None,
    )

    assert status.status == "unavailable"
    assert status.authority_effect == "none"
    assert status.missing_markers == ("Jennifer L. Henderson",)


def test_populated_treasurer_change_still_fails_closed(monkeypatch) -> None:
    changed = page(
        "County Treasurer office hours phone: 325-555-0100. "
        "Current Treasurer: Another Person"
    )
    monkeypatch.setattr(validator, "fetch_once", lambda _url, _attempt: changed)

    with pytest.raises(SystemExit, match="lost markers"):
        validator.validate_contract(
            validator.TREASURER_URL,
            ("Jennifer L. Henderson",),
            attempts=2,
            sleep=lambda _seconds: None,
        )


def test_generic_shell_on_other_office_route_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(validator, "fetch_once", lambda _url, _attempt: civicweb_shell())

    with pytest.raises(SystemExit, match="lost markers"):
        validator.validate_contract(
            "https://www.schleichercounty.gov/page/Sheriff",
            ("Jason Chatham",),
            attempts=2,
            sleep=lambda _seconds: None,
        )


def test_retained_marker_verifies_page(monkeypatch) -> None:
    verified = page("County Treasurer Jennifer L. Henderson")
    monkeypatch.setattr(validator, "fetch_once", lambda _url, _attempt: verified)

    status = validator.validate_contract(
        validator.TREASURER_URL,
        ("Jennifer L. Henderson",),
        attempts=1,
        sleep=lambda _seconds: None,
    )

    assert status.status == "verified"
    assert status.missing_markers == ()


def test_unavailable_http_status_preserves_fail_soft_behavior(monkeypatch) -> None:
    monkeypatch.setattr(validator, "fetch_once", lambda _url, _attempt: None)

    status = validator.validate_contract(
        "https://example.test/page",
        ("Expected Marker",),
        attempts=1,
        sleep=lambda _seconds: None,
    )

    assert status.status == "unavailable"
    assert status.authority_effect == "none"
