"""Test household consumption deficit handling"""

from unittest.mock import patch
import pytest

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator


@pytest.mark.parametrize(
    "production_power, consumption_power, device_a_power, device_b_power, expected_excess_power, expected_household_base",
    [
        # fmt: off
        # Case 1: Normal case - no deficit
        # Production=6500W, Consumption=300W (includes 0W from devices), base=300W, excess=6200W
        (6500, 300, 0, 0, 6200, 300),
        
        # Case 2: Deficit scenario from user logs
        # Production=6523W, Consumption=287W (sensor reading), Devices=4000W
        # base_household_raw = 287 - 4000 = -3713 (deficit)
        # base_household = max(0, -3713) = 0
        # excess = 6523 - 0 = 6523W (NOT 0!)
        (6523, 287, 4000, 0, 6523, 0),
        
        # Case 3: Small deficit with high production
        # Production=5000W, Consumption=500W, Devices=550W
        # base_household_raw = 500 - 550 = -50 (deficit)
        # base_household = 0
        # excess = 5000 - 0 = 5000W
        (5000, 500, 550, 0, 5000, 0),
        
        # Case 4: Multiple devices causing deficit
        # Production=7000W, Consumption=400W, DeviceA=200W, DeviceB=250W
        # base_household_raw = 400 - 450 = -50
        # base_household = 0
        # excess = 7000 - 0 = 7000W
        (7000, 400, 200, 250, 7000, 0),
        
        # Case 5: Low production with deficit - should still compute correctly
        # Production=100W, Consumption=50W, Device=100W
        # base_household_raw = 50 - 100 = -50
        # base_household = 0
        # excess = max(0, 100 - 0) = 100W
        (100, 50, 100, 0, 100, 0),
        
        # Case 6: No deficit, normal operation
        # Production=3000W, Consumption=1500W (includes 500W from device), Device=500W
        # base_household = 1500 - 500 = 1000W
        # excess = 3000 - 1000 = 2000W
        (3000, 1500, 500, 0, 2000, 1000),
        # fmt: on
    ],
)
async def test_household_deficit_does_not_zero_excess(
    hass: HomeAssistant,
    reset_coordinator,
    production_power,
    consumption_power,
    device_a_power,
    device_b_power,
    expected_excess_power,
    expected_household_base,
):
    """Test that household deficit (negative base_household_raw) does not force available_excess_power to 0"""

    # Create central config
    entry_central = MockConfigEntry(
        domain=DOMAIN,
        title="Central",
        unique_id="centralUniqueId",
        data={
            CONF_NAME: "Configuration",
            CONF_REFRESH_PERIOD_SEC: 60,
            CONF_DEVICE_TYPE: CONF_DEVICE_CENTRAL,
            CONF_POWER_CONSUMPTION_ENTITY_ID: "sensor.fake_power_consumption",
            CONF_POWER_PRODUCTION_ENTITY_ID: "sensor.fake_power_production",
            CONF_SELL_COST_ENTITY_ID: "input_number.fake_sell_cost",
            CONF_BUY_COST_ENTITY_ID: "input_number.fake_buy_cost",
            CONF_SELL_TAX_PERCENT_ENTITY_ID: "input_number.fake_sell_tax_percent",
            CONF_SMOOTH_PRODUCTION: False,
            CONF_SMOOTHING_HOUSEHOLD_WINDOW_MIN: 0,  # No smoothing for these tests
            CONF_BATTERY_SOC_ENTITY_ID: "sensor.fake_battery_soc",
            CONF_BATTERY_CHARGE_POWER_ENTITY_ID: "sensor.fake_battery_charge_power",
            CONF_RAZ_TIME: "05:00",
        },
    )

    entry_central.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_central.entry_id)

    # Create device A if needed
    if device_a_power > 0:
        entry_a = MockConfigEntry(
            domain=DOMAIN,
            title="Equipement A",
            unique_id="eqtAUniqueId",
            data={
                CONF_NAME: "Equipement A",
                CONF_DEVICE_TYPE: CONF_DEVICE,
                CONF_ENTITY_ID: "input_boolean.fake_device_a",
                CONF_POWER_MAX: device_a_power,
                CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
                CONF_DURATION_MIN: 0.3,
                CONF_DURATION_STOP_MIN: 0.1,
                CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
                CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
                CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            },
        )

        device_a = await create_managed_device(hass, entry_a, "equipement_a")
        assert device_a is not None
        # Simulate device A is currently active
        device_a.current_power = device_a_power

    # Create device B if needed
    if device_b_power > 0:
        entry_b = MockConfigEntry(
            domain=DOMAIN,
            title="Equipement B",
            unique_id="eqtBUniqueId",
            data={
                CONF_NAME: "Equipement B",
                CONF_DEVICE_TYPE: CONF_DEVICE,
                CONF_ENTITY_ID: "input_boolean.fake_device_b",
                CONF_POWER_MAX: device_b_power,
                CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
                CONF_DURATION_MIN: 0.3,
                CONF_DURATION_STOP_MIN: 0.1,
                CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
                CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
                CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            },
        )

        device_b = await create_managed_device(hass, entry_b, "equipement_b")
        assert device_b is not None
        # Simulate device B is currently active
        device_b.current_power = device_b_power

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None

    # Set up mock states
    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", consumption_power),
            "sensor.fake_power_production": State("sensor.fake_power_production", production_power),
            "sensor.fake_battery_charge_power": State("sensor.fake_battery_charge_power", 0),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 1),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 1),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "sensor.fake_battery_soc": State("sensor.fake_battery_soc", 50),
        },
        State("unknown.entity_id", "unknown"),
    )

    # Run the update
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        calculated_data = await coordinator._async_update_data()

    # Verify the results
    assert calculated_data is not None
    assert calculated_data["power_production"] == production_power
    assert calculated_data["power_consumption"] == consumption_power

    # Check household base consumption (clamped to >= 0)
    assert (
        calculated_data["household_consumption"] == expected_household_base
    ), f"Expected household_consumption={expected_household_base}, got {calculated_data['household_consumption']}"

    # Check available excess power - this should NOT be 0 when production is high
    assert (
        calculated_data["available_excess_power"] == expected_excess_power
    ), f"Expected available_excess_power={expected_excess_power}, got {calculated_data['available_excess_power']}"


