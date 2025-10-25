""" Test the battery recharge reserve before/after smoothing feature """

from unittest.mock import patch
import pytest

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator


@pytest.mark.parametrize(
    "production_power, battery_reserve_w, battery_soc, reserve_before_smoothing, smoothing_window_min, expected_production_after_reserve, expected_production_after_smoothing",
    [
        # fmt: off
        # Case 1: Reserve AFTER smoothing (default behavior) - no smoothing
        (2000, 500, 50, False, 0, 2000, 1500),  # Reserve subtracted after (no smoothing)
        
        # Case 2: Reserve BEFORE smoothing - no smoothing (should be same as after)
        (2000, 500, 50, True, 0, 1500, 1500),  # Reserve subtracted before (no smoothing)
        
        # Case 3: Reserve AFTER smoothing with smoothing enabled
        (2000, 500, 50, False, 5, 2000, 1500),  # Reserve subtracted after smoothing
        
        # Case 4: Reserve BEFORE smoothing with smoothing enabled (new feature)
        (2000, 500, 50, True, 5, 1500, 1500),  # Reserve subtracted before smoothing
        
        # Case 5: Battery full (SOC 100) - no reserve should be applied regardless of setting
        (2000, 500, 100, False, 0, 2000, 2000),  # No reserve when battery full
        (2000, 500, 100, True, 0, 2000, 2000),  # No reserve when battery full
        
        # Case 6: No battery reserve configured
        (2000, 0, 50, False, 0, 2000, 2000),  # No reserve configured
        (2000, 0, 50, True, 0, 2000, 2000),  # No reserve configured
        
        # Case 7: Reserve larger than production
        (500, 1000, 50, False, 0, 500, 0),  # Reserve capped at production (after)
        (500, 1000, 50, True, 0, 0, 0),  # Reserve capped at production (before)
        # fmt: on
    ],
)
async def test_battery_reserve_before_after_smoothing(
    hass: HomeAssistant,
    reset_coordinator,
    production_power,
    battery_reserve_w,
    battery_soc,
    reserve_before_smoothing,
    smoothing_window_min,
    expected_production_after_reserve,
    expected_production_after_smoothing,
):
    """Test battery reserve applied before or after smoothing"""
    
    # Create central config with battery reserve settings
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
            CONF_SMOOTH_PRODUCTION: smoothing_window_min > 0,
            CONF_SMOOTHING_PRODUCTION_WINDOW_MIN: smoothing_window_min,
            CONF_BATTERY_SOC_ENTITY_ID: "sensor.fake_battery_soc",
            CONF_BATTERY_CHARGE_POWER_ENTITY_ID: "sensor.fake_battery_charge_power",
            CONF_BATTERY_RECHARGE_RESERVE_W: battery_reserve_w,
            CONF_BATTERY_RECHARGE_RESERVE_BEFORE_SMOOTHING: reserve_before_smoothing,
            CONF_RAZ_TIME: "05:00",
        },
    )
    
    entry_central.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_central.entry_id)
    
    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    
    # Set up mock states
    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State(
                "sensor.fake_power_consumption", 100
            ),
            "sensor.fake_power_production": State(
                "sensor.fake_power_production", production_power
            ),
            "sensor.fake_battery_charge_power": State(
                "sensor.fake_battery_charge_power", 0
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
    
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
        calculated_data = await coordinator._async_update_data()
        
        assert calculated_data is not None
        
        # Check that raw production is stored correctly
        assert calculated_data["power_production_brut"] == production_power
        
        # Check the final production after all processing
        assert calculated_data["power_production"] == expected_production_after_smoothing, \
            f"Expected production {expected_production_after_smoothing}, got {calculated_data['power_production']}"
        
        # Check that the reserved amount is calculated correctly
        if battery_reserve_w > 0 and battery_soc < 100:
            expected_reserved = min(battery_reserve_w, expected_production_after_reserve)
            assert calculated_data["power_production_reserved"] == expected_reserved, \
                f"Expected reserved {expected_reserved}, got {calculated_data['power_production_reserved']}"
        else:
            assert calculated_data["power_production_reserved"] == 0


@pytest.mark.parametrize(
    "production_values, battery_reserve_w, battery_soc, reserve_before_smoothing, expected_final_production",
    [
        # fmt: off
        # Test smoothing with reserve BEFORE smoothing
        # Production varies: 1000, 2000, 3000 -> Average ~2000, then subtract reserve 500 -> ~1500
        ([1000, 2000, 3000], 500, 50, True, 1500),  # Reserve before, smoothed to ~1500
        
        # Test smoothing with reserve AFTER smoothing
        # Production varies: 1000, 2000, 3000 -> Average ~2000, then subtract reserve 500 -> ~1500
        ([1000, 2000, 3000], 500, 50, False, 1500),  # Reserve after, result ~1500
        
        # Test that reserve before smoothing creates smoother transitions
        # When reserve is applied before smoothing, the reserve itself gets smoothed
        ([2000, 2000, 2000], 500, 50, True, 1500),  # Stable production, reserve before
        ([2000, 2000, 2000], 500, 50, False, 1500),  # Stable production, reserve after
        # fmt: on
    ],
)
async def test_battery_reserve_with_smoothing_window(
    hass: HomeAssistant,
    reset_coordinator,
    production_values,
    battery_reserve_w,
    battery_soc,
    reserve_before_smoothing,
    expected_final_production,
):
    """Test battery reserve with actual smoothing window over multiple updates"""
    
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
            CONF_SMOOTH_PRODUCTION: True,
            CONF_SMOOTHING_PRODUCTION_WINDOW_MIN: 3,
            CONF_BATTERY_SOC_ENTITY_ID: "sensor.fake_battery_soc",
            CONF_BATTERY_CHARGE_POWER_ENTITY_ID: "sensor.fake_battery_charge_power",
            CONF_BATTERY_RECHARGE_RESERVE_W: battery_reserve_w,
            CONF_BATTERY_RECHARGE_RESERVE_BEFORE_SMOOTHING: reserve_before_smoothing,
            CONF_RAZ_TIME: "05:00",
        },
    )
    
    entry_central.add_to_hass(hass)
    await hass.config_entries.async_setup(entry_central.entry_id)
    
    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    
    # Run multiple updates to fill the smoothing window
    for production_value in production_values:
        side_effects = SideEffects(
            {
                "sensor.fake_power_consumption": State(
                    "sensor.fake_power_consumption", 100
                ),
                "sensor.fake_power_production": State(
                    "sensor.fake_power_production", production_value
                ),
                "sensor.fake_battery_charge_power": State(
                    "sensor.fake_battery_charge_power", 0
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
        
        with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()):
            calculated_data = await coordinator._async_update_data()
    
    # After the window is full, check the final production
    assert calculated_data is not None
    assert calculated_data["power_production"] == expected_final_production, \
        f"Expected final production {expected_final_production}, got {calculated_data['power_production']}"
