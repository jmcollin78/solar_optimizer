"""Tests for the GreedyPriorityAlgorithm."""

from datetime import datetime, timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.core import State

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .commons import (
    SideEffects,
    create_managed_device,
    search_entity,
)
from custom_components.solar_optimizer.const import (
    get_tz,
    DOMAIN,
    CONF_NAME,
    CONF_DEVICE_TYPE,
    CONF_DEVICE_CENTRAL,
    CONF_DEVICE,
    CONF_POWERED_DEVICE,
    CONF_POWER_CONSUMPTION_ENTITY_ID,
    CONF_POWER_PRODUCTION_ENTITY_ID,
    CONF_SELL_COST_ENTITY_ID,
    CONF_BUY_COST_ENTITY_ID,
    CONF_SELL_TAX_PERCENT_ENTITY_ID,
    CONF_SMOOTH_PRODUCTION,
    CONF_BATTERY_SOC_ENTITY_ID,
    CONF_REFRESH_PERIOD_SEC,
    CONF_RAZ_TIME,
    CONF_ENTITY_ID,
    CONF_POWER_MAX,
    CONF_POWER_MIN,
    CONF_POWER_STEP,
    CONF_CHECK_USABLE_TEMPLATE,
    CONF_DURATION_MIN,
    CONF_DURATION_STOP_MIN,
    CONF_ACTION_MODE,
    CONF_ACTION_MODE_ACTION,
    CONF_ACTIVATION_SERVICE,
    CONF_DEACTIVATION_SERVICE,
    CONF_BATTERY_SOC_THRESHOLD,
    CONF_ALGORITHM_TYPE,
    ALGORITHM_GREEDY_PRIORITY,
    PRIORITY_MAP,
    PRIORITY_WEIGHTS,
    PRIORITY_WEIGHT_MAP,
    PRIORITY_WEIGHT_NULL,
    PRIORITY_WEIGHT_HIGH,
    PRIORITY_WEIGHT_VERY_HIGH,
    PRIORITY_VERY_HIGH,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_VERY_LOW,
)
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

CENTRAL_CONFIG_DATA = {
    CONF_NAME: "Central",
    CONF_REFRESH_PERIOD_SEC: 60,
    CONF_DEVICE_TYPE: CONF_DEVICE_CENTRAL,
    CONF_POWER_CONSUMPTION_ENTITY_ID: "sensor.fake_power_consumption",
    CONF_POWER_PRODUCTION_ENTITY_ID: "sensor.fake_power_production",
    CONF_SELL_COST_ENTITY_ID: "input_number.fake_sell_cost",
    CONF_BUY_COST_ENTITY_ID: "input_number.fake_buy_cost",
    CONF_SELL_TAX_PERCENT_ENTITY_ID: "input_number.fake_sell_tax_percent",
    CONF_SMOOTH_PRODUCTION: False,
    CONF_BATTERY_SOC_ENTITY_ID: "sensor.fake_battery_soc",
    CONF_RAZ_TIME: "05:00",
    CONF_ALGORITHM_TYPE: ALGORITHM_GREEDY_PRIORITY,
}

BASE_SIDE_EFFECTS = {
    "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 0.07),
    "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 0.22),
    "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
    "sensor.fake_battery_soc": State("sensor.fake_battery_soc", 100),
}


def _device_entry(name, unique_id, power_max, duration_min=0.1, duration_stop_min=0.1, battery_soc_threshold=0):
    return MockConfigEntry(
        domain=DOMAIN,
        title=name,
        unique_id=unique_id,
        data={
            CONF_NAME: name,
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: f"input_boolean.{unique_id}",
            CONF_POWER_MAX: power_max,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: duration_min,
            CONF_DURATION_STOP_MIN: duration_stop_min,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_BATTERY_SOC_THRESHOLD: battery_soc_threshold,
        },
    )


async def _setup_central(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Central",
        unique_id="centralUniqueId",
        data=CENTRAL_CONFIG_DATA,
    )
    await create_managed_device(hass, entry, "centralUniqueId")
    coordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None
    assert coordinator.is_central_config_done
    return coordinator


