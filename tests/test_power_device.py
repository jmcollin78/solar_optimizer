""" Test a dimmable light device """
from unittest.mock import patch, call
# from datetime import datetime

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_light_power_device(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing light device"""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "light.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "light/turn_on",
            CONF_DEACTIVATION_SERVICE: "light/turn_off",
            CONF_POWER_MIN: 100,
            CONF_POWER_STEP: 4,
            CONF_POWER_ENTITY_ID: "light.fake_device_a",
            CONF_DURATION_POWER_MIN: 0.25,
            CONF_CHANGE_POWER_SERVICE: "light/turn_on/brightness",
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 4,
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
                        "light",
                        "turn_on",
                        service_data= {},
                        target= {
                            "entity_id": "light.fake_device_a",
                        },
                    ),
                ]
            )

    # try to change the power of the device directly to max power
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.change_requested_power(1000)

        mock_service_call.assert_has_calls(
                [
                    call.call(
                        "light",
                        "turn_on",
                        service_data= { 'brightness': 250 },  # 1000 / 4 = 250
                        target= {
                            "entity_id": "light.fake_device_a",
                        },
                    ),
                ]
            )

    # try to change the power of the device directly to 50% power
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.change_requested_power(500)

        mock_service_call.assert_has_calls(
                [
                    call.call(
                        "light",
                        "turn_on",
                        service_data= { 'brightness': 125 },  # 500 / 4 = 125
                        target= {
                            "entity_id": "light.fake_device_a",
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
                        "light",
                        "turn_off",
                        service_data= {},
                        target= {
                            "entity_id": "light.fake_device_a",
                        },
                    ),
                ]
            )


async def test_fan_power_device(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing light device"""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "fan.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0.3,
            CONF_DURATION_STOP_MIN: 0.1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "fan/turn_on",
            CONF_DEACTIVATION_SERVICE: "fan/turn_off",
            CONF_POWER_MIN: 100,
            CONF_POWER_STEP: 10,
            CONF_POWER_ENTITY_ID: "fan.fake_device_a",
            CONF_DURATION_POWER_MIN: 0.25,
            CONF_CHANGE_POWER_SERVICE: "fan/turn_on/percentage",
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 10,
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
                        "fan",
                        "turn_on",
                        service_data= {},
                        target= {
                            "entity_id": "fan.fake_device_a",
                        },
                    ),
                ]
            )

    # try to change the power of the device directly to max power
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.change_requested_power(1000)

        mock_service_call.assert_has_calls(
                [
                    call.call(
                        "fan",
                        "turn_on",
                        service_data= { 'percentage': 100 },  # 1000 / 10 = 100%
                        target= {
                            "entity_id": "fan.fake_device_a",
                        },
                    ),
                ]
            )

    # try to change the power of the device directly to 50% power
    # fmt: off
    with patch("homeassistant.core.ServiceRegistry.async_call") as mock_service_call:
    # fmt: on
        await device.change_requested_power(500)

        mock_service_call.assert_has_calls(
                [
                    call.call(
                        "fan",
                        "turn_on",
                        service_data= { 'percentage': 50 },  # 500 / 10 = 50%
                        target= {
                            "entity_id": "fan.fake_device_a",
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
                        "fan",
                        "turn_off",
                        service_data= {},
                        target= {
                            "entity_id": "fan.fake_device_a",
                        },
                    ),
                ]
            )
