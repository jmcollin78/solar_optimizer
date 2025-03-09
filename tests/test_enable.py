""" Test the "enable" flag """
# from unittest.mock import patch
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_set_enable(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing set_enable feature"""

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

    #
    # Disable the device by simulating a call into the switch enable sensor
    #
    enable_switch = search_entity(
        hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert enable_switch is not None

    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None

    assert enable_switch.state == "on"
    # The state of the underlying switch
    assert device_switch.state == "off"
    # The enable state should be True
    assert device_switch.get_attr_extra_state_attributes.get("is_enabled") is True

    await enable_switch.async_turn_off()
    await hass.async_block_till_done()

    assert enable_switch.state == "off"
    assert device.is_enabled is False
    # The enable state should be True
    assert device_switch.get_attr_extra_state_attributes.get("is_enabled") is False

    #
    # Enable the switch device
    #
    await enable_switch.async_turn_on()
    await hass.async_block_till_done()

    assert enable_switch.state == "on"
    assert device.is_enabled is True
    assert device_switch.state == "off"
    # The enable state should be False
    assert device_switch.get_attr_extra_state_attributes.get("is_enabled") is True
