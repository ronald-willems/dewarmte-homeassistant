"""DeWarmte's side: the hourly energy history the insights API holds for a pump.

Only `hourly` is imported, because Home Assistant stores long-term statistics
at exactly one resolution (hourly rows) and derives every coarser view from
them at read time. `yearly` is used only to find where the history begins.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterator, NamedTuple
from zoneinfo import ZoneInfo

from ..api.client import DeWarmteApiClient
from ..api.models.device import Device

_LOGGER = logging.getLogger(__name__)

# Bucket labels are Dutch wall-clock time, whatever Home Assistant's own time
# zone is: DeWarmte is a Dutch company metering pumps installed in NL.
API_TIME_ZONE = ZoneInfo("Europe/Amsterdam")

ONE_HOUR = timedelta(hours=1)

# Years of history mean thousands of requests, and nothing waits on them.
REQUEST_DELAY = 0.3


@dataclass(frozen=True)
class EnergyHour:
    """One hour of a heat pump's metered energy, in kWh.

    `electric_backup_usage` is already part of `electricity_consumed` on HC
    pumps but a separate meter on PT; only heat and electricity are safe to put
    in the Energy dashboard.
    """

    start: datetime
    heat_supplied: float
    electricity_consumed: float
    electric_backup_usage: float

    @classmethod
    def from_bucket(cls, start: datetime, bucket: dict[str, Any]) -> EnergyHour:
        return cls(
            start=start,
            heat_supplied=float(bucket.get("heat_supplied") or 0.0),
            electricity_consumed=float(bucket.get("electricity_consumed") or 0.0),
            electric_backup_usage=float(bucket.get("electric_backup_usage") or 0.0),
        )

    def has_ended(self, now: datetime | None = None) -> bool:
        """Only a complete hour can be stored; its running total is never redone."""
        return self.start + ONE_HOUR <= (now or datetime.now(timezone.utc))


class PortalHistory:
    """The hourly energy history DeWarmte holds for one heat pump."""

    def __init__(self, api: DeWarmteApiClient, device: Device) -> None:
        self._api = api
        self._device = device

    async def hours_of(self, day: date) -> list[EnergyHour]:
        """Every hour of a Dutch calendar day the portal has data for."""
        payload = await self._get_insights("hourly", day)
        return [
            EnergyHour.from_bucket(start, bucket)
            for start, bucket in hourly_buckets(day, payload.get("data") or [])
        ]

    async def find_first_day(self) -> date | None:
        """The day to start importing from, or None when there is no history yet.

        `yearly` names the years with data, but hourly buckets often begin
        later than the aggregates do. So probe the 15th of each month (the 1st
        is as likely as any day to be missing) until one has hours, and start
        the day after the last empty probe so that a history beginning on, say,
        the 19th is not cut short.
        """
        years = await self._years_with_data()
        if not years:
            return None

        start = date(years[0], 1, 1)
        probe = date(years[0], 1, 15)
        while probe <= today_in_the_netherlands():
            if await self.hours_of(probe):
                return start
            start = probe + timedelta(days=1)
            probe = _the_15th_of_the_month_after(probe)
        return None

    async def _years_with_data(self) -> list[int]:
        payload = await self._get_insights("yearly")
        return sorted(int(b["key"]) for b in payload.get("data") or [] if b.get("key"))

    async def _get_insights(self, timespan: str, day: date | None = None) -> dict[str, Any]:
        payload = await self._api.async_get_insights(
            self._device, timespan=timespan, start_date=day.isoformat() if day else None
        )
        await asyncio.sleep(REQUEST_DELAY)
        return payload


class WallClockHour(NamedTuple):
    """A real hour of a Dutch day: when it starts (UTC) and how the API labels it."""

    start: datetime
    label: str


def today_in_the_netherlands() -> date:
    return datetime.now(API_TIME_ZONE).date()


def dutch_day_of(instant: datetime) -> date:
    return instant.astimezone(API_TIME_ZONE).date()


def wall_clock_hours(day: date) -> list[WallClockHour]:
    """The real hours of a Dutch calendar day: 24, or 23 and 25 on the DST days.

    On the autumn day "02:00" legitimately appears twice, CEST then CET.
    """
    cursor = _dutch_midnight(day)
    end = _dutch_midnight(day + timedelta(days=1))
    hours = []
    while cursor < end:
        hours.append(WallClockHour(cursor, format(cursor.astimezone(API_TIME_ZONE), "%H:00")))
        cursor += ONE_HOUR
    return hours


def hourly_buckets(day: date, buckets: list[dict[str, Any]]) -> Iterator[tuple[datetime, dict[str, Any]]]:
    """Pair each bucket of an `hourly` response with the UTC hour it covers.

    Labels alone are ambiguous ("02:00" twice in autumn) and positions alone
    are unreliable (the API drops hours it has no data for, the first ones
    included). So walk the day's real hours and the buckets together, matching
    on the label and skipping the hours the API left out.

    A label names the hour a bucket was *closed*: "08:00" holds 07:00-08:00.
    Verified hour by hour against this integration's own energy sensor on
    three days, one of them 25 hours long.
    """
    hours = wall_clock_hours(day)
    position = 0
    for bucket in buckets:
        position = _position_of(bucket.get("key"), hours, start=position)
        if position is None:
            _LOGGER.warning("Ignoring hourly bucket %s for %s: no such hour in that day",
                            bucket.get("key"), day)
            return
        yield hours[position].start - ONE_HOUR, bucket
        position += 1


def _position_of(label: str | None, hours: list[WallClockHour], *, start: int) -> int | None:
    for position in range(start, len(hours)):
        if hours[position].label == label:
            return position
    return None


def _dutch_midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=API_TIME_ZONE).astimezone(timezone.utc)


def _the_15th_of_the_month_after(day: date) -> date:
    return (day.replace(day=28) + timedelta(days=7)).replace(day=15)
