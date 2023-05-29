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
    _equipements: list[ManagedDevice]
    _puissance_totale_eqt_initiale: float
    _cout_achat: float = 15  # centimes
    _cout_revente: float = 10  # centimes
    _taxe_revente: float = 0.13  # pourcentage
    _consommation_net: float
    _production_solaire: float

    def __init__(
        self,
        initial_temp: float,
        min_temp: float,
        cooling_factor: float,
        max_iteration_number: int,
    ):
        """Initialize the algorithm with values"""
        self._temperature_initiale = initial_temp
        self._temperature_minimale = min_temp
        self._facteur_refroidissement = cooling_factor
        self._nombre_iterations = max_iteration_number
        _LOGGER.info(
            "Initializing the SimulatedAnnealingAlgorithm with initial_temp=%.2f min_temp=%.2f cooling_factor=%.2f max_iterations_number=%d",
            self._temperature_initiale,
            self._temperature_minimale,
            self._facteur_refroidissement,
            self._nombre_iterations,
        )

    def recuit_simule(
        self,
        devices: list[ManagedDevice],
        power_consumption: float,
        solar_power_production: float,
        sell_cost: float,
        buy_cost: float,
        sell_tax_percent: float,
    ):
        """The entrypoint of the algorithm:
        You should give:
         - devices: a list of ManagedDevices. devices that are is_usable false are not taken into account
         - power_consumption: the current power consumption. Can be negeative if power is given back to grid
         - solar_power_production: the solar production power
         - sell_cost: the sell cost of energy
         - buy_cost: the buy cost of energy
         - sell_tax_percent: a sell taxe applied to sell energy (a percentage)

         In return you will have:
          - best_solution: a list of object in whitch name, power_max and state are set,
          - best_objectif: the measure of the objective for that solution,
          - total_power_consumption: the total of power consumption for all equipments which should be activated (state=True)
        """
        if (
            len(devices) <= 0  # pylint: disable=too-many-boolean-expressions
            or power_consumption is None
            or solar_power_production is None
            or sell_cost is None
            or buy_cost is None
            or sell_tax_percent is None
        ):
            _LOGGER.info(
                "Not all informations are available for Simulated Annealign algorithm to work. Calculation is abandoned"
            )
            return [], -1, -1

        _LOGGER.debug(
            "Calling recuit_simule with power_consumption=%.2f, solar_power_production=%.2f sell_cost=%.2f, buy_cost=%.2f, tax=%.2f%% devices=%s",
            power_consumption,
            solar_power_production,
            sell_cost,
            buy_cost,
            sell_tax_percent,
            devices,
        )
        self._cout_achat = buy_cost
        self._cout_revente = sell_cost
        self._taxe_revente = sell_tax_percent
        self._consommation_net = power_consumption
        self._production_solaire = solar_power_production

        self._equipements = []
        for _, device in enumerate(devices):
            self._equipements.append(
                {
                    "power_max": device.power_max,
                    "name": device.name,
                    "state": device.is_active,
                    "is_usable": device.is_usable,
                }
            )
        if DEBUG:
            _LOGGER.debug("_equipements are: %s", self._equipements)

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
                _LOGGER.debug("Objecttif voisin : %2.f", objectif_voisin)

            # Accepter le voisin si son objectif est meilleur ou si la consommation totale n'excède pas la production solaire
            if objectif_voisin < objectif_actuel:
                if DEBUG:
                    _LOGGER.debug("---> On garde l'objectif voisin")
                solution_actuelle = voisin
                if objectif_voisin < self.calculer_objectif(meilleure_solution):
                    if DEBUG:
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
            if temperature < self._temperature_minimale:
                break

        return (
            meilleure_solution,
            meilleure_objectif,
            self.consommation_equipements(meilleure_solution),
        )

    def calculer_objectif(self, solution) -> float:
        """Calcul de l'objectif : minimiser le surplus de production solaire
        rejets = 0 if consommation_net >=0 else -consommation_net
        consommation_solaire = min(production_solaire, production_solaire - rejets)
        consommation_totale = consommation_net + consommation_solaire
        """

        puissance_totale_eqt = self.consommation_equipements(solution)
        diff_puissance_totale_eqt = (
            puissance_totale_eqt - self._puissance_totale_eqt_initiale
        )

        new_consommation_net = self._consommation_net + diff_puissance_totale_eqt
        new_rejets = 0 if new_consommation_net >= 0 else -new_consommation_net
        new_import = 0 if new_consommation_net < 0 else new_consommation_net
        new_consommation_solaire = min(
            self._production_solaire, self._production_solaire - new_rejets
        )
        new_consommation_totale = (
            new_consommation_net + new_rejets
        ) + new_consommation_solaire
        if DEBUG:
            _LOGGER.debug(
                "Objectif : cette solution ajoute %.3fW a la consommation initial. Nouvelle consommation nette=%.3fW. Nouveaux rejets=%.3fW. Nouvelle conso totale=%.3fW",
                diff_puissance_totale_eqt,
                new_consommation_net,
                new_rejets,
                new_consommation_totale,
            )

        cout_revente_impose = self._cout_revente * (1.0 - self._taxe_revente / 100.0)
        coef_import = (self._cout_achat) / (self._cout_achat + cout_revente_impose)
        coef_rejets = (cout_revente_impose) / (self._cout_achat + cout_revente_impose)

        return coef_import * new_import + coef_rejets * new_rejets

    def generer_solution_initiale(self, solution):
        """Generate the initial solution (which is the solution given in argument) and calculate the total initial power"""
        self._puissance_totale_eqt_initiale = self.consommation_equipements(solution)
        return copy.deepcopy(solution)

    def consommation_equipements(self, solution):
        """The total power consumption for all active equipement"""
        return sum(
            equipement["power_max"]
            for _, equipement in enumerate(solution)
            if equipement["state"]
        )

    def permuter_equipement(self, solution):
        """Permuter le state d'un equipement eau hasard"""
        voisin = copy.deepcopy(solution)

        usable = [eqt for eqt in voisin if eqt["is_usable"]]

        eqt = random.choice(usable)
        eqt["state"] = not eqt["state"]
        if DEBUG:
            _LOGGER.debug(
                "      -- On permute %s puissance max de %.2f. Il passe à %s",
                eqt["name"],
                eqt["power_max"],
                eqt["state"],
            )
        return voisin


