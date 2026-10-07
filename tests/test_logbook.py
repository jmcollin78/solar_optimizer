"""Logbook attribution: each action fires a solar_optimizer_action event first, so the
change of the device is shown as triggered by Solar Optimizer"""

# pylint: disable=unused-argument, wildcard-import, unused-wildcard-import, protected-access

from datetime import timedelta

import pytest

from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import mock_component

from custom_components.solar_optimizer.logbook import describe_action

from .commons import *
from .test_manual_override import _setup_device


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """The recorder must be set up before hass: override the conftest fixture in this module"""
    yield


def test_describe_action_uses_configured_service():
    """The message names the device, the action and the configured service of the device"""
    assert describe_action("es", {"action": "Activate", "device_name": "Bomba", "service": "switch/turn_on"}) == "encendió Bomba (switch.turn_on)"
    assert (
        describe_action("en", {"action": "Deactivate", "device_name": "AC", "service": "climate/set_hvac_mode/hvac_mode:off"})
        == "turned off AC (climate.set_hvac_mode hvac_mode:off)"
    )
    assert (
        describe_action("fr", {"action": "ChangePower", "device_name": "Tesla", "service": "number/set_value", "requested_power": 2300})
        == "a réglé Tesla à 2300 W (number.set_value)"
    )
    # event mode: no service, unknown language falls back to English
    assert describe_action("de", {"action": "Activate", "device_name": "Pool"}) == "turned on Pool"


async def test_action_event_is_origin_of_context(hass, init_solar_optimizer_central_config):
    """The event is fired with the Context of the action and is its origin event"""
    device, _ = await _setup_device(hass)
    events = []
    hass.bus.async_listen("solar_optimizer_action", events.append)

    await device.activate()
    await hass.async_block_till_done()

    assert len(events) == 1
    assert events[0].data["action"] == "Activate"
    assert events[0].data["service"] == "input_boolean/turn_on"
    assert events[0].data["entity_id"] == "input_boolean.fake_device_a"
    assert events[0].context is device.last_context
    assert device.last_context.origin_event is events[0]


async def test_logbook_shows_solar_optimizer_as_origin(hass, hass_client, init_solar_optimizer_central_config):
    """End to end with the real recorder and logbook: the entry of the underlying entity
    says it was triggered by Solar Optimizer"""
    mock_component(hass, "frontend")  # logbook dependency, not installed in tests
    assert await async_setup_component(hass, "logbook", {})
    device, _ = await _setup_device(hass)
    start = dt_util.utcnow() - timedelta(seconds=1)

    await device.activate()
    await hass.async_block_till_done()
    await hass.async_add_executor_job(hass.data["recorder_instance"].block_till_done)

    client = await hass_client()
    response = await client.get(f"/api/logbook/{start.isoformat()}")
    entries = await response.json()

    entry = next(e for e in entries if e.get("entity_id") == "input_boolean.fake_device_a" and e.get("state") == "on")
    assert entry["context_domain"] == "solar_optimizer"
    assert entry["context_name"] == "Solar Optimizer"
    assert entry["context_event_type"] == "solar_optimizer_action"
