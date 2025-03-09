""" Testing the ConfigFlow """

# pylint: disable=unused-argument, wildcard-import, unused-wildcard-import

import itertools
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.solar_optimizer import config_flow

from custom_components.solar_optimizer.const import *
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator


async def test_empty_config(hass: HomeAssistant):
    """Test an empty config. This should not work"""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert _result["step_id"] == "device_central"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] == {}

    with pytest.raises(InvalidData) as err:
        await hass.config_entries.flow.async_configure(
            _result["flow_id"], user_input={}
        )

    assert err.typename == "InvalidData"
    assert err.value.error_message == "required key not provided"


@pytest.mark.parametrize(
    "power_consumption,power_production,sell_cost,buy_cost,raz_time,battery_soc",
    [
        (
            "sensor.power_consumption",
            "sensor.power_production",
            "input_number.sell_cost",
            "input_number.buy_cost",
            "00:00",
            None,
        ),
        (
            "input_number.power_consumption",
            "input_number.power_production",
            "input_number.sell_cost",
            "input_number.buy_cost",
            "04:00",
            None,
        ),
        (
            "sensor.power_consumption",
            "sensor.power_production",
            "input_number.sell_cost",
            "input_number.buy_cost",
            "00:00",
            "sensor.battery_soc",
        ),
        (
            "input_number.power_consumption",
            "input_number.power_production",
            "input_number.sell_cost",
            "input_number.buy_cost",
            "04:00",
            "input_number.battery_soc",
        ),
    ],
)
async def test_central_config_inputs(
    hass: HomeAssistant,
    skip_hass_states_get,
    reset_coordinator,
    power_consumption,
    power_production,
    sell_cost,
    buy_cost,
    raz_time,
    battery_soc,
):
    """Test a combinaison of config_flow without battery configuration"""

    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert _result["step_id"] == "device_central"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] == {}

    user_input = {
        "refresh_period_sec": 300,
        "power_consumption_entity_id": power_consumption,
        "power_production_entity_id": power_production,
        "sell_cost_entity_id": sell_cost,
        "buy_cost_entity_id": buy_cost,
        "sell_tax_percent_entity_id": "input_number.tax_percent",
        "raz_time": raz_time,
    }

    if battery_soc:
        user_input["battery_soc_entity_id"] = battery_soc

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"],
        user_input
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    data = result.get("data")
    assert data is not None

    for key, value in user_input.items():
        assert data.get(key) == value

    if battery_soc:
        assert data["battery_soc_entity_id"] == battery_soc

    assert data["smooth_production"]

    assert result["title"] == "Configuration"


async def test_default_values_central_config(
    hass: HomeAssistant, skip_hass_states_get, reset_coordinator
):
    """Test a combinaison of config_flow with battery configuration"""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert _result["step_id"] == "device_central"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] == {}

    user_input = {
        # "refresh_period_sec": 300,
        # "raz_time": "04:00",
        # "smooth_production": True,
        # battery_soc_entity_id: None,
        "power_consumption_entity_id": "input_number.power_consumption",
        "power_production_entity_id": "input_number.power_production",
        "sell_cost_entity_id": "input_number.sell_cost",
        "buy_cost_entity_id": "input_number.buy_cost",
        "sell_tax_percent_entity_id": "input_number.tax_percent",
    }

    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.CREATE_ENTRY
    data = result.get("data")
    assert data is not None

    for key, value in user_input.items():
        assert data.get(key) == value

    assert data.get("refresh_period_sec") == 300
    assert data.get("raz_time") == DEFAULT_RAZ_TIME

    assert data["smooth_production"]
    assert data.get("battery_soc_entity_id") is None

    assert result["title"] == "Configuration"


async def test_wrong_raz_time(
    hass: HomeAssistant, skip_hass_states_get, reset_coordinator
):
    """Test an empty config. This should not work"""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert _result["step_id"] == "device_central"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] == {}

    user_input = {
        # "refresh_period_sec": 300,
        "raz_time": "04h00",  # Not valid !
        # "smooth_production": True,
        # battery_soc_entity_id: None,
        "power_consumption_entity_id": "input_number.power_consumption",
        "power_production_entity_id": "input_number.power_production",
        "sell_cost_entity_id": "input_number.sell_cost",
        "buy_cost_entity_id": "input_number.buy_cost",
        "sell_tax_percent_entity_id": "input_number.tax_percent",
    }

    _result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input=user_input
    )

    assert _result["step_id"] == "device_central"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] == {"raz_time": "format_time_invalid"}
