"""Tests for StatusData parsing."""

from custom_components.dewarmte.api.models.status_data import StatusData


def test_status_data_handles_missing_numeric_values() -> None:
    """StatusData.from_dict should not raise when numeric fields are missing or invalid."""
    raw = {
        "water_flow": None,
        "supply_temperature": "20.5",
        "heat_input": "",
        "electricity_consumption": "3.8",
        "fault_code": "not-an-int",
        "gas_boiler": "true",
        "thermostat": "OFF",
        "status": {},  # noise
    }

    status = StatusData.from_dict(raw)

    assert status.water_flow is None
    assert status.supply_temperature == 20.5
    assert status.heat_input is None
    assert status.electricity_consumption == 3.8
    assert status.fault_code is None
    assert status.gas_boiler is True
    assert status.thermostat is False
    assert status.invalid_fields
    assert any("water_flow" in entry for entry in status.invalid_fields)
    assert any("heat_input" in entry for entry in status.invalid_fields)
    assert any("fault_code" in entry for entry in status.invalid_fields)

