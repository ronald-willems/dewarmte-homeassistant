"""API client for DeWarmte v2."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import aiohttp

from .models.device import Device
from .models.sensor import SENSOR_DEFINITIONS, DeviceSensor
from .models.settings import ConnectionSettings, DeviceOperationSettings
from .auth import DeWarmteAuth

_LOGGER = logging.getLogger(__name__)

class DeWarmteApiClient:
    """API client for DeWarmte v2."""

    def __init__(self, connection_settings: ConnectionSettings, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._settings = connection_settings
        self._session = session
        self._base_url = "https://api.mydewarmte.com/v1"
        self._auth = DeWarmteAuth(connection_settings.username, connection_settings.password, session)
        self._device: Device | None = None
        self._operation_settings: DeviceOperationSettings | None = None

    @property
    def device(self) -> Device | None:
        """Return the current device."""
        return self._device

    @property
    def operation_settings(self) -> DeviceOperationSettings | None:
        """Return the current operation settings."""
        return self._operation_settings

    async def async_login(self) -> bool:
        """Login to the API and get device info."""
        success, device_id, product_id, access_token = await self._auth.login()
        if success and device_id and product_id and access_token:
            self._device = Device.from_api_response(device_id, product_id, access_token)
            # Get initial settings
            await self.async_get_operation_settings()
            return True
        return False

    async def async_get_status_data(self) -> Dict[str, DeviceSensor]:
        """Get status data from the API."""
        if not self._device:
            _LOGGER.error("No device available")
            return {}

        try:
            # Get main status data
            products_url = f"{self._base_url}/customer/products/"
            async with self._session.get(products_url, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status data: %d", response.status)
                    return {}
                data = await response.json()
                _LOGGER.debug("Products data: %s", data)
                
                # Find our device in the results
                for product in data.get("results", []):
                    if product.get("id") == self._device.device_id:
                        # Get both top-level and nested status data
                        status = {**product, **product.get("status", {})}
                        
                        # Get outdoor temperature from tb-status endpoint
                        tb_status_url = f"{self._base_url}/customer/products/tb-status/"
                        async with self._session.get(tb_status_url, headers=self._auth.headers) as tb_response:
                            if tb_response.status == 200:
                                tb_data = await tb_response.json()
                                _LOGGER.debug("TB status data: %s", tb_data)
                                if "outdoor_temperature" in tb_data:
                                    status["outdoor_temperature"] = tb_data["outdoor_temperature"]
                        
                        _LOGGER.debug("Combined status data: %s", status)
                        
                        # Map the status data to sensors
                        sensors: Dict[str, DeviceSensor] = {}
                        for sensor_def in SENSOR_DEFINITIONS.values():
                            _LOGGER.debug("Checking sensor %s (var_name: %s)", sensor_def.key, sensor_def.var_name)
                            if sensor_def.var_name in status:
                                value = status[sensor_def.var_name]
                                _LOGGER.debug("Found value for %s: %s", sensor_def.key, value)
                                if sensor_def.convert_func:
                                    value = sensor_def.convert_func(value)
                                sensors[sensor_def.key] = DeviceSensor(
                                    key=sensor_def.key,
                                    name=sensor_def.name,
                                    value=value,
                                    device_class=sensor_def.device_class,
                                    state_class=sensor_def.state_class,
                                    unit=sensor_def.unit,
                                )
                            else:
                                _LOGGER.debug("No value found for %s", sensor_def.key)
                        _LOGGER.debug("Created sensors: %s", sensors)
                        return sensors
                
                _LOGGER.error("Device not found in products response")
                return {}
        except Exception as err:
            _LOGGER.error("Error getting status data: %s", str(err))
            return {}

    async def async_get_operation_settings(self) -> DeviceOperationSettings | None:
        """Get operation settings from the API."""
        if not self._device:
            _LOGGER.error("No device available")
            return None

        try:
            settings_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/"
            async with self._session.get(settings_url, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get operation settings: %d", response.status)
                    return None
                data = await response.json()
                _LOGGER.debug("Operation settings data: %s", data)
                
                self._operation_settings = DeviceOperationSettings.from_api_response(data)
                return self._operation_settings
                
        except Exception as err:
            _LOGGER.error("Error getting operation settings: %s", str(err))
            return None

    async def async_update_operation_settings(self, settings: Dict[str, Any]) -> bool:
        """Update operation settings."""
        if not self._device:
            _LOGGER.error("No device available")
            return False

        try:
            settings_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/"
            async with self._session.patch(settings_url, json=settings, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update settings: %d", response.status)
                    return False
                    
                # Update local settings
                await self.async_get_operation_settings()
                return True
                
        except Exception as err:
            _LOGGER.error("Error updating settings: %s", str(err))
            return False 