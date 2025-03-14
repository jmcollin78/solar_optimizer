"""Global fixtures for integration_blueprint integration."""
# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)
from unittest.mock import patch

import pytest

from homeassistant.setup import async_setup_component
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import StateMachine

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_optimizer.const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator
from .commons import create_managed_device

# from homeassistant.core import StateMachine

pytest_plugins = "pytest_homeassistant_custom_component"  # pylint: disable=invalid-name


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # pylint: disable=unused-argument
    """Enable all integration in tests"""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture(name="skip_hass_states_get")
def skip_hass_states_get_fixture():
    """Skip the get state in HomeAssistant"""
    with patch.object(StateMachine, "get"):
        yield


@pytest.fixture(name="reset_coordinator")
def reset_coordinator_fixture():
    """Reset the coordinator"""
    SolarOptimizerCoordinator.reset()
    yield


@pytest.fixture(name="config_2_devices_power_not_power")
def define_config_2_devices():
    """ Define a configuration with 2 devices. One with power and the other without power """

    return {
        "solar_optimizer": {
            "algorithm": {
                "initial_temp": 1000,
                "min_temp": 0.1,
                "cooling_factor": 0.95,
                "max_iteration_number": 1000,
            },
            "devices": [
                {
                    "name": "Equipement A",
                    "entity_id": "input_boolean.fake_device_a",
                    "power_max": 1000,
                    "check_usable_template": "{{ True }}",
                    "duration_min": 0.3,
                    "duration_stop_min": 0.1,
                    "action_mode": "action_call",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                    "max_on_time_per_day_min": 10,
                },
                {
                    "name": "Equipement B",
                    "entity_id": "input_boolean.fake_device_b",
                    "power_max": 2000,
                    "power_min": 100,
                    "power_step": 150,
                    "check_usable_template": "{{ False }}",
                    "duration_min": 1,
                    "duration_stop_min": 2,
                    "duration_power_min": 3,
                    "action_mode": "event",
                    "convert_power_divide_factor": 6,
                    "change_power_service": "input_number/set_value",
                    "power_entity_id": "input_number.tesla_amps",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                },
            ],
        }
    }

@pytest.fixture(name="init_solar_optimizer_with_2_devices_power_not_power")
async def init_solar_optimizer_with_2_devices_power_not_power(hass, config_2_devices_power_not_power) -> SolarOptimizerCoordinator:
    """ Initialization of Solar Optimizer with 2 managed device:
    The first don't have the power activated, and second is configured for power.
    The second is also not usable because the temple returns always False
    """
    await async_setup_component(hass, "solar_optimizer", config_2_devices_power_not_power)
    return hass.data[DOMAIN]["coordinator"]


@pytest.fixture(name="config_2_devices_power_not_power_battery")
def define_config_2_devices_battery():
    """Define a configuration with 2 devices. One with power and the other without power"""

    return {
        "solar_optimizer": {
            "algorithm": {
                "initial_temp": 1000,
                "min_temp": 0.1,
                "cooling_factor": 0.95,
                "max_iteration_number": 1000,
            },
            "devices": [
                {
                    "name": "Equipement A",
                    "entity_id": "input_boolean.fake_device_a",
                    "power_max": 1000,
                    "check_usable_template": "{{ True }}",
                    "duration_min": 0.3,
                    "duration_stop_min": 0.1,
                    "action_mode": "action_call",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                    "battery_soc_threshold": 30,
                    "max_on_time_per_day_min": 10,
                },
                {
                    "name": "Equipement B",
                    "entity_id": "input_boolean.fake_device_b",
                    "power_max": 2000,
                    "power_min": 100,
                    "power_step": 150,
                    "check_usable_template": "{{ False }}",
                    "duration_min": 1,
                    "duration_stop_min": 2,
                    "duration_power_min": 3,
                    "action_mode": "event",
                    "convert_power_divide_factor": 6,
                    "change_power_service": "input_number/set_value",
                    "power_entity_id": "input_number.tesla_amps",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                    "battery_soc_threshold": 50,
                },
            ],
        }
    }


@pytest.fixture(name="init_solar_optimizer_with_2_devices_power_not_power_battery")
async def init_solar_optimizer_with_2_devices_power_not_power_battery(
    hass, config_2_devices_power_not_power_battery
) -> SolarOptimizerCoordinator:
    """Initialization of Solar Optimizer with 2 managed device:
    The first don't have the power activated, and second is configured for power.
    The second is also not usable because the temple returns always False
    """
    await async_setup_component(
        hass, "solar_optimizer", config_2_devices_power_not_power_battery
    )
    return hass.data[DOMAIN]["coordinator"]


