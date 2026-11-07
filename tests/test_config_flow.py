"""The install screen switches the energy history import on for new installs only."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.dewarmte.config_flow import ConfigFlow, OptionsFlowHandler
from custom_components.dewarmte.const import CONF_IMPORT_ENERGY_HISTORY, DOMAIN

CREDENTIALS = {"username": "user@example.com", "password": "secret"}


async def _install(user_input: dict) -> dict:
    flow = ConfigFlow()
    flow.hass = MagicMock()
    flow.handler = DOMAIN
    flow.context = {"source": "user"}
    with patch("custom_components.dewarmte.config_flow._async_validate_login", AsyncMock()):
        return await flow.async_step_user(user_input)


@pytest.mark.asyncio
async def test_new_install_imports_energy_history_by_default() -> None:
    result = await _install(dict(CREDENTIALS))

    assert result["options"] == {CONF_IMPORT_ENERGY_HISTORY: True}
    assert CONF_IMPORT_ENERGY_HISTORY not in result["data"]


@pytest.mark.asyncio
async def test_install_can_leave_the_import_off() -> None:
    result = await _install({**CREDENTIALS, CONF_IMPORT_ENERGY_HISTORY: False})

    assert result["options"] == {CONF_IMPORT_ENERGY_HISTORY: False}


def test_existing_install_without_the_option_stays_off() -> None:
    """Entries created before the install-screen option have no such key."""
    entry = MagicMock(options={"update_interval": 300})

    assert OptionsFlowHandler(entry)._energy_history_on is False
