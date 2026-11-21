""" Device with power Unit test module"""
from unittest.mock import AsyncMock, call, patch, PropertyMock, ANY
from datetime import datetime, timedelta

from homeassistant.setup import async_setup_component
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN


from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.managed_device import ACTION_ACTIVATE, ACTION_DEACTIVATE, ACTION_CHANGE_POWER


async def test_event_change_power_uses_explicit_setpoint(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Transmit the explicit setpoint without taking ownership of the prior plan."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_EVENT,
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None
    device.set_requested_power(100)
    device._current_power = 100
    announcements = []
    commands = []
    hass.bus.async_listen(EVENT_TYPE_SOLAR_OPTIMIZER_ACTION, announcements.append)
    hass.bus.async_listen(EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER, commands.append)

    await device.change_requested_power(600)
    await hass.async_block_till_done()

    assert len(announcements) == len(commands) == 1
    assert announcements[0].data == {
        "device_name": "Power Device A",
        "entity_id": "input_boolean.fake_device_a",
        "action": ACTION_CHANGE_POWER,
        "service": None,
        "requested_power": 600,
    }
    assert commands[0].data == {
        "action_type": ACTION_CHANGE_POWER,
        "requested_power": 600,
        "current_power": 100,
        "entity_id": "input_boolean.fake_device_a",
    }
    context = device.last_context
    assert context is not None
    assert announcements[0].context is commands[0].context is context
    assert context.origin_event is announcements[0]
    assert device.current_power == 600
    assert device.requested_power == 100


@pytest.mark.parametrize("action_mode", [CONF_ACTION_MODE_EVENT, CONF_ACTION_MODE_ACTION])
@pytest.mark.parametrize(
    "action_type, requested_power, expected_power",
    [
        (ACTION_ACTIVATE, None, 100),
        (ACTION_ACTIVATE, 600, 600),
        (ACTION_DEACTIVATE, 0, 0),
        (ACTION_CHANGE_POWER, None, 100),
        (ACTION_CHANGE_POWER, 600, 600),
    ],
)
async def test_apply_action_uses_normalized_setpoint(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    action_mode,
    action_type,
    requested_power,
    expected_power,
):
    """Preserve the fallback and transmit explicit power for both action modes."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: action_mode,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None
    device.set_requested_power(100)
    device._current_power = 100
    event_mode = action_mode == CONF_ACTION_MODE_EVENT
    change_power = action_type == ACTION_CHANGE_POWER
    entity_id = data[CONF_POWER_ENTITY_ID] if change_power and not event_mode else data[CONF_ENTITY_ID]
    service = {
        ACTION_ACTIVATE: data[CONF_ACTIVATION_SERVICE],
        ACTION_DEACTIVATE: data[CONF_DEACTIVATION_SERVICE],
        ACTION_CHANGE_POWER: data[CONF_CHANGE_POWER_SERVICE],
    }[action_type]
    event_type = EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER if event_mode or change_power else EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE
    announcements = []
    commands = []
    hass.bus.async_listen(EVENT_TYPE_SOLAR_OPTIMIZER_ACTION, announcements.append)
    hass.bus.async_listen(event_type, commands.append)

    with patch("homeassistant.core.ServiceRegistry.async_call", new_callable=AsyncMock) as service_call:
        if action_type == ACTION_ACTIVATE:
            await device.activate(requested_power)
        elif action_type == ACTION_DEACTIVATE:
            await device.deactivate()
        else:
            await device.change_requested_power(requested_power)
        await hass.async_block_till_done()

    context = device.last_context
    assert context is not None
    assert len(announcements) == len(commands) == 1
    assert announcements[0].data == {
        "device_name": "Power Device A",
        "entity_id": entity_id,
        "action": action_type,
        "service": None if event_mode else service,
        "requested_power": expected_power,
    }
    assert commands[0].data == {
        "action_type": action_type,
        "requested_power": expected_power,
        "current_power": 100,
        "entity_id": entity_id,
    }
    assert announcements[0].context is commands[0].context is context
    assert context.origin_event is announcements[0]
    if event_mode:
        service_call.assert_not_awaited()
    else:
        domain, action = service.split("/")
        service_call.assert_awaited_once_with(
            domain,
            action,
            service_data={"value": expected_power} if change_power else {},
            target={"entity_id": entity_id},
            context=context,
        )
    assert device.current_power == expected_power
    assert device.requested_power == 100


async def test_offpeak_event_setpoint_is_emitted_once(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Emit the off-peak setpoint before updating the plan, then stay stable."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_EVENT,
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None
    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", "0")
    hass.states.async_set("sensor.fake_power_production", "0")
    hass.states.async_set("input_number.fake_sell_cost", "1")
    hass.states.async_set("input_number.fake_buy_cost", "1")
    hass.states.async_set("input_number.fake_sell_tax_percent", "0")
    device.set_requested_power(100)
    device._current_power = 100
    announcements = []
    commands = []
    hass.bus.async_listen(EVENT_TYPE_SOLAR_OPTIMIZER_ACTION, announcements.append)
    hass.bus.async_listen(EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER, commands.append)
    solution = [{"name": "Power Device A", "requested_power": 100, "state": True}]

    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=True
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(device, "set_current_power_with_device_state"):
        await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert len(announcements) == len(commands) == 1
        assert announcements[0].data["requested_power"] == 600
        assert commands[0].data == {
            "action_type": ACTION_CHANGE_POWER,
            "requested_power": 600,
            "current_power": 100,
            "entity_id": "input_boolean.fake_device_a",
        }
        assert announcements[0].context is commands[0].context is device.last_context
        assert device.current_power == device.requested_power == 600

        announcements.clear()
        commands.clear()
        await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert announcements == commands == []
        assert device.current_power == device.requested_power == 600
        assert solution == [{"name": "Power Device A", "requested_power": 100, "state": True}]


@pytest.mark.parametrize("offpeak_power, expected_power", [(600, 600), ("{{ 600 }}", 600), (None, 1000)])
async def test_offpeak_forcing_sets_variable_device_power(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    offpeak_power,
    expected_power,
):
    """Off-peak forcing explicitly applies configured power or the power-max fallback."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    if offpeak_power is not None:
        data[CONF_OFFPEAK_POWER] = offpeak_power
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    device._set_now(datetime(2024, 11, 10, 23, 0, tzinfo=get_tz(hass)))
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    solution = [{"name": "Power Device A", "requested_power": 0, "state": False}]
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=False
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "activate", new_callable=AsyncMock
    ) as activate, patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        await coordinator._async_update_data()

    activate.assert_awaited_once_with(expected_power)
    change_power.assert_awaited_once_with(expected_power)


