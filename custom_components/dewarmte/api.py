"""API client for DeWarmte."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

class DeWarmteApiClient:
    """Client for interacting with the DeWarmte API."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the client."""
        self._session: aiohttp.ClientSession | None = None
        self._email = email
        self._password = password
        self._base_url = "https://mydewarmte.com"
        self._token: str | None = None

    async def __aenter__(self) -> DeWarmteApiClient:
        """Create a session when entering context manager."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the session when exiting context manager."""
        if self._session:
            await self._session.close()

    async def async_login(self) -> bool:
        """Login to the DeWarmte website."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            # First get the login page to get any necessary tokens
            async with self._session.get(f"{self._base_url}/login") as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get login page")
                    return False
                
                # Parse the login page to get any necessary tokens
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Find the login form and submit it
                login_data = {
                    "email": self._email,
                    "password": self._password,
                }
                
                async with self._session.post(
                    f"{self._base_url}/login",
                    data=login_data,
                    allow_redirects=True
                ) as login_response:
                    if login_response.status != 200:
                        _LOGGER.error("Login failed")
                        return False
                    
                    # Check if we're redirected to the dashboard
                    if "/dashboard" in str(login_response.url):
                        return True
                    
                    return False
        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False

    async def async_get_dashboard_data(self) -> dict[str, Any]:
        """Get data from the dashboard."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            async with self._session.get(f"{self._base_url}/dashboard") as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get dashboard data")
                    return {}
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Extract relevant data from the dashboard
                data = {}
                
                # Example: Get current temperature
                temp_element = soup.find("div", {"class": "temperature"})
                if temp_element:
                    data["temperature"] = float(temp_element.text.strip().replace("°C", ""))
                
                # Example: Get system status
                status_element = soup.find("div", {"class": "system-status"})
                if status_element:
                    data["status"] = status_element.text.strip()
                
                return data
        except Exception as err:
            _LOGGER.error("Error getting dashboard data: %s", err)
            return {} 