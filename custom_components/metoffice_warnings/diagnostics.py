"""On-demand warning geometry and filtering diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    AREA_ALL,
    CONF_API_KEY,
    CONF_AREAS,
    CONF_USE_HOME_LOCATION,
)
from .coordinator import MetOfficeWarningsCoordinator
from .geometry import geometry_covers, valid_coordinates

TO_REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Export the latest warning geometries without home coordinates or keys."""
    coordinator: MetOfficeWarningsCoordinator = entry.runtime_data
    areas = entry.options.get(
        CONF_AREAS, entry.data.get(CONF_AREAS, [AREA_ALL])
    )
    use_location = entry.options.get(CONF_USE_HOME_LOCATION, False)
    valid_home = valid_coordinates(
        hass.config.latitude, hass.config.longitude
    )
    included_ids = {w.warning_id for w in coordinator.data.warnings}

    warnings = []
    for warning in coordinator.all_warnings:
        region_match = AREA_ALL in areas or any(
            region in areas for region in warning.region_names
        )
        polygon_match = (
            geometry_covers(
                warning.geometry, hass.config.latitude, hass.config.longitude
            )
            if use_location and valid_home
            else None
        )
        warnings.append(
            {
                "id": warning.warning_id,
                "level": warning.level,
                "headline": warning.headline,
                "areas": warning.region_names,
                "valid_from": warning.valid_from.isoformat(),
                "valid_to": warning.valid_to.isoformat(),
                "included": warning.warning_id in included_ids,
                "region_match": region_match,
                "polygon_match": polygon_match,
                "geometry": warning.geometry,
            }
        )

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "coordinator_data": {
            "level": coordinator.data.level,
            "filter_method": coordinator.data.filter_method,
            "warnings": [w.as_dict() for w in coordinator.data.warnings],
        },
        "geometry_diagnostics": {
            "home_coordinates_valid": valid_home,
            "warnings": warnings,
            "privacy_note": (
                "Exact home coordinates are excluded. "
                "GeoJSON warning polygons may be large."
            ),
        },
    }
