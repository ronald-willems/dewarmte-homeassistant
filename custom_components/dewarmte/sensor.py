"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import DeWarmteApiClient
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    SENSOR_NAMES,
    PERCENTAGE_SENSORS,
    TEMPERATURE_SENSORS,
    SENSOR_STATUS,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte sensor platform."""
    entities = []

    # Create temperature sensors
    for sensor_id in TEMPERATURE_SENSORS:
        entities.append(
            DeWarmteTemperatureSensor(
                entry,
                sensor_id,
                SENSOR_NAMES[sensor_id]
            )
        )

    # Create percentage sensors
    for sensor_id in PERCENTAGE_SENSORS:
        entities.append(
            DeWarmtePercentageSensor(
                entry,
                sensor_id,
                SENSOR_NAMES[sensor_id]
            )
        )

    # Create status sensor
    entities.append(DeWarmteStatusSensor(entry))

    async_add_entities(entities, True)

class DeWarmteBaseSensor(SensorEntity):
    """Base class for DeWarmte sensors."""

    def __init__(
        self,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        self._entry = entry
        self._key = key
        self._attr_name = f"DeWarmte {name}"
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_native_value: StateType = None
        self._attr_has_entity_name = True
        self._attr_should_poll = True

    async def async_update(self) -> None:
        """Update the sensor value."""
        try:
            async with DeWarmteApiClient(
                self._entry.data[CONF_USERNAME],
                self._entry.data[CONF_PASSWORD],
            ) as client:
                if await client.async_login():
                    data = await client.async_get_status_data()
                    if self._key in data:
                        if isinstance(data[self._key], dict):
                            self._attr_native_value = data[self._key]["value"]
                        else:
                            self._attr_native_value = data[self._key]
        except Exception as err:
            _LOGGER.error("Error updating sensor %s: %s", self._key, err)

class DeWarmteTemperatureSensor(DeWarmteBaseSensor):
    """Representation of a DeWarmte temperature sensor."""

    def __init__(
        self,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(entry, key, name)
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

class DeWarmtePercentageSensor(DeWarmteBaseSensor):
    """Representation of a DeWarmte percentage sensor."""

    def __init__(
        self,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        """Initialize the percentage sensor."""
        super().__init__(entry, key, name)
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

class DeWarmteStatusSensor(DeWarmteBaseSensor):
    """Representation of a DeWarmte status sensor."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the status sensor."""
        super().__init__(entry, SENSOR_STATUS, SENSOR_NAMES[SENSOR_STATUS]) 