async def test_offpeak_power_is_rejected_for_standard_device(hass: HomeAssistant, init_solar_optimizer_central_config):
    """Injected off-peak power is invalid for a standard on/off device."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Equipement A",
        unique_id="eqtA",
        data={
            CONF_NAME: "Equipement A",
            CONF_DEVICE_TYPE: CONF_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_MAX: 1000,
            CONF_OFFPEAK_POWER: 600,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 0,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        },
    )

    device = await create_managed_device(hass, entry, "equipement_a")
    assert device is None


async def test_invalid_offpeak_power_template_does_not_interrupt_cycle(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """An invalid resolved off-peak power skips only the affected device cycle."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: "{{ states('input_number.offpeak_power') }}",
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    hass.states.async_set("input_number.offpeak_power", 600)
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)
    hass.states.async_set("input_number.offpeak_power", "invalid")

    solution = [{"name": "Power Device A", "requested_power": 0, "state": False}]
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=False
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "activate", new_callable=AsyncMock
    ) as activate, patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        calculated_data = await coordinator._async_update_data()

    activate.assert_not_awaited()
    change_power.assert_not_awaited()
    assert calculated_data["best_solution"] == solution


async def test_offpeak_forcing_overrides_active_algorithm_power(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """AC-002: an active solution asking power_min must not override offpeak_power."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    # The device is already active and the last planned power is power_min (100),
    # while the algorithm asks power_min and the solution is active.
    device.set_requested_power(100)
    solution = [{"name": "Power Device A", "requested_power": 100, "state": True}]
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=True
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "set_current_power_with_device_state"
    ), patch.object(
        device, "activate", new_callable=AsyncMock
    ) as activate, patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        device._current_power = 100
        await coordinator._async_update_data()

    activate.assert_not_awaited()
    change_power.assert_awaited_once_with(600)
    assert change_power.await_args_list[0] != call(100)


async def test_offpeak_forcing_updates_planning_after_algorithm_power_change(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Keep the plan aligned outside forcing so off-peak entry applies its target."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", "0")
    hass.states.async_set("sensor.fake_power_production", "0")
    hass.states.async_set("input_number.fake_sell_cost", "1")
    hass.states.async_set("input_number.fake_buy_cost", "1")
    hass.states.async_set("input_number.fake_sell_tax_percent", "0")

    cycles = [
        (False, False, 600, 0, 600, 600),
        (True, False, 300, 600, 300, 300),
        (True, True, 300, 300, 600, 600),
        (True, True, 300, 600, 600, None),
    ]
    for is_active, forcing, algorithm_power, measured_power, planned_power, command_power in cycles:
        solution = [{"name": "Power Device A", "requested_power": algorithm_power, "state": True}]
        with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
            type(device), "is_active", new_callable=PropertyMock, return_value=is_active
        ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=forcing), patch.object(
            device, "set_current_power_with_device_state"
        ), patch.object(
            device, "activate", new_callable=AsyncMock
        ) as activate, patch.object(
            device, "deactivate", new_callable=AsyncMock
        ) as deactivate, patch.object(
            device, "change_requested_power", new_callable=AsyncMock
        ) as change_power:
            device._current_power = measured_power
            await coordinator._async_update_data()

        if is_active:
            activate.assert_not_awaited()
        else:
            activate.assert_awaited_once_with(600)
        deactivate.assert_not_awaited()
        if command_power is None:
            change_power.assert_not_awaited()
        else:
            change_power.assert_awaited_once_with(command_power)
        assert device.requested_power == planned_power


async def test_offpeak_forcing_no_reemission_when_already_applied(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """REQ-009 / AC-013: no power command is re-issued while the setpoint is stable."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    device.set_requested_power(600)
    solution = [{"name": "Power Device A", "requested_power": 600, "state": True}]
    for _ in range(3):
        with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
            type(device), "is_active", new_callable=PropertyMock, return_value=True
        ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
            device, "set_current_power_with_device_state"
        ), patch.object(
            device, "activate", new_callable=AsyncMock
        ) as activate, patch.object(
            device, "change_requested_power", new_callable=AsyncMock
        ) as change_power:
            device._current_power = 600
            await coordinator._async_update_data()

        activate.assert_not_awaited()
        change_power.assert_not_awaited()
        assert device.requested_power == 600


