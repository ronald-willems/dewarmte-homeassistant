"""API client for DeWarmte."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple
import asyncio

import aiohttp
from bs4 import BeautifulSoup

from .auth import DeWarmteAuth
from .models import ValueUnit
from .models.device import Device, DeviceInfo, DeviceState, DeviceSensor
from .models.sensor import SENSOR_DEFINITIONS, SensorDefinition, SensorDeviceClass
from .models.settings import ConnectionSettings, IntegrationSettings

_LOGGER = logging.getLogger(__name__)

class DeWarmteApiClient:
    """Client for interacting with the DeWarmte API."""

    def __init__(
        self, 
        connection_settings: ConnectionSettings,
        session: aiohttp.ClientSession
    ) -> None:
        """Initialize the client."""
        self._auth = DeWarmteAuth(
            connection_settings.username,
            connection_settings.password,
            session
        )
        self._session = session
        self._csrf_token: Optional[str] = None
        self._device: Optional[Device] = None
        self._connection_settings = connection_settings

    @property
    def device(self) -> Optional[Device]:
        """Get the current device."""
        return self._device

    async def async_login(self) -> bool:
        """Login to the DeWarmte website."""
        success, csrf_token, device_id, product_id = await self._auth.login()
        if success and csrf_token and device_id and product_id:
            self._csrf_token = csrf_token
            self._device = Device(
                device_id=device_id,
                info=DeviceInfo(
                    name=f"DeWarmte {device_id}",
                    model=product_id,
                ),
                state=DeviceState(online=True),
                sensors={}
            )
            return True
        return False

    async def async_get_status_data(self) -> Dict[str, DeviceSensor]:
        """Get data from the status page."""
        if not self._device:
            _LOGGER.error("No device available")
            return {}

        try:
            # Get the status page
            status_url = f"{self._auth.base_url}/status/{self._device.device_id}/{self._device.info.model}/"
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
                sensors: Dict[str, DeviceSensor] = {}

                # Find all script tags
                for script in soup.find_all("script"):
                    script_text = script.string
                    if not script_text:
                        continue

                    # Process each sensor definition
                    for key, definition in SENSOR_DEFINITIONS.items():
                        pattern = f'var\\s+{definition.var_name}\\s*=\\s*"([^"]*)"'
                        match = re.search(pattern, script_text)
                        if match:
                            try:
                                value = definition.convert_func(match.group(1))
                                sensors[key] = DeviceSensor(
                                    definition=definition,
                                    state=ValueUnit(
                                        value=value,
                                        unit=definition.unit
                                    )
                                )
                                _LOGGER.debug(
                                    f"Found {definition.name}: {value} "
                                    f"{definition.unit if definition.unit else ''}"
                                )
                            except (ValueError, TypeError) as err:
                                _LOGGER.error(f"Error parsing {definition.name}: {err}")

                if not sensors:
                    _LOGGER.error("No data found in status page")
                    return {}

                # Update device sensors
                self._device.sensors = sensors
                _LOGGER.info(f"Successfully parsed {len(sensors)} values from status page")
                return sensors

        except Exception as err:
            _LOGGER.error("Error getting status data: %s", err)
            return {}

    async def async_get_basic_settings(self) -> Dict[str, DeviceSensor]:
        """Get basic settings from the settings page."""
        if not self._device:
            _LOGGER.error("No device available")
            return {}

        try:
            settings_url = f"{self._auth.base_url}/basic_settings/{self._device.device_id}/{self._device.info.model}/"
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
                settings: Dict[str, DeviceSensor] = {}

                # Find all checkboxes in the form
                checkboxes = soup.find_all("input", type="checkbox")
                for checkbox in checkboxes:
                    name = checkbox.get("name")
                    if name:
                        is_checked = checkbox.get("checked") is not None
                        # Create a sensor definition for this setting
                        settings[name] = DeviceSensor(
                            definition=SensorDefinition(
                                key=name,
                                name=name.replace("_", " ").title(),
                                var_name=name,
                                device_class=SensorDeviceClass.ENUM,
                                state_class=None,
                                unit=None,
                                convert_func=bool
                            ),
                            state=ValueUnit(
                                value=is_checked,
                                unit=None
                            )
                        )
                        _LOGGER.debug(f"Found setting {name}: {is_checked}")

                if not settings:
                    _LOGGER.error("No settings found in basic settings page")
                    return {}

                _LOGGER.info(f"Successfully parsed {len(settings)} settings")
                return settings

        except Exception as err:
            _LOGGER.error("Error getting basic settings: %s", err)
            return {}

    async def async_update_basic_setting(self, setting_name: str, value: bool) -> bool:
        """Update a basic setting."""
        if not self._device:
            _LOGGER.error("No device available")
            return False

        try:
            # Get the settings page to get the current CSRF token
            settings_url = f"{self._auth.base_url}/basic_settings/{self._device.device_id}/{self._device.info.model}/"
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

                # Update headers with new CSRF token and referer
                headers = self._auth.headers.copy()
                headers.update({
                    "X-CSRFToken": csrf_token,
                    "Referer": settings_url,
                    "Origin": self._auth.base_url,
                })

                # Get all current form values to maintain state
                form_data = {"csrfmiddlewaretoken": csrf_token}
                checkboxes = soup.find_all("input", type="checkbox")
                for checkbox in checkboxes:
                    name = checkbox.get("name")
                    if name:
                        # Only update the target setting, keep others as is
                        if name == setting_name:
                            form_data[name] = "on" if value else ""
                        else:
                            form_data[name] = "on" if checkbox.get("checked") is not None else ""

                # Submit the form
                async with self._session.post(
                    settings_url,
                    data=form_data,
                    headers=headers,
                    ssl=False,
                    allow_redirects=True
                ) as response:
                    if response.status not in (200, 302):
                        _LOGGER.error("Failed to update setting: %d", response.status)
                        return False

                    # Update the device's settings if successful
                    if self._device and setting_name in self._device.sensors:
                        sensor = self._device.sensors[setting_name]
                        sensor.state.value = value

                    _LOGGER.info("Successfully updated %s to %s", setting_name, value)
                    return True

        except Exception as err:
            _LOGGER.error("Error updating setting: %s", err)
            return False 