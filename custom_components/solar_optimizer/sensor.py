""" A sensor entity that holds the result of the recuit simule algorithm """
import logging
from homeassistant.const import UnitOfPower
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)


from .const import DOMAIN
from .coordinator import SolarOptimizerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup the entries of type Sensor"""

    # Sets the config entries values to SolarOptimizer coordinator
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN]["coordinator"]

    entity1 = SolarOptimizerSensorEntity(coordinator, hass, "best_objective")
    entity2 = SolarOptimizerSensorEntity(coordinator, hass, "total_power")
    entity3 = SolarOptimizerSensorEntity(coordinator, hass, "power_production")
    entity4 = SolarOptimizerSensorEntity(coordinator, hass, "power_production_brut")

    async_add_entities([entity1, entity2, entity3, entity4], False)

    await coordinator.configure(entry)


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
        if (
            not self.coordinator
            or not self.coordinator.data
            or (value := self.coordinator.data.get(self.idx)) == None
        ):
            _LOGGER.debug("No coordinator found or no data...")
            return

        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        # Retournez des informations sur le périphérique associé à votre entité
        return {
            "identifiers": {(DOMAIN, "solar_optimizer_device")},
            "name": "Solar Optimizer",
            # Autres attributs du périphérique ici
        }

    @property
    def icon(self) -> str | None:
        if self.idx == "best_objective":
            return "mdi:bullseye-arrow"
        elif self.idx == "total_power":
            return "mdi:flash"
        else:
            return "mdi:solar-power-variant"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        if self.idx == "best_objective":
            return SensorDeviceClass.MONETARY
        else:
            return SensorDeviceClass.POWER

    @property
    def state_class(self) -> SensorStateClass | None:
        if self.idx == "best_objective":
            return SensorStateClass.TOTAL
        else:
            return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.idx == "best_objective":
            return "€"
        else:
            return UnitOfPower.WATT
