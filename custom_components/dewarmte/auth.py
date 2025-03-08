"""Authentication module for DeWarmte."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class DeWarmteAuth:
    """Authentication handler for DeWarmte."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize the auth handler."""
        self._username = username
        self._password = password
        self._base_url = "https://mydewarmte.com"
        self._session = session
        self._csrf_token: str | None = None
        self._device_id: str | None = None
        self._product_id: str | None = None
        
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://mydewarmte.com",
            "Referer": "https://mydewarmte.com/"
        }

    async def _get_csrf_token(self) -> str | None:
        """Get CSRF token from login page."""
        try:
            async with self._session.get(
                f"{self._base_url}/",
                headers=self._headers,
                ssl=False
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get login page: %s", response.status)
                    return None

                html = await response.text()
                _LOGGER.debug("Login page content: %s", html[:500])
                
                soup = BeautifulSoup(html, "html.parser")
                csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
                if csrf_input:
                    token = csrf_input.get("value")
                    _LOGGER.debug("Found CSRF token: %s", token)
                    return token
                _LOGGER.error("No CSRF token found in login page")
        except Exception as err:
            _LOGGER.error("Error getting CSRF token: %s", err)
        return None

    async def login(self) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Login to the DeWarmte website.
        
        Returns:
            Tuple containing:
            - Success status (bool)
            - CSRF token (str or None)
            - Device ID (str or None)
            - Product ID (str or None)
        """
        try:
            # Get CSRF token
            self._csrf_token = await self._get_csrf_token()
            if not self._csrf_token:
                return False, None, None, None

            # Update headers with CSRF token
            self._headers["X-CSRFToken"] = self._csrf_token

            # Submit login form
            login_data = {
                "username": self._username,
                "password": self._password,
                "csrfmiddlewaretoken": self._csrf_token
            }
            
            _LOGGER.debug("Attempting login with data: %s", login_data)

            async with self._session.post(
                f"{self._base_url}/",
                data=login_data,
                headers=self._headers,
                allow_redirects=True,
                ssl=False
            ) as response:
                _LOGGER.debug("Login response status: %d", response.status)
                _LOGGER.debug("Login response URL: %s", str(response.url))
                
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d", response.status)
                    return False, None, None, None

                # Store status URL and extract device/product IDs
                response_url = str(response.url)
                if "/status/" in response_url:
                    # Extract device and product IDs from URL like /status/859/A-534/
                    parts = response_url.strip('/').split('/')
                    if len(parts) >= 4:
                        self._device_id = parts[-2]
                        self._product_id = parts[-1]
                        _LOGGER.debug("Found device_id: %s, product_id: %s", self._device_id, self._product_id)
                        return True, self._csrf_token, self._device_id, self._product_id
                
                _LOGGER.error("Login succeeded but no status URL found. Response URL: %s", response_url)
                html = await response.text()
                _LOGGER.debug("Response content: %s", html[:500])
                return False, None, None, None

        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False, None, None, None

    @property
    def headers(self) -> dict[str, str]:
        """Get the current headers."""
        return self._headers.copy()

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url 