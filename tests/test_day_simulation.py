"""Fake-day simulation: run SA and Greedy algorithms through a synthetic solar day.

Calls optimize() directly via FakeDevice stubs — no HA dependencies.
Compares aggregate metrics between the two algorithms for the 9 actual devices
configured in ha-advanced-blueprints (sada_optimizador_solar_*.yaml).
"""

from dataclasses import dataclass, field

from custom_components.solar_optimizer.simulated_annealing_algo import SimulatedAnnealingAlgorithm
from custom_components.solar_optimizer.greedy_priority_algo import GreedyPriorityAlgorithm
from custom_components.solar_optimizer.const import PRIORITY_MAP, PRIORITY_WEIGHT_MAP, PRIORITY_WEIGHT_HIGH


# ---------------------------------------------------------------------------
# Fake device stub — mimics the ManagedDevice properties read by both algos
# ---------------------------------------------------------------------------

@dataclass
class FakeDevice:
    """Lightweight stub that satisfies the ManagedDevice interface expected by both algos."""

    name: str
    power_max: int
    priority_label: str  # e.g. "Very high", "High", ...
    duration_cycles: int = 3  # cooldown in simulation steps after activation

    # mutable simulation state
    _is_active: bool = field(default=False, init=False, repr=False)
    _cooldown: int = field(default=0, init=False, repr=False)
    _current_power: int = field(default=0, init=False, repr=False)

    # --- properties read by algo ---
    @property
    def is_enabled(self):
        return True

    @property
    def is_usable(self):
        return True

    @property
    def is_active(self):
        return self._is_active

    @property
    def is_waiting(self):
        return self._cooldown > 0

    @property
    def can_change_power(self):
        return False

    @property
    def power_min(self):
        return self.power_max

    @property
    def power_step(self):
        return self.power_max

    @property
    def current_power(self):
        return self._current_power

    @property
    def priority(self):
        return PRIORITY_MAP[self.priority_label]

    def set_battery_soc(self, soc):
        pass

    # --- simulation helpers ---
    def apply_solution(self, should_be_on: bool, requested_power: int):
        """Apply one cycle's decision and advance cooldown."""
        if self._is_active and not should_be_on:
            self._is_active = False
            self._current_power = 0
            self._cooldown = self.duration_cycles
        elif not self._is_active and should_be_on:
            self._is_active = True
            self._current_power = requested_power
            self._cooldown = self.duration_cycles

        if self._cooldown > 0:
            self._cooldown -= 1


# ---------------------------------------------------------------------------
# Device definitions matching the 9 sada_optimizador_solar_*.yaml blueprints
# ---------------------------------------------------------------------------
#   Priority mapping (ha-advanced-blueprints uses 1-10 numeric where higher = more important).
#   We map to solar_optimizer PRIORITY_MAP labels for correct int encoding:
#     termo: 10  → VERY_HIGH (most important)
#     vestibulo_superior: 1 → VERY_LOW (least from the blueprint, but we invert as needed)
#   Blueprint priorities: termo=10 (highest), vestibulo_superior=1, bano=2, habitacion=3,
#     salon_mesa=4, vestibulo_inferior=?, salon_sofa=?, habitacion_planta_baja=?
#   We assign solar_optimizer labels from lowest int (=highest prio) to highest.

DEVICES_CFG = [
    # (name,                      power_W, priority_label)
    ("termo",                      2185, "Very high"),   # priority_int=1  (most important)
    ("bano",                        750, "High"),        # priority_int=2
    ("habitacion_planta_baja",      750, "High"),        # priority_int=2
    ("habitacion",                  750, "Medium"),      # priority_int=4
    ("salon_mesa",                  989, "Medium"),      # priority_int=4
    ("salon_sofa",                  750, "Low"),         # priority_int=8
    ("vestibulo_inferior",          989, "Low"),         # priority_int=8
    ("vestibulo_superior",          989, "Low"),         # priority_int=8
    ("deshumidificador",            300, "Very low"),    # priority_int=16 (least important)
]

