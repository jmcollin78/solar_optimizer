"""Scenario tests of the manual override, driving real coordinator cycles: the algorithm
decides, its actions really switch the underlying input_booleans, the net consumption
follows the devices that are on, and the time is simulated.

With "Respect manual changes" ON, a change made by the user is kept until it is released.
With it OFF, Solar Optimizer behaves like before the feature: it puts the device back
as it decides at the next cycle. The override and the switch of a device never affect
another device."""

# pylint: disable=unused-argument, wildcard-import, unused-wildcard-import, protected-access

from datetime import timedelta

import pytest

from homeassistant.setup import async_setup_component
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN

from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator

from .commons import *

DEVICE_POWER = 1000
SURPLUS = -1000  # net consumption without the managed devices: 1000 W exported
NO_SURPLUS = 500  # 500 W imported


class Home:
    """Simulated installation: devices, net consumption that follows them, and time"""

    def __init__(self, hass, coordinator, devices, bools):
        self.hass = hass
        self.coordinator = coordinator
        self.devices = devices  # name -> ManagedDevice
        self.bools = bools  # name -> input_boolean entity (the "real" device)
        self.now = devices[next(iter(devices))].now + timedelta(minutes=1)
        self.base = SURPLUS
        self._set_now()

    def _set_now(self):
        for device in self.devices.values():
            device._set_now(self.now)

    def advance(self, seconds):
        """Let time pass (durations of the devices are 18 s on / 6 s off)"""
        self.now += timedelta(seconds=seconds)
        self._set_now()

    async def cycle(self, base=None, advance=60):
        """One Solar Optimizer cycle after `advance` seconds, with the net consumption
        of the house (`base`) plus the devices that are really on"""
        if base is not None:
            self.base = base
        self.advance(advance)
        consumption = self.base + sum(DEVICE_POWER for d in self.devices.values() if d.is_active)
        self.hass.states.async_set("sensor.fake_power_consumption", consumption)
        await self.coordinator._async_update_data()
        await self.hass.async_block_till_done()

    async def user_turns(self, name, on: bool, via_so_switch=False):
        """The user changes the device: on the device itself, or with the SO switch"""
        if via_so_switch:
            entity = search_entity(self.hass, f"switch.solar_optimizer_{name}", SWITCH_DOMAIN)
        else:
            entity = self.bools[name]
        await (entity.async_turn_on() if on else entity.async_turn_off())
        await self.hass.async_block_till_done()

    def is_on(self, name):
        return self.devices[name].is_active

    def overridden(self, name):
        device = self.devices[name]
        sensor = self.hass.states.get(f"binary_sensor.solar_optimizer_override_{name}")
        assert sensor is not None and (sensor.state == "on") == device.override_active
        return device.override_active

    def enabled(self, name):
        return self.devices[name].is_enabled

    async def set_respect(self, name, on: bool):
        entity = search_entity(self.hass, f"switch.respect_manual_changes_solar_optimizer_{name}", SWITCH_DOMAIN)
        await (entity.async_turn_on() if on else entity.async_turn_off())
        await self.hass.async_block_till_done()


async def make_home(hass, respect: dict) -> Home:
    """One on/off device of 1000 W per entry of `respect` (name -> Respect manual changes)"""
    for entity_id, value in {
        "sensor.fake_power_production": 5000,
        "sensor.fake_battery_soc": 100,
        "sensor.fake_battery_charge_power": 0,
        "input_number.fake_sell_cost": 1,
        "input_number.fake_buy_cost": 1,
        "input_number.fake_sell_tax_percent": 0,
    }.items():
        hass.states.async_set(entity_id, value)

    await async_setup_component(
        hass, INPUT_BOOLEAN_DOMAIN, {INPUT_BOOLEAN_DOMAIN: {f"fake_{name}": {"name": f"fake {name}"} for name in respect}}
    )
    devices, bools = {}, {}
    for name in respect:
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=name,
            unique_id=f"{name}UniqueId",
            data={
                CONF_NAME: name,
                CONF_DEVICE_TYPE: CONF_DEVICE,
                CONF_ENTITY_ID: f"input_boolean.fake_{name}",
                CONF_POWER_MAX: DEVICE_POWER,
                CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
                CONF_DURATION_MIN: 0.3,
                CONF_DURATION_STOP_MIN: 0.1,
                CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
                CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
                CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
                CONF_BATTERY_SOC_THRESHOLD: 0,
            },
        )
        devices[name] = await create_managed_device(hass, entry, name)
        bools[name] = search_entity(hass, f"input_boolean.fake_{name}", INPUT_BOOLEAN_DOMAIN)

    home = Home(hass, SolarOptimizerCoordinator.get_coordinator(), devices, bools)
    for name, on in respect.items():
        await home.set_respect(name, on)
    return home


