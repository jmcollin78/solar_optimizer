""" Nominal Unit test module"""

# pylint: disable=protected-access

# from unittest.mock import patch
from datetime import datetime, timedelta, time


from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN

from custom_components.solar_optimizer.const import get_tz
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import


async def test_min_on_time_config_ok(
    hass: HomeAssistant,
):
    """Testing min_on_time configuration ok"""
    await async_setup_component(
        hass,
        "solar_optimizer",
        {
            "solar_optimizer": {
                "algorithm": {
                    "initial_temp": 1000,
                    "min_temp": 0.1,
                    "cooling_factor": 0.95,
                    "max_iteration_number": 1000,
                },
                "devices": [
                    {
                        "name": "Equipement A",
                        "entity_id": "input_boolean.fake_device_a",
                        "power_max": 1000,
                        "check_usable_template": "{{ True }}",
                        "duration_min": 2,
                        "duration_stop_min": 1,
                        "action_mode": "service_call",
                        "activation_service": "input_boolean/turn_on",
                        "deactivation_service": "input_boolean/turn_off",
                        "battery_soc_threshold": 30,
                        "max_on_time_per_day_min": 10,
                        "min_on_time_per_day_min": 5,
                        "offpeak_time": "23:00",
                    },
                    {
                        "name": "Equipement B",
                        "entity_id": "input_boolean.fake_device_b",
                        "power_max": 2000,
                        "check_usable_template": "{{ False }}",
                        "duration_min": 1,
                        "duration_stop_min": 2,
                        "duration_power_min": 3,
                        "action_mode": "service_call",
                        "activation_service": "input_boolean/turn_on",
                        "deactivation_service": "input_boolean/turn_off",
                    },
                ],
            }
        },
    )
    await hass.async_block_till_done()
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN].get("coordinator", None)

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2

    device: ManagedDevice = coordinator.devices[0]
    assert device.name == "Equipement A"
    assert device.is_enabled is True
    assert device.max_on_time_per_day_sec == 10 * 60
    assert device.min_on_time_per_day_sec == 5 * 60
    assert device.offpeak_time == time(23, 0)


async def test_min_on_time_config_ko_1(
    hass: HomeAssistant,
):
    """Testing min_in_time with min >= max"""
    await async_setup_component(
        hass,
        "solar_optimizer",
        {
            "solar_optimizer": {
                "algorithm": {
                    "initial_temp": 1000,
                    "min_temp": 0.1,
                    "cooling_factor": 0.95,
                    "max_iteration_number": 1000,
                },
                "devices": [
                    {
                        "name": "Equipement A",
                        "entity_id": "input_boolean.fake_device_a",
                        "power_max": 1000,
                        "check_usable_template": "{{ True }}",
                        "duration_min": 0.3,
                        "duration_stop_min": 0.1,
                        "action_mode": "service_call",
                        "activation_service": "input_boolean/turn_on",
                        "deactivation_service": "input_boolean/turn_off",
                        "battery_soc_threshold": 30,
                        "max_on_time_per_day_min": 10,
                        "min_on_time_per_day_min": 15,
                        "offpeak_time": "23:00",
                    },
                ],
            }
        },
    )
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN].get("coordinator", None)

    assert coordinator is None


async def test_min_on_time_config_ko_2(
    hass: HomeAssistant,
):
    """Testing min_in_time with min requires offpeak_time"""
    await async_setup_component(
        hass,
        "solar_optimizer",
        {
            "solar_optimizer": {
                "algorithm": {
                    "initial_temp": 1000,
                    "min_temp": 0.1,
                    "cooling_factor": 0.95,
                    "max_iteration_number": 1000,
                },
                "devices": [
                    {
                        "name": "Equipement A",
                        "entity_id": "input_boolean.fake_device_a",
                        "power_max": 1000,
                        "check_usable_template": "{{ True }}",
                        "duration_min": 0.3,
                        "duration_stop_min": 0.1,
                        "action_mode": "service_call",
                        "activation_service": "input_boolean/turn_on",
                        "deactivation_service": "input_boolean/turn_off",
                        "battery_soc_threshold": 30,
                        "max_on_time_per_day_min": 10,
                        "min_on_time_per_day_min": 5,
                    },
                ],
            }
        },
    )
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN].get("coordinator", None)

    assert coordinator is None


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
    init_solar_optimizer_with_devices_offpeak_morning,
    init_solar_optimizer_entry,
    current_datetime,
    should_be_forced_offpeak,
):
    """Testing min_in_time with min requires offpeak_time < raz_time"""

    coordinator: SolarOptimizerCoordinator = (
        init_solar_optimizer_with_devices_offpeak_morning
    )

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
    hass: HomeAssistant,
    init_solar_optimizer_with_2_devices_min_on_time_ok,
    init_solar_optimizer_entry,  # pylint: disable=unused-argument
):
    """Testing the nominal case with min_on_time and offpeak_time"""

    coordinator: SolarOptimizerCoordinator = (
        init_solar_optimizer_with_2_devices_min_on_time_ok
    )

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 2
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
    with patch(
        "custom_components.solar_optimizer.managed_device.ManagedDevice.is_usable",
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
    hass: HomeAssistant,
):
    """Testing the nominal case with min_on_time and offpeak_time"""

    await async_setup_component(
        hass,
        "solar_optimizer",
        {
            "solar_optimizer": {
                "algorithm": {
                    "initial_temp": 1000,
                    "min_temp": 0.1,
                    "cooling_factor": 0.95,
                    "max_iteration_number": 1000,
                },
                "devices": [
                    {
                        "name": "Equipement A",
                        "entity_id": "input_boolean.fake_device_a",
                        "power_max": 1000,
                        "check_usable_template": "{{ True }}",
                        "duration_min": 2,
                        "duration_stop_min": 1,
                        "action_mode": "service_call",
                        "activation_service": "input_boolean/turn_on",
                        "deactivation_service": "input_boolean/turn_off",
                        "battery_soc_threshold": 30,
                        "max_on_time_per_day_min": 10,
                    }
                ],
            }
        },
    )
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN]["coordinator"]

    assert coordinator is not None
    assert coordinator.devices is not None
    assert len(coordinator.devices) == 1

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheSolarOptimizer",
        unique_id="uniqueId",
        data={},
    )

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

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
    with patch(
        "custom_components.solar_optimizer.managed_device.ManagedDevice.is_usable",
        return_value=True,
    ):
        now = datetime(2024, 11, 10, 1, 00, 00).replace(tzinfo=get_tz(hass))
        device_a._set_now(now)
        assert device_a.should_be_forced_offpeak is False
