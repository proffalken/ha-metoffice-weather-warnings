"""Shared aioclient_mock helpers for mocking the NSWWS feed -> issued flow.

Confirmed against a live call: `/objects/feed` returns an Atom feed whose
rel="related" link points at the actual GeoJSON snapshot, under a URL
containing the feed's own UUID. There is no fixed "issued" path.
"""

from custom_components.metoffice_warnings.const import FEED_PATH

NSWWS_BASE_URL = "https://example-nswws.metoffice.gov.uk"
FEED_ID = "893ba1f8-730b-49b7-aa95-46f2c2a79421"


def issued_snapshot_url(base_url: str = NSWWS_BASE_URL) -> str:
    """Return the (fake) discovered issued-snapshot URL for a base URL."""
    return f"{base_url}/objects/issued/{FEED_ID}/"


def feed_xml(base_url: str = NSWWS_BASE_URL, related_href: str | None = None) -> str:
    """Build a minimal but realistic NSWWS Atom feed document."""
    href = related_href if related_href is not None else issued_snapshot_url(base_url)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        "<title>Met Office Warnings Feed</title>"
        f'<link rel="self" type="application/atom+xml" href="{base_url}{FEED_PATH}/"/>'
        f'<link rel="related" type="application/vnd.geo+json" href="{href}" '
        'title="Latest version of all issued warnings"/>'
        f"<id>urn:uuid:{FEED_ID}</id>"
        "<updated>2026-08-25T09:23:16Z</updated>"
        "</feed>"
    )


def feed_xml_without_related_link(base_url: str = NSWWS_BASE_URL) -> str:
    """A feed document missing the rel="related" link entirely."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        "<title>Met Office Warnings Feed</title>"
        f'<link rel="self" type="application/atom+xml" href="{base_url}{FEED_PATH}/"/>'
        f"<id>urn:uuid:{FEED_ID}</id>"
        "<updated>2026-08-25T09:23:16Z</updated>"
        "</feed>"
    )


def register_nswws(
    aioclient_mock, payload: dict, base_url: str = NSWWS_BASE_URL
) -> None:
    """Register mocks for a successful feed -> issued-snapshot round trip.

    Clears earlier mocks first: aioclient_mock keeps responses registered for
    the whole test, so a stale error response would otherwise keep matching."""
    aioclient_mock.clear_requests()
    snapshot_url = issued_snapshot_url(base_url)
    aioclient_mock.get(
        f"{base_url}{FEED_PATH}",
        text=feed_xml(base_url, snapshot_url),
        headers={"Content-Type": "application/atom+xml"},
        status=200,
    )
    aioclient_mock.get(snapshot_url, json=payload, status=200)


def register_nswws_feed_error(
    aioclient_mock, status: int, base_url: str = NSWWS_BASE_URL
) -> None:
    """Register a feed-level failure. Auth is enforced on every call, so an
    auth/connection error surfaces here before the issued snapshot is ever
    requested."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{base_url}{FEED_PATH}", status=status)
