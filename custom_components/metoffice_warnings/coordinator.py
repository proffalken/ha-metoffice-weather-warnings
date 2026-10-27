"""Data update coordinator for the Met Office Warnings integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NSWWSApiClient, NSWWSAuthError, NSWWSConnectionError
from .const import (
    AREA_ALL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    WARNING_LEVEL_NONE,
    WARNING_LEVELS,
)
from .geometry import geometry_covers, valid_coordinates
from .models import Warning

_LOGGER = logging.getLogger(__name__)

_SEVERITY_RANK = {level: index for index, level in enumerate(WARNING_LEVELS)}


def highest_level(warnings: list[Warning]) -> str:
    """Return the most severe level present, or 'none' if the list is empty."""
    if not warnings:
        return WARNING_LEVEL_NONE
    return max((w.level for w in warnings), key=lambda level: _SEVERITY_RANK[level])


def top_warning(warnings: list[Warning]) -> Warning | None:
    """Return the most prominent active warning, or None if there isn't one.

    The API already sorts `/objects/issued` by severity (RED > AMBER > YELLOW),
    then impact/likelihood, then chronologically - so the first entry in an
    already-filtered list is the one worth surfacing on its own.
    """
    return warnings[0] if warnings else None


def _matches_area(warning: Warning, areas: list[str]) -> bool:
    if AREA_ALL in areas:
        return True
    return any(region in areas for region in warning.region_names)


@dataclass(frozen=True, slots=True)
class WarningsData:
    """Coordinator payload: the filtered warnings plus the derived overall level."""

    warnings: list[Warning]
    level: str
    filter_method: str = "region"


class MetOfficeWarningsCoordinator(DataUpdateCoordinator[WarningsData]):
    """Polls NSWWS `/issued` and filters the result to the configured areas."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: NSWWSApiClient,
        areas: list[str],
        update_interval=DEFAULT_SCAN_INTERVAL,
        use_home_location: bool = False,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self._client = client
        self._areas = areas
        self._use_home_location = use_home_location
        self.all_warnings: list[Warning] = []

    async def _async_update_data(self) -> WarningsData:
        try:
            all_warnings = await self._client.async_get_active_warnings()
        except NSWWSAuthError as err:
            raise ConfigEntryAuthFailed(
                "Met Office rejected the configured API key"
            ) from err
        except NSWWSConnectionError as err:
            raise UpdateFailed(f"Error fetching NSWWS warnings: {err}") from err

        self.all_warnings = all_warnings

        if self._use_home_location and valid_coordinates(
            self.hass.config.latitude, self.hass.config.longitude
        ):
            latitude = self.hass.config.latitude
            longitude = self.hass.config.longitude
            matched = []
            fallback_used = False
            for warning in all_warnings:
                covered = geometry_covers(warning.geometry, latitude, longitude)
                if covered is True:
                    matched.append(warning)
                elif covered is None and _matches_area(warning, self._areas):
                    matched.append(warning)
                    fallback_used = True
            method = "polygon_with_region_fallback" if fallback_used else "polygon"
        else:
            matched = [w for w in all_warnings if _matches_area(w, self._areas)]
            method = "region_fallback" if self._use_home_location else "region"
        return WarningsData(
            warnings=matched, level=highest_level(matched), filter_method=method
        )
