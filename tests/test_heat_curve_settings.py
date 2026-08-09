"""Unit tests for the fixed -> weather heat curve switch (issue #22).

Weather mode requires S1 target > S2 target, but while the pump is in fixed mode
the cloud reports both curve points as heat_curve_fixed_temperature. That made
the mode switch permanently impossible from Home Assistant: the values we read
back always violated the rule, and S1/S2 cannot be corrected while in fixed mode
because the cloud overwrites them.

Behaviour below was established against the live API; see the notes in
`api/openapi.yaml` for the exact validator messages.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from custom_components.dewarmte.api.client import DeWarmteApiError

from test_cooling_settings import NEW_SETTINGS, FakeResponse, _make_client


def _fixed_mode_settings(fixed_temp: float = 30) -> Dict[str, Any]:
    """A settings payload as the cloud reports it while in fixed mode.

    Both curve points collapse onto the fixed temperature, and the outside temps
    collapse to the ends of the allowed range.
    """
    return {
        **NEW_SETTINGS,
        "heat_curve_mode": "fixed",
        "heat_curve_fixed_temperature": fixed_temp,
        "heat_curve_s1_outside_temp": -10,
        "heat_curve_s1_target_temp": fixed_temp,
        "heat_curve_s2_outside_temp": 15,
        "heat_curve_s2_target_temp": fixed_temp,
    }


@pytest.mark.asyncio
async def test_switch_to_weather_from_fixed_raises_s1_above_s2() -> None:
    """The core fix: S1 == S2 must be lifted so the switch is accepted."""
    client, session, device = _make_client()
    session._get_payload = _fixed_mode_settings(30)

    await client.async_update_operation_settings(device, "heat_curve_mode", "weather")

    url, body = session.posts[-1]
    assert url.endswith("/settings/heat-curve/")
    assert body is not None
    assert body["heat_curve_mode"] == "weather"
    assert body["heat_curve_s1_target_temp"] == 31
    assert body["heat_curve_s2_target_temp"] == 30


@pytest.mark.asyncio
async def test_switch_to_weather_posts_mode_and_curve_in_one_request() -> None:
    """The corrected curve must ride along in the same POST as the mode.

    The API rejects a partial body ("If 'weather' mode is selected, a
    'heating_kind' must be provided", then "If 'custom' kind is selected, a
    [...s1/s2 fields] must be provided"), so mode and curve cannot be split
    across two requests.
    """
    client, session, device = _make_client()
    session._get_payload = _fixed_mode_settings(30)

    await client.async_update_operation_settings(device, "heat_curve_mode", "weather")

    assert len(session.posts) == 1
    _url, body = session.posts[-1]
    assert body is not None
    for field in (
        "heat_curve_mode",
        "heating_kind",
        "heat_curve_s1_outside_temp",
        "heat_curve_s1_target_temp",
        "heat_curve_s2_outside_temp",
        "heat_curve_s2_target_temp",
    ):
        assert field in body


@pytest.mark.asyncio
async def test_switch_to_weather_leaves_a_valid_curve_untouched() -> None:
    """A curve that already satisfies S1 > S2 must be posted unchanged."""
    client, session, device = _make_client()
    session._get_payload = {**NEW_SETTINGS, "heat_curve_mode": "fixed"}  # s1=60, s2=35

    await client.async_update_operation_settings(device, "heat_curve_mode", "weather")

    _url, body = session.posts[-1]
    assert body is not None
    assert body["heat_curve_s1_target_temp"] == 60
    assert body["heat_curve_s2_target_temp"] == 35


@pytest.mark.asyncio
async def test_switch_to_fixed_does_not_touch_the_curve() -> None:
    """The guard is for entering weather mode only."""
    client, session, device = _make_client()

    await client.async_update_operation_settings(device, "heat_curve_mode", "fixed")

    _url, body = session.posts[-1]
    assert body is not None
    assert body["heat_curve_mode"] == "fixed"
    assert body["heat_curve_s1_target_temp"] == 60
    assert body["heat_curve_s2_target_temp"] == 35


@pytest.mark.asyncio
async def test_explicit_s2_edit_is_not_silently_corrected() -> None:
    """An S1/S2 edit that violates the rule must still fail loudly.

    Rewriting the user's own value would silently discard the edit they asked
    for; the API's message is the more useful outcome.
    """
    rejection = {
        "non_field_errors": [
            "heat_curve_s1_target_temp must be larger than or equal to "
            "heat_curve_s2_target_temp"
        ]
    }
    client, session, device = _make_client(post_response=FakeResponse(400, rejection))

    with pytest.raises(DeWarmteApiError) as excinfo:
        # NEW_SETTINGS has s1=60; raising s2 to 65 breaks the rule.
        await client.async_update_operation_settings(
            device, "heat_curve_s2_target_temp", 65
        )

    _url, body = session.posts[-1]
    assert body is not None
    assert body["heat_curve_s2_target_temp"] == 65
    assert body["heat_curve_s1_target_temp"] == 60
    assert "must be larger than or equal to" in str(excinfo.value)
