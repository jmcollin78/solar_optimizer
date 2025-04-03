""" Test all templating features """
from unittest.mock import patch, call

from homeassistant.helpers.template import Template
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
import pytest

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

@pytest.mark.parametrize(
    "input_value, expected_output, is_template, expect_exception",
    [
        ("{{ 1 }}", 1, True, False),
        ("{% set a = 1 %}{{ a }}", 1, True, False),
        ("1", 1, False, False),
        ("1.0", 1.0, False, False),
        ("True", True, False, False),
        ("False", False, False, False),
        ("None", None, False, False),
        ("test", "test", False, True),
        (1, 1, False, False),
        (1.0, 1.0, False, False),
        (True, True, False, False),
        (False, False, False, False),
        (None, None, False, False),
    ],
)
async def test_templating_conversion(hass: HomeAssistant, input_value, expected_output, is_template, expect_exception):
    """Test the convert_to_template_or_value function"""
    if expect_exception:
        with pytest.raises(ValueError):
            convert_to_template_or_value(hass, input_value)
    else:
        value = convert_to_template_or_value(hass, input_value)
        assert isinstance(value, Template) == is_template
        assert get_template_or_value(hass, value) == expected_output

@pytest.mark.parametrize(
    "power_max, battery_soc_threshold, max_on_time_per_day_min, min_on_time_per_day_min, power_max_value, battery_soc_threshold_value, max_on_time_per_day_min_value, min_on_time_per_day_min_value",
    [
        (1000, 30, 10, 5, 1000, 30, 10, 5),
        ("{{ 1000 }}", "{{ 30 }}", "{{ 10 }}", "{{ 5 }}", 1000, 30, 10, 5),
        ("{{ 1000 }}", "{{ 30 }}", 10, "{{ 5 }}", 1000, 30, 10, 5),
        (1000, "{{ 30 }}", "{{ 10 }}", 5, 1000, 30, 10, 5),
        ("{% if 1 > 2 %}{{ 10 }}{% else %}{{ 0 }}{% endif %}", "{{ '30' | float(0) }}", "{{ 'coucou' | float(10) }}", "{{ 5 }}", 0, 30, 10, 5),
    ],
)
async def tests_device_with_template(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    power_max,
    battery_soc_threshold,
    max_on_time_per_day_min,
    min_on_time_per_day_min,
    power_max_value,
    battery_soc_threshold_value,
    max_on_time_per_day_min_value,
    min_on_time_per_day_min_value,
):
    """" Test the creation of a device with template """
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: power_max,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: battery_soc_threshold,
            CONF_MAX_ON_TIME_PER_DAY_MIN: max_on_time_per_day_min,
            CONF_MIN_ON_TIME_PER_DAY_MIN: min_on_time_per_day_min,
            CONF_OFFPEAK_TIME: "06:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )

    assert device is not None
    assert device.name == "Equipement A"
    assert device.power_max == power_max_value
    assert device.battery_soc_threshold == battery_soc_threshold_value
    assert device.max_on_time_per_day_sec == max_on_time_per_day_min_value * 60
    assert device.min_on_time_per_day_sec == min_on_time_per_day_min_value * 60