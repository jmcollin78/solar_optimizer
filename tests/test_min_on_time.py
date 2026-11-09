""" Nominal Unit test module"""

# pylint: disable=protected-access

from unittest.mock import AsyncMock, patch, PropertyMock
from datetime import datetime, timedelta, time
from types import SimpleNamespace


from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.solar_optimizer.const import get_tz
from custom_components.solar_optimizer.sensor import TodayOnTimeSensor
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def _create_restored_device(
    hass,
    monkeypatch,
    old_state,
    now,
    min_on_time=120,
    max_on_time=600,
    active=False,
):
    """Create a device whose duration sensor receives a supplied restored state."""
    entity_id = "sensor.on_time_today_solar_optimizer_restored_device"
    events = []
    original_get_last_state = RestoreEntity.async_get_last_state
    original_set_on_time = ManagedDevice.set_on_time
    original_update_custom_attributes = TodayOnTimeSensor.update_custom_attributes
    original_write_ha_state = TodayOnTimeSensor.async_write_ha_state

    async def get_last_state(entity):
        if isinstance(entity, TodayOnTimeSensor):
            return old_state
        return await original_get_last_state(entity)

    def set_on_time(device, value):
        original_set_on_time(device, value)
        if device.name == "Restored device":
            events.append(("setter", value, device._on_time_sec))

    def update_custom_attributes(entity):
        original_update_custom_attributes(entity)
        if entity._device.name == "Restored device":
            events.append(
                (
                    "attributes",
                    entity._attr_native_value,
                    entity._device._on_time_sec,
                    entity._attr_extra_state_attributes["should_be_forced_offpeak"],
                    entity.last_datetime_on,
                )
            )

    def write_ha_state(entity):
        original_write_ha_state(entity)
        if isinstance(entity, TodayOnTimeSensor) and hasattr(entity, "_attr_extra_state_attributes"):
            events.append(
                (
                    "publish",
                    entity._attr_native_value,
                    entity._device._on_time_sec,
                    dict(entity._attr_extra_state_attributes),
                )
            )

    monkeypatch.setattr(RestoreEntity, "async_get_last_state", get_last_state)
    monkeypatch.setattr(ManagedDevice, "set_on_time", set_on_time)
    monkeypatch.setattr(TodayOnTimeSensor, "update_custom_attributes", update_custom_attributes)
    monkeypatch.setattr(TodayOnTimeSensor, "async_write_ha_state", write_ha_state)

    fake_switch = await create_test_input_boolean(hass, "input_boolean.restored_device", "restored device")
    if active:
        await fake_switch.async_turn_on()

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Restored device",
        unique_id="restoredDevice",
        data={
            CONF_NAME: "Restored device",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.restored_device",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0,
            CONF_DURATION_STOP_MIN: 0,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 0,
            CONF_MAX_ON_TIME_PER_DAY_MIN: max_on_time,
            CONF_MIN_ON_TIME_PER_DAY_MIN: min_on_time,
            CONF_OFFPEAK_TIME: "02:00",
        },
    )

    with patch.object(ManagedDevice, "now", new_callable=PropertyMock, return_value=now):
        device = await create_managed_device(hass, entry, "restored_device")
        await hass.async_block_till_done()
    device._set_now(now)

    sensor = search_entity(hass, entity_id, SENSOR_DOMAIN)
    assert sensor is not None
    return device, sensor, events


async def test_restored_on_time_is_synchronized_before_initial_attributes(hass: HomeAssistant, init_solar_optimizer_central_config, monkeypatch):
    """The restored counter is effective before initial attributes are published."""
    now = datetime(2024, 11, 10, 2, 3, tzinfo=get_tz(hass))
    restored_state = State(
        "sensor.on_time_today_solar_optimizer_restored_device",
        "7800",
        {"last_datetime_on": None},
    )
    device, sensor, events = await _create_restored_device(hass, monkeypatch, restored_state, now)
    assert sensor.native_value == 7800
    assert device._on_time_sec == 7800
    assert device.should_be_forced_offpeak is False
    assert [event[0] for event in events[:3]] == ["setter", "attributes", "publish"]
    assert events[0] == ("setter", 7800, 7800)
    assert events[1][:3] == ("attributes", 7800, 7800)
    assert events[1][3] is False
    assert events[2][0:3] == ("publish", 7800, 7800)
    assert events[2][3]["should_be_forced_offpeak"] is False
    published_state = hass.states.get(sensor.entity_id)
    assert published_state is not None
    assert published_state.state == "7800"
    assert published_state.attributes["should_be_forced_offpeak"] is False


