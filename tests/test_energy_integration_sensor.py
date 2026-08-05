"""Regression test for DeWarmteEnergyIntegrationSensor construction.

home-assistant/core#177596 ("Do not set a device on YAML integration
entities", merged 2026-07-30, released in HA 2026.8.0) changed
``homeassistant.components.integration.sensor.IntegrationSensor.__init__``
from accepting ``hass`` as the first positional-or-keyword parameter to a
fully keyword-only signature that no longer accepts ``hass`` at all.

``DeWarmteEnergyIntegrationSensor.__init__`` used to call
``super().__init__(source_sensor.hass, ...)``, passing ``hass``
*positionally*. On HA 2026.8+ that raises:

    TypeError: IntegrationSensor.__init__() takes 1 positional argument
    but 2 positional arguments (and 8 keyword-only arguments) were given

This test constructs the sensor against whatever ``homeassistant`` version
is actually installed, so it fails on the old positional-argument code and
passes once the constructor only adds ``hass`` as a conditional keyword
argument (detected via ``inspect.signature``).
"""
from datetime import timedelta
from unittest.mock import MagicMock

from custom_components.dewarmte.sensor import DeWarmteEnergyIntegrationSensor


def _make_source_sensor() -> MagicMock:
    """Build a mock power sensor sufficient to construct the energy sensor."""
    source_sensor = MagicMock()
    source_sensor.hass = MagicMock()
    source_sensor.coordinator.update_interval = timedelta(seconds=30)
    source_sensor.entity_id = "sensor.test_device_power"
    source_sensor.name = "Test Device Power"
    source_sensor.unique_id = "test_device_power"
    source_sensor.coordinator.device_info = {
        "identifiers": {("dewarmte", "test_device")}
    }
    return source_sensor


def test_energy_integration_sensor_constructs_without_error() -> None:
    """DeWarmteEnergyIntegrationSensor must build under the installed HA version.

    Regression test for the positional ``hass`` argument that broke on
    HA 2026.8+ (home-assistant/core#177596).
    """
    source_sensor = _make_source_sensor()

    sensor = DeWarmteEnergyIntegrationSensor(source_sensor)

    assert sensor.source_sensor is source_sensor
    assert sensor._attr_device_info == source_sensor.coordinator.device_info


def test_energy_integration_sensor_raises_when_update_interval_missing() -> None:
    """Unrelated guard clause should still work after the constructor rewrite."""
    source_sensor = _make_source_sensor()
    source_sensor.coordinator.update_interval = None

    try:
        DeWarmteEnergyIntegrationSensor(source_sensor)
    except ValueError as err:
        assert "update interval" in str(err)
    else:
        raise AssertionError("Expected ValueError when update_interval is None")
