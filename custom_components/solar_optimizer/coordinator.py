""" The data coordinator class """
import logging
import math
from datetime import timedelta


from homeassistant.core import HomeAssistant  # callback

from homeassistant.helpers.update_coordinator import (
    # CoordinatorEntity,
    DataUpdateCoordinator,
    # UpdateFailed,
)

from .const import DEFAULT_REFRESH_PERIOD_SEC, name_to_unique_id
from .managed_device import ManagedDevice
from .simulated_annealing_algo import SimulatedAnnealingAlgorithm

_LOGGER = logging.getLogger(__name__)


def get_safe_float(hass, entity_id: str):
    """Get a safe float state value for an entity.
    Return None if entity is not available"""
    state = hass.states.get(entity_id)
    if not state:
        return None
    float_val = float(state.state)
    return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val


class SolarOptimizerCoordinator(DataUpdateCoordinator):
    """The coordinator class which is used to coordinate all update"""

    _devices: list[ManagedDevice]
    _power_consumption_entity_id: str
    _power_production_entity_id: str

    _algo: SimulatedAnnealingAlgorithm

    def __init__(self, hass: HomeAssistant, config):
        """Initialize the coordinator"""
        # TODO mettre un Voluptuous schema pour verifier la config dans __init__
        refresh_period_sec = (
            config.get("refresh_period_sec") or DEFAULT_REFRESH_PERIOD_SEC
        )
        super().__init__(
            hass,
            _LOGGER,
            name="Solar Optimizer",
            update_interval=timedelta(seconds=refresh_period_sec),
        )  # pylint : disable=line-too-long
        self._devices = []
        try:
            for _, device in enumerate(config.get("devices")):
                _LOGGER.debug("Configuration of manageable device: %s", device)
                self._devices.append(ManagedDevice(hass, device))
        except Exception as err:
            _LOGGER.error(err)
            _LOGGER.error(
                "Your 'devices' configuration is wrong. SolarOptimizer will not be operational until you fix it"
            )
            raise err
        self._power_consumption_entity_id = config.get("power_consumption_entity_id")
        # if self._power_consumption_entity_id is None:
        #     err = HomeAssistantError(
        #         "Your 'power_consumption_entity_id' configuration is wrong. SolarOptimizer will not be operational until you fix it"
        #     )
        #     _LOGGER.error(err)
        #     raise err
        self._power_production_entity_id = config.get("power_production_entity_id")
        self._sell_cost_entity_id = config.get("sell_cost_entity_id")
        self._buy_cost_entity_id = config.get("buy_cost_entity_id")
        self._sell_tax_percent_entity_id = config.get("sell_tax_percent_entity_id")

        algo_config = config.get("algorithm")
        self._algo = SimulatedAnnealingAlgorithm(
            float(algo_config.get("initial_temp")),
            float(algo_config.get("min_temp")),
            float(algo_config.get("cooling_factor")),
            int(algo_config.get("max_iteration_number")),
        )
        self.config = config

    async def _async_update_data(self):
        _LOGGER.info("Refreshing Solar Optimizer calculation")

        calculated_data = {}

        # device_states = {}
        # Add a device state attributes
        for _, device in enumerate(self._devices):
            # Initialize current power if not set and is active
            if device.is_active and device.current_power == 0:
                power = device.power_max
                if device.can_change_power:
                    state = self.hass.states.get(device.power_entity_id)
                    if power is not None:
                        power = round(
                            float(state.state) * device.convert_power_divide_factor
                        )
                    else:
                        power = device.power_min
                    device.reset_next_date_available()
                    device.reset_next_date_available_power()

                device.init_power(power)
            if not device.is_active:
                device.init_power(0)

        # Add a power_consumption and power_production
        calculated_data["power_production"] = get_safe_float(
            self.hass, self._power_production_entity_id
        )

        calculated_data["power_consumption"] = get_safe_float(
            self.hass, self._power_consumption_entity_id
        )

        calculated_data["sell_cost"] = get_safe_float(
            self.hass, self._sell_cost_entity_id
        )

        calculated_data["buy_cost"] = get_safe_float(
            self.hass, self._buy_cost_entity_id
        )

        calculated_data["sell_tax_percent"] = get_safe_float(
            self.hass, self._sell_tax_percent_entity_id
        )

        best_solution, best_objective, total_power = self._algo.recuit_simule(
            self._devices,
            calculated_data["power_consumption"],
            calculated_data["power_production"],
            calculated_data["sell_cost"],
            calculated_data["buy_cost"],
            calculated_data["sell_tax_percent"],
        )

        calculated_data["best_solution"] = best_solution
        calculated_data["best_objective"] = best_objective
        calculated_data["total_power"] = total_power

        # Uses the result to turn on or off or change power
        for _, equipement in enumerate(best_solution):
            _LOGGER.debug("Dealing with best_solution for %s", equipement)
            name = equipement["name"]
            requested_power = equipement.get("requested_power")
            state = equipement["state"]
            device = self.get_device_name(name)
            calculated_data[name_to_unique_id(name)] = device
            if not device:
                continue
            is_active = device.is_active
            if is_active and not state:
                _LOGGER.debug("Extinction de %s", name)
                await device.deactivate()
            elif not is_active and state:
                _LOGGER.debug("Allumage de %s", name)
                await device.activate(requested_power)

            # Send change power if state is now on and change power is accepted and (power have change or eqt is just activated)
            if (
                state
                and device.can_change_power
                and (device.current_power != requested_power or not is_active)
            ):
                _LOGGER.debug(
                    "Change power of %s to %s",
                    equipement["name"],
                    requested_power,
                )
                await device.change_requested_power(requested_power)

        _LOGGER.debug("Calculated data are: %s", calculated_data)

        return calculated_data

    @property
    def devices(self) -> list[ManagedDevice]:
        """Get all the managed device"""
        return self._devices

    def get_device_name(self, name: str) -> ManagedDevice | None:
        """Returns the device which name is given in argument"""
        for _, device in enumerate(self._devices):
            if device.name == name:
                return device
        return None
