""" Priority Unit test module"""
# from unittest.mock import patch
from datetime import datetime, time

from homeassistant.setup import async_setup_component
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_priority_select_creation(hass: HomeAssistant):
    """A nominal start of Solar Optimizer should create the select entities"""

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

    assert device_central is None
    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    assert coordinator.is_central_config_done is True

    priority_weight_entity = search_entity(hass, "select.solar_optimizer_priority_weight", SELECT_DOMAIN)
    assert priority_weight_entity is not None
    assert priority_weight_entity.name == "Priority weight"
    assert priority_weight_entity.current_option == PRIORITY_WEIGHT_NULL
    assert priority_weight_entity.options == PRIORITY_WEIGHTS

    assert coordinator.priority_weight == PRIORITY_WEIGHT_MAP.get(PRIORITY_WEIGHT_NULL)

    # Change the priority weight
    priority_weight_entity.select_option(PRIORITY_WEIGHT_HIGH)
    await hass.async_block_till_done()
    assert priority_weight_entity.current_option == PRIORITY_WEIGHT_HIGH
    assert coordinator.priority_weight == PRIORITY_WEIGHT_MAP.get(PRIORITY_WEIGHT_HIGH)

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
    assert device_a.priority == PRIORITY_MAP.get(PRIORITY_MEDIUM)

    priority_entity_a = search_entity(hass, "select.solar_optimizer_priority_equipement_a", SELECT_DOMAIN)
    assert priority_entity_a is not None
    assert priority_entity_a.name == "Priority"
    assert priority_entity_a.current_option == PRIORITY_MEDIUM

    # Change the priority weight
    priority_entity_a.select_option(PRIORITY_HIGH)
    await hass.async_block_till_done()
    assert priority_entity_a.current_option == PRIORITY_HIGH
    assert device_a.priority == PRIORITY_MAP.get(PRIORITY_HIGH)


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
    assert device_b.priority == PRIORITY_MAP.get(PRIORITY_MEDIUM)
    priority_entity_b = search_entity(hass, "select.solar_optimizer_priority_equipement_b", SELECT_DOMAIN)
    assert priority_entity_b is not None
    assert priority_entity_b.name == "Priority"
    assert priority_entity_b.current_option == PRIORITY_MEDIUM

    # Change the priority weight
    priority_entity_b.select_option(PRIORITY_HIGH)
    await hass.async_block_till_done()
    assert priority_entity_b.current_option == PRIORITY_HIGH
    assert device_b.priority == PRIORITY_MAP.get(PRIORITY_HIGH)

# In dev env, you should remove the skip decorator
@pytest.mark.skip(reason="Do not work every time due to the random nature of the test")
@pytest.mark.parametrize(
    "consumption_power, production_power, priority_weight, device_a_power_max, priority_a, device_b_power_min, device_b_power_max, priority_b, is_a_activated, is_b_activated, best_objective, device_a_power, device_b_power",
    [
        # fmt: off
        # consumption_power, production_power, priority_weight, device_a_power_max, priority_a, device_b_power_min, device_b_power_max, priority_b, is_a_activated, is_b_activated, best_objective, device_a_power, device_b_power
        # not enough production
        ( 500,               100,              PRIORITY_WEIGHT_NULL, 1000,          PRIORITY_MEDIUM, 0,             "2000", PRIORITY_MEDIUM,             False,          False,     250,               0,              0),
        # not enough production and very high priority
        ( 500,               100,              PRIORITY_WEIGHT_VERY_HIGH, 1000,     PRIORITY_MEDIUM, 0,             "2000", PRIORITY_MEDIUM,             False,          False,     62.5,               0,             0),
        # enough production
        ( -1000,            1000,              PRIORITY_WEIGHT_LOW, 1000,          PRIORITY_MEDIUM, 200,           "2000", PRIORITY_LOW,                True,           False,      0.4,             1000,             0),
        # enough production and very high priority for device B
        ( -1000,            1000,              PRIORITY_WEIGHT_MEDIUM, 1000,        PRIORITY_MEDIUM, 200,           "2000", PRIORITY_VERY_HIGH,          False,          True,      0.25,               0,             1000),
        # large production and low priority for device B, high for device A but A stops at 1000 and B goes to 2000
        ( -2000,            2000,              PRIORITY_WEIGHT_MEDIUM, 1000,        PRIORITY_HIGH, 200,             "2000", PRIORITY_LOW,                 True,          True,      1.25,             1000,             1000),
        # fmt: on
    ],
)
async def test_full_nominal_test_with_priority(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    consumption_power,
    production_power,
    priority_weight,
    device_a_power_max,
    priority_a,
    device_b_power_min,
    device_b_power_max,
    priority_b,
    is_a_activated,
    is_b_activated,
    best_objective,
    device_a_power,
    device_b_power,
):
    """A full test with 2 equipements, one powered and one not powered"""

    # Set the priority weight before running the algorithm
    priority_weight_entity = search_entity(hass, "select.solar_optimizer_priority_weight", SELECT_DOMAIN)
    assert priority_weight_entity is not None
    priority_weight_entity.select_option(priority_weight)
    await hass.async_block_till_done()
    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator.priority_weight == PRIORITY_WEIGHT_MAP.get(priority_weight, 0)

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

    priority_entity_a = search_entity(hass, "select.solar_optimizer_priority_equipement_a", SELECT_DOMAIN)
    assert priority_entity_a is not None
    priority_entity_a.select_option(priority_a)
    await hass.async_block_till_done()

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
            # CONF_BATTERY_SOC_THRESHOLD removed
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

    priority_entity_b = search_entity(hass, "select.solar_optimizer_priority_equipement_b", SELECT_DOMAIN)
    assert priority_entity_b is not None
    priority_entity_b.select_option(priority_b)
    await hass.async_block_till_done()

    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", consumption_power),
            "sensor.fake_power_production": State("sensor.fake_power_production", production_power),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 1),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 1),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "sensor.fake_battery_soc": State("sensor.fake_battery_soc", 0),
        },
        State("unknown.entity_id", "unknown"),
    )

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt:on
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert calculated_data["total_power"] == device_a_power + device_b_power
        assert calculated_data["best_objective"] == best_objective
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
