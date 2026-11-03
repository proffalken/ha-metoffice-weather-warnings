"""Tests for the NSWWS API client (feed -> discovered issued snapshot)."""

import pytest

from custom_components.metoffice_warnings.api import (
    NSWWSApiClient,
    NSWWSAuthError,
    NSWWSConnectionError,
)
from custom_components.metoffice_warnings.const import API_KEY_HEADER, FEED_PATH
from tests.nswws_helpers import (
    NSWWS_BASE_URL,
    feed_xml,
    feed_xml_without_related_link,
    issued_snapshot_url,
    register_nswws,
    register_nswws_feed_error,
)


@pytest.fixture
def client(hass):
    return NSWWSApiClient(hass, base_url=NSWWS_BASE_URL, api_key="test-key")


async def test_get_active_warnings_success(
    aioclient_mock, client, issued_active
) -> None:
    register_nswws(aioclient_mock, issued_active)
    warnings = await client.async_get_active_warnings()

    assert len(warnings) == 2
    assert warnings[0].level == "amber"


async def test_get_active_warnings_empty(aioclient_mock, client, issued_empty) -> None:
    register_nswws(aioclient_mock, issued_empty)
    warnings = await client.async_get_active_warnings()

    assert warnings == []


async def test_sends_api_key_header_on_both_requests(
    aioclient_mock, client, issued_empty
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    await client.async_get_active_warnings()

    headers_by_url: dict[str, list] = {}
    for method, url, _, headers in aioclient_mock.mock_calls:
        if method == "GET":
            headers_by_url.setdefault(str(url), []).append(headers)
    for url in (client._url(FEED_PATH), issued_snapshot_url()):
        assert headers_by_url[url]
        assert all(h[API_KEY_HEADER] == "test-key" for h in headers_by_url[url])


async def test_auth_error_on_feed_raises(aioclient_mock, client) -> None:
    register_nswws_feed_error(aioclient_mock, status=401)
    with pytest.raises(NSWWSAuthError):
        await client.async_get_active_warnings()


async def test_auth_error_on_issued_snapshot_raises(aioclient_mock, client) -> None:
    aioclient_mock.get(
        f"{NSWWS_BASE_URL}{FEED_PATH}",
        text=feed_xml(),
        headers={"Content-Type": "application/atom+xml"},
        status=200,
    )
    aioclient_mock.get(issued_snapshot_url(), status=403)
    with pytest.raises(NSWWSAuthError):
        await client.async_get_active_warnings()


async def test_connection_error_raises(aioclient_mock, client) -> None:
    aioclient_mock.get(f"{NSWWS_BASE_URL}{FEED_PATH}", exc=TimeoutError())
    with pytest.raises(NSWWSConnectionError):
        await client.async_get_active_warnings()


async def test_server_error_raises_connection_error(aioclient_mock, client) -> None:
    register_nswws_feed_error(aioclient_mock, status=500)
    with pytest.raises(NSWWSConnectionError):
        await client.async_get_active_warnings()


async def test_missing_related_link_raises_connection_error(
    aioclient_mock, client
) -> None:
    aioclient_mock.get(
        f"{NSWWS_BASE_URL}{FEED_PATH}",
        text=feed_xml_without_related_link(),
        headers={"Content-Type": "application/atom+xml"},
        status=200,
    )
    with pytest.raises(NSWWSConnectionError):
        await client.async_get_active_warnings()


async def test_malformed_feed_xml_raises_connection_error(
    aioclient_mock, client
) -> None:
    aioclient_mock.get(
        f"{NSWWS_BASE_URL}{FEED_PATH}",
        text="not xml <<<",
        headers={"Content-Type": "application/atom+xml"},
        status=200,
    )
    with pytest.raises(NSWWSConnectionError):
        await client.async_get_active_warnings()


async def test_malformed_issued_json_raises_connection_error(
    aioclient_mock, client
) -> None:
    aioclient_mock.get(
        f"{NSWWS_BASE_URL}{FEED_PATH}",
        text=feed_xml(),
        headers={"Content-Type": "application/atom+xml"},
        status=200,
    )
    aioclient_mock.get(issued_snapshot_url(), text="not json", status=200)
    with pytest.raises(NSWWSConnectionError):
        await client.async_get_active_warnings()
