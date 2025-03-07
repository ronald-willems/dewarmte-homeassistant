"""API client for DeWarmte."""
from __future__ import annotations

import logging
from typing import Any
import re
import ssl
import asyncio
from contextlib import asynccontextmanager

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
        self._username = username
        self._password = password
        self._base_url = "https://mydewarmte.com"
        self._csrf_token: str | None = None
        self._status_url: str | None = None
        
        # Create connector with SSL context
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        self._connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://mydewarmte.com",
            "Referer": "https://mydewarmte.com/"
        }
        
        self._session: aiohttp.ClientSession | None = None
        self._session_lock = asyncio.Lock()

    @asynccontextmanager
    async def _get_session(self):
        """Get or create a session."""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(connector=self._connector)
            try:
                yield self._session
            except Exception as e:
                _LOGGER.error("Session error: %s", e)
                if self._session and not self._session.closed:
                    await self._session.close()
                self._session = None
                raise

    async def _get_csrf_token(self) -> str | None:
        """Get CSRF token from login page."""
        try:
            async with self._get_session() as session:
                async with session.get(
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

    async def async_login(self) -> bool:
        """Login to the DeWarmte website."""
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
            
            _LOGGER.debug("Attempting login with data: %s", login_data)

            async with self._get_session() as session:
                async with session.post(
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
                        return False

                    # Store status URL for future use
                    response_url = str(response.url)
                    if "/status/" in response_url:
                        self._status_url = response_url
                        _LOGGER.debug("Found status URL: %s", self._status_url)
                        return True
                    
                    _LOGGER.error("Login succeeded but no status URL found. Response URL: %s", response_url)
                    html = await response.text()
                    _LOGGER.debug("Response content: %s", html[:500])
                    return False

        except Exception as err:
            _LOGGER.error("Error during login: %s", err)
            return False

    async def async_get_status_data(self) -> dict[str, Any]:
        """Get data from the status page."""
        if not self._status_url:
            _LOGGER.error("No status URL available")
            return {}

        try:
            async with self._get_session() as session:
                _LOGGER.debug("Fetching status page: %s", self._status_url)
                async with session.get(
                    self._status_url,
                    headers=self._headers,
                    ssl=False
                ) as response:
                    if response.status != 200:
                        _LOGGER.error("Failed to get status page: %d", response.status)
                        return {}

                    html = await response.text()
                    _LOGGER.debug("Status page content: %s", html[:500])
                    
                    soup = BeautifulSoup(html, "html.parser")
                    data = {}

                    # Find all divs with values
                    for label_elem in soup.find_all("label"):
                        label_text = label_elem.get_text().strip().lower()
                        _LOGGER.debug("Found label: %s", label_text)
                        
                        if label_text in LABEL_TO_SENSOR:
                            # Find the next div with the value
                            value_div = label_elem.find_next("div")
                            if value_div:
                                value_text = value_div.get_text().strip()
                                _LOGGER.debug("Found value for %s: %s", label_text, value_text)
                                
                                try:
                                    # Extract numeric value and unit
                                    match = re.match(r"(-?\d+\.?\d*)\s*([°C%])?", value_text)
                                    if match:
                                        value = float(match.group(1))
                                        unit = match.group(2) or ""
                                        sensor_id = LABEL_TO_SENSOR[label_text]
                                        data[sensor_id] = {
                                            "value": value,
                                            "unit": unit
                                        }
                                        _LOGGER.debug("Parsed value for %s: %s %s", sensor_id, value, unit)
                                except ValueError as err:
                                    _LOGGER.error("Error parsing value for %s: %s", label_text, err)
                                    continue

                    # Extract status information
                    status_div = soup.find("div", class_=lambda x: x and "status" in x)
                    if status_div:
                        status_text = status_div.get_text().strip()
                        # Truncate status text to avoid length issues
                        status_text = status_text[:250] if status_text else "Unknown"
                        data[SENSOR_STATUS] = status_text
                        _LOGGER.debug("Found status: %s", status_text)
                    else:
                        _LOGGER.debug("No status div found")

                    _LOGGER.debug("Collected data: %s", data)
                    return data

        except Exception as err:
            _LOGGER.error("Error getting status data: %s", err)
            return {}

    async def __aenter__(self) -> DeWarmteApiClient:
        """Create a session when entering context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close the session when exiting context manager."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None 