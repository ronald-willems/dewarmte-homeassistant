"""Replicate DeWarmte's own energy history into Home Assistant statistics.

The portal meters energy itself and exposes it as hourly buckets per product.
The integration's live `*_energy` sensors are Riemann sums over polled power, so
they approximate the same quantity but drift from it -- and overshoot badly when
a polling gap makes them integrate a stale reading across hours of downtime.

Rather than reconcile the two, this writes the portal's numbers as *external*
statistics under the `dewarmte:` namespace. They are a separate series with no
entity behind them: they show up in the Energy dashboard's source picker and in
statistics cards, never in the state machine. The user picks one series or the
other -- adding both to the Energy dashboard double-counts.

Only `hourly` is imported, because Home Assistant stores long-term statistics at
exactly one resolution (hourly rows) and derives every coarser view from them at
read time. The other timespans are used only to find where the history starts.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .api.client import DeWarmteApiClient, DeWarmteApiError
from .api.models.device import Device
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

try:  # Cores from 2025.5 want mean_type; the boolean stops working in 2026.11.
    from homeassistant.components.recorder.models import StatisticMeanType

    _MEAN_METADATA: dict[str, Any] = {"mean_type": StatisticMeanType.NONE}
except ImportError:  # pragma: no cover - older cores only know the boolean
    _MEAN_METADATA = {"has_mean": False}

# The bucket labels are Dutch wall-clock time, not UTC and not the user's own
# time zone: DeWarmte is a Dutch company metering pumps installed in NL. Reading
# them as `hass.config.time_zone` would shift the whole series for anyone whose
# Home Assistant is set to something else.
API_TIME_ZONE = ZoneInfo("Europe/Amsterdam")

# One request per day of history: a few thousand for a multi-device account with
# years of data. Nothing is waiting on the result, so stay unhurried.
REQUEST_DELAY = 0.3

# Hand rows to the recorder in batches instead of per day, without letting an
# interrupted run lose more than a month of work.
FLUSH_EVERY_DAYS = 30

# The three per-bucket energy fields. `temperature` is also present (null on AO,
# a boiler temperature on PT) but would need mean statistics, and the top-level
# `cop` is a ratio that cannot be summed -- neither belongs in this series.
#
# Note `electric_backup_usage` means different things per device type: on HC it
# is already contained in `electricity_consumed`, on PT the two are separate
# meters. It is imported for visibility, but only heat and electricity are safe
# to put in the Energy dashboard.
SERIES: tuple[tuple[str, str], ...] = (
    ("heat_supplied", "Heat supplied"),
    ("electricity_consumed", "Electricity consumed"),
    ("electric_backup_usage", "Electric backup usage"),
)


def statistic_id(device: Device, key: str) -> str:
    """Return the external statistic id for one series of one device.

    Home Assistant validates statistic ids as `[\\da-z_]+:[\\da-z_]+`, so the
    device's UUID has to lose its hyphens.
    """
    return f"{DOMAIN}:{slugify(device.device_id)}_{key}"


def all_statistic_ids(device: Device) -> list[str]:
    """Return every statistic id this module writes for a device."""
    return [statistic_id(device, key) for key, _name in SERIES]


def _local_midnight_utc(day: date) -> datetime:
    """Return the UTC instant at which the given Dutch calendar day starts."""
    return datetime.combine(day, time.min, tzinfo=API_TIME_ZONE).astimezone(timezone.utc)


def _expected_hours(day: date) -> list[tuple[datetime, str]]:
    """Return every real hour of a Dutch calendar day, with its wall-clock label.

    Normally 24 entries, 23 on the spring-forward day, 25 on the autumn one --
    where "02:00" legitimately appears twice, once in CEST and once in CET.
    """
    cursor = _local_midnight_utc(day)
    limit = _local_midnight_utc(day + timedelta(days=1))
    hours: list[tuple[datetime, str]] = []
    while cursor < limit:
        hours.append((cursor, format(cursor.astimezone(API_TIME_ZONE), "%H:00")))
        cursor += timedelta(hours=1)
    return hours


def hourly_buckets(day: date, buckets: list[dict[str, Any]]) -> Iterator[tuple[datetime, dict[str, Any]]]:
    """Pair each bucket of an `hourly` response with the UTC hour it covers.

    Neither the labels nor the positions can carry this on their own. The labels
    ("00:00".."23:00") are local wall clock, so on the autumn DST day "02:00"
    arrives twice and is ambiguous; but the positions cannot be trusted either,
    because the API drops hours it has no data for -- 2024-03-31 comes back with
    22 buckets starting at "01:00", and walking that positionally from midnight
    would shift the whole day an hour early.

    So walk the day's real hours and the returned buckets together, matching on
    the label and skipping over hours the API left out. Order settles the
    duplicate: the first "02:00" is the CEST one, the second the CET one.
    """
    expected = _expected_hours(day)
    index = 0
    for bucket in buckets:
        label = bucket.get("key")
        while index < len(expected) and expected[index][1] != label:
            index += 1
        if index >= len(expected):
            _LOGGER.warning(
                "Ignoring hourly bucket %s for %s: no such hour in that day (%d buckets returned)",
                label,
                day,
                len(buckets),
            )
            return
        yield expected[index][0], bucket
        index += 1


@dataclass
class _Series:
    """Accumulator for one statistic while an import is running."""

    key: str
    name: str
    statistic_id: str
    # First hour not yet imported; None when nothing has been imported at all.
    next_hour: datetime | None
    total: float
    rows: list[StatisticData] = field(default_factory=list)

    def add(self, start: datetime, value: float) -> None:
        """Record one hour, carrying the running total forward."""
        if self.next_hour is not None and start < self.next_hour:
            return
        self.total += value
        self.rows.append(StatisticData(start=start, state=value, sum=self.total))
        self.next_hour = start + timedelta(hours=1)


class EnergyHistoryImporter:
    """Keeps one device's `dewarmte:` statistics in step with the portal."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: DeWarmteApiClient,
        device: Device,
    ) -> None:
        """Initialize the importer for a single device."""
        self.hass = hass
        self._api = api
        self._device = device
        self._lock = asyncio.Lock()

    async def async_catch_up(self) -> None:
        """Import every completed hour that is not in the database yet.

        Safe to call repeatedly: the first run walks years of history, later
        ones only the hours since the last. Concurrent calls are dropped rather
        than queued, so a slow first import cannot be started twice.
        """
        if self._lock.locked():
            _LOGGER.debug(
                "Energy history import for %s already running; skipping this run",
                self._device.device_id,
            )
            return
        async with self._lock:
            try:
                await self._async_run()
            except DeWarmteApiError as err:
                # Stop rather than skip the failing day: skipping would move the
                # resume point past a hole we would never come back to. Whatever
                # was flushed stays, and the next run picks up from there.
                _LOGGER.warning(
                    "Energy history import for %s stopped early: %s",
                    self._device.device_id,
                    err,
                )

    async def _async_run(self) -> None:
        """Walk day by day from the resume point to the current hour."""
        series = await self._async_load_resume_state()
        started = [s.next_hour for s in series if s.next_hour is not None]

        if started:
            first_day = min(started).astimezone(API_TIME_ZONE).date()
        elif (first_day := await self._async_discover_first_day()) is None:
            _LOGGER.info(
                "No energy history available for %s yet", self._device.device_id
            )
            return

        # The hour in progress is still filling up, and rewriting an hour later
        # would not recompute the running totals of the hours after it. Import
        # only hours that are already complete.
        now = datetime.now(timezone.utc)
        cutoff = now.replace(minute=0, second=0, microsecond=0)
        last_day = now.astimezone(API_TIME_ZONE).date()

        _LOGGER.info(
            "Importing DeWarmte energy history for %s from %s (%d days)",
            self._device.device_id,
            first_day,
            (last_day - first_day).days + 1,
        )

        day = first_day
        days_done = 0
        imported = 0
        while day <= last_day:
            payload = await self._api.async_get_insights(
                self._device, timespan="hourly", start_date=day.isoformat()
            )
            for start, bucket in hourly_buckets(day, payload.get("data") or []):
                if start >= cutoff:
                    break
                for entry in series:
                    entry.add(start, float(bucket.get(entry.key) or 0.0))
                imported += 1

            day += timedelta(days=1)
            days_done += 1
            if days_done % FLUSH_EVERY_DAYS == 0:
                self._flush(series)
                _LOGGER.debug(
                    "Energy history for %s: %d days processed, up to %s",
                    self._device.device_id,
                    days_done,
                    day,
                )
            await asyncio.sleep(REQUEST_DELAY)

        self._flush(series)
        _LOGGER.info(
            "Energy history for %s complete: %d hours imported over %d days",
            self._device.device_id,
            imported,
            days_done,
        )

    async def _async_discover_first_day(self) -> date | None:
        """Find the month where hourly history begins.

        `yearly` says which years hold data, but hourly buckets do not go back
        as far as the aggregates do -- an account can report a full year of
        energy and return nothing at all for every day of it. So probe forward a
        month at a time for the first one that actually answers, then start at
        the beginning of that month. The 15th is the probe date because isolated
        days are missing here and there and the 1st is as likely as any to be
        one of them.
        """
        yearly = await self._api.async_get_insights(self._device, timespan="yearly")
        years = sorted(
            int(bucket["key"]) for bucket in yearly.get("data") or [] if bucket.get("key")
        )
        if not years:
            return None

        today = datetime.now(timezone.utc).astimezone(API_TIME_ZONE).date()
        probe = date(years[0], 1, 15)
        while probe <= today:
            payload = await self._api.async_get_insights(
                self._device, timespan="hourly", start_date=probe.isoformat()
            )
            if payload.get("data"):
                return probe.replace(day=1)
            probe = (probe.replace(day=28) + timedelta(days=7)).replace(day=15)
            await asyncio.sleep(REQUEST_DELAY)
        return None

    async def _async_load_resume_state(self) -> list[_Series]:
        """Read back where each series left off, and its running total."""
        recorder = get_instance(self.hass)
        series: list[_Series] = []
        for key, name in SERIES:
            stat_id = statistic_id(self._device, key)
            last = await recorder.async_add_executor_job(
                get_last_statistics, self.hass, 1, stat_id, True, {"sum"}
            )
            rows = last.get(stat_id) or []
            if rows and rows[0].get("sum") is not None:
                previous = datetime.fromtimestamp(rows[0]["start"], tz=timezone.utc)
                series.append(
                    _Series(
                        key=key,
                        name=name,
                        statistic_id=stat_id,
                        next_hour=previous + timedelta(hours=1),
                        total=float(rows[0]["sum"]),
                    )
                )
            else:
                series.append(
                    _Series(
                        key=key, name=name, statistic_id=stat_id, next_hour=None, total=0.0
                    )
                )
        return series

    def _flush(self, series: list[_Series]) -> None:
        """Hand the buffered rows to the recorder and start a new batch."""
        for entry in series:
            if not entry.rows:
                continue
            metadata = StatisticMetaData(
                has_sum=True,
                name=f"{self._device.info.name} {entry.name}",
                source=DOMAIN,
                statistic_id=entry.statistic_id,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                **_MEAN_METADATA,
            )
            async_add_external_statistics(self.hass, metadata, entry.rows)
            entry.rows = []


def async_delete_history(hass: HomeAssistant, device: Device) -> None:
    """Drop every imported statistic for a device.

    Long-term statistics outlive the config entry and are never purged by
    `purge_keep_days`, so without this an experiment with the import would leave
    rows behind for good.
    """
    ids = all_statistic_ids(device)
    _LOGGER.info("Deleting imported DeWarmte energy history: %s", ", ".join(ids))
    get_instance(hass).async_clear_statistics(ids)
