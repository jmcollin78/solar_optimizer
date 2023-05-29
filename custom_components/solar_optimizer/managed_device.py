""" A ManagedDevice represent a device than can be managed by the optimisatiion algorithm"""
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_OFF

from .const import get_tz

_LOGGER = logging.getLogger(__name__)


class ManagedDevice:
    """A Managed device representation"""

    _name: str
    _entity_id: str
    _power_max: int
    _duration_sec: int
    _check_usable_template: Template
    _next_date_available: datetime

    def __init__(self, hass: HomeAssistant, device_config):
        """Initialize a manageable device"""
        self._hass = hass
        self._name = device_config.get("name")
        self._entity_id = device_config.get("entity_id")
        self._power_max = int(device_config.get("power_max"))
        self._duration_sec = int(device_config.get("duration_sec"))
        self._check_usable_template = Template(
            device_config.get("check_usable_template"), hass
        )
        self._next_date_available = datetime.now(get_tz(hass))

    async def activate(self):
        """Use this method to activate this ManagedDevice"""
        await self._hass.services.async_call(
            "input_boolean", "turn_on", {"entity_id": self.entity_id}
        )
        self.reset_next_date_available()

    async def deactivate(self):
        """Use this method to deactivate this ManagedDevice"""
        await self._hass.services.async_call(
            "input_boolean", "turn_off", {"entity_id": self.entity_id}
        )
        self.reset_next_date_available()

    def reset_next_date_available(self):
        """Incremente the next availability date to now + _duration_sec"""
        self._next_date_available = datetime.now(get_tz(self._hass)) + timedelta(
            seconds=self._duration_sec
        )
        _LOGGER.debug(
            "Next availability date for %s is %s", self._name, self._next_date_available
        )

    @property
    def is_active(self):
        """Check if device is active by getting the underlying state of the device"""
        state = self._hass.states.get(self._entity_id)
        if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        elif state.state in (STATE_OFF):
            return False
        else:
            return True

    @property
    def is_usable(self):
        """A device is usable for optimisation if the check_usable_template returns true and
        if the device is not waiting for the end of its cycle"""
        context = {}
        now = datetime.now(get_tz(self._hass))
        result = (
            self._check_usable_template.async_render(context)
            and now >= self._next_date_available
        )
        if not result:
            _LOGGER.debug("%s is not usable", self._name)

        return result

    @property
    def name(self):
        """The name of the ManagedDevice"""
        return self._name

    @property
    def power_max(self):
        """The power max of the managed device"""
        return self._power_max

    @property
    def duration_sec(self):
        """The duration a device is not available after a change of the managed device"""
        return self._duration_sec

    @property
    def entity_id(self):
        """The entity_id of the device"""
        return self._entity_id