async def test_restored_fractional_on_time_keeps_existing_rounding(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    monkeypatch,
):
    """The restored sensor and business counter retain the existing rounding."""
    old_state = State(
        "sensor.on_time_today_solar_optimizer_restored_device",
        "7140.6",
        {},
    )
    now = datetime(2024, 11, 10, 2, 3, tzinfo=get_tz(hass))
    device, sensor, events = await _create_restored_device(hass, monkeypatch, old_state, now)

    assert sensor.native_value == 7141
    assert device._on_time_sec == 7141
    assert events[0] == ("setter", 7141, 7141)


@pytest.mark.parametrize(
    ("restored_seconds", "hour", "minute", "expected_forcing"),
    [
        (24600, 2, 3, False),
        (7800, 2, 3, False),
        (7200, 2, 3, False),
        (7140, 2, 3, True),
        (7140, 1, 59, False),
    ],
)
async def test_restored_minimum_and_offpeak_window(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    monkeypatch,
    restored_seconds,
    hour,
    minute,
    expected_forcing,
):
    """The restored duration and existing off-peak window govern forcing."""
    now = datetime(2024, 11, 10, hour, minute, tzinfo=get_tz(hass))
    old_state = State(
        "sensor.on_time_today_solar_optimizer_restored_device",
        str(restored_seconds),
        {},
    )
    device, sensor, events = await _create_restored_device(hass, monkeypatch, old_state, now)

    assert sensor.native_value == restored_seconds
    assert device._on_time_sec == restored_seconds
    assert device.should_be_forced_offpeak is expected_forcing
    assert events[1][0] == "attributes"
    assert events[1][3] is expected_forcing
    assert events[2][0] == "publish"
    assert events[2][3]["should_be_forced_offpeak"] is expected_forcing


@pytest.mark.parametrize(
    ("state_value", "has_old_state", "date_value"),
    [
        (None, False, None),
        (None, True, "2024-11-10T01:00:00-05:00"),
        ("unknown", True, None),
        ("unavailable", True, None),
        ("not-a-number", True, "2024-11-10T01:00:00-05:00"),
    ],
)
async def test_unrestorable_on_time_synchronizes_zero_before_publication(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    monkeypatch,
    state_value,
    has_old_state,
    date_value,
):
    """Every currently handled fallback synchronizes zero before attributes."""
    entity_id = "sensor.on_time_today_solar_optimizer_restored_device"
    attributes = {"last_datetime_on": date_value} if date_value else {}
    if not has_old_state:
        old_state = None
    elif state_value is None:
        old_state = SimpleNamespace(state=None, attributes=attributes)
    else:
        old_state = State(entity_id, state_value, attributes)

    now = datetime(2024, 11, 10, 2, 3, tzinfo=get_tz(hass))
    device, sensor, events = await _create_restored_device(hass, monkeypatch, old_state, now)

    assert sensor.native_value == 0
    assert device._on_time_sec == 0
    assert [event[0] for event in events[:3]] == [
        "setter",
        "attributes",
        "publish",
    ]
    assert events[0] == ("setter", 0, 0)
    assert events[1][1:3] == (0, 0)
    assert events[2][1:3] == (0, 0)
    expected_date = datetime.fromisoformat(date_value) if date_value else None
    assert sensor.last_datetime_on == expected_date
    assert events[1][4] == expected_date


async def test_inactive_refresh_preserves_restored_on_time_without_activation(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    monkeypatch,
):
    """An inactive refresh retains restored time and never activates the device."""
    old_state = State(
        "sensor.on_time_today_solar_optimizer_restored_device",
        "7800",
        {},
    )
    now = datetime(2024, 11, 10, 2, 3, tzinfo=get_tz(hass))
    device, sensor, _ = await _create_restored_device(hass, monkeypatch, old_state, now)

    with patch.object(device, "activate", new_callable=AsyncMock) as activate:
        await sensor._on_update_on_time()

    assert sensor.native_value == 7800
    assert device._on_time_sec == 7800
    assert sensor.last_datetime_on is None
    activate.assert_not_awaited()


