"""The data coordinator class"""

import logging
import math
from collections import deque
from datetime import datetime, timedelta, time
from typing import Any

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.components.select import SelectEntity

from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from homeassistant.util.unit_conversion import BaseUnitConverter, PowerConverter

from homeassistant.config_entries import ConfigEntry

from .const import (
    DEFAULT_REFRESH_PERIOD_SEC,
    name_to_unique_id,
    SOLAR_OPTIMIZER_DOMAIN,
    DEFAULT_RAZ_TIME,
    DEFAULT_SMOOTHING_PRODUCTION_WINDOW_MIN,
    DEFAULT_SMOOTHING_CONSUMPTION_WINDOW_MIN,
    DEFAULT_SMOOTHING_HOUSEHOLD_WINDOW_MIN,
    DEFAULT_BATTERY_RECHARGE_RESERVE_W,
    DEFAULT_BATTERY_RECHARGE_RESERVE_BEFORE_SMOOTHING,
    DEFAULT_MIN_EXPORT_MARGIN_W,
    DEFAULT_SWITCHING_PENALTY_FACTOR,
    CONF_SMOOTHING_PRODUCTION_WINDOW_MIN,
    CONF_SMOOTHING_CONSUMPTION_WINDOW_MIN,
    CONF_SMOOTHING_HOUSEHOLD_WINDOW_MIN,
    CONF_BATTERY_RECHARGE_RESERVE_W,
    CONF_BATTERY_RECHARGE_RESERVE_BEFORE_SMOOTHING,
    CONF_MIN_EXPORT_MARGIN_W,
    CONF_SWITCHING_PENALTY_FACTOR,
)
from .managed_device import ManagedDevice
from .simulated_annealing_algo import SimulatedAnnealingAlgorithm

_LOGGER = logging.getLogger(__name__)


def get_safe_float(hass, entity_id: str, unit: str = None):
    """Get a safe float state value for an entity.
    Return None if entity is not available"""
    if entity_id is None or not (state := hass.states.get(entity_id)) or state.state == "unknown" or state.state == "unavailable":
        return None

    float_val = float(state.state)

    if (unit is not None) and ("device_class" in state.attributes) and (state.attributes["device_class"] == "power"):
        float_val = PowerConverter.convert(float_val, state.attributes["unit_of_measurement"], unit)

    return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val


