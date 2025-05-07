"""API client for DeWarmte v1."""
from __future__ import annotations

import logging
from typing import Any, Dict, Union, Callable, List
from dataclasses import dataclass

import aiohttp

from .models.device import Device
from .models.api_sensor import ApiSensor
from .models.config import ConnectionSettings
from .models.settings import DeviceOperationSettings
from .models.settings_group import SettingsGroup
from .auth import DeWarmteAuth
from .models.status_data import StatusData

_LOGGER = logging.getLogger(__name__)

# Define all settings groups
SETTING_GROUPS = {
    "heat_curve": SettingsGroup(
        endpoint="heat-curve",
        keys=["heat_curve_mode", "heating_kind", "heat_curve_s1_outside_temp", 
              "heat_curve_s1_target_temp", "heat_curve_s2_outside_temp", 
              "heat_curve_s2_target_temp", "heat_curve_fixed_temperature", 
              "heat_curve_use_smart_correction"],
    ),
    "heating_performance": SettingsGroup(
        endpoint="heating-performance",
        keys=["heating_performance_mode", "heating_performance_backup_temperature"],
    ),
    "backup_heating": SettingsGroup(
        endpoint="backup-heating",
        keys=["backup_heating_mode"],
    ),
    "sound": SettingsGroup(
        endpoint="sound",
        keys=["sound_mode", "sound_compressor_power", "sound_fan_speed"],
    ),
    "advanced": SettingsGroup(
        endpoint="advanced",
        keys=["advanced_boost_mode_control", "advanced_thermostat_delay"],
    ),
    "cooling": SettingsGroup(
        endpoint="cooling",
        keys=["cooling_thermostat_type", "cooling_control_mode", 
              "cooling_temperature", "cooling_duration"],
    ),
}

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

    async def _update_settings(self, group: SettingsGroup, key: str, value: Any) -> None:
        """Common logic for updating settings."""
        url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/{group.endpoint}/"
        
        # Get current settings
        current_settings = await self.async_get_operation_settings()
        if not current_settings:
            raise ValueError("Could not get current settings")
        
        # Build update settings by getting each value directly from settings
        update_settings = {
            setting_key: getattr(current_settings, setting_key)
            for setting_key in group.keys
        }
        
        # Update with new value
        update_settings[key] = value
        
        _LOGGER.debug("Making POST request to %s with data: %s", url, update_settings)
        async with self._session.post(url, json=update_settings, headers=self._auth.headers) as response:
            if response.status != 200:
                _LOGGER.error("Failed to update %s settings: %d", group.endpoint, response.status)
                response_text = await response.text()
                _LOGGER.error("Response: %s", response_text)
                raise ValueError(f"Failed to update {group.endpoint} settings: {response.status}")
            response_data = await response.json()
            _LOGGER.debug("%s settings update response: %s", group.endpoint, response_data)

    async def async_update_operation_settings(self, key: str, value: Union[float, str, int, bool]) -> None:
        """Update a single operation setting."""
        if not self._device:
            raise ValueError("No device selected")

        # Find which group this setting belongs to
        for group in SETTING_GROUPS.values():
            if key in group.keys:
                await self._update_settings(group, key, value)
                # Refresh settings after update
                await self.async_get_operation_settings()
                return

        raise ValueError(
            f"Unable to change setting {key}. "
            "Please report this as a bug."
        ) 