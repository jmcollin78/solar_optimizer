""" Nominal Unit test module"""
# from unittest.mock import patch
from datetime import datetime, time

from homeassistant.setup import async_setup_component

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_normal_start_one_device(hass: HomeAssistant):
    """A full nominal start of Solar Optimizer"""

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

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 50,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 1,
            CONF_OFFPEAK_TIME: "22:00",
        },
    )

    device_b = await create_managed_device(
        hass,
        entry_a,
        "eqtAUniqueId",
    )

    entry_b = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement B",
        unique_id="eqtBUniqueId",
        data={
            CONF_NAME: "Equipement B",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_b",
            CONF_POWER_MAX: 2000,
            CONF_POWER_MIN: 100,
            CONF_POWER_STEP: 150,
            CONF_CHECK_USABLE_TEMPLATE: "{{ False }}",
            CONF_DURATION_MIN: 1,
            CONF_DURATION_STOP_MIN: 2,
            CONF_DURATION_POWER_MIN: 3,
            CONF_ACTION_MODE: CONF_ACTION_MODE_EVENT,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 6,
            CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
            CONF_POWER_ENTITY_ID: "input_number.tesla_amps",
            CONF_BATTERY_SOC_THRESHOLD: 0,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 0,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 0,
            CONF_OFFPEAK_TIME: "00:00",
        },
    )

    device_b = await create_managed_device(
        hass,
        entry_b,
        "eqtBUniqueId",
    )

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None

    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2

    #
    # First device tests
    device:ManagedDevice = coordinator.devices[0]
    assert device.name == "Equipement A"
    assert device.is_enabled is True
    assert device.is_active is False
    assert device.is_usable is True
    assert device.is_waiting is False
    assert device.power_max == 1000
    assert device.power_min == -1
    assert device.power_step == 0
    assert device.duration_sec == 18
    assert device.duration_stop_sec == 6
    # duration_power is set to duration_sec in not power mode
    assert device.duration_power_sec == 18
    assert device.entity_id == "input_boolean.fake_device_a"
    assert device.power_entity_id is None
    assert device.current_power == 0
    assert device.requested_power == 0
    assert device.can_change_power is False
    assert device.max_on_time_per_day_sec == 10 * 60
    assert device.min_on_time_per_day_sec == 1 * 60
    assert device.battery_soc_threshold == 50
    assert device.offpeak_time == time(22, 0)

    tz = get_tz(hass) # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    assert (device.next_date_available.astimezone(tz) - now).total_seconds() < 1
    assert (device.next_date_available_power.astimezone(tz) - now).total_seconds() < 1

    assert device.convert_power_divide_factor == 1

    #
    # Second device test
    #
    device = coordinator.devices[1]
    assert device.name == "Equipement B"
    assert device.is_enabled is True
    assert device.is_active is False
    assert device.is_usable is False
    assert device.is_waiting is False
    assert device.power_max == 2000
    assert device.power_min == 100
    assert device.power_step == 150
    assert device.duration_sec == 60
    assert device.duration_stop_sec == 120
    assert device.duration_power_sec == 180
    assert device.entity_id == "input_boolean.fake_device_b"
    assert device.power_entity_id == "input_number.tesla_amps"
    assert device.current_power == 0
    assert device.requested_power == 0
    assert device.can_change_power is True
    assert device.max_on_time_per_day_sec == 24 * 60 * 60
    assert device.min_on_time_per_day_sec == 0
    assert device.battery_soc_threshold == 0
    assert device.offpeak_time == time(0, 0)

    tz = get_tz(hass) # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    assert (device.next_date_available.astimezone(tz) - now).total_seconds() < 1
    assert (device.next_date_available_power.astimezone(tz) - now).total_seconds() < 1

    assert device.convert_power_divide_factor == 6
