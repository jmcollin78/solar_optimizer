""" A ManagedDevice represent a device than can be managed by the optimisatiion algorithm"""
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_OFF, STATE_ON

from .const import (
    get_tz,
    CONF_ACTION_MODE_SERVICE,
    CONF_ACTION_MODE_EVENT,
    CONF_ACTION_MODES,
    ConfigurationError,
    EVENT_TYPE_SOLAR_OPTIMIZER,
)

ACTION_ACTIVATE = "Activate"
ACTION_DEACTIVATE = "Deactivate"
ACTION_CHANGE_POWER = "ChangePower"

_LOGGER = logging.getLogger(__name__)


async def do_service_action(
    hass: HomeAssistant,
    entity_id,
    service_name,
    current_power=None,
    requested_power=None,
):
    """Activate an entity via a service call"""
    _LOGGER.info("Calling service %s for entity %s", service_name, entity_id)

    parties = service_name.split("/")
    if len(parties) == 2:
        service_data = {
            "entity_id": entity_id,
        }
        # Don't work
        # if requested_power:
        #     service_data.update(
        #         {"requested_power": requested_power, "current_power": current_power}
        #     )

        await hass.services.async_call(
            parties[0],
            parties[1],
            service_data,
        )
    else:
        raise ConfigurationError(
            f"Incorrect service declaration for entity {entity_id}. Service {service_name} should be formatted with: 'domain/service'"
        )


def do_event_action(
    hass: HomeAssistant, entity_id, action_type, current_power, requested_power
):
    """Activate an entity via an event"""
    _LOGGER.info(
        "Sending event %s for entity %s with requested_power %s and current_power %s",
        EVENT_TYPE_SOLAR_OPTIMIZER,
        entity_id,
        requested_power,
        current_power,
    )

    hass.bus.fire(
        event_type=EVENT_TYPE_SOLAR_OPTIMIZER,
        event_data={
            "action_type": action_type,
            "requested_power": requested_power,
            "current_power": current_power,
            "entity_id": entity_id,
        },
    )


class ManagedDevice:
    """A Managed device representation"""

    _name: str
    _entity_id: str
    _power_max: int
    _power_min: int
    _power_step: int
    _can_change_power: bool
    _current_power: int
    _requested_power: int
    _duration_sec: int
    _check_usable_template: Template
    _check_active_template: Template
    _next_date_available: datetime
    _action_mode: str
    _activation_service: str
    _deactivation_service: str
    _change_power_service: str

    def __init__(self, hass: HomeAssistant, device_config):
        """Initialize a manageable device"""
        self._hass = hass
        self._name = device_config.get("name")
        self._entity_id = device_config.get("entity_id")
        self._power_max = int(device_config.get("power_max"))
        self._power_min = int(device_config.get("power_min") or -1)
        self._power_step = int(device_config.get("power_step") or 0)
        self._can_change_power = self._power_min >= 0

        self._current_power = self._requested_power = 0
        self._duration_sec = int(device_config.get("duration_sec"))
        if device_config.get("check_usable_template"):
            self._check_usable_template = Template(
                device_config.get("check_usable_template"), hass
            )
        else:
            # If no template for usability, the device is supposed to be always usable
            self._check_usable_template = Template("{{ True }}", hass)
        if device_config.get("check_active_template"):
            self._check_active_template = Template(
                device_config.get("check_active_template"), hass
            )
        else:
            template_string = (
                "{{ is_state('" + self._entity_id + "', '" + STATE_ON + "') }}"
            )
            self._check_active_template = Template(template_string, hass)
        self._next_date_available = datetime.now(get_tz(hass))
        self._action_mode = device_config.get("action_mode")
        self._activation_service = device_config.get("activation_service")
        self._deactivation_service = device_config.get("deactivation_service")
        self._change_power_service = device_config.get("change_power_service")

    async def _apply_action(self, action_type: str, requested_power=None):
        """Apply an action to a managed device.
        This method is a generical method for activate, deactivate, change_requested_power
        """
        _LOGGER.debug(
            "Applying action %s for entity %s. requested_power=%s",
            action_type,
            self._entity_id,
            requested_power,
        )
        if requested_power:
            self._requested_power = requested_power

        if self._action_mode == CONF_ACTION_MODE_SERVICE:
            method = None
            if action_type == ACTION_ACTIVATE:
                method = self._activation_service
            elif action_type == ACTION_DEACTIVATE:
                method = self._deactivation_service
            elif action_type == ACTION_CHANGE_POWER:
                method = self._change_power_service

            await do_service_action(
                self._hass,
                self._entity_id,
                method,
                self._current_power,
                self._requested_power,
            )
        elif self._action_mode == CONF_ACTION_MODE_EVENT:
            do_event_action(
                self._hass,
                self._entity_id,
                action_type,
                self._current_power,
                self._requested_power,
            )
        else:
            raise ConfigurationError(
                f"Incorrect action_mode declaration for entity '{self._entity_id}'. Action_mode '{self._action_mode}' is not supported. Use one of {CONF_ACTION_MODES}"
            )

        self._current_power = self._requested_power
        self.reset_next_date_available()

    async def activate(self, requested_power=None):
        """Use this method to activate this ManagedDevice"""
        return await self._apply_action(ACTION_ACTIVATE, requested_power)

    async def deactivate(self):
        """Use this method to deactivate this ManagedDevice"""
        return await self._apply_action(ACTION_DEACTIVATE)

    async def change_requested_power(self, requested_power):
        """Use this method to change the requested power of this ManagedDevice"""
        return await self._apply_action(ACTION_CHANGE_POWER, requested_power)

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
        result = self._check_active_template.async_render(context={})
        if result:
            _LOGGER.debug("%s is active", self._name)

        return result

        # state = self._hass.states.get(self._entity_id)
        # if not state or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        #     return None
        # elif state.state in (STATE_OFF):
        #     return False
        # else:
        #     return True

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
    def power_min(self):
        """The power min of the managed device"""
        return self._power_min

    @property
    def power_step(self):
        """The power step of the managed device"""
        return self._power_step

    @property
    def duration_sec(self) -> int:
        """The duration a device is not available after a change of the managed device"""
        return self._duration_sec

    @property
    def entity_id(self) -> str:
        """The entity_id of the device"""
        return self._entity_id

    @property
    def current_power(self) -> int:
        """The current_power of the device"""
        return self._current_power

    @property
    def requested_power(self) -> int:
        """The requested_power of the device"""
        return self._requested_power

    @property
    def can_change_power(self) -> bool:
        """true is the device can change its power"""
        return self._can_change_power
