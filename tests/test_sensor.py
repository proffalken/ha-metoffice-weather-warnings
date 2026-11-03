"""Tests for the Met Office Warnings sensor platform."""

from tests.nswws_helpers import register_nswws


async def test_sensor_state_no_active_warnings(
    aioclient_mock, hass, issued_empty, mock_config_entry
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.met_office_warnings_warning_level")
    assert state is not None
    assert state.state == "none"
    assert state.attributes["warnings"] == []
    assert state.attributes["warning_count"] == 0


async def test_sensor_state_active_warnings(
    aioclient_mock, hass, issued_active, mock_config_entry
) -> None:
    register_nswws(aioclient_mock, issued_active)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.met_office_warnings_warning_level")
    assert state.state == "amber"
    assert state.attributes["warning_count"] == 2
    assert state.attributes["warnings"][0]["id"] == (
        "11111111-1111-1111-1111-111111111111"
    )


async def test_top_warning_detail_sensors_no_active_warnings(
    aioclient_mock, hass, issued_empty, mock_config_entry
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    for entity_id in (
        "sensor.met_office_warnings_warning_headline",
        "sensor.met_office_warnings_warning_areas",
        "sensor.met_office_warnings_warning_valid_from",
        "sensor.met_office_warnings_warning_valid_to",
    ):
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == "unknown"


async def test_top_warning_detail_sensors_active_warnings(
    aioclient_mock, hass, issued_active, mock_config_entry
) -> None:
    register_nswws(aioclient_mock, issued_active)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    headline_state = hass.states.get("sensor.met_office_warnings_warning_headline")
    assert headline_state.state == "Thunderstorms may cause disruption Tuesday"
    assert headline_state.attributes["level"] == "amber"
    assert headline_state.attributes["weather_types"] == ["THUNDERSTORM"]
    assert "what_should_i_do" in headline_state.attributes
    assert "what_to_expect" in headline_state.attributes

    areas_state = hass.states.get("sensor.met_office_warnings_warning_areas")
    assert areas_state.state == "London & South East England"

    valid_from_state = hass.states.get("sensor.met_office_warnings_warning_valid_from")
    assert valid_from_state.state == "2026-08-26T02:00:00+00:00"

    valid_to_state = hass.states.get("sensor.met_office_warnings_warning_valid_to")
    assert valid_to_state.state == "2026-08-26T21:00:00+00:00"
