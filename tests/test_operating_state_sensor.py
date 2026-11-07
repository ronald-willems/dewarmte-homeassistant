"""Tests for the Operating State sensor (status.state), issue #28."""
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from custom_components.dewarmte.api.models.status_data import StatusData
from custom_components.dewarmte.sensor import (
    SENSOR_DESCRIPTIONS,
    STATE_OPTIONS,
    DeWarmteSensor,
)

STATE_DESCRIPTION = next(d for d in SENSOR_DESCRIPTIONS if d.key == "state")


def _make_sensor(status: StatusData | None) -> DeWarmteSensor:
    coordinator = MagicMock()
    coordinator.device.device_id = "dev1"
    coordinator.device_info = {"identifiers": {("dewarmte", "dev1")}}
    coordinator.data = status
    sensor = DeWarmteSensor(coordinator, STATE_DESCRIPTION)
    sensor.entity_id = "sensor.dewarmte_operating_state"
    return sensor


def test_state_parsed_from_products_status() -> None:
    """status.state from the products payload lands on StatusData.state."""
    product = {"id": "dev1", "type": "AO", "status": {"is_on": True, "state": "defrosting"}}
    status = StatusData.from_dict({**product, **product["status"]})
    assert status.state == "defrosting"
    assert status.is_on is True


def test_known_state_is_reported() -> None:
    assert _make_sensor(StatusData(state="heating")).native_value == "heating"


def test_missing_state_is_unknown() -> None:
    """A payload without the field (e.g. HC) yields None, not an error."""
    assert _make_sensor(StatusData()).native_value is None


def test_unknown_state_returns_none_and_warns_once(caplog: pytest.LogCaptureFixture) -> None:
    """A value outside the options must not reach HA (it would raise ValueError)."""
    sensor = _make_sensor(StatusData(state="legionella"))
    with caplog.at_level(logging.WARNING):
        assert sensor.native_value is None
        assert sensor.native_value is None
    warnings = [r for r in caplog.records if "legionella" in r.getMessage()]
    assert len(warnings) == 1


def test_unique_id_and_device_types() -> None:
    """Key mirrors the API field; HC is excluded because its status has no state."""
    assert _make_sensor(None).unique_id == "dev1_state"
    assert set(STATE_DESCRIPTION.device_types) == {"AO", "MP", "PT"}


def test_every_option_has_a_translation() -> None:
    en = json.loads(
        (Path(__file__).parent.parent / "custom_components/dewarmte/translations/en.json").read_text()
    )
    assert set(en["entity"]["sensor"]["state"]["state"]) == set(STATE_OPTIONS)