@pytest.fixture(name="init_solar_optimizer_entry")
async def init_solar_optimizer_entry(hass):
    """ Initialization of the integration from an Entry """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheSolarOptimizer",
        unique_id="uniqueId",
        data={},
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED


@pytest.fixture(name="config_2_devices_min_on_time_ok")
def define_config_2_devices_min_on_time_ok():
    """Define a configuration with 2 devices. One with min_on_time and offpeak, the other without"""

    return {
        "solar_optimizer": {
            "algorithm": {
                "initial_temp": 1000,
                "min_temp": 0.1,
                "cooling_factor": 0.95,
                "max_iteration_number": 1000,
            },
            "devices": [
                {
                    "name": "Equipement A",
                    "entity_id": "input_boolean.fake_device_a",
                    "power_max": 1000,
                    "check_usable_template": "{{ True }}",
                    "duration_min": 2,
                    "duration_stop_min": 1,
                    "action_mode": "action_call",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                    "battery_soc_threshold": 30,
                    "max_on_time_per_day_min": 10,
                    "min_on_time_per_day_min": 5,
                    "offpeak_time": "23:00",
                },
                {
                    "name": "Equipement B",
                    "entity_id": "input_boolean.fake_device_b",
                    "power_max": 2000,
                    "check_usable_template": "{{ False }}",
                    "duration_min": 1,
                    "duration_stop_min": 2,
                    "duration_power_min": 3,
                    "action_mode": "action_call",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                },
            ],
        }
    }


@pytest.fixture(name="init_solar_optimizer_with_2_devices_min_on_time_ok")
async def init_solar_optimizer_with_2_devices_min_on_time_ok(
    hass, config_2_devices_min_on_time_ok
) -> SolarOptimizerCoordinator:
    """Initialization of Solar Optimizer with 2 managed device"""
    await async_setup_component(
        hass, "solar_optimizer", config_2_devices_min_on_time_ok
    )
    return hass.data[DOMAIN]["coordinator"]


@pytest.fixture(name="config_devices_offpeak_morning")
def define_config_devices_offpeak_morning():
    """Define a configuration with 1 devices which have its offpeak_time on morning"""

    return {
        "solar_optimizer": {
            "algorithm": {
                "initial_temp": 1000,
                "min_temp": 0.1,
                "cooling_factor": 0.95,
                "max_iteration_number": 1000,
            },
            "devices": [
                {
                    "name": "Equipement A",
                    "entity_id": "input_boolean.fake_device_a",
                    "power_max": 1000,
                    "check_usable_template": "{{ True }}",
                    "duration_min": 2,
                    "duration_stop_min": 1,
                    "action_mode": "action_call",
                    "activation_service": "input_boolean/turn_on",
                    "deactivation_service": "input_boolean/turn_off",
                    "battery_soc_threshold": 30,
                    "max_on_time_per_day_min": 10,
                    "min_on_time_per_day_min": 5,
                    "offpeak_time": "01:00",
                }
            ],
        }
    }


@pytest.fixture(name="init_solar_optimizer_with_devices_offpeak_morning")
async def init_solar_optimizer_with_devices_offpeak_morning(
    hass, config_devices_offpeak_morning
) -> SolarOptimizerCoordinator:
    """Initialization of Solar Optimizer with 2 managed device"""
    await async_setup_component(hass, "solar_optimizer", config_devices_offpeak_morning)
    return hass.data[DOMAIN]["coordinator"]


@pytest.fixture(name="init_solar_optimizer_central_config")
async def init_solar_optimizer_central_config(hass):
    """Initialization of the integration from an Entry"""
    entry_central = MockConfigEntry(
        domain=DOMAIN,
        title="Central",
        unique_id="centralUniqueId",
        data={
            CONF_REFRESH_PERIOD_SEC: 60,
            CONF_DEVICE_TYPE: CONF_DEVICE_CENTRAL,
            CONF_POWER_CONSUMPTION_ENTITY_ID: "sensor.fake_power_consumption",
            CONF_POWER_PRODUCTION_ENTITY_ID: "sensor.fake_power_production",
            CONF_SELL_COST_ENTITY_ID: "input_number.fake_sell_cost",
            CONF_BUY_COST_ENTITY_ID: "input_number.fake_buy_cost",
            CONF_SELL_TAX_PERCENT_ENTITY_ID: "input_number.fake_sell_tax_percent",
            CONF_SMOOTH_PRODUCTION: True,
            CONF_BATTERY_SOC_ENTITY_ID: "sensor.fake_battery_soc",
            CONF_RAZ_TIME: "05:00",
        },
    )
    device_central = await create_managed_device(
        hass,
        entry_central,
        "centralUniqueId",
    )
