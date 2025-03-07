"""API client for DeWarmte."""
from __future__ import annotations

import logging
from typing import Any
import re

import aiohttp
from bs4 import BeautifulSoup

from .const import (
    SENSOR_SUPPLY_TEMPERATURE,
    SENSOR_RETURN_TEMPERATURE,
    SENSOR_ROOM_TEMPERATURE,
    SENSOR_OUTSIDE_TEMPERATURE,
    SENSOR_TARGET_TEMPERATURE,
    SENSOR_HEAT_DEMAND,
    SENSOR_VALVE_POSITION,
    SENSOR_STATUS,
)

_LOGGER = logging.getLogger(__name__)

# Mapping of Dutch labels to sensor keys
LABEL_TO_SENSOR = {
    "aanvoer temperatuur": SENSOR_SUPPLY_TEMPERATURE,
    "retour temperatuur": SENSOR_RETURN_TEMPERATURE,
    "kamer temperatuur": SENSOR_ROOM_TEMPERATURE,
    "buiten temperatuur": SENSOR_OUTSIDE_TEMPERATURE,
    "gewenste temperatuur": SENSOR_TARGET_TEMPERATURE,
    "warmtevraag": SENSOR_HEAT_DEMAND,
    "klepstand": SENSOR_VALVE_POSITION,
}

class DeWarmteApiClient:
    """Client for interacting with the DeWarmte API."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the client."""
        self._session: aiohttp.ClientSession | None = None
        self._username = username
        self._password = password
        self._base_url = "https://mydewarmte.com"
        self._csrf_token: str | None = None
        self._status_url: str | None = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://mydewarmte.com",
            "Referer": "https://mydewarmte.com/"
        }

    async def __aenter__(self) -> DeWarmteApiClient:
        """Create a session when entering context manager."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the session when exiting context manager."""
        if self._session:
            await self._session.close()

    async def _get_csrf_token(self) -> str | None:
        """Get CSRF token from login page."""
        if not self._session:
            return None

        try:
            async with self._session.get(
                f"{self._base_url}/",
                headers=self._headers
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get login page")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
                if csrf_input:
                    return csrf_input.get("value")
        except Exception as err:
            _LOGGER.error("Error getting CSRF token: %s", err)
        return None

    async def async_login(self) -> bool:
        """Login to the DeWarmte website."""
        if not self._session:
            self._session = aiohttp.ClientSession()

        try:
            # Get CSRF token
            self._csrf_token = await self._get_csrf_token()
            if not self._csrf_token:
                return False

            # Update headers with CSRF token
            self._headers["X-CSRFToken"] = self._csrf_token

            # Submit login form
            login_data = {
                "username": self._username,
                "password": self._password,
                "csrfmiddlewaretoken": self._csrf_token
            }

            async with self._session.post(
                f"{self._base_url}/",
                data=login_data,
                headers=self._headers,
                allow_redirects=True
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Login failed with status %d", response.status)
                    return False

                # Store status URL for future use
                if "/status/" in str(response.url):
                    self._status_url = str(response.url)
                    return True
                return False

        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False

    async def async_get_status_data(self) -> dict[str, Any]:
        """Get data from the status page."""
        if not self._session or not self._status_url:
            return {}

        try:
            async with self._session.get(
                self._status_url,
                headers=self._headers
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status page")
                    return {}

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                data = {}

                # Find all divs with values
                for label_elem in soup.find_all("label"):
                    label_text = label_elem.get_text().strip().lower()
                    if label_text in LABEL_TO_SENSOR:
                        # Find the next div with the value
                        value_div = label_elem.find_next("div")
                        if value_div:
                            value_text = value_div.get_text().strip()
                            try:
                                # Extract numeric value and unit
                                match = re.match(r"(-?\d+\.?\d*)\s*([°C%])?", value_text)
                                if match:
                                    value = float(match.group(1))
                                    unit = match.group(2) or ""
                                    data[LABEL_TO_SENSOR[label_text]] = {
                                        "value": value,
                                        "unit": unit
                                    }
                            except ValueError:
                                continue

                # Extract status information
                status_div = soup.find("div", class_=lambda x: x and "status" in x)
                if status_div:
                    data[SENSOR_STATUS] = status_div.get_text().strip()

                return data

        except Exception as err:
            _LOGGER.error("Error getting status data: %s", err)
            return {} 