async def test_offpeak_forcing_uses_planned_value_when_measurement_unavailable(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """R2 / AC-013: with an unavailable measurement (current_power falls back to
    power_min), the planned value is used and no re-issuance happens."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    device.set_requested_power(600)
    solution = [{"name": "Power Device A", "requested_power": 100, "state": True}]
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=True
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "set_current_power_with_device_state"
    ), patch.object(
        device, "activate", new_callable=AsyncMock
    ) as activate, patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        # Simulate the power_min fallback of set_current_power_with_device_state.
        device._current_power = 100
        await coordinator._async_update_data()

    activate.assert_not_awaited()
    change_power.assert_not_awaited()


async def test_offpeak_dynamic_template_resampled_once_per_cycle(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """AC-005 / Q-003: a template offpeak_power is re-sampled once per cycle."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: "{{ states('input_number.offpeak_power') | int }}",
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 0,
        CONF_OFFPEAK_TIME: "23:00",
    }
    hass.states.async_set("input_number.offpeak_power", 600)
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    solution = [{"name": "Power Device A", "requested_power": 100, "state": True}]

    # Cycle 1: template renders 600.
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=True
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "set_current_power_with_device_state"
    ), patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        device._current_power = 100
        await coordinator._async_update_data()
    change_power.assert_awaited_once_with(600)

    # Cycle 2: template now renders 800 -> re-sampled once, applied once.
    hass.states.async_set("input_number.offpeak_power", 800)
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=True
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "set_current_power_with_device_state"
    ), patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        device._current_power = 600
        await coordinator._async_update_data()
    change_power.assert_awaited_once_with(800)


