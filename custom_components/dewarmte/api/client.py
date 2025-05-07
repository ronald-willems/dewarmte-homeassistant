"""API client for DeWarmte v1."""
from __future__ import annotations

import logging
from typing import Any, Dict, Union

import aiohttp

from .models.device import Device
from .models.api_sensor import ApiSensor
from .models.config import ConnectionSettings
from .models.settings import DeviceOperationSettings
from .auth import DeWarmteAuth
from .models.status_data import StatusData

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

    async def async_get_status_data(self) -> StatusData | None:
        """Get status data from the API."""
        if not self._device:
            _LOGGER.error("No device available")
            return None

        try:
            # Get main status data
            products_url = f"{self._base_url}/customer/products/"
            _LOGGER.debug("Making GET request to %s", products_url)
            async with self._session.get(products_url, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status data: %d", response.status)
                    return None
                data = await response.json()
                _LOGGER.debug("Products data: %s", data)
                
                # Find our device in the results
                for product in data.get("results", []):
                    if product.get("id") == self._device.device_id:
                        # Create StatusData from the product data
                        status_data = StatusData.from_dict({**product, **product.get("status", {})})
                        
                        # Get outdoor temperature from tb-status endpoint
                        tb_status_url = f"{self._base_url}/customer/products/tb-status/"
                        _LOGGER.debug("Making GET request to %s", tb_status_url)
                        async with self._session.get(tb_status_url, headers=self._auth.headers) as tb_response:
                            if tb_response.status == 200:
                                tb_data = await tb_response.json()
                                _LOGGER.debug("TB status data: %s", tb_data)
                                if "outdoor_temperature" in tb_data:
                                    status_data.outdoor_temperature = float(tb_data["outdoor_temperature"])
                        
                        return status_data
                
                _LOGGER.error("Device not found in products response")
                return None
        except Exception as err:
            _LOGGER.error("Error getting status data: %s", str(err))
            return None

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

    async def async_update_operation_settings(self, key: str, value: Union[float, str, int, bool]) -> None:
        """Update a single operation setting."""
        if not self._device:
            raise ValueError("No device selected")

        # If any heat curve settings are being updated, we need to send all heat curve settings
        if key.startswith("heat_curve_") or key == "heating_kind":
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

            # Update with new value
            heat_curve_settings[key] = value

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
        elif key == "heating_performance_mode":
            # For heating performance mode, use the dedicated endpoint
            _LOGGER.debug("Updating heating performance mode with value: %s", value)
            
            # Get current settings to include backup temperature
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Include backup temperature in the update
            update_settings = {
                "heating_performance_mode": value,
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
        elif key == "backup_heating_mode":
            # For backup heating mode, use the dedicated backup-heating endpoint
            _LOGGER.debug("Updating backup heating mode with value: %s", value)
            backup_heating_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/backup-heating/"
            _LOGGER.debug("Making POST request to %s with data: %s", backup_heating_url, {key: value})
            async with self._session.post(
                backup_heating_url,
                json={key: value},
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update backup heating mode: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update backup heating mode: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Backup heating mode update response: %s", response_data)
        elif key in ["sound_mode", "sound_compressor_power", "sound_fan_speed"]:
            # For sound settings, use the dedicated sound endpoint
            _LOGGER.debug("Updating sound setting %s with value: %s", key, value)
            
            # Get current settings to include all sound settings
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Include all sound settings in the update
            update_settings = {
                "sound_mode": current_settings.sound_mode,
                "sound_compressor_power": current_settings.sound_compressor_power,
                "sound_fan_speed": current_settings.sound_fan_speed,
            }
            # Update with new value
            update_settings[key] = value
            
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
        elif key in ["advanced_boost_mode_control", "advanced_thermostat_delay"]:
            # For advanced settings (thermostat delay and boost mode), use the advanced endpoint
            _LOGGER.debug("Updating advanced setting %s with value: %s", key, value)
            
            # Get current settings to include any missing values
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Prepare update settings with current values
            update_settings = {
                "advanced_boost_mode_control": current_settings.advanced_boost_mode_control,
                "advanced_thermostat_delay": current_settings.advanced_thermostat_delay,
            }
            
            # Update with new value
            update_settings[key] = value
            
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
        elif key in ["cooling_thermostat_type", "cooling_control_mode", "cooling_temperature", "cooling_duration"]:
            # For cooling settings, use the dedicated cooling endpoint
            _LOGGER.debug("Updating cooling setting %s with value: %s", key, value)
            
            # Get current settings to include all cooling settings
            current_settings = await self.async_get_operation_settings()
            if not current_settings:
                raise ValueError("Could not get current settings")
            
            # Include all cooling settings in the update
            update_settings = {
                "cooling_thermostat_type": current_settings.cooling_thermostat_type,
                "cooling_control_mode": current_settings.cooling_control_mode,
                "cooling_temperature": current_settings.cooling_temperature,
                "cooling_duration": current_settings.cooling_duration,
            }
            # Update with new value
            update_settings[key] = value
            
            cooling_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/cooling/"
            _LOGGER.debug("Making POST request to %s with data: %s", cooling_url, update_settings)
            async with self._session.post(
                cooling_url,
                json=update_settings,
                headers=self._auth.headers,
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to update cooling settings: %d", response.status)
                    response_text = await response.text()
                    _LOGGER.error("Response: %s", response_text)
                    raise ValueError(f"Failed to update cooling settings: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("Cooling settings update response: %s", response_data)
        else:
            # Instead of using general endpoint, raise an error
            raise ValueError(
                f"Unable to change setting {key}. "
                "Please report this as a bug."
            )

        # Refresh settings after update
        await self.async_get_operation_settings() 