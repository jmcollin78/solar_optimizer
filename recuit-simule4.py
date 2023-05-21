import random
import math
import copy

# Exemple de données des équipements (puissance et durée)
equipements = [
    {"nom": "Equipement A", "puissance": 1000, "duree": 4, "state": False},
    {"nom": "Equipement B", "puissance": 500, "duree": 2, "state": False},
    {"nom": "Equipement C", "puissance": 800, "duree": 3, "state": False},
    {"nom": "Equipement D", "puissance": 2100, "duree": 1, "state": False},
    {"nom": "Equipement E", "puissance": 300, "duree": 3, "state": False},
    {"nom": "Equipement F", "puissance": 500, "duree": 5, "state": False},
    {"nom": "Equipement G", "puissance": 1200, "duree": 2, "state": False},
    {"nom": "Equipement H", "puissance": 5000, "duree": 3, "state": False},
    {"nom": "Equipement I", "puissance": 700, "duree": 4, "state": False}
]

# Données de production solaire
production_solaire = 4000

# Consommation totale du logement (< 0 -> production solaire)
consommation_net = -2350

puissance_totale_eqt_initiale = 0

# Paramètres de l'algorithme de recuit simulé
temperature_initiale = 1000
temperature_minimale = 0.1
facteur_refroidissement = 0.95
nombre_iterations = 1000

cout_achat = 15 # centimes
cout_revente = 10 # centimes
taxe_revente = 0.13 # pourcentage

def calculer_objectif(solution) -> float:
    # Calcul de l'objectif : minimiser le surplus de production solaire
    # rejets = 0 if consommation_net >=0 else -consommation_net
    # consommation_solaire = min(production_solaire, production_solaire - rejets)
    # consommation_totale = consommation_net + consommation_solaire

    puissance_totale_eqt = consommation_equipements(solution)
    diff_puissance_totale_eqt = puissance_totale_eqt - puissance_totale_eqt_initiale

    new_consommation_net = consommation_net + diff_puissance_totale_eqt
    new_rejets = 0 if new_consommation_net >=0 else -new_consommation_net
    new_import = 0 if new_consommation_net < 0 else new_consommation_net
    new_consommation_solaire = min(production_solaire, production_solaire - new_rejets)
    new_consommation_totale = (new_consommation_net + new_rejets) + new_consommation_solaire
    print("Objectif : cette solution ajoute ", diff_puissance_totale_eqt, " W a la consommation initial. Nouvelle consommation nette ", new_consommation_net, " W. Nouveaux rejets ", new_rejets, " W. Nouvelle conso totale ", new_consommation_totale, " W")

    cout_revente_impose = cout_revente * (1.0 - taxe_revente)
    coef_import = (cout_achat) / (cout_achat + cout_revente_impose)
    coef_rejets = (cout_revente_impose) / (cout_achat + cout_revente_impose)

    return coef_import * new_import + coef_rejets * new_rejets

def generer_solution_initiale(solution):
    global puissance_totale_eqt_initiale
    # Générer une solution initiale vide
    #solution = []
    #for _, eqt in enumerate(equipements):
    #    eqt["state"] = random.choice([True, False])
    #    solution += [eqt]
    puissance_totale_eqt_initiale = consommation_equipements(solution)
    return copy.deepcopy(solution)

def consommation_equipements(solution):
    return sum(equipement["puissance"] for equipement in solution if equipement["state"])

def permuter_equipement(solution):
    global consommation_totale

    # Permuter le state d'un equipement eau hasard
    voisin = copy.deepcopy(solution)
    
    eqt = random.choice(voisin)
    eqt["state"] = not eqt["state"]
    print("      -- On permute ", eqt["nom"], " puissance de ", eqt["puissance"], ". Il passe à ", eqt["state"])
    return voisin

def recuit_simule():
    # Générer une solution initiale
    solution_actuelle = generer_solution_initiale(equipements)
    meilleure_solution = solution_actuelle
    temperature = temperature_initiale

    for _ in range(nombre_iterations):
        # Générer un voisin
        objectif_actuel = calculer_objectif(solution_actuelle)
        print("Objectif actuel :", objectif_actuel)

        voisin = permuter_equipement(solution_actuelle)

        # Calculer les objectifs pour la solution actuelle et le voisin
        objectif_voisin = calculer_objectif(voisin)
        print("Objecttif voisin :", objectif_voisin)

        # Accepter le voisin si son objectif est meilleur ou si la consommation totale n'excède pas la production solaire
        if objectif_voisin < objectif_actuel:
            print("---> On garde l'objectif voisin")
            solution_actuelle = voisin
            if objectif_voisin < calculer_objectif(meilleure_solution):
                print("---> C'est la meilleure jusque là")
                meilleure_solution = voisin
        else:
            # Accepter le voisin avec une certaine probabilité
            probabilite = math.exp((objectif_actuel - objectif_voisin) / temperature)
            if (seuil := random.random()) < probabilite:
                solution_actuelle = voisin
                print("---> On garde l'objectif voisin car seuil (",seuil, ") inférieur à proba (", probabilite, ")")
            else:
                print("--> On ne prend pas")

        # Réduire la température
        temperature *= facteur_refroidissement
        print(" !! Temperature ", temperature)
        if temperature < temperature_minimale:
            break

    return meilleure_solution

def calculer_consommation(solution):
    # Calculer la consommation totale de la solution
    return sum(equipement["puissance"] for equipement in solution)

# Résolution du problème avec l'algorithme de recuit simulé
solution_optimale = recuit_simule()

# Affichage de la solution optimale
print("Solution optimale :")
for equipement in solution_optimale:
    if equipement["state"]:
        print("- ", equipement["nom"], "(", equipement["puissance"], "W) etat:", equipement["state"])

# Calcul de la puissance totale consommée et de la durée totale
puissance_totale = sum(equipement["puissance"] for equipement in solution_optimale if equipement["state"]) 
duree_totale = sum(equipement["duree"] for equipement in solution_optimale if equipement["state"])

print("Puissance totale consommée :", puissance_totale)
print("Durée totale :", duree_totale)
print("Valeur de l'objectif: ", calculer_objectif(solution_optimale))