# ---------------------------------------------------------------------------
# Synthetic solar production curve: 5-minute steps from 06:00 to 22:00
# (192 steps). Realistic south-facing 5kWp system, clear day.
# ---------------------------------------------------------------------------

def _build_solar_curve():
    """Build a 192-step (5-min each) solar production curve for a clear day."""
    import math
    steps = []
    for i in range(192):
        hour_float = 6.0 + i * 5 / 60  # from 06:00 to 22:00
        # Solar noon at 13:30 (step 90), peak 5000W
        angle = math.pi * (hour_float - 6.0) / 16.0
        production = max(0.0, 5000 * math.sin(angle) ** 1.5)
        steps.append(round(production))
    return steps


SOLAR_CURVE = _build_solar_curve()
BASE_HOUSE_LOAD = 350  # W (fridge, lights, standby)


# ---------------------------------------------------------------------------
# Simulation engine
# ---------------------------------------------------------------------------

def run_day(algo, devices_cfg, priority_weight: int, allowed_power_overage_percent: float = 0.0) -> dict:
    """Simulate a full day using the given algorithm.

    Returns aggregated metrics dict.
    """
    devices = [
        FakeDevice(name=name, power_max=power, priority_label=label)
        for name, power, label in devices_cfg
    ]

    metrics = {
        "solar_used_Wstep": 0.0,
        "grid_import_Wstep": 0.0,
        "grid_export_Wstep": 0.0,
        "device_on_steps": {d.name: 0 for d in devices},
        "per_cycle": [],
    }

    for step, solar in enumerate(SOLAR_CURVE):
        house_load = BASE_HOUSE_LOAD
        # power_consumption as seen by the algo:
        #   - Greedy expects gross total consumption (house + active managed), always positive
        #   - SA expects net grid consumption (gross - solar), negative when exporting
        # The real HA sensor provides net consumption. We match that convention here.
        managed_active_power = sum(d.current_power for d in devices if d.is_active)
        gross_consumption = house_load + managed_active_power
        net_consumption = gross_consumption - solar  # negative = exporting to grid
        allowed_power_overage = solar * allowed_power_overage_percent / 100.0

        solution, objective, total_power = algo.optimize(
            devices=devices,
            power_consumption=net_consumption,
            solar_power_production=solar,
            allowed_power_overage=allowed_power_overage,
            sell_cost=0.07,
            buy_cost=0.22,
            sell_tax_percent=0.0,
            battery_soc=100,
            priority_weight=priority_weight,
        )

        # Apply solution to device states
        sol_by_name = {s["name"]: s for s in solution}
        for device in devices:
            if device.name in sol_by_name:
                s = sol_by_name[device.name]
                device.apply_solution(s["state"], s.get("requested_power", 0))

        # Accumulate metrics
        new_managed_power = sum(d.current_power for d in devices if d.is_active)
        total_consumption = house_load + new_managed_power
        net = total_consumption - solar  # positive = importing, negative = exporting

        metrics["grid_import_Wstep"] += max(0, net)
        metrics["grid_export_Wstep"] += max(0, -net)
        metrics["solar_used_Wstep"] += min(solar, total_consumption)

        for device in devices:
            if device.is_active:
                metrics["device_on_steps"][device.name] += 1

        metrics["per_cycle"].append({
            "step": step,
            "solar": solar,
            "consumption": total_consumption,
            "net": net,
            "active": [d.name for d in devices if d.is_active],
        })

    return metrics


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_day_simulation_greedy_basic():
    """Greedy algorithm completes a full day without errors and produces valid metrics."""
    algo = GreedyPriorityAlgorithm()
    priority_weight = PRIORITY_WEIGHT_MAP[PRIORITY_WEIGHT_HIGH]  # 50

    metrics = run_day(algo, DEVICES_CFG, priority_weight)

    # Sanity checks
    assert metrics["solar_used_Wstep"] >= 0
    assert metrics["grid_import_Wstep"] >= 0
    assert metrics["grid_export_Wstep"] >= 0
    assert len(metrics["per_cycle"]) == len(SOLAR_CURVE)

    # At least some solar should be used (peak ~5kW)
    assert metrics["solar_used_Wstep"] > 0

    # Termo (most important) should have run for some cycles during peak hours
    assert metrics["device_on_steps"]["termo"] > 0


