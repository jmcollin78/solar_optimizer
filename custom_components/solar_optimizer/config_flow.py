""" Le Config Flow """

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, FlowResult
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.input_number import DOMAIN as INPUT_NUMBER_DOMAIN
from homeassistant.helpers import selector

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
}


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
