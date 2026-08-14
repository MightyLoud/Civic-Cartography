from __future__ import annotations

import pytest

import scripts.validate_schleicher_live_pages as live_pages


def result(text: str, attempt: int = 1) -> live_pages.PageResult:
    return live_pages.PageResult(
        text=text,
        request_url=live_pages.cache_busted_url(
            "https://example.test/page/Treasurer", attempt
        ),
        status=200,
        content_type="text/html; charset=utf-8",
    )


def test_cache_busted_url_preserves_existing_query() -> None:
    url = live_pages.cache_busted_url(
        "https://example.test/page/Treasurer?language=en", 3
    )

    assert "language=en" in url
    assert "_cc_contract_attempt=3" in url
    assert "_cc_contract_transport=html" in url


def test_live_page_contract_retries_incomplete_http_success(monkeypatch) -> None:
    responses = iter(
        [
            result("<html><body>County Treasurer</body></html>", 1),
            result(
                "<html><body>County Treasurer Jennifer L. Henderson</body></html>",
                2,
            ),
        ]
    )
    attempts = []
    sleeps = []

    def fake_fetch(_url: str, attempt: int):
        attempts.append(attempt)
        return next(responses)

    monkeypatch.setattr(live_pages, "fetch_once", fake_fetch)
    monkeypatch.setattr(live_pages.time, "sleep", sleeps.append)

    page = live_pages.fetch_contract_page(
        "https://example.test/page/Treasurer",
        ("Jennifer L. Henderson",),
        attempts=2,
    )

    assert page is not None
    assert "Jennifer L. Henderson" in page.text
    assert attempts == [1, 2]
    assert sleeps == [3]


def test_live_page_contract_fails_closed_with_bounded_diagnostics(monkeypatch) -> None:
    monkeypatch.setattr(
        live_pages,
        "fetch_once",
        lambda _url, attempt: result("<html>County Treasurer</html>", attempt),
    )
    monkeypatch.setattr(live_pages.time, "sleep", lambda _seconds: None)

    with pytest.raises(SystemExit, match="did not satisfy") as error:
        live_pages.fetch_contract_page(
            "https://example.test/page/Treasurer",
            ("Jennifer L. Henderson",),
            attempts=3,
        )

    message = str(error.value)
    assert "status=200" in message
    assert "sha256=" in message
    assert "missing=['Jennifer L. Henderson']" in message
    assert "attempt=1" in message
    assert "attempt=3" in message


def test_live_page_contract_preserves_unavailable_page_behavior(monkeypatch) -> None:
    monkeypatch.setattr(live_pages, "fetch_once", lambda _url, _attempt: None)

    assert (
        live_pages.fetch_contract_page(
            "https://example.test/page/Treasurer",
            ("Jennifer L. Henderson",),
        )
        is None
    )


def test_live_page_contract_retries_transport_error(monkeypatch) -> None:
    calls = []
    sleeps = []

    def fake_fetch(_url: str, attempt: int):
        calls.append(attempt)
        if attempt == 1:
            raise OSError("temporary reset")
        return result("Jennifer L. Henderson", attempt)

    monkeypatch.setattr(live_pages, "fetch_once", fake_fetch)
    monkeypatch.setattr(live_pages.time, "sleep", sleeps.append)

    page = live_pages.fetch_contract_page(
        "https://example.test/page/Treasurer",
        ("Jennifer L. Henderson",),
        attempts=2,
    )

    assert page is not None
    assert calls == [1, 2]
    assert sleeps == [3]
