"""The DeWarmte integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import DeWarmteApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DeWarmte from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create API client
    session = async_get_clientsession(hass)
    client = DeWarmteApiClient(
        username=entry.data["username"],
        password=entry.data["password"],
        session=session,
    )

    # Create coordinator
    coordinator = DeWarmteDataUpdateCoordinator(hass, client)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class DeWarmteDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, api: DeWarmteApiClient) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.api = api
        self._device_id = f"{api._device_id}_{api._product_id}" if api._device_id and api._product_id else None

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # First ensure we're logged in
            if not await self.api.async_login():
                raise ConfigEntryNotReady("Failed to log in to DeWarmte")

            # Get both status data and basic settings
            status_data = await self.api.async_get_status_data()
            settings_data = await self.api.async_get_basic_settings()

            # Update device ID if needed
            if not self._device_id and self.api._device_id and self.api._product_id:
                self._device_id = f"{self.api._device_id}_{self.api._product_id}"

            # Combine the data
            return {**status_data, **settings_data}
        except Exception as exception:
            raise UpdateFailed() from exception

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if not self._device_id:
            return None
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name="DeWarmte Heat Pump",
            manufacturer="DeWarmte",
            model="Heat Pump",
        ) 