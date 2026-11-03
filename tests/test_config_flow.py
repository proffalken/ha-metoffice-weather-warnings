"""Tests for the Met Office Warnings config and options flows."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.metoffice_warnings.const import (
    AREA_ALL,
    CONF_API_KEY,
    CONF_AREAS,
    CONF_BASE_URL,
    CONF_MONITOR_ALL,
    CONF_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)
from tests.nswws_helpers import (
    NSWWS_BASE_URL,
    register_nswws,
    register_nswws_feed_error,
)

BASE_URL = NSWWS_BASE_URL


async def _start_user_step(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_step_success_no_active_warnings(
    aioclient_mock, hass, issued_empty
) -> None:
    result = await _start_user_step(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    register_nswws(aioclient_mock, issued_empty)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "test-key", CONF_BASE_URL: BASE_URL},
    )

    # No live warnings to derive area choices from -> go straight to a completed entry.
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == "test-key"
    assert result["data"][CONF_AREAS] == [AREA_ALL]


async def test_user_step_then_area_selection(
    aioclient_mock, hass, issued_active
) -> None:
    result = await _start_user_step(hass)

    register_nswws(aioclient_mock, issued_active)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "test-key", CONF_BASE_URL: BASE_URL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "areas"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_MONITOR_ALL: False, CONF_AREAS: ["West Midlands"]},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_AREAS] == ["West Midlands"]


async def test_area_step_monitor_all_ignores_selection(
    aioclient_mock, hass, issued_active
) -> None:
    result = await _start_user_step(hass)

    register_nswws(aioclient_mock, issued_active)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "test-key", CONF_BASE_URL: BASE_URL},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_MONITOR_ALL: True, CONF_AREAS: []},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_AREAS] == [AREA_ALL]


async def test_user_step_invalid_auth(aioclient_mock, hass) -> None:
    result = await _start_user_step(hass)

    register_nswws_feed_error(aioclient_mock, status=401)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "bad-key", CONF_BASE_URL: BASE_URL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_step_cannot_connect(aioclient_mock, hass) -> None:
    result = await _start_user_step(hass)

    register_nswws_feed_error(aioclient_mock, status=500)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "test-key", CONF_BASE_URL: BASE_URL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_unknown_error(hass) -> None:
    result = await _start_user_step(hass)

    with patch(
        "custom_components.metoffice_warnings.config_flow._async_fetch_warnings",
        side_effect=RuntimeError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "test-key", CONF_BASE_URL: BASE_URL},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}


async def test_duplicate_entry_aborts(aioclient_mock, hass, issued_empty) -> None:
    register_nswws(aioclient_mock, issued_empty)
    result = await _start_user_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "dup-key", CONF_BASE_URL: BASE_URL},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    register_nswws(aioclient_mock, issued_empty)
    result = await _start_user_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "dup-key", CONF_BASE_URL: BASE_URL},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_scan_interval(
    aioclient_mock, hass, issued_empty
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    result = await _start_user_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "opt-key", CONF_BASE_URL: BASE_URL},
    )

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    register_nswws(aioclient_mock, issued_empty)
    options_result = await hass.config_entries.options.async_init(entry.entry_id)
    options_result = await hass.config_entries.options.async_configure(
        options_result["flow_id"],
        {
            CONF_SCAN_INTERVAL_MINUTES: 15,
            CONF_MONITOR_ALL: True,
            CONF_AREAS: [],
        },
    )

    assert options_result["type"] is FlowResultType.CREATE_ENTRY
    assert options_result["data"][CONF_SCAN_INTERVAL_MINUTES] == 15


async def test_options_flow_interval_too_short(
    aioclient_mock, hass, issued_empty
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    result = await _start_user_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "short-key", CONF_BASE_URL: BASE_URL},
    )

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    register_nswws(aioclient_mock, issued_empty)
    options_result = await hass.config_entries.options.async_init(entry.entry_id)
    options_result = await hass.config_entries.options.async_configure(
        options_result["flow_id"],
        {
            CONF_SCAN_INTERVAL_MINUTES: 1,
            CONF_MONITOR_ALL: True,
            CONF_AREAS: [],
        },
    )

    assert options_result["type"] is FlowResultType.FORM
    assert options_result["errors"] == {"base": "interval_too_short"}


async def test_reauth_flow_success(
    aioclient_mock, hass, issued_empty, mock_config_entry
) -> None:
    register_nswws_feed_error(aioclient_mock, status=401)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    reauth_flows = [f for f in flows if f["context"]["source"] == "reauth"]
    assert len(reauth_flows) == 1

    register_nswws(aioclient_mock, issued_empty)
    result = await hass.config_entries.flow.async_configure(
        reauth_flows[0]["flow_id"],
        {CONF_API_KEY: "new-key"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == "new-key"


async def test_reauth_flow_invalid_auth_shows_error(
    aioclient_mock, hass, mock_config_entry
) -> None:
    register_nswws_feed_error(aioclient_mock, status=401)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    reauth_flows = [
        f
        for f in hass.config_entries.flow.async_progress()
        if f["context"]["source"] == "reauth"
    ]

    register_nswws_feed_error(aioclient_mock, status=401)
    result = await hass.config_entries.flow.async_configure(
        reauth_flows[0]["flow_id"],
        {CONF_API_KEY: "still-bad-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_cannot_connect_shows_error(
    aioclient_mock, hass, mock_config_entry
) -> None:
    register_nswws_feed_error(aioclient_mock, status=401)
    assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    reauth_flows = [
        f
        for f in hass.config_entries.flow.async_progress()
        if f["context"]["source"] == "reauth"
    ]

    register_nswws_feed_error(aioclient_mock, status=500)
    result = await hass.config_entries.flow.async_configure(
        reauth_flows[0]["flow_id"],
        {CONF_API_KEY: "new-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_fetch_failure_falls_back_to_empty_choices(
    aioclient_mock, hass, issued_empty
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    result = await _start_user_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_API_KEY: "fallback-key", CONF_BASE_URL: BASE_URL},
    )

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    register_nswws_feed_error(aioclient_mock, status=500)
    options_result = await hass.config_entries.options.async_init(entry.entry_id)

    assert options_result["type"] is FlowResultType.FORM
    assert options_result["step_id"] == "init"
