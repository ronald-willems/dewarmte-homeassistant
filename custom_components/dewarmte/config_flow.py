"""Config flow for DeWarmte integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DeWarmteApiClient
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
from .models.settings import ConnectionSettings

_LOGGER = logging.getLogger(__name__)

class DeWarmteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DeWarmte."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_USERNAME): str,
                        vol.Required(CONF_PASSWORD): str,
                        vol.Optional(
                            CONF_UPDATE_INTERVAL,
                            default=DEFAULT_UPDATE_INTERVAL
                        ): int,
                    }
                ),
            )

        try:
            # Get the client session from Home Assistant
            session = async_get_clientsession(self.hass)
            
            # Create connection settings from user input
            settings = ConnectionSettings(
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                update_interval=user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            )
            
            # Create the API client with the session and settings
            client = DeWarmteApiClient(
                connection_settings=settings,
                session=session,
            )
            
            # Validate the credentials
            if not await client.async_login():
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(
                    f"{DOMAIN}_{settings.username}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"DeWarmte ({settings.username})",
                    data={
                        CONF_USERNAME: settings.username,
                        CONF_PASSWORD: settings.password,
                        CONF_UPDATE_INTERVAL: settings.update_interval,
                    },
                )
                
        except aiohttp.ClientConnectionError:
            errors["base"] = "cannot_connect"
        except aiohttp.ClientError as err:
            _LOGGER.error("API error occurred: %s", err)
            errors["base"] = "api_error"
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception: %s", err)
            errors["base"] = "unknown"

        # If there are errors, show the form again with the errors
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=DEFAULT_UPDATE_INTERVAL
                    ): int,
                }
            ),
            errors=errors,
        ) 