"""Tests for the Met Office Warnings binary_sensor platform."""

from tests.nswws_helpers import register_nswws


async def test_binary_sensor_off_when_no_warnings(
    aioclient_mock, hass, issued_empty, mock_config_entry
) -> None:
    register_nswws(aioclient_mock, issued_empty)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.met_office_warnings_warning_active")
    assert state is not None
    assert state.state == "off"


async def test_binary_sensor_on_when_warnings_active(
    aioclient_mock, hass, issued_active, mock_config_entry
) -> None:
    register_nswws(aioclient_mock, issued_active)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("binary_sensor.met_office_warnings_warning_active")
    assert state.state == "on"
    assert state.attributes["headline"] == "Thunderstorms may cause disruption Tuesday"
