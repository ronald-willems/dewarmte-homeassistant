"""API client for DeWarmte v1."""
from __future__ import annotations

import logging
from typing import Any, Dict, Union, Callable, List

import aiohttp

from .models.device import Device
from .models.api_sensor import ApiSensor
from .models.config import ConnectionSettings
from .models.settings import DeviceOperationSettings, SettingsGroup, SETTING_GROUPS
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
        self._is_logged_in = False

    async def async_login(self) -> bool:
        """Login to the API."""
        if self._is_logged_in:
            return True
            
        token = await self._auth.login()
        if token:
            self._is_logged_in = True
            return True
        return False

    async def async_discover_devices(self) -> list[Device]:
        """Discover all supported devices from the API."""
        # Ensure we're logged in
        if not await self.async_login():
            return []

        try:
            # Get device info
            products_url = f"{self._base_url}/customer/products/"
            _LOGGER.debug("Making GET request to %s", products_url)
            async with self._session.get(products_url, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get products info: %d", response.status)
                    return []
                data = await response.json()
                _LOGGER.debug("Products data: %s", data)
                
                # Build device list for supported types (AO and T)
                devices: list[Device] = []
                for product in data.get("results", []):
                    product_type = product.get("type")
                    if product_type not in ("AO", "PT","HC"):  # PT appears to be the T device type
                        continue
                    #TODO: Device handling is overly complex. Important: keep entity ID generation backward compatible.
                    device = Device.from_api_response(
                        device_id=product.get("id"),
                        product_id=f"{product_type} {product.get('name')}",
                        access_token=self._auth.access_token,  # Get token from auth object
                        device_type=product_type,  # Pass device_type directly from API response
                        #name=product.get("nickname"),  # Pass nickname for device name
                        supports_cooling=product.get("cooling", False),
                    )
                    devices.append(device)

                _LOGGER.debug("Discovered devices: %s", [d.device_id for d in devices])
                return devices

        except Exception as err:
            _LOGGER.error("Error getting device info: %s", str(err))
            return []

    async def async_get_status_data(self, device: Device) -> StatusData | None:
        """Get status data from the API for a specific device."""
        # Ensure we're logged in
        if not await self.async_login():
            _LOGGER.error("Failed to login")
            return None

        try:
            # Get main status data
            products_url = f"{self._base_url}/customer/products/"
            _LOGGER.debug("Making GET request to %s", products_url)
            async with self._session.get(products_url, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status data: %d", response.status)
                    if response.status == 401:  # Unauthorized - token expired
                        self._is_logged_in = False
                    return None
                data = await response.json()
                _LOGGER.debug("Products data: %s", data)
                
                # Find our device in the results
                for product in data.get("results", []):
                    if product.get("id") == device.device_id:
                        # Create StatusData from the product data
                        status_data = StatusData.from_dict({**product, **product.get("status", {})})
                        if status_data.invalid_fields:
                            _LOGGER.debug(
                                "Device %s returned missing/invalid status fields: %s",
                                device.device_id,
                                ", ".join(status_data.invalid_fields),
                            )
                        
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
                
                _LOGGER.error("Device %s not found in products response", device.device_id)
                return None
        except Exception as err:
            _LOGGER.error("Error getting status data: %s", str(err))
            return None

    async def async_get_operation_settings(self, device: Device) -> DeviceOperationSettings | None:
        """Get operation settings from the API for a specific device."""
        # Ensure we're logged in
        if not await self.async_login():
            _LOGGER.error("Failed to login")
            return None

        try:
            settings_url = f"{self._base_url}/customer/products/{device.device_id}/settings/"
            _LOGGER.debug("Making GET request to %s", settings_url)
            async with self._session.get(settings_url, headers=self._auth.headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get operation settings: %d", response.status)
                    if response.status == 401:  # Unauthorized - token expired
                        self._is_logged_in = False
                    return None
                data = await response.json()
                _LOGGER.debug("Operation settings data: %s", data)
                
                settings = DeviceOperationSettings.from_api_response(data)
                return settings
                
        except Exception as err:
            _LOGGER.error("Error getting operation settings: %s", str(err))
            return None

    async def async_update_operation_settings(self, device: Device, key: str, value: Union[float, str, int, bool]) -> None:
        """Update a single operation setting for a specific device."""
        # Ensure we're logged in
        if not await self.async_login():
            raise ValueError("Failed to login")

        _LOGGER.debug("Updating operation setting %s to %s", key, value)

        # Find which group this setting belongs to
        for group in SETTING_GROUPS.values():
            if key in group.keys:
                _LOGGER.debug("Found setting group %s for key %s", group.endpoint, key)
                await self._update_settings(device, group, key, value)
                return

        raise ValueError(
            f"Unable to change setting {key}. "
            "Please report this as a bug."
        )

    async def _update_settings(self, device: Device, group: SettingsGroup, key: str, value: Any) -> None:
        """Common logic for updating settings for a specific device."""
        url = f"{self._base_url}/customer/products/{device.device_id}/settings/{group.endpoint}/"
        
        # Get current settings
        current_settings = await self.async_get_operation_settings(device)
        if not current_settings:
            raise ValueError("Could not get current settings")
        
        # Build update settings by getting each value directly from settings
        update_settings = {
            setting_key: getattr(current_settings, setting_key)
            for setting_key in group.keys
        }
        
        # Update with new value
        update_settings[key] = value

        # Adjust cooling settings if needed
        if group.endpoint == "cooling":
            thermostat_type = update_settings.get("cooling_thermostat_type")
            control_mode = update_settings.get("cooling_control_mode")
            
            if thermostat_type == "heating_only" and control_mode == "thermostat":
                update_settings["cooling_control_mode"] = "heating_only"
            elif thermostat_type == "heating_and_cooling" and control_mode in ["cooling_only", "heating_only"]:
                update_settings["cooling_control_mode"] = "thermostat"
        
        # Handle warm water target temperature - set scheduled=false and create single range
        if group.endpoint == "warm-water" and "warm_water_target_temperature" in update_settings:
            target_temp = update_settings["warm_water_target_temperature"]
            # Set scheduled mode to false for simple temperature control
            update_settings["warm_water_is_scheduled"] = False
            # Create single 24/7 range with the target temperature
            update_settings["warm_water_ranges"] = [
                {
                    "order": 0,
                    "temperature": target_temp,
                    "period": "00:00-00:00"  # 24/7 period
                }
            ]
            # Remove the flattened field as API expects ranges
            del update_settings["warm_water_target_temperature"]
        
        
        _LOGGER.debug("Making POST request to %s with data: %s", url, update_settings)
        try:
            async with self._session.post(url, json=update_settings, headers=self._auth.headers) as response:
                if response.status != 200:
                    response_text = await response.text()
                    _LOGGER.error("Failed to update %s settings: %d", group.endpoint, response.status)
                    _LOGGER.error("Response: %s", response_text)
                    if response.status == 401:  # Unauthorized - token expired
                        self._is_logged_in = False
                    raise ValueError(f"Failed to update {group.endpoint} settings: {response.status}")
                response_data = await response.json()
                _LOGGER.debug("%s settings update response: %s", group.endpoint, response_data)
        except Exception as err:
            _LOGGER.error("Error updating %s settings: %s", group.endpoint, str(err))
            raise 