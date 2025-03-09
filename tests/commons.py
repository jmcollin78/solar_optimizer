""" Some common resources """
# pylint: disable=unused-import

import asyncio
import logging
from unittest.mock import patch, MagicMock
import pytest  # pylint: disable=unused-import

from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, Event, EVENT_STATE_CHANGED, State
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.entity import Entity

from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_optimizer.const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator
from custom_components.solar_optimizer.managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


async def create_managed_device(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    entity_id: str,
) -> ManagedDevice:
    """Creates and return a ManagedDevice"""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()
    assert coordinator is not None

    return coordinator.get_device_by_unique_id(entity_id)


def search_entity(hass: HomeAssistant, entity_id, domain) -> Entity:
    """Search and return the entity in the domain"""
    # component = hass.data["components"].domain #hass.data[domain]

    component = hass.data["entity_components"].get(domain)
    for entity in component.entities:
        if entity.entity_id == entity_id:
            return entity
    return None

async def send_state_change(hass, entity_id, old_state, new_state, date, sleep=False):
    """ Send a state change event for an entity """
    _LOGGER.info(
        "------- Testu: sending send_change_event, new_state=%s old_state=%s date=%s on %s",
        new_state,
        old_state,
        date,
        entity_id,
    )
    event = {
        "entity_id": entity_id,
        "new_state": State(
            entity_id=entity_id,
            state=STATE_ON if new_state else STATE_OFF,
            last_changed=date,
            last_updated=date,
        ),
        "old_state": State(
            entity_id=entity_id,
            state=STATE_ON if old_state else STATE_OFF,
            last_changed=date,
            last_updated=date,
        ),
    }
    hass.bus.fire(
        event_type=EVENT_STATE_CHANGED,
        event_data=event
    )
    if sleep:
        await asyncio.sleep(0.1)

async def create_test_input_boolean(hass, entity_id, name):
    """ Creation of an input_boolean """

    config = {
        "input_boolean": {
            # input_boolean to simulate the windows entity. Only for development environment.
            # TODO replace with dynamic entity_id
            "fake_device_a": {
                "name": name,
                "icon": "mdi:window-closed-variant"
            }
        }
    }
    await async_setup_component(hass, INPUT_BOOLEAN_DOMAIN, config)
