""" A ManagedDevice represent a device than can be managed by the optimisatiion algorithm"""
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN

from .const import (
    get_tz,
    name_to_unique_id,
    CONF_ACTION_MODE_SERVICE,
    CONF_ACTION_MODE_EVENT,
    CONF_ACTION_MODES,
    ConfigurationError,
    EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
    EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE,
    EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
)

ACTION_ACTIVATE = "Activate"
ACTION_DEACTIVATE = "Deactivate"
ACTION_CHANGE_POWER = "ChangePower"

_LOGGER = logging.getLogger(__name__)


async def do_service_action(
    hass: HomeAssistant,
    entity_id,
    action_type,
    service_name,
    current_power,
    requested_power,
    convert_power_divide_factor,
):
    """Activate an entity via a service call"""
    _LOGGER.info("Calling service %s for entity %s", service_name, entity_id)

    parties = service_name.split("/")
    if len(parties) != 2:
        raise ConfigurationError(
            f"Incorrect service declaration for entity {entity_id}. Service {service_name} should be formatted with: 'domain/service'"
        )

    if action_type == ACTION_CHANGE_POWER:
        value = round(requested_power / convert_power_divide_factor)
        service_data = {"value": value}
    else:
        service_data = {}

    target = {
        "entity_id": entity_id,
    }

    await hass.services.async_call(
        parties[0], parties[1], service_data=service_data, target=target
    )

    # Also send an event to inform
    do_event_action(
        hass,
        entity_id,
        action_type,
        current_power,
        requested_power,
        EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE,
    )


