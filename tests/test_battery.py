""" Test the "is_usable" flag with battery """

# from unittest.mock import patch
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_is_usable(
    hass: HomeAssistant,
    init_solar_optimizer_with_2_devices_power_not_power_battery,
    init_solar_optimizer_entry,  # pylint: disable=unused-argument
):
    """Testing is_usable feature"""

    coordinator: SolarOptimizerCoordinator = (
        init_solar_optimizer_with_2_devices_power_not_power_battery
    )

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2

    device: ManagedDevice = coordinator.devices[0]
    assert device.name == "Equipement A"
    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )

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
