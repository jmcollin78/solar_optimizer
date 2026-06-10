"""Greedy priority-based algorithm for Solar Optimizer.

Adapted from ha-advanced-blueprints/PV_Excess_Control (pv_excess_control.py).

Two-pass deterministic algorithm:
  Pass 1 (highest priority first): turn ON devices whose power fits in current
          solar excess, or can be enabled by load-shedding lower-priority devices.
  Pass 2 (lowest priority first):  turn OFF devices while solar deficit persists.

Unlike the Simulated Annealing algorithm this is stateless, deterministic, and
O(n log n) per cycle instead of O(1000 * n). It does not model energy costs;
it purely maximises solar self-consumption while respecting device priorities.
"""

import copy
import logging

from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)


class GreedyPriorityAlgorithm:
    """Priority-based greedy algorithm with load shedding."""

    def optimize(
        self,
        devices: list[ManagedDevice],
        power_consumption: float,
        solar_power_production: float,
        allowed_power_overage: float,
        sell_cost: float,
        buy_cost: float,
        sell_tax_percent: float,
        battery_soc: float,
        priority_weight: int,
    ) -> tuple[list[dict], float, float]:
        """Run one greedy optimization cycle.

        Returns (solution, objective, total_power) matching the SA interface.
        """
        if not devices or power_consumption is None or solar_power_production is None:
            _LOGGER.info(
                "GreedyPriorityAlgorithm: missing inputs, skipping calculation"
            )
            return [], -1, -1

        _LOGGER.debug(
            "GreedyPriorityAlgorithm: power_consumption=%.1f solar=%.1f priority_weight=%d",
            power_consumption,
            solar_power_production,
            priority_weight,
        )

        # Build internal device dicts (mirrors SA's optimize preamble)
        equipements: list[dict] = []
        for device in devices:
            if not device.is_enabled:
                _LOGGER.debug("%s is disabled, skipping", device.name)
                continue

            device.set_battery_soc(battery_soc)
            usable = device.is_usable
            waiting = device.is_waiting
            force_state = (
                False
                if device.is_active
                and ((not usable and not waiting) or device.current_power <= 0)
                else device.is_active
            )
            power_min = device.power_min if device.power_min > 0 else device.power_max
            equipements.append(
                {
                    "name": device.name,
                    "power_max": device.power_max,
                    "power_min": power_min,
                    "power_step": device.power_step,
                    "current_power": device.current_power,
                    "requested_power": device.current_power,
                    "state": force_state,
                    "is_usable": usable,
                    "is_waiting": waiting,
                    "can_change_power": device.can_change_power,
                    "priority": device.priority,
                }
            )

        if not equipements:
            return [], -1, -1

        # excess > 0: solar surplus available; < 0: currently importing from grid.
        # power_consumption is net grid consumption (positive = importing, negative = exporting),
        # matching the real HA sensor. excess = -(net_consumption) = available solar headroom.
        excess = -power_consumption

        # Sort ascending by priority int: lower int = higher importance (VERY_HIGH=1)
        by_priority = sorted(equipements, key=lambda d: d["priority"])

        # Work on a mutable copy keyed by name for O(1) lookup during shedding
        solution: dict[str, dict] = {d["name"]: copy.copy(d) for d in by_priority}

        # ------------------------------------------------------------------ #
        # PASS 1: Turn on, highest priority first                             #
        # ------------------------------------------------------------------ #
        for dev in by_priority:
            name = dev["name"]
            s = solution[name]

            if s["state"]:
                continue  # already on
            if not s["is_usable"] or s["is_waiting"]:
                continue  # locked by cooldown or usability check

            power_needed = s["power_min"]

            if excess + allowed_power_overage >= power_needed:
                # Enough surplus (or within allowed overage) to turn on
                s["state"] = True
                s["requested_power"] = power_needed
                excess -= power_needed
                _LOGGER.debug(
                    "GreedyPriorityAlgorithm: turning ON %s (%.0fW, excess=%.0f, overage=%.0f)",
                    name,
                    power_needed,
                    excess + power_needed,
                    allowed_power_overage,
                )
            elif priority_weight > 0:
                # Try load shedding: free power from lower-priority active devices
                shed_available = self._calc_shed_power(solution, s["priority"])
                if excess + shed_available >= power_needed:
                    freed = self._shed_for(
                        solution, s["priority"], power_needed - excess
                    )
                    excess += freed
                    s["state"] = True
                    s["requested_power"] = power_needed
                    excess -= power_needed
                    _LOGGER.debug(
                        "GreedyPriorityAlgorithm: turning ON %s (%.0fW) via load shedding (freed=%.0f)",
                        name,
                        power_needed,
                        freed,
                    )

        # ------------------------------------------------------------------ #
        # PASS 2: Turn off, lowest priority first (highest int first)         #
        # Only shed when deficit exceeds the allowed overage — a deficit      #
        # within that tolerance is intentional (we chose to import for it).  #
        # ------------------------------------------------------------------ #
        for dev in reversed(by_priority):
            if excess >= -allowed_power_overage:
                break  # deficit is within tolerance, stop

            name = dev["name"]
            s = solution[name]

            if not s["state"]:
                continue

            # Can only turn off if not in cooldown
            if not s["is_waiting"]:
                _LOGGER.debug(
                    "GreedyPriorityAlgorithm: turning OFF %s (%.0fW) to reduce deficit=%.0f",
                    name,
                    s["requested_power"],
                    excess,
                )
                excess += s["requested_power"]
                s["state"] = False
                s["requested_power"] = 0

        solution_list = list(solution.values())
        total_power = sum(d["requested_power"] for d in solution_list if d["state"])

        # Objective: residual imbalance as fraction of production (lower = better).
        # 0.0 means perfect solar absorption.
        objective = abs(excess) / max(1.0, solar_power_production)

        _LOGGER.debug(
            "GreedyPriorityAlgorithm: total_power=%.0f excess=%.0f objective=%.4f",
            total_power,
            excess,
            objective,
        )
        return solution_list, objective, total_power

    # ---------------------------------------------------------------------- #
    # Helpers                                                                  #
    # ---------------------------------------------------------------------- #

    def _calc_shed_power(self, solution: dict[str, dict], above_priority: int) -> float:
        """Total W that could be freed by shedding lower-priority active devices."""
        return sum(
            d["requested_power"]
            for d in solution.values()
            if d["state"]
            and d["priority"] > above_priority
            and not d["is_waiting"]
        )

    def _shed_for(
        self, solution: dict[str, dict], above_priority: int, needed: float
    ) -> float:
        """Turn off lowest-priority devices until *needed* watts are freed.

        Returns the total watts actually freed.
        """
        freed = 0.0
        # Shed in reverse priority order: highest int (lowest importance) first
        candidates = sorted(
            [
                d
                for d in solution.values()
                if d["state"]
                and d["priority"] > above_priority
                and not d["is_waiting"]
            ],
            key=lambda d: -d["priority"],
        )
        for dev in candidates:
            if freed >= needed:
                break
            freed += dev["requested_power"]
            solution[dev["name"]]["state"] = False
            solution[dev["name"]]["requested_power"] = 0
            _LOGGER.debug(
                "GreedyPriorityAlgorithm: shed %s (%.0fW) for load shedding",
                dev["name"],
                dev["requested_power"] + freed - freed,  # original power
            )
        return freed
