"""Sensor platform for DeWarmte integration."""
from __future__ import annotations

import logging
from datetime import timedelta
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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .api import DeWarmteApiClient
from .const import (
    DOMAIN,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_UPDATE_INTERVAL,
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
    
    coordinator = DeWarmteDataUpdateCoordinator(
        hass,
        entry=entry,
        name="DeWarmte",
        update_interval=timedelta(
            seconds=entry.data.get(CONF_UPDATE_INTERVAL, 300)
        ),
    )
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    entities = []

    # Create temperature sensors
    for sensor_id in TEMPERATURE_SENSORS:
        entities.append(
            DeWarmteTemperatureSensor(
                coordinator,
                sensor_id,
                SENSOR_NAMES[sensor_id]
            )
        )

    # Create percentage sensors
    for sensor_id in PERCENTAGE_SENSORS:
        entities.append(
            DeWarmtePercentageSensor(
                coordinator,
                sensor_id,
                SENSOR_NAMES[sensor_id]
            )
        )

    # Create status sensor
    entities.append(DeWarmteStatusSensor(coordinator))

    async_add_entities(entities)

class DeWarmteDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching DeWarmte data."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry: ConfigEntry,
        name: str,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=update_interval,
        )
        self.entry = entry
        self._api_client = DeWarmteApiClient(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            async with self._api_client as client:
                if await client.async_login():
                    data = await client.async_get_status_data()
                    if not data:
                        _LOGGER.error("No data received from API")
                        return {}
                    return data
                _LOGGER.error("Failed to login to DeWarmte")
                return {}
        except Exception as err:
            _LOGGER.error("Error updating data: %s", err)
            return {}

class DeWarmteBaseSensor(CoordinatorEntity, SensorEntity):
    """Base class for DeWarmte sensors."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        key: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"DeWarmte {name}"
        self._attr_unique_id = f"{DOMAIN}_{key}"
        self._attr_has_entity_name = True
        self._attr_available = False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self._attr_available

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            self._attr_available = False
            return None
            
        if self._key not in self.coordinator.data:
            self._attr_available = False
            return None
            
        data = self.coordinator.data[self._key]
        self._attr_available = True
        
        if isinstance(data, dict):
            return data.get("value")
        return data

class DeWarmteTemperatureSensor(DeWarmteBaseSensor):
    """Representation of a DeWarmte temperature sensor."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        key: str,
        name: str,
    ) -> None:
        """Initialize the temperature sensor."""
        super().__init__(coordinator, key, name)
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT

class DeWarmtePercentageSensor(DeWarmteBaseSensor):
    """Representation of a DeWarmte percentage sensor."""

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        key: str,
        name: str,
    ) -> None:
        """Initialize the percentage sensor."""
        super().__init__(coordinator, key, name)
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT

class DeWarmteStatusSensor(DeWarmteBaseSensor):
    """Representation of a DeWarmte status sensor."""

    def __init__(self, coordinator: DeWarmteDataUpdateCoordinator) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator, SENSOR_STATUS, SENSOR_NAMES[SENSOR_STATUS]) 