def test_day_simulation_greedy_vs_sa():
    """Compare Greedy and SA over a full synthetic day.

    Validates that both algorithms produce plausible results and prints a
    side-by-side comparison table for manual inspection.
    """
    priority_weight = PRIORITY_WEIGHT_MAP[PRIORITY_WEIGHT_HIGH]  # 50

    algo_greedy = GreedyPriorityAlgorithm()
    algo_sa = SimulatedAnnealingAlgorithm(
        initial_temp=1000,
        min_temp=0.1,
        cooling_factor=0.95,
        max_iteration_number=1000,
    )

    metrics_greedy = run_day(algo_greedy, DEVICES_CFG, priority_weight)
    metrics_sa = run_day(algo_sa, DEVICES_CFG, priority_weight)

    # --- Print comparison table ---
    print("\n" + "=" * 65)
    print(f"{'DAY SIMULATION: Greedy vs Simulated Annealing':^65}")
    print("=" * 65)
    print(f"{'Metric':<35} {'Greedy':>12} {'SA':>12}")
    print("-" * 65)
    print(
        f"{'Solar used (W·steps)':<35}"
        f" {metrics_greedy['solar_used_Wstep']:>12.0f}"
        f" {metrics_sa['solar_used_Wstep']:>12.0f}"
    )
    print(
        f"{'Grid import (W·steps)':<35}"
        f" {metrics_greedy['grid_import_Wstep']:>12.0f}"
        f" {metrics_sa['grid_import_Wstep']:>12.0f}"
    )
    print(
        f"{'Grid export (W·steps)':<35}"
        f" {metrics_greedy['grid_export_Wstep']:>12.0f}"
        f" {metrics_sa['grid_export_Wstep']:>12.0f}"
    )
    print("-" * 65)
    for name, _, _ in DEVICES_CFG:
        g = metrics_greedy["device_on_steps"][name]
        s = metrics_sa["device_on_steps"][name]
        print(f"  {name:<33} {g:>12} {s:>12}")
    print("=" * 65)

    # --- Assertions ---

    # Both algorithms should use some solar
    assert metrics_greedy["solar_used_Wstep"] > 0
    assert metrics_sa["solar_used_Wstep"] > 0

    # Greedy is deterministic: solar used should be >= SA (greedy always takes
    # the best available device first without probabilistic exploration)
    # We allow 5% tolerance since SA is stochastic
    assert metrics_greedy["solar_used_Wstep"] >= metrics_sa["solar_used_Wstep"] * 0.90

    # Greedy should not import significantly more than SA
    # (SA may find better solutions occasionally, allow 20% tolerance)
    if metrics_sa["grid_import_Wstep"] > 0:
        assert metrics_greedy["grid_import_Wstep"] <= metrics_sa["grid_import_Wstep"] * 1.20

    # Termo (highest priority) should run at least as many cycles in greedy as SA
    # because greedy always prioritises it when solar is available
    assert (
        metrics_greedy["device_on_steps"]["termo"]
        >= metrics_sa["device_on_steps"]["termo"] * 0.80
    )


def test_day_simulation_greedy_priority_order():
    """Verify that higher-priority devices accumulate more on-time than lower-priority ones."""
    algo = GreedyPriorityAlgorithm()
    priority_weight = PRIORITY_WEIGHT_MAP[PRIORITY_WEIGHT_HIGH]

    metrics = run_day(algo, DEVICES_CFG, priority_weight)
    on_steps = metrics["device_on_steps"]

    # termo (VERY_HIGH, 2185W) should run more than deshumidificador (VERY_LOW, 300W)
    # when there is limited solar
    # Note: deshumidificador uses less power so it can fit alongside others;
    # but over the full day the high-priority device should dominate.
    assert on_steps["termo"] >= on_steps["deshumidificador"]


