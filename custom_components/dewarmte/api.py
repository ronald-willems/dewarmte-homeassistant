"""API client for DeWarmte."""
from __future__ import annotations

import logging
import ssl
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from .const import (
    SENSOR_WATER_FLOW,
    SENSOR_SUPPLY_TEMP,
    SENSOR_OUTSIDE_TEMP,
    SENSOR_HEAT_INPUT,
    SENSOR_RETURN_TEMP,
    SENSOR_ELEC_CONSUMP,
    SENSOR_PUMP_AO_STATE,
    SENSOR_HEAT_OUTPUT,
    SENSOR_BOILER_STATE,
    SENSOR_THERMOSTAT_STATE,
    SENSOR_TOP_TEMP,
    SENSOR_BOTTOM_TEMP,
    SENSOR_HEAT_OUTPUT_PUMP_T,
    SENSOR_ELEC_CONSUMP_PUMP_T,
    SENSOR_PUMP_T_STATE,
    SENSOR_PUMP_T_HEATER_STATE,
)

_LOGGER = logging.getLogger(__name__)

class DeWarmteApiClient:
    """Client for interacting with the DeWarmte API."""

    def __init__(self, username: str, password: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client."""
        self._username = username
        self._password = password
        self._base_url = "https://mydewarmte.com"
        self._csrf_token: str | None = None
        self._status_url: str | None = None
        self._device_id: str | None = None
        self._product_id: str | None = None
        self._session = session
        
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
                    return False

                # Store status URL and extract device/product IDs
                response_url = str(response.url)
                if "/status/" in response_url:
                    self._status_url = response_url
                    # Extract device and product IDs from URL like /status/859/A-534/
                    parts = response_url.strip('/').split('/')
                    if len(parts) >= 4:
                        self._device_id = parts[-2]
                        self._product_id = parts[-1]
                        _LOGGER.debug("Found device_id: %s, product_id: %s", self._device_id, self._product_id)
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
        if not self._device_id or not self._product_id:
            _LOGGER.error("No device ID or product ID available")
            return {}

        try:
            # Get the status page
            async with self._session.get(
                self._status_url,
                headers=self._headers,
                ssl=False
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get status page: %d", response.status)
                    return {}

                html = await response.text()
                _LOGGER.debug("Status page HTML received")

                # Parse the HTML
                soup = BeautifulSoup(html, "html.parser")
                data = {}

                # Define variable mappings
                var_mappings = {
                    "WaterFlow": (SENSOR_WATER_FLOW, float, "L/min"),
                    "SupplyTemp": (SENSOR_SUPPLY_TEMP, float, "°C"),
                    "OutSideTemp": (SENSOR_OUTSIDE_TEMP, float, "°C"),
                    "HeatInput": (SENSOR_HEAT_INPUT, float, "kW"),
                    "ReturnTemp": (SENSOR_RETURN_TEMP, float, "°C"),
                    "ElecConsump": (SENSOR_ELEC_CONSUMP, float, "kW"),
                    "PompAoOnOff": (SENSOR_PUMP_AO_STATE, int, None),
                    "HeatOutPut": (SENSOR_HEAT_OUTPUT, float, "kW"),
                    "BoilerOnOff": (SENSOR_BOILER_STATE, int, None),
                    "ThermostatOnOff": (SENSOR_THERMOSTAT_STATE, int, None),
                    "TopTemp": (SENSOR_TOP_TEMP, float, "°C"),
                    "BottomTemp": (SENSOR_BOTTOM_TEMP, float, "°C"),
                    "HeatOutputPompT": (SENSOR_HEAT_OUTPUT_PUMP_T, float, "kW"),
                    "ElecConsumpPompT": (SENSOR_ELEC_CONSUMP_PUMP_T, float, "kW"),
                    "PompTOnOff": (SENSOR_PUMP_T_STATE, int, None),
                    "PompTHeaterOnOff": (SENSOR_PUMP_T_HEATER_STATE, int, None)
                }

                # Find all script tags
                for script in soup.find_all("script"):
                    script_text = script.string
                    if not script_text:
                        continue

                    # Process each variable mapping
                    for var_name, (sensor_name, convert_func, unit) in var_mappings.items():
                        pattern = f'var\\s+{var_name}\\s*=\\s*"([^"]*)"'
                        match = re.search(pattern, script_text)
                        if match:
                            try:
                                value = convert_func(match.group(1))
                                data_entry = {"value": value}
                                if unit:
                                    data_entry["unit"] = unit
                                data[sensor_name] = data_entry
                                _LOGGER.debug(f"Found {sensor_name}: {value} {unit if unit else ''}")
                            except (ValueError, TypeError) as err:
                                _LOGGER.error(f"Error parsing {sensor_name}: {err}")

                if not data:
                    _LOGGER.error("No data found in status page")
                    return {}

                _LOGGER.info(f"Successfully parsed {len(data)} values from status page")
                return data

        except Exception as err:
            _LOGGER.error("Error getting status data: %s", err)
            return {}

    async def async_get_basic_settings(self) -> dict[str, Any]:
        """Get basic settings from the settings page."""
        if not self._device_id or not self._product_id:
            _LOGGER.error("No device ID or product ID available")
            return {}

        try:
            settings_url = f"{self._base_url}/basic_settings/{self._device_id}/{self._product_id}/"
            async with self._session.get(
                settings_url,
                headers=self._headers,
                ssl=False
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get basic settings page: %d", response.status)
                    return {}

                html = await response.text()
                _LOGGER.debug("Basic settings page HTML received")

                # Parse the HTML
                soup = BeautifulSoup(html, "html.parser")
                data = {}

                # Find all checkboxes in the form
                checkboxes = soup.find_all("input", type="checkbox")
                for checkbox in checkboxes:
                    name = checkbox.get("name")
                    if name:
                        is_checked = checkbox.get("checked") is not None
                        data[name] = {"value": is_checked}
                        _LOGGER.debug(f"Found setting {name}: {is_checked}")

                if not data:
                    _LOGGER.error("No settings found in basic settings page")
                    return {}

                _LOGGER.info(f"Successfully parsed {len(data)} settings")
                return data

        except Exception as err:
            _LOGGER.error("Error getting basic settings: %s", err)
            return {}

    async def async_update_basic_setting(self, setting_name: str, value: bool) -> bool:
        """Update a single basic setting while preserving others."""
        try:
            # First get current settings
            current_settings = await self.async_get_basic_settings()
            if not current_settings:
                return False

            # Prepare the form data with all current settings
            form_data = {
                "csrfmiddlewaretoken": self._csrf_token,
            }
            
            # Add all current settings to the form data
            for name, setting in current_settings.items():
                # Update the specific setting we want to change
                if name == setting_name:
                    form_data[name] = "on" if value else ""
                else:
                    # Keep other settings as they are
                    form_data[name] = "on" if setting["value"] else ""

            # Submit the form
            settings_url = f"{self._base_url}/basic_settings/{self._device_id}/{self._product_id}/"
            async with self._session.post(
                settings_url,
                data=form_data,
                headers=self._headers,
                allow_redirects=True,
                ssl=False
            ) as response:
                success = response.status == 200
                if not success:
                    _LOGGER.error("Failed to update basic setting %s: %d", setting_name, response.status)
                return success

        except Exception as err:
            _LOGGER.error("Error updating basic setting %s: %s", setting_name, err)
            return False 