# Exemple de données des équipements (puissance et durée)
# equipements = [
#    {"nom": "Equipement A", "puissance": 1000, "duree": 4, "state": False},
#    {"nom": "Equipement B", "puissance": 500, "duree": 2, "state": False},
#    {"nom": "Equipement C", "puissance": 800, "duree": 3, "state": False},
#    {"nom": "Equipement D", "puissance": 2100, "duree": 1, "state": False},
#    {"nom": "Equipement E", "puissance": 300, "duree": 3, "state": False},
#    {"nom": "Equipement F", "puissance": 500, "duree": 5, "state": False},
#    {"nom": "Equipement G", "puissance": 1200, "duree": 2, "state": False},
#    {"nom": "Equipement H", "puissance": 5000, "duree": 3, "state": False},
#    {"nom": "Equipement I", "puissance": 700, "duree": 4, "state": False},
# ]


# Données de production solaire
# production_solaire = 4000

# Consommation totale du logement (< 0 -> production solaire)
# consommation_net = -2350

# puissance_totale_eqt_initiale = 0

# Paramètres de l'algorithme de recuit simulé
# temperature_initiale = 1000
# temperature_minimale = 0.1
# facteur_refroidissement = 0.95
# nombre_iterations = 1000
#
# cout_achat = 15  # centimes
# cout_revente = 10  # centimes
# taxe_revente = 0.13  # pourcentage


# Résolution du problème avec l'algorithme de recuit simulé
# solution_optimale = recuit_simule()

# Affichage de la solution optimale
# _LOGGER.debug("Solution optimale :")
# for equipement in solution_optimale:
#     if equipement["state"]:
#         _LOGGER.debug(
#             "- ",
#             equipement["nom"],
#             "(",
#             equipement["puissance"],
#             "W) etat:",
#             equipement["state"],
#         )
#
# # Calcul de la puissance totale consommée et de la durée totale
# puissance_totale = sum(
#     equipement["puissance"] for equipement in solution_optimale if equipement["state"]
# )
#
# _LOGGER.debug("Puissance totale consommée :", puissance_totale)
# _LOGGER.debug("Valeur de l'objectif: ", calculer_objectif(solution_optimale))
