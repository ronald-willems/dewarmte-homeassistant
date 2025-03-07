"""Config flow for DeWarmte integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import DeWarmteApiClient
from .const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class DeWarmteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DeWarmte."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Validate the credentials
                async with DeWarmteApiClient(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                ) as client:
                    if not await client.async_login():
                        errors["base"] = "invalid_auth"
                    else:
                        return self.async_create_entry(
                            title="DeWarmte",
                            data={
                                CONF_USERNAME: user_input[CONF_USERNAME],
                                CONF_PASSWORD: user_input[CONF_PASSWORD],
                                CONF_UPDATE_INTERVAL: user_input.get(
                                    CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                                ),
                            },
                        )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=config_entries.Schema(
                {
                    CONF_USERNAME: str,
                    CONF_PASSWORD: str,
                    CONF_UPDATE_INTERVAL: int,
                }
            ),
            errors=errors,
        ) 