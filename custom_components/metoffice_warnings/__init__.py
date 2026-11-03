"""The Met Office Warnings integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import NSWWSApiClient
from .const import (
    AREA_ALL,
    CONF_API_KEY,
    CONF_AREAS,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_USE_HOME_LOCATION,
    DEFAULT_SCAN_INTERVAL_MINUTES,
)
from .coordinator import MetOfficeWarningsCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

type MetOfficeWarningsConfigEntry = ConfigEntry[MetOfficeWarningsCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: MetOfficeWarningsConfigEntry
) -> bool:
    """Set up Met Office Warnings from a config entry."""
    client = NSWWSApiClient(
        hass,
        base_url=entry.data[CONF_BASE_URL],
        api_key=entry.data[CONF_API_KEY],
    )
    areas = entry.options.get(CONF_AREAS, entry.data.get(CONF_AREAS, [AREA_ALL]))
    use_home_location = entry.options.get(CONF_USE_HOME_LOCATION, False)
    scan_minutes = entry.options.get(
        CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
    )

    coordinator = MetOfficeWarningsCoordinator(
        hass,
        client=client,
        areas=areas,
        use_home_location=use_home_location,
        update_interval=timedelta(minutes=scan_minutes),
    )
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        # A failed first refresh still leaves the coordinator's internal
        # retry timer scheduled. Since entry.runtime_data is never set on
        # this path, nothing else can cancel it later - shut it down here.
        await coordinator.async_shutdown()
        raise

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MetOfficeWarningsConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: MetOfficeWarningsConfigEntry
) -> None:
    """Reload the entry when options change (e.g. scan interval, areas)."""
    await hass.config_entries.async_reload(entry.entry_id)
