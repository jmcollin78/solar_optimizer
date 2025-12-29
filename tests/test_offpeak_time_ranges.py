"""Unit tests for off-peak time ranges and entity-based off-peak detection"""

# pylint: disable=protected-access

from datetime import datetime, timedelta, time
from unittest.mock import patch, MagicMock

import pytest

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.solar_optimizer.const import (
    get_tz,
    parse_time_ranges,
    CONF_NAME,
    CONF_DEVICE_TYPE,
    CONF_DEVICE,
    CONF_ENTITY_ID,
    CONF_POWER_MAX,
    CONF_CHECK_USABLE_TEMPLATE,
    CONF_DURATION_MIN,
    CONF_DURATION_STOP_MIN,
    CONF_ACTION_MODE,
    CONF_ACTION_MODE_ACTION,
    CONF_ACTIVATION_SERVICE,
    CONF_DEACTIVATION_SERVICE,
    CONF_BATTERY_SOC_THRESHOLD,
    CONF_MAX_ON_TIME_PER_DAY_MIN,
    CONF_MIN_ON_TIME_PER_DAY_MIN,
    CONF_OFFPEAK_TIME,
    CONF_OFFPEAK_ENTITY_ID,
    DOMAIN,
)
from .commons import (
    create_managed_device,
    search_entity,
    create_test_input_boolean,
    MockConfigEntry,
    HomeAssistant,
    SolarOptimizerCoordinator,
    ManagedDevice,
)


class TestParseTimeRanges:
    """Test the parse_time_ranges utility function"""

    def test_parse_single_range(self):
        """Test parsing a single time range"""
        ranges = parse_time_ranges("13:00-14:00")
        assert len(ranges) == 1
        assert ranges[0] == (time(13, 0), time(14, 0))

    def test_parse_multiple_ranges(self):
        """Test parsing multiple time ranges"""
        ranges = parse_time_ranges("13:00-14:00,22:00-06:00")
        assert len(ranges) == 2
        assert ranges[0] == (time(13, 0), time(14, 0))
        assert ranges[1] == (time(22, 0), time(6, 0))

    def test_parse_three_ranges(self):
        """Test parsing three time ranges"""
        ranges = parse_time_ranges("06:00-07:00,12:00-13:00,22:00-23:00")
        assert len(ranges) == 3
        assert ranges[0] == (time(6, 0), time(7, 0))
        assert ranges[1] == (time(12, 0), time(13, 0))
        assert ranges[2] == (time(22, 0), time(23, 0))

    def test_parse_empty_string(self):
        """Test parsing an empty string"""
        ranges = parse_time_ranges("")
        assert len(ranges) == 0

    def test_parse_none(self):
        """Test parsing None"""
        ranges = parse_time_ranges(None)
        assert len(ranges) == 0


