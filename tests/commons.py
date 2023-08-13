""" Some common resources """
# pylint: disable=unused-import

import asyncio
import logging
from unittest.mock import patch, MagicMock
import pytest  # pylint: disable=unused-import

from homeassistant.core import HomeAssistant, Event, EVENT_STATE_CHANGED, State
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.entity import Entity

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_optimizer.const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator
from custom_components.solar_optimizer.managed_device import ManagedDevice

def search_entity(hass: HomeAssistant, entity_id, domain) -> Entity:
    """Search and return the entity in the domain"""
    component = hass.data[domain]
    for entity in component.entities:
        if entity.entity_id == entity_id:
            return entity
    return None
