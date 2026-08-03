"""Unit tests for the cooling settings API change (thermostat_type rename).

Regression coverage for the outage where the API renamed
`cooling_thermostat_type` -> `thermostat_type`, which broke parsing of the
settings response and therefore every settings write.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytest

from custom_components.dewarmte.api.client import DeWarmteApiClient, DeWarmteApiError
from custom_components.dewarmte.api.models.config import ConnectionSettings
from custom_components.dewarmte.api.models.device import Device
from custom_components.dewarmte.api.models.settings import DeviceOperationSettings


# A settings payload in the current (post-rename) API shape, mirroring a real
# GET /customer/products/{id}/settings/ response.
NEW_SETTINGS: Dict[str, Any] = {
    "advanced_boost_mode_control": True,
    "advanced_thermostat_delay": "med",
    "backup_heating_mode": "eco",
    "thermostat_type": "heating_only",
    "cooling_temperature": 18,
    "cooling_control_mode": "heating_only",
    "cooling_duration": 0,
    "force_cooling_temperature": 18,
    "force_cooling_end": None,
    "is_force_cooling_active": False,
    "cooling_schedules": [],
    "heat_curve_mode": "weather",
    "heating_kind": "custom",
    "heat_curve_s1_outside_temp": -7,
    "heat_curve_s1_target_temp": 60,
    "heat_curve_s2_outside_temp": 10,
    "heat_curve_s2_target_temp": 35,
    "heat_curve_fixed_temperature": 60,
    "heat_curve_use_smart_correction": False,
    "heating_performance_mode": "pomp_ao_only",
    "heating_performance_backup_temperature": -20,
    "sound_mode": "normal",
    "sound_compressor_power": "max",
    "sound_fan_speed": "max",
    "warm_water_is_scheduled": False,
    "warm_water_ranges": [{"order": 0, "temperature": 50, "period": "00:00-23:59"}],
    "version": 229,
    "is_applied": True,
}


class FakeResponse:
    """Minimal aiohttp-style response supporting async context management."""

    def __init__(self, status: int = 200, payload: Optional[Dict[str, Any]] = None) -> None:
        self.status = status
        self._payload = payload if payload is not None else {}

    async def json(self) -> Dict[str, Any]:
        return self._payload

    async def text(self) -> str:
        return str(self._payload)

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class RecordingSession:
    """Session stub: GET returns a fixed settings payload, POST is recorded.

    `post_response` lets a test make the POST fail the way the real API does.
    """

    def __init__(
        self,
        get_payload: Dict[str, Any],
        post_response: Optional[FakeResponse] = None,
    ) -> None:
        self._get_payload = get_payload
        self._post_response = post_response
        self.posts: List[Tuple[str, Optional[Dict[str, Any]]]] = []

    def get(self, url: str, *, headers: Optional[Dict[str, str]] = None) -> FakeResponse:
        return FakeResponse(200, self._get_payload)

    def post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> FakeResponse:
        self.posts.append((url, json))
        return self._post_response or FakeResponse(200, {})


class StubAuth:
    """Stub auth object emulating the interface the client relies on."""

    def __init__(self) -> None:
        self.access_token = "test"
        self._headers: Dict[str, str] = {"Authorization": "Bearer test"}

    async def ensure_token(self, force: bool = False, buffer_seconds: int | None = None) -> bool:
        return True

    def mark_expired(self) -> None:
        self._headers["Authorization"] = "Bearer null"

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._headers)


def _make_client(
    post_response: Optional[FakeResponse] = None,
) -> Tuple[DeWarmteApiClient, RecordingSession, Device]:
    session = RecordingSession(NEW_SETTINGS, post_response)
    client = DeWarmteApiClient(
        ConnectionSettings(username="user", password="pass", update_interval=60),
        session,
    )
    client._auth = StubAuth()  # type: ignore[attr-defined]
    device = Device(
        device_id="dev-1",
        product_id="AO Test",
        access_token="test",
        device_type="AO",
    )
    return client, session, device


def test_from_api_response_reads_new_schema() -> None:
    """Parsing the renamed field must succeed and populate the internal name."""
    settings = DeviceOperationSettings.from_api_response(NEW_SETTINGS)

    assert settings.cooling_thermostat_type == "heating_only"
    assert settings.cooling_schedules == []
    assert settings.is_force_cooling_active is False
    assert settings.force_cooling_temperature == 18.0
    assert settings.force_cooling_end is None


def test_force_cooling_end_parses_to_aware_datetime() -> None:
    """A populated force_cooling_end must parse to a timezone-aware datetime."""
    data = {**NEW_SETTINGS, "force_cooling_end": "2026-07-15T21:10:40.511852+02:00"}

    settings = DeviceOperationSettings.from_api_response(data)

    assert isinstance(settings.force_cooling_end, datetime)
    assert settings.force_cooling_end.tzinfo is not None


@pytest.mark.asyncio
async def test_non_cooling_write_works_after_rename() -> None:
    """A non-cooling write must succeed now that the GET parse no longer crashes.

    This is the core of the outage: before the fix, the settings GET failed to
    parse, so the read-modify-write aborted for *every* group.
    """
    client, session, device = _make_client()

    await client.async_update_operation_settings(device, "sound_mode", "silent")

    url, body = session.posts[-1]
    assert url.endswith("/settings/sound/")
    assert body is not None and body["sound_mode"] == "silent"


@pytest.mark.asyncio
async def test_cooling_write_translates_field_and_keeps_schedule() -> None:
    """Cooling writes must emit `thermostat_type` (not the internal name) and
    pass the cooling schedule through unchanged."""
    client, session, device = _make_client()

    await client.async_update_operation_settings(device, "cooling_control_mode", "cooling_only")

    url, body = session.posts[-1]
    assert url.endswith("/settings/cooling/")
    assert body is not None
    assert body["thermostat_type"] == "heating_only"
    assert "cooling_thermostat_type" not in body
    assert body["cooling_control_mode"] == "cooling_only"
    assert body["cooling_schedules"] == []


@pytest.mark.asyncio
async def test_settings_write_error_includes_api_explanation() -> None:
    """A rejected write must surface the API's reason, not just "failed"."""
    rejection = {"cooling_control_mode": ['"forced" is not a valid choice.']}
    client, _session, device = _make_client(post_response=FakeResponse(400, rejection))

    with pytest.raises(DeWarmteApiError) as excinfo:
        await client.async_update_operation_settings(device, "cooling_temperature", 20.0)

    message = str(excinfo.value)
    assert "Failed to update cooling settings" in message
    assert "HTTP 400" in message
    assert "not a valid choice" in message


