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
from .energy_history.status import async_describe, dismiss_notification
from .const import (
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
        # On for new installs only: existing entries have no such option and
        # read it as off.
        vol.Optional(CONF_IMPORT_ENERGY_HISTORY, default=True): bool,
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
                    options={
                        CONF_IMPORT_ENERGY_HISTORY: user_input.get(
                            CONF_IMPORT_ENERGY_HISTORY, True
                        ),
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


def _status_of(coordinator):
    importer = coordinator.energy_history
    return importer.status if importer is not None else None


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
        """Show how the import is doing, with its setting and its one action."""
        return self.async_show_menu(
            step_id="energy_history",
            menu_options=["energy_history_settings", "energy_history_delete"],
            description_placeholders={"status": await self._energy_history_status()},
        )

    async def async_step_energy_history_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Switch the import on or off.

        A changed option reloads the entry, and setup starts the import when it
        is on.
        """
        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self._config_entry.options, **user_input}
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_IMPORT_ENERGY_HISTORY, default=self._energy_history_on
                ): bool,
            }
        )
        return self.async_show_form(step_id="energy_history_settings", data_schema=schema)

    async def async_step_energy_history_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete the imported history; with the import on, that means import it again."""
        if user_input is not None:
            await self._delete_energy_history()
            return self.async_create_entry(title="", data=dict(self._config_entry.options))

        if self._energy_history_on:
            what_happens = "This deletes the imported history and imports it again from the start."
        else:
            what_happens = (
                "This deletes the imported history. "
                "Switch the import on in Settings to import it again."
            )
        return self.async_show_form(
            step_id="energy_history_delete",
            data_schema=vol.Schema({}),
            description_placeholders={"what_happens": what_happens},
        )

    @property
    def _energy_history_on(self) -> bool:
        return self._config_entry.options.get(CONF_IMPORT_ENERGY_HISTORY, False)

    @property
    def _coordinators(self) -> list:
        return self.hass.data[DOMAIN].get(self._config_entry.entry_id, [])

    async def _energy_history_status(self) -> str:
        lines = [
            f"{coordinator.device.info.name}: "
            + await async_describe(self.hass, coordinator.device, _status_of(coordinator))
            for coordinator in self._coordinators
            if coordinator.device is not None
        ]
        return "\n".join(lines) or "unknown, the integration is not loaded"

    async def _delete_energy_history(self) -> None:
        """Stop a running import first, so it cannot write on top of the deletion."""
        entry_id = self._config_entry.entry_id
        devices = [c.device for c in self._coordinators if c.device is not None]
        if self._energy_history_on:
            await self.hass.config_entries.async_unload(entry_id)
        await async_delete_history(self.hass, devices)
        for device in devices:
            dismiss_notification(self.hass, device)
        if self._energy_history_on:
            self.hass.config_entries.async_schedule_reload(entry_id)

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