""" A sensor entity that holds the result of the recuit simule algorithm """
import logging
from datetime import datetime, timedelta
from homeassistant.const import (
    UnitOfPower,
    UnitOfTime,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_ON,
)
from homeassistant.core import callback, HomeAssistant, Event, State
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    DOMAIN as SENSOR_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    DEVICE_MANUFACTURER,
    INTEGRATION_MODEL,
    name_to_unique_id,
    DEVICE_MODEL,
    seconds_to_hms,
)
from .coordinator import SolarOptimizerCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup the entries of type Sensor"""

    # Sets the config entries values to SolarOptimizer coordinator
    coordinator: SolarOptimizerCoordinator = hass.data[DOMAIN]["coordinator"]

    entities = []
    for _, device in enumerate(coordinator.devices):
        entity = TodayOnTimeSensor(
            hass,
            device,
        )
        if entity is not None:
            entities.append(entity)

    entities.append(SolarOptimizerSensorEntity(coordinator, hass, "best_objective"))
    entities.append(SolarOptimizerSensorEntity(coordinator, hass, "total_power"))
    entities.append(SolarOptimizerSensorEntity(coordinator, hass, "power_production"))
    entities.append(
        SolarOptimizerSensorEntity(coordinator, hass, "power_production_brut")
    )
    entities.append(SolarOptimizerSensorEntity(coordinator, hass, "battery_soc"))

    async_add_entities(entities, False)

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
            or (value := self.coordinator.data.get(self.idx)) is None
        ):
            _LOGGER.debug("No coordinator found or no data...")
            return

        self._attr_native_value = value
        self.async_write_ha_state()

    @property
    def device_info(self):
        # Retournez des informations sur le périphérique associé à votre entité
        return {
            "model": INTEGRATION_MODEL,
            "manufacturer": DEVICE_MANUFACTURER,
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
        elif self.idx == "battery_soc":
            return "mdi:battery"
        else:
            return "mdi:solar-power-variant"

    @property
    def device_class(self) -> SensorDeviceClass | None:
        if self.idx == "best_objective":
            return SensorDeviceClass.MONETARY
        elif self.idx == "battery_soc":
            return SensorDeviceClass.BATTERY
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
        elif self.idx == "battery_soc":
            return "%"
        else:
            return UnitOfPower.WATT


class TodayOnTimeSensor(SensorEntity, RestoreEntity):
    """Gives the time in minute in which the device was on for a day"""

    _entity_component_unrecorded_attributes = (
        SensorEntity._entity_component_unrecorded_attributes.union(
            frozenset(
                {
                    "max_on_time_per_day_sec",
                    "max_on_time_per_day_min",
                    "max_on_time_hms",
                    "on_time_hms",
                }
            )
        )
    )

    def __init__(self, hass: HomeAssistant, device) -> None:
        """Initialize the sensor"""
        self.hass = hass
        idx = name_to_unique_id(device.name)
        self._attr_name = "On time today"
        self._attr_has_entity_name = True
        self.entity_id = f"{SENSOR_DOMAIN}.on_time_today_solar_optimizer_{idx}"
        self._attr_unique_id = "solar_optimizer_on_time_today_" + idx
        self._attr_native_value = None
        self._entity_id = device.entity_id
        self._device = device
        self._last_datetime_on = None

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

        # Add listener to midnight to reset the counter
        self.async_on_remove(
            async_track_time_change(
                hass=self.hass, action=self._on_midnight, hour=0, minute=0, second=0
            )
        )

        # Add a listener to calculate OnTine at each minute
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._on_update_on_time,
                interval=timedelta(minutes=1),
            )
        )

        # restore the last value or set to 0
        self._attr_native_value = 0
        old_state = await self.async_get_last_state()
        if old_state is not None:
            if old_state.state is not None:
                self._attr_native_value = round(float(old_state.state))

            old_value = old_state.attributes.get("last_datetime_on")
            if old_value is not None:
                self._last_datetime_on = datetime.fromisoformat(old_value)

        self.update_custom_attributes()
        self.async_write_ha_state()

    @callback
    async def _on_state_change(self, event: Event) -> None:
        """The entity have change its state"""
        now = self._device.now
        _LOGGER.info("Call of on_state_change at %s with event %s", now, event)

        if not event.data:
            return

        new_state: State = event.data.get("new_state")
        old_state: State = event.data.get("old_state")

        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            _LOGGER.debug("No available state. Event is ignored")
            return

        need_save = False
        # We search for the date of the event
        new_state = new_state.state == STATE_ON
        old_state = old_state is not None and old_state.state == STATE_ON
        if new_state and not old_state:
            _LOGGER.debug("The managed device becomes on - store the last_datetime_on")
            self._last_datetime_on = now
            need_save = True

        if not new_state and old_state and self._last_datetime_on is not None:
            _LOGGER.debug("The managed device becomes off - increment the delta time")
            self._attr_native_value += round(
                (now - self._last_datetime_on).total_seconds()
            )
            self._last_datetime_on = None
            need_save = True

        # On sauvegarde le nouvel état
        if need_save:
            self.update_custom_attributes()
            self.async_write_ha_state()
            self._device.set_on_time(self._attr_native_value)

    @callback
    async def _on_midnight(self, _=None) -> None:
        """Called each day at midnight to reset the counter"""
        self._attr_native_value = 0

        _LOGGER.info("Call of _on_midnight to reset onTime")

        # reset _last_datetime_on to now if it was active. Here we lose the time on of yesterday but it is too late I can't do better.
        # Else you will have two point with the same date and not the same value (one with value + duration and one with 0)
        if self._last_datetime_on is not None:
            self._last_datetime_on = self._device.now

        self.update_custom_attributes()
        self.async_write_ha_state()
        self._device.set_on_time(self._attr_native_value)

    @callback
    async def _on_update_on_time(self, _=None) -> None:
        """Called priodically to update the on_time sensor"""
        now = self._device.now
        _LOGGER.info("Call of _on_update_on_time at %s", now)

        if self._last_datetime_on is not None:
            self._attr_native_value += round(
                (now - self._last_datetime_on).total_seconds()
            )
            self._last_datetime_on = now
            self.update_custom_attributes()
            self.async_write_ha_state()

            self._device.set_on_time(self._attr_native_value)

    def update_custom_attributes(self):
        """Add some custom attributes to the entity"""
        self._attr_extra_state_attributes: dict(str, str) = {
            "last_datetime_on": self._last_datetime_on,
            "max_on_time_per_day_min": round(self._device.max_on_time_per_day_sec / 60),
            "max_on_time_per_day_sec": self._device.max_on_time_per_day_sec,
            "on_time_hms": seconds_to_hms(self._attr_native_value),
            "max_on_time_hms": seconds_to_hms(self._device.max_on_time_per_day_sec),
        }

    @property
    def icon(self) -> str | None:
        return "mdi:timer-play"

    @property
    def device_info(self) -> DeviceInfo | None:
        # Retournez des informations sur le périphérique associé à votre entité
        return {
            "model": DEVICE_MODEL,
            "manufacturer": DEVICE_MANUFACTURER,
            "identifiers": {(DOMAIN, self._device.name)},
            "name": "Solar Optimizer-" + self._device.name,
        }

    @property
    def device_class(self) -> SensorDeviceClass | None:
        return SensorDeviceClass.DURATION

    @property
    def state_class(self) -> SensorStateClass | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return UnitOfTime.SECONDS

    @property
    def suggested_display_precision(self) -> int | None:
        """Return the suggested number of decimal digits for display."""
        return 0

    @property
    def last_datetime_on(self) -> datetime | None:
        """Returns the last_datetime_on"""
        return self._last_datetime_on

    @property
    def get_attr_extra_state_attributes(self):
        """Get the extra state attributes for the entity"""
        return self._attr_extra_state_attributes
