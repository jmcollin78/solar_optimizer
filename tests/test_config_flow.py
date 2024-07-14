import itertools
import pytest
import voluptuous

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData

from custom_components.solar_optimizer import config_flow


async def test_empty_config(hass: HomeAssistant):
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert _result["step_id"] == "user"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] is None

    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            _result["flow_id"], user_input={}
        )


@pytest.mark.parametrize(
    "power_consumption,power_production,sell_cost,buy_cost",
    itertools.product(
        ["sensor.power_consumption", "input_number.power_consumption"],
        ["sensor.power_production", "input_number.power_production"],
        ["sensor.sell_cost", "input_number.sell_cost"],
        ["sensor.buy_cost", "input_number.buy_cost"],
    ),
)
async def test_config_inputs(
    hass: HomeAssistant,
    init_solar_optimizer_with_2_devices_power_not_power,
    init_solar_optimizer_entry,
    power_consumption,
    power_production,
    sell_cost,
    buy_cost,
):
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    assert _result["step_id"] == "user"
    assert _result["type"] == FlowResultType.FORM
    assert _result["errors"] is None

    user_input = {
            "refresh_period_sec": 300,
            "power_consumption_entity_id": power_consumption,
            "power_production_entity_id": power_production,
            "sell_cost_entity_id": sell_cost,
            "buy_cost_entity_id": buy_cost,
            "sell_tax_percent_entity_id": "input_number.tax_percent",
    }

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

    assert data["smooth_production"]

    assert result["title"] == "SolarOptimizer"