async def test_offpeak_forcing_logs_decision(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
    caplog,
):
    """AC-014: the off-peak setpoint decision is logged with device and target."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    device.set_requested_power(600)
    solution = [{"name": "Power Device A", "requested_power": 100, "state": True}]
    with caplog.at_level("DEBUG", logger="custom_components.solar_optimizer.coordinator"):
        with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
            type(device), "is_active", new_callable=PropertyMock, return_value=True
        ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
            device, "set_current_power_with_device_state"
        ), patch.object(
            device, "change_requested_power", new_callable=AsyncMock
        ):
            device._current_power = 600
            await coordinator._async_update_data()

    assert "off-peak setpoint imposed" in caplog.text
    assert "Power Device A" in caplog.text
    assert "600" in caplog.text


async def test_offpeak_forcing_does_not_affect_switch_device(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """REQ-007 / AC-010: a switch device is never given an off-peak power."""
    power_data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    switch_data = {
        CONF_NAME: "Equipement B",
        CONF_DEVICE_TYPE: CONF_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_b",
        CONF_POWER_MAX: 1000,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    power_device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=power_data),
        "power_device_a",
    )
    switch_device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Equipement B", unique_id="eqtB", data=switch_data),
        "equipement_b",
    )
    assert power_device is not None
    assert switch_device is not None
    assert switch_device.can_change_power is False

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    power_device.set_requested_power(600)
    solution = [
        {"name": "Power Device A", "requested_power": 100, "state": True},
        {"name": "Equipement B", "requested_power": 0, "state": True},
    ]
    # NOTE: PowerDevice and switch devices share the same class, so class-level
    # PropertyMock patches would overwrite each other. The switch is therefore
    # checked in a separate cycle below.
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(power_device), "is_active", new_callable=PropertyMock, return_value=True
    ), patch.object(type(power_device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        power_device, "set_current_power_with_device_state"
    ), patch.object(
        power_device, "change_requested_power", new_callable=AsyncMock
    ) as power_change:
        power_device._current_power = 600
        await coordinator._async_update_data()

    power_change.assert_not_awaited()

    solution_switch = [{"name": "Equipement B", "requested_power": 0, "state": True}]
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution_switch, 0, 0)), patch.object(
        type(switch_device), "is_active", new_callable=PropertyMock, return_value=False
    ), patch.object(type(switch_device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        switch_device, "set_current_power_with_device_state"
    ), patch.object(
        switch_device, "activate", new_callable=AsyncMock
    ) as switch_activate, patch.object(
        switch_device, "change_requested_power", new_callable=AsyncMock
    ) as switch_change:
        await coordinator._async_update_data()

    switch_activate.assert_awaited_once_with(0)
    switch_change.assert_not_awaited()


async def test_offpeak_forcing_activates_inactive_device_with_setpoint(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """AC-001: an inactive variable device is activated with the off-peak setpoint,
    even when the algorithm solution is active with another power."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_OFFPEAK_POWER: 600,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
        CONF_MAX_ON_TIME_PER_DAY_MIN: 10,
        CONF_MIN_ON_TIME_PER_DAY_MIN: 5,
        CONF_OFFPEAK_TIME: "23:00",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None

    coordinator = SolarOptimizerCoordinator.get_coordinator()
    hass.states.async_set("sensor.fake_power_consumption", 0)
    hass.states.async_set("sensor.fake_power_production", 0)
    hass.states.async_set("input_number.fake_sell_cost", 1)
    hass.states.async_set("input_number.fake_buy_cost", 1)
    hass.states.async_set("input_number.fake_sell_tax_percent", 0)

    solution = [{"name": "Power Device A", "requested_power": 100, "state": True}]
    with patch.object(coordinator._algo, "recuit_simule", return_value=(solution, 0, 0)), patch.object(
        type(device), "is_active", new_callable=PropertyMock, return_value=False
    ), patch.object(type(device), "should_be_forced_offpeak", new_callable=PropertyMock, return_value=True), patch.object(
        device, "set_current_power_with_device_state"
    ), patch.object(
        device, "activate", new_callable=AsyncMock
    ) as activate, patch.object(
        device, "change_requested_power", new_callable=AsyncMock
    ) as change_power:
        device._current_power = 0
        await coordinator._async_update_data()

    activate.assert_awaited_once_with(600)
    change_power.assert_awaited_once_with(600)


async def test_offpeak_setpoint_validation(hass: HomeAssistant, init_solar_optimizer_central_config):
    """BR-003: offpeak_setpoint validates the value and falls back to power_max."""
    data = {
        CONF_NAME: "Power Device A",
        CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
        CONF_ENTITY_ID: "input_boolean.fake_device_a",
        CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
        CONF_POWER_MAX: 1000,
        CONF_POWER_MIN: 100,
        CONF_POWER_STEP: 100,
        CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
        CONF_DURATION_MIN: 0,
        CONF_DURATION_POWER_MIN: 0,
        CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
        CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
        CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
        CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
    }
    device = await create_managed_device(
        hass,
        MockConfigEntry(domain=DOMAIN, title="Power Device A", unique_id="powerA", data=data),
        "power_device_a",
    )
    assert device is not None
    # No offpeak_power configured -> fallback to power_max.
    assert device.offpeak_power_configured is False
    assert device.offpeak_setpoint == 1000
    assert device.offpeak_power == device.offpeak_setpoint


