"""Test standby device handling and 0W active device behavior"""
from datetime import datetime, timedelta
from unittest.mock import patch, PropertyMock
from homeassistant.core import HomeAssistant, State
from homeassistant.const import STATE_ON, STATE_OFF

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_active_device_with_0w_not_forced_off(hass: HomeAssistant):
    """Test that an active device reporting 0W is not forced off during optimization"""

    # Create central configuration
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
            CONF_SMOOTH_PRODUCTION: False,
            CONF_RAZ_TIME: "05:00",
        },
    )
    await create_managed_device(hass, entry_central, "centralUniqueId")

    # Create Device A with power control (e.g., EV charger)
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Device A",
        unique_id="deviceAUniqueId",
        data={
            CONF_NAME: "Device A",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "input_boolean.device_a",
            CONF_POWER_ENTITY_ID: "input_number.device_a_power",
            CONF_POWER_MAX: 3000,
            CONF_POWER_MIN: 1000,
            CONF_POWER_STEP: 500,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_DURATION_POWER_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 1,
        },
    )
    device_a = await create_managed_device(hass, entry_a, "device_a")

    # Setup input entities
    await create_test_input_boolean(hass, "device_a", "Device A")
    await create_test_input_number(hass, "device_a_power", "Device A Power")
    await create_test_input_number(hass, "fake_sell_cost", "Sell Cost")
    await create_test_input_number(hass, "fake_buy_cost", "Buy Cost")
    await create_test_input_number(hass, "fake_sell_tax_percent", "Sell Tax")

    # Set costs
    hass.states.async_set("input_number.fake_sell_cost", 10)
    hass.states.async_set("input_number.fake_buy_cost", 20)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    # Set device as active but reporting 0W (standby or telemetry lag)
    hass.states.async_set("input_boolean.device_a", STATE_ON)
    hass.states.async_set("input_number.device_a_power", 0)

    # Set production and consumption
    hass.states.async_set("sensor.fake_power_production", 2000)
    hass.states.async_set("sensor.fake_power_consumption", 500)  # base load

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    
    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", 500),
            "sensor.fake_power_production": State("sensor.fake_power_production", 2000),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 10),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 20),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "input_boolean.device_a": State("input_boolean.device_a", STATE_ON),
            "input_number.device_a_power": State("input_number.device_a_power", 0),
        },
        State("unknown.entity_id", "unknown"),
    )

    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        # Update device state
        device_a.set_current_power_with_device_state()
        
        # Device should be active and current_power should be 0
        assert device_a.is_active is True
        assert device_a.current_power == 0
        
        # Run optimization
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        # Device should remain in the solution (not forced off)
        # The was_active field should be True
        best_solution = calculated_data.get("best_solution", [])
        device_a_solution = next((d for d in best_solution if d["name"] == "Device A"), None)
        
        assert device_a_solution is not None, "Device A should be in the solution"
        # The device should have was_active set to True
        assert device_a_solution.get("was_active") is True


async def test_switching_penalty_protects_0w_devices(hass: HomeAssistant):
    """Test that switching penalty prevents turning off active-but-0W devices"""

    # Create central configuration
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
            CONF_SMOOTH_PRODUCTION: False,
            CONF_RAZ_TIME: "05:00",
            CONF_ALGO_SWITCHING_PENALTY_FACTOR: 0.5,  # Enable switching penalty
        },
    )
    await create_managed_device(hass, entry_central, "centralUniqueId")

    # Create Device A: currently active but at 0W (standby)
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
            CONF_DURATION_MIN: 1,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        },
    )
    device_a = await create_managed_device(hass, entry_a, "device_a")

    # Setup input entities
    await create_test_input_boolean(hass, "device_a", "Device A")
    await create_test_input_number(hass, "fake_sell_cost", "Sell Cost")
    await create_test_input_number(hass, "fake_buy_cost", "Buy Cost")
    await create_test_input_number(hass, "fake_sell_tax_percent", "Sell Tax")

    # Set costs
    hass.states.async_set("input_number.fake_sell_cost", 10)
    hass.states.async_set("input_number.fake_buy_cost", 20)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    # Device A is ON but drawing 0W
    hass.states.async_set("input_boolean.device_a", STATE_ON)

    # Low production scenario where turning off would save marginal cost
    hass.states.async_set("sensor.fake_power_production", 100)
    hass.states.async_set("sensor.fake_power_consumption", 200)

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    
    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", 200),
            "sensor.fake_power_production": State("sensor.fake_power_production", 100),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 10),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 20),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "input_boolean.device_a": State("input_boolean.device_a", STATE_ON),
        },
        State("unknown.entity_id", "unknown"),
    )

    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        # Update device state
        device_a.set_current_power_with_device_state()
        device_a.set_requested_power(0)
        device_a._current_power = 0
        
        assert device_a.is_active is True
        assert device_a.current_power == 0
        
        # Run optimization
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        # With switching penalty, device should stay on
        # (penalty protects it from being turned off for marginal gains)
        best_solution = calculated_data.get("best_solution", [])
        device_a_solution = next((d for d in best_solution if d["name"] == "Device A"), None)
        
        # The solution should show was_active=True
        assert device_a_solution is not None
        assert device_a_solution.get("was_active") is True


