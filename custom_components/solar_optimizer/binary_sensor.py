""" A binary sensor entity exposing the manual override state of each managed_device """

import logging
from datetime import datetime

from homeassistant.core import callback, HomeAssistant, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.binary_sensor import BinarySensorEntity, DOMAIN as BINARY_SENSOR_DOMAIN

from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .coordinator import SolarOptimizerCoordinator
from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup the entries of type Binary sensor, one for each ManagedDevice"""
    _LOGGER.debug("Calling binary_sensor.async_setup_entry")

    coordinator: SolarOptimizerCoordinator = SolarOptimizerCoordinator.get_coordinator()

    if entry.data[CONF_DEVICE_TYPE] == CONF_DEVICE_CENTRAL:
        return

    unique_id = name_to_unique_id(entry.data[CONF_NAME])
    device = coordinator.get_device_by_unique_id(unique_id)
    if device is None:
        _LOGGER.error("Calling binary_sensor.async_setup_entry in error cause device with unique_id %s not found", unique_id)
        return

    async_add_entities([ManagedDeviceOverride(hass, device)])


class ManagedDeviceOverride(BinarySensorEntity, RestoreEntity):
    """Exposes whether Solar Optimizer's management of a device is currently paused
    because of a manual override (the user or an automation acted directly on the
    device, bypassing the algorithm's own decision). See ManagedDevice.trigger_manual_override
    / clear_override in managed_device.py."""

    def __init__(self, hass: HomeAssistant, device: ManagedDevice):
        idx = name_to_unique_id(device.name)
        self._hass = hass
        self._device = device
        self.idx = idx
        self._attr_has_entity_name = True
        self.entity_id = f"{BINARY_SENSOR_DOMAIN}.solar_optimizer_override_{idx}"
        self._attr_name = "Override"
        self._attr_unique_id = "solar_optimizer_override_" + idx
        self._attr_is_on = device.override_active

    async def async_added_to_hass(self) -> None:
        """The entity have been added to hass, restore state and listen for changes"""
        await super().async_added_to_hass()

        # Restore the override state from the last persisted state (HA restart)
        last_state = await self.async_get_last_state()
        if last_state and last_state.state == "on":
            since_str = last_state.attributes.get("override_since")
            baseline = last_state.attributes.get("override_baseline_state")
            try:
                since = datetime.fromisoformat(since_str) if since_str else None
            except (ValueError, TypeError) as err:
                _LOGGER.warning("Could not restore override_since for %s: %s", self._device.name, err)
                since = None
            self._device.set_override_state(True, since, baseline)
            self._attr_is_on = True
            _LOGGER.info("Restored manual override state for %s (since=%s)", self._device.name, since)

        self.async_on_remove(
            self._hass.bus.async_listen(
                event_type=EVENT_TYPE_SOLAR_OPTIMIZER_ENABLE_STATE_CHANGE,
                listener=self._on_enable_state_change,
            )
        )

        self.update_custom_attributes()
        self.async_write_ha_state()

    @callback
    async def _on_enable_state_change(self, event: Event) -> None:
        """Triggered when the ManagedDevice enable/override state have changed"""
        if not event.data or event.data.get("device_unique_id") != self.idx:
            return

        new_is_on = event.data.get("override_active", False)
        if new_is_on == self._attr_is_on:
            return

        self._attr_is_on = new_is_on
        self.update_custom_attributes()
        self.async_write_ha_state()

    def update_custom_attributes(self) -> None:
        """Add some custom attributes to the entity"""
        self._attr_extra_state_attributes: dict(str, str) = {
            "override_since": self._device.override_since.isoformat() if self._device.override_since else None,
            "override_baseline_state": self._device.override_baseline_state,
        }

    @property
    def icon(self) -> str | None:
        return "mdi:hand-back-right" if self._attr_is_on else "mdi:hand-back-right-off"

    @property
    def device_info(self) -> DeviceInfo | None:
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._device.name)},
            name="Solar Optimizer-" + self._device.name,
            manufacturer=DEVICE_MANUFACTURER,
            model=DEVICE_MODEL,
        )

    @property
    def get_attr_extra_state_attributes(self):
        """Get the extra state attributes for the entity"""
        return self._attr_extra_state_attributes
