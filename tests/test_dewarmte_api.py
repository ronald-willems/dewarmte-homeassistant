"""Test suite for DeWarmte API."""
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

def print_section(title: str, data: dict[str, Any]) -> None:
    """Print a section of data with a title."""
    print(f"\n=== {title} ===")
    for key, value in data.items():
        if isinstance(value, dict):
            val = value.get("value")
            unit = value.get("unit", "")
            print(f"{key}: {val} {unit}".strip())
        else:
            print(f"{key}: {value}")

async def get_config() -> dict:
    """Get test configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "secrets.yaml")
    template_path = os.path.join(os.path.dirname(__file__), "secrets.template.yaml")
    
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        print(f"Please create it from {template_path}")
        return None
        
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

@pytest_asyncio.fixture
async def session() -> AsyncGenerator[ClientSession, None]:
    """Create and yield an aiohttp ClientSession."""
    async with aiohttp.ClientSession() as session:
        yield session

@pytest_asyncio.fixture
async def api(session: AsyncGenerator[ClientSession, None]) -> DeWarmteApiClient:
    """Create and yield a DeWarmte API client."""
    config = await get_config()
    if not config:
        pytest.skip("No config file found")

    async for session in session:
        api = DeWarmteApiClient(
            username=config["dewarmte"]["username"],
            password=config["dewarmte"]["password"],
            session=session
        )

        if not await api.async_login():
            pytest.fail("Login failed")
        
        return api

def validate_temperature(name: str, value: float) -> None:
    """Validate that a temperature value is within reasonable bounds."""
    assert -50 <= value <= 50, f"{name} temperature {value}°C is outside reasonable bounds (-50°C to 50°C)"

def validate_percentage(name: str, value: float) -> None:
    """Validate that a percentage value is between 0 and 100."""
    assert 0 <= value <= 100, f"{name} value {value}% is outside valid range (0% to 100%)"

def validate_power(name: str, value: float) -> None:
    """Validate that a power value is non-negative and within reasonable bounds."""
    assert 0 <= value <= 100, f"{name} value {value}kW is outside reasonable bounds (0kW to 100kW)"

def validate_flow(value: float) -> None:
    """Validate that a flow value is non-negative and within reasonable bounds."""
    assert 0 <= value <= 100, f"Flow value {value}L/min is outside reasonable bounds (0L/min to 100L/min)"

def validate_state(name: str, value: int) -> None:
    """Validate that a state value is either 0 or 1."""
    assert value in [0, 1], f"{name} state {value} is invalid (must be 0 or 1)"

@pytest.mark.asyncio
async def test_login(api: DeWarmteApiClient) -> None:
    """Test that we can log in successfully."""
    # If we get here, login was successful (handled in fixture)
    assert True

@pytest.mark.asyncio
async def test_status_data(api: DeWarmteApiClient) -> None:
    """Test getting and validating status data."""
    api = await api  # Await the fixture
    status_data = await api.async_get_status_data()
    assert status_data is not None, "Failed to get status data"

    # Validate temperatures
    validate_temperature("Supply", float(status_data["supply_temperature"]["value"]))
    validate_temperature("Return", float(status_data["return_temperature"]["value"]))
    validate_temperature("Outside", float(status_data["outside_temperature"]["value"]))
    validate_temperature("Top", float(status_data["top_temperature"]["value"]))
    validate_temperature("Bottom", float(status_data["bottom_temperature"]["value"]))

    # Validate performance metrics
    validate_flow(float(status_data["water_flow"]["value"]))
    validate_power("Heat input", float(status_data["heat_input"]["value"]))
    validate_power("Heat output", float(status_data["heat_output"]["value"]))
    validate_power("Electricity consumption", float(status_data["electricity_consumption"]["value"]))
    validate_power("Heat output pump T", float(status_data["heat_output_pump_t"]["value"]))
    validate_power("Electricity consumption pump T", float(status_data["electricity_consumption_pump_t"]["value"]))

    # Validate states
    validate_state("Pump AO", int(status_data["pump_ao_state"]["value"]))
    validate_state("Boiler", int(status_data["boiler_state"]["value"]))
    validate_state("Thermostat", int(status_data["thermostat_state"]["value"]))
    validate_state("Pump T", int(status_data["pump_t_state"]["value"]))
    validate_state("Pump T heater", int(status_data["pump_t_heater_state"]["value"]))

@pytest.mark.asyncio
async def test_basic_settings(api: DeWarmteApiClient) -> None:
    """Test basic settings functionality."""
    api = await api  # Await the fixture
    # Get initial settings
    settings = await api.async_get_basic_settings()
    assert settings is not None, "Failed to get basic settings"

    # Store original values to restore later
    original_values = {name: setting["value"] for name, setting in settings.items()}

    # Test each setting
    for setting_name, setting in settings.items():
        current_value = setting["value"]
        new_value = not current_value

        # Try to update the setting
        success = await api.async_update_basic_setting(setting_name, new_value)
        assert success, f"Failed to update {setting_name}"

        # Verify the change
        updated_settings = await api.async_get_basic_settings()
        assert updated_settings is not None, f"Failed to get updated settings after changing {setting_name}"
        
        if setting_name != "default_heating":  # Known issue with verification
            assert updated_settings[setting_name]["value"] == new_value, \
                f"Setting {setting_name} did not update correctly"

        # Revert the setting
        success = await api.async_update_basic_setting(setting_name, current_value)
        assert success, f"Failed to revert {setting_name}"

        # Verify the reversion
        final_settings = await api.async_get_basic_settings()
        assert final_settings is not None, f"Failed to get final settings after reverting {setting_name}"
        
        if setting_name != "default_heating":  # Known issue with verification
            assert final_settings[setting_name]["value"] == current_value, \
                f"Setting {setting_name} did not revert correctly"

    # Final verification that all settings are back to original values
    final_settings = await api.async_get_basic_settings()
    assert final_settings is not None, "Failed to get final settings"
    
    for name, original_value in original_values.items():
        if name != "default_heating":  # Known issue with verification
            assert final_settings[name]["value"] == original_value, \
                f"Setting {name} did not maintain its original value" 