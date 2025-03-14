""" Test the "is_usable" flag with battery """

# from unittest.mock import patch
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


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
