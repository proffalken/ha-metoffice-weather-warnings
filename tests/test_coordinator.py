"""Tests for the Met Office Warnings data update coordinator."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.metoffice_warnings.api import (
    NSWWSAuthError,
    NSWWSConnectionError,
)
from custom_components.metoffice_warnings.const import AREA_ALL, WARNING_LEVEL_AMBER
from custom_components.metoffice_warnings.coordinator import (
    MetOfficeWarningsCoordinator,
    highest_level,
    top_warning,
)
from custom_components.metoffice_warnings.models import warnings_from_geojson


async def test_update_success_no_filter(hass, issued_active) -> None:
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings_from_geojson(issued_active)
    coordinator = MetOfficeWarningsCoordinator(hass, client=client, areas=[AREA_ALL])

    data = await coordinator._async_update_data()

    assert len(data.warnings) == 2
    assert data.level == WARNING_LEVEL_AMBER


async def test_update_filters_by_area(hass, issued_active) -> None:
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings_from_geojson(issued_active)
    coordinator = MetOfficeWarningsCoordinator(
        hass, client=client, areas=["West Midlands"]
    )

    data = await coordinator._async_update_data()

    assert len(data.warnings) == 1
    assert data.warnings[0].region_names == ["West Midlands"]
    assert data.level == "yellow"


async def test_update_no_matches_gives_none_level(hass, issued_active) -> None:
    client = AsyncMock()
    client.async_get_active_warnings.return_value = warnings_from_geojson(issued_active)
    coordinator = MetOfficeWarningsCoordinator(hass, client=client, areas=["Scotland"])

    data = await coordinator._async_update_data()

    assert data.warnings == []
    assert data.level == "none"


async def test_auth_error_raises_config_entry_auth_failed(hass) -> None:
    client = AsyncMock()
    client.async_get_active_warnings.side_effect = NSWWSAuthError("nope")
    coordinator = MetOfficeWarningsCoordinator(hass, client=client, areas=[AREA_ALL])

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_connection_error_raises_update_failed(hass) -> None:
    client = AsyncMock()
    client.async_get_active_warnings.side_effect = NSWWSConnectionError("down")
    coordinator = MetOfficeWarningsCoordinator(hass, client=client, areas=[AREA_ALL])

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


def test_highest_level_orders_by_severity(issued_active) -> None:
    warnings = warnings_from_geojson(issued_active)
    assert highest_level(warnings) == WARNING_LEVEL_AMBER
    assert highest_level([]) == "none"


def test_top_warning_returns_first_or_none(issued_active) -> None:
    warnings = warnings_from_geojson(issued_active)
    assert top_warning(warnings) is warnings[0]
    assert top_warning([]) is None
