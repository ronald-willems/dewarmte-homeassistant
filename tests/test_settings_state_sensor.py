"""Tests for the Settings State sensor and the restore warning (issue #30).

The settings API answers a write with state "sent"; the next polls show
"applied" (the pump picked the version up) or "restored" (the backend reverted
to the previous version). The official web app reads only this enum.
"""
import json
import logging
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.dewarmte import _warn_if_settings_restored
from custom_components.dewarmte.api.models.settings import DeviceOperationSettings
from custom_components.dewarmte.sensor import (
    SENSOR_DESCRIPTIONS,
    SETTINGS_STATE_OPTIONS,
    DeWarmteSensor,
)

from test_cooling_settings import NEW_SETTINGS

DESCRIPTION = next(d for d in SENSOR_DESCRIPTIONS if d.key == "settings_state")
OPERATING_STATE = next(d for d in SENSOR_DESCRIPTIONS if d.key == "state")


def _settings(**overrides) -> DeviceOperationSettings:
    return DeviceOperationSettings.from_api_response({**NEW_SETTINGS, **overrides})


def _make_sensor(settings: DeviceOperationSettings | None) -> DeWarmteSensor:
    coordinator = MagicMock()
    coordinator.device.device_id = "dev1"
    coordinator.device_info = {"identifiers": {("dewarmte", "dev1")}}
    coordinator._cached_settings = settings
    coordinator.data = MagicMock(state="heating")  # status.state must not leak in
    sensor = DeWarmteSensor(coordinator, DESCRIPTION)
    sensor.entity_id = "sensor.dewarmte_settings_state"
    return sensor


def test_state_is_parsed_and_required() -> None:
    assert _settings(state="sent").state == "sent"
    with pytest.raises(KeyError):
        DeviceOperationSettings.from_api_response(
            {k: v for k, v in NEW_SETTINGS.items() if k != "state"}
        )


def test_is_applied_is_not_needed() -> None:
    """The web app never reads it, so DeWarmte may drop it; we must not depend on it."""
    data = {k: v for k, v in NEW_SETTINGS.items() if k != "is_applied"}
    assert DeviceOperationSettings.from_api_response(data).state == "applied"


def test_sensor_reads_settings_state_not_status_state() -> None:
    sensor = _make_sensor(_settings(state="restored"))
    assert sensor.native_value == "restored"
    assert sensor.extra_state_attributes == {"version": 229}


def test_sensor_without_settings_is_unknown() -> None:
    sensor = _make_sensor(None)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None


def test_unknown_value_returns_none_and_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    sensor = _make_sensor(_settings(state="queued"))
    with caplog.at_level(logging.WARNING):
        assert sensor.native_value is None
        assert sensor.native_value is None
    warnings = [r for r in caplog.records if "queued" in r.getMessage()]
    assert len(warnings) == 1
    assert "state" in warnings[0].getMessage()


def test_entity_identity_and_gating() -> None:
    """Own unique_id (status.state keeps `dev1_state`), diagnostic, settings devices only."""
    assert _make_sensor(None).unique_id == "dev1_settings_state"
    assert DESCRIPTION.key != OPERATING_STATE.key
    assert DESCRIPTION.entity_category == "diagnostic"
    assert DESCRIPTION.source == "settings"
    assert set(DESCRIPTION.device_types) == {"AO", "MP", "PT"}


def test_every_option_has_a_translation() -> None:
    en = json.loads(
        (Path(__file__).parent.parent / "custom_components/dewarmte/translations/en.json").read_text()
    )
    assert set(en["entity"]["sensor"]["settings_state"]["state"]) == set(SETTINGS_STATE_OPTIONS)


def test_restore_after_sent_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    sent = _settings(state="sent", version=230)
    with caplog.at_level(logging.WARNING):
        _warn_if_settings_restored("dev1", sent, replace(sent, state="restored", version=229))
    assert [r.levelno for r in caplog.records] == [logging.WARNING]
    assert "restored" in caplog.records[0].getMessage()
    assert "229" in caplog.records[0].getMessage()


@pytest.mark.parametrize(
    ("previous", "current"),
    [
        (None, "restored"),  # first poll after startup: nothing to compare with
        ("sent", "applied"),
        ("sent", "sent"),
        ("applied", "applied"),
        ("restored", "restored"),  # already reported on the transition
    ],
)
def test_other_transitions_are_silent(
    previous: str | None, current: str, caplog: pytest.LogCaptureFixture
) -> None:
    prev = _settings(state=previous) if previous else None
    with caplog.at_level(logging.WARNING):
        _warn_if_settings_restored("dev1", prev, _settings(state=current))
        _warn_if_settings_restored("dev1", _settings(state="sent"), None)
    assert caplog.records == []
