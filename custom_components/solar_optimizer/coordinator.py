""" The data coordinator class """
import logging
from datetime import timedelta


from homeassistant.core import HomeAssistant # callback
from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_OFF
)

from homeassistant.helpers.update_coordinator import (
    #CoordinatorEntity,
    DataUpdateCoordinator,
    #UpdateFailed,
)

from homeassistant.helpers.template import Template


from .const import DEFAULT_REFRESH_PERIOD_SEC

_LOGGER = logging.getLogger(__name__)

class ManagedDevice:
    """ A Managed device representation """

    _name: str
    _entity_id: str
    _power_max: int
    _check_usable_template: Template

    def __init__(self, hass: HomeAssistant, device_config):
        """ Initialize a manageable device"""
        self._hass = hass
        self._name = device_config.get("name")
        self._entity_id = device_config.get("entity_id")
        self._power_max = int(device_config.get("power_max"))
        self._check_usable_template = Template(device_config.get("check_usable_template"), hass)

    @property
    def is_device_active(self):
        """ Check if device is active by getting the underlying state of the device"""
        state = self._hass.states.get(self._entity_id)
        if not state or state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return None
        elif state.state in (STATE_OFF):
            return False
        else:
            return True

    @property
    def is_device_usable(self):
        """ A device is usable for optimisation if the check_usable_template returns true and
        if the device is not waiting for the end of its cycle """
        context = {}
        result = self._check_usable_template.async_render(context)
        _LOGGER.debug("Evaluation of check_usable_template for %s is %s", self._name, result)
        return result

    @property
    def name(self):
        """ The name of the ManagedDevice"""
        return self._name

    @property
    def power_max(self):
        """ The power max of the managed device"""
        return self._power_max

class SolarOptimizerCoordinator(DataUpdateCoordinator):
    """ The coordinator class which is used to coordinate all update """

    devices: list[ManagedDevice]

    def __init__(self, hass: HomeAssistant, config):
        """ Initialize the coordinator """
        refresh_period_sec = config.get("refresh_period_sec") or DEFAULT_REFRESH_PERIOD_SEC
        super().__init__(hass,
            _LOGGER, name="Solar Optimizer",
            update_interval=timedelta(seconds=refresh_period_sec)) # pylint : disable=line-too-long
        self.devices = []
        try:
            for _, device in enumerate(config.get("devices")):
                _LOGGER.debug("Configuration of manageable device: %s", device)
                self.devices.append(ManagedDevice(hass, device))
        except Exception as err:
            _LOGGER.error(err)
            _LOGGER.error("Your configuration is wrong. SolarOptimizer will not be operational until you fix it")
            raise err
        self.config = config

    async def _async_update_data(self):
        _LOGGER.info("Refreshing Solar Optimizer calculation")

        calculated_data = {}
        for _, device in enumerate(self.devices):
            _LOGGER.debug("Evaluation of %s, device_active: %s, device_usable: %s", device.name, device.is_device_active, device.is_device_usable)

        return calculated_data
