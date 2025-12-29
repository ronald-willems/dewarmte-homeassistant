"""The DeWarmte integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, Optional, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api.client import DeWarmteApiClient
from .api.models.config import ConnectionSettings
from .api.models.device import Device, DwDeviceInfo
from .api.models.api_sensor import ApiSensor
from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .api.models.status_data import StatusData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DeWarmte from a config entry."""
    try:
        # Import platforms here to avoid circular imports
        from . import sensor, binary_sensor, number, select, switch  # noqa: F401

        hass.data.setdefault(DOMAIN, {})

        # Create API client
        session = async_get_clientsession(hass)
        connection_settings = ConnectionSettings(
            username=entry.data["username"],
            password=entry.data["password"],
            update_interval=entry.data.get("update_interval", DEFAULT_UPDATE_INTERVAL)
        )
        client = DeWarmteApiClient(
            connection_settings=connection_settings,
            session=session,
        )

        # Discover devices (this also handles login)
        devices = await client.async_discover_devices()
        if not devices:
            raise ConfigEntryNotReady("No devices discovered")

        # Create coordinators for all discovered devices
        coordinators: List[DeWarmteDataUpdateCoordinator] = []
        for device in devices:
            coordinator = DeWarmteDataUpdateCoordinator(
                hass,
                client,
                device,
                update_interval=timedelta(seconds=connection_settings.update_interval)
            )
            await coordinator.async_config_entry_first_refresh()
            if not coordinator.last_update_success:
                raise ConfigEntryNotReady("Failed to fetch initial data for device")
            coordinators.append(coordinator)

        hass.data[DOMAIN][entry.entry_id] = coordinators

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

class DeWarmteDataUpdateCoordinator(DataUpdateCoordinator[StatusData]):
    """Class to manage fetching data from the API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DeWarmteApiClient,
        device: Device,
        update_interval: timedelta
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api
        self._device = device

    @property
    def device(self) -> Optional[Device]:
        """Get the current device."""
        return self._device

    async def _async_update_data(self) -> StatusData:
        """Update data via library."""
        try:
            # First ensure we're logged in by attempting to get status data
            # This will trigger login if needed
            status_data = await self.api.async_get_status_data(self.device)
            if not status_data:
                raise UpdateFailed("Failed to get status data")

            # Log thermostat state for debugging
            _LOGGER.debug("Device %s: thermostat state = %s", 
                         self.device.device_id if self.device else "unknown", 
                         status_data.thermostat)

            # Get operation settings (needed for number, select, and switch entities)
            # Fetch settings for AO, MP, and PT devices (HC devices have no settings)
            if self.device.product_id.startswith(("AO ", "MP ", "PT ")):
                self._cached_settings = await self.api.async_get_operation_settings(self.device)
            else:
                self._cached_settings = None

            return status_data

        except Exception as exception:
            _LOGGER.error("Error updating data: %s", str(exception))
            raise UpdateFailed() from exception

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        if not self.device:
            raise ValueError("Device must be available to get device info")
            
        return DeviceInfo(
            identifiers={(DOMAIN, self.device.device_id)},
            name=self.device.info.name,
            manufacturer=self.device.info.manufacturer,
            model=self.device.info.model,
            sw_version=self.device.info.sw_version,
            hw_version=self.device.info.hw_version,
        ) 