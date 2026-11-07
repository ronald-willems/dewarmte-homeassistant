"""Telling the user how the import is doing: in the log, the bell and the options screen."""
from __future__ import annotations

import logging
from datetime import date, datetime

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from ..api.models.device import Device
from ..const import DOMAIN
from .store import ImportedStatistics

_LOGGER = logging.getLogger(__name__)


class ImportStatus:
    """How one heat pump's import is doing.

    Only the first import goes to the bell. Catching up after a restart or an
    outage, and the hourly top-up, are routine and only logged at DEBUG.
    """

    def __init__(self, hass: HomeAssistant, device: Device) -> None:
        self._hass = hass
        self._device = device
        self._first_import = False
        # Set by the importer for the whole run, from its very first request.
        self.running = False
        self.problem: str | None = None

    def started(self, first_day: date, days: int, *, first_import: bool) -> None:
        self._first_import = first_import
        _LOGGER.log(self._log_level, "Importing DeWarmte energy history for %s from %s (%d days)",
                    self._device.device_id, first_day, days)
        if self._first_import:
            self._notify(
                f"Importing the energy history of {self._name} from {first_day:%-d %B %Y}. "
                "This runs in the background and can take several minutes."
            )

    def finished(self, stored: ImportedStatistics) -> None:
        self.problem = None
        _LOGGER.log(self._log_level, "Energy history for %s complete: %d hours imported",
                    self._device.device_id, stored.hours_added)
        if self._first_import:
            self._notify(
                f"Imported {stored.hours_added:,} hours of energy history for {self._name}, "
                f"up to {_readable(stored.next_hour)}. You can use them in the Energy dashboard."
            )

    def stopped_early(self, error: Exception) -> None:
        self.problem = str(error)
        _LOGGER.warning("Energy history import for %s stopped early: %s",
                        self._device.device_id, error)
        if self._first_import:
            self._notify(
                f"The energy history import for {self._name} stopped early: {error}. "
                "It carries on from where it stopped within the hour."
            )

    @property
    def _name(self) -> str:
        return self._device.info.name

    @property
    def _log_level(self) -> int:
        return logging.INFO if self._first_import else logging.DEBUG

    def _notify(self, message: str) -> None:
        persistent_notification.async_create(
            self._hass, message, title="DeWarmte energy history",
            notification_id=notification_id(self._device),
        )


async def async_describe(hass: HomeAssistant, device: Device, status: ImportStatus | None) -> str:
    """One line for the options screen: running, imported up to when, or nothing yet."""
    if status is not None and status.running:
        return "import running…"
    stored = await ImportedStatistics.load(hass, device)
    if stored.next_hour is None:
        return "nothing imported"
    text = f"imported up to {_readable(stored.next_hour)}"
    if status is not None and status.problem:
        text += f"; the last run stopped early: {status.problem}"
    return text


def dismiss_notification(hass: HomeAssistant, device: Device) -> None:
    persistent_notification.async_dismiss(hass, notification_id(device))


def notification_id(device: Device) -> str:
    return f"{DOMAIN}_energy_history_{device.device_id}"


def _readable(instant: datetime | None) -> str:
    if instant is None:
        return "now"
    return format(dt_util.as_local(instant), "%-d %B %Y %H:%M")
