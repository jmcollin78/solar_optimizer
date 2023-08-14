""" A bonary sensor entity that holds the state of each managed_device """
import logging
from datetime import datetime
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_ON
from homeassistant.core import callback, HomeAssistant, State, Event
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.switch import (
    SwitchEntity,
)

from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)

from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from .const import (
    DOMAIN,
    name_to_unique_id,
    get_tz,
    EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
)
from .coordinator import SolarOptimizerCoordinator
from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, _, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup the entries of type Binary sensor, one for each ManagedDevice"""
    _LOGGER.debug("Calling switch.async_setup_entry")

    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN]["coordinator"]

    entities = []
    for _, device in enumerate(coordinator.devices):
        entity = ManagedDeviceSwitch(
            coordinator,
            hass,
            device.name,
            name_to_unique_id(device.name),
            device.entity_id,
        )
        if entity is not None:
            entities.append(entity)

        entity = ManagedDeviceEnable(hass, device)
        if entity is not None:
            entities.append(entity)

    async_add_entities(entities)


class ManagedDeviceSwitch(CoordinatorEntity, SwitchEntity):
    """The entity holding the algorithm calculation"""

    def __init__(self, coordinator, hass, name, idx, entity_id):
        _LOGGER.debug("Adding ManagedDeviceSwitch for %s", name)
        super().__init__(coordinator, context=idx)
        self._hass: HomeAssistant = hass
        self.idx = idx
        self._attr_name = "Solar Optimizer " + name
        self._attr_unique_id = "solar_optimizer_" + idx
        self._entity_id = entity_id

        # Try to get the state if it exists
        device: ManagedDevice = None
        if (device := coordinator.get_device_by_unique_id(self.idx)) is not None:
            self._attr_is_on = device.is_active
        else:
            self._attr_is_on = None

    async def async_added_to_hass(self) -> None:
        """The entity have been added to hass, listen to state change of the underlying entity"""
        await super().async_added_to_hass()

        # Arme l'écoute de la première entité
        listener_cancel = async_track_state_change_event(
            self.hass,
            [self._entity_id],
            self._on_state_change,
        )
        # desarme le timer lors de la destruction de l'entité
        self.async_on_remove(listener_cancel)

        # desarme le timer lors de la destruction de l'entité
        self.async_on_remove(
            self._hass.bus.async_listen(
                event_type=EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
                listener=self._on_enable_state_change,
            )
        )

    @callback
    async def _on_enable_state_change(self, event: Event) -> None:
        """Triggered when the ManagedDevice enable state have change"""

        # is it for me ?
        if (
            not event.data
            or (device_id := event.data.get("device_unique_id")) != self.idx
        ):
            return

        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(device_id)
        ):
            return

        _LOGGER.info(
            "Changing enabled state for %s to %s", device_id, device.is_enabled
        )

        self.update_custom_attributes(device)
        self.async_write_ha_state()

    @callback
    async def _on_state_change(self, event: Event) -> None:
        """The entity have change its state"""
        _LOGGER.info(
            "Appel de on_state_change à %s avec l'event %s", datetime.now(), event
        )

        if not event.data:
            return

        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(self.idx)
        ):
            return

        new_state: State = event.data.get("new_state")
        # old_state: State = event.data.get("old_state")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("Pas d'état disponible. Evenement ignoré")
            return

        # On recherche la date de l'event pour la stocker dans notre état
        new_state = new_state.state == STATE_ON
        if new_state == self._attr_is_on:
            return

        self._attr_is_on = new_state
        # On sauvegarde le nouvel état
        self.update_custom_attributes(device)
        self.async_write_ha_state()

    def update_custom_attributes(self, device):
        """Add some custom attributes to the entity"""
        current_tz = get_tz(self._hass)
        self._attr_extra_state_attributes: dict(str, str) = {
            "is_enabled": device.is_enabled,
            "is_active": device.is_active,
            "is_waiting": device.is_waiting,
            "is_usable": device.is_usable,
            "can_change_power": device.can_change_power,
            "current_power": device.current_power,
            "requested_power": device.requested_power,
            "duration_sec": device.duration_sec,
            "duration_power_sec": device.duration_power_sec,
            "power_min": device.power_min,
            "power_max": device.power_max,
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
        _LOGGER.debug("Calling _handle_coordinator_update for %s", self._attr_name)

        if not self.coordinator or not self.coordinator.data:
            _LOGGER.debug("No coordinator found or no data...")
            return

        device: ManagedDevice = self.coordinator.data.get(self.idx)
        if not device:
            # it is possible to not have device in coordinator update (if device is not enabled)
            _LOGGER.debug("No device %s found ...", self.idx)
            return

        self._attr_is_on = device.is_active
        self.update_custom_attributes(device)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if not self.coordinator or not self.coordinator.data:
            return

        _LOGGER.info("Turn_on Solar Optimizer switch %s", self._attr_name)
        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(self.idx)
        ):
            return

        if not self._attr_is_on:
            await device.activate()
            self._attr_is_on = True
            self.update_custom_attributes(device)
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        if not self.coordinator or not self.coordinator.data:
            return

        _LOGGER.info("Turn_on Solar Optimizer switch %s", self._attr_name)
        # search for coordinator and device
        if not self.coordinator or not (
            device := self.coordinator.get_device_by_unique_id(self.idx)
        ):
            return

        if self._attr_is_on:
            await device.deactivate()
            self._attr_is_on = False
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

    @property
    def get_attr_extra_state_attributes(self):
        """Get the extra state attributes for the entity"""
        return self._attr_extra_state_attributes


class ManagedDeviceEnable(SwitchEntity, RestoreEntity):
    """The that enables the ManagedDevice optimisation with"""

    _device: ManagedDevice

    def __init__(self, hass: HomeAssistant, device: ManagedDevice):
        self._hass: HomeAssistant = hass
        self._device = device
        self._attr_name = "Enable Solar Optimizer " + device.name
        self._attr_unique_id = "solar_optimizer_enable_" + name_to_unique_id(
            device.name
        )
        self._attr_is_on = True

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
        return "mdi:check"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        # Récupérer le dernier état sauvegardé de l'entité
        last_state = await self.async_get_last_state()

        # Si l'état précédent existe, vous pouvez l'utiliser
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"
        else:
            # Si l'état précédent n'existe pas, initialisez l'état comme vous le souhaitez
            self._attr_is_on = True

        # this breaks the start of integration
        self.update_device_enabled()

    @callback
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        self._attr_is_on = True
        self.async_write_ha_state()
        self.update_device_enabled()

    @callback
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        self._attr_is_on = False
        self.async_write_ha_state()
        self.update_device_enabled()

    def update_device_enabled(self) -> None:
        """Update the device is enabled flag"""
        if not self._device:
            return

        self._device.set_enable(self._attr_is_on)
