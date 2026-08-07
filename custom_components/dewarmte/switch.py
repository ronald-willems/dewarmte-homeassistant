"""Switch platform for DeWarmte integration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast, final

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator
from .const import DOMAIN
from .api.client import DeWarmteApiError
from .api.models.settings import SETTING_GROUPS, DeviceOperationSettings

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class DeWarmteSwitchEntityDescription(SwitchEntityDescription):
    """Class describing DeWarmte switch entities."""
    icon: str | None = None
    translation_key: str | None = None
    device_types: tuple[str, ...] = ("AO", "PT", "HC")  # Device types this switch applies to

SWITCH_DESCRIPTIONS = {
    "advanced_boost_mode_control": DeWarmteSwitchEntityDescription(
        key="advanced_boost_mode_control",
        name="Boost Mode",
        icon="mdi:rocket-launch",
        device_types=("AO", "MP"),  # AO/MP-specific: boost mode for space heating
    ),
}

# Forced ("cool now") cooling is deliberately kept out of SWITCH_DESCRIPTIONS:
# unlike every other switch it is not a boolean setting written through the
# settings endpoints, but a pair of dedicated start/stop commands that need a
# setpoint and a duration. Only the entity differs, so the description still
# carries the metadata (name, icon, device gating) like the others do.
FORCED_COOLING_DESCRIPTION = DeWarmteSwitchEntityDescription(
    key="forced_cooling",
    name="Forced Cooling",
    icon="mdi:snowflake",
    device_types=("AO", "MP"),  # AO/MP-specific, and only when cooling is supported
)

# The DeWarmte app's own default for "cool now"; used when the device has no
# cooling duration configured yet (a fresh device reports 0, which would ask the
# API for a zero-length run).
DEFAULT_FORCED_COOLING_DURATION = 7200  # 2 hours in seconds


def forced_cooling_params(settings: DeviceOperationSettings) -> tuple[float, int]:
    """Return the (setpoint, duration_seconds) a bare on/off toggle should use.

    The toggle carries no parameters, so it reuses the two cooling settings the
    user can already edit (`Cooling Temperature` and `Cooling Duration`). Kept a
    module-level function rather than a method so it can be tested on its own.
    """
    duration = settings.cooling_duration
    if duration <= 0:
        duration = DEFAULT_FORCED_COOLING_DURATION
    return settings.cooling_temperature, duration

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte switch platform."""
    coordinators = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Setting up DeWarmte switch platform")

    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        # Filter switch descriptions by device type
        filtered_descriptions = [
            description for description in SWITCH_DESCRIPTIONS.values()
            if coordinator.device.device_type in description.device_types
        ]
        
        switches: list[SwitchEntity] = [
            DeWarmteSwitchEntity(coordinator, description)
            for description in filtered_descriptions
            if hasattr(coordinator, '_cached_settings') and coordinator._cached_settings is not None
        ]

        # Forced cooling: same device gating as the settings switches, plus the
        # cooling capability, but its own entity (start/stop commands).
        if (
            coordinator.device.device_type in FORCED_COOLING_DESCRIPTION.device_types
            and coordinator.device.supports_cooling
            and getattr(coordinator, '_cached_settings', None) is not None
        ):
            switches.append(
                DeWarmteForcedCoolingSwitch(coordinator, FORCED_COOLING_DESCRIPTION)
            )

        _LOGGER.debug("Adding %d switches for device %s (type: %s)",
                     len(switches),
                     coordinator.device.device_id if coordinator.device else "unknown",
                     coordinator.device.device_type)
        
        if switches:
            async_add_entities(switches)

@final
class DeWarmteSwitchEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SwitchEntity):  # type: ignore[override]
    """Representation of a DeWarmte switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteSwitchEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteSwitchEntityDescription, self.entity_description)

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        # Settings are cached in coordinator, read from there
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return None

        settings = self.coordinator._cached_settings
        return getattr(settings, self.dewarmte_description.key) if settings else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""

        await self.coordinator.api.async_update_operation_settings(self.coordinator.device, self.dewarmte_description.key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""

        await self.coordinator.api.async_update_operation_settings(self.coordinator.device, self.dewarmte_description.key, False)
        await self.coordinator.async_request_refresh()


@final
class DeWarmteForcedCoolingSwitch(CoordinatorEntity[DeWarmteDataUpdateCoordinator], SwitchEntity):  # type: ignore[override]
    """Start/stop forced ("cool now") cooling.

    A sibling of DeWarmteSwitchEntity rather than a subclass: on/off map to the
    dedicated start-forced/stop-forced commands instead of writing a boolean
    setting, and turning on has to supply a setpoint and a duration.

    The run also ends on its own when the duration expires, so this switch can
    turn itself off without anyone touching it.

    Both commands finish with `async_refresh()` rather than the debounced
    `async_request_refresh()` the settings switches use: the API reflects
    is_force_cooling_active immediately, and waiting out the debounce makes the
    toggle visibly flip back to its old position for several seconds.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteSwitchEntityDescription,
    ) -> None:
        """Initialize the forced cooling switch."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        # Keep the historical key so the entity id stays stable for anyone who
        # used an earlier build of this switch.
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def _settings(self) -> DeviceOperationSettings | None:
        """Return the cached operation settings, if the first poll has landed."""
        return getattr(self.coordinator, '_cached_settings', None)

    @property
    def is_on(self) -> bool | None:
        """Return true while a forced cooling run is active."""
        settings = self._settings
        if settings is None:
            return None
        return settings.is_force_cooling_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start forced cooling using the configured cooling temperature/duration."""
        settings = self._settings
        if settings is None:
            raise HomeAssistantError(
                "Cannot start forced cooling: DeWarmte settings are not available yet"
            )

        setpoint, duration = forced_cooling_params(settings)
        _LOGGER.debug(
            "Starting forced cooling at %s degrees for %s seconds", setpoint, duration
        )
        try:
            await self.coordinator.api.async_start_forced_cooling(
                self.coordinator.device, setpoint, duration
            )
        except DeWarmteApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop an active forced cooling run."""
        try:
            await self.coordinator.api.async_stop_forced_cooling(self.coordinator.device)
        except DeWarmteApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_refresh()