async def test_power_device(
    hass: HomeAssistant,
    init_solar_optimizer_central_config,
):
    """Testing power device functionality"""

    fake_device_a = await create_test_input_boolean(hass, "fake_device_a", "fake device a")
    assert fake_device_a is not None
    assert fake_device_a.state == STATE_OFF

    fake_amps_number = await create_test_input_number(hass, "fake_amps_number", "fake amps number")
    assert fake_amps_number is not None
    assert fake_amps_number.state == 0

    entry_a = MockConfigEntry(
        domain=DOMAIN,
        title="Power Device A",
        unique_id="powerDeviceAUniqueId",
        data={
            CONF_NAME: "Power Device A",
            CONF_DEVICE_TYPE: CONF_POWERED_DEVICE,
            CONF_ENTITY_ID: "input_boolean.fake_device_a",
            CONF_POWER_ENTITY_ID: "input_number.fake_amps_number",
            CONF_POWER_MAX: 1000,
            CONF_POWER_MIN: 100,
            CONF_POWER_STEP: 100,
            CONF_CHECK_USABLE_TEMPLATE: "{{ True }}",
            CONF_DURATION_MIN: 10,
            CONF_DURATION_STOP_MIN: 5,
            CONF_DURATION_POWER_MIN: 2,
            CONF_ACTION_MODE: CONF_ACTION_MODE_ACTION,
            CONF_ACTIVATION_SERVICE: "input_boolean/turn_on",
            CONF_DEACTIVATION_SERVICE: "input_boolean/turn_off",
            CONF_CHANGE_POWER_SERVICE: "input_number/set_value",
            CONF_CONVERT_POWER_DIVIDE_FACTOR: 10,
        },
    )

    device = await create_managed_device(
        hass,
        entry_a,
        "power_device_a",
    )
    assert device is not None
    assert device.name == "Power Device A"
    assert device.power_max == 1000
    assert device.power_min == 100
    assert device.power_step == 100
    assert device.power_entity_id == "input_number.fake_amps_number"
    assert device.duration_sec == 600
    assert device.duration_stop_sec == 300
    assert device.duration_power_sec == 120
    assert device._action_mode == CONF_ACTION_MODE_ACTION
    assert device._activation_service == "input_boolean/turn_on"
    assert device._deactivation_service == "input_boolean/turn_off"
    assert device._change_power_service == "input_number/set_value"
    assert device.convert_power_divide_factor == 10
    assert device.battery_soc_threshold == 0
    assert device.max_on_time_per_day_sec == 86400  # 60 * 24 * 60
    assert device.min_on_time_per_day_sec == 0
    assert device.offpeak_time == None
    assert device.entity_id == "input_boolean.fake_device_a"
    assert device.unique_id == "power_device_a"
    assert device.is_active is False
    assert device.is_usable is True
    assert device.can_change_power is True
    assert device.priority == 4

    # get the SO switch entity
    device_a_switch = search_entity(
        hass, "switch.solar_optimizer_power_device_a", SWITCH_DOMAIN
    )
    assert device_a_switch is not None

    # get the SO priority entity
    priority_weight_entity = search_entity(hass, "select.solar_optimizer_priority_weight", SELECT_DOMAIN)
    assert priority_weight_entity is not None
    assert priority_weight_entity.name == "Priority weight"
    assert priority_weight_entity.current_option == PRIORITY_WEIGHT_NULL
    assert priority_weight_entity.options == PRIORITY_WEIGHTS

    # 1. Test the next_date_available and next_date_available_power
    tz = get_tz(hass) # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
    assert (device.next_date_available.astimezone(tz) - now).total_seconds() < 1
    assert (device.next_date_available_power.astimezone(tz) - now).total_seconds() < 1

    coordinator = SolarOptimizerCoordinator.get_coordinator()

    side_effects = SideEffects(
        {
            "sensor.fake_power_consumption": State("sensor.fake_power_consumption", -500),
            "sensor.fake_power_production": State("sensor.fake_power_production", 500),
            "sensor.fake_battery_charge_power": State("sensor.fake_battery_charge_power", 0),
            "input_number.fake_sell_cost": State("input_number.fake_sell_cost", 1),
            "input_number.fake_buy_cost": State("input_number.fake_buy_cost", 1),
            "input_number.fake_sell_tax_percent": State("input_number.fake_sell_tax_percent", 0),
            "sensor.fake_battery_soc": State("sensor.fake_battery_soc", 0),
        },
        State("unknown.entity_id", "unknown"),
    )

    # 2. starts the algorithm at now
    # fmt:off
    # patch("custom_components.solar_optimizer.managed_device.do_service_action", autospec=True) as mock_do_service_action, \
    # patch("custom_components.solar_optimizer.managed_device.ManagedDevice.change_requested_power", autospec=True) as mock_change_requested_power:
    device._set_now(now)
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        assert device.check_usable() is True

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        assert calculated_data["total_power"] == 500
        assert calculated_data["power_device_a"].is_waiting is True
        assert calculated_data["power_device_a"].requested_power == 500
        assert calculated_data["power_device_a"].current_power == 500
        assert calculated_data["power_device_a"].is_active is False # it was not activated
        assert calculated_data["power_device_a"].is_usable is False # no more usable cause waiting
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 600  # 10 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 120

        assert calculated_data["best_solution"][0]["name"] == "Power Device A"
        assert calculated_data["best_solution"][0]["state"] is True
        assert calculated_data["best_solution"][0]["current_power"] == 0 # calculated before the activation
        assert calculated_data["best_solution"][0]["requested_power"] == 500

        # there is a cache in template evaluation which prevent this test to work
        # assert device.is_active is True
        # assert device_a_switch.is_on is True
        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 50

        # check hass.bus.fire has been called
        assert mock_fire.call_count == 2
        mock_fire.assert_has_calls(
            [
                call(
                    event_type=EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE,
                    event_data={
                        'action_type': ACTION_ACTIVATE,
                        'requested_power': 500,
                        'current_power': 0,
                        'entity_id': 'input_boolean.fake_device_a'
                    },
                    context=ANY),
                call(
                    event_type=EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
                    event_data={
                        'action_type': ACTION_CHANGE_POWER,
                        'requested_power': 500,
                        'current_power': 500,
                        'entity_id': 'input_number.fake_amps_number'
                    },
                    context=ANY)
            ],
            any_order=True,
        )

    # 2. one minute later, the device should be still waiting. The power should not change
    now = now + timedelta(minutes=1)
    device._set_now(now)
    # -300 is -800 of the production - 500 of the consumption
    side_effects.add_or_update_side_effect("sensor.fake_power_production", State("sensor.fake_power_production", 800))
    side_effects.add_or_update_side_effect("sensor.fake_power_consumption", State("sensor.fake_power_consumption", -300))
    # we add the Get state side effect for the input_number fake Amps
    side_effects.add_or_update_side_effect("input_number.fake_amps_number", State("input_number.fake_amps_number", 50))

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        assert device.check_usable() is False
        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        # No change
        assert calculated_data["total_power"] == 500
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 540  # 9 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 60

        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 50

        assert mock_fire.call_count == 0

    # 3. one minute later, the power can be changed
    now = now + timedelta(minutes=1)
    device._set_now(now)

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        # the device is waiting but the power can be changed (usable = True)
        assert device.check_usable() is True
        assert device.is_waiting is True

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        # Changes !
        assert calculated_data["total_power"] == 800
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 480  # 8 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 120 # 2 minutes now cause the power changed

        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 80

        # check hass.bus.fire has been called
        assert mock_fire.call_count == 1
        mock_fire.assert_has_calls(
            [
                call(
                    event_type=EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
                    event_data={
                        'action_type': ACTION_CHANGE_POWER,
                        'requested_power': 800,
                        'current_power': 500,
                        'entity_id': 'input_number.fake_amps_number'
                    },
                    context=ANY)
            ],
            any_order=True,
        )

    # 4. one minute later, the device and power are waiting
    now = now + timedelta(minutes=1)
    device._set_now(now)
    # slow down the production
    side_effects.add_or_update_side_effect("sensor.fake_power_production", State("sensor.fake_power_production", 0))
    side_effects.add_or_update_side_effect("sensor.fake_power_consumption", State("sensor.fake_power_consumption", 800))
    # we add the Get state side effect for the input_number fake Amps
    side_effects.add_or_update_side_effect("input_number.fake_amps_number", State("input_number.fake_amps_number", 80))

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        # the device is waiting but the power can be changed (usable = True)
        assert device.check_usable() is False
        assert device.is_waiting is True

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        # No changes
        assert calculated_data["total_power"] == 800
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 420  # 7 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 60 # 1 minute

        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 80

        assert mock_fire.call_count == 0

    # 5. one minute later, the device is waiting the power can change
    now = now + timedelta(minutes=1)
    device._set_now(now)

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        # the device is waiting but the power can be changed (usable = True)
        assert device.check_usable() is True
        assert device.is_waiting is True

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        # Changes !
        assert calculated_data["total_power"] == 100 # the power min
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 360  # 6 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 120 # 2 minutes cause change is done

        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 10

        # check hass.bus.fire has been called
        assert mock_fire.call_count == 1
        mock_fire.assert_has_calls(
            [
                call(
                    event_type=EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
                    event_data={
                        'action_type': ACTION_CHANGE_POWER,
                        'requested_power': 100,
                        'current_power': 800,
                        'entity_id': 'input_number.fake_amps_number'
                    },
                    context=ANY)
            ],
            any_order=True,
        )

    # 6. one minute later, no changes
    now = now + timedelta(minutes=1)
    device._set_now(now)
    side_effects.add_or_update_side_effect("sensor.fake_power_production", State("sensor.fake_power_production", 0))
    side_effects.add_or_update_side_effect("sensor.fake_power_consumption", State("sensor.fake_power_consumption", 100))
    # we add the Get state side effect for the input_number fake Amps
    side_effects.add_or_update_side_effect("input_number.fake_amps_number", State("input_number.fake_amps_number", 10))

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        # the device is waiting but the power can be changed (usable = True)
        assert device.check_usable() is False
        assert device.is_waiting is True

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        # No changes
        assert calculated_data["total_power"] == 100 # the power min
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 300  # 5 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 60 # 1 minutes

        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 10

        assert mock_fire.call_count == 0

    # 7. one minute later, no changes
    now = now + timedelta(minutes=1)
    device._set_now(now)

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        # the device is waiting but the power can be changed (usable = True)
        assert device.check_usable() is True
        assert device.is_waiting is True

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_ON

        # No changes
        assert calculated_data["total_power"] == 100 # the power min
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 240  # 4 minutes
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() >= 0 # 0 minutes

        assert fake_device_a.state == STATE_ON
        assert fake_amps_number.state == 10

        assert mock_fire.call_count == 0

    # 8. 4 minutes later, the device is turned off
    now = now + timedelta(minutes=4)
    device._set_now(now)

    # fmt:off
    with patch("homeassistant.core.StateMachine.get", side_effect=side_effects.get_side_effects()), \
         patch("custom_components.solar_optimizer.managed_device.ManagedDevice.is_active", new_callable=PropertyMock, return_value=True), \
         patch("homeassistant.core.EventBus.fire") as mock_fire:
    # fmt:on
        # the device is waiting but the power can be changed (usable = True)
        assert device.check_usable() is True
        assert device.is_waiting is False

        calculated_data = await coordinator._async_update_data()
        await hass.async_block_till_done()

        assert fake_device_a.state == STATE_OFF # should be OFF now

        # No changes
        assert calculated_data["total_power"] == 0 # the power min
        assert calculated_data["power_device_a"].is_waiting is True
        assert (calculated_data["power_device_a"].next_date_available.astimezone(tz) - now).total_seconds() >= 5*60  # 5 minutes stop
        assert (calculated_data["power_device_a"].next_date_available_power.astimezone(tz) - now).total_seconds() <= -4*60 # -4 minutes

        assert fake_device_a.state == STATE_OFF
        assert fake_amps_number.state == 10 # the last value

        # check hass.bus.fire has been called
        assert mock_fire.call_count == 1
        mock_fire.assert_has_calls(
            [
                call(
                    event_type=EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE,
                    event_data={
                        'action_type': ACTION_DEACTIVATE,
                        'requested_power': 0,
                        'current_power': 100,
                        'entity_id': 'input_boolean.fake_device_a'
                    },
                    context=ANY),
            ],
            any_order=True,
        )

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
                        context=ANY,
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
                        context=ANY,
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
                        context=ANY,
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
                        context=ANY,
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
                        context=ANY,
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
                        context=ANY,
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
                        context=ANY,
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
                        context=ANY,
                    ),
                ]
            )
