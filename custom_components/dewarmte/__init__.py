"""The DeWarmte integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

import aiohttp
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
    UnitOfTemperature,
    UnitOfPower,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import DeWarmteApiClient, ConnectionSettings, Device, DeviceSensor
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DeWarmte from a config entry."""
    try:
        hass.data.setdefault(DOMAIN, {})

        # Create API client
        session = async_get_clientsession(hass)
        connection_settings = ConnectionSettings(
            username=entry.data["username"],
            password=entry.data["password"],
            update_interval=entry.data.get("update_interval", 300)
        )
        client = DeWarmteApiClient(
            connection_settings=connection_settings,
            session=session,
        )

        # Try to login first
        if not await client.async_login():
            raise ConfigEntryNotReady("Failed to log in to DeWarmte")

        # Create coordinator
        coordinator = DeWarmteDataUpdateCoordinator(
            hass,
            client,
            update_interval=timedelta(seconds=connection_settings.update_interval)
        )

        # Fetch initial data
        await coordinator.async_config_entry_first_refresh()

        if not coordinator.last_update_success:
            raise ConfigEntryNotReady("Failed to fetch initial data")

        hass.data[DOMAIN][entry.entry_id] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        return True
    except Exception as err:
        _LOGGER.error("Error setting up DeWarmte integration: %s", str(err))
        raise ConfigEntryNotReady from err

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class DeWarmteDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, DeviceSensor]]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DeWarmteApiClient,
        update_interval: timedelta = timedelta(seconds=60)
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api

    @property
    def device(self) -> Optional[Device]:
        """Get the current device."""
        return self.api.device

    async def _async_update_data(self) -> Dict[str, DeviceSensor]:
        """Update data via library."""
        try:
            # First ensure we're logged in
            if not await self.api.async_login():
                raise UpdateFailed("Failed to log in to DeWarmte")

            # Get status data
            status_data = await self.api.async_get_status_data()
            if not status_data:
                raise UpdateFailed("Failed to get status data")

            # Get operation settings (needed for number and select entities)
            await self.api.async_get_operation_settings()

            return status_data

        except Exception as exception:
            _LOGGER.error("Error updating data: %s", str(exception))
            raise UpdateFailed() from exception

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if not self.device:
            return None
            
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.device_id)},
            name=self.device.info.name,
            manufacturer=self.device.info.manufacturer,
            model=self.device.info.model,
            sw_version=self.device.info.sw_version,
            hw_version=self.device.info.hw_version,
        ) 