def _side_effects(production, consumption, extra=None):
    se = dict(BASE_SIDE_EFFECTS)
    se["sensor.fake_power_production"] = State("sensor.fake_power_production", production)
    se["sensor.fake_power_consumption"] = State("sensor.fake_power_consumption", consumption)
    if extra:
        se.update(extra)
    return SideEffects(se, State("unknown.entity", "unknown"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_greedy_algo_is_selected(hass: HomeAssistant):
    """The coordinator should instantiate GreedyPriorityAlgorithm when configured."""
    from custom_components.solar_optimizer.greedy_priority_algo import GreedyPriorityAlgorithm

    coordinator = await _setup_central(hass)
    assert isinstance(coordinator._algo, GreedyPriorityAlgorithm)


async def test_greedy_turns_on_with_sufficient_excess(hass: HomeAssistant):
    """Device turns on when solar excess covers its power requirement."""
    coordinator = await _setup_central(hass)

    entry_a = _device_entry("Device A", "device_a", power_max=1000)
    device_a = await create_managed_device(hass, entry_a, "device_a")
    assert device_a is not None

    # 2000W solar, 200W house load → 1800W excess, device needs 1000W
    se = _side_effects(production=2000, consumption=200)
    with patch("homeassistant.core.StateMachine.get", side_effect=se.get_side_effects()):
        data = await coordinator._async_update_data()
        await hass.async_block_till_done()

    assert data["device_a"].is_waiting is True  # just turned on → in cooldown
    assert data["device_a"].requested_power == 1000
    assert data["total_power"] == 1000


async def test_greedy_stays_off_insufficient_excess(hass: HomeAssistant):
    """Device stays off when solar excess is insufficient."""
    coordinator = await _setup_central(hass)

    entry_a = _device_entry("Device A", "device_a", power_max=1000)
    device_a = await create_managed_device(hass, entry_a, "device_a")
    assert device_a is not None

    # 500W solar, 400W house load → 100W excess, device needs 1000W
    se = _side_effects(production=500, consumption=400)
    with patch("homeassistant.core.StateMachine.get", side_effect=se.get_side_effects()):
        data = await coordinator._async_update_data()
        await hass.async_block_till_done()

    assert data["device_a"].is_waiting is False
    assert data["device_a"].requested_power == 0
    assert data["total_power"] == 0


async def test_greedy_priority_ordering(hass: HomeAssistant):
    """With limited solar, highest-priority device wins over lower-priority one."""
    coordinator = await _setup_central(hass)

    # Device A: LOW priority (int=8), 800W
    entry_a = _device_entry("Device A", "device_a", power_max=800)
    device_a = await create_managed_device(hass, entry_a, "device_a")

    # Device B: VERY_HIGH priority (int=1), 800W
    entry_b = _device_entry("Device B", "device_b", power_max=800)
    device_b = await create_managed_device(hass, entry_b, "device_b")

    # Set priorities
    priority_a = search_entity(hass, "select.solar_optimizer_priority_device_a", SELECT_DOMAIN)
    priority_b = search_entity(hass, "select.solar_optimizer_priority_device_b", SELECT_DOMAIN)
    priority_a.select_option(PRIORITY_LOW)
    priority_b.select_option(PRIORITY_VERY_HIGH)
    await hass.async_block_till_done()

    # Solar 1000W, house 200W → 800W excess: exactly fits one 800W device
    se = _side_effects(production=1000, consumption=200)
    with patch("homeassistant.core.StateMachine.get", side_effect=se.get_side_effects()):
        data = await coordinator._async_update_data()
        await hass.async_block_till_done()

    # VERY_HIGH priority device B should be on, LOW priority device A off
    assert data["device_b"].is_waiting is True   # turned on
    assert data["device_a"].is_waiting is False  # stayed off
    assert data["total_power"] == 800


async def test_greedy_load_shedding_enables_higher_priority(hass: HomeAssistant):
    """High-priority device causes low-priority device to be shed.

    Two-cycle test: A turns on in cycle 1, then B (higher priority) sheds A in cycle 2.
    """
    coordinator = await _setup_central(hass)

    pw_entity = search_entity(hass, "select.solar_optimizer_priority_weight", SELECT_DOMAIN)
    pw_entity.select_option(PRIORITY_WEIGHT_HIGH)
    await hass.async_block_till_done()

    # Device A: LOW priority, 600W, very short cooldown
    entry_a = _device_entry("Device A", "device_a", power_max=600, duration_min=0.1, duration_stop_min=0.1)
    device_a = await create_managed_device(hass, entry_a, "device_a")

    # Device B: VERY_HIGH priority, 800W
    entry_b = _device_entry("Device B", "device_b", power_max=800, duration_min=0.1, duration_stop_min=0.1)
    device_b = await create_managed_device(hass, entry_b, "device_b")

    priority_a = search_entity(hass, "select.solar_optimizer_priority_device_a", SELECT_DOMAIN)
    priority_b = search_entity(hass, "select.solar_optimizer_priority_device_b", SELECT_DOMAIN)
    priority_a.select_option(PRIORITY_LOW)
    priority_b.select_option(PRIORITY_VERY_HIGH)
    await hass.async_block_till_done()

    # Cycle 1: Solar=700W, house=100W → 600W excess. Only A (600W LOW) fits exactly.
    # B (800W VERY_HIGH) can't fit (0W left) and nothing to shed yet (A just turned on).
    now = datetime.now(tz=get_tz(hass))
    device_a._set_now(now)
    device_b._set_now(now)
    se1 = _side_effects(production=700, consumption=100)
    with patch("homeassistant.core.StateMachine.get", side_effect=se1.get_side_effects()):
        data1 = await coordinator._async_update_data()
        await hass.async_block_till_done()
    assert data1["total_power"] == 600  # A turned on

    # Advance time past cooldown so devices are no longer waiting
    now = now + timedelta(minutes=1)
    device_a._set_now(now)
    device_b._set_now(now)

    # Cycle 2: A is ON (mock its HA entity as "on" so is_active=True).
    # Solar=1000W, measured consumption = house(100) + A(600) = 700W.
    # excess = 1000 - 700 = 300W. B needs 800W → can't turn on directly.
    # But shed A (600W): 300 + 600 = 900W >= 800W → B turns on, A is shed.
    se2 = _side_effects(
        production=1000,
        consumption=700,
        extra={"input_boolean.device_a": State("input_boolean.device_a", "on")},
    )
    with patch("homeassistant.core.StateMachine.get", side_effect=se2.get_side_effects()):
        data2 = await coordinator._async_update_data()
        await hass.async_block_till_done()

    assert data2["total_power"] == 800   # B on, A shed
    sol = {s["name"]: s for s in data2["best_solution"]}
    assert sol["Device B"]["state"] is True
    assert sol["Device A"]["state"] is False


async def test_greedy_no_shedding_when_priority_weight_zero(hass: HomeAssistant):
    """Load shedding is disabled when priority_weight is None/zero.

    Two-cycle: A turns on cycle 1, then in cycle 2 B cannot shed A because priority_weight=0.
    """
    coordinator = await _setup_central(hass)

    pw_entity = search_entity(hass, "select.solar_optimizer_priority_weight", SELECT_DOMAIN)
    pw_entity.select_option(PRIORITY_WEIGHT_NULL)
    await hass.async_block_till_done()
    assert coordinator.priority_weight == 0

    entry_a = _device_entry("Device A", "device_a", power_max=600, duration_min=0.1, duration_stop_min=0.1)
    device_a = await create_managed_device(hass, entry_a, "device_a")

    entry_b = _device_entry("Device B", "device_b", power_max=800, duration_min=0.1, duration_stop_min=0.1)
    device_b = await create_managed_device(hass, entry_b, "device_b")

    priority_a = search_entity(hass, "select.solar_optimizer_priority_device_a", SELECT_DOMAIN)
    priority_b = search_entity(hass, "select.solar_optimizer_priority_device_b", SELECT_DOMAIN)
    priority_a.select_option(PRIORITY_LOW)
    priority_b.select_option(PRIORITY_VERY_HIGH)
    await hass.async_block_till_done()

    # Cycle 1: A turns on (600W fits in 600W excess)
    now = datetime.now(tz=get_tz(hass))
    device_a._set_now(now)
    device_b._set_now(now)
    se1 = _side_effects(production=700, consumption=100)
    with patch("homeassistant.core.StateMachine.get", side_effect=se1.get_side_effects()):
        await coordinator._async_update_data()
        await hass.async_block_till_done()

    # Advance past cooldown
    now = now + timedelta(minutes=1)
    device_a._set_now(now)
    device_b._set_now(now)

    # Cycle 2: A is ON. With shedding disabled (priority_weight=0), B cannot displace A.
    # A stays on, B stays off.
    se2 = _side_effects(
        production=1000,
        consumption=700,
        extra={"input_boolean.device_a": State("input_boolean.device_a", "on")},
    )
    with patch("homeassistant.core.StateMachine.get", side_effect=se2.get_side_effects()):
        data2 = await coordinator._async_update_data()
        await hass.async_block_till_done()

    sol = {s["name"]: s for s in data2["best_solution"]}
    assert sol["Device A"]["state"] is True   # stays on
    assert sol["Device B"]["state"] is False  # cannot shed without priority_weight


async def test_greedy_turns_off_on_production_drop(hass: HomeAssistant):
    """Active device is turned off when production drops below consumption."""
    coordinator = await _setup_central(hass)

    entry_a = _device_entry("Device A", "device_a", power_max=1000, duration_min=0.3, duration_stop_min=0.1)
    device_a = await create_managed_device(hass, entry_a, "device_a")
    assert device_a is not None

    # Cycle 1: enough solar → device on (is_waiting=True because duration_min=0.3)
    now = datetime.now(tz=get_tz(hass))
    device_a._set_now(now)
    se = _side_effects(production=2000, consumption=200)
    with patch("homeassistant.core.StateMachine.get", side_effect=se.get_side_effects()):
        data = await coordinator._async_update_data()
        await hass.async_block_till_done()
    assert data["device_a"].is_waiting is True  # turned on, in cooldown

    # Advance past cooldown so device can be turned off
    now = now + timedelta(minutes=1)
    device_a._set_now(now)

    # Cycle 2: solar drops → measured consumption = house(200) + device(1000) = 1200W
    # excess = 500 - 1200 = -700W (deficit) → device should be turned off
    se2 = _side_effects(production=500, consumption=1200)
    with patch("homeassistant.core.StateMachine.get", side_effect=se2.get_side_effects()):
        data2 = await coordinator._async_update_data()
        await hass.async_block_till_done()

    assert data2["total_power"] == 0
    sol = {s["name"]: s for s in data2["best_solution"]}
    assert sol["Device A"]["state"] is False


async def test_greedy_multiple_devices_all_fit(hass: HomeAssistant):
    """All devices turn on when there is enough solar for all of them."""
    coordinator = await _setup_central(hass)

    entry_a = _device_entry("Device A", "device_a", power_max=500, duration_min=0.3, duration_stop_min=0.1)
    entry_b = _device_entry("Device B", "device_b", power_max=700, duration_min=0.3, duration_stop_min=0.1)
    device_a = await create_managed_device(hass, entry_a, "device_a")
    device_b = await create_managed_device(hass, entry_b, "device_b")

    # 2000W solar, 100W house → 1900W excess, both devices need 500+700=1200W
    se = _side_effects(production=2000, consumption=100)
    with patch("homeassistant.core.StateMachine.get", side_effect=se.get_side_effects()):
        data = await coordinator._async_update_data()
        await hass.async_block_till_done()

    # Both turned on → in cooldown (is_waiting=True with duration_min=0.3)
    assert data["device_a"].is_waiting is True
    assert data["device_b"].is_waiting is True
    assert data["total_power"] == 1200


async def test_greedy_no_solar_nothing_turns_on(hass: HomeAssistant):
    """No device turns on when there is zero solar production."""
    coordinator = await _setup_central(hass)

    entry_a = _device_entry("Device A", "device_a", power_max=1000)
    device_a = await create_managed_device(hass, entry_a, "device_a")

    se = _side_effects(production=0, consumption=300)
    with patch("homeassistant.core.StateMachine.get", side_effect=se.get_side_effects()):
        data = await coordinator._async_update_data()
        await hass.async_block_till_done()

    assert data["device_a"].is_waiting is False
    assert data["total_power"] == 0