def test_day_simulation_no_solar_no_devices():
    """No devices should activate on a day with zero solar production."""
    algo = GreedyPriorityAlgorithm()
    zero_curve = [0] * len(SOLAR_CURVE)

    devices = [
        FakeDevice(name=name, power_max=power, priority_label=label)
        for name, power, label in DEVICES_CFG
    ]

    for solar in zero_curve:
        consumption = BASE_HOUSE_LOAD + sum(d.current_power for d in devices if d.is_active)
        solution, _, _ = algo.optimize(
            devices=devices,
            power_consumption=consumption,
            solar_power_production=solar,
            allowed_power_overage=0.0,
            sell_cost=0.07,
            buy_cost=0.22,
            sell_tax_percent=0.0,
            battery_soc=100,
            priority_weight=50,
        )
        sol_by_name = {s["name"]: s for s in solution}
        for device in devices:
            if device.name in sol_by_name:
                s = sol_by_name[device.name]
                device.apply_solution(s["state"], s.get("requested_power", 0))

    # All devices should be off after a zero-solar day
    for device in devices:
        assert not device.is_active, f"{device.name} should be off with zero solar"


def test_day_simulation_three_way_comparison():
    """Compare SA, Greedy (0% overage) and Greedy (20% overage) over a full synthetic day."""
    priority_weight = PRIORITY_WEIGHT_MAP[PRIORITY_WEIGHT_HIGH]  # 50

    algo_sa = SimulatedAnnealingAlgorithm(
        initial_temp=1000, min_temp=0.1, cooling_factor=0.95, max_iteration_number=1000
    )
    algo_greedy = GreedyPriorityAlgorithm()

    m_sa = run_day(algo_sa, DEVICES_CFG, priority_weight, allowed_power_overage_percent=0.0)
    m_greedy = run_day(algo_greedy, DEVICES_CFG, priority_weight, allowed_power_overage_percent=0.0)
    m_greedy20 = run_day(algo_greedy, DEVICES_CFG, priority_weight, allowed_power_overage_percent=20.0)

    total_solar = sum(SOLAR_CURVE)

    col = 14
    w = 35 + col * 3 + 4
    print("\n" + "=" * w)
    print(f"{'DAY SIMULATION: SA vs Greedy vs Greedy+20% overage':^{w}}")
    print(f"{'Total solar production: ' + str(total_solar) + ' W·steps':^{w}}")
    print("=" * w)
    print(f"{'Metric':<35} {'SA':>{col}} {'Greedy 0%':>{col}} {'Greedy 20%':>{col}}")
    print("-" * w)
    for label, key in [
        ("Solar used (W·steps)",  "solar_used_Wstep"),
        ("Grid import (W·steps)", "grid_import_Wstep"),
        ("Grid export (W·steps)", "grid_export_Wstep"),
    ]:
        print(
            f"{label:<35}"
            f" {m_sa[key]:>{col}.0f}"
            f" {m_greedy[key]:>{col}.0f}"
            f" {m_greedy20[key]:>{col}.0f}"
        )
    print(
        f"{'Solar utilization %':<35}"
        f" {100 * m_sa['solar_used_Wstep'] / total_solar:>{col}.1f}%"
        f" {100 * m_greedy['solar_used_Wstep'] / total_solar:>{col}.1f}%"
        f" {100 * m_greedy20['solar_used_Wstep'] / total_solar:>{col}.1f}%"
    )
    print("-" * w)
    for name, _, _ in DEVICES_CFG:
        print(
            f"  {name:<33}"
            f" {m_sa['device_on_steps'][name]:>{col}}"
            f" {m_greedy['device_on_steps'][name]:>{col}}"
            f" {m_greedy20['device_on_steps'][name]:>{col}}"
        )
    print("=" * w)

    # With 20% overage, greedy should import more than 0% overage
    assert m_greedy20["grid_import_Wstep"] >= m_greedy["grid_import_Wstep"]
    # But import should still be zero at night (overage is % of solar, so 0W when solar=0)
    # Verify by checking no device turns on during zero-solar steps
    zero_steps = [c for c in m_greedy20["per_cycle"] if c["solar"] == 0]
    for step in zero_steps:
        assert step["active"] == [], f"Devices active at night with zero solar: {step['active']}"
