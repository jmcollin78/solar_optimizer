"""Protocol definition for Solar Optimizer algorithms."""

from typing import Protocol, runtime_checkable

from .managed_device import ManagedDevice


@runtime_checkable
class SolarOptimizerAlgorithm(Protocol):
    """Protocol that all optimization algorithms must implement."""

    def recuit_simule(
        self,
        devices: list[ManagedDevice],
        power_consumption: float,
        solar_power_production: float,
        sell_cost: float,
        buy_cost: float,
        sell_tax_percent: float,
        battery_soc: float,
        priority_weight: int,
    ) -> tuple[list[dict], float, float]:
        """Run one optimization cycle.

        Args:
            devices: list of managed devices to optimize
            power_consumption: current net grid consumption in W (including battery charge)
            solar_power_production: current solar production in W
            sell_cost: grid sell price in €/kWh
            buy_cost: grid buy price in €/kWh
            sell_tax_percent: tax applied to sold energy (%)
            battery_soc: battery state of charge 0-100
            priority_weight: how much device priority influences decisions (0-100)

        Returns:
            (solution, objective, total_power):
                solution: list of device dicts with at minimum 'name', 'state', 'requested_power'
                objective: scalar cost metric (lower = better)
                total_power: total W consumed by active devices in solution
        """
        ...
