""" The Simulated Annealing (recuit simulé) algorithm"""
import logging
import random
import math
import copy

from .managed_device import ManagedDevice

_LOGGER = logging.getLogger(__name__)

DEBUG = False


class SimulatedAnnealingAlgorithm:
    """The class which implemenets the Simulated Annealing algorithm"""

    # Paramètres de l'algorithme de recuit simulé
    _temperature_initiale: float = 1000
    _temperature_minimale: float = 0.1
    _facteur_refroidissement: float = 0.95
    _nombre_iterations: float = 1000
    _switching_penalty_factor: float = 0.5  # Penalty for switching off active devices
    _last_suggested_penalty: float = None  # Last calculated suggested penalty
    _equipements: list[ManagedDevice]
    _puissance_totale_eqt_initiale: float
    _cout_achat: float = 15  # centimes
    _cout_revente: float = 10  # centimes
    _taxe_revente: float = 10  # pourcentage
    _consommation_net: float
    _production_solaire: float

    def __init__(
        self,
        initial_temp: float,
        min_temp: float,
        cooling_factor: float,
        max_iteration_number: int,
        switching_penalty_factor: float = 0.5,
        auto_switching_penalty: bool = False,
        clamp_price_step: float = 0.0,
    ):
        """Initialize the algorithm with values
        
        Args:
            initial_temp: Initial temperature for simulated annealing
            min_temp: Minimum temperature before stopping
            cooling_factor: Factor to reduce temperature each iteration
            max_iteration_number: Maximum number of iterations
            switching_penalty_factor: Penalty for switching off active devices (0-1)
            auto_switching_penalty: If True, automatically calculate optimal penalty
            clamp_price_step: If > 0, clamp prices to this step (e.g., 0.05 for 5 cents)
        """
        self._temperature_initiale = initial_temp
        self._temperature_minimale = min_temp
        self._facteur_refroidissement = cooling_factor
        self._nombre_iterations = max_iteration_number
        self._switching_penalty_factor = switching_penalty_factor
        self._auto_switching_penalty = auto_switching_penalty
        self._clamp_price_step = clamp_price_step
        _LOGGER.info(
            "Initializing the SimulatedAnnealingAlgorithm with initial_temp=%.2f min_temp=%.2f cooling_factor=%.2f max_iterations_number=%d switching_penalty_factor=%.2f auto_penalty=%s clamp_price_step=%.2f",
            self._temperature_initiale,
            self._temperature_minimale,
            self._facteur_refroidissement,
            self._nombre_iterations,
            self._switching_penalty_factor,
            self._auto_switching_penalty,
            self._clamp_price_step,
        )

    def _clamp_price(self, price: float) -> float:
        """Clamp price to configured step to reduce volatility
        
        Args:
            price: The raw price value
            
        Returns:
            Clamped price if clamp_price_step > 0, otherwise original price
        """
        if self._clamp_price_step <= 0:
            return price
        
        # Round to nearest step (e.g., 0.05 for 5-cent increments)
        clamped = round(price / self._clamp_price_step) * self._clamp_price_step
        
        if abs(clamped - price) > 0.001:  # Log only if there's a change
            _LOGGER.debug(
                "Clamped price from %.4f to %.4f (step=%.2f)",
                price,
                clamped,
                self._clamp_price_step
            )
        
        return clamped

    def _calculate_optimal_switching_penalty(
        self,
        devices: list[ManagedDevice],
        solar_production: float,
        household_consumption: float,
    ) -> float:
        """Calculate optimal switching penalty based on current conditions
        
        The penalty should be:
        - Higher when there's abundant solar power (avoid unnecessary switching)
        - Lower when power is scarce (allow more flexibility)
        - Scaled by the number and size of active devices
        - Balanced to prevent excessive switching costs
        
        Args:
            devices: List of managed devices
            solar_production: Current solar production in watts
            household_consumption: Base household consumption in watts
            
        Returns:
            Suggested switching penalty factor (0.0-1.0)
        """
        if solar_production <= 0:
            # No solar power, minimal penalty to allow aggressive optimization
            return 0.1
        
        # Count active devices and total active power capacity
        active_count = sum(1 for d in devices if d.is_active and d.is_enabled)
        total_active_capacity = sum(
            d.power_max for d in devices if d.is_active and d.is_enabled
        )
        
        if active_count == 0:
            # No active devices, use moderate penalty
            return 0.3
        
        # Calculate excess power ratio (how much headroom we have)
        available_power = solar_production - household_consumption
        if available_power <= 0:
            # Deficit scenario: lower penalty to allow optimization
            return 0.2
        
        # Calculate capacity utilization
        capacity_ratio = min(1.0, total_active_capacity / solar_production) if solar_production > 0 else 0
        
        # Calculate stability factor based on number of devices
        # More devices = higher penalty to avoid cascade switching
        device_factor = min(1.0, active_count / 5.0)  # Normalize to 5 devices
        
        # Calculate abundance factor (how much excess power we have)
        abundance_ratio = min(1.0, available_power / solar_production) if solar_production > 0 else 0
        
        # Combine factors:
        # - High abundance + many devices = high penalty (keep things stable)
        # - Low abundance + few devices = low penalty (optimize aggressively)
        penalty = 0.2 + (0.6 * abundance_ratio * device_factor)
        
        # Clamp to reasonable range
        penalty = max(0.1, min(0.9, penalty))
        
        # Store for later retrieval
        self._last_suggested_penalty = penalty
        
        _LOGGER.info(
            "Auto-calculated switching penalty: %.2f (active_devices=%d, capacity=%.0fW, production=%.0fW, available=%.0fW)",
            penalty,
            active_count,
            total_active_capacity,
            solar_production,
            available_power
        )
        
        return penalty

    @property
    def suggested_penalty(self) -> float | None:
        """Get the last calculated suggested switching penalty"""
        return self._last_suggested_penalty

    def recuit_simule(
        self,
        devices: list[ManagedDevice],
        household_consumption: float,
        solar_power_production: float,
        sell_cost: float,
        buy_cost: float,
        sell_tax_percent: float,
        battery_soc: float,
        priority_weight: int,
    ):
        """The entrypoint of the algorithm:
        You should give:
         - devices: a list of ManagedDevices. devices that are is_usable false are not taken into account
         - household_consumption: the base household power consumption in watts (positive value, excluding managed devices)
         - solar_power_production: the solar production power (already smoothed and with battery reserve applied if configured)
         - sell_cost: the sell cost of energy
         - buy_cost: the buy cost of energy
         - sell_tax_percent: a sell taxe applied to sell energy (a percentage)
         - battery_soc: the state of charge of the battery (0-100)
         - priority_weight: the weight of the priority in the cost calculation. 10 means 10%

         In return you will have:
          - best_solution: a list of object in whitch name, power_max and state are set,
          - best_objectif: the measure of the objective for that solution,
          - total_power_consumption: the total of power consumption for all equipments which should be activated (state=True)
        """
        if (
            len(devices) <= 0  # pylint: disable=too-many-boolean-expressions
            or household_consumption is None
            or solar_power_production is None
            or sell_cost is None
            or buy_cost is None
            or sell_tax_percent is None
        ):
            _LOGGER.info(
                "Not all information is available for Simulated Annealing algorithm to work. Calculation is abandoned"
            )
            return [], -1, -1

        _LOGGER.debug(
            "Calling recuit_simule with household_consumption=%.2f, solar_power_production=%.2f sell_cost=%.2f, buy_cost=%.2f, tax=%.2f%% devices=%s",
            household_consumption,
            solar_power_production,
            sell_cost,
            buy_cost,
            sell_tax_percent,
            devices,
        )
        
        # Apply price clamping if configured
        self._cout_achat = self._clamp_price(buy_cost)
        self._cout_revente = self._clamp_price(sell_cost)
        self._taxe_revente = sell_tax_percent
        self._consommation_net = household_consumption
        self._production_solaire = solar_power_production
        self._priority_weight = priority_weight / 100.0  # to get percentage

        # Always calculate suggested penalty for monitoring/tuning purposes
        suggested_penalty = self._calculate_optimal_switching_penalty(
            devices,
            solar_power_production,
            household_consumption
        )
        
        # Apply auto-calculated penalty if enabled
        if self._auto_switching_penalty:
            original_penalty = self._switching_penalty_factor
            self._switching_penalty_factor = suggested_penalty
            if abs(original_penalty - self._switching_penalty_factor) > 0.05:
                _LOGGER.info(
                    "Switching penalty adjusted from %.2f to %.2f (auto-mode)",
                    original_penalty,
                    self._switching_penalty_factor
                )

        # fix #131 - costs cannot be negative or 0
        if self._cout_achat <= 0 or self._cout_revente <= 0:
            _LOGGER.warning(
                "The cost of energy cannot be negative or 0. Buy cost=%.2f, Sell cost=%.2f. Setting them to 1",
                self._cout_achat,
                self._cout_revente,
            )
            self._cout_achat = self._cout_revente = 1

        self._equipements = []
        for _, device in enumerate(devices):
            if not device.is_enabled:
                _LOGGER.debug("%s is disabled. Forget it", device.name)
                continue

            device.set_battery_soc(battery_soc)
            usable = device.is_usable
            waiting = device.is_waiting
            # Track initial activity state for switching penalty calculation
            was_active = device.is_active
            # Force deactivation if active, not usable and not waiting
            # Note: We no longer force off based solely on current_power <= 0
            # This allows devices in standby or with telemetry lag to remain active
            force_state = (
                False
                if device.is_active and (not usable and not waiting)
                else device.is_active
            )
            self._equipements.append(
                {
                    "power_max": device.power_max,
                    "power_min": device.power_min,
                    "power_step": device.power_step,
                    "current_power": device.current_power,  # if force_state else 0,
                    # Initial Requested power is the current power if usable
                    "requested_power": device.current_power,  # if force_state else 0,
                    "name": device.name,
                    "state": force_state,
                    "is_usable": device.is_usable,
                    "is_waiting": waiting,
                    "can_change_power": device.can_change_power,
                    "priority": device.priority,
                    "was_active": was_active,  # Track initial activity for switching penalty
                }
            )
        if DEBUG:
            _LOGGER.debug("enabled _equipements are: %s", self._equipements)

        # Générer une solution initiale
        solution_actuelle = self.generer_solution_initiale(self._equipements)
        meilleure_solution = solution_actuelle
        meilleure_objectif = self.calculer_objectif(solution_actuelle)
        temperature = self._temperature_initiale

        for _ in range(self._nombre_iterations):
            # Générer un voisin
            objectif_actuel = self.calculer_objectif(solution_actuelle)
            if DEBUG:
                _LOGGER.debug("Objectif actuel : %.2f", objectif_actuel)

            voisin = self.permuter_equipement(solution_actuelle)

            # Calculer les objectifs pour la solution actuelle et le voisin
            objectif_voisin = self.calculer_objectif(voisin)
            if DEBUG:
                _LOGGER.debug("Objectif voisin : %2.f", objectif_voisin)

            # Accepter le voisin si son objectif est meilleur ou si la consommation totale n'excède pas la production solaire
            if objectif_voisin < objectif_actuel:
                _LOGGER.debug("---> On garde l'objectif voisin")
                solution_actuelle = voisin
                if objectif_voisin < meilleure_objectif:
                    _LOGGER.debug("---> C'est la meilleure jusque là")
                    meilleure_solution = voisin
                    meilleure_objectif = objectif_voisin
            else:
                # Accepter le voisin avec une certaine probabilité
                probabilite = math.exp(
                    (objectif_actuel - objectif_voisin) / temperature
                )
                if (seuil := random.random()) < probabilite:
                    solution_actuelle = voisin
                    if DEBUG:
                        _LOGGER.debug(
                            "---> On garde l'objectif voisin car seuil (%.2f) inférieur à proba (%.2f)",
                            seuil,
                            probabilite,
                        )
                else:
                    if DEBUG:
                        _LOGGER.debug("--> On ne prend pas")

            # Réduire la température
            temperature *= self._facteur_refroidissement
            if DEBUG:
                _LOGGER.debug(" !! Temperature %.2f", temperature)
            if temperature < self._temperature_minimale or meilleure_objectif <= 0:
                break

        return (
            meilleure_solution,
            meilleure_objectif,
            self.consommation_equipements(meilleure_solution),
        )

    def calculer_objectif(self, solution) -> float:
        """Calculate the objective: minimize grid import and maximize solar usage
        
        With household_consumption (positive W) representing base household load (excluding managed devices)
        and solar_production:
        - Total consumption = household_consumption + devices (from solution)
        - Net consumption = total_consumption - solar_production
        - If net > 0: importing from grid
        - If net < 0: exporting to grid
        
        Note: household_consumption already excludes currently active managed devices,
        so we add the full device power from the solution, not the difference.
        """

        puissance_totale_eqt = self.consommation_equipements(solution)

        # Calculate total consumption (base household + managed devices from solution)
        # household_consumption already has current devices subtracted, so we add solution devices directly
        total_consumption = self._consommation_net + puissance_totale_eqt

        # Calculate net consumption (total - production)
        # Positive = import, negative = export
        new_consommation_net = total_consumption - self._production_solaire

        new_rejets = 0 if new_consommation_net >= 0 else -new_consommation_net
        new_import = 0 if new_consommation_net < 0 else new_consommation_net
        new_consommation_solaire = min(
            self._production_solaire, total_consumption
        )
        new_consommation_totale = total_consumption

        if DEBUG:
            _LOGGER.debug(
                "Objective: devices in solution use %.3fW. Total consumption=%.3fW, Net consumption=%.3fW. Export=%.3fW. Import=%.3fW. Solar used=%.3fW",
                puissance_totale_eqt,
                total_consumption,
                new_consommation_net,
                new_rejets,
                new_import,
                new_consommation_solaire,
            )

        cout_revente_impose = self._cout_revente * (1.0 - self._taxe_revente / 100.0)
        coef_import = (self._cout_achat) / (self._cout_achat + cout_revente_impose)
        coef_rejets = (cout_revente_impose) / (self._cout_achat + cout_revente_impose)

        consumption_coef = coef_import * new_import + coef_rejets * new_rejets

        # calculate the priority coef as the sum of the priority of all devices
        # in the solution
        if puissance_totale_eqt > 0:
            priority_coef = sum(
                (equip["priority"] * equip["requested_power"] / puissance_totale_eqt)
                for i, equip in enumerate(solution) if equip["state"]
            )
        else:
            priority_coef = 0
        priority_weight = self._priority_weight

        # Calculate switching penalty: penalize turning OFF devices that were initially active
        # AND reward turning ON devices when there's abundant excess power
        # This encourages device stability and prevents frequent switching for marginal gains
        # Note: We use 'was_active' (initial state) rather than current_power to determine
        # if a device was running, which correctly handles standby/0W devices.
        # For variable power devices, changing power (up or down) is NOT penalized.
        # Only turning the device completely OFF/ON incurs a penalty/reward.
        switching_penalty = 0
        if self._switching_penalty_factor > 0:
            for equip in solution:
                # If device was initially active but solution turns it off, apply penalty
                was_active = equip.get("was_active", False)
                solution_turns_off = not equip["state"] and was_active
                solution_turns_on = equip["state"] and not was_active
                
                # Penalize turning OFF active devices
                if solution_turns_off:
                    # Penalty proportional to the device's power capacity
                    # Use power_max as the reference since the device was active
                    # Normalized by total production to make it scale-invariant
                    penalty_value = 0
                    if self._production_solaire > 0:
                        # Scale penalty by device size relative to production
                        power_max = equip.get("power_max", 0)
                        power_fraction = power_max / self._production_solaire
                        penalty_value = self._switching_penalty_factor * power_fraction
                        switching_penalty += penalty_value

                    if DEBUG:
                        _LOGGER.debug(
                            "Switching penalty for turning off %s (was_active=%s, power_max=%.2fW): +%.4f",
                            equip["name"],
                            was_active,
                            equip.get("power_max", 0),
                            penalty_value
                        )
                
                # Reward turning ON devices when there's excess power available
                # This encourages using available solar power rather than exporting it
                elif solution_turns_on:
                    # Calculate if solution would have excess power after turning on this device
                    devices_power = self.consommation_equipements(solution)
                    total_consumption = self._consommation_net + devices_power
                    net_consumption = total_consumption - self._production_solaire
                    
                    # If we'd still be exporting power (negative net), reward turning on
                    if net_consumption < 0:  # Still exporting after device is on
                        # Reward is smaller than penalty to prefer stability
                        # But encourages using available solar power
                        power_max = equip.get("power_max", 0)
                        export_after_on = -net_consumption
                        
                        # Only reward if device power is smaller than the excess
                        # This prevents turning on devices that would cause import
                        if power_max <= export_after_on:
                            if self._production_solaire > 0:
                                # Reward is 50% of the penalty factor to encourage use of excess
                                reward_factor = self._switching_penalty_factor * 0.5
                                power_fraction = power_max / self._production_solaire
                                reward_value = reward_factor * power_fraction
                                switching_penalty -= reward_value  # Negative = reward
                                
                                if DEBUG:
                                    _LOGGER.debug(
                                        "Switching reward for turning on %s with excess power (was_active=%s, power_max=%.2fW, excess=%.2fW): -%.4f",
                                        equip["name"],
                                        was_active,
                                        power_max,
                                        export_after_on,
                                        reward_value
                                    )

        ret = (
            consumption_coef * (1.0 - priority_weight)
            + priority_coef * priority_weight
            + switching_penalty
        )
        return ret

    def generer_solution_initiale(self, solution):
        """Generate the initial solution (which is the solution given in argument)
        
        Note: We no longer track initial power since household_consumption
        already excludes currently active devices.
        """
        return copy.deepcopy(solution)

    def consommation_equipements(self, solution):
        """The total power consumption for all active equipement"""
        return sum(
            equipement["requested_power"]
            for _, equipement in enumerate(solution)
            if equipement["state"]
        )

    def calculer_new_power(
        self, current_power, power_step, power_min, power_max, can_switch_off
    ):
        """Calcul une nouvelle puissance"""
        choices = []
        power_min_to_use = max(0, power_min - power_step) if can_switch_off else power_min

        # add all choices from current_power to power_min_to_use descending
        cp = current_power
        choice = -1
        while cp > power_min_to_use:
            cp -= power_step
            choices.append(choice)
            choice -= 1

        # if current_power > power_min_to_use:
        #    choices.append(-1)

        # add all choices from current_power to power_max ascending
        cp = current_power
        choice = 1
        while cp < power_max:
            cp += power_step
            choices.append(choice)
            choice += 1
        # if current_power < power_max:
        #     choices.append(1)

        if len(choices) <= 0:
            # No changes
            return current_power

        power_add = random.choice(choices) * power_step
        _LOGGER.debug("Adding %d power to current_power (%d)", power_add, current_power)
        requested_power = current_power + power_add
        _LOGGER.debug("New requested_power is %s", requested_power)
        return requested_power

    def permuter_equipement(self, solution):
        """Permuter le state d'un equipement eau hasard"""
        voisin = copy.deepcopy(solution)

        usable = [eqt for eqt in voisin if eqt["is_usable"]]

        if len(usable) <= 0:
            return voisin

        eqt = random.choice(usable)

        # name = eqt["name"]
        state = eqt["state"]
        can_change_power = eqt["can_change_power"]
        is_waiting = eqt["is_waiting"]

        # Current power is the last requested_power
        current_power = eqt.get("requested_power")
        power_max = eqt.get("power_max")
        power_step = eqt.get("power_step")
        if can_change_power:
            power_min = eqt.get("power_min")
        else:
            # If power is not manageable, min = max
            power_min = power_max

        # On veut gérer le is_waiting qui interdit d'allumer ou éteindre un eqt usable.
        # On veut pouvoir changer la puissance si l'eqt est déjà allumé malgré qu'il soit waiting.
        # Usable veut dire qu'on peut l'allumer/éteindre OU qu'on peut changer la puissance

        # if not can_change_power and is_waiting:
        #    -> on ne fait rien (mais ne devrait pas arriver car il ne serait pas usable dans ce cas)
        #
        # if state and can_change_power and is_waiting:
        #    -> change power mais sans l'éteindre (requested_power >= power_min)
        #
        # if state and can_change_power and not is_waiting:
        #    -> change power avec extinction possible
        #
        # if not state and not is_waiting
        #    -> allumage
        #
        # if state and not is_waiting
        #    -> extinction
        #
        if (not can_change_power and is_waiting) or (
            not state and can_change_power and is_waiting
        ):
            _LOGGER.debug("not can_change_power and is_waiting -> do nothing")
            return voisin

        if state and can_change_power and is_waiting:
            # calculated a new power but do not switch off (because waiting)
            requested_power = self.calculer_new_power(
                current_power, power_step, power_min, power_max, can_switch_off=False
            )
            assert (
                requested_power > 0
            ), "Requested_power should be > 0 because is_waiting is True"

        elif state and can_change_power and not is_waiting:
            # change power and accept switching off
            requested_power = self.calculer_new_power(
                current_power, power_step, power_min, power_max, can_switch_off=True
            )
            if requested_power < power_min:
                # deactivate the equipment
                eqt["state"] = False
                requested_power = 0

        elif not state and not is_waiting:
            # Allumage
            eqt["state"] = not state
            requested_power = power_min

        elif state and not is_waiting:
            # Extinction
            eqt["state"] = not state
            requested_power = 0

        elif "requested_power" not in locals():
            _LOGGER.error("We should not be there. eqt=%s", eqt)
            assert False, "Requested power n'a pas été calculé. Ce n'est pas normal"

        eqt["requested_power"] = requested_power

        if DEBUG:
            _LOGGER.debug(
                "      -- On permute %s puissance max de %.2f. Il passe à %s",
                eqt["name"],
                eqt["requested_power"],
                eqt["state"],
            )
        return voisin
