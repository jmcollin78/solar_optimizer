""" A sensor entity that holds the result of the recuit simule algorithm """
import logging
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.sensor import SensorEntity, DOMAIN as SENSOR_DOMAIN

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant) -> None:
    """Setup the entries of type Sensor"""
    entity1 = SolarOptimizerSensorEntity(
        hass.data[DOMAIN]["coordinator"], hass, "best_objective"
    )
    entity2 = SolarOptimizerSensorEntity(
        hass.data[DOMAIN]["coordinator"], hass, "total_power"
    )

    component: EntityComponent[SensorEntity] = hass.data.get(SENSOR_DOMAIN)
    if component is None:
        component = hass.data[SENSOR_DOMAIN] = EntityComponent[SensorEntity](
            _LOGGER, SENSOR_DOMAIN, hass
        )
    await component.async_add_entities([entity1, entity2])


class SolarOptimizerSensorEntity(CoordinatorEntity, SensorEntity):
    """The entity holding the algorithm calculation"""

    def __init__(self, coordinator, hass, idx):
        super().__init__(coordinator, context=idx)
        self._hass = hass
        self.idx = idx
        self._attr_name = idx
        self._attr_unique_id = "solar_optimizer_" + idx

        self._attr_native_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_native_value = self.coordinator.data[self.idx]
        self.async_write_ha_state()

    @property
    def device_info(self):
        # Retournez des informations sur le périphérique associé à votre entité
        return {
            "identifiers": {(DOMAIN, "solar_optimizer_device")},
            "name": "Solar Optimizer",
            # Autres attributs du périphérique ici
        }
