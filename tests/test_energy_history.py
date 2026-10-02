"""Tests for mapping insights buckets onto Home Assistant statistics hours.

The mapping is the whole risk surface of the energy-history import: the bucket
labels are Dutch wall-clock time, so they are ambiguous twice a year, and every
row's cumulative sum depends on the one before it. All of it is pure, so it is
tested here without a recorder.

The bucket lists below are the shapes the live API actually returns; see the
`n=` counts recorded against real DST dates in the feature investigation.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from custom_components.dewarmte.energy_history import (
    SERIES,
    _expected_hours,
    _Series,
    hourly_buckets,
)


def _buckets(count: int, *, first_hour: int = 0, value: float = 1.0) -> list[dict]:
    """Build `count` buckets, labelled the way the API labels them."""
    return [
        {
            "key": f"{(first_hour + i) % 24:02d}:00",
            "heat_supplied": value,
            "electricity_consumed": value,
            "electric_backup_usage": 0,
            "temperature": None,
        }
        for i in range(count)
    ]


def test_ordinary_day_maps_to_24_utc_hours() -> None:
    """A winter day starts at 23:00 UTC the day before (CET is UTC+1)."""
    mapped = list(hourly_buckets(date(2025, 1, 15), _buckets(24)))

    assert len(mapped) == 24
    assert mapped[0][0] == datetime(2025, 1, 14, 23, tzinfo=timezone.utc)
    assert mapped[-1][0] == datetime(2025, 1, 15, 22, tzinfo=timezone.utc)


def test_summer_day_starts_two_hours_earlier() -> None:
    """CEST is UTC+2, so local midnight is 22:00 UTC the day before."""
    mapped = list(hourly_buckets(date(2025, 7, 15), _buckets(24)))

    assert mapped[0][0] == datetime(2025, 7, 14, 22, tzinfo=timezone.utc)


def test_spring_forward_day_has_23_hours() -> None:
    """The API omits the hour that does not exist; 02:00 is simply absent.

    Real response for 2025-03-30: 23 buckets, keys jumping 01:00 -> 03:00.
    """
    buckets = _buckets(24)
    del buckets[2]  # 02:00 never happened
    mapped = list(hourly_buckets(date(2025, 3, 30), buckets))

    assert len(mapped) == 23
    assert [b["key"] for _start, b in mapped][:4] == ["00:00", "01:00", "03:00", "04:00"]
    # Consecutive real hours, with no gap where the clock jumped.
    starts = [start for start, _b in mapped]
    assert starts == [starts[0] + timedelta(hours=i) for i in range(23)]
    assert starts[-1] == datetime(2025, 3, 30, 21, tzinfo=timezone.utc)


def test_fall_back_day_has_25_hours_and_a_repeated_label() -> None:
    """The repeated "02:00" must become two distinct hours, not overwrite one.

    Real response for 2024-10-27: 25 buckets with "02:00" appearing twice. This
    is why the label cannot be used as a key.
    """
    buckets = _buckets(24)
    buckets.insert(3, dict(buckets[2]))  # 02:00 happened twice
    assert [b["key"] for b in buckets][:5] == ["00:00", "01:00", "02:00", "02:00", "03:00"]

    mapped = list(hourly_buckets(date(2024, 10, 27), buckets))

    assert len(mapped) == 25
    starts = [start for start, _b in mapped]
    assert len(set(starts)) == 25, "every bucket must land on its own hour"
    assert starts == [starts[0] + timedelta(hours=i) for i in range(25)]


def test_missing_leading_hour_does_not_shift_the_day() -> None:
    """The API drops hours it has no data for, including the first one.

    Real response for 2024-03-31: 22 buckets whose first key is "01:00" -- both
    the missing midnight hour and the DST jump. Walking positionally from local
    midnight would put every value an hour too early.
    """
    buckets = _buckets(24)
    del buckets[2]  # 02:00 never happened (spring forward)
    del buckets[0]  # 00:00 simply has no data
    assert [b["key"] for b in buckets][:3] == ["01:00", "03:00", "04:00"]

    mapped = list(hourly_buckets(date(2024, 3, 31), buckets))

    assert len(mapped) == 22
    # 01:00 CET is 00:00 UTC, and that is where the first bucket must land.
    assert mapped[0][0] == datetime(2024, 3, 31, 0, tzinfo=timezone.utc)
    assert mapped[0][1]["key"] == "01:00"
    assert mapped[-1][0] == datetime(2024, 3, 31, 21, tzinfo=timezone.utc)


def test_hole_in_the_middle_of_a_day_leaves_a_gap() -> None:
    """Hours the API omits are skipped, not backfilled by the ones after them."""
    buckets = _buckets(24)
    del buckets[10:14]  # 10:00-13:00 missing

    mapped = list(hourly_buckets(date(2025, 1, 15), buckets))

    assert len(mapped) == 20
    labels = [b["key"] for _start, b in mapped]
    assert "09:00" in labels and "10:00" not in labels and "14:00" in labels
    by_label = {b["key"]: start for start, b in mapped}
    # 14:00 CET keeps its own hour rather than sliding into the gap.
    assert by_label["14:00"] == datetime(2025, 1, 15, 13, tzinfo=timezone.utc)


def test_unknown_label_is_ignored_rather_than_misplaced() -> None:
    """A label that is not an hour of this day must not consume a real slot."""
    buckets = _buckets(3)
    buckets[1]["key"] = "99:00"

    mapped = list(hourly_buckets(date(2025, 1, 15), buckets))

    assert [b["key"] for _start, b in mapped] == ["00:00"]


def test_expected_hours_match_the_real_dst_day_lengths() -> None:
    """23, 24 and 25 hours, with the autumn day carrying "02:00" twice."""
    assert len(_expected_hours(date(2025, 3, 30))) == 23
    assert len(_expected_hours(date(2025, 1, 15))) == 24

    autumn = _expected_hours(date(2024, 10, 27))
    assert len(autumn) == 25
    assert [label for _start, label in autumn].count("02:00") == 2


def test_partial_day_maps_only_the_hours_present() -> None:
    """Today's response holds only the hours so far, and that is fine."""
    mapped = list(hourly_buckets(date(2026, 9, 5), _buckets(19)))

    assert len(mapped) == 19
    assert mapped[0][0] == datetime(2026, 9, 4, 22, tzinfo=timezone.utc)


