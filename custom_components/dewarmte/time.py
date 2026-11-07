"""Time platform for DeWarmte integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import cast

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DeWarmteDataUpdateCoordinator, _LOGGER
from .const import DOMAIN
from .api.client import DeWarmteApiError

# The API reads and writes these as "HH:MM" strings (GET settings/ returns
# e.g. "00:00"; OPTIONS settings/legionella/ declares the field a `time`).
TIME_FORMAT = "%H:%M"

@dataclass(frozen=True)
class DeWarmteTimeEntityDescription(TimeEntityDescription):
    """Class describing DeWarmte time entities."""
    device_types: tuple[str, ...] = ("PT",)  # Device types this time applies to

TIME_DESCRIPTIONS = {
    "legionella_protection_time": DeWarmteTimeEntityDescription(
        key="legionella_protection_time",
        name="Legionella Protection Time",
        device_types=("PT",),  # PT-specific: start time of the weekly disinfecting run
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DeWarmte time entities."""
    coordinators = hass.data[DOMAIN][entry.entry_id]

    if not isinstance(coordinators, list):
        coordinators = [coordinators]

    for coordinator in coordinators:
        entities = [
            DeWarmteTimeEntity(coordinator, description)
            for description in TIME_DESCRIPTIONS.values()
            if coordinator.device.device_type in description.device_types
        ]

        _LOGGER.debug("Adding %d time entities for device %s (type: %s)",
                     len(entities),
                     coordinator.device.device_id if coordinator.device else "unknown",
                     coordinator.device.device_type)

        if entities:
            async_add_entities(entities)

class DeWarmteTimeEntity(CoordinatorEntity[DeWarmteDataUpdateCoordinator], TimeEntity): # type: ignore[override]
    """Representation of a DeWarmte time entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DeWarmteDataUpdateCoordinator,
        description: DeWarmteTimeEntityDescription,
    ) -> None:
        """Initialize the time entity."""
        super().__init__(coordinator)
        assert coordinator.device is not None, "Coordinator device must not be None"
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def dewarmte_description(self) -> DeWarmteTimeEntityDescription:
        """Get the DeWarmte specific entity description."""
        return cast(DeWarmteTimeEntityDescription, self.entity_description)

    @property
    def native_value(self) -> time | None:  # type: ignore[override]
        """Return the current value."""
        # Settings are cached in coordinator, read from there
        if not hasattr(self.coordinator, '_cached_settings') or not self.coordinator._cached_settings:
            return None

        value = getattr(self.coordinator._cached_settings, self.dewarmte_description.key, None)
        if value is None:
            return None
        try:
            return time.fromisoformat(value)
        except ValueError:
            _LOGGER.warning("Unexpected %s value from the API: %r", self.dewarmte_description.key, value)
            return None

    async def async_set_value(self, value: time) -> None:
        """Change the time."""
        try:
            await self.coordinator.async_write_setting(
                self.dewarmte_description.key, value.strftime(TIME_FORMAT)
            )
        except DeWarmteApiError as err:
            # Surface the API's reason (e.g. a rejected value) instead of an
            # "Unexpected error" toast with no explanation.
            raise HomeAssistantError(str(err)) from err
