""" Test the "enable" flag """
# from unittest.mock import patch
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_underlying_state_change(
    hass: HomeAssistant,
    init_solar_optimizer_with_2_devices_power_not_power,
    init_solar_optimizer_entry,  # pylint: disable=unused-argument
):
    """Testing underlying state change"""

    coordinator: SolarOptimizerCoordinator = (
        init_solar_optimizer_with_2_devices_power_not_power
    )

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2

    device: ManagedDevice = coordinator.devices[0]
    assert device.name == "Equipement A"
    assert device.is_enabled is True

    # Creates the fake input_boolean
    await create_test_input_boolean(hass, device.entity_id, "fake underlying A")

    fake_input_bool = search_entity(hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN)
    assert fake_input_bool is not None

    #
    # Check initial 'active' state
    #
    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None

    assert device.is_active is False
    # The state of the underlying switch
    assert device_switch.state == "off"
    # The enable state should be True
    assert device_switch.get_attr_extra_state_attributes.get("is_active") is False

    #
    # Send a state change to ON for the underlying switch
    #
    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()

    # The state of the underlying switch
    # The state should be True
    assert device_switch.state == "on"
    assert device.is_active is True
    assert device_switch.get_attr_extra_state_attributes.get("is_active") is True

    #
    # Send a state change to OFF for the underlying switch
    #
    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()

    # The state of the underlying switch
    # The state should be True
    assert device_switch.state == "off"
    assert device.is_active is False
    assert device_switch.get_attr_extra_state_attributes.get("is_active") is False

async def test_underlying_state_initialize(hass, init_solar_optimizer_with_2_devices_power_not_power):
    """ Test the initialization of underlying device """

    # Creates the fake input_boolean
    device_id="input_boolean.fake_device_a"
    await create_test_input_boolean(hass, device_id, "fake underlying A")

    fake_input_bool = search_entity(hass, device_id, INPUT_BOOLEAN_DOMAIN)
    assert fake_input_bool is not None

    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()

    coordinator: SolarOptimizerCoordinator = (
        init_solar_optimizer_with_2_devices_power_not_power
    )

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2

    device: ManagedDevice = coordinator.devices[0]
    assert device.name == "Equipement A"
    assert device.is_active is True

    #
    # Creates the entry manually (after underlying change)
    #
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


    #
    # test the device_switch is on
    #
    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )
    assert device_switch is not None
    assert device_switch.state == "on"
    assert device_switch.get_attr_extra_state_attributes.get("is_active") is True
