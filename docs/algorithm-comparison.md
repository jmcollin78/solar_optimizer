# Solar Optimizer — Algorithm Comparison

Findings from synthetic day simulation (534,168 W·steps total solar production,
192 × 5-min steps, 06:00–22:00, 5 kWp peak, 9 devices, 350 W base house load).

---

## Algorithms

### Simulated Annealing (SA) — default

Probabilistic metaheuristic. At each of 1,000 iterations it randomly flips
device states, evaluates a cost function, and keeps the new state with a
probability that decreases as "temperature" cools. Runs on every refresh cycle.

**Objective function:**

```
cost = consumption_coef × (1 − priority_weight)
     + priority_coef    × priority_weight
```

Where:

```
net_grid       = power_consumption + Σ(active_device_power) − solar_production
consumption_coef = coef_import × max(0,  net_grid)
                 + coef_rejets × max(0, -net_grid)

coef_import = buy_cost  / (buy_cost + sell_cost_after_tax)
coef_rejets = sell_cost / (buy_cost + sell_cost_after_tax)

priority_coef = Σ(priority_int × power / total_active_power)   # lower int = higher priority
```

SA **minimises** cost. `power_consumption` is the net grid sensor reading
(negative when exporting), so a large negative value means lots of surplus to
absorb.

### Greedy Priority

Deterministic, two-pass, O(n log n) per cycle.

**Pass 1 — turn ON, highest priority first:**
For each device sorted by ascending priority integer (VERY_HIGH=1 first):
- Skip if already on, not usable, or in cooldown.
- Turn on if `excess + allowed_power_overage ≥ device_power_min`.
- Otherwise, if `priority_weight > 0`: attempt load shedding — turn off the
  lowest-priority active device(s) that have `can_be_shed: true` until enough
  power is freed.

**Pass 2 — turn OFF, lowest priority first:**
While `excess < −allowed_power_overage` (deficit exceeds tolerance):
- Turn off the lowest-priority active device that is not in cooldown
  (or has `can_be_shed: true`).

`excess = −power_consumption` (net convention: negative consumption = surplus).

---

## Simulation results

```
Total solar production: 534,168 W·steps

Metric                              SA       Greedy 0%   Greedy 20%
--------------------------------------------------------------------
Solar used (W·steps)           522,576       497,469      526,639
Grid import (W·steps)            6,816         4,376       68,931
Grid export (W·steps)           11,592        36,699        7,529
Solar utilization %              97.8%         93.1%        98.6%
--------------------------------------------------------------------
  termo          (VERY_HIGH, 2185W)  38           107          112
  bano           (HIGH,       750W)  89           126          135
  habitacion_pb  (HIGH,       750W)  82            80           99
  habitacion     (MEDIUM,     750W)  63            29           64
  salon_mesa     (MEDIUM,     989W)  70             0            0
  salon_sofa     (LOW,        750W)  26             0           31
  vestibulo_inf  (LOW,        989W)  38             0            0
  vestibulo_sup  (LOW,        989W)  50             0            0
  deshumidif.    (VERY_LOW,   300W)  93            82          123
```

---

## Key findings

### 1. SA does not enforce priority ordering

`priority_weight` has almost no observable effect on which devices run.
Across all five levels (None / Low / Medium / High / Very high), SA's solar
utilisation stays at ~98% and device runtimes change only marginally.

**Why:** The dominant term in the objective is `consumption_coef`, which is
proportional to watts of import or export. Any device combination that absorbs
available surplus scores well, regardless of which devices it contains.
`priority_coef` only acts as a tiebreaker when two combinations have nearly
identical import/export profiles — which is rare.

**Concrete example at 4,000 W solar:**

| Combination | pw=0 | pw=0.5 | pw=0.75 |
|---|---|---|---|
| termo+bano+deshu (415 W export) | 100.2 | 51.4 | **27.0** |
| termo+bano (715 W export)       | 172.6 | 86.9 | 44.1 |
| termo only (1465 W export)      | 353.6 | 177.3 | 89.2 |

