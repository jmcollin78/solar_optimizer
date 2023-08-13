""" Some common resources """
import asyncio
import logging
from unittest.mock import patch, MagicMock
import pytest  # pylint: disable=unused-import

from homeassistant.core import HomeAssistant, Event, EVENT_STATE_CHANGED, State
from pytest_homeassistant_custom_component.common import MockConfigEntry
from homeassistant.config_entries import ConfigEntryState

from custom_components.solar_optimizer.const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from custom_components.solar_optimizer.coordinator import SolarOptimizerCoordinator
from custom_components.solar_optimizer.managed_device import ManagedDevice
