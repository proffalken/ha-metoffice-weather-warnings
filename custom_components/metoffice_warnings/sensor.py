"""Sensor platform for the Met Office Warnings integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import WARNING_LEVELS
from .coordinator import MetOfficeWarningsCoordinator, top_warning
from .entity import MetOfficeWarningsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the warning sensors for this config entry."""
    coordinator: MetOfficeWarningsCoordinator = entry.runtime_data
    async_add_entities(
        [
            MetOfficeWarningLevelSensor(coordinator, entry),
            MetOfficeWarningHeadlineSensor(coordinator, entry),
            MetOfficeWarningAreasSensor(coordinator, entry),
            MetOfficeWarningValidFromSensor(coordinator, entry),
            MetOfficeWarningValidToSensor(coordinator, entry),
        ]
    )


class MetOfficeWarningLevelSensor(MetOfficeWarningsEntity, SensorEntity):
    """Highest active warning level among the configured areas."""

    _attr_name = "Warning level"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(WARNING_LEVELS)

    def __init__(
        self, coordinator: MetOfficeWarningsCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_warning_level"

    @property
    def native_value(self) -> str:
        return self._data.level

    @property
    def extra_state_attributes(self) -> dict:
        warnings = self._data.warnings
        return {
            "warning_count": len(warnings),
            "filter_method": self._data.filter_method,
            "warnings": [w.as_dict() for w in warnings],
        }


class MetOfficeWarningHeadlineSensor(MetOfficeWarningsEntity, SensorEntity):
    """Headline of the single most prominent active warning, if any."""

    _attr_name = "Warning headline"

    def __init__(
        self, coordinator: MetOfficeWarningsCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_warning_headline"

    @property
    def native_value(self) -> str | None:
        top = top_warning(self._data.warnings)
        return top.headline if top else None

    @property
    def extra_state_attributes(self) -> dict | None:
        top = top_warning(self._data.warnings)
        if top is None:
            return None
        return {
            "level": top.level,
            "weather_types": top.weather_types,
            "what_to_expect": top.what_to_expect,
            "what_should_i_do": top.what_should_i_do,
            "further_details": top.further_details,
            "likelihood": top.likelihood,
            "impact": top.impact,
        }


class MetOfficeWarningAreasSensor(MetOfficeWarningsEntity, SensorEntity):
    """Comma-separated regions affected by the most prominent active warning."""

    _attr_name = "Warning areas"

    def __init__(
        self, coordinator: MetOfficeWarningsCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_warning_areas"

    @property
    def native_value(self) -> str | None:
        top = top_warning(self._data.warnings)
        return ", ".join(top.region_names) if top else None


class MetOfficeWarningValidFromSensor(MetOfficeWarningsEntity, SensorEntity):
    """Start time of the most prominent active warning."""

    _attr_name = "Warning valid from"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: MetOfficeWarningsCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_warning_valid_from"

    @property
    def native_value(self) -> datetime | None:
        top = top_warning(self._data.warnings)
        return top.valid_from if top else None


class MetOfficeWarningValidToSensor(MetOfficeWarningsEntity, SensorEntity):
    """End time of the most prominent active warning."""

    _attr_name = "Warning valid to"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self, coordinator: MetOfficeWarningsCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_warning_valid_to"

    @property
    def native_value(self) -> datetime | None:
        top = top_warning(self._data.warnings)
        return top.valid_to if top else None
