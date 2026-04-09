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
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    connection_settings = ConnectionSettings(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        update_interval=data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    )
    client = DeWarmteApiClient(
        connection_settings=connection_settings,
        session=session,
    )

    try:
        if not await client._auth.ensure_token():
            raise InvalidAuth
    except Exception as err:
        raise InvalidAuth from err

    # Return info that you want to store in the config entry.
    return {
        "title": f"DeWarmte ({data[CONF_USERNAME]})",
        "data": {
            CONF_USERNAME: data[CONF_USERNAME],
            CONF_PASSWORD: data[CONF_PASSWORD],
            CONF_UPDATE_INTERVAL: data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        }
    }


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
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data=info["data"]
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
        """Manage the DeWarmte options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update interval is stored in options.
            update_interval = user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            updated_options = {
                **self._config_entry.options,
                CONF_UPDATE_INTERVAL: update_interval,
            }

            # Username/password are optionally changed; empty means keep current.
            new_username: str | None = user_input.get(CONF_USERNAME) or None
            new_password: str | None = user_input.get(CONF_PASSWORD) or None

            updated_data = dict(self._config_entry.data)
            if new_username is not None:
                updated_data[CONF_USERNAME] = new_username
            if new_password is not None:
                updated_data[CONF_PASSWORD] = new_password

            # If credentials changed, validate them before saving.
            if new_username is not None or new_password is not None:
                try:
                    await _validate_credentials(
                        self.hass,
                        updated_data[CONF_USERNAME],
                        updated_data[CONF_PASSWORD],
                        update_interval,
                    )
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception while validating options")
                    errors["base"] = "unknown"
                else:
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        title=f"DeWarmte ({updated_data[CONF_USERNAME]})",
                        data=updated_data,
                    )
                    return self.async_create_entry(title="", data=updated_options)
            else:
                return self.async_create_entry(title="", data=updated_options)

        current_interval = self._config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self._config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )

        # NOTE: We intentionally default username/password to empty so users can
        # change them without exposing existing secrets.
        schema = vol.Schema(
            {
                vol.Optional(CONF_USERNAME, default=""): str,
                vol.Optional(CONF_PASSWORD, default=""): str,
                vol.Optional(CONF_UPDATE_INTERVAL, default=current_interval): int,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


async def _validate_credentials(
    hass: HomeAssistant, username: str, password: str, update_interval: int
) -> None:
    """Validate DeWarmte credentials by ensuring we can get a token."""
    session = async_get_clientsession(hass)
    connection_settings = ConnectionSettings(
        username=username,
        password=password,
        update_interval=update_interval,
    )
    client = DeWarmteApiClient(connection_settings=connection_settings, session=session)

    if not await client._auth.ensure_token():
        raise InvalidAuth