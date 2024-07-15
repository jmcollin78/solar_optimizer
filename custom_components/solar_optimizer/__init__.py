"""Initialisation du package de l'intégration HACS Tuto"""
import logging
import voluptuous as vol

from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.humidifier import DOMAIN as HUMIDIFIER_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.number import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN

# from homeassistant.helpers.entity_component import EntityComponent


from .const import DOMAIN, PLATFORMS
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
                "devices": vol.All(
                    [
                        {
                            vol.Required("name"): str,
                            vol.Required("entity_id"): selector.EntitySelector(
                                selector.EntitySelectorConfig(
                                    domain=[INPUT_BOOLEAN_DOMAIN, SWITCH_DOMAIN, HUMIDIFIER_DOMAIN, CLIMATE_DOMAIN, BUTTON_DOMAIN]
                                )
                            ),
                            vol.Optional("power_entity_id"): selector.EntitySelector(
                                selector.EntitySelectorConfig(
                                    domain=[INPUT_NUMBER_DOMAIN, NUMBER_DOMAIN]
                                )
                            ),
                            vol.Required("power_max"): vol.Coerce(float),
                            vol.Optional("power_min"): vol.Coerce(float),
                            vol.Optional("power_step"): vol.Coerce(float),
                            vol.Optional("check_usable_template"): str,
                            vol.Optional("check_active_template"): str,
                            vol.Optional("duration_min"): vol.Coerce(float),
                            vol.Optional("duration_stop_min"): vol.Coerce(float),
                            vol.Optional("duration_power_min"): vol.Coerce(float),
                            vol.Optional("action_mode"): str,
                            vol.Required("activation_service"): str,
                            vol.Required("deactivation_service"): str,
                            vol.Optional("change_power_service"): str,
                            vol.Optional("convert_power_divide_factor"): vol.Coerce(
                                float
                            ),
                        }
                    ]
                ),
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


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

    hass.data[DOMAIN]["coordinator"] = coordinator = SolarOptimizerCoordinator(
        hass, solar_optimizer_config
    )

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
        pass
        # hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    # await async_setup_entry(hass, entry)