class SolarOptimizerCoordinator(DataUpdateCoordinator):
    """The coordinator class which is used to coordinate all update"""

    hass: HomeAssistant

    def __init__(self, hass: HomeAssistant, config):
        """Initialize the coordinator"""
        SolarOptimizerCoordinator.hass = hass
        self._devices: list[ManagedDevice] = []
        self._power_consumption_entity_id: str = None
        self._power_production_entity_id: str = None
        self._subscribe_to_events: bool = False
        self._unsub_events = None
        self._sell_cost_entity_id: str = None
        self._buy_cost_entity_id: str = None
        self._sell_tax_percent_entity_id: str = None
        self._smooth_production: bool = True
        self._smoothing_window_min: int = 0
        self._production_window: deque = deque()
        self._smoothing_consumption_window_min: int = 0
        self._consumption_window: deque = deque()
        self._smoothing_household_window_min: int = 0
        self._household_window: deque = deque()
        self._last_production: float = 0.0
        self._battery_soc_entity_id: str = None
        self._battery_charge_power_entity_id: str = None
        self._battery_recharge_reserve_w: float = 0.0
        self._battery_recharge_reserve_before_smoothing: bool = False
        self._min_export_margin_w: float = 0.0
        self._raz_time: time = None

        self._central_config_done = False
        self._priority_weight_entity = None

        super().__init__(hass, _LOGGER, name="Solar Optimizer")

        init_temp = 1000
        min_temp = 0.05
        cooling_factor = 0.95
        max_iteration_number = 1000
        switching_penalty_factor = DEFAULT_SWITCHING_PENALTY_FACTOR  # Will be updated from config entry

        if config and (algo_config := config.get("algorithm")):
            init_temp = float(algo_config.get("initial_temp", 1000))
            min_temp = float(algo_config.get("min_temp", 0.05))
            cooling_factor = float(algo_config.get("cooling_factor", 0.95))
            max_iteration_number = int(algo_config.get("max_iteration_number", 1000))

        self._algo = SimulatedAnnealingAlgorithm(init_temp, min_temp, cooling_factor, max_iteration_number, switching_penalty_factor)
        self.config = config

    async def configure(self, config: ConfigEntry) -> None:
        """Configure the coordinator from configEntry of the integration"""
        refresh_period_sec = config.data.get("refresh_period_sec") or DEFAULT_REFRESH_PERIOD_SEC
        self.update_interval = timedelta(seconds=refresh_period_sec)
        self._schedule_refresh()

        self._power_consumption_entity_id = config.data.get("power_consumption_entity_id")
        self._power_production_entity_id = config.data.get("power_production_entity_id")
        self._subscribe_to_events = config.data.get("subscribe_to_events")

        if self._unsub_events is not None:
            self._unsub_events()
            self._unsub_events = None

        if self._subscribe_to_events:
            self._unsub_events = async_track_state_change_event(self.hass, [self._power_consumption_entity_id, self._power_production_entity_id], self._async_on_change)

        self._sell_cost_entity_id = config.data.get("sell_cost_entity_id")
        self._buy_cost_entity_id = config.data.get("buy_cost_entity_id")
        self._sell_tax_percent_entity_id = config.data.get("sell_tax_percent_entity_id")
        self._battery_soc_entity_id = config.data.get("battery_soc_entity_id")
        self._battery_charge_power_entity_id = config.data.get("battery_charge_power_entity_id")
        self._smooth_production = config.data.get("smooth_production") is True
        self._smoothing_window_min = int(config.data.get(CONF_SMOOTHING_PRODUCTION_WINDOW_MIN, DEFAULT_SMOOTHING_PRODUCTION_WINDOW_MIN))
        self._production_window = deque()
        self._smoothing_consumption_window_min = int(config.data.get(CONF_SMOOTHING_CONSUMPTION_WINDOW_MIN, DEFAULT_SMOOTHING_CONSUMPTION_WINDOW_MIN))
        self._consumption_window = deque()
        self._smoothing_household_window_min = int(config.data.get(CONF_SMOOTHING_HOUSEHOLD_WINDOW_MIN, DEFAULT_SMOOTHING_HOUSEHOLD_WINDOW_MIN))
        self._household_window = deque()
        self._last_production = 0.0
        self._battery_recharge_reserve_w = float(config.data.get(CONF_BATTERY_RECHARGE_RESERVE_W, DEFAULT_BATTERY_RECHARGE_RESERVE_W))
        self._battery_recharge_reserve_before_smoothing = bool(config.data.get(CONF_BATTERY_RECHARGE_RESERVE_BEFORE_SMOOTHING, DEFAULT_BATTERY_RECHARGE_RESERVE_BEFORE_SMOOTHING))
        self._min_export_margin_w = float(config.data.get(CONF_MIN_EXPORT_MARGIN_W, DEFAULT_MIN_EXPORT_MARGIN_W))

        # Update switching penalty factor from config entry
        switching_penalty_factor = float(config.data.get(CONF_SWITCHING_PENALTY_FACTOR, DEFAULT_SWITCHING_PENALTY_FACTOR))
        self._algo._switching_penalty_factor = switching_penalty_factor
        _LOGGER.info("Switching penalty factor set to: %.2f", switching_penalty_factor)
        
        # Update auto switching penalty and price clamping settings
        auto_switching_penalty = bool(config.data.get(CONF_AUTO_SWITCHING_PENALTY, DEFAULT_AUTO_SWITCHING_PENALTY))
        clamp_price_step = float(config.data.get(CONF_CLAMP_PRICE_STEP, DEFAULT_CLAMP_PRICE_STEP))
        self._algo._auto_switching_penalty = auto_switching_penalty
        self._algo._clamp_price_step = clamp_price_step
        _LOGGER.info("Auto switching penalty: %s, Price clamp step: %.2f", auto_switching_penalty, clamp_price_step)
        
        # Initialize suggested penalty tracking
        self._suggested_penalty = None

        self._raz_time = datetime.strptime(config.data.get("raz_time") or DEFAULT_RAZ_TIME, "%H:%M").time()
        self._central_config_done = True

    async def on_ha_started(self, _) -> None:
        """Listen the homeassistant_started event to initialize the first calculation"""
        _LOGGER.info("First initialization of Solar Optimizer")

    def _apply_smoothing_window(self, window: deque, window_minutes: int, raw_value: float, field_name: str) -> float:
        """Apply sliding-window smoothing to a value.

        Args:
            window: deque containing (timestamp, value) tuples
            window_minutes: window size in minutes
            raw_value: current raw value
            field_name: name of field for logging

        Returns:
            Smoothed value (rounded to integer)
        """
        if window_minutes <= 0:
            return raw_value

        now = datetime.now()

        # Add current value to window
        window.append((now, raw_value))

        # Remove old entries outside the window
        cutoff_time = now - timedelta(minutes=window_minutes)
        while window and window[0][0] < cutoff_time:
            window.popleft()

        # Calculate average of values in window
        if window:
            avg_value = sum(val for _, val in window) / len(window)
            smoothed = round(avg_value)
            _LOGGER.debug("Smoothing %s: raw=%s, smoothed=%s, window_size=%s, window_minutes=%s", field_name, raw_value, smoothed, len(window), window_minutes)
            return smoothed
        else:
            return raw_value

    async def _async_on_change(self, event: Event[EventStateChangedData]) -> None:
        await self.async_refresh()
        self._schedule_refresh()

    async def _async_update_data(self):
        _LOGGER.info("Refreshing Solar Optimizer calculation")

        calculated_data = {}

        # Add a device state attributes
        for _, device in enumerate(self._devices):
            # Initialize current power depending or reality
            device.set_current_power_with_device_state()

        # Add a power_consumption and power_production
        power_production = get_safe_float(self.hass, self._power_production_entity_id, "W")
        if power_production is None:
            _LOGGER.warning("Power production is not valued. Solar Optimizer will be disabled")
            return None

        # Always store raw production in power_production_brut
        calculated_data["power_production_brut"] = power_production

        # Apply battery recharge reserve before smoothing if configured
        battery_reserve_reduction_active = False
        if self._battery_recharge_reserve_before_smoothing and self._battery_recharge_reserve_w > 0:
            soc_for_reserve = get_safe_float(self.hass, self._battery_soc_entity_id)
            battery_soc_for_reserve = soc_for_reserve if soc_for_reserve is not None else 0
            if battery_soc_for_reserve < 100:
                reserved_watts = min(self._battery_recharge_reserve_w, power_production)
                power_production = max(0, power_production - reserved_watts)
                calculated_data["power_production_reserved"] = reserved_watts
                battery_reserve_reduction_active = True
                _LOGGER.debug(
                    "Battery reserve applied BEFORE smoothing: reserved=%sW, battery_soc=%s%%, remaining_production=%sW", reserved_watts, battery_soc_for_reserve, power_production
                )
            else:
                calculated_data["power_production_reserved"] = 0
        else:
            calculated_data["power_production_reserved"] = 0

        calculated_data["battery_reserve_reduction_active"] = battery_reserve_reduction_active

        # Apply sliding-window smoothing to production if enabled
        if not self._smooth_production or self._smoothing_window_min <= 0:
            # No smoothing: use raw production (possibly with reserve already subtracted)
            calculated_data["power_production"] = power_production
            calculated_data["power_production_smoothing_mode"] = "none"
            calculated_data["power_production_window_count"] = 0
        else:
            # Sliding-window smoothing enabled
            calculated_data["power_production"] = self._apply_smoothing_window(self._production_window, self._smoothing_window_min, power_production, "power_production")
            calculated_data["power_production_smoothing_mode"] = "sliding_window"
            calculated_data["power_production_window_count"] = len(self._production_window)

        # Get raw consumption and apply smoothing if configured
        power_consumption_raw = get_safe_float(self.hass, self._power_consumption_entity_id, "W")
        calculated_data["power_consumption_brut"] = power_consumption_raw

        if self._smoothing_consumption_window_min > 0 and power_consumption_raw is not None:
            calculated_data["power_consumption"] = self._apply_smoothing_window(
                self._consumption_window, self._smoothing_consumption_window_min, power_consumption_raw, "power_consumption"
            )
            calculated_data["power_consumption_smoothing_mode"] = "sliding_window"
            calculated_data["power_consumption_window_count"] = len(self._consumption_window)
        else:
            calculated_data["power_consumption"] = power_consumption_raw
            calculated_data["power_consumption_smoothing_mode"] = "none"
            calculated_data["power_consumption_window_count"] = 0

        calculated_data["sell_cost"] = get_safe_float(self.hass, self._sell_cost_entity_id)

        calculated_data["buy_cost"] = get_safe_float(self.hass, self._buy_cost_entity_id)

        calculated_data["sell_tax_percent"] = get_safe_float(self.hass, self._sell_tax_percent_entity_id)

        soc = get_safe_float(self.hass, self._battery_soc_entity_id)
        calculated_data["battery_soc"] = soc if soc is not None else 0

        # Get raw battery charge power (for diagnostics only, no smoothing)
        charge_power_raw = get_safe_float(self.hass, self._battery_charge_power_entity_id)
        calculated_data["battery_charge_power_brut"] = charge_power_raw if charge_power_raw is not None else 0
        calculated_data["battery_charge_power"] = charge_power_raw if charge_power_raw is not None else 0
        calculated_data["battery_charge_power_smoothing_mode"] = "none"
        calculated_data["battery_charge_power_window_count"] = 0

        calculated_data["priority_weight"] = self.priority_weight

        # Calculate total power currently distributed to managed devices
        # The household consumption sensor includes all devices, so we need to subtract
        # the power of currently active managed devices to get base household consumption
        total_current_distributed_power = sum(device.current_power for device in self._devices if device.current_power > 0)
        _LOGGER.debug("Total currently distributed power to managed devices: %.2fW", total_current_distributed_power)

        # Compute base household consumption (excluding managed devices)
        # The power_consumption_entity_id includes ALL consumption (household + managed devices)
        # We subtract currently active managed devices to get the base household consumption
        raw_consumption = calculated_data["power_consumption"] if calculated_data["power_consumption"] is not None else 0

        # Calculate base household consumption (without managed devices)
        # If this goes negative, it means devices are consuming more than the sensor reading
        # (can happen due to reporting lag). We clamp this to zero by design.
        # A negative raw intermediate value only indicates transient report lag, not a true deficit.
        base_household_raw = raw_consumption - total_current_distributed_power

        # Log when a deficit is observed (for diagnostics), but do not treat it as a blocker
        if base_household_raw < 0:
            _LOGGER.debug("Household deficit observed (likely sensor/reporting lag): %.2fW. Clamping base to 0.", abs(base_household_raw))

        # Clamp base household consumption to non-negative
        household_consumption_raw = max(0, base_household_raw)

        # Apply smoothing to household consumption if configured
        # This helps compensate for short-duration devices like fridges, kettles, etc.
        if self._smoothing_household_window_min > 0:
            household_consumption = self._apply_smoothing_window(self._household_window, self._smoothing_household_window_min, household_consumption_raw, "household_consumption")
            # After smoothing, ensure it stays non-negative (by design)
            household_consumption = max(0, household_consumption)
            calculated_data["household_consumption_smoothing_mode"] = "sliding_window"
            calculated_data["household_consumption_window_count"] = len(self._household_window)
        else:
            household_consumption = household_consumption_raw
            calculated_data["household_consumption_smoothing_mode"] = "none"
            calculated_data["household_consumption_window_count"] = 0

        calculated_data["household_consumption"] = household_consumption
        calculated_data["household_consumption_brut"] = household_consumption_raw
        calculated_data["total_current_distributed_power"] = total_current_distributed_power

        # Apply battery recharge reserve after smoothing if configured (and not already applied before)
        if not self._battery_recharge_reserve_before_smoothing and self._battery_recharge_reserve_w > 0 and calculated_data["battery_soc"] < 100:
            reserved_watts = min(self._battery_recharge_reserve_w, calculated_data["power_production"])
            calculated_data["power_production"] = max(0, calculated_data["power_production"] - reserved_watts)
            calculated_data["power_production_reserved"] = reserved_watts
            calculated_data["battery_reserve_reduction_active"] = True
            _LOGGER.debug(
                "Battery reserve applied AFTER smoothing: reserved=%sW, battery_soc=%s%%, remaining_production=%sW",
                reserved_watts,
                calculated_data["battery_soc"],
                calculated_data["power_production"],
            )
        elif not self._battery_recharge_reserve_before_smoothing:
            # Only set to 0 if we're in "after smoothing" mode and conditions aren't met
            calculated_data["power_production_reserved"] = 0
            calculated_data["battery_reserve_reduction_active"] = False

        # Apply minimum export margin when battery is at 100%
        # This keeps a small buffer to prevent importing/battery discharge
        effective_production = calculated_data["power_production"]
        if calculated_data["battery_soc"] >= 100 and self._min_export_margin_w > 0:
            effective_production = max(0, calculated_data["power_production"] - self._min_export_margin_w)
            calculated_data["min_export_margin_active"] = True
            calculated_data["min_export_margin_reduction"] = self._min_export_margin_w
            _LOGGER.debug("Min export margin applied at 100%% SOC: margin=%sW, effective_production=%sW", self._min_export_margin_w, effective_production)
        else:
            calculated_data["min_export_margin_active"] = False
            calculated_data["min_export_margin_reduction"] = 0

        # Calculate available excess power for optimization
        # Formula: PV Production (with margin if battery at 100%) - base household consumption
        # The base household consumption is already clamped to >= 0, so we compute excess correctly
        # even when there was a transient reporting deficit
        available_excess_power = max(0, effective_production - household_consumption)

        calculated_data["available_excess_power"] = available_excess_power
        _LOGGER.debug(
            "Available excess power before optimization: %.2fW (effective_production=%.2fW, household_base=%.2fW)",
            available_excess_power,
            effective_production,
            household_consumption,
        )

        #
        # Call Algorithm Recuit simulé
        #
        best_solution, best_objective, total_power = self._algo.recuit_simule(
            self._devices,
            household_consumption,
            effective_production,  # Use effective production (with min export margin if battery at 100%)
            calculated_data["sell_cost"],
            calculated_data["buy_cost"],
            calculated_data["sell_tax_percent"],
            calculated_data["battery_soc"],
            calculated_data["priority_weight"],
        )
        
        # Update suggested penalty from algorithm (if auto-calculation was done)
        self._suggested_penalty = self._algo.suggested_penalty

        calculated_data["best_solution"] = best_solution
        calculated_data["best_objective"] = best_objective
        calculated_data["total_power"] = total_power
        calculated_data["suggested_penalty"] = self._suggested_penalty

        # Uses the result to turn on or off or change power
        should_log = False
        for _, equipement in enumerate(best_solution):
            name = equipement["name"]
            requested_power = equipement.get("requested_power")
            state = equipement["state"]
            _LOGGER.debug("Dealing with best_solution for %s - %s", name, equipement)
            device = self.get_device_by_name(name)
            if not device:
                continue

            old_requested_power = device.requested_power
            is_active = device.is_active
            should_force_offpeak = device.should_be_forced_offpeak
            if should_force_offpeak:
                _LOGGER.debug("%s - we should force %s name", self, name)
            if is_active and not state and not should_force_offpeak:
                _LOGGER.debug("Extinction de %s", name)
                should_log = True
                old_requested_power = 0
                await device.deactivate()
            elif not is_active and (state or should_force_offpeak):
                _LOGGER.debug("Allumage de %s", name)
                should_log = True
                old_requested_power = requested_power
                await device.activate(requested_power)

            # Send change power if state is now on and change power is accepted and (power have change or eqt is just activated)
            if state and device.can_change_power and (device.current_power != requested_power or not is_active):
                _LOGGER.debug(
                    "Change power of %s to %s",
                    equipement["name"],
                    requested_power,
                )
                should_log = True
                await device.change_requested_power(requested_power)

            device.set_requested_power(old_requested_power)

            # Add updated data to the result
            calculated_data[name_to_unique_id(name)] = device

        if should_log:
            _LOGGER.info("Calculated data are: %s", calculated_data)
        else:
            _LOGGER.debug("Calculated data are: %s", calculated_data)

        return calculated_data

    @classmethod
    def get_coordinator(cls) -> Any:
        """Get the coordinator from the hass.data"""
        if not hasattr(SolarOptimizerCoordinator, "hass") or SolarOptimizerCoordinator.hass is None or SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN] is None:
            return None

        return SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN]["coordinator"]

    @classmethod
    def reset(cls) -> Any:
        """Reset the coordinator from the hass.data"""
        if not hasattr(SolarOptimizerCoordinator, "hass") or SolarOptimizerCoordinator.hass is None or SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN] is None:
            return

        SolarOptimizerCoordinator.hass.data[SOLAR_OPTIMIZER_DOMAIN]["coordinator"] = None

    @property
    def is_central_config_done(self) -> bool:
        """Return True if the central config is done"""
        return self._central_config_done

    @property
    def devices(self) -> list[ManagedDevice]:
        """Get all the managed device"""
        return self._devices

    def get_device_by_name(self, name: str) -> ManagedDevice | None:
        """Returns the device which name is given in argument"""
        for _, device in enumerate(self._devices):
            if device.name == name:
                return device
        return None

    def get_device_by_unique_id(self, uid: str) -> ManagedDevice | None:
        """Returns the device which name is given in argument"""
        for _, device in enumerate(self._devices):
            if device.unique_id == uid:
                return device
        return None

    def set_priority_weight_entity(self, entity: SelectEntity):
        """Set the priority weight entity"""
        self._priority_weight_entity = entity

    @property
    def priority_weight(self) -> int:
        """Get the priority weight"""
        if self._priority_weight_entity is None:
            return 0
        return self._priority_weight_entity.current_priority_weight

    @property
    def raz_time(self) -> time:
        """Get the raz time with default to DEFAULT_RAZ_TIME"""
        return self._raz_time

    @property
    def suggested_switching_penalty(self) -> float | None:
        """Get the last calculated suggested switching penalty"""
        return self._suggested_penalty

    def add_device(self, device: ManagedDevice):
        """Add a new device to the list of managed device"""
        # Append or replace the device
        for i, dev in enumerate(self._devices):
            if dev.unique_id == device.unique_id:
                self._devices[i] = device
                return
        self._devices.append(device)

    def remove_device(self, unique_id: str):
        """Remove a device from the list of managed device"""
        for i, dev in enumerate(self._devices):
            if dev.unique_id == unique_id:
                self._devices.pop(i)
                return
