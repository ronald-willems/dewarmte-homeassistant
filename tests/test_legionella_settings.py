"""Unit tests for the legionella protection settings (issue #29).

Pomp T schedules a weekly disinfecting run through settings/legionella/.
The weekday is written as a number (1 = Monday ... 7 = Sunday), the start time
as "HH:MM"; both keys are required by the endpoint so a write sends the pair.
"""

from __future__ import annotations

from datetime import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.dewarmte.api.models.settings import (
    SETTING_GROUPS,
    DeviceOperationSettings,
)
from custom_components.dewarmte.select import (
    MODE_SELECTS,
    WEEKDAYS,
    DeWarmteSelectEntity,
)
from custom_components.dewarmte.time import TIME_DESCRIPTIONS, DeWarmteTimeEntity

from tests.test_cooling_settings import NEW_SETTINGS, _make_client

LEGIONELLA_SETTINGS = {
    **NEW_SETTINGS,
    "legionella_protection_day": 3,
    "legionella_protection_time": "02:00",
}


def _make_coordinator(settings: DeviceOperationSettings | None) -> MagicMock:
    coordinator = MagicMock()
    coordinator.device.device_id = "dev1"
    coordinator.device_info = {"identifiers": {("dewarmte", "dev1")}}
    coordinator._cached_settings = settings
    coordinator.async_write_setting = AsyncMock()
    return coordinator


def test_from_api_response_reads_legionella_fields() -> None:
    settings = DeviceOperationSettings.from_api_response(LEGIONELLA_SETTINGS)

    assert settings.legionella_protection_day == 3
    assert settings.legionella_protection_time == "02:00"


def test_from_api_response_tolerates_null_and_absent() -> None:
    """The web app's model declares both nullable: an unconfigured pump sends null."""
    null = DeviceOperationSettings.from_api_response(
        {**NEW_SETTINGS, "legionella_protection_day": None, "legionella_protection_time": None}
    )
    absent = DeviceOperationSettings.from_api_response(NEW_SETTINGS)

    for settings in (null, absent):
        assert settings.legionella_protection_day is None
        assert settings.legionella_protection_time is None


@pytest.mark.asyncio
async def test_write_sends_both_keys_to_legionella_endpoint() -> None:
    """Changing one value must POST the pair, matching the app's write body."""
    client, session, device = _make_client()
    session._get_payload = LEGIONELLA_SETTINGS

    await client.async_update_operation_settings(device, "legionella_protection_day", 7)

    url, body = session.posts[-1]
    assert url.endswith("/settings/legionella/")
    assert body == {"legionella_protection_day": 7, "legionella_protection_time": "02:00"}


def test_legionella_group_covers_exactly_the_write_body() -> None:
    assert SETTING_GROUPS["legionella"].endpoint == "legionella"
    assert SETTING_GROUPS["legionella"].keys == [
        "legionella_protection_day",
        "legionella_protection_time",
    ]


def test_legionella_entities_are_pomp_t_only() -> None:
    """The app shows the screen for PT devices only; other selects keep AO/MP."""
    assert MODE_SELECTS["legionella_protection_day"].device_types == ("PT",)
    assert TIME_DESCRIPTIONS["legionella_protection_time"].device_types == ("PT",)
    for key, description in MODE_SELECTS.items():
        if key != "legionella_protection_day":
            assert description.device_types == ("AO", "MP"), key


@pytest.mark.asyncio
async def test_day_select_maps_weekday_names_to_api_numbers() -> None:
    settings = DeviceOperationSettings.from_api_response(LEGIONELLA_SETTINGS)
    coordinator = _make_coordinator(settings)
    entity = DeWarmteSelectEntity(coordinator, MODE_SELECTS["legionella_protection_day"])

    assert entity.options == WEEKDAYS
    assert entity.current_option == "wednesday"

    await entity.async_select_option("sunday")

    coordinator.async_write_setting.assert_awaited_once_with("legionella_protection_day", 7)


def test_day_select_is_unknown_while_unconfigured() -> None:
    settings = DeviceOperationSettings.from_api_response(NEW_SETTINGS)
    entity = DeWarmteSelectEntity(_make_coordinator(settings), MODE_SELECTS["legionella_protection_day"])

    assert entity.current_option is None


def test_other_selects_still_pass_their_option_through() -> None:
    settings = DeviceOperationSettings.from_api_response(NEW_SETTINGS)
    entity = DeWarmteSelectEntity(_make_coordinator(settings), MODE_SELECTS["sound_mode"])

    assert entity.current_option == "normal"


@pytest.mark.asyncio
async def test_time_entity_round_trips_hh_mm() -> None:
    settings = DeviceOperationSettings.from_api_response(LEGIONELLA_SETTINGS)
    coordinator = _make_coordinator(settings)
    entity = DeWarmteTimeEntity(coordinator, TIME_DESCRIPTIONS["legionella_protection_time"])

    assert entity.native_value == time(2, 0)

    await entity.async_set_value(time(23, 30))

    coordinator.async_write_setting.assert_awaited_once_with("legionella_protection_time", "23:30")


def test_time_entity_is_unknown_while_unconfigured() -> None:
    settings = DeviceOperationSettings.from_api_response(NEW_SETTINGS)
    entity = DeWarmteTimeEntity(_make_coordinator(settings), TIME_DESCRIPTIONS["legionella_protection_time"])

    assert entity.native_value is None
