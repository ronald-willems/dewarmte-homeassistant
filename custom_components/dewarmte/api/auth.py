"""Authentication module for DeWarmte."""
from __future__ import annotations

import logging
from typing import Optional

import aiohttp

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

    async def login(self) -> str | None:
        """Login to DeWarmte API and get access token."""
        try:
            login_url = f"{self._base_url}/auth/token/"
            login_data = {
                "email": self._username,
                "password": self._password,
            }
            _LOGGER.debug("Attempting login with email: %s", self._username)
            async with self._session.post(login_url, json=login_data, headers=self._headers) as response:
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d: %s", response.status, await response.text())
                    return None
                data = await response.json()
                self._access_token = data.get("access")
                if not self._access_token:
                    _LOGGER.error("No access token in response")
                    return None
                self._headers["Authorization"] = f"Bearer {self._access_token}"
                _LOGGER.debug("Successfully obtained access token")
                return self._access_token

        except Exception as err:
            _LOGGER.error("Error during login: %s", str(err))
            _LOGGER.error("Error type: %s", type(err).__name__)
            import traceback
            _LOGGER.error("Traceback: %s", traceback.format_exc())
            return None

    @property
    def headers(self) -> dict[str, str]:
        """Get the current headers."""
        return self._headers.copy()

    @property
    def base_url(self) -> str:
        """Get the base URL."""
        return self._base_url 