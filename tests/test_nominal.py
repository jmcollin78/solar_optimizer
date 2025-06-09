""" Nominal Unit test module"""
# from unittest.mock import patch
from datetime import datetime, time

from homeassistant.setup import async_setup_component
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_normal_nominal_start(hass: HomeAssistant):
    """A full nominal start of Solar Optimizer"""

    entry_central = MockConfigEntry(
        domain=DOMAIN,
        title="Central",
        unique_id="centralUniqueId",
        data={
            CONF_NAME: "Central",
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

    device_a = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )

    assert device_a is not None

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
        "equipement_b",
    )

    assert device_b is not None

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    assert coordinator.is_central_config_done is True

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


async def test_normal_nominal_start_with_fixture(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """A test with the init of the central config in fixture"""

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    assert coordinator.is_central_config_done is True

    assert coordinator.devices is not None
    assert len(coordinator.devices) == 0


async def test_empty_start(hass: HomeAssistant, reset_coordinator):
    """A test with no central config"""

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is None


# no_parallel is not useful here but it is a good example
# @pytest.mark.no_parallel
# In dev env, you should remove the skip decorator
@pytest.mark.skip(reason="Do not work every time due to the random nature of the test")
@pytest.mark.parametrize(
    "consumption_power, production_power, battery_charge_power, battery_soc, device_a_power_max, device_b_power_min, device_b_power_max, battery_b_soc_threshold, is_a_activated, is_b_activated, device_a_power, device_b_power",
    [
        # fmt: off
        # consumption_power, production_power, battery_charge_power, battery_soc, device_a_power_max, device_b_power_min, device_b_power_max, battery_b_soc_threshold, is_a_activated, is_b_activated, device_a_power, device_b_power
        # not enough production
        ( 500,               100,              0,                    0,           1000,               0,                  "2000",               "0",                       False,          False,          0,              0),
        # not enough production but battery is charging
        ( 500,               100,              -600,                 0,           1000,               0,                  "2000",               "0",                       False,          True,           0,            100),
        # not enough production but battery is charging but b power min too high
        ( 500,               100,              -600,                 0,           1000,               200,                "2000",               "0",                       False,          False,          0,              0),
        # enough production rejected
        ( -1000,            1000,              0,                    0,           1000,               200,                "2000",               "0",                       True,           False,        1000,             0),
        # enough production rejected + battery charge power
        ( -1000,            1000,              -500,                 0,           1000,               0,                  "2000",               "0",                       True,           True,         1000,           500),
        # enough production rejected + battery charge power but equipement B soc threshold too low
        ( -1000,            1000,              -500,                 10,          1000,               0,                  "2000",              "20",                       True,          False,         1000,             0),
        # fmt: on
    ],
)
async def test_full_nominal_test(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    consumption_power,
    production_power,
    battery_charge_power,
    battery_soc,
    device_a_power_max,
    device_b_power_min,
    device_b_power_max,
    battery_b_soc_threshold,
    is_a_activated,
    is_b_activated,
    device_a_power,
    device_b_power,
):
    """A full test with 2 equipements, one powered and one not powered"""
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: device_a_power_max,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 0,
        },
    )

    device_a = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )

    assert device_a is not None
    assert device_a.name == "Equipement A"
    device_a_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )

    assert device_a_switch is not None

    entry_b = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement B",
        unique_id="eqtBUniqueId",
        data={
            CONF_NAME: "Equipement B",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_b",
            CONF_POWER_MIN: device_b_power_min,
            CONF_POWER_MAX: device_b_power_max,
            CONF_POWER_STEP: 100,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 1,
            CONF_DURATION_STOP_MIN: 0.5,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: battery_b_soc_threshold,
            CONF_DURATION_POWER_MIN: 1,
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 6,
            CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
            CONF_POWER_ENTITY_ID: "input_number.tesla_amps",
        },
    )

    device_b = await create_managed_device(
        hass,
        entry_b,
        "equipement_b",
    )

    assert device_b is not None
    assert device_b.name == "Equipement B"
    device_b_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_b", SWITCH_DOMAIN
    )

    assert device_b_switch is not None

    # starts the algorithm
    coordinator = SolarOptimizerCoordinator.get_coordinator()

    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", consumption_power),
            "sensor.fake_power_production": State("sensor.fake_power_production", production_power),
            "sensor.fake_battery_charge_power": State("sensor.fake_battery_charge_power", battery_charge_power),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 1),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 1),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "sensor.fake_battery_soc": State("sensor.fake_battery_soc", battery_soc),
        },
        State("unknown.entity_id", "unknown"),
    )

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt:on
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert calculated_data["total_power"] == device_a_power + device_b_power
        assert calculated_data["equipement_a"].is_waiting is is_a_activated
        assert calculated_data["equipement_a"].requested_power == device_a_power
        assert calculated_data["equipement_b"].is_waiting is is_b_activated
        assert calculated_data["equipement_b"].requested_power == device_b_power

        assert calculated_data["best_solution"][0]["name"] == "Equipement A"
        assert calculated_data["best_solution"][0]["state"] is is_a_activated
        assert calculated_data["best_solution"][0]["current_power"] == 0
        assert calculated_data["best_solution"][0]["requested_power"] == device_a_power
        assert calculated_data["best_solution"][1]["name"] == "Equipement B"
        assert calculated_data["best_solution"][1]["state"] is is_b_activated
        assert calculated_data["best_solution"][1]["current_power"] == 0
        assert calculated_data["best_solution"][1]["requested_power"] == device_b_power


async def test_migration_from_2_0(hass: HomeAssistant):
    """A test for migration from 2.0 to 2.1"""

    entry_a = MockConfigEntry(
        version=CONFIG_VERSION,
        minor_version=0,
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
    device_a = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )

    assert device_a is not None

    assert device_a.name == "Equipement A"
    assert device_a.power_max == 1000
    assert device_a.battery_soc_threshold == 50
    assert device_a.max_on_time_per_day_sec == 10 * 60
    assert device_a.min_on_time_per_day_sec == 1 * 60


@pytest.mark.parametrize(
    "sell_cost, buy_cost, best_objective",
    [
        (1, 2, 0),
        (1, 1, 0),
        (0, 1, 0),
        (1, 0, 0),
        (-1, 1, 0),
        (1, -1, 0),
        (0, 0, 0),
    ],
)
async def test_negative_or_null_costs(hass: HomeAssistant, init_solar_optimizer_central_config, sell_cost, buy_cost, best_objective):
    """Test handling of negative or null costs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Device",
        unique_id="testDeviceUniqueId",
        data={
            CONF_NAME: "Test Device",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device",
            CONF_POWER_MAX: 1000,
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        },
    )

    device = await create_managed_device(hass, entry, "test_device")
    assert device is not None

    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", -1000),
            "sensor.fake_power_production": State("sensor.fake_power_production", 5000),
            "sensor.fake_battery_charge_power": State("sensor.fake_battery_charge_power", 0),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", sell_cost),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", buy_cost),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
        },
        State("unknown.entity_id", "unknown"),
    )
    coordinator = SolarOptimizerCoordinator.get_coordinator()

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt:on
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()
        assert calculated_data is not None
        assert calculated_data["sell_cost"] == sell_cost
        assert calculated_data["buy_cost"] == buy_cost
        assert calculated_data["best_solution"] is not None
        assert calculated_data["best_solution"][0]["name"] == "Test Device"
        assert calculated_data["best_solution"][0]["state"] is True
        assert calculated_data["best_objective"] == best_objective
