"""Authentication module for DeWarmte."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import aiohttp
import ssl

_LOGGER = logging.getLogger(__name__)

class DeWarmteAuth:
    """Authentication handler for DeWarmte."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize the auth handler."""
        self._username = username
        self._password = password
        self._base_url = "https://api.mydewarmte.com/v1"
        self._session = session
        self._access_token: str | None = None
        self._device_id: str | None = None
        self._product_id: str | None = None
        
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
            "Authorization": "Bearer null"  # Required for initial login
        }
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    async def login(self) -> tuple[bool, str | None, str | None, str | None]:
        """Login to DeWarmte API."""
        try:
            # First get the access token
            login_url = f"{self._base_url}/auth/token/"
            login_data = {
                "email": self._username,
                "password": self._password,
            }
            _LOGGER.debug("Attempting login with email: %s", self._username)
            async with self._session.post(login_url, json=login_data, headers=self._headers, ssl=self._ssl_context) as response:
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d: %s", response.status, await response.text())
                    return False, None, None, None
                data = await response.json()
                self._access_token = data.get("access")
                if not self._access_token:
                    _LOGGER.error("No access token in response")
                    return False, None, None, None
                self._headers["Authorization"] = f"Bearer {self._access_token}"
                _LOGGER.debug("Successfully obtained access token")

            # Get user info
            user_url = f"{self._base_url}/auth/user/"
            async with self._session.get(user_url, headers=self._headers, ssl=self._ssl_context) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get user info with status %d: %s", response.status, await response.text())
                    return False, None, None, None
                user_data = await response.json()
                _LOGGER.debug("User info: %s", user_data)

            # Get products info
            products_url = f"{self._base_url}/customer/products/"
            async with self._session.get(products_url, headers=self._headers, ssl=self._ssl_context) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get products info with status %d: %s", response.status, await response.text())
                    return False, None, None, None
                products_data = await response.json()
                _LOGGER.debug("Products info: %s", products_data)

                # Extract device and product IDs from the first product
                if products_data.get("results") and len(products_data["results"]) > 0:
                    product = products_data["results"][0]
                    self._device_id = product.get("id")
                    self._product_id = str(product.get("related_ao"))
                    _LOGGER.debug("Found device ID: %s, product ID: %s", self._device_id, self._product_id)
                else:
                    _LOGGER.error("No products found in response")
                    return False, None, None, None

            return True, self._device_id, self._product_id, self._access_token

        except Exception as err:
            _LOGGER.error("Error during login: %s", str(err))
            _LOGGER.error("Error type: %s", type(err).__name__)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return False, None, None, None

    @property
    def headers(self) -> dict[str, str]:
        """Get the current headers."""
        return self._headers.copy()

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url 