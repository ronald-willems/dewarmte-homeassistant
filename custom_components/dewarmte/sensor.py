"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import DeWarmteApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte sensor platform."""
    async_add_entities([DeWarmteTemperatureSensor(entry)], True)

class DeWarmteTemperatureSensor(SensorEntity):
    """Representation of a DeWarmte temperature sensor."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._attr_name = "DeWarmte Temperature"
        self._attr_unique_id = f"{DOMAIN}_temperature"
        self._attr_native_value: StateType = None
        self._attr_native_unit_of_measurement = "°C"
        self._attr_device_class = "temperature"

    async def async_update(self) -> None:
        """Update the sensor value."""
        try:
            async with DeWarmteApiClient(
                self._entry.data["email"],
                self._entry.data["password"],
            ) as client:
                if await client.async_login():
                    data = await client.async_get_dashboard_data()
                    if "temperature" in data:
                        self._attr_native_value = data["temperature"]
        except Exception as err:
            _LOGGER.error("Error updating temperature: %s", err) 