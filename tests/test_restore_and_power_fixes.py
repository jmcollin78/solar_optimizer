"""Unit tests for:
- on_time restore race at HA restart (sensor.py)
- real power_entity_id reading regardless of can_change_power (managed_device.py)
- best_objective is no longer mislabeled as a monetary/€ value (sensor.py)
- current_power of an on/off device already on at startup (managed_device.py)
"""
# pylint: disable=protected-access

from unittest.mock import patch, AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import mock_restore_cache, mock_restore_cache_with_extra_data

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.core import State

from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


DEVICE_A_DATA = {
    CONF_NAME: "Equipement A",
    CONF_DEVICE_TYPE: CONF_DEVICE,
    CONF_ENTITY_ID: "input_boolean.fake_device_a",
    CONF_POWER_MAX: 1000,
    CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
    CONF_DURATION_MIN: 0.3,
    CONF_DURATION_STOP_MIN: 0.1,
    CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
    CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
    CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
    CONF_BATTERY_SOC_THRESHOLD: 0,
    CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
}


async def test_on_time_restore_syncs_device_immediately(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """The device's internal on_time_sec must be synced right away from the restored
    sensor value, not only at the first state change or 1-minute tick: on restart, a
    device that already reached its daily max should stay unusable immediately, not
    for up to 60s."""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data=DEVICE_A_DATA,
    )

    restored_state = State(
        "sensor.on_time_today_solar_optimizer_equipement_a",
        "590",
        attributes={},
    )

    with patch(
        "custom_components.solar_optimizer.sensor.TodayOnTimeSensor.async_get_last_state",
        new_callable=AsyncMock,
        return_value=restored_state,
    ):
        device = await create_managed_device(hass, entry_a, "equipement_a")
        assert device is not None
        await create_test_input_boolean(hass, device.entity_id, "fake underlying A")
        await hass.async_block_till_done()

    # max_on_time_per_day is 10 minutes = 600s ; restored value is 590s.
    # Without the fix, device._on_time_sec would still be 0 right after restore.
    assert device._on_time_sec == 590

    on_time_sensor = search_entity(
        hass, "sensor.on_time_today_solar_optimizer_equipement_a", SENSOR_DOMAIN
    )
    assert on_time_sensor.state == 590


async def test_power_entity_id_used_when_cannot_change_power(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """A fixed on/off device (can_change_power=False) with a power_entity_id configured
    for monitoring should report the real measured power, not the configured power_max
    (e.g. 560W measured vs 585W reserved for planning)."""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Pool pump",
        unique_id="poolPumpUniqueId",
        data={
            **DEVICE_A_DATA,
            CONF_NAME: "Pool pump",
            CONF_POWER_MAX: 585,
            CONF_POWER_ENTITY_ID: "input_number.fake_pool_pump_power",
        },
    )

    device = await create_managed_device(hass, entry_a, "pool_pump")
    assert device is not None
    assert device.can_change_power is False

    await create_test_input_boolean(hass, device.entity_id, "fake pool pump switch")
    fake_switch = search_entity(hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN)
    fake_power = await create_test_input_number(
        hass, "input_number.fake_pool_pump_power", "fake pool pump power"
    )

    await fake_switch.async_turn_on()
    await hass.services.async_call("input_number", "set_value", {"entity_id": fake_power.entity_id, "value": 560}, blocking=True)
    await hass.async_block_till_done()

    device.set_current_power_with_device_state()
    assert device.current_power == 560

    # If the power monitoring entity can't be found, fall back to the planning value
    # (power_max). Point the device at a nonexistent entity rather than patching
    # hass.states.get globally, since is_active's own template also reads states.
    device._power_entity_id = "input_number.does_not_exist"
    device.set_current_power_with_device_state()
    assert device.current_power == 585


async def test_power_entity_id_fallback_when_not_configured(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Without a power_entity_id configured, a fixed device keeps using power_max as
    its current_power estimate (unchanged behavior)."""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data=DEVICE_A_DATA,
    )

    device = await create_managed_device(hass, entry_a, "equipement_a")
    assert device is not None
    assert device.can_change_power is False

    await create_test_input_boolean(hass, device.entity_id, "fake underlying A")
    fake_switch = search_entity(hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN)
    await fake_switch.async_turn_on()
    await hass.async_block_till_done()

    device.set_current_power_with_device_state()
    assert device.current_power == 1000


async def test_best_objective_is_not_monetary(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """best_objective is a dimensionless optimizer score, it must not be tagged as a
    monetary value in euros regardless of the user's currency."""

    component = hass.data["entity_components"].get(SENSOR_DOMAIN)
    best_objective_sensor = None
    for entity in component.entities:
        if entity.unique_id == "solar_optimizer_best_objective":
            best_objective_sensor = entity
            break
    assert best_objective_sensor is not None
    assert best_objective_sensor.device_class is None
    assert best_objective_sensor.native_unit_of_measurement is None
    assert best_objective_sensor.device_class != SensorDeviceClass.MONETARY


async def test_on_off_device_already_on_at_startup_reports_power_max(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """An on/off device already on when SO starts must report power_max as current
    power, not power_min (-1): the init ternary was inverted, so the card bar showed
    0 until the first coordinator refresh."""

    hass.states.async_set("input_boolean.fake_device_a", "on")

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data=DEVICE_A_DATA,
    )
    device = await create_managed_device(hass, entry_a, "equipement_a")

    assert device.can_change_power is False
    assert device.is_active is True
    assert device.current_power == 1000


@pytest.mark.parametrize(
    "state, unit, extra_data",
    [
        # 1h45 shown in hours (the case of the issue): stored state is 1.75
        ("1.75", "h", None),
        ("105", "min", None),
        ("6300", "s", None),
        # after the update, the native value in seconds is stored by RestoreSensor
        ("1.75", "h", {"native_value": 6300, "native_unit_of_measurement": "s"}),
    ],
)
async def test_on_time_restored_whatever_the_display_unit(hass: HomeAssistant, init_solar_optimizer_central_config, state, unit, extra_data):
    """The on_time is restored in seconds even when the sensor is displayed in minutes
    or hours (it used to read 1.75 h as 1.75 s and lose the daily on time at restart)"""
    stored = State("sensor.on_time_today_solar_optimizer_equipement_a", state, {"unit_of_measurement": unit})
    if extra_data:
        mock_restore_cache_with_extra_data(hass, ((stored, extra_data),))
    else:
        mock_restore_cache(hass, (stored,))

    entry_a = MockConfigEntry(domain=DOMAIN, title="Equipement A", unique_id="eqtAUniqueId", data=DEVICE_A_DATA)
    device = await create_managed_device(hass, entry_a, "equipement_a")
    await hass.async_block_till_done()

    on_time_sensor = search_entity(hass, "sensor.on_time_today_solar_optimizer_equipement_a", SENSOR_DOMAIN)
    assert on_time_sensor.native_value == 6300
    assert device._on_time_sec == 6300
    # what is stored for the next restart is in seconds, whatever the display unit
    assert on_time_sensor.extra_restore_state_data.as_dict() == {"native_value": 6300, "native_unit_of_measurement": "s"}
