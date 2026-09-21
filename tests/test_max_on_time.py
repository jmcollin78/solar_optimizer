""" Nominal Unit test module"""

# pylint: disable=protected-access

# from unittest.mock import patch
from datetime import timedelta


from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN


from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_max_on_time_calculation(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Testing on_time calculation change"""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data={
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
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None
    assert device.name == "Equipement A"

    assert device.is_enabled is True
    assert device.max_on_time_per_day_sec == 10 * 60

    # Creates the fake input_boolean
    await create_test_input_boolean(hass, device.entity_id, "fake underlying A")

    fake_input_bool = search_entity(
        hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN
    )
    assert fake_input_bool is not None

    #
    # Get the swotch and on_time_sensor
    #
    device_switch = search_entity(
        hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN
    )

    device_on_time_sensor = search_entity(
        hass, "sensor.on_time_today_solar_optimizer_equipement_a", SENSOR_DOMAIN
    )
    assert device_switch is not None
    assert device.is_active is False
    # The state of the underlying switch
    assert device_switch.state == "off"
    # The enable state should be True
    assert device_switch.get_attr_extra_state_attributes.get("is_active") is False

    #
    # 1. check initial extra_attributes and state
    #
    assert (
        device_switch.get_attr_extra_state_attributes.get("device_name")
        == "Equipement A"
    )
    assert (
        device_on_time_sensor.get_attr_extra_state_attributes.get("last_datetime_on")
        is None
    )
    assert (
        device_on_time_sensor.get_attr_extra_state_attributes.get(
            "max_on_time_per_day_sec"
        )
        == 60 * 10
    )
    assert (
        device_on_time_sensor.get_attr_extra_state_attributes.get(
            "max_on_time_per_day_min"
        )
        == 10
    )
    assert (
        device_on_time_sensor.get_attr_extra_state_attributes.get("on_time_hms")
        == "0:00"
    )
    assert (
        device_on_time_sensor.get_attr_extra_state_attributes.get("max_on_time_hms")
        == "10:00"
    )

    # The on_time should be 0
    assert device_on_time_sensor.state == 0
    assert device_on_time_sensor.last_datetime_on is None

    #
    # 2. Activate the underlying switch
    #
    await fake_input_bool.async_turn_on()
    now = device.now
    device._set_now(now)

    await hass.async_block_till_done()

    #
    # 3. check We have start counting on_time
    #
    assert device_on_time_sensor.last_datetime_on is not None
    assert device_on_time_sensor.last_datetime_on == now
    assert device_on_time_sensor.state == 0

    #
    # 4. de-activate the underlying switch
    # Change now
    now = now + timedelta(seconds=13)
    device._set_now(now)

    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()

    #
    # 5. we should have increment counter and stop counting
    #
    assert device_on_time_sensor.last_datetime_on is None
    assert device_on_time_sensor.state == 13

    #
    # 6. reactivate and call on_update_on_time
    #
    # Change now
    now = now + timedelta(minutes=1)
    device._set_now(now)

    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()
    assert device_on_time_sensor.last_datetime_on == now
    assert device_on_time_sensor.state == 13

    #
    # 7. Simulate the call to the periodic _on_update_on_time
    #
    # Change now
    now = now + timedelta(seconds=55)
    device._set_now(now)

    await device_on_time_sensor._on_update_on_time()
    await hass.async_block_till_done()

    assert device_on_time_sensor.last_datetime_on == now
    assert device_on_time_sensor.state == 68  # 55+13

    #
    # 8. Call _at_midnight to reset the counter
    # Change now
    now = now + timedelta(hours=1)
    device._set_now(now)

    await device_on_time_sensor._on_midnight()
    await hass.async_block_till_done()

    assert device_on_time_sensor.last_datetime_on == now
    assert device_on_time_sensor.state == 0

    #
    # 9. Stop the switch -> it should count from last reset dateetime now
    #
    now = now + timedelta(minutes=12)
    device._set_now(now)

    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()

    assert device_on_time_sensor.last_datetime_on is None
    assert device_on_time_sensor.state == 12 * 60


async def test_on_time_with_delayed_active_template(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """on_time must count real on time when check_active_template relies on an
    entity (a power sensor) which is updated a few seconds after the underlying
    switch. Before the fix, is_active was evaluated only at the underlying state
    change event, so on/off transitions were inverted and the sensor counted the
    off time instead (e.g. 06:00 -> 10:30 = 4h30 added when the switch turns on)."""

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Water heater",
        unique_id="waterHeaterUniqueId",
        data={
            CONF_NAME: "Water heater",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_water_heater",
            CONF_POWER_MAX: 2000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_CHECK_ACTIVE_TEMPLATE: "{{ states('input_number.fake_water_heater_power')|float(0) > 100 }}",
            CONF_DURATION_MIN: 10,
            CONF_DURATION_STOP_MIN: 10,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 0,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 180,
        },
    )

    device = await create_managed_device(hass, entry_a, "water_heater")
    assert device is not None

    fake_switch = await create_test_input_boolean(hass, device.entity_id, "fake water heater")
    fake_power = await create_test_input_number(
        hass, "input_number.fake_water_heater_power", "fake water heater power"
    )
    assert fake_switch is not None
    assert fake_power is not None

    on_time_sensor = search_entity(
        hass, "sensor.on_time_today_solar_optimizer_water_heater", SENSOR_DOMAIN
    )
    assert on_time_sensor is not None
    assert on_time_sensor.state == 0

    async def set_power(value: float):
        await fake_power.async_set_value(value)
        await hass.async_block_till_done()

    async def tick(at):
        device._set_now(at)
        await on_time_sensor._on_update_on_time()
        await hass.async_block_till_done()

    now = device.now

    # 1. Switch on: the power sensor is not updated yet -> not active, nothing counted
    device._set_now(now)
    await fake_switch.async_turn_on()
    await hass.async_block_till_done()
    assert device.is_active is False
    assert on_time_sensor.last_datetime_on is None
    assert on_time_sensor.state == 0

    # 2. The power sensor catches up 5s later, the next periodic tick starts counting
    await set_power(2000)
    now = now + timedelta(seconds=30)
    await tick(now)
    assert on_time_sensor.last_datetime_on == now
    assert on_time_sensor.state == 0

    # 3. The device runs 10 minutes
    now = now + timedelta(minutes=10)
    await tick(now)
    assert on_time_sensor.state == 600

    # 4. Switch off: the power sensor still reads 2000W at the event
    now = now + timedelta(seconds=20)
    device._set_now(now)
    await fake_switch.async_turn_off()
    await hass.async_block_till_done()
    assert on_time_sensor.state == 620

    # 5. The power sensor drops, the next tick stops counting
    await set_power(0)
    now = now + timedelta(seconds=40)
    await tick(now)
    assert on_time_sensor.last_datetime_on is None
    assert on_time_sensor.state == 660

    # 6. Daily reset, then the device stays off for 4 hours
    await on_time_sensor._on_midnight()
    await hass.async_block_till_done()
    assert on_time_sensor.state == 0
    assert on_time_sensor.last_datetime_on is None

    for _ in range(4 * 60):
        now = now + timedelta(minutes=1)
        await tick(now)
    assert on_time_sensor.state == 0

    # 7. Switch on again, power still 0 at the event: the off period must not be counted
    now = now + timedelta(seconds=10)
    device._set_now(now)
    await fake_switch.async_turn_on()
    await hass.async_block_till_done()
    assert on_time_sensor.state == 0
    assert device.check_usable() is True
