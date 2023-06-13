""" A bonary sensor entity that holds the state of each managed_device """
import logging
from homeassistant.core import callback, HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from .const import DOMAIN, name_to_unique_id, get_tz
from .coordinator import SolarOptimizerCoordinator
from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant) -> None:
    """Setup the entries of type Binary sensor, one for each ManagedDevice"""
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN]["coordinator"]

    entities = []
    for _, device in enumerate(coordinator.devices):
        entity = ManagedDeviceBinarySensor(
            coordinator, hass, device.name, name_to_unique_id(device.name)
        )
        if entity is not None:
            entities.append(entity)

    component: EntityComponent[BinarySensorEntity] = hass.data.get(BINARY_SENSOR_DOMAIN)
    if component is None:
        component = hass.data[BINARY_SENSOR_DOMAIN] = EntityComponent[
            BinarySensorEntity
        ](_LOGGER, BINARY_SENSOR_DOMAIN, hass)
    await component.async_add_entities(entities)


class ManagedDeviceBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """The entity holding the algorithm calculation"""

    def __init__(self, coordinator, hass, name, idx):
        super().__init__(coordinator, context=idx)
        self._hass = hass
        self.idx = idx
        self._attr_name = name
        self._attr_unique_id = "solar_optimizer_" + idx

        self._attr_is_on = None

    def update_custom_attributes(self, device):
        """Add some custom attributes to the entity"""
        current_tz = get_tz(self._hass)
        self._attr_extra_state_attributes: dict(str, str) = {
            "is_active": device.is_active,
            "is_waiting": device.is_waiting,
            "is_usable": device.is_usable,
            "can_change_power": device.can_change_power,
            "current_power": device.current_power,
            "requested_power": device.requested_power,
            "duration_sec": device.duration_sec,
            "duration_power_sec": device.duration_power_sec,
            "next_date_available": device.next_date_available.astimezone(
                current_tz
            ).isoformat(),
            "next_date_available_power": device.next_date_available_power.astimezone(
                current_tz
            ).isoformat(),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device: ManagedDevice = self.coordinator.data[self.idx]
        if not device:
            return
        self._attr_is_on = device.is_active
        self.update_custom_attributes(device)
        self.async_write_ha_state()

    @property
    def device_info(self):
        # Retournez des informations sur le périphérique associé à votre entité
        return {
            "identifiers": {(DOMAIN, "solar_optimizer_device")},
            "name": "Solar Optimizer",
            # Autres attributs du périphérique ici
        }
