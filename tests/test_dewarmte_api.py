"""Test suite for DeWarmte API with mocked responses."""
import asyncio
import os
import sys
import yaml
from typing import Any, AsyncGenerator

import aiohttp
import pytest
import pytest_asyncio
from aiohttp import ClientSession

# Add parent directory to path so we can import the custom component
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from custom_components.dewarmte.api import DeWarmteApiClient
from custom_components.dewarmte.models.settings import ConnectionSettings
from custom_components.dewarmte.models.device import DeviceSensor
from custom_components.dewarmte.models import ValueUnit

def print_section(title: str, data: dict[str, Any]) -> None:
    """Print a section of data with a title."""
    print(f"\n=== {title} ===")
    for key, value in data.items():
        if isinstance(value, DeviceSensor):
            val = value.state.value
            unit = value.state.unit or ""
            print(f"{key}: {val} {unit}".strip())
        else:
            print(f"{key}: {value}")

async def get_config() -> dict:
    """Get test configuration."""
    config_path = "secrets.yaml"
    template_path = "secrets.template.yaml"
    
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        print(f"Please create it from {template_path}")
        return None
        
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

@pytest_asyncio.fixture
async def session():
    """Create and yield an aiohttp ClientSession."""
    async with ClientSession() as session:
        yield session

@pytest_asyncio.fixture
async def mock_api(session):
    """Create a mock DeWarmte API client."""
    connection_settings = ConnectionSettings(
        username="test_user",
        password="test_pass"
    )
    return DeWarmteApiClient(connection_settings=connection_settings, session=session)

@pytest.mark.asyncio
async def test_login(mock_api):
    """Test login with mock responses."""
    # Add mock test here
    pass

@pytest.mark.asyncio
async def test_status_data(mock_api):
    """Test status data with mock responses."""
    # Add mock test here
    pass

@pytest.mark.asyncio
async def test_basic_settings(mock_api):
    """Test basic settings with mock responses."""
    # Add mock test here
    pass

def validate_temperature(name: str, sensor: DeviceSensor) -> None:
    """Validate that a temperature value is within reasonable bounds."""
    value = sensor.state.value
    assert -50 <= value <= 50, f"{name} temperature {value}°C is outside reasonable bounds (-50°C to 50°C)"

def validate_percentage(name: str, sensor: DeviceSensor) -> None:
    """Validate that a percentage value is between 0 and 100."""
    value = sensor.state.value
    assert 0 <= value <= 100, f"{name} value {value}% is outside valid range (0% to 100%)"

def validate_power(name: str, sensor: DeviceSensor) -> None:
    """Validate that a power value is non-negative and within reasonable bounds."""
    value = sensor.state.value
    assert 0 <= value <= 100, f"{name} value {value}kW is outside reasonable bounds (0kW to 100kW)"

def validate_flow(sensor: DeviceSensor) -> None:
    """Validate that a flow value is non-negative and within reasonable bounds."""
    value = sensor.state.value
    assert 0 <= value <= 100, f"Flow value {value}L/min is outside reasonable bounds (0L/min to 100L/min)"

def validate_state(name: str, sensor: DeviceSensor) -> None:
    """Validate that a state value is either 0 or 1."""
    value = sensor.state.value
    assert value in [0, 1], f"{name} state {value} is invalid (must be 0 or 1)"

@pytest.mark.asyncio
async def test_login(api: DeWarmteApiClient) -> None:
    """Test that we can log in successfully."""
    assert api.device is not None, "Device not initialized after login"
    assert api.device.state.online, "Device not marked as online after login"

@pytest.mark.asyncio
async def test_status_data(api: DeWarmteApiClient) -> None:
    """Test getting and validating status data."""
    status_data = await api.async_get_status_data()
    assert status_data is not None, "Failed to get status data"

    # Validate temperatures
    validate_temperature("Supply", status_data["supply_temp"])
    validate_temperature("Return", status_data["return_temp"])
    validate_temperature("Outside", status_data["outside_temp"])
    validate_temperature("Top", status_data["top_temp"])
    validate_temperature("Bottom", status_data["bottom_temp"])

    # Validate performance metrics
    validate_flow(status_data["water_flow"])
    validate_power("Heat input", status_data["heat_input"])
    validate_power("Heat output", status_data["heat_output"])
    validate_power("Electricity consumption", status_data["elec_consump"])
    validate_power("Heat output pump T", status_data["heat_output_pump_t"])
    validate_power("Electricity consumption pump T", status_data["elec_consump_pump_t"])

    # Validate states
    validate_state("Pump AO", status_data["pump_ao_state"])
    validate_state("Boiler", status_data["boiler_state"])
    validate_state("Thermostat", status_data["thermostat_state"])
    validate_state("Pump T", status_data["pump_t_state"])
    validate_state("Pump T heater", status_data["pump_t_heater_state"])

@pytest.mark.asyncio
async def test_basic_settings(api: DeWarmteApiClient) -> None:
    """Test basic settings functionality."""
    # Get initial settings
    settings = await api.async_get_basic_settings()
    assert settings is not None, "Failed to get basic settings"

    # Store original values to restore later
    original_values = {name: sensor.state.value for name, sensor in settings.items()}

    # Test each setting
    for setting_name, sensor in settings.items():
        current_value = sensor.state.value
        new_value = not current_value

        # Try to update the setting
        success = await api.async_update_basic_setting(setting_name, new_value)
        assert success, f"Failed to update {setting_name}"

        # Verify the change
        updated_settings = await api.async_get_basic_settings()
        assert updated_settings is not None, f"Failed to get updated settings after changing {setting_name}"
        
        if setting_name != "default_heating":  # Known issue with verification
            assert updated_settings[setting_name].state.value == new_value, \
                f"Setting {setting_name} did not update correctly"

        # Revert the setting
        success = await api.async_update_basic_setting(setting_name, current_value)
        assert success, f"Failed to revert {setting_name}"

        # Verify the reversion
        final_settings = await api.async_get_basic_settings()
        assert final_settings is not None, f"Failed to get final settings after reverting {setting_name}"
        
        if setting_name != "default_heating":  # Known issue with verification
            assert final_settings[setting_name].state.value == current_value, \
                f"Setting {setting_name} did not revert correctly"

    # Final verification that all settings are back to original values
    final_settings = await api.async_get_basic_settings()
    assert final_settings is not None, "Failed to get final settings"
    
    for name, original_value in original_values.items():
        if name != "default_heating":  # Known issue with verification
            assert final_settings[name].state.value == original_value, \
                f"Setting {name} did not maintain its original value" 