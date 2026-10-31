"""Unit tests for Pomp T smart heating control (issue #24).

Smart control lives on its own endpoint (GET/PATCH smart-control/), but is
handled as one more settings group. SMART_CONTROL mirrors a real Pomp T GET
response; the PATCH body mirrors what the official web app sends.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pytest

from custom_components.dewarmte.api.client import DeWarmteApiClient, DeWarmteApiError
from custom_components.dewarmte.api.models.config import ConnectionSettings
from custom_components.dewarmte.api.models.device import Device

from test_cooling_settings import NEW_SETTINGS, FakeResponse, StubAuth


SMART_CONTROL: Dict[str, Any] = {
    "is_control_enabled": False,
    "is_frank_energie_connected": False,
    "is_training_mode": True,
    "use_dynamic_tariff": False,
    "use_solar_optimization": False,
    "use_flexibility_trading": False,
    "pompt_min_temp": 40,
    "pompt_max_temp": 55,
}


class RoutingSession:
    """Session stub: GET answers per endpoint, PATCH is recorded."""

    def __init__(self, patch_response: Optional[FakeResponse] = None) -> None:
        self._patch_response = patch_response
        self.gets: List[str] = []
        self.patches: List[Tuple[str, Optional[Dict[str, Any]]]] = []

    def get(self, url: str, *, headers: Optional[Dict[str, str]] = None) -> FakeResponse:
        self.gets.append(url)
        if url.endswith("/smart-control/"):
            return FakeResponse(200, SMART_CONTROL)
        return FakeResponse(200, NEW_SETTINGS)

    def patch(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> FakeResponse:
        self.patches.append((url, json))
        return self._patch_response or FakeResponse(200, {})


def _make_client(
    device_type: str = "PT",
    patch_response: Optional[FakeResponse] = None,
) -> Tuple[DeWarmteApiClient, RoutingSession, Device]:
    session = RoutingSession(patch_response)
    client = DeWarmteApiClient(
        ConnectionSettings(username="user", password="pass", update_interval=60),
        session,
    )
    client._auth = StubAuth()  # type: ignore[attr-defined]
    device = Device(
        device_id="dev-1",
        product_id=f"{device_type} Test",
        access_token="test",
        device_type=device_type,
    )
    return client, session, device


@pytest.mark.asyncio
async def test_pt_settings_include_smart_control() -> None:
    client, _session, device = _make_client()

    settings = await client.async_get_operation_settings(device)

    assert settings is not None
    assert settings.is_control_enabled is False
    assert settings.pompt_min_temp == 40
    assert settings.pompt_max_temp == 55


@pytest.mark.asyncio
async def test_other_devices_do_not_fetch_smart_control() -> None:
    """The API answers for AO/HC too, but only with unused defaults."""
    client, session, device = _make_client(device_type="AO")

    settings = await client.async_get_operation_settings(device)

    assert settings is not None and settings.pompt_min_temp is None
    assert not any(url.endswith("/smart-control/") for url in session.gets)


@pytest.mark.asyncio
async def test_write_patches_the_web_app_body() -> None:
    client, session, device = _make_client()

    await client.async_update_operation_settings(device, "pompt_min_temp", 45.0)

    url, body = session.patches[-1]
    assert url.endswith("/customer/products/dev-1/smart-control/")
    assert body == {
        "is_control_enabled": False,
        "pompt_min_temp": 45.0,
        "pompt_max_temp": 55,
        "is_frank_energie_connected": False,
        "use_dynamic_tariff": False,
        "use_solar_optimization": False,
        "use_flexibility_trading": False,
    }


@pytest.mark.asyncio
async def test_write_response_is_merged_into_settings() -> None:
    """The PATCH answers with only the smart control fields, not all settings."""
    client, _session, device = _make_client(
        patch_response=FakeResponse(200, {**SMART_CONTROL, "is_control_enabled": True})
    )

    settings = await client.async_update_operation_settings(device, "is_control_enabled", True)

    assert settings is not None
    assert settings.is_control_enabled is True
    assert settings.sound_mode == NEW_SETTINGS["sound_mode"]


@pytest.mark.asyncio
async def test_unparsable_write_response_returns_none() -> None:
    client, _session, device = _make_client(patch_response=FakeResponse(200, {"unexpected": True}))

    assert await client.async_update_operation_settings(device, "pompt_max_temp", 60) is None


@pytest.mark.asyncio
async def test_failed_write_raises_with_api_message() -> None:
    client, _session, device = _make_client(
        patch_response=FakeResponse(400, {"detail": "Terms not accepted"})
    )

    with pytest.raises(DeWarmteApiError, match="Terms not accepted"):
        await client.async_update_operation_settings(device, "is_control_enabled", True)
