"""Initialisation du package de l'intégration HACS Tuto"""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import SolarOptimizerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant, entry: ConfigEntry
):  # pylint: disable=unused-argument
    """Initialisation de l'intégration"""
    _LOGGER.info(
        "Initializing %s integration with plaforms: %s with config: %s",
        DOMAIN,
        PLATFORMS,
        entry,
    )

    hass.data.setdefault(DOMAIN, {})

    # L'argument config contient votre fichier configuration.yaml
    solar_optimizer_config = entry.get(DOMAIN)

    hass.data[DOMAIN]["coordinator"] = coordinator = SolarOptimizerCoordinator(hass, solar_optimizer_config)

    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # entry.async_on_unload(entry.add_update_listener(async_reload_entry))


    # Return boolean to indicate that initialization was successful.
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
