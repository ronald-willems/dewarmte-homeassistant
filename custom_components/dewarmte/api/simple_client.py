"""Simple DeWarmte API client."""
"""This is a new client that is the base of a future refactoring. it is not yet used."""
from __future__ import annotations

import logging
import ssl
from typing import Any, TypeVar, Type, cast

import aiohttp
from aiohttp import ClientTimeout, TCPConnector

from custom_components.dewarmte.api.models.device import Device
from custom_components.dewarmte.api.models.settings import DeviceOperationSettings
from custom_components.dewarmte.api.models.status_data import StatusData
from custom_components.dewarmte.const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")

class DeWarmteSimpleApiClient:
    """Simple DeWarmte API client."""

    def __init__(
        self,
        username: str,
        password: str,
        timeout: int = 30,
        verify_ssl: bool = False,
    ) -> None:
        """Initialize the DeWarmte API client.

        Args:
            username: The username for authentication
            password: The password for authentication
            timeout: The timeout in seconds for API requests
            verify_ssl: Whether to verify SSL certificates
        """
        self._username = username
        self._password = password
        self._timeout = ClientTimeout(total=timeout)
        self._verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = None
        self._token: str | None = None
        self._base_url = "https://api.mydewarmte.com/v1"
        self._headers = {
            "Accept": "application/json",
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/json",
            "Origin": "https://mydewarmte.com",
            "Referer": "https://mydewarmte.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Authorization": "Bearer null"  # Will be updated after login
        }

    def _create_session(self) -> aiohttp.ClientSession:
        """Create a new aiohttp session with proper SSL settings."""
        ssl_context = None if self._verify_ssl else ssl.create_default_context()
        if not self._verify_ssl and ssl_context:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        connector = TCPConnector(ssl=ssl_context)
        return aiohttp.ClientSession(timeout=self._timeout, connector=connector)

    async def __aenter__(self) -> DeWarmteSimpleApiClient:
        """Create aiohttp session when entering context manager."""
        self._session = self._create_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close aiohttp session when exiting context manager."""
        if self._session:
            await self._session.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        model_class: Type[T] | None = None,
        json_data: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> T | bool | None:
        """Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            model_class: Optional model class to parse response
            json_data: Optional JSON data to send
            expected_status: Expected HTTP status code

        Returns:
            Parsed response data or boolean for success/failure
        """
        if not self._session or not self._token:
            return None

        try:
            headers = {"Authorization": f"Bearer {self._token}"}
            async with self._session.request(
                method,
                f"{self._base_url}/{endpoint}",
                headers=headers,
                json=json_data,
            ) as response:
                if response.status == expected_status:
                    if model_class:
                        data = await response.json()
                        if isinstance(data, list):
                            return [model_class.from_dict(item) for item in data]
                        return model_class.from_dict(data)
                    return True
                _LOGGER.error(
                    "Request failed with status %d: %s %s",
                    response.status,
                    method,
                    endpoint,
                )
                return None
        except Exception as e:
            _LOGGER.error("Request failed: %s %s - %s", method, endpoint, str(e))
            return None

    async def login(self) -> bool:
        """Login to the DeWarmte API.

        Returns:
            bool: True if login was successful, False otherwise
        """
        if not self._session:
            self._session = self._create_session()

        try:
            # First get the access token
            login_url = f"{self._base_url}/auth/token/"
            login_data = {
                "email": self._username,
                "password": self._password,
            }
            async with self._session.post(login_url, json=login_data, headers=self._headers) as response:
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d", response.status)
                    return False
                data = await response.json()
                self._token = data.get("access")
                if not self._token:
                    _LOGGER.error("No access token in response")
                    return False
                self._headers["Authorization"] = f"Bearer {self._token}"
                return True
        except Exception as e:
            _LOGGER.error("Login failed: %s", str(e))
            return False

    async def get_device_info(self) -> Device | None:
        """Get device information.

        Returns:
            Device | None: Device information if successful, None otherwise
        """
        if not self._session or not self._token:
            return None

        try:
            # Get products info
            products_url = f"{self._base_url}/customer/products/"
            async with self._session.get(products_url, headers=self._headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get products info with status %d", response.status)
                    return None
                data = await response.json()
                if data.get("results") and len(data["results"]) > 0:
                    product = data["results"][0]
                    device_id = product.get("id")
                    product_id = str(product.get("related_ao"))
                    return Device.from_api_response(device_id, product_id, self._token)
                _LOGGER.error("No products found in response")
                return None
        except Exception as e:
            _LOGGER.error("Failed to get device info: %s", str(e))
            return None

    async def get_operation_settings(self, device_id: str) -> DeviceOperationSettings | None:
        """Get device operation settings.

        Args:
            device_id: The ID of the device

        Returns:
            DeviceOperationSettings | None: Operation settings if successful, None otherwise
        """
        if not self._session or not self._token:
            return None

        try:
            settings_url = f"{self._base_url}/customer/products/{device_id}/settings/"
            async with self._session.get(settings_url, headers=self._headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get operation settings with status %d", response.status)
                    return None
                data = await response.json()
                return DeviceOperationSettings.from_api_response(data)
        except Exception as e:
            _LOGGER.error("Failed to get operation settings: %s", str(e))
            return None

    async def get_status_data(self, device_id: str) -> StatusData | None:
        """Get device status data.

        Args:
            device_id: The ID of the device

        Returns:
            StatusData | None: Status data if successful, None otherwise
        """
        if not self._session or not self._token:
            return None

        try:
            # Get main status data
            products_url = f"{self._base_url}/customer/products/"
            async with self._session.get(products_url, headers=self._headers) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status data with status %d", response.status)
                    return None
                data = await response.json()
                
                # Find our device in the results
                for product in data.get("results", []):
                    if product.get("id") == device_id:
                        # Get both top-level and nested status data
                        status = {**product, **product.get("status", {})}
                        
                        # Get outdoor temperature from tb-status endpoint
                        tb_status_url = f"{self._base_url}/customer/products/tb-status/"
                        async with self._session.get(tb_status_url, headers=self._headers) as tb_response:
                            if tb_response.status == 200:
                                tb_data = await tb_response.json()
                                if "outdoor_temperature" in tb_data:
                                    status["outdoor_temperature"] = tb_data["outdoor_temperature"]
                        
                        return StatusData.from_dict(status)
                
                _LOGGER.error("Device not found in products response")
                return None
        except Exception as e:
            _LOGGER.error("Failed to get status data: %s", str(e))
            return None

  