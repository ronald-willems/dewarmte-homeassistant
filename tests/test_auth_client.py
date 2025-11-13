"""Unit tests for token refresh and retry logic."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest

from custom_components.dewarmte.api.auth import (
    DEFAULT_TOKEN_LIFETIME,
    DeWarmteAuth,
)
from custom_components.dewarmte.api.client import DeWarmteApiClient
from custom_components.dewarmte.api.models.config import ConnectionSettings
from custom_components.dewarmte.api.models.device import Device


class DummySession:
    """Minimal session stub for auth tests."""

    def post(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - not used here
        raise RuntimeError("Network access is not expected in tests")


def test_needs_refresh_logic() -> None:
    """Auth should flag refresh when token is missing or near expiry."""
    auth = DeWarmteAuth("user", "pass", DummySession())

    # No token yet -> needs refresh
    assert auth.needs_refresh()

    # Fresh token should not require refresh with zero buffer
    auth._access_token = "token"  # type: ignore[attr-defined]
    auth._token_issued_at = datetime.now(timezone.utc)  # type: ignore[attr-defined]
    assert not auth.needs_refresh(buffer_seconds=0)

    # Token older than (lifetime - buffer) should trigger refresh
    auth._token_issued_at = datetime.now(timezone.utc) - DEFAULT_TOKEN_LIFETIME + timedelta(seconds=30)  # type: ignore[attr-defined]
    assert auth.needs_refresh(buffer_seconds=60)


class FakeResponse:
    """A fake aiohttp response supporting async context management."""

    def __init__(self, status: int, payload: Optional[Dict[str, Any]] = None) -> None:
        self.status = status
        self._payload = payload or {}

    async def json(self) -> Dict[str, Any]:
        return self._payload

    async def text(self) -> str:
        return str(self._payload)

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeSession:
    """Session that yields predefined responses."""

    def __init__(self, responses: List[FakeResponse]) -> None:
        self._responses = responses
        self.get_calls: List[str] = []

    def get(self, url: str, *, headers: Optional[Dict[str, str]] = None) -> FakeResponse:
        self.get_calls.append(url)
        if not self._responses:
            raise AssertionError("No responses left for GET")
        return self._responses.pop(0)

    # login path may attempt to post; delegate to DummySession behaviour if needed
    def post(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover - not used
        raise RuntimeError("Network POST not expected in FakeSession")


class StubAuth:
    """Stub auth object emulating the needed interface."""

    def __init__(self) -> None:
        self._needs_refresh = False
        self.login_calls = 0
        self.force_calls = 0
        self.mark_expired_calls = 0
        self._headers: Dict[str, str] = {"Authorization": "Bearer null"}

    async def ensure_token(self, force: bool = False, buffer_seconds: int | None = None) -> bool:
        self.login_calls += 1
        if force:
            self.force_calls += 1
        self._needs_refresh = False
        self._headers["Authorization"] = "Bearer test"
        return True

    def mark_expired(self) -> None:
        self.mark_expired_calls += 1
        self._needs_refresh = True
        self._headers["Authorization"] = "Bearer null"

    @property
    def headers(self) -> Dict[str, str]:
        return dict(self._headers)


@pytest.mark.asyncio
async def test_get_with_retry_handles_401() -> None:
    """_get_with_retry should refresh the token once after a 401."""
    session = FakeSession(
        [
            FakeResponse(401),
            FakeResponse(200, {"results": []}),
        ]
    )
    client = DeWarmteApiClient(
        ConnectionSettings(username="user", password="pass", update_interval=60),
        session,
    )
    stub_auth = StubAuth()
    client._auth = stub_auth  # type: ignore[attr-defined]

    data = await client._get_with_retry("https://example.com")

    assert data == {"results": []}
    assert stub_auth.login_calls == 2
    assert stub_auth.force_calls == 1
    assert stub_auth.mark_expired_calls == 1
    assert len(session.get_calls) == 2


@pytest.mark.asyncio
async def test_async_get_status_data_refreshes_before_expiry() -> None:
    """Status fetch should refresh token proactively when near expiry."""
    responses = [
        FakeResponse(
            200,
            {
                "results": [
                    {
                        "id": "device-1",
                        "status": {
                            "is_on": False,
                            "heat_input": 0.0,
                            "heat_output": 0.0,
                            "water_flow": 0.0,
                            "electricity_consumption": 0.0,
                            "gas_boiler": False,
                            "thermostat": False,
                            "supply_temperature": 25.0,
                            "actual_temperature": 25.0,
                            "target_temperature": 30.0,
                            "fault_code": 0,
                            "electric_backup_usage": 0.0,
                            "is_connected": True,
                        },
                    }
                ]
            },
        ),
        FakeResponse(200, {"outdoor_temperature": 12}),
    ]
    session = FakeSession(responses)
    client = DeWarmteApiClient(
        ConnectionSettings(username="user", password="pass", update_interval=60),
        session,
    )
    stub_auth = StubAuth()
    stub_auth._needs_refresh = True
    client._auth = stub_auth  # type: ignore[attr-defined]

    device = Device(
        device_id="device-1",
        product_id="AO Test",
        access_token="token",
        device_type="AO",
    )

    status = await client.async_get_status_data(device)

    assert status is not None
    assert stub_auth.login_calls == 3  # initial call + two GETs
    assert session.get_calls[0].endswith("/customer/products/")
    assert len(session.get_calls) == 2  # product + tb-status