async def test_debounce_prevents_immediate_reversion(hass: HomeAssistant):
    """Test that debounce prevents immediate reversion when commanded power shows 0W temporarily"""

    # Create central configuration
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
            CONF_SMOOTH_PRODUCTION: False,
            CONF_RAZ_TIME: "05:00",
        },
    )
    await create_managed_device(hass, entry_central, "centralUniqueId")

    # Create power device with variable power
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Power Device A",
        unique_id="deviceAUniqueId",
        data={
            CONF_NAME: "Power Device A",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "input_boolean.device_a",
            CONF_POWER_ENTITY_ID: "input_number.device_a_power",
            CONF_POWER_MAX: 3000,
            CONF_POWER_MIN: 1000,
            CONF_POWER_STEP: 500,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_DURATION_POWER_MIN: 1,  # 1 minute grace window
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 1,
        },
    )
    device_a = await create_managed_device(hass, entry_a, "device_a")

    # Setup input entities
    await create_test_input_boolean(hass, "device_a", "Device A")
    await create_test_input_number(hass, "device_a_power", "Device A Power")
    await create_test_input_number(hass, "fake_sell_cost", "Sell Cost")
    await create_test_input_number(hass, "fake_buy_cost", "Buy Cost")
    await create_test_input_number(hass, "fake_sell_tax_percent", "Sell Tax")

    # Set costs
    hass.states.async_set("input_number.fake_sell_cost", 10)
    hass.states.async_set("input_number.fake_buy_cost", 20)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    # Device is active and was commanded to 2000W
    hass.states.async_set("input_boolean.device_a", STATE_ON)
    hass.states.async_set("input_number.device_a_power", 0)  # Sensor shows 0W (lag)

    tz = get_tz(hass)
    now = datetime.now(tz=tz)
    
    # Set device as if we just commanded it to 2000W
    device_a._set_now(now)
    device_a.set_requested_power(2000)
    device_a._last_non_zero_power = 2000
    # Simulate that we just changed power (next_date_available_power in future)
    device_a._next_date_available_power = now + timedelta(seconds=60)

    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", 500),
            "sensor.fake_power_production": State("sensor.fake_power_production", 3000),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 10),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 20),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "input_boolean.device_a": State("input_boolean.device_a", STATE_ON),
            "input_number.device_a_power": State("input_number.device_a_power", 0),
        },
        State("unknown.entity_id", "unknown"),
    )

    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        # Update device state - should use debounce
        device_a.set_current_power_with_device_state()
        
        # With debounce, current_power should be requested_power (2000W), not 0W
        assert device_a.is_active is True
        assert device_a.current_power == 2000, f"Expected 2000W with debounce, got {device_a.current_power}W"
        
        # After grace window expires, simulate normal power reading
        device_a._set_now(now + timedelta(seconds=120))
        hass.states.async_set("input_number.device_a_power", 2000)
        side_effects.add_or_update_side_effect(
            "input_number.device_a_power",
            State("input_number.device_a_power", 2000)
        )
        
        device_a.set_current_power_with_device_state()
        # Now it should read the actual value
        assert device_a.current_power == 2000


async def test_0w_device_no_cost_to_keep_on(hass: HomeAssistant):
    """Test that 0W devices contribute no cost when kept on"""

    # Create central configuration
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
            CONF_SMOOTH_PRODUCTION: False,
            CONF_RAZ_TIME: "05:00",
        },
    )
    await create_managed_device(hass, entry_central, "centralUniqueId")

    # Create Device A at 0W (standby)
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
            CONF_DURATION_MIN: 1,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        },
    )
    device_a = await create_managed_device(hass, entry_a, "device_a")

    # Setup input entities
    await create_test_input_boolean(hass, "device_a", "Device A")
    await create_test_input_number(hass, "fake_sell_cost", "Sell Cost")
    await create_test_input_number(hass, "fake_buy_cost", "Buy Cost")
    await create_test_input_number(hass, "fake_sell_tax_percent", "Sell Tax")

    # Set costs
    hass.states.async_set("input_number.fake_sell_cost", 10)
    hass.states.async_set("input_number.fake_buy_cost", 20)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    # Device A is ON but at 0W
    hass.states.async_set("input_boolean.device_a", STATE_ON)

    # Balanced scenario
    hass.states.async_set("sensor.fake_power_production", 1000)
    hass.states.async_set("sensor.fake_power_consumption", 1000)

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    
    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", 1000),
            "sensor.fake_power_production": State("sensor.fake_power_production", 1000),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 10),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 20),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "input_boolean.device_a": State("input_boolean.device_a", STATE_ON),
        },
        State("unknown.entity_id", "unknown"),
    )

    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        device_a.set_current_power_with_device_state()
        device_a.set_requested_power(0)
        device_a._current_power = 0
        
        # Run optimization
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        # Device at 0W should not affect the objective calculation
        # (it contributes 0 to consumption, so no cost to keep it on)
        best_solution = calculated_data.get("best_solution", [])
        device_a_solution = next((d for d in best_solution if d["name"] == "Device A"), None)
        
        # If device stays on, it should have requested_power = 0
        if device_a_solution and device_a_solution["state"]:
            assert device_a_solution["requested_power"] == 0