def test_series_accumulates_a_running_total() -> None:
    """External statistics carry a cumulative sum, not just the hour's value."""
    series = _Series(
        key="heat_supplied", name="Heat", statistic_id="dewarmte:x_heat", next_hour=None, total=0.0
    )
    start = datetime(2025, 1, 15, 0, tzinfo=timezone.utc)
    for i, value in enumerate([1.5, 2.0, 0.5]):
        series.add(start + timedelta(hours=i), value)

    assert [row["state"] for row in series.rows] == [1.5, 2.0, 0.5]
    assert [row["sum"] for row in series.rows] == [1.5, 3.5, 4.0]


def test_series_resumes_without_double_counting() -> None:
    """Hours already in the database are skipped, and the total continues."""
    start = datetime(2025, 1, 15, 0, tzinfo=timezone.utc)
    series = _Series(
        key="heat_supplied",
        name="Heat",
        statistic_id="dewarmte:x_heat",
        next_hour=start + timedelta(hours=2),
        total=100.0,
    )

    for i, value in enumerate([1.0, 1.0, 3.0, 4.0]):
        series.add(start + timedelta(hours=i), value)

    # The first two hours were already imported; only the last two are new.
    assert [row["state"] for row in series.rows] == [3.0, 4.0]
    assert [row["sum"] for row in series.rows] == [103.0, 107.0]


def test_every_series_key_exists_in_a_real_bucket() -> None:
    """Guard against renaming a field without updating the API mapping."""
    bucket = _buckets(1)[0]
    for key, _name in SERIES:
        assert key in bucket


@pytest.mark.parametrize(
    ("device_id", "expected"),
    [
        (
            "98462771-2861-4180-8b29-349aefed845a",
            "dewarmte:98462771_2861_4180_8b29_349aefed845a_heat_supplied",
        ),
    ],
)
def test_statistic_ids_are_valid_for_home_assistant(device_id: str, expected: str) -> None:
    """Statistic ids allow only [\\da-z_], so the device UUID loses its hyphens."""
    from homeassistant.components.recorder.statistics import valid_statistic_id

    from custom_components.dewarmte.api.models.device import Device
    from custom_components.dewarmte.energy_history import all_statistic_ids, statistic_id

    device = Device(
        device_id=device_id, product_id="AO A-534", access_token="t", device_type="AO"
    )

    assert statistic_id(device, "heat_supplied") == expected
    for stat_id in all_statistic_ids(device):
        assert valid_statistic_id(stat_id), stat_id
