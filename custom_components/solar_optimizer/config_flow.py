""" Le Config Flow """

import logging
from typing import Any
import copy
from collections.abc import Mapping
import voluptuous as vol


from homeassistant.core import callback
from homeassistant.config_entries import (
    ConfigFlow,
    FlowResult,
    OptionsFlow,
    ConfigEntry,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

solar_optimizer_schema = {
    vol.Required("refresh_period_sec", default=300): int,
    vol.Required("power_consumption_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
    ),
    vol.Required("power_production_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=[SENSOR_DOMAIN, INPUT_NUMBER_DOMAIN])
    ),
    vol.Required("sell_cost_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=[INPUT_NUMBER_DOMAIN])
    ),
    vol.Required("buy_cost_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=[INPUT_NUMBER_DOMAIN])
    ),
    vol.Required("sell_tax_percent_entity_id"): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=[INPUT_NUMBER_DOMAIN])
    ),
    vol.Optional("smooth_production", default=True): cv.boolean,
}


def add_suggested_values_to_schema(
    data_schema: vol.Schema, suggested_values: Mapping[str, Any]
) -> vol.Schema:
    """Make a copy of the schema, populated with suggested values.

    For each schema marker matching items in `suggested_values`,
    the `suggested_value` will be set. The existing `suggested_value` will
    be left untouched if there is no matching item.
    """
    schema = {}
    for key, val in data_schema.schema.items():
        new_key = key
        if key in suggested_values and isinstance(key, vol.Marker):
            # Copy the marker to not modify the flow schema
            new_key = copy.copy(key)
            new_key.description = {"suggested_value": suggested_values[key]}
        schema[new_key] = val
    _LOGGER.debug("add_suggested_values_to_schema: schema=%s", schema)
    return vol.Schema(schema)


class SolarOptimizerConfigFlow(ConfigFlow, domain=DOMAIN):
    """La classe qui implémente le config flow pour notre DOMAIN.
    Elle doit dériver de FlowHandler"""

    # La version de notre configFlow. Va permettre de migrer les entités
    # vers une version plus récente en cas de changement
    VERSION = 1
    _user_inputs: dict = {}

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Gestion de l'étape 'user'. Point d'entrée de notre
        configFlow. Cette méthode est appelée 2 fois :
        1. une première fois sans user_input -> on affiche le formulaire de configuration
        2. une deuxième fois avec les données saisies par l'utilisateur dans user_input -> on sauvegarde les données saisies
        """
        user_form = vol.Schema(solar_optimizer_schema)

        if user_input is None:
            _LOGGER.debug(
                "config_flow step user (1). 1er appel : pas de user_input -> on affiche le form user_form"
            )
            return self.async_show_form(step_id="user", data_schema=user_form)

        # 2ème appel : il y a des user_input -> on stocke le résultat
        self._user_inputs.update(user_input)
        _LOGGER.debug(
            "config_flow step2 (2). L'ensemble de la configuration est: %s",
            self._user_inputs,
        )

        return self.async_create_entry(title="SolarOptimizer", data=self._user_inputs)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get options flow for this handler"""
        return SolarOptimizerOptionsFlow(config_entry)


class SolarOptimizerOptionsFlow(OptionsFlow):
    """The class which enable to modified the configuration"""

    _user_inputs: dict = {}
    config_entry: ConfigEntry = None

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialisation de l'option flow. On a le ConfigEntry existant en entrée"""
        self.config_entry = config_entry
        # On initialise les user_inputs avec les données du configEntry
        self._user_inputs = config_entry.data.copy()

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Gestion de l'étape 'user'. Point d'entrée de notre
        configFlow. Cette méthode est appelée 2 fois :
        1. une première fois sans user_input -> on affiche le formulaire de configuration
        2. une deuxième fois avec les données saisies par l'utilisateur dans user_input -> on sauvegarde les données saisies
        """
        user_form = vol.Schema(solar_optimizer_schema)

        if user_input is None:
            _LOGGER.debug(
                "config_flow step user (1). 1er appel : pas de user_input -> on affiche le form user_form"
            )
            return self.async_show_form(
                step_id="init",
                data_schema=add_suggested_values_to_schema(
                    data_schema=user_form,
                    suggested_values=self._user_inputs,
                ),
            )

        # 2ème appel : il y a des user_input -> on stocke le résultat
        self._user_inputs.update(user_input)
        _LOGGER.debug(
            "config_flow step_user (2). L'ensemble de la configuration est: %s",
            self._user_inputs,
        )

        # On appelle le step de fin pour enregistrer les modifications
        return await self.async_end()

    async def async_end(self):
        """Finalization of the ConfigEntry creation"""
        _LOGGER.info(
            "Recreation de l'entry %s. La nouvelle config est maintenant : %s",
            self.config_entry.entry_id,
            self._user_inputs,
        )

        # Modification des data de la configEntry
        # (et non pas ajout d'un objet options dans la configEntry)
        self.hass.config_entries.async_update_entry(
            self.config_entry, data=self._user_inputs
        )
        # Suppression de l'objet options dans la configEntry
        return self.async_create_entry(title=None, data=None)
