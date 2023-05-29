""" Les constantes pour l'intégration Tuto HACS """

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

DOMAIN = "solar_optimizer"
PLATFORMS: list[Platform] = [Platform.SENSOR]

DEFAULT_REFRESH_PERIOD_SEC = 300


def get_tz(hass: HomeAssistant):
    """Get the current timezone"""

    return dt_util.get_time_zone(hass.config.time_zone)
