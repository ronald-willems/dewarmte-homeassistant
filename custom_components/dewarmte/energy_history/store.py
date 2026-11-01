"""Home Assistant's side: the `dewarmte:` statistics that hold the imported hours."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics,
    get_last_statistics,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.util import slugify
from homeassistant.util.unit_conversion import EnergyConverter

from ..api.models.device import Device
from ..const import DOMAIN
from .portal import ONE_HOUR, EnergyHour

_LOGGER = logging.getLogger(__name__)

# One statistic per energy field of `EnergyHour`, with its display name.
SERIES: tuple[tuple[str, str], ...] = (
    ("heat_supplied", "Heat supplied"),
    ("electricity_consumed", "Electricity consumed"),
    ("electric_backup_usage", "Electric backup usage"),
)


class ImportedStatistics:
    """What Home Assistant has stored for one heat pump, plus the hours to add.

    The three series are always written together, so they share one resume
    point: the hour after the last one stored.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        device: Device,
        series: list[_Series],
        next_hour: datetime | None,
    ) -> None:
        self._hass = hass
        self._device = device
        self._series = series
        self.next_hour = next_hour
        self.hours_added = 0

    @classmethod
    async def load(cls, hass: HomeAssistant, device: Device) -> ImportedStatistics:
        """Read back each running total and where the last run stopped."""
        series = []
        last_starts = []
        for key, name in SERIES:
            stat_id = statistic_id(device, key)
            last_row = await _last_row_of(hass, stat_id)
            series.append(_Series(key, name, stat_id, total=last_row["sum"] if last_row else 0.0))
            if last_row:
                last_starts.append(datetime.fromtimestamp(last_row["start"], tz=timezone.utc))
        # Should the series ever be out of step, a gap beats a double count.
        next_hour = max(last_starts) + ONE_HOUR if last_starts else None
        return cls(hass, device, series, next_hour)

    def add(self, hour: EnergyHour) -> None:
        """Queue an hour for saving; one already stored is ignored."""
        if self.next_hour is not None and hour.start < self.next_hour:
            return
        for series in self._series:
            series.record(hour.start, getattr(hour, series.key))
        self.next_hour = hour.start + ONE_HOUR
        self.hours_added += 1

    def save(self) -> None:
        """Hand the queued hours to the recorder."""
        for series in self._series:
            if series.rows:
                async_add_external_statistics(self._hass, self._metadata_for(series), series.rows)
                series.rows = []

    def _metadata_for(self, series: _Series) -> StatisticMetaData:
        return StatisticMetaData(
            has_sum=True,
            name=f"{self._device.info.name} {series.name}",
            source=DOMAIN,
            statistic_id=series.statistic_id,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            **_METADATA_EXTRAS,
        )


@dataclass
class _Series:
    """One statistic's running total and the rows queued for it."""

    key: str
    name: str
    statistic_id: str
    total: float
    rows: list[StatisticData] = field(default_factory=list)

    def record(self, start: datetime, value: float) -> None:
        """Queue one hour, carrying the running total forward."""
        self.total += value
        self.rows.append(StatisticData(start=start, state=value, sum=self.total))


def statistic_id(device: Device, key: str) -> str:
    """Statistic ids allow only `[\\da-z_]`, so the device UUID loses its hyphens."""
    return f"{DOMAIN}:{slugify(device.device_id)}_{key}"


def all_statistic_ids(device: Device) -> list[str]:
    return [statistic_id(device, key) for key, _name in SERIES]


async def async_delete_history(hass: HomeAssistant, devices: Iterable[Device]) -> None:
    """Drop every imported statistic for the given devices, and wait until gone.

    Long-term statistics outlive the config entry and are never purged, so this
    is the only way out of an experiment.
    """
    ids = [stat_id for device in devices for stat_id in all_statistic_ids(device)]
    _LOGGER.info("Deleting imported DeWarmte energy history: %s", ", ".join(ids))
    gone = hass.loop.create_future()
    # The recorder reports back from its own thread, hence the hand-off.
    get_instance(hass).async_clear_statistics(
        ids, on_done=lambda: hass.loop.call_soon_threadsafe(gone.set_result, None)
    )
    await gone


async def _last_row_of(hass: HomeAssistant, stat_id: str) -> dict | None:
    rows = await get_instance(hass).async_add_executor_job(
        get_last_statistics, hass, 1, stat_id, True, {"sum"}
    )
    last = (rows.get(stat_id) or [None])[0]
    return last if last and last.get("sum") is not None else None


def _metadata_extras() -> dict[str, Any]:
    """Metadata keys that only some cores know; the recorder rejects unknown ones.

    `mean_type` replaced the `has_mean` boolean in 2025.5; `unit_class` is
    required from 2026.11.
    """
    extras: dict[str, Any] = {}
    if "mean_type" in StatisticMetaData.__annotations__:
        from homeassistant.components.recorder.models import StatisticMeanType

        extras["mean_type"] = StatisticMeanType.NONE
    else:  # pragma: no cover - older cores only know the boolean
        extras["has_mean"] = False
    if "unit_class" in StatisticMetaData.__annotations__:
        extras["unit_class"] = EnergyConverter.UNIT_CLASS
    return extras


_METADATA_EXTRAS = _metadata_extras()