@pytest.mark.parametrize(
    "production_power, consumption_power, device_power, smoothing_window_min, battery_soc, min_export_margin_w, expected_excess",
    [
        # fmt: off
        # Case 1: Deficit with min export margin at 100% SOC
        # Production=6500W, margin=300W, effective=6200W, consumption=287W, device=4000W
        # base_household = max(0, 287-4000) = 0
        # excess = max(0, 6200 - 0) = 6200W
        (6500, 287, 4000, 0, 100, 300, 6200),
        
        # Case 2: Deficit with smoothing enabled (should still work correctly)
        # With smoothing, the household base might be different, but deficit shouldn't zero excess
        (6500, 287, 4000, 5, 50, 0, 6500),
        
        # Case 3: Deficit with battery reserve and margin
        # Production=7000W, consumption=500W, device=600W
        # base_household = 0, margin=200W at 100% SOC
        # excess = max(0, 6800 - 0) = 6800W
        (7000, 500, 600, 0, 100, 200, 6800),
        # fmt: on
    ],
)
async def test_household_deficit_with_smoothing_and_margins(
    hass: HomeAssistant,
    reset_coordinator,
    production_power,
    consumption_power,
    device_power,
    smoothing_window_min,
    battery_soc,
    min_export_margin_w,
    expected_excess,
):
    """Test that deficit handling works correctly with smoothing and min export margin"""

    # Create central config with smoothing and margin
    entry_central = MockConfigEntry(
        domain=DOMAIN,
        title="Central",
        unique_id="centralUniqueId",
        data={
            CONF_NAME: "Configuration",
            CONF_REFRESH_PERIOD_SEC: 60,
            CONF_DEVICE_TYPE: CONF_DEVICE_CENTRAL,
            CONF_POWER_CONSUMPTION_ENTITY_ID: "sensor.fake_power_consumption",
            CONF_POWER_PRODUCTION_ENTITY_ID: "sensor.fake_power_production",
            CONF_SELL_COST_ENTITY_ID: "input_number.fake_sell_cost",
            CONF_BUY_COST_ENTITY_ID: "input_number.fake_buy_cost",
            CONF_SELL_TAX_PERCENT_ENTITY_ID: "input_number.fake_sell_tax_percent",
            CONF_SMOOTH_PRODUCTION: False,
            CONF_SMOOTHING_HOUSEHOLD_WINDOW_MIN: smoothing_window_min,
            CONF_MIN_EXPORT_MARGIN_W: min_export_margin_w,
            CONF_BATTERY_SOC_ENTITY_ID: "sensor.fake_battery_soc",
            CONF_BATTERY_CHARGE_POWER_ENTITY_ID: "sensor.fake_battery_charge_power",
            CONF_RAZ_TIME: "05:00",
        },
    )

    entry_central.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_central.entry_id)

    # Create a device
    if device_power > 0:
        entry_a = MockConfigEntry(
            domain=DOMAIN,
            title="Equipement A",
            unique_id="eqtAUniqueId",
            data={
                CONF_NAME: "Equipement A",
                CONF_DEVICE_TYPE: CONF_DEVICE,
                CONF_ENTITY_ID: "input_boolean.fake_device_a",
                CONF_POWER_MAX: device_power,
                CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
                CONF_DURATION_MIN: 0.3,
                CONF_DURATION_STOP_MIN: 0.1,
                CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
                CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
                CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            },
        )

        device_a = await create_managed_device(hass, entry_a, "equipement_a")
        assert device_a is not None
        device_a.current_power = device_power

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None

    # Set up mock states
    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", consumption_power),
            "sensor.fake_power_production": State("sensor.fake_power_production", production_power),
            "sensor.fake_battery_charge_power": State("sensor.fake_battery_charge_power", 0),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 1),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 1),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "sensor.fake_battery_soc": State("sensor.fake_battery_soc", battery_soc),
        },
        State("unknown.entity_id", "unknown"),
    )

    # Run the update
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        calculated_data = await coordinator._async_update_data()

    # Verify the results
    assert calculated_data is not None

    # Check that excess power is computed correctly despite deficit
    assert calculated_data["available_excess_power"] == expected_excess, f"Expected available_excess_power={expected_excess}, got {calculated_data['available_excess_power']}"

    # Verify household consumption is clamped to >= 0
    assert calculated_data["household_consumption"] >= 0, f"household_consumption should be >= 0, got {calculated_data['household_consumption']}"
