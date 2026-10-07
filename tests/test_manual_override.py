"""Unit tests for the manual override feature:
- detecting an out-of-band change of the underlying entity (check_for_manual_override)
- detecting a manual click on the 'Active' switch (ManagedDeviceSwitch)
- clearing the override: by matching the pre-override state, at raz_time, via the
  Enable switch, or via the solar_optimizer.clear_override service
- the binary_sensor.solar_optimizer_override_<device> entity
- Context propagation for Home Assistant history/logbook attribution
"""
# pylint: disable=protected-access

from datetime import timedelta
from unittest.mock import AsyncMock

from homeassistant.core import Context
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN

from custom_components.solar_optimizer.const import get_tz
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
    CONF_MAX_ON_TIME_PER_DAY_MIN: 60,
}


async def _setup_device(hass):
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtAUniqueId",
        data=DEVICE_A_DATA,
    )
    device = await create_managed_device(hass, entry_a, "equipement_a")
    assert device is not None
    await create_test_input_boolean(hass, device.entity_id, "fake underlying A")
    fake_bool = search_entity(hass, "input_boolean.fake_device_a", INPUT_BOOLEAN_DOMAIN)
    # Reset the debounce timer so is_waiting doesn't get in the way of the tests below
    device.reset_next_date_available("Activate")
    device._next_date_available = device.now - timedelta(minutes=5)
    return device, fake_bool


# ---------------------------------------------------------------------------
# trigger_manual_override / clear_override basics
# ---------------------------------------------------------------------------

async def test_trigger_manual_override_pauses_device(hass, init_solar_optimizer_central_config):
    """trigger_manual_override disables SO management and records the override."""
    device, _ = await _setup_device(hass)

    enable_switch = search_entity(hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN)
    assert enable_switch.state == "on"

    device.trigger_manual_override()
    await hass.async_block_till_done()

    assert device.override_active is True
    assert device.override_since is not None
    assert device.is_enabled is False
    assert enable_switch.state == "off"


async def test_trigger_manual_override_is_idempotent(hass, init_solar_optimizer_central_config):
    """Calling trigger_manual_override while already overridden does not reset override_since."""
    device, _ = await _setup_device(hass)

    device.trigger_manual_override()
    since = device.override_since

    device._set_now(device.now + timedelta(minutes=5))
    device.trigger_manual_override()

    assert device.override_since == since


async def test_clear_override(hass, init_solar_optimizer_central_config):
    """clear_override resumes SO management."""
    device, _ = await _setup_device(hass)

    device.trigger_manual_override()
    assert device.is_enabled is False

    device.clear_override()

    assert device.override_active is False
    assert device.override_since is None
    assert device.is_enabled is True


# ---------------------------------------------------------------------------
# check_for_manual_override: coordinator-detected mismatch
# ---------------------------------------------------------------------------

async def test_check_for_manual_override_detects_mismatch(hass, init_solar_optimizer_central_config):
    """If SO last commanded ON but the real device is now OFF (and it's not waiting,
    not in a forced session), the coordinator's periodic check must flag an override."""
    device, fake_bool = await _setup_device(hass)

    await device.activate()
    assert device.is_active is True
    assert device.last_commanded_state is True

    # Move past activate()'s own debounce window (duration_min) so the mismatch below
    # isn't mistaken for the real entity merely catching up with our own last command
    device._set_now(device.now + timedelta(seconds=20))

    # Someone switches it off directly, bypassing Solar Optimizer entirely
    await fake_bool.async_turn_off()
    await hass.async_block_till_done()
    assert device.is_active is False

    device.check_for_manual_override()

    assert device.override_active is True
    assert device.is_enabled is False


async def test_check_for_manual_override_ignores_match(hass, init_solar_optimizer_central_config):
    """No override should be raised when the real state matches what SO commanded."""
    device, _ = await _setup_device(hass)

    await device.deactivate()
    device.check_for_manual_override()

    assert device.override_active is False
    assert device.is_enabled is True


async def test_check_for_manual_override_ignores_while_waiting(hass, init_solar_optimizer_central_config):
    """A mismatch during the post-command debounce window (is_waiting) must not be
    flagged - that's just the real entity catching up with SO's own last command."""
    device, fake_bool = await _setup_device(hass)

    await device.activate()
    # Re-arm a waiting window as if the command had just been sent
    device.reset_next_date_available("Activate")

    await fake_bool.async_turn_off()
    await hass.async_block_till_done()

    device.check_for_manual_override()

    assert device.override_active is False


async def test_check_for_manual_override_ignores_during_forced_session(hass, init_solar_optimizer_central_config):
    """An explicit forced activation (start_forced) must not also be flagged as a
    manual override - it already has its own dedicated tracking (forced_end_time)."""
    device, _ = await _setup_device(hass)

    device.activate = AsyncMock()
    await device.start_forced(duration_hours=1)
    await hass.async_block_till_done()

    assert device.is_enabled is False
    assert device.forced_end_time is not None

    device.check_for_manual_override()

    assert device.override_active is False


# ---------------------------------------------------------------------------
# Resolving an override
# ---------------------------------------------------------------------------

async def test_override_resolved_when_state_matches_baseline_again(hass, init_solar_optimizer_central_config):
    """'el propio algoritmo': once the real state returns to what SO had requested
    before the override, the next coordinator cycle clears it automatically."""
    device, fake_bool = await _setup_device(hass)

    await device.activate()
    device._set_now(device.now + timedelta(seconds=20))
    await fake_bool.async_turn_off()
    await hass.async_block_till_done()
    device.check_for_manual_override()
    assert device.override_active is True

    # The user changes their mind and puts it back the way SO wanted it
    await fake_bool.async_turn_on()
    await hass.async_block_till_done()
    device.check_for_manual_override()

    assert device.override_active is False
    assert device.is_enabled is True


async def test_override_cleared_at_raz_time(hass, init_solar_optimizer_central_config):
    """The daily reset time clears any pending override, same as the on_time counter."""
    device, _ = await _setup_device(hass)
    device.trigger_manual_override()
    assert device.override_active is True

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    await coordinator._async_on_raz_time()

    assert device.override_active is False
    assert device.is_enabled is True


async def test_override_cleared_via_enable_switch(hass, init_solar_optimizer_central_config):
    """Turning the Enable switch back on (by the user or an automation) clears the override."""
    device, _ = await _setup_device(hass)
    device.trigger_manual_override()

    enable_switch = search_entity(hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN)
    await enable_switch.async_turn_on()
    await hass.async_block_till_done()

    assert device.override_active is False
    assert device.is_enabled is True


async def test_clear_override_service(hass, init_solar_optimizer_central_config):
    """The solar_optimizer.clear_override service lets an automation resume SO
    management explicitly, without needing to know about the Enable switch."""
    device, _ = await _setup_device(hass)
    device.trigger_manual_override()

    await hass.services.async_call(
        DOMAIN, "clear_override", {"device_id": "equipement_a"}, blocking=True
    )
    await hass.async_block_till_done()

    assert device.override_active is False
    assert device.is_enabled is True


# ---------------------------------------------------------------------------
# Manual click on the 'Active' switch
# ---------------------------------------------------------------------------

async def test_active_switch_turn_on_triggers_override(hass, init_solar_optimizer_central_config):
    """Clicking the 'Active' switch on directly is an explicit override: it must not
    be reverted by the algorithm on the next refresh."""
    device, _ = await _setup_device(hass)

    device_switch = search_entity(hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN)
    assert device_switch.state == "off"

    await device_switch.async_turn_on()
    await hass.async_block_till_done()

    assert device.override_active is True
    assert device.is_enabled is False
    assert device.is_active is True


async def test_active_switch_turn_off_triggers_override(hass, init_solar_optimizer_central_config):
    """Clicking the 'Active' switch off directly (no forced session running) is an
    explicit override."""
    device, fake_bool = await _setup_device(hass)
    await fake_bool.async_turn_on()
    await hass.async_block_till_done()

    device_switch = search_entity(hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN)
    assert device_switch.state == "on"

    await device_switch.async_turn_off()
    await hass.async_block_till_done()

    assert device.override_active is True
    assert device.is_enabled is False


