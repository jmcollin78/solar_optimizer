""" Nominal Unit test module"""

# pylint: disable=protected-access

from datetime import datetime, timedelta
from unittest.mock import PropertyMock, patch


from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.helpers.restore_state import RestoreEntity


from custom_components.solar_optimizer.const import get_tz
from custom_components.solar_optimizer.sensor import TodayOnTimeSensor
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def _create_max_test_device(
    hass,
    restored_seconds,
    now,
    max_on_time=120,
    last_datetime_on=None,
    active=False,
):
    """Create a device with a supplied restored daily duration and timestamp."""
    entity_id = "sensor.on_time_today_solar_optimizer_restored_max_device"
    restored_state = State(
        entity_id,
        str(restored_seconds),
        {"last_datetime_on": last_datetime_on} if last_datetime_on else {},
    )
    original_get_last_state = RestoreEntity.async_get_last_state

    async def get_last_state(entity):
        if isinstance(entity, TodayOnTimeSensor):
            return restored_state
        return await original_get_last_state(entity)

    fake_switch = await create_test_input_boolean(hass, "input_boolean.restored_max_device", "restored max device")
    assert fake_switch is not None
    if active:
        await fake_switch.async_turn_on()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Restored max device",
        unique_id="restoredMaxDevice",
        data={
            CONF_NAME: "Restored max device",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.restored_max_device",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0,
            CONF_DURATION_STOP_MIN: 0,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 0,
            CONF_MAX_ON_TIME_PER_DAY_MIN: max_on_time,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 0,
        },
    )

    with (
        patch.object(RestoreEntity, "async_get_last_state", new=get_last_state),
        patch.object(ManagedDevice, "now", new_callable=PropertyMock, return_value=now),
    ):
        device = await create_managed_device(hass, entry, "restored_max_device")
        await hass.async_block_till_done()
    device._set_now(now)

    sensor = search_entity(hass, entity_id, SENSOR_DOMAIN)
    assert sensor is not None
    return device, sensor


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
    # Freeze now before turning on: the state listener may run during async_turn_on
    now = device.now
    device._set_now(now)
    await fake_input_bool.async_turn_on()

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
        await hass.services.async_call("input_number", "set_value", {"entity_id": fake_power.entity_id, "value": value}, blocking=True)
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


@pytest.mark.parametrize(
    ("restored_seconds", "expected_usable"),
    [(7140, True), (7200, False), (7800, False)],
)
async def test_restored_daily_maximum_is_used_by_real_annealing(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    restored_seconds,
    expected_usable,
):
    """The inclusive daily maximum reaches both real usability readers."""
    now = datetime(2024, 11, 10, 2, 3, tzinfo=get_tz(hass))
    device, sensor = await _create_max_test_device(hass, restored_seconds, now)
    coordinator = SolarOptimizerCoordinator.get_coordinator()

    assert sensor.native_value == restored_seconds
    assert device._on_time_sec == restored_seconds
    assert device.check_usable(False) is expected_usable
    assert device.is_usable is expected_usable

    coordinator._algo.recuit_simule(
        coordinator.devices,
        power_consumption=0,
        solar_power_production=0,
        sell_cost=1,
        buy_cost=1,
        sell_tax_percent=0,
        battery_soc=50,
        priority_weight=0,
    )

    assert coordinator._algo._equipements[0]["is_usable"] is expected_usable


async def test_active_restored_on_time_counts_once_and_resets(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Active restoration preserves the timestamp, counts once, and resets."""
    restored_at = datetime(2024, 11, 10, 1, 0, tzinfo=get_tz(hass))
    device, sensor = await _create_max_test_device(
        hass,
        600,
        restored_at,
        last_datetime_on=restored_at.isoformat(),
        active=True,
    )

    assert sensor.native_value == 600
    assert device._on_time_sec == 600
    assert sensor.last_datetime_on == restored_at

    device._set_now(restored_at + timedelta(seconds=60))
    await sensor._on_update_on_time()
    assert sensor.native_value == 660
    assert device._on_time_sec == 660

    await sensor._on_update_on_time()
    assert sensor.native_value == 660
    assert device._on_time_sec == 660

    reset_at = restored_at + timedelta(minutes=2)
    device._set_now(reset_at)
    await sensor._on_midnight()
    assert sensor.native_value == 0
    assert device._on_time_sec == 0
    assert sensor.last_datetime_on == reset_at

    device._set_now(reset_at + timedelta(seconds=60))
    await sensor._on_update_on_time()
    assert sensor.native_value == 60
    assert device._on_time_sec == 60