# ---------------------------------------------------------------------------
# Respect manual changes = ON
# ---------------------------------------------------------------------------


async def test_on_user_turns_off_what_so_turned_on(hass, init_solar_optimizer_central_config):
    """1. SO turns the device on with the surplus, the user turns it off on the device:
    it stays off in the next cycles although the surplus is still there"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(SURPLUS)
    assert home.is_on("pump")

    await home.user_turns("pump", False)
    for _ in range(3):
        await home.cycle(SURPLUS, advance=600)
        assert not home.is_on("pump")
        assert home.overridden("pump") and not home.enabled("pump")


async def test_on_user_turns_on_what_so_keeps_off(hass, init_solar_optimizer_central_config):
    """2. No surplus, SO keeps the device off, the user turns it on: it stays on"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(NO_SURPLUS)
    assert not home.is_on("pump")

    await home.user_turns("pump", True)
    for _ in range(3):
        await home.cycle(NO_SURPLUS, advance=600)
        assert home.is_on("pump")
        assert home.overridden("pump")


async def test_on_user_puts_back_releases_override(hass, init_solar_optimizer_central_config):
    """3. The user puts the device back as SO wanted: the override is released and SO
    decides again at the next cycle"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(SURPLUS)
    await home.user_turns("pump", False)
    await home.cycle(SURPLUS)
    assert home.overridden("pump")

    await home.user_turns("pump", True)
    await home.cycle(SURPLUS)
    assert not home.overridden("pump") and home.enabled("pump")

    # SO manages it again: no surplus any more, it turns it off
    await home.cycle(NO_SURPLUS, advance=600)
    assert not home.is_on("pump")
    assert not home.overridden("pump")


async def test_on_raz_time_releases_override_without_retrigger(hass, init_solar_optimizer_central_config):
    """4. At raz_time the override is released, SO decides at the next cycle and the
    override is not triggered again"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(SURPLUS)
    await home.user_turns("pump", False)
    await home.cycle(SURPLUS)
    assert home.overridden("pump")

    await home.coordinator._async_on_raz_time()
    await hass.async_block_till_done()
    assert not home.overridden("pump") and home.enabled("pump")

    for _ in range(3):
        await home.cycle(SURPLUS, advance=600)
        assert home.is_on("pump")  # SO turns it back on with the surplus
        assert not home.overridden("pump") and home.enabled("pump")


async def test_on_enable_or_clear_override_releases_without_retrigger(hass, init_solar_optimizer_central_config):
    """5. Turning Enable back on, or the clear_override action, releases the override
    and it is not triggered again"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(NO_SURPLUS)
    await home.user_turns("pump", True)
    await home.cycle(NO_SURPLUS)
    assert home.overridden("pump")

    enable = search_entity(hass, "switch.enable_solar_optimizer_pump", SWITCH_DOMAIN)
    await enable.async_turn_on()
    await hass.async_block_till_done()
    assert not home.overridden("pump")
    for _ in range(2):
        await home.cycle(NO_SURPLUS, advance=600)
        assert not home.is_on("pump")  # SO manages it again: no surplus, off
        assert not home.overridden("pump") and home.enabled("pump")

    await home.user_turns("pump", True)
    await home.cycle(NO_SURPLUS)
    assert home.overridden("pump")
    await hass.services.async_call(DOMAIN, "clear_override", {"device_id": "pump"}, blocking=True)
    await hass.async_block_till_done()
    assert not home.overridden("pump")
    await home.cycle(NO_SURPLUS, advance=600)
    assert not home.is_on("pump") and not home.overridden("pump")


async def test_on_user_change_during_so_waiting_window(hass, init_solar_optimizer_central_config):
    """6. The user turns off the device 5 s after SO turned it on, during its minimal on
    duration (18 s). The detection waits for the end of that window, and meanwhile SO
    does not turn it back on: then the override is detected and kept"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(SURPLUS)
    assert home.is_on("pump")

    home.advance(5)
    await home.user_turns("pump", False)
    await home.cycle(SURPLUS, advance=5)  # still in the window
    assert not home.is_on("pump")

    await home.cycle(SURPLUS, advance=60)  # window over
    assert not home.is_on("pump")
    assert home.overridden("pump")
    await home.cycle(SURPLUS, advance=600)
    assert not home.is_on("pump") and home.overridden("pump")


