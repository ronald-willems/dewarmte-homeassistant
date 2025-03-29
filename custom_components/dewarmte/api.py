"""API client for DeWarmte v2."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import aiohttp

from .models.device import Device
from .models.sensor import SENSOR_DEFINITIONS, DeviceSensor
from .auth import DeWarmteAuth

_LOGGER = logging.getLogger(__name__)

class DeWarmteApiClient:
    """API client for DeWarmte v2."""

    def __init__(self, device: Device, session: aiohttp.ClientSession, auth: DeWarmteAuth) -> None:
        """Initialize the API client."""
        self._device = device
        self._session = session
        self._auth = auth
        self._base_url = "https://api.mydewarmte.com/v1"

    async def async_get_status_data(self) -> dict[str, Any]:
        """Get status data from the API."""
        try:
            products_url = f"{self._base_url}/customer/products/"
            async with self._session.get(products_url, headers=self._auth.headers, ssl=self._auth._ssl_context) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status data: %d", response.status)
                    return {}
                data = await response.json()
                _LOGGER.debug("Products data: %s", data)
                
                # Find our device in the results
                for product in data.get("results", []):
                    if product.get("id") == self._device.device_id:
                        status = product.get("status", {})
                        _LOGGER.debug("Found status data: %s", status)
                        return status
                
                _LOGGER.error("Device not found in products response")
                return {}
        except Exception as err:
            _LOGGER.error("Error getting status data: %s", str(err))
            return {}

    async def async_get_basic_settings(self) -> dict[str, Any]:
        """Get basic settings from the API."""
        try:
            settings_url = f"{self._base_url}/customer/products/{self._device.device_id}/settings/"
            async with self._session.get(settings_url, headers=self._auth.headers, ssl=self._auth._ssl_context) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get basic settings: %d", response.status)
                    return {}
                data = await response.json()
                _LOGGER.debug("Basic settings: %s", data)
                return data
        except Exception as err:
            _LOGGER.error("Error getting basic settings: %s", str(err))
            return {} 