async def test_offpeak_time_ranges_config(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Test configuration with time ranges format"""

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
            CONF_OFFPEAK_TIME: "13:00-14:00,22:00-06:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    assert device.name == "Equipement A"
    assert device.offpeak_time is None  # Legacy single time should be None
    assert len(device.offpeak_time_ranges) == 2
    assert device.offpeak_time_ranges[0] == (time(13, 0), time(14, 0))
    assert device.offpeak_time_ranges[1] == (time(22, 0), time(6, 0))


@pytest.mark.parametrize(
    "current_datetime, should_be_offpeak",
    [
        # Not in any range
        (datetime(2024, 11, 10, 10, 0, 0), False),
        (datetime(2024, 11, 10, 15, 0, 0), False),
        (datetime(2024, 11, 10, 20, 0, 0), False),
        # In first range (13:00-14:00)
        (datetime(2024, 11, 10, 13, 0, 0), True),
        (datetime(2024, 11, 10, 13, 30, 0), True),
        (datetime(2024, 11, 10, 13, 59, 0), True),
        # Just before/after first range
        (datetime(2024, 11, 10, 12, 59, 0), False),
        (datetime(2024, 11, 10, 14, 0, 0), False),
        # In second range (22:00-06:00) - crosses midnight
        (datetime(2024, 11, 10, 22, 0, 0), True),
        (datetime(2024, 11, 10, 23, 30, 0), True),
        (datetime(2024, 11, 11, 0, 0, 0), True),
        (datetime(2024, 11, 11, 3, 0, 0), True),
        (datetime(2024, 11, 11, 5, 59, 0), True),
        # Just before/after second range
        (datetime(2024, 11, 10, 21, 59, 0), False),
        (datetime(2024, 11, 11, 6, 0, 0), False),
    ],
)
async def test_offpeak_time_ranges_detection(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    current_datetime,
    should_be_offpeak,
):
    """Test off-peak detection with multiple time ranges"""

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
            CONF_OFFPEAK_TIME: "13:00-14:00,22:00-06:00",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    device._set_now(current_datetime.replace(tzinfo=get_tz(hass)))
    # Make device available
    device._next_date_available = device.now - timedelta(minutes=5)

    with patch(
        "custom_components.solar_optimizer.managed_device.ManagedDevice.is_usable",
        return_value=True,
    ):
        assert device.is_offpeak is should_be_offpeak
        if should_be_offpeak:
            assert device.should_be_forced_offpeak is True


async def test_offpeak_entity_config(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Test configuration with entity-based off-peak detection"""

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
            CONF_OFFPEAK_ENTITY_ID: "binary_sensor.offpeak_hours",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    assert device.name == "Equipement A"
    assert device.offpeak_time is None
    assert len(device.offpeak_time_ranges) == 0
    assert device.offpeak_entity_id == "binary_sensor.offpeak_hours"


@pytest.mark.parametrize(
    "entity_state, should_be_offpeak",
    [
        (STATE_ON, True),
        ("on", True),
        ("true", True),
        ("1", True),
        ("yes", True),
        (STATE_OFF, False),
        ("off", False),
        ("false", False),
        ("0", False),
        ("no", False),
        ("unavailable", False),
        ("unknown", False),
    ],
)
async def test_offpeak_entity_detection(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    entity_state,
    should_be_offpeak,
):
    """Test off-peak detection using entity state"""

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
            CONF_OFFPEAK_ENTITY_ID: "binary_sensor.offpeak_hours",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    now = datetime(2024, 11, 10, 10, 0, 0).replace(tzinfo=get_tz(hass))
    device._set_now(now)
    device._next_date_available = device.now - timedelta(minutes=5)

    # Mock the entity state
    mock_state = MagicMock()
    mock_state.state = entity_state
    hass.states._states["binary_sensor.offpeak_hours"] = mock_state

    with patch(
        "custom_components.solar_optimizer.managed_device.ManagedDevice.is_usable",
        return_value=True,
    ):
        assert device.is_offpeak is should_be_offpeak
        if should_be_offpeak:
            assert device.should_be_forced_offpeak is True


async def test_offpeak_entity_not_found(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Test off-peak detection when entity is not found"""

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
            CONF_OFFPEAK_ENTITY_ID: "binary_sensor.nonexistent",
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    now = datetime(2024, 11, 10, 10, 0, 0).replace(tzinfo=get_tz(hass))
    device._set_now(now)
    device._next_date_available = device.now - timedelta(minutes=5)

    # Entity doesn't exist, should return False
    assert device.is_offpeak is False


async def test_legacy_offpeak_time_still_works(
    hass: HomeAssistant, init_solar_optimizer_central_config
):
    """Test that legacy single offpeak_time format still works"""

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
            CONF_OFFPEAK_TIME: "23:00",  # Legacy format
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "equipement_a",
    )
    assert device is not None

    assert device.offpeak_time == time(23, 0)
    assert len(device.offpeak_time_ranges) == 0
    assert device.offpeak_entity_id is None

    # Test that legacy logic still works
    now = datetime(2024, 11, 10, 23, 30, 0).replace(tzinfo=get_tz(hass))
    device._set_now(now)
    device._next_date_available = device.now - timedelta(minutes=5)

    with patch(
        "custom_components.solar_optimizer.managed_device.ManagedDevice.is_usable",
        return_value=True,
    ):
        assert device.is_offpeak is True
        assert device.should_be_forced_offpeak is True
