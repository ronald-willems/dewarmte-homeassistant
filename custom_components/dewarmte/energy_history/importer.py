"""Keep a heat pump's `dewarmte:` statistics in step with the portal."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

from homeassistant.core import HomeAssistant

from ..api.client import DeWarmteApiClient, DeWarmteApiError
from ..api.models.device import Device
from .portal import PortalHistory, dutch_day_of, today_in_the_netherlands
from .status import ImportStatus
from .store import ImportedStatistics

_LOGGER = logging.getLogger(__name__)

# Hand rows to the recorder in batches, without letting an interrupted run
# lose more than a month of work.
SAVE_EVERY_DAYS = 30


class EnergyHistoryImporter:
    """Imports every hour the portal has that Home Assistant does not."""

    def __init__(self, hass: HomeAssistant, api: DeWarmteApiClient, device: Device) -> None:
        self._hass = hass
        self._device = device
        self._portal = PortalHistory(api, device)
        self._lock = asyncio.Lock()
        self.status = ImportStatus(hass, device)

    async def async_catch_up(self) -> None:
        """Import the completed hours that are not stored yet.

        The first run walks years of history; later runs only the hours since.
        A run still in progress is left alone rather than started twice.
        """
        if self._lock.locked():
            _LOGGER.debug("Energy history import for %s already running", self._device.device_id)
            return
        async with self._lock:
            self.status.running = True
            try:
                await self._import_hours_not_stored_yet()
            except DeWarmteApiError as err:
                # Stop at the failing day. Skipping it would move the resume
                # point past a hole that no later run would come back to.
                self.status.stopped_early(err)
            finally:
                self.status.running = False

    async def async_catch_up_on_interval(self, _now: datetime) -> None:
        """`async_track_time_interval` action; the tick time itself is unused."""
        await self.async_catch_up()

    async def _import_hours_not_stored_yet(self) -> None:
        stored = await ImportedStatistics.load(self._hass, self._device)
        first_day = await self._first_day_to_import(stored)
        if first_day is None:
            _LOGGER.info("No energy history available for %s yet", self._device.device_id)
            return

        days = _days_from(first_day, until=today_in_the_netherlands())
        self.status.started(first_day, len(days), first_import=stored.next_hour is None)

        for count, day in enumerate(days, start=1):
            for hour in await self._portal.hours_of(day):
                if hour.has_ended():
                    stored.add(hour)
            if count % SAVE_EVERY_DAYS == 0:
                stored.save()
                _LOGGER.debug("Energy history for %s: %d days processed, up to %s",
                              self._device.device_id, count, day)

        stored.save()
        self.status.finished(stored)

    async def _first_day_to_import(self, stored: ImportedStatistics) -> date | None:
        """Carry on where the last run stopped, or find where the history begins."""
        if stored.next_hour is not None:
            return dutch_day_of(stored.next_hour)
        return await self._portal.find_first_day()


def _days_from(first: date, *, until: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((until - first).days + 1)]