@pytest.mark.parametrize(("restored_seconds", "expected_activation"), [(7800, False), (7140, True)])
async def test_first_coordinator_calculation_uses_restored_minimum(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    monkeypatch,
    restored_seconds,
    expected_activation,
):
    """The first explicit optimization applies real forcing to restored time."""
    old_state = State(
        "sensor.on_time_today_solar_optimizer_restored_device",
        str(restored_seconds),
        {},
    )
    now = datetime(2024, 11, 10, 2, 3, tzinfo=get_tz(hass))
    device, sensor, _ = await _create_restored_device(hass, monkeypatch, old_state, now)
    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)
    solution = [{"name": device.name, "requested_power": 0, "state": False}]

    with (
        patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)),
        patch.object(device, "activate", new_callable=AsyncMock) as activate,
    ):
        await coordinator._async_update_data()

    assert sensor.native_value == restored_seconds
    assert device._on_time_sec == restored_seconds
    assert device.should_be_forced_offpeak is expected_activation
    if expected_activation:
        activate.assert_awaited_once()
    else:
        activate.assert_not_awaited()


async def test_min_on_time_config_ok(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Testing min_on_time configuration ok"""

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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
            CONF_OFFPEAK_TIME: "23:00",
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
    assert device.min_on_time_per_day_sec == 5 * 60
    assert device.offpeak_time == time(23, 0)


@pytest.mark.parametrize(
    ("offpeak_max", "expected_max", "on_time", "expected_force"),
    [
        (None, 10 * 60, 9 * 60, True),
        (6, 6 * 60, 5 * 60, True),
        (6, 6 * 60, 6 * 60, False),
    ],
)
async def test_offpeak_maximum_duration(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    offpeak_max,
    expected_max,
    on_time,
    expected_force,
):
    """The off-peak limit falls back to the daily maximum and remains absolute."""
    data = {
        CONF_NAME: "Equipement A",
        CONF_DEVICE_TYPE: CONF_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_MAX: 1000,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_STOP_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 10 if offpeak_max is None else 6,
        CONF_OFFPEAK_TIME: "23:00",
    }
    if offpeak_max is not None:
        data[CONF_MAX_ON_TIME_OFFPEAK_MIN] = offpeak_max

    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Equipement A", unique_id="eqtA", data=data),
        "equipement_a",
    )
    assert device is not None
    assert device.max_on_time_offpeak_sec == expected_max

    device._set_now(datetime(2024, 11, 10, 23, 0, tzinfo=get_tz(hass)))
    device._next_date_available = device.now - timedelta(seconds=1)
    device.set_on_time(on_time)
    with patch.object(device, "check_usable", return_value=True):
        assert device.should_be_forced_offpeak is expected_force


async def test_offpeak_maximum_duration_incompatible_with_minimum_is_rejected(hass: HomeAssistant, init_solar_optimizer_central_config):
    """A template resolving below the minimum duration cannot force the device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtA",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_BATTERY_SOC_THRESHOLD: 0,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
            CONF_MAX_ON_TIME_OFFPEAK_MIN: "{{ 4 }}",
            CONF_OFFPEAK_TIME: "23:00",
        },
    )

    device = await create_managed_device(hass, entry, "equipement_a")
    assert device is None


async def test_invalid_runtime_offpeak_maximum_duration_blocks_forcing(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """A duration template that becomes incoherent cannot force the device."""
    hass.states.async_set("input_number.offpeak_max", 6)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtA",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
            CONF_MAX_ON_TIME_OFFPEAK_MIN: "{{ states('input_number.offpeak_max') }}",
            CONF_OFFPEAK_TIME: "23:00",
        },
    )

    device = await create_managed_device(hass, entry, "equipement_a")
    assert device is not None

    device._set_now(datetime(2024, 11, 10, 23, 0, tzinfo=get_tz(hass)))
    device.set_on_time(0)
    hass.states.async_set("input_number.offpeak_max", 4)

    with patch.object(device, "check_usable", return_value=True):
        assert device.should_be_forced_offpeak is False


