"""Config flow for the Met Office Warnings integration."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .api import NSWWSApiClient, NSWWSAuthError, NSWWSConnectionError
from .const import (
    AREA_ALL,
    CONF_API_KEY,
    CONF_AREAS,
    CONF_BASE_URL,
    CONF_MONITOR_ALL,
    CONF_SCAN_INTERVAL_MINUTES,
    CONF_USE_HOME_LOCATION,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    MIN_SCAN_INTERVAL_MINUTES,
    NSWWS_REGIONS,
)
from .models import Warning

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)


async def _async_fetch_warnings(hass, api_key: str, base_url: str) -> list[Warning]:
    """Validate credentials and return the currently active warnings.

    Raises NSWWSAuthError / NSWWSConnectionError on failure.
    """
    client = NSWWSApiClient(hass, base_url=base_url, api_key=api_key)
    return await client.async_get_active_warnings()


def _region_choices(
    warnings: list[Warning], extra: Iterable[str] = ()
) -> dict[str, str]:
    """Fixed NSWWS regions, plus any live or previously saved names.

    Live and saved names are merged in so that a renamed or newly added region
    is never hidden, and an existing selection always stays selectable.
    """
    names = set(NSWWS_REGIONS)
    names.update(name for w in warnings for name in w.region_names)
    names.update(extra)
    names -= {"", AREA_ALL}
    return {name: name for name in sorted(names)}


def _areas_schema(region_choices: dict[str, str]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_MONITOR_ALL, default=True): bool,
            vol.Optional(CONF_AREAS, default=[]): cv.multi_select(region_choices),
        }
    )


class MetOfficeWarningsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Met Office Warnings."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._base_url: str | None = None
        self._region_choices: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._base_url = user_input[CONF_BASE_URL]

            await self.async_set_unique_id(self._api_key)
            self._abort_if_unique_id_configured()

            try:
                warnings = await _async_fetch_warnings(
                    self.hass, self._api_key, self._base_url
                )
            except NSWWSAuthError:
                errors["base"] = "invalid_auth"
            except NSWWSConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - guard config flow against any bug
                _LOGGER.exception("Unexpected error validating NSWWS credentials")
                errors["base"] = "unknown"
            else:
                self._region_choices = _region_choices(warnings)
                return await self.async_step_areas()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_areas(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            areas = (
                [AREA_ALL]
                if user_input[CONF_MONITOR_ALL]
                else user_input[CONF_AREAS] or [AREA_ALL]
            )
            return self.async_create_entry(
                title="Met Office Warnings",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_BASE_URL: self._base_url,
                    CONF_AREAS: areas,
                },
            )

        return self.async_show_form(
            step_id="areas", data_schema=_areas_schema(self._region_choices)
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> Any:
        """Handle a reauth triggered by ConfigEntryAuthFailed (e.g. a rejected key)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            try:
                await _async_fetch_warnings(
                    self.hass, api_key, reauth_entry.data[CONF_BASE_URL]
                )
            except NSWWSAuthError:
                errors["base"] = "invalid_auth"
            except NSWWSConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - guard config flow against any bug
                _LOGGER.exception("Unexpected error validating NSWWS credentials")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={**reauth_entry.data, CONF_API_KEY: api_key},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MetOfficeWarningsOptionsFlow()


class MetOfficeWarningsOptionsFlow(OptionsFlow):
    """Handle options: scan interval and area filter."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            interval = user_input[CONF_SCAN_INTERVAL_MINUTES]
            if interval < MIN_SCAN_INTERVAL_MINUTES:
                errors["base"] = "interval_too_short"
            else:
                areas = (
                    [AREA_ALL]
                    if user_input[CONF_MONITOR_ALL]
                    else user_input[CONF_AREAS] or [AREA_ALL]
                )
                return self.async_create_entry(
                    data={
                        CONF_SCAN_INTERVAL_MINUTES: interval,
                        CONF_AREAS: areas,
                        CONF_USE_HOME_LOCATION: user_input[CONF_USE_HOME_LOCATION],
                    }
                )

        try:
            warnings = await _async_fetch_warnings(
                self.hass,
                self.config_entry.data[CONF_API_KEY],
                self.config_entry.data[CONF_BASE_URL],
            )
        except (NSWWSAuthError, NSWWSConnectionError):
            warnings = []

        current_areas = self.config_entry.options.get(
            CONF_AREAS, self.config_entry.data.get(CONF_AREAS, [AREA_ALL])
        )
        region_choices = _region_choices(warnings, extra=current_areas)
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_MINUTES, DEFAULT_SCAN_INTERVAL_MINUTES
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL_MINUTES, default=current_interval
                ): vol.Coerce(int),
                vol.Required(
                    CONF_MONITOR_ALL, default=AREA_ALL in current_areas
                ): bool,
                vol.Required(
                    CONF_USE_HOME_LOCATION,
                    default=self.config_entry.options.get(
                        CONF_USE_HOME_LOCATION, False
                    ),
                ): bool,
                vol.Optional(
                    CONF_AREAS,
                    default=[a for a in current_areas if a != AREA_ALL],
                ): cv.multi_select(region_choices),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
