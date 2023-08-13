""" Les constantes pour l'intégration Solar Optimizer """
from slugify import slugify

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

DOMAIN = "solar_optimizer"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

DEFAULT_REFRESH_PERIOD_SEC = 300

CONF_ACTION_MODE_SERVICE = "service_call"
CONF_ACTION_MODE_EVENT = "event"

CONF_ACTION_MODES = [CONF_ACTION_MODE_SERVICE, CONF_ACTION_MODE_EVENT]

EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER = "solar_optimizer_change_power_event"
EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE = "solar_optimizer_state_change_event"

EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE = (
    "solar_optimizer_enable_state_change_event"
)


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


def name_to_unique_id(name: str) -> str:
    """Convert a name to a unique id. Replace ' ' by _"""
    return slugify(name).replace("-", "_")


class ConfigurationError(Exception):
    """An error in configuration"""

    def __init__(self, message):
        super().__init__(message)
