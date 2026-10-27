"""Tests for the Met Office Warnings config and options flows."""

from unittest.mock import patch

from aioresponses import aioresponses
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.metoffice_warnings.const import (
    AREA_ALL,
    CONF_API_KEY,
    CONF_AREAS,
    CONF_BASE_URL,
    CONF_MONITOR_ALL,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_USE_HOME_LOCATION,
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


async def test_user_step_success_no_active_warnings(hass, issued_empty) -> None:
    result = await _start_user_step(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "test-key", CONF_BASE_URL: BASE_URL},
        )

    # No live warnings to derive area choices from -> go straight to a completed entry.
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_API_KEY] == "test-key"
    assert result["data"][CONF_AREAS] == [AREA_ALL]


async def test_user_step_then_area_selection(hass, issued_active) -> None:
    result = await _start_user_step(hass)

    with aioresponses() as mocked:
        register_nswws(mocked, issued_active)
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


async def test_area_step_monitor_all_ignores_selection(hass, issued_active) -> None:
    result = await _start_user_step(hass)

    with aioresponses() as mocked:
        register_nswws(mocked, issued_active)
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


async def test_user_step_invalid_auth(hass) -> None:
    result = await _start_user_step(hass)

    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=401)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "bad-key", CONF_BASE_URL: BASE_URL},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_step_cannot_connect(hass) -> None:
    result = await _start_user_step(hass)

    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=500)
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


async def test_duplicate_entry_aborts(hass, issued_empty) -> None:
    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await _start_user_step(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "dup-key", CONF_BASE_URL: BASE_URL},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await _start_user_step(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "dup-key", CONF_BASE_URL: BASE_URL},
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_scan_interval(hass, issued_empty) -> None:
    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await _start_user_step(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "opt-key", CONF_BASE_URL: BASE_URL},
        )

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
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


async def test_options_flow_interval_too_short(hass, issued_empty) -> None:
    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await _start_user_step(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "short-key", CONF_BASE_URL: BASE_URL},
        )

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
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


async def test_reauth_flow_success(hass, issued_empty, mock_config_entry) -> None:
    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=401)
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    reauth_flows = [f for f in flows if f["context"]["source"] == "reauth"]
    assert len(reauth_flows) == 1

    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await hass.config_entries.flow.async_configure(
            reauth_flows[0]["flow_id"],
            {CONF_API_KEY: "new-key"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data[CONF_API_KEY] == "new-key"


async def test_reauth_flow_invalid_auth_shows_error(
    hass, mock_config_entry
) -> None:
    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=401)
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    reauth_flows = [
        f
        for f in hass.config_entries.flow.async_progress()
        if f["context"]["source"] == "reauth"
    ]

    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=401)
        result = await hass.config_entries.flow.async_configure(
            reauth_flows[0]["flow_id"],
            {CONF_API_KEY: "still-bad-key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_flow_cannot_connect_shows_error(
    hass, mock_config_entry
) -> None:
    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=401)
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    reauth_flows = [
        f
        for f in hass.config_entries.flow.async_progress()
        if f["context"]["source"] == "reauth"
    ]

    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=500)
        result = await hass.config_entries.flow.async_configure(
            reauth_flows[0]["flow_id"],
            {CONF_API_KEY: "new-key"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_fetch_failure_falls_back_to_empty_choices(
    hass, issued_empty
) -> None:
    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await _start_user_step(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "fallback-key", CONF_BASE_URL: BASE_URL},
        )

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    with aioresponses() as mocked:
        register_nswws_feed_error(mocked, status=500)
        options_result = await hass.config_entries.options.async_init(entry.entry_id)

    assert options_result["type"] is FlowResultType.FORM
    assert options_result["step_id"] == "init"


async def test_options_flow_saves_and_restores_home_location_checkbox(
    hass, issued_empty
) -> None:
    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        result = await _start_user_step(hass)
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "location-opt-key", CONF_BASE_URL: BASE_URL},
        )

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        options_result = await hass.config_entries.options.async_init(entry.entry_id)
        assert options_result["type"] is FlowResultType.FORM
        options_result = await hass.config_entries.options.async_configure(
            options_result["flow_id"],
            {
                CONF_SCAN_INTERVAL_MINUTES: 15,
                CONF_MONITOR_ALL: True,
                CONF_AREAS: [],
                CONF_USE_HOME_LOCATION: True,
            },
        )

    assert options_result["type"] is FlowResultType.CREATE_ENTRY
    assert options_result["data"][CONF_USE_HOME_LOCATION] is True
    assert options_result["data"][CONF_AREAS] == [AREA_ALL]

    with aioresponses() as mocked:
        register_nswws(mocked, issued_empty)
        reopened = await hass.config_entries.options.async_init(entry.entry_id)
    assert reopened["type"] is FlowResultType.FORM
    defaults = reopened["data_schema"]({})
    assert defaults[CONF_USE_HOME_LOCATION] is True
