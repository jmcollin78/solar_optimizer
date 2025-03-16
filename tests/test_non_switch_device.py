""" Test a climate device """
from unittest.mock import patch, call
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_climate_device(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing climate device"""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "climate.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "climate/set_hvac_mode/hvac_mode:cool",
            CONF_DEACTIVATION_SERVICE: "climate/set_hvac_mode/hvac_mode:off",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None
    assert device.name == "Equipement A"

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

    assert enable_switch.state == "on"
    # The state of the underlying switch
    assert device_switch.state == "off"

    # try to activate the device directly
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.activate()

        mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "climate",
                        "set_hvac_mode",
                        service_data= {
                            "hvac_mode": "cool"
                        },
                        target= {
                            "entity_id": "climate.fake_device_a",
                        },
                    ),
                ]
            )

    # try to de-activate the device directly
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.deactivate()

        mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "climate",
                        "set_hvac_mode",
                        service_data= {
                            "hvac_mode": "off"
                        },
                        target= {
                            "entity_id": "climate.fake_device_a",
                        },
                    ),
                ]
            )

async def test_humidifier_device(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing humidifier device"""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "humidifier.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "humidifier/turn_on",
            CONF_DEACTIVATION_SERVICE: "humidifier/turn_off",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None
    assert device.name == "Equipement A"

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

    # try to activate the device directly
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.activate()

        mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "humidifier",
                        "turn_on",
                        service_data= {},
                        target= {
                            "entity_id": "humidifier.fake_device_a",
                        },
                    ),
                ]
            )

    # try to de-activate the device directly
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.deactivate()

        mock_service_call.assert_has_calls(
                [
                    call.service_call(
                        "humidifier",
                        "turn_off",
                        service_data= {},
                        target= {
                            "entity_id": "humidifier.fake_device_a",
                        },
                    ),
                ]
            )