`termo+bano+deshu` wins at every priority weight even though `deshu` is
VERY_LOW priority, because it absorbs more solar.

**Consequence:** `deshumidificador` (300 W) runs more steps than `termo`
(2185 W) in SA. SA uses it as a "filler" device for leftover watts.

### 2. SA is governed by power fit, not priority

A device runs in SA when its power approximately matches available surplus:
- `termo` (2185 W) turns on when solar ≈ 2,200–2,500 W (narrow window)
- `deshumidificador` (300 W) fills leftover surplus at almost any level

Higher-power devices run fewer steps not because they are deprioritised, but
because the surplus window where they fit without causing import is narrower.

### 3. Greedy strictly respects priority ordering

`salon_mesa`, `vestibulo_inferior`, and `vestibulo_superior` (MEDIUM/LOW) run
zero steps in Greedy 0% because VERY_HIGH and HIGH devices consume all
available solar first. The lowest-priority device that runs is
`deshumidificador` because the 300 W footprint fits after the others.

### 4. Greedy 0% wastes solar at the edges of the day

At dawn/dusk, solar surplus is 200–500 W — not enough for any single device
after the cooldown gate. Result: 36,699 W·steps exported unused (vs 11,592 for
SA). SA finds small combinations that absorb these scraps; Greedy cannot because
it won't import even 1 W.

### 5. `allowed_power_overage_percent` closes the export gap

At 20% overage: Greedy is allowed to import up to `solar × 20%` watts to turn
on a device. This captures dawn/dusk surplus and raises utilisation from 93.1%
to 98.6% — nearly matching SA. Grid import increases from 4,376 to 68,931
W·steps, but export drops from 36,699 to 7,529.

The overage is a percentage of *current* solar production, so it is
automatically zero at night (solar = 0) — no device can turn on purely from
grid.

### 6. Pass 2 must respect the overage tolerance

If Pass 1 turns on a device using the overage allowance (accepting a small
deficit), Pass 2 must not immediately shed a lower-priority device to eliminate
that deficit — doing so would reduce total solar utilisation. Pass 2 only sheds
when `deficit > allowed_power_overage`. Without this fix, Greedy 20% produced
*lower* utilisation than Greedy 0%.

### 7. `power_consumption` convention matters

Both algorithms receive `power_consumption` from the HA net-grid sensor:
- **Positive** = importing from grid
- **Negative** = exporting to grid (surplus)

SA uses this directly as `_consommation_net` (already signed).
Greedy computes `excess = −power_consumption` (flip sign: negative consumption
= positive surplus available).

Passing gross consumption (always positive house load) to SA causes it to
conclude it is permanently importing from the grid and refuse to turn on any
device — a silent failure mode producing ~12% utilisation.

---

## When to use each algorithm

| Requirement | Recommendation |
|---|---|
| Variable-power device (EV charger, solar router) | **SA** — only SA models power steps |
| Strict priority ordering required | **Greedy Priority** |
| Low CPU / many devices | **Greedy Priority** — O(n log n) vs 1,000 iterations |
| Fine-grained import/export cost optimisation | **SA** — models buy/sell costs explicitly |
| Load shedding (interrupt lower-priority device for higher-priority one) | **Greedy Priority** + `can_be_shed: true` |
| Maximum solar absorption with controlled grid import | **Greedy Priority** + `allowed_power_overage_percent > 0` |

---

## Effective configuration levers per algorithm

### SA
- `buy_cost` / `sell_cost` ratio — primary control over import/export tolerance
- `priority_weight` — weak tiebreaker only; does not enforce ordering
- `max_on_time_per_day_min` on lower-priority devices — caps their runtime
- `check_usable_template` — conditionally exclude devices
- `min_on_time_per_day_min` — guarantees minimum runtime for important devices

### Greedy Priority
- `priority` per device — strict ordering enforced
- `priority_weight` — enables/disables load shedding
- `can_be_shed` per device — opts a device into forced-stop during cooldown
- `allowed_power_overage_percent` — controls grid import tolerance (0 = solar only)
