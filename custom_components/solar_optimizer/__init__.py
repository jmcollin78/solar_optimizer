"""Initialisation du package de l'intégration HACS Tuto"""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant, config: ConfigEntry
):  # pylint: disable=unused-argument
    """Initialisation de l'intégration"""
    _LOGGER.info(
        "Initializing %s integration with plaforms: %s with config: %s",
        DOMAIN,
        PLATFORMS,
        config,
    )

    # Mettre ici un eventuel code permettant l'initialisation de l'intégration
    # (pas nécessaire pour le tuto)

    # L'argument config contient votre fichier configuration.yaml
    my_config = config.get(DOMAIN)  # pylint: disable=unused-variable

    # Return boolean to indicate that initialization was successful.
    return True