def do_event_action(
    hass: HomeAssistant,
    entity_id,
    action_type,
    current_power,
    requested_power,
    event_type: str,
):
    """Activate an entity via an event"""
    _LOGGER.info(
        "Sending event %s with action %s for entity %s with requested_power %s and current_power %s",
        event_type,
        action_type,
        entity_id,
        requested_power,
        current_power,
    )

    hass.bus.fire(
        event_type=event_type,
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
    _unique_id: str
    _entity_id: str
    _power_entity_id: str
    _power_max: int
    _power_min: int
    _power_step: int
    _can_change_power: bool
    _current_power: int
    _requested_power: int
    _duration_sec: int
    _duration_stop_sec: int
    _duration_power_sec: int
    _check_usable_template: Template
    _check_active_template: Template
    _next_date_available: datetime
    _next_date_available_power: datetime
    _action_mode: str
    _activation_service: str
    _deactivation_service: str
    _change_power_service: str
    _convert_power_divide_factor: int
    _battery_soc: float
    _battery_soc_threshold: float

    def __init__(self, hass: HomeAssistant, device_config):
        """Initialize a manageable device"""
        self._hass = hass
        self._name = device_config.get("name")
        self._unique_id = name_to_unique_id(self._name)
        self._entity_id = device_config.get("entity_id")
        self._power_entity_id = device_config.get("power_entity_id")
        self._power_max = int(device_config.get("power_max"))
        self._power_min = int(device_config.get("power_min") or -1)
        self._power_step = int(device_config.get("power_step") or 0)
        self._can_change_power = self._power_min >= 0
        self._convert_power_divide_factor = int(
            device_config.get("convert_power_divide_factor") or 1
        )

        self._current_power = self._requested_power = 0
        duration_min = float(device_config.get("duration_min"))
        self._duration_sec = round(duration_min * 60)
        self._duration_power_sec = round(
            float(device_config.get("duration_power_min") or duration_min) * 60
        )

        self._duration_stop_sec = round(
            float(device_config.get("duration_stop_min") or duration_min) * 60
        )

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
        self._next_date_available_power = self._next_date_available = datetime.now(
            get_tz(hass)
        )
        self._action_mode = device_config.get("action_mode")
        self._activation_service = device_config.get("activation_service")
        self._deactivation_service = device_config.get("deactivation_service")
        self._change_power_service = device_config.get("change_power_service")

        self._battery_soc = None
        self._battery_soc_threshold = float(device_config.get("battery_soc_threshold") or 0)

        if self.is_active:
            self._requested_power = self._current_power = (
                self._power_max if self._can_change_power else self._power_min
            )

        self._enable = True

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
        if requested_power is not None:
            self._requested_power = requested_power

        if self._action_mode == CONF_ACTION_MODE_SERVICE:
            method = None
            entity_id = self._entity_id
            if action_type == ACTION_ACTIVATE:
                method = self._activation_service
                self.reset_next_date_available(action_type)
                if self._can_change_power:
                    self.reset_next_date_available_power()
            elif action_type == ACTION_DEACTIVATE:
                method = self._deactivation_service
                self.reset_next_date_available(action_type)
            elif action_type == ACTION_CHANGE_POWER:
                assert (
                    self._can_change_power
                ), f"Equipment {self._name} cannot change its power. We should not be there."
                method = self._change_power_service
                entity_id = self._power_entity_id
                self.reset_next_date_available_power()

            await do_service_action(
                self._hass,
                entity_id,
                action_type,
                method,
                self._current_power,
                self._requested_power,
                self._convert_power_divide_factor,
            )
        elif self._action_mode == CONF_ACTION_MODE_EVENT:
            do_event_action(
                self._hass,
                self._entity_id,
                action_type,
                self._current_power,
                self._requested_power,
                EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER,
            )
        else:
            raise ConfigurationError(
                f"Incorrect action_mode declaration for entity '{self._entity_id}'. Action_mode '{self._action_mode}' is not supported. Use one of {CONF_ACTION_MODES}"
            )

        self._current_power = self._requested_power

    async def activate(self, requested_power=None):
        """Use this method to activate this ManagedDevice"""
        return await self._apply_action(ACTION_ACTIVATE, requested_power)

    async def deactivate(self):
        """Use this method to deactivate this ManagedDevice"""
        return await self._apply_action(ACTION_DEACTIVATE, 0)

    async def change_requested_power(self, requested_power):
        """Use this method to change the requested power of this ManagedDevice"""
        return await self._apply_action(ACTION_CHANGE_POWER, requested_power)

    def reset_next_date_available(self, action_type):
        """Incremente the next availability date to now + _duration_sec"""
        if action_type == ACTION_ACTIVATE:
            self._next_date_available = datetime.now(get_tz(self._hass)) + timedelta(
                seconds=self._duration_sec
            )
        else:
            self._next_date_available = datetime.now(get_tz(self._hass)) + timedelta(
                seconds=self._duration_stop_sec
            )

        _LOGGER.debug(
            "Next availability date for %s is %s", self._name, self._next_date_available
        )

    def reset_next_date_available_power(self):
        """Incremente the next availability date for power change to now + _duration_power_sec"""
        self._next_date_available_power = datetime.now(get_tz(self._hass)) + timedelta(
            seconds=self._duration_power_sec
        )
        _LOGGER.debug(
            "Next availability date for power change for %s is %s",
            self._name,
            self._next_date_available_power,
        )

    # def init_power(self, power: int):
    #     """Initialise current_power and requested_power to the given value"""
    #     _LOGGER.debug(
    #         "Initializing power for entity '%s' with %s value", self._name, power
    #     )
    #     self._requested_power = self._current_power = power

    def set_current_power_with_device_state(self):
        """Set the current power according to the real device state"""
        if not self.is_active:
            self._current_power = 0
            _LOGGER.debug(
                "Set current_power to 0 for device %s cause not active", self._name
            )
            return

        if not self._can_change_power:
            self._current_power = self._power_max
            _LOGGER.debug(
                "Set current_power to %s for device %s cause active and not can_change_power",
                self._current_power,
                self._name,
            )
            return

        amps = self._hass.states.get(self._power_entity_id)
        if not amps or amps.state in [None, STATE_UNKNOWN, STATE_UNAVAILABLE]:
            self._current_power = self._power_min
            _LOGGER.debug(
                "Set current_power to %s for device %s cause can_change_power but amps is %s",
                self._current_power,
                self._name,
                amps,
            )
            return

        self._current_power = round(
            float(amps.state) * self._convert_power_divide_factor
        )
        _LOGGER.debug(
            "Set current_power to %s for device %s cause can_change_power and amps is %s",
            self._current_power,
            self._name,
            amps.state,
        )

    def set_enable(self, enable: bool):
        """Enable or disable the ManagedDevice for Solar Optimizer"""
        _LOGGER.info("%s - Set enable=%s", self.name, enable)
        self._enable = enable
        self.publish_enable_state_change()

    @property
    def is_enabled(self) -> bool:
        """return true if the managed device is enabled for solar optimisation"""
        return self._enable

    @property
    def is_active(self) -> bool:
        """Check if device is active by getting the underlying state of the device"""
        result = self._check_active_template.async_render(context={})
        if result:
            _LOGGER.debug("%s is active", self._name)

        return result

    @property
    def is_usable(self) -> bool:
        """A device is usable for optimisation if the check_usable_template returns true and
        if the device is not waiting for the end of its cycle and if the battery_soc_threshold is >= battery_soc"""

        context = {}
        now = datetime.now(get_tz(self._hass))
        result = self._check_usable_template.async_render(context) and (
            now >= self._next_date_available
            or (self._can_change_power and now >= self._next_date_available_power)
        )
        if not result:
            _LOGGER.debug("%s is not usable", self._name)

        if result and self._battery_soc is not None and self._battery_soc_threshold is not None:
            if self._battery_soc < self._battery_soc_threshold:
                result = False
                _LOGGER.debug("%s is not usable due to battery soc threshold (%s < %s)", self._name, self._battery_soc, self._battery_soc_threshold)

        return result

    @property
    def is_waiting(self):
        """A device is waiting if the device is waiting for the end of its cycle"""
        now = datetime.now(get_tz(self._hass))
        result = now < self._next_date_available

        if result:
            _LOGGER.debug("%s is waiting", self._name)

        return result

    @property
    def name(self):
        """The name of the ManagedDevice"""
        return self._name

    @property
    def unique_id(self):
        """The id of the ManagedDevice"""
        return self._unique_id

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
    def duration_stop_sec(self) -> int:
        """The duration a device is not available after a change of the managed device to stop"""
        return self._duration_stop_sec

    @property
    def duration_power_sec(self) -> int:
        """The duration a device is not available after a change of the managed device for power change"""
        return self._duration_power_sec

    @property
    def entity_id(self) -> str:
        """The entity_id of the device"""
        return self._entity_id

    @property
    def power_entity_id(self) -> str:
        """The entity_id of the device which gives the current power"""
        return self._power_entity_id

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

    @property
    def next_date_available(self) -> datetime:
        """returns the next available date for state change"""
        return self._next_date_available

    @property
    def next_date_available_power(self) -> datetime:
        """return the next available date for power change"""
        return self._next_date_available_power

    @property
    def convert_power_divide_factor(self) -> int:
        """return"""
        return self._convert_power_divide_factor

    def set_battery_soc(self, battery_soc):
        """Define the battery soc. This is used with is_usable
        to determine if the device is usable"""
        self._battery_soc = battery_soc


    def publish_enable_state_change(self) -> None:
        """Publish an event when the state is changed"""

        self._hass.bus.fire(
            event_type=EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
            event_data={
                "device_unique_id": self._unique_id,
                "is_enabled": self.is_enabled,
                "is_active": self.is_active,
                "is_usable": self.is_usable,
                "is_waiting": self.is_waiting,
            },
        )
