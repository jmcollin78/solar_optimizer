""" Les constantes pour l'intégration Solar Optimizer """
import re

from slugify import slugify
from voluptuous.error import Invalid

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

DOMAIN = "solar_optimizer"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

DEFAULT_REFRESH_PERIOD_SEC = 300
DEFAULT_RAZ_TIME = "05:00"

CONF_ACTION_MODE_SERVICE = "service_call"
CONF_ACTION_MODE_EVENT = "event"

CONF_ACTION_MODES = [CONF_ACTION_MODE_SERVICE, CONF_ACTION_MODE_EVENT]

EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER = "solar_optimizer_change_power_event"
EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE = "solar_optimizer_state_change_event"

EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE = (
    "solar_optimizer_enable_state_change_event"
)

DEVICE_MODEL = "Solar Optimizer device"
INTEGRATION_MODEL = "Solar Optimizer"
DEVICE_MANUFACTURER = "JM. COLLIN"

SERVICE_RESET_ON_TIME = "reset_on_time"

TIME_REGEX = r"^(?:[01]\d|2[0-3]):[0-5]\d$"


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)


def name_to_unique_id(name: str) -> str:
    """Convert a name to a unique id. Replace ' ' by _"""
    return slugify(name).replace("-", "_")


def seconds_to_hms(seconds):
    """Convert seconds to a formatted string of hours:minutes:seconds."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def validate_time_format(value: str) -> str:
    """check is a string have format "hh:mm" with hh between 00 and 23 and mm between 00 et 59"""
    if not re.match(TIME_REGEX, value):
        raise Invalid("The time value should be formatted like 'hh:mm'")
    return value


class ConfigurationError(Exception):
    """An error in configuration"""

    def __init__(self, message):
        super().__init__(message)


class overrides:  # pylint: disable=invalid-name
    """An annotation to inform overrides"""

    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        raise RuntimeError(f"Method {self.func.__name__} should have been overridden")
