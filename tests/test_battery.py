""" Test the "is_usable" flag with battery """

from unittest.mock import patch, call

# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator

async def test_is_usable(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing is_usable feature"""
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
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )

    assert device is not None
    assert device.name == "Equipement A"
    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )

    assert device_switch is not None

    assert (
        device_switch.get_attr_extra_state_attributes.get("battery_soc_threshold") == 30
    )

    # no soc set
    assert device.is_usable is True
    assert device_switch.get_attr_extra_state_attributes.get("is_usable") is True

    device.set_battery_soc(20)
    # device A threshold is 30
    assert device.is_usable is False
    # Change state to force writing new state
    device_switch.update_custom_attributes(device)
    assert device_switch.get_attr_extra_state_attributes.get("is_usable") is False

    device.set_battery_soc(30)
    # device A threshold is 30
    assert device.is_usable is True
    device_switch.update_custom_attributes(device)
    assert device_switch.get_attr_extra_state_attributes.get("is_usable") is True

    device.set_battery_soc(40)
    # device A threshold is 30
    assert device.is_usable is True
    device_switch.update_custom_attributes(device)
    assert device_switch.get_attr_extra_state_attributes.get("is_usable") is True

    device.set_battery_soc(None)
    # device A threshold is 30
    assert device.is_usable is True
    device_switch.update_custom_attributes(device)
    assert device_switch.get_attr_extra_state_attributes.get("is_usable") is True


@pytest.mark.parametrize(
    "consumption_power, production_power, battery_charge_power, device_power_max, battery_soc, battery_soc_threshold, is_activated",
    [
        # fmt: off
        # enough production + battery charge power
        ( -1000, 2000, -500, 1000, 10, 0, True),
        # not enough
        ( 1000, 2000, 500, 1000, 10, 0, False),
        # enough but battery_soc too low
        ( -1000, 2000, -500, 1000, 10, 20, False),
        # not enough production  charge power
        ( -500, 2000, 0, 1000, 10, 0, False),
        # enough production with battery discharge  charge power
        ( -500, 2000, -500, 1000, 10, 0, True),
        # fmt: on
    ],
)
async def test_battery_power(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    consumption_power,
    production_power,
    battery_charge_power,
    device_power_max,
    battery_soc,
    battery_soc_threshold,
    is_activated,
):
    """Testing battery power feature"""
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: device_power_max,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: battery_soc_threshold,
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )

    assert device is not None
    assert device.name == "Equipement A"
    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )

    assert device_switch is not None

    # starts the algorithm
    coordinator = SolarOptimizerCoordinator.get_coordinator()

    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State(
                "sensor.fake_power_consumption", consumption_power
            ),
            "sensor.fake_power_production": State(
                "sensor.fake_power_production", production_power
            ),
            "sensor.fake_battery_charge_power": State(
                "sensor.fake_battery_charge_power", battery_charge_power
            ),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 1),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 1),
            "input_number.fake_sell_tax_percent": State(
                "input_number.fake_sell_tax_percent", 0
            ),
            "sensor.fake_battery_soc": State("sensor.fake_battery_soc", battery_soc),
        },
        State("unknown.entity_id", "unknown"),
    )

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
    # fmt:on
        calculated_data = await coordinator._async_update_data()

        assert  calculated_data["total_power"] == (1000 if is_activated else 0)
        assert  calculated_data["equipement_a"].is_waiting is is_activated

        assert calculated_data["best_solution"][0]["name"] == "Equipement A"
        assert calculated_data["best_solution"][0]["state"] is is_activated
