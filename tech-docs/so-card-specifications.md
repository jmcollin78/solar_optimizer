Ce fichier décrit les spécifications de la carte Solar Optimizer. Cette carte va permettre d'intégrer nativement dans un dashboard une vision des managed device avec gestion de la puissance ou non.

# Objectif

Cette carte a pour objectifs :
1. d'aider l'utilsateur à voir dans quel état sont les équipements gérés par Solar Optimizer (les managed devices),
2. d'interagir avec SO pour :
   - changer l'état dde l'entité 'enable' du managed device,
   - forcer l'allumage du device,
   - voir les détails de tous les attributs du device (temps de démarrage, durée maximale, ...)


# Specifications UI
La carte doit prendre toute la largeur disponible spécifiée via l'IHM de HA.

## Les informations globales
Un bloc dont le titre est Solar Optimizer contient les informations globales suivantes:
1. La puissance solaire produite lissée (sensor.power_production),
2. La puissance nette consommée,
3. Le SOC de la batterie,
4. Le total de la puissance allumé par l'algo,
5. Le meilleur objectif de l'algo.

Chaque info doit être affichée avec un icone qui la représente le mieux.

## Les informations à afficher pour chaque device

- Prochaine dispo : heure minutes secondes de la prochaines dispo. Si inférieure à l'heure courante, affiche "disponible immédiatement",
- Prochaine dispo puissance: heure minutes secondes de la prochaines dispo du changement de puissance. Si inférieure à l'heure courante, affiche "disponible immédiatement",
- Utilisable : un indicateur visuel disant si le managed device est utilisable par l'algorithme
- Est en attente : un indicateur visuel disant le managed device est en attente d'une prochaine dispo
- Est forcé en heures creuses : un indicateur visuel disant le managed device est forcé en heure creuses
- Heures creuses : l'heure des heures creuses pour cet équipement,
- Puissance requise : la puissance requise
- Puissance courante : la puissance courante
- temps de marche / temps max utilisable : sous la forme hh:mm:ss / hh:mm:ss.
- le seuil de SOC batterie si il est configuré et > 0

Le bloc pour chaque équipement est pliable et dépliable. Lorsqu'il est plié, seuls les infos de nom, état, puissance courante / puissance max, bouton start/stop et bouton enable sont visibles.
Un chevron global permet de tout plier / déplier.

## Les actions
Chaque bloc représentant un équipement sera équipé des boutons d'actions suivants:
1. Un bouton enable : un bouton permettant d'enable l'équipement,
2. Un bouton start/stop : un bouton permettant d'activer/desactiver l'équipement manuellement.




