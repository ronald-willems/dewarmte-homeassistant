"""Tests for the insights-based electric backup energy and element entities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from custom_components.dewarmte.api.client import DeWarmteApiClient
from custom_components.dewarmte.api.models.config import ConnectionSettings
from custom_components.dewarmte.api.models.device import Device
from custom_components.dewarmte.api.models.insights import InsightsSummary
from custom_components.dewarmte.binary_sensor import BINARY_SENSOR_DESCRIPTIONS
from custom_components.dewarmte.sensor import SENSOR_DESCRIPTIONS

from tests.test_cooling_settings import FakeResponse, StubAuth


# Illustrative values in the shape of a GET /customer/products/{id}/insights/?start_date=2026-01-01&timespan=monthly
# response of an MP with an electric backup element.
MP_INSIGHTS: Dict[str, Any] = {
    "time_start": "2026-01-01",
    "time_end": "2026-12-31",
    "timespan": "monthly",
    "data": [
        {"key": "Jan", "heat_supplied": 4000.0, "electricity_consumed": 1200.0,
         "electric_backup_usage": 300.0, "temperature": None},
        {"key": "Feb", "heat_supplied": 3500.0, "electricity_consumed": 1000.0,
         "electric_backup_usage": 200.0, "temperature": None},
    ],
    "heat_sum": 7500.0,
    "electricity_sum": 2200.0,
    "dwe_consumption": 500.0,
    "electric_backup_usage_sum": 500.0,
    "has_dwe": True,
    "has_element": True,
    "cop": 3.2,
}


class UrlRecordingSession:
    """Session stub that records GET URLs with their query params."""

    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.requests: List[tuple[str, Optional[Dict[str, str]]]] = []

    def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> FakeResponse:
        self.requests.append((url, params))
        return self._response


def _make_client(response: FakeResponse) -> tuple[DeWarmteApiClient, UrlRecordingSession, Device]:
    session = UrlRecordingSession(response)
    client = DeWarmteApiClient(
        ConnectionSettings(username="user", password="pass", update_interval=60),
        session,
    )
    client._auth = StubAuth()  # type: ignore[attr-defined]
    device = Device(device_id="mp-1", product_id="MP Test", access_token="test", device_type="MP")
    return client, session, device


def test_insights_summary_parses_totals() -> None:
    summary = InsightsSummary.from_api_response(MP_INSIGHTS)

    assert summary.electric_backup_usage_sum == 500.0
    assert summary.heat_sum == 7500.0
    assert summary.electricity_sum == 2200.0


def test_insights_summary_names_missing_field() -> None:
    """A schema change must fail loudly with the field name, not become 0."""
    data = {k: v for k, v in MP_INSIGHTS.items() if k != "electric_backup_usage_sum"}

    with pytest.raises(KeyError, match="electric_backup_usage_sum"):
        InsightsSummary.from_api_response(data)


@pytest.mark.asyncio
async def test_client_requests_year_to_date_insights() -> None:
    client, session, device = _make_client(FakeResponse(200, MP_INSIGHTS))

    summary = await client.async_get_insights_summary(device, 2026)

    assert summary is not None
    assert summary.electric_backup_usage_sum == 500.0
    assert session.requests == [
        (
            "https://api.mydewarmte.com/v1/customer/products/mp-1/insights/",
            {"timespan": "monthly", "start_date": "2026-01-01"},
        )
    ]


@pytest.mark.asyncio
async def test_client_returns_none_when_insights_fail() -> None:
    """MPE products answer HTTP 400 on insights; that must not raise."""
    client, _session, device = _make_client(
        FakeResponse(400, {"code": "unable_to_get_product_insights"})
    )

    assert await client.async_get_insights_summary(device, 2026) is None


def _sensor(key: str):
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


def _binary_sensor(key: str):
    return next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == key)


def test_electric_backup_energy_sensor_reads_insights() -> None:
    description = _sensor("electric_backup_usage_sum")

    assert description.source == "insights"
    assert description.device_types == ("MP", "PT")


def test_element_state_exists_for_mp_and_pt() -> None:
    """MP reads the account-wide tb-status element; PT its own status.gas_boiler (#18)."""
    assert _binary_sensor("is_element_on").device_types == ("MP", "PT")


@pytest.mark.parametrize(
    ("description", "key"),
    [
        (_sensor, "fault_code"),
        (_sensor, "electric_backup_usage"),
    ],
)
def test_fields_missing_from_pt_status_are_not_created_for_pt(description, key) -> None:
    """PT status responses never contained these fields; the entities stayed unknown.

    is_connected is deliberately not listed: PT responses carried it until
    September 2026 and it reported on/off until then.
    """
    assert "PT" not in description(key).device_types
