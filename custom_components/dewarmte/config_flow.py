"""Config flow for DeWarmte integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.client import DeWarmteApiClient
from .api.models.config import ConnectionSettings
from .energy_history import async_delete_history
from .const import (
    CONF_DELETE_ENERGY_HISTORY,
    CONF_IMPORT_ENERGY_HISTORY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
    }
)


async def _async_validate_login(
    hass: HomeAssistant, *, username: str, password: str, update_interval: int
) -> None:
    """Validate the given credentials allow us to connect."""
    session = async_get_clientsession(hass)
    connection_settings = ConnectionSettings(
        username=username,
        password=password,
        update_interval=update_interval,
    )
    client = DeWarmteApiClient(connection_settings=connection_settings, session=session)

    try:
        if not await client._auth.ensure_token():
            raise InvalidAuth
    except Exception as err:
        raise InvalidAuth from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DeWarmte."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler for this config entry."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate_login(
                    self.hass,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    update_interval=user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"DeWarmte ({user_input[CONF_USERNAME]})",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        # Keep for backward compatibility; actual interval is stored in options.
                        CONF_UPDATE_INTERVAL: user_input.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth.""" 


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle DeWarmte options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize DeWarmte options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["update_interval", "credentials", "energy_history"],
        )

    async def async_step_update_interval(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update polling interval."""
        if user_input is not None:
            update_interval = user_input[CONF_UPDATE_INTERVAL]
            updated_options = {
                **self._config_entry.options,
                CONF_UPDATE_INTERVAL: update_interval,
            }
            return self.async_create_entry(title="", data=updated_options)

        current_interval = self._config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self._config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current_interval): int,
            }
        )
        return self.async_show_form(step_id="update_interval", data_schema=schema)

    async def async_step_energy_history(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Turn the experimental energy-history import on or off.

        Submitting reloads the entry (see the update listener), and setup starts
        the import when the option is on -- so switching it on here is what
        kicks off the first, long, catch-up run.
        """
        if user_input is not None:
            import_on = user_input[CONF_IMPORT_ENERGY_HISTORY]
            unchanged = import_on == self._config_entry.options.get(
                CONF_IMPORT_ENERGY_HISTORY, False
            )
            if user_input.get(CONF_DELETE_ENERGY_HISTORY):
                entry_id = self._config_entry.entry_id
                devices = [
                    coordinator.device
                    for coordinator in self.hass.data[DOMAIN].get(entry_id, [])
                    if coordinator.device is not None
                ]
                await async_delete_history(self.hass, devices)
                # An unchanged option fires no update listener, so with the
                # import left on nothing would rebuild the history until the
                # next hourly run.
                if import_on and unchanged:
                    self.hass.config_entries.async_schedule_reload(entry_id)

            updated_options = {
                **self._config_entry.options,
                CONF_IMPORT_ENERGY_HISTORY: user_input[CONF_IMPORT_ENERGY_HISTORY],
            }
            # Deleting is a one-off action, not a setting; never persist it.
            updated_options.pop(CONF_DELETE_ENERGY_HISTORY, None)
            return self.async_create_entry(title="", data=updated_options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_IMPORT_ENERGY_HISTORY,
                    default=self._config_entry.options.get(
                        CONF_IMPORT_ENERGY_HISTORY, False
                    ),
                ): bool,
                vol.Required(CONF_DELETE_ENERGY_HISTORY, default=False): bool,
            }
        )
        return self.async_show_form(step_id="energy_history", data_schema=schema)

    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            update_interval = self._config_entry.options.get(
                CONF_UPDATE_INTERVAL,
                self._config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            )
            try:
                await _async_validate_login(
                    self.hass,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    update_interval=update_interval,
                )
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception while validating credentials")
                errors["base"] = "unknown"
            else:
                updated_data = dict(self._config_entry.data)
                updated_data[CONF_USERNAME] = user_input[CONF_USERNAME]
                updated_data[CONF_PASSWORD] = user_input[CONF_PASSWORD]
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    title=f"DeWarmte ({updated_data[CONF_USERNAME]})",
                    data=updated_data,
                )
                # Return existing options unchanged so we don't overwrite them.
                return self.async_create_entry(
                    title="", data=dict(self._config_entry.options)
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="credentials",
            data_schema=schema,
            errors=errors,
        )