@pytest.mark.parametrize("base, user_turns_on", [(SURPLUS, False), (NO_SURPLUS, True)])
async def test_on_user_uses_so_switch(hass, init_solar_optimizer_central_config, base, user_turns_on):
    """7. Same as 1 and 2 through the Solar Optimizer switch instead of the device"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(base)
    assert home.is_on("pump") is not user_turns_on

    await home.user_turns("pump", user_turns_on, via_so_switch=True)
    assert home.overridden("pump")
    for _ in range(2):
        await home.cycle(base, advance=600)
        assert home.is_on("pump") is user_turns_on and home.overridden("pump")


# ---------------------------------------------------------------------------
# Respect manual changes = OFF: behavior from before the feature
# ---------------------------------------------------------------------------


async def test_off_so_turns_back_on(hass, init_solar_optimizer_central_config):
    """8. SO turned the device on, the user turns it off: SO turns it back on"""
    home = await make_home(hass, {"pump": False})
    await home.cycle(SURPLUS)
    await home.user_turns("pump", False)
    await home.cycle(SURPLUS)
    assert home.is_on("pump")
    assert not home.overridden("pump") and home.enabled("pump")


async def test_off_so_turns_back_off(hass, init_solar_optimizer_central_config):
    """9. No surplus, the user turns the device on (the EV plugged in): SO turns it off"""
    home = await make_home(hass, {"pump": False})
    await home.cycle(NO_SURPLUS)
    await home.user_turns("pump", True)
    await home.cycle(NO_SURPLUS)
    assert not home.is_on("pump")
    assert not home.overridden("pump") and home.enabled("pump")


async def test_off_so_switch_is_reverted(hass, init_solar_optimizer_central_config):
    """10. Same through the Solar Optimizer switch: reverted at the next cycle"""
    home = await make_home(hass, {"pump": False})
    await home.cycle(SURPLUS)
    await home.user_turns("pump", False, via_so_switch=True)
    assert not home.overridden("pump") and home.enabled("pump")
    await home.cycle(SURPLUS)
    assert home.is_on("pump")
    assert not home.overridden("pump")


async def test_respect_turned_off_with_active_override(hass, init_solar_optimizer_central_config):
    """11. An override is active and Respect manual changes is turned off: the override
    is cleared and from then on the device behaves exactly as before the feature"""
    home = await make_home(hass, {"pump": True})
    await home.cycle(SURPLUS)
    await home.user_turns("pump", False)
    await home.cycle(SURPLUS)
    assert home.overridden("pump") and not home.enabled("pump")

    await home.set_respect("pump", False)
    assert not home.overridden("pump") and home.enabled("pump")

    await home.cycle(SURPLUS)
    assert home.is_on("pump")  # SO turns it back on, as before the feature
    await home.user_turns("pump", False)
    await home.cycle(SURPLUS)
    assert home.is_on("pump") and not home.overridden("pump")  # and again


# ---------------------------------------------------------------------------
# Isolation between devices
# ---------------------------------------------------------------------------


async def test_devices_are_independent(hass, init_solar_optimizer_central_config):
    """The pump respects manual changes, the heater does not. The user turns both off:
    only the pump is overridden, the heater is turned back on. Releasing or changing the
    pump never changes the heater"""
    home = await make_home(hass, {"pump": True, "heater": False})
    await home.cycle(2 * SURPLUS)
    assert home.is_on("pump") and home.is_on("heater")

    await home.user_turns("pump", False)
    await home.user_turns("heater", False)
    await home.cycle(2 * SURPLUS)
    assert not home.is_on("pump") and home.overridden("pump") and not home.enabled("pump")
    assert home.is_on("heater") and not home.overridden("heater") and home.enabled("heater")
    assert home.devices["heater"].respect_manual_changes is False

    # turning the heater's switch on does not touch the pump, and vice versa
    await home.set_respect("heater", True)
    assert home.overridden("pump") and home.devices["pump"].respect_manual_changes
    await home.set_respect("pump", False)
    assert not home.overridden("pump")
    assert home.devices["heater"].respect_manual_changes and not home.overridden("heater") and home.enabled("heater")

    # an override of the heater does not touch the pump, which SO manages
    await home.cycle(2 * SURPLUS)
    await home.user_turns("heater", False)
    await home.cycle(2 * SURPLUS)
    assert home.overridden("heater") and not home.is_on("heater")
    assert home.is_on("pump") and not home.overridden("pump") and home.enabled("pump")