async def test_min_on_time_config_ko_1(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Testing min_in_time with min >= max"""
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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 15,
            CONF_OFFPEAK_TIME: "23:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is None
    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    assert coordinator is not None
    assert len(coordinator.devices) == 0


async def test_min_on_time_config_ko_2(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Testing min_in_time with min requires offpeak_time"""
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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is None
    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    assert coordinator is not None
    assert len(coordinator.devices) == 0


@pytest.mark.parametrize(
    "current_datetime, should_be_forced_offpeak",
    [
        (datetime(2024, 11, 10, 10, 00, 00), False),
        (datetime(2024, 11, 10, 0, 59, 00), False),
        (datetime(2024, 11, 10, 1, 0, 00), True),
    ],
)
async def test_min_on_time_config_ko_3(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    current_datetime,
    should_be_forced_offpeak,
):
    """Testing min_in_time with min requires offpeak_time < raz_time"""

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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
            CONF_OFFPEAK_TIME: "01:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    assert device.name == "Equipement A"

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None

    assert len(coordinator.devices) == 1
    device = coordinator.devices[0]
    assert device.offpeak_time == time(1, 0, 0)

    device._set_now(current_datetime.replace(tzinfo=get_tz(hass)))
    # 5 minutes back so that device is_available
    device._next_date_available = device.now - timedelta(minutes=5)

    with patch(
        "custom_components.solar_optimizer.managed_device.ManagedDevice.is_usable",
        return_value=True,
    ):
        assert device.should_be_forced_offpeak is should_be_forced_offpeak


async def test_nominal_use_min_on_time(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Testing the nominal case with min_on_time and offpeak_time"""

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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
            CONF_OFFPEAK_TIME: "23:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    assert device.name == "Equipement A"

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    # default value
    assert coordinator.raz_time == time(5, 0, 0)

    device_a: ManagedDevice = coordinator.devices[0]
    assert device_a.min_on_time_per_day_sec == 5 * 60
    assert device_a.offpeak_time == time(23, 0)

    now = datetime(2024, 11, 10, 10, 00, 00).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)

    # Creates the fake input_boolean (the device)
    await create_test_input_boolean(hass, device_a.entity_id, "fake underlying A")
    fake_input_bool = search_entity(
        hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN
    )
    assert fake_input_bool is not None

    # The on_time should be 0
    device_a_on_time_sensor = search_entity(
        hass, "sensor.on_time_today_solar_optimizer_equipement_a", SENSOR_DOMAIN
    )
    assert device_a_on_time_sensor.state == 0
    assert device_a_on_time_sensor.last_datetime_on is None
    device_a.reset_next_date_available(
        "Activate"
    )  # for test only to reset the next_available date

    #
    # 1. Activate the underlying switch
    #
    assert device_a.is_usable is False  # because duration_min is 3 minutes
    assert device_a.is_enabled is True

    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()

    #
    # 2. stop the unerlying switch, after 3 minutes.
    #
    now = now + timedelta(minutes=4)
    device_a._set_now(now)

    assert device_a.is_usable is True
    # before 23:00 device should not be forcable
    assert device_a.should_be_forced_offpeak is False

    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()

    assert device_a_on_time_sensor.state == 4 * 60

    #
    # 3. before 23:00, the device should not be Usable
    #
    now = datetime(2024, 11, 10, 22, 59, 59).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)
    assert device_a.should_be_forced_offpeak is False

    #
    # 4. just after 23:00 it should be possible to force offpeak
    #
    now = datetime(2024, 11, 10, 23, 00, 00).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)
    assert device_a.should_be_forced_offpeak is True

    #
    # 5. at 01:00 it should be possible to force offpeak
    #
    with patch.object(
        type(device_a),
        "is_usable",
        new_callable=PropertyMock,
        return_value=True,
    ):
        now = datetime(2024, 11, 11, 1, 00, 00).replace(tzinfo=get_tz(hass))
        device_a._set_now(now)
        assert device_a.should_be_forced_offpeak is True

        #
        # 6. at 04:59 it should be possible to force offpeak
        #
        now = datetime(2024, 11, 11, 4, 59, 00).replace(tzinfo=get_tz(hass))
        device_a._set_now(now)
        assert device_a.should_be_forced_offpeak is True

        #
        # 6. at 05:01 it should be not possible to force offpeak
        #
        now = datetime(2024, 11, 11, 5, 1, 00).replace(tzinfo=get_tz(hass))
        device_a._set_now(now)
        assert device_a.should_be_forced_offpeak is False

        #
        # 7. when on_time is > max_on_time it should be not possible to force off_peak
        #
        # Come back in offpeak
        now = datetime(2024, 11, 11, 0, 0, 00).replace(tzinfo=get_tz(hass))
        device_a._set_now(now)
        assert device_a.should_be_forced_offpeak is True

        await fake_input_bool.async_turn_on()
        await hass.async_block_till_done()

        now = now + timedelta(minutes=6)  # 6 minutes + 4 minutes already done
        device_a._set_now(now)
        await fake_input_bool.async_turn_off()
        await hass.async_block_till_done()

        assert device_a_on_time_sensor.state == 10 * 60
        assert device_a._on_time_sec == 10 * 60

        assert device_a.should_be_forced_offpeak is False


async def test_nominal_use_offpeak_without_min(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Testing the nominal case with min_on_time and offpeak_time"""

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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
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
    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 1

    # default value
    assert coordinator.raz_time == time(5, 0, 0)

    # 0. check default values
    device_a: ManagedDevice = coordinator.devices[0]
    assert device_a.min_on_time_per_day_sec == 0
    # default offpeak_time
    assert device_a.offpeak_time is None

    now = datetime(2024, 11, 10, 10, 00, 00).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)

    # Creates the fake input_boolean (the device)
    await create_test_input_boolean(hass, device_a.entity_id, "fake underlying A")
    fake_input_bool = search_entity(
        hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN
    )
    assert fake_input_bool is not None

    # The on_time should be 0
    device_a_on_time_sensor = search_entity(
        hass, "sensor.on_time_today_solar_optimizer_equipement_a", SENSOR_DOMAIN
    )
    assert device_a_on_time_sensor.state == 0
    assert device_a_on_time_sensor.last_datetime_on is None
    device_a.reset_next_date_available(
        "Activate"
    )  # for test only to reset the next_available date

    #
    # 2. Activate the underlying switch during 3 minutes
    #
    assert device_a.is_usable is False  # because duration_min is 3 minutes
    assert device_a.is_enabled is True

    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()
    now = now + timedelta(minutes=4)
    device_a._set_now(now)

    assert device_a.is_usable is True
    # before 23:00 device should not be forcable
    assert device_a.should_be_forced_offpeak is False

    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()

    assert device_a_on_time_sensor.state == 4 * 60

    #
    # 4. just at 23:59 it should be not possible to force offpeak
    #
    now = datetime(2024, 11, 10, 23, 59, 00).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)
    assert device_a.should_be_forced_offpeak is False

    #
    # 5. at 01:00 it should be not possible to force offpeak
    #
    with patch.object(
        type(device_a),
        "is_usable",
        new_callable=PropertyMock,
        return_value=True,
    ):
        now = datetime(2024, 11, 10, 1, 00, 00).replace(tzinfo=get_tz(hass))
        device_a._set_now(now)
        assert device_a.should_be_forced_offpeak is False


