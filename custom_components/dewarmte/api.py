"""API client for DeWarmte."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from .auth import DeWarmteAuth
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
        self._auth = DeWarmteAuth(username, password, session)
        self._session = session
        self._csrf_token: str | None = None
        self._device_id: str | None = None
        self._product_id: str | None = None

    async def async_login(self) -> bool:
        """Login to the DeWarmte website."""
        success, csrf_token, device_id, product_id = await self._auth.login()
        if success and csrf_token and device_id and product_id:
            self._csrf_token = csrf_token
            self._device_id = device_id
            self._product_id = product_id
            return True
        return False

    async def async_get_status_data(self) -> dict[str, Any]:
        """Get data from the status page."""
        if not self._device_id or not self._product_id:
            _LOGGER.error("No device ID or product ID available")
            return {}

        try:
            # Get the status page
            status_url = f"{self._auth.base_url}/status/{self._device_id}/{self._product_id}/"
            async with self._session.get(
                status_url,
                headers=self._auth.headers,
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
            settings_url = f"{self._auth.base_url}/basic_settings/{self._device_id}/{self._product_id}/"
            async with self._session.get(
                settings_url,
                headers=self._auth.headers,
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
        """Update a basic setting."""
        if not self._device_id or not self._product_id or not self._csrf_token:
            _LOGGER.error("Missing required data for updating settings")
            return False

        try:
            # First get the settings page to get the current CSRF token
            settings_url = f"{self._auth.base_url}/basic_settings/{self._device_id}/{self._product_id}/"
            async with self._session.get(
                settings_url,
                headers=self._auth.headers,
                ssl=False
            ) as response:
                if response.status != 200:
                    _LOGGER.error("Failed to get settings page: %d", response.status)
                    return False

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
                if not csrf_input or not csrf_input.get("value"):
                    _LOGGER.error("No CSRF token found in settings page")
                    return False

                csrf_token = csrf_input.get("value")
                headers = self._auth.headers.copy()
                headers["X-CSRFToken"] = csrf_token

                # Prepare the form data
                form_data = {
                    "csrfmiddlewaretoken": csrf_token,
                    setting_name: "on" if value else ""
                }

                # Submit the form
                async with self._session.post(
                    settings_url,
                    data=form_data,
                    headers=headers,
                    ssl=False
                ) as response:
                    if response.status != 200:
                        _LOGGER.error("Failed to update setting: %d", response.status)
                        return False

                    _LOGGER.info(f"Successfully updated {setting_name} to {value}")
                    return True

        except Exception as err:
            _LOGGER.error("Error updating setting: %s", err)
            return False 