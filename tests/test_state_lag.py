"""Test for state lag between command and HA state update"""
from unittest.mock import patch, MagicMock
from datetime import datetime

from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_device_switching_with_state_lag(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Test that power distribution is correct when HA state lags behind commands
    
    This test simulates the scenario described in the bug:
    1. Device A is ON with 1000W
    2. Algorithm turns Device A OFF and Device B ON (1900W)
    3. In the next cycle, HA state hasn't updated yet (Device A still shows ON, Device B still shows OFF)
    4. The system should still correctly track that Device B is now using 1900W
    """
    
    # Create Device A - simple on/off device
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Device A",
        unique_id="deviceAUniqueId",
        data={
            CONF_NAME: "Device A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.1,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        },
    )

    device_a = await create_managed_device(hass, entry_a, "device_a")
    assert device_a is not None

    # Create Device B - simple on/off device with higher power
    entry_b = MockConfigEntry(
        domain=DOMAIN,
        title="Device B",
        unique_id="deviceBUniqueId",
        data={
            CONF_NAME: "Device B",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.device_b",
            CONF_POWER_MAX: 1900,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.1,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        },
    )

    device_b = await create_managed_device(hass, entry_b, "device_b")
    assert device_b is not None

    # Create fake input_booleans for both devices
    await create_test_input_boolean(hass, "input_boolean.device_a", "Device A")
    await create_test_input_boolean(hass, "input_boolean.device_b", "Device B")

    # Turn Device A on initially
    fake_input_bool_a = search_entity(hass, "input_boolean.device_a", INPUT_BOOLEAN_DOMAIN)
    fake_input_bool_b = search_entity(hass, "input_boolean.device_b", INPUT_BOOLEAN_DOMAIN)
    
    await fake_input_bool_a.async_turn_on()
    await hass.async_block_till_done()

    # Verify initial state - Device A is ON
    assert device_a.is_active is True
    device_a.set_current_power_with_device_state()
    assert device_a.current_power == 1000
    
    # Device B is OFF
    assert device_b.is_active is False
    device_b.set_current_power_with_device_state()
    assert device_b.current_power == 0

    # Simulate the algorithm's decision: turn Device A OFF, turn Device B ON
    # This sets requested_power for both devices
    await device_a.deactivate()
    device_a.set_requested_power(0)
    
    await device_b.activate(1900)
    device_b.set_requested_power(1900)
    
    # At this point, the devices have been commanded but HA state hasn't updated yet
    # Device A's input_boolean is still ON
    # Device B's input_boolean is still OFF
    
    # Now simulate the next cycle where set_current_power_with_device_state is called
    # This is the critical moment where the bug would occur without the fix
    
    device_a.set_current_power_with_device_state()
    device_b.set_current_power_with_device_state()
    
    # With the fix:
    # Device A: requested_power=0, HA state shows ON (1000W)
    #   -> Should use requested_power=0 (deactivation lag handling)
    # Device B: requested_power=1900, HA state shows OFF (0W)  
    #   -> Should use requested_power=1900 (activation lag handling)
    
    assert device_a.current_power == 0, \
        f"Device A should use requested_power=0W even though HA state shows ON (deactivation lag). Got {device_a.current_power}W"
    
    assert device_b.current_power == 1900, \
        f"Device B should use requested_power=1900W even though HA state shows OFF (activation lag). Got {device_b.current_power}W"
    
    # Total distributed power should now correctly be 0 + 1900 = 1900W
    # NOT 1000 + 0 = 1000W (the bug) or 1000 + 1900 = 2900W (old understanding)
    # This prevents the algorithm from thinking there's more power available than there is


async def test_device_power_tracking_with_requested_power(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Test that requested_power is used when it's higher than actual state power
    
    This specifically tests the fix where we use max(requested_power, actual_state_power)
    when requested_power > 0, to handle state lag.
    """
    
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Device",
        unique_id="testDeviceUniqueId",
        data={
            CONF_NAME: "Test Device",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.test_device",
            CONF_POWER_MAX: 2000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.1,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        },
    )

    device = await create_managed_device(hass, entry, "test_device")
    await create_test_input_boolean(hass, "input_boolean.test_device", "Test Device")
    
    # Test 1: Device OFF in HA, but we just turned it on (requested_power=2000)
    # Should use requested_power
    device.set_requested_power(2000)
    device.set_current_power_with_device_state()
    assert device.current_power == 2000, \
        "Should use requested_power when device state hasn't caught up"
    
    # Test 2: Device ON in HA, requested_power matches
    fake_input_bool = search_entity(hass, "input_boolean.test_device", INPUT_BOOLEAN_DOMAIN)
    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()
    
    device.set_requested_power(2000)
    device.set_current_power_with_device_state()
    assert device.current_power == 2000, \
        "Should use actual state when it matches requested"
    
    # Test 3: Device OFF in HA, requested_power=0 (we turned it off and HA updated)
    # Should use actual state (0)
    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()
    
    device.set_requested_power(0)
    device.set_current_power_with_device_state()
    assert device.current_power == 0, \
        "Should use actual state (0) when requested_power is 0 and HA updated"
    
    # Test 4: Device ON in HA (old state), but we turned it off (requested_power=0)
    # This is DEACTIVATION LAG - should use requested_power=0
    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()
    
    device.set_requested_power(0)  # We asked to turn off
    device.set_current_power_with_device_state()
    # With the fix: should use requested_power=0 (deactivation lag)
    # This prevents counting the device as still using power when we just turned it off
    assert device.current_power == 0, \
        "Should use requested_power=0 when device was turned off but HA still shows ON (deactivation lag)"
    
    # Test 5: Device consuming more than requested (both ON)
    # Should trust actual state (device might be using more power than expected)
    device.set_requested_power(1000)  # We asked for 1000W
    # But actual state shows 2000W (device using more than requested)
    device.set_current_power_with_device_state()
    assert device.current_power == 2000, \
        "Should trust actual state when device is consuming more than requested"
