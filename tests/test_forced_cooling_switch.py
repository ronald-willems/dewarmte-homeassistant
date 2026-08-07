"""Unit tests for the forced ("cool now") cooling switch.

The switch is an exception to the other switches: on/off drive the dedicated
start-forced/stop-forced commands, and turning on has to invent a setpoint and a
duration from the cooling settings the user can already edit.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pytest

from custom_components.dewarmte.api.client import DeWarmteApiClient
from custom_components.dewarmte.api.models.config import ConnectionSettings
from custom_components.dewarmte.api.models.device import Device
from custom_components.dewarmte.api.models.settings import DeviceOperationSettings
from custom_components.dewarmte.switch import (
    DEFAULT_FORCED_COOLING_DURATION,
    FORCED_COOLING_DESCRIPTION,
    DeWarmteForcedCoolingSwitch,
    forced_cooling_params,
)

from test_cooling_settings import NEW_SETTINGS, FakeResponse, RecordingSession, StubAuth


def _settings(**overrides: Any) -> DeviceOperationSettings:
    """Build parsed settings from the shared API payload."""
    return DeviceOperationSettings.from_api_response({**NEW_SETTINGS, **overrides})


class StubCoordinator:
    """Minimal stand-in for DeWarmteDataUpdateCoordinator."""

    def __init__(self, api: DeWarmteApiClient, device: Device, settings: Any) -> None:
        self.api = api
        self._device = device
        self._cached_settings = settings
        self.refresh_calls = 0

    @property
    def device(self) -> Device:
        return self._device

    @property
    def device_info(self) -> Dict[str, Any]:
        return {"identifiers": {("dewarmte", self._device.device_id)}}

    async def async_refresh(self) -> None:
        self.refresh_calls += 1

    async def async_request_refresh(self) -> None:  # pragma: no cover - not used here
        raise AssertionError(
            "the forced cooling switch must refresh immediately, not via the debouncer"
        )


def _make_switch(
    settings: Any = None,
    post_response: Optional[FakeResponse] = None,
) -> Tuple[DeWarmteForcedCoolingSwitch, RecordingSession, StubCoordinator]:
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
        supports_cooling=True,
    )
    coordinator = StubCoordinator(client, device, settings)
    switch = DeWarmteForcedCoolingSwitch(coordinator, FORCED_COOLING_DESCRIPTION)  # type: ignore[arg-type]
    return switch, session, coordinator


def test_params_use_the_configured_cooling_settings() -> None:
    """Setpoint and duration come from the two editable cooling settings."""
    setpoint, duration = forced_cooling_params(
        _settings(cooling_temperature=21, cooling_duration=10800)
    )

    assert setpoint == 21.0
    assert duration == 10800


@pytest.mark.parametrize("configured", [0, -1])
def test_zero_duration_falls_back_to_two_hours(configured: int) -> None:
    """A device with no duration configured must not ask for a zero-length run."""
    _setpoint, duration = forced_cooling_params(_settings(cooling_duration=configured))

    assert duration == DEFAULT_FORCED_COOLING_DURATION == 7200


def test_unique_id_matches_the_historical_key() -> None:
    """The entity id must stay stable for anyone who used an earlier build."""
    switch, _session, _coordinator = _make_switch(_settings())

    assert switch.unique_id == "dev-1_forced_cooling"


def test_is_on_reflects_the_active_flag() -> None:
    """State comes from is_force_cooling_active, and is unknown before the first poll."""
    active, _s, _c = _make_switch(_settings(is_force_cooling_active=True))
    idle, _s2, _c2 = _make_switch(_settings(is_force_cooling_active=False))
    unpolled, _s3, _c3 = _make_switch(None)

    assert active.is_on is True
    assert idle.is_on is False
    assert unpolled.is_on is None


@pytest.mark.asyncio
async def test_turn_on_starts_with_resolved_params() -> None:
    """Turning on must hit start-forced with the resolved setpoint and duration."""
    switch, session, coordinator = _make_switch(
        _settings(cooling_temperature=19, cooling_duration=3600)
    )

    await switch.async_turn_on()

    url, body = session.posts[-1]
    assert url.endswith("/settings/cooling/start-forced/")
    assert body == {"force_cool_setpoint": 19.0, "forced_duration": 3600}
    assert coordinator.refresh_calls == 1


@pytest.mark.asyncio
async def test_turn_on_uses_the_fallback_duration() -> None:
    """The zero-duration fallback must reach the API, not a literal 0."""
    switch, session, _coordinator = _make_switch(_settings(cooling_duration=0))

    await switch.async_turn_on()

    _url, body = session.posts[-1]
    assert body is not None
    assert body["forced_duration"] == DEFAULT_FORCED_COOLING_DURATION


@pytest.mark.asyncio
async def test_turn_off_stops_forced_cooling() -> None:
    """Turning off must hit stop-forced with an empty body."""
    switch, session, coordinator = _make_switch(_settings(is_force_cooling_active=True))

    await switch.async_turn_off()

    url, body = session.posts[-1]
    assert url.endswith("/settings/cooling/stop-forced/")
    assert body == {}
    assert coordinator.refresh_calls == 1


@pytest.mark.asyncio
async def test_turn_on_before_first_poll_raises() -> None:
    """Without settings there are no parameters to send, so fail loudly."""
    from homeassistant.exceptions import HomeAssistantError

    switch, session, _coordinator = _make_switch(None)

    with pytest.raises(HomeAssistantError, match="not available yet"):
        await switch.async_turn_on()

    assert session.posts == []


@pytest.mark.asyncio
async def test_api_rejection_surfaces_as_home_assistant_error() -> None:
    """An API failure must reach the user with the reason attached."""
    from homeassistant.exceptions import HomeAssistantError

    switch, _session, coordinator = _make_switch(
        _settings(), post_response=FakeResponse(400, {"detail": "nope"})
    )

    with pytest.raises(HomeAssistantError, match="Failed to start forced cooling"):
        await switch.async_turn_on()

    assert coordinator.refresh_calls == 0
