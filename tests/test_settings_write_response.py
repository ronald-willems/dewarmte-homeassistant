"""The settings write returns the API's own echo of the new settings.

Every settings POST is answered with the complete new settings object. Using it
lets the coordinator publish the new state straight away instead of polling for
it, which is both faster and three GETs cheaper - see async_write_setting.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from custom_components.dewarmte.api.models.settings import DeviceOperationSettings

from test_cooling_settings import NEW_SETTINGS, FakeResponse, _make_client


def _response(**overrides: Any) -> Dict[str, Any]:
    """A settings write response, as the API sends it (values already applied)."""
    return {**NEW_SETTINGS, "state": "sent", "is_applied": False, **overrides}


@pytest.mark.asyncio
async def test_write_returns_the_settings_from_the_response() -> None:
    client, _session, device = _make_client(
        post_response=FakeResponse(200, _response(sound_mode="silent"))
    )

    settings = await client.async_update_operation_settings(device, "sound_mode", "silent")

    assert isinstance(settings, DeviceOperationSettings)
    assert settings.sound_mode == "silent"


@pytest.mark.asyncio
async def test_returned_settings_reflect_the_write_not_the_pre_write_state() -> None:
    """The echo is the point: the GET before the write still has the old value."""
    client, session, device = _make_client(
        post_response=FakeResponse(200, _response(cooling_temperature=21))
    )
    assert session._get_payload["cooling_temperature"] == 18

    settings = await client.async_update_operation_settings(device, "cooling_temperature", 21)

    assert settings is not None
    assert settings.cooling_temperature == 21.0


@pytest.mark.asyncio
async def test_unparsable_response_returns_none_instead_of_raising() -> None:
    """The write succeeded; only the echo was unusable.

    Callers fall back to polling, so a schema change must not make a write that
    actually worked look like a failure to the user.
    """
    client, _session, device = _make_client(post_response=FakeResponse(200, {"unexpected": True}))

    assert await client.async_update_operation_settings(device, "sound_mode", "silent") is None


@pytest.mark.asyncio
async def test_empty_response_returns_none() -> None:
    client, _session, device = _make_client(post_response=FakeResponse(200, {}))

    assert await client.async_update_operation_settings(device, "sound_mode", "silent") is None
