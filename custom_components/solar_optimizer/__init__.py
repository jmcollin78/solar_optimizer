"""Initialisation du package de l'intégration HACS Tuto"""

import logging
import asyncio
import voluptuous as vol

from homeassistant.const import EVENT_HOMEASSISTANT_START, SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector

from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.reload import (
    async_setup_reload_service,
    async_reload_integration_platforms,
    _resetup_platform,
)


from .const import (
    DOMAIN,
    PLATFORMS,
    CONFIG_VERSION,
    CONFIG_MINOR_VERSION,
    SERVICE_RESET_ON_TIME,
    SERVICE_START_DEVICE,
    SERVICE_STOP_DEVICE,
    validate_time_format,
    name_to_unique_id,
    CONF_NAME,
    CONF_POWER_MAX,
    CONF_BATTERY_SOC_THRESHOLD,
    CONF_MAX_ON_TIME_PER_DAY_MIN,
    CONF_MIN_ON_TIME_PER_DAY_MIN,
)
from .coordinator import SolarOptimizerCoordinator

# from .input_boolean import async_setup_entry as async_setup_entry_input_boolean

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                "algorithm": vol.Schema(
                    {
                        vol.Required("initial_temp", default=1000): vol.Coerce(float),
                        vol.Required("min_temp", default=0.1): vol.Coerce(float),
                        vol.Required("cooling_factor", default=0.95): vol.Coerce(float),
                        vol.Required(
                            "max_iteration_number", default=1000
                        ): cv.positive_int,
                    }
                ),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Enregistre le dossier frontend pour servir la carte et l'ajoute dans Lovelace."""
    if not hasattr(hass, "http") or hass.http is None:
        _LOGGER.debug("Le serveur HTTP de Home Assistant n'est pas disponible (environnement de test)")
        return

    import os
    current_dir = os.path.dirname(__file__)
    frontend_path = os.path.join(current_dir, "frontend")
    _LOGGER.info("Enregistrement du chemin statique pour Solar Optimizer Card : /solar-optimizer-frontend -> %s", frontend_path)

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths([StaticPathConfig("/solar-optimizer-frontend", frontend_path, False)])
    except ImportError:
        hass.http.register_static_path(
            "/solar-optimizer-frontend",
            frontend_path,
            cache_headers=False,
        )

    async def register_lovelace_resource(*_):
        lovelace_data = hass.data.get("lovelace")
        if lovelace_data is None:
            _LOGGER.debug("L'intégration Lovelace n'est pas chargée, impossible d'enregistrer la ressource automatiquement.")
            return

        resources = None
        if hasattr(lovelace_data, "resources"):
            resources = lovelace_data.resources
        elif isinstance(lovelace_data, dict):
            resources = lovelace_data.get("resources")

        if resources is None:
            _LOGGER.debug("Les ressources Lovelace ne sont pas accessibles.")
            return

        if not resources.loaded:
            try:
                await resources.async_load()
            except Exception as err:
                _LOGGER.warning("Erreur lors du chargement des ressources Lovelace: %s", err)
                return

        url = "/solar-optimizer-frontend/solar-optimizer-card.js"

        exists = False
        try:
            for entry in resources.async_items():
                if entry.get("url") == url:
                    exists = True
                    break
        except Exception as err:
            _LOGGER.warning("Erreur lors de la lecture des ressources Lovelace: %s", err)
            return

        if not exists:
            _LOGGER.info("Ajout de la carte Solar Optimizer aux ressources Lovelace : %s", url)
            try:
                await resources.async_create_item({"res_type": "module", "url": url})
            except Exception as err:
                _LOGGER.warning(
                    "Impossible d'ajouter automatiquement la ressource Lovelace : %s. " "Si vous êtes en mode Lovelace YAML, vous devez ajouter la ressource manuellement.", err
                )

    hass.async_create_task(register_lovelace_resource())


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

    # On enregistre la partie frontend (carte Lovelace)
    await async_register_frontend(hass)

    # L'argument config contient votre fichier configuration.yaml
    solar_optimizer_config = config.get(DOMAIN)

    hass.data[DOMAIN]["coordinator"] = coordinator = SolarOptimizerCoordinator(
        hass, solar_optimizer_config
    )

    async def _handle_reload(_):
        """The reload callback"""
        await reload_config(hass)

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    async def _handle_start_device(call):
        """Handle solar_optimizer.start_device service call"""
        coordinator = SolarOptimizerCoordinator.get_coordinator()
        if coordinator is None:
            _LOGGER.error("start_device: coordinator not found")
            return
        device_id = call.data.get("device_id")
        duration = call.data.get("duration")
        device = coordinator.get_device_by_unique_id(device_id)
        if device is None:
            _LOGGER.warning("start_device: device '%s' not found", device_id)
            return
        await device.start_forced(duration_hours=float(duration) if duration is not None else None)
        hass.async_create_task(coordinator.async_refresh())

    hass.services.async_register(DOMAIN, SERVICE_START_DEVICE, _handle_start_device)

    async def _handle_stop_device(call):
        """Handle solar_optimizer.stop_device service call"""
        coordinator = SolarOptimizerCoordinator.get_coordinator()
        if coordinator is None:
            _LOGGER.error("stop_device: coordinator not found")
            return
        device_id = call.data.get("device_id")
        device = coordinator.get_device_by_unique_id(device_id)
        if device is None:
            _LOGGER.warning("stop_device: device '%s' not found", device_id)
            return
        await device.stop_forced()
        hass.async_create_task(coordinator.async_refresh())

    hass.services.async_register(DOMAIN, SERVICE_STOP_DEVICE, _handle_stop_device)

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    hass.bus.async_listen_once("homeassistant_started", coordinator.on_ha_started)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Creation des entités à partir d'une configEntry"""

    _LOGGER.debug(
        "Appel de async_setup_entry entry: entry_id='%s', data='%s'",
        entry.entry_id,
        entry.data,
    )

    hass.data.setdefault(DOMAIN, {})

    # Enregistrement de l'écouteur de changement 'update_listener'
    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Fonction qui force le rechargement des entités associées à une configEntry"""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if (coordinator := SolarOptimizerCoordinator.get_coordinator()) is not None:
            coordinator.remove_device(name_to_unique_id(entry.data[CONF_NAME]))
        # hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# Migration function (not used yet)
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug(
        "Migrating from version %s/%s", config_entry.version, config_entry.minor_version
    )

    if config_entry.version == CONFIG_VERSION and config_entry.minor_version == 0:
        _LOGGER.debug("Migration from version 0 to %s/%s is needed", CONFIG_VERSION, CONFIG_MINOR_VERSION)
        new = {**config_entry.data}
        for key in (CONF_POWER_MAX, CONF_BATTERY_SOC_THRESHOLD, CONF_MAX_ON_TIME_PER_DAY_MIN, CONF_MIN_ON_TIME_PER_DAY_MIN):
            if key in new:
                new[key] = str(new[key])

        hass.config_entries.async_update_entry(
            config_entry,
            data=new,
            version=CONFIG_VERSION,
            minor_version=CONFIG_MINOR_VERSION,
        )

        _LOGGER.info(
            "Migration to version %s (%s) successful",
            config_entry.version,
            config_entry.minor_version,
        )

    return True


async def reload_config(hass):
    """Handle reload service call."""
    _LOGGER.info("Service %s.reload called: reloading integration", DOMAIN)

    # await async_reload_integration_platforms(hass, DOMAIN, PLATFORMS)
    # await _resetup_platform(hass, DOMAIN, DOMAIN, None)
    await async_setup_component(hass, DOMAIN, None)
