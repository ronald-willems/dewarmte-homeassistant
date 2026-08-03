"""Home Assistant services for DeWarmte forced cooling.

Kept deliberately separate from the entity platforms: these are domain-level
services that target a device (via the HA device registry) and drive the
forced-cooling API directly. The `switch.forced_cooling` entity covers simple
on/off; these services add setpoint/duration control.
"""
from __future__ import annotations

import logging
from typing import Iterator

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api.client import DeWarmteApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_START_FORCED_COOLING = "start_forced_cooling"
SERVICE_STOP_FORCED_COOLING = "stop_forced_cooling"

ATTR_DEVICE_ID = "device_id"
ATTR_SETPOINT = "setpoint"
ATTR_DURATION_HOURS = "duration_hours"

MIN_SETPOINT = 10.0
MAX_SETPOINT = 25.0
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 72

_DEVICE_IDS = vol.All(cv.ensure_list, [cv.string])

START_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): _DEVICE_IDS,
        vol.Required(ATTR_SETPOINT): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_SETPOINT, max=MAX_SETPOINT)
        ),
        vol.Required(ATTR_DURATION_HOURS): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_DURATION_HOURS, max=MAX_DURATION_HOURS)
        ),
    }
)

STOP_SCHEMA = vol.Schema({vol.Required(ATTR_DEVICE_ID): _DEVICE_IDS})


def _iter_coordinators(hass: HomeAssistant) -> Iterator:
    """Yield every DeWarmte coordinator across all config entries."""
    for coordinators in hass.data.get(DOMAIN, {}).values():
        if isinstance(coordinators, list):
            yield from coordinators
        else:
            yield coordinators


def _coordinators_for_targets(hass: HomeAssistant, ha_device_ids: list[str]) -> list:
    """Resolve HA device-registry ids to their DeWarmte coordinators."""
    device_registry = dr.async_get(hass)
    coordinators = []
    for ha_device_id in ha_device_ids:
        entry = device_registry.async_get(ha_device_id)
        if entry is None:
            raise HomeAssistantError(f"Unknown device: {ha_device_id}")
        match = next(
            (
                c
                for c in _iter_coordinators(hass)
                if c.device is not None
                and (DOMAIN, c.device.device_id) in entry.identifiers
            ),
            None,
        )
        if match is None:
            raise HomeAssistantError(f"{ha_device_id} is not a DeWarmte device")
        coordinators.append(match)
    return coordinators


def async_setup_services(hass: HomeAssistant) -> None:
    """Register DeWarmte services once."""
    if hass.services.has_service(DOMAIN, SERVICE_START_FORCED_COOLING):
        return

    async def _handle_start(call: ServiceCall) -> None:
        duration_seconds = call.data[ATTR_DURATION_HOURS] * 3600
        setpoint = call.data[ATTR_SETPOINT]
        for coordinator in _coordinators_for_targets(hass, call.data[ATTR_DEVICE_ID]):
            try:
                await coordinator.api.async_start_forced_cooling(
                    coordinator.device, setpoint, duration_seconds
                )
            except DeWarmteApiError as err:
                raise HomeAssistantError(str(err)) from err
            await coordinator.async_request_refresh()

    async def _handle_stop(call: ServiceCall) -> None:
        for coordinator in _coordinators_for_targets(hass, call.data[ATTR_DEVICE_ID]):
            try:
                await coordinator.api.async_stop_forced_cooling(coordinator.device)
            except DeWarmteApiError as err:
                raise HomeAssistantError(str(err)) from err
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_START_FORCED_COOLING, _handle_start, schema=START_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_FORCED_COOLING, _handle_stop, schema=STOP_SCHEMA
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove DeWarmte services (call when the last config entry unloads)."""
    for service in (SERVICE_START_FORCED_COOLING, SERVICE_STOP_FORCED_COOLING):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
