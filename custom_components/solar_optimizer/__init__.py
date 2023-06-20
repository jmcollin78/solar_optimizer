"""Initialisation du package de l'intégration HACS Tuto"""
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

# from homeassistant.helpers.entity_component import EntityComponent

from .const import DOMAIN, PLATFORMS
from .coordinator import SolarOptimizerCoordinator

# from .input_boolean import async_setup_entry as async_setup_entry_input_boolean

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant, config: ConfigType
):  # pylint: disable=unused-argument
    """Initialisation de l'intégration"""
    _LOGGER.info(
        "Initializing %s integration with plaforms: %s with config: %s",
        DOMAIN,
        PLATFORMS,
        config.get(DOMAIN),
    )

    hass.data.setdefault(DOMAIN, {})

    # L'argument config contient votre fichier configuration.yaml
    solar_optimizer_config = config.get(DOMAIN)

    hass.data[DOMAIN]["coordinator"] = SolarOptimizerCoordinator(
        hass, solar_optimizer_config
    )

    # await async_setup_entry_sensor(hass)
    # await async_setup_entry_switch(hass)
    #
    # # refresh data on startup
    # async def _internal_startup(*_):
    #     await coordinator.async_config_entry_first_refresh()
    #
    # hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, _internal_startup)

    # Return boolean to indicate that initialization was successful.
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Creation des entités à partir d'une configEntry"""

    _LOGGER.debug(
        "Appel de async_setup_entry entry: entry_id='%s', data='%s'",
        entry.entry_id,
        entry.data,
    )

    hass.data.setdefault(DOMAIN, {})

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # component: EntityComponent[InputBoolean] = hass.data.get(INPUT_BOOLEAN_DOMAIN)
    # if component is None:
    #     component = hass.data[INPUT_BOOLEAN_DOMAIN] = EntityComponent[InputBoolean](
    #         _LOGGER, INPUT_BOOLEAN_DOMAIN, hass
    #     )
    # return await async_setup_entry_input_boolean(
    #     hass, entry, component.async_add_entities
    # )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    # await async_setup_entry(hass, entry)
