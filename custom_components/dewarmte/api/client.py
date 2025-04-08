"""API client for DeWarmte v1."""
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
    """API client for DeWarmte v1."""

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
            _LOGGER.debug("Making GET request to %s", products_url)
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
                        _LOGGER.debug("Making GET request to %s", tb_status_url)
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
            _LOGGER.debug("Making GET request to %s", settings_url)
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

    async def async_update_operation_settings(self, settings: dict[str, Any]) -> None:
        """Update operation settings."""
        if not self._device:
            raise ValueError("No device selected")

        # If any heat curve settings are being updated, we need to send all heat curve settings
        if any(key.startswith("heat_curve_") for key in settings.keys()) or "heating_kind" in settings:
            # Get current heat curve settings
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")

            # Update only the heat curve settings that were provided
            heat_curve_settings = {
                "heat_curve_mode": current_settings.heat_curve.mode,
                "heating_kind": current_settings.heat_curve.heating_kind,
                "heat_curve_s1_outside_temp": current_settings.heat_curve.s1_outside_temp,
                "heat_curve_s1_target_temp": current_settings.heat_curve.s1_target_temp,
                "heat_curve_s2_outside_temp": current_settings.heat_curve.s2_outside_temp,
                "heat_curve_s2_target_temp": current_settings.heat_curve.s2_target_temp,
                "heat_curve_fixed_temperature": current_settings.heat_curve.fixed_temperature,
                "heat_curve_use_smart_correction": current_settings.heat_curve.use_smart_correction,
            }

            # Update with new values
            heat_curve_settings.update(settings)

            # Send all heat curve settings at once
            heat_curve_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/heat-curve/"
            _LOGGER.debug("Making POST request to %s with data: %s", heat_curve_url, heat_curve_settings)
            async with self._session.post(
                heat_curve_url,
                json=heat_curve_settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update heat curve settings: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update heat curve settings: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Heat curve settings update response: %s", response_data)
        elif "heating_performance_mode" in settings:
            # For heating performance mode, use the dedicated endpoint
            _LOGGER.debug("Updating heating performance mode with settings: %s", settings)
            
            # Get current settings to include backup temperature
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Include backup temperature in the update
            update_settings = {
                "heating_performance_mode": settings["heating_performance_mode"],
                "heating_performance_backup_temperature": current_settings.heating_performance_backup_temperature
            }
            
            heating_performance_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/heating-performance/"
            _LOGGER.debug("Making POST request to %s with data: %s", heating_performance_url, update_settings)
            async with self._session.post(
                heating_performance_url,
                json=update_settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update heating performance mode: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update heating performance mode: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Heating performance mode update response: %s", response_data)
        elif "backup_heating_mode" in settings:
            # For backup heating mode, use the dedicated backup-heating endpoint
            _LOGGER.debug("Updating backup heating mode with settings: %s", settings)
            backup_heating_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/backup-heating/"
            _LOGGER.debug("Making POST request to %s with data: %s", backup_heating_url, settings)
            async with self._session.post(
                backup_heating_url,
                json=settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update backup heating mode: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update backup heating mode: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Backup heating mode update response: %s", response_data)
        elif any(key in ["sound_mode", "sound_compressor_power", "sound_fan_speed"] for key in settings.keys()):
            # For sound settings, use the dedicated sound endpoint
            _LOGGER.debug("Updating sound settings with: %s", settings)
            
            # Get current settings to include all sound settings
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Include all sound settings in the update
            update_settings = {
                "sound_mode": current_settings.sound_mode.value,
                "sound_compressor_power": current_settings.sound_compressor_power.value,
                "sound_fan_speed": current_settings.sound_fan_speed.value,
            }
            # Update with new values
            update_settings.update(settings)
            
            sound_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/sound/"
            _LOGGER.debug("Making POST request to %s with data: %s", sound_url, update_settings)
            async with self._session.post(
                sound_url,
                json=update_settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update sound settings: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update sound settings: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Sound settings update response: %s", response_data)
        elif any(key in settings for key in ["advanced_boost_mode_control", "advanced_thermostat_delay"]):
            # For advanced settings (thermostat delay and boost mode), use the advanced endpoint
            _LOGGER.debug("Updating advanced settings with: %s", settings)
            
            # Get current settings to include any missing values
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Prepare update settings with current values
            update_settings = {
                "advanced_boost_mode_control": current_settings.advanced_boost_mode_control,
                "advanced_thermostat_delay": current_settings.advanced_thermostat_delay,
            }
            
            # Update with new values
            update_settings.update(settings)
            
            advanced_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/advanced/"
            _LOGGER.debug("Making POST request to %s with data: %s", advanced_url, update_settings)
            async with self._session.post(
                advanced_url,
                json=update_settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update advanced settings: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update advanced settings: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Advanced settings update response: %s", response_data)
        else:
            # For all other settings, use the regular settings endpoint
            _LOGGER.debug("Updating regular settings with: %s", settings)
            settings_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/"
            _LOGGER.debug("Making POST request to %s with data: %s", settings_url, settings)
            async with self._session.post(
                settings_url,
                json=settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update settings: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update settings: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Settings update response: %s", response_data)

        # Refresh settings after update
        await self.async_get_operation_settings() 