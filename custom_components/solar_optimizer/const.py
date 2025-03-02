""" Les constantes pour l'intégration Solar Optimizer """

from slugify import slugify

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.util import dt as dt_util

SOLAR_OPTIMIZER_DOMAIN = DOMAIN = "solar_optimizer"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]

DEVICE_MANUFACTURER = "JMCOLLIN"
DEVICE_MODEL = "Solar Optimizer"

DEFAULT_REFRESH_PERIOD_SEC = 300

CONF_ACTION_MODE_SERVICE = "service_call"
CONF_ACTION_MODE_EVENT = "event"

CONF_ACTION_MODES = [CONF_ACTION_MODE_SERVICE, CONF_ACTION_MODE_EVENT]

EVENT_TYPE_SOLAR_OPTIMIZER_CHANGE_POWER = "solar_optimizer_change_power_event"
EVENT_TYPE_SOLAR_OPTIMIZER_STATE_CHANGE = "solar_optimizer_state_change_event"

EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE = (
    "solar_optimizer_enable_state_change_event"
)

CONFIG_VERSION = 2
CONFIG_MINOR_VERSION = 0

CONF_DEVICE_TYPE = "device_type"
CONF_DEVICE_CENTRAL = "central_config"
CONF_DEVICE = "device_type"
CONF_POWERED_DEVICE = "powered_device_type"
CONF_ALL_CONFIG_TYPES = [CONF_DEVICE_CENTRAL, CONF_DEVICE, CONF_POWERED_DEVICE]
CONF_DEVICE_TYPES = [CONF_DEVICE, CONF_POWERED_DEVICE]
CONF_POWER_CONSUMPTION_ENTITY_ID = "power_consumption_entity_id"
CONF_POWER_PRODUCTION_ENTITY_ID = "power_production_entity_id"
CONF_SELL_COST_ENTITY_ID = "sell_cost_entity_id"
CONF_BUY_COST_ENTITY_ID = "buy_cost_entity_id"
CONF_SELL_TAX_PERCENT_ENTITY_ID = "sell_tax_percent_entity_id"
CONF_SMOOTH_PRODUCTION = "smooth_production"
CONF_REFRESH_PERIOD_SEC = "refresh_period_sec"
CONF_NAME = "name"
CONF_ENTITY_ID = "entity_id"
CONF_POWER_MAX = "power_max"
CONF_CHECK_USABLE_TEMPLATE = "check_usable_template"
CONF_CHECK_ACTIVE_TEMPLATE = "check_active_template"
CONF_DURATION_MIN = "duration_min"
CONF_DURATION_STOP_MIN = "duration_stop_min"
CONF_ACTION_MODE = "action_mode"
CONF_ACTIVATION_SERVICE = "activation_service"
CONF_DEACTIVATION_SERVICE = "deactivation_service"


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


class UnknownEntity(HomeAssistantError):
    """Error to indicate there is an unknown entity_id given."""