@pytest.mark.asyncio
async def test_forced_cooling_start_error_includes_api_explanation() -> None:
    """Same for the forced-cooling commands."""
    client, _session, device = _make_client(post_response=FakeResponse(400, {"detail": "nope"}))

    with pytest.raises(DeWarmteApiError, match="Failed to start forced cooling"):
        await client.async_start_forced_cooling(device, 19.0, 7200)

    with pytest.raises(DeWarmteApiError, match="Failed to stop forced cooling"):
        await client.async_stop_forced_cooling(device)


@pytest.mark.asyncio
async def test_start_forced_cooling_posts_setpoint_and_duration() -> None:
    """Forced cooling start must hit start-forced with setpoint + duration."""
    client, session, device = _make_client()

    await client.async_start_forced_cooling(device, 19.0, 7200)

    url, body = session.posts[-1]
    assert url.endswith("/settings/cooling/start-forced/")
    assert body == {"force_cool_setpoint": 19.0, "forced_duration": 7200}


@pytest.mark.asyncio
async def test_stop_forced_cooling_posts_empty_body() -> None:
    """Forced cooling stop must hit stop-forced with an empty body."""
    client, session, device = _make_client()

    await client.async_stop_forced_cooling(device)

    url, body = session.posts[-1]
    assert url.endswith("/settings/cooling/stop-forced/")
    assert body == {}
