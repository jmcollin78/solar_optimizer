""" Test the "enable" flag """
# from unittest.mock import patch
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_set_enable(
    hass: HomeAssistant,
    init_solar_optimizer_with_2_devices_power_not_power,
    init_solar_optimizer_entry,  # pylint: disable=unused-argument
):
    """Testing set_enable feature"""

    coordinator: SolarOptimizerCoordinator = (
        init_solar_optimizer_with_2_devices_power_not_power
    )

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2

    device: ManagedDevice = coordinator.devices[0]
    assert device.name == "Equipement A"
    assert device.is_enabled is True

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

    assert enable_switch.state is "on"
    # The state of the underlying switch
    assert device_switch.state is "off"
    # The enable state should be True
    assert device_switch.get_attr_extra_state_attributes.get("is_enabled") is True

    await enable_switch.async_turn_off()
    await hass.async_block_till_done()

    assert enable_switch.state is "off"
    assert device.is_enabled is False
    # The enable state should be True
    assert device_switch.get_attr_extra_state_attributes.get("is_enabled") is False

    #
    # Enable the switch device
    #
    await enable_switch.async_turn_on()
    await hass.async_block_till_done()

    assert enable_switch.state is "on"
    assert device.is_enabled is True
    assert device_switch.state is "off"
    # The enable state should be False
    assert device_switch.get_attr_extra_state_attributes.get("is_enabled") is True