async def test_active_switch_turn_off_during_forced_session_does_not_override(hass, init_solar_optimizer_central_config):
    """Stopping an explicit forced session through the 'Active' switch is not a manual
    override - it already has its own semantics (stay disabled until the user acts),
    preserved from before this feature existed."""
    device, _ = await _setup_device(hass)

    device.activate = AsyncMock()
    device.deactivate = AsyncMock()
    await device.start_forced(duration_hours=1)
    await hass.async_block_till_done()

    device_switch = search_entity(hass, "switch.solar_optimizer_equipement_a", SWITCH_DOMAIN)
    device_switch._attr_is_on = True

    await device_switch.async_turn_off()
    await hass.async_block_till_done()

    assert device.forced_end_time is None
    assert device.override_active is False
    # Still disabled, as before this feature (test_enable_switch_turns_on_after_stop_forced)
    assert device.is_enabled is False


# ---------------------------------------------------------------------------
# binary_sensor.solar_optimizer_override_<device>
# ---------------------------------------------------------------------------

async def test_override_binary_sensor_reflects_state(hass, init_solar_optimizer_central_config):
    """The override binary_sensor mirrors ManagedDevice.override_active and exposes
    override_since as an attribute."""
    device, _ = await _setup_device(hass)

    override_sensor = search_entity(
        hass, "binary_sensor.solar_optimizer_override_equipement_a", BINARY_SENSOR_DOMAIN
    )
    assert override_sensor is not None
    assert override_sensor.is_on is False

    device.trigger_manual_override()
    await hass.async_block_till_done()

    assert override_sensor.is_on is True
    assert override_sensor.get_attr_extra_state_attributes.get("override_since") is not None

    device.clear_override()
    await hass.async_block_till_done()

    assert override_sensor.is_on is False


# ---------------------------------------------------------------------------
# Context propagation (history/logbook attribution)
# ---------------------------------------------------------------------------

async def test_activate_sets_last_context(hass, init_solar_optimizer_central_config):
    """Every action Solar Optimizer applies carries a fresh Context, so history can
    trace the underlying entity's change back to our own switch entity."""
    device, _ = await _setup_device(hass)

    assert device.last_context is None

    await device.activate()

    assert isinstance(device.last_context, Context)

    first_context = device.last_context
    await device.deactivate()
    assert isinstance(device.last_context, Context)
    assert device.last_context.id != first_context.id


# ---------------------------------------------------------------------------
# Resuming control must not re-trigger an override from a stale command
# ---------------------------------------------------------------------------

async def test_device_changed_while_disabled_is_not_an_override(hass, init_solar_optimizer_central_config):
    """SO turned the device on, then management was disabled and the device turned off
    by itself. Re-enabling (e.g. an automation at 4:00) must take the real state as the
    new reference instead of flagging the stale 'on' command as an override."""
    device, fake_bool = await _setup_device(hass)
    await device.activate()
    device._set_now(device.now + timedelta(seconds=20))

    enable_switch = search_entity(hass, "switch.enable_solar_optimizer_equipement_a", SWITCH_DOMAIN)
    await enable_switch.async_turn_off()
    await fake_bool.async_turn_off()
    await hass.async_block_till_done()

    await enable_switch.async_turn_on()
    await hass.async_block_till_done()
    device.check_for_manual_override()

    assert device.override_active is False
    assert device.is_enabled is True


async def test_override_cleared_at_raz_time_is_not_retriggered(hass, init_solar_optimizer_central_config):
    """An override whose device stays off is cleared at raz_time: the next periodic check
    must not flag it again (it used to loop Enable ON/OFF and stay overridden forever)."""
    device, fake_bool = await _setup_device(hass)
    await device.activate()
    device._set_now(device.now + timedelta(seconds=20))
    await fake_bool.async_turn_off()
    await hass.async_block_till_done()
    device.check_for_manual_override()
    assert device.override_active is True

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    await coordinator._async_on_raz_time()
    device.check_for_manual_override()

    assert device.override_active is False
    assert device.is_enabled is True