async def test_nominal_use_min_on_time_exceeded(hass: HomeAssistant, init_solar_optimizer_central_config):
    """Testing the nominal case with min_on_time and offpeak_time"""

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
            CONF_DURATION_MIN: 2,
            CONF_DURATION_STOP_MIN: 1,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: 30,
            CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
            CONF_MIN_ON_TIME_PER_DAY_MIN: 2,
            CONF_OFFPEAK_TIME: "23:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    assert device.name == "Equipement A"

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    # default value
    assert coordinator.raz_time == time(5, 0, 0)

    device_a: ManagedDevice = coordinator.devices[0]
    assert device_a.min_on_time_per_day_sec == 2 * 60
    assert device_a.offpeak_time == time(23, 0)

    now = datetime(2024, 11, 10, 10, 00, 00).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)

    # Creates the fake input_boolean (the device)
    await create_test_input_boolean(hass, device_a.entity_id, "fake underlying A")
    fake_input_bool = search_entity(hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN)
    assert fake_input_bool is not None

    # The on_time should be 0
    device_a_on_time_sensor = search_entity(hass, "sensor.on_time_today_solar_optimizer_equipement_a", SENSOR_DOMAIN)
    assert device_a_on_time_sensor.state == 0
    assert device_a_on_time_sensor.last_datetime_on is None
    device_a.reset_next_date_available("Activate")  # for test only to reset the next_available date

    #
    # 1. Activate the underlying switch
    #
    assert device_a.is_usable is False  # because duration_min is 3 minutes
    assert device_a.is_enabled is True

    await fake_input_bool.async_turn_on()
    await hass.async_block_till_done()

    #
    # 2. stop the unerlying switch, after 3 minutes.
    #
    now = now + timedelta(minutes=4)
    device_a._set_now(now)

    assert device_a.is_usable is True
    # before 23:00 device should not be forcable
    assert device_a.should_be_forced_offpeak is False

    await fake_input_bool.async_turn_off()
    await hass.async_block_till_done()

    assert device_a_on_time_sensor.state == 4 * 60

    #
    # 3. before 23:00, the device should not be Usable
    #
    now = datetime(2024, 11, 10, 22, 59, 59).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)
    assert device_a.should_be_forced_offpeak is False

    #
    # 4. just after 23:00 it should be possible to force offpeak
    #
    now = datetime(2024, 11, 10, 23, 00, 00).replace(tzinfo=get_tz(hass))
    device_a._set_now(now)
    assert device_a.should_be_forced_offpeak is False
