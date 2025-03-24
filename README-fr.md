[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacs_badge]][hacs]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

![Icon](https://github.com/jmcollin78/solar_optimizer/blob/main/images/icon.png?raw=true)

> ![Tip](https://github.com/jmcollin78/solar_optimizer/blob/main/images/tips.png?raw=true) Cette intégration permet d'optimiser l'utilisation de votre énergie solaire. Elle commande l'allumage et l'extinction de vos équipements dont l'activation est différable dans le temps en fonction de la production et de la consommation électrique courante.

- [Qu'est-ce que Solar Optimizer ?](#quest-ce-que-solar-optimizer-)
- [Comment fonctionne-t-elle ?](#comment-fonctionne-t-elle-)
  - [Anti-bagot](#anti-bagot)
  - [Utilisabilité](#utilisabilité)
- [Installation](#installation)
  - [Procédure de migration d'une version 2.x vers la 3.x](#procédure-de-migration-dune-version-2x-vers-la-3x)
  - [HACS installation (recommendé)](#hacs-installation-recommendé)
  - [Installation manuelle](#installation-manuelle)
- [La configuration](#la-configuration)
  - [Configurer l'intégration pour la première fois](#configurer-lintégration-pour-la-première-fois)
  - [Configurer les équipements](#configurer-les-équipements)
    - [Configurer un équipement simple (on/off)](#configurer-un-équipement-simple-onoff)
  - [Configurer un équipement avec une puissance variable](#configurer-un-équipement-avec-une-puissance-variable)
  - [Exemples de configurations](#exemples-de-configurations)
    - [Commande d'une recharge de Tesla](#commande-dune-recharge-de-tesla)
    - [Commande d'une climatisation](#commande-dune-climatisation)
    - [Commande du preset d'une climatisation](#commande-du-preset-dune-climatisation)
    - [Commande d'un deshumidificateur](#commande-dun-deshumidificateur)
  - [Configurer l'algorithme en mode avancé](#configurer-lalgorithme-en-mode-avancé)
- [Entités disponibles](#entités-disponibles)
  - [L'appareil "configuration"](#lappareil-configuration)
  - [Les appareils](#les-appareils)
- [Les évènements](#les-évènements)
- [Créer des modèles de capteur pour votre installation](#créer-des-modèles-de-capteur-pour-votre-installation)
- [Une carte pour vos dashboards en complément](#une-carte-pour-vos-dashboards-en-complément)
  - [Installez les plugins](#installez-les-plugins)
  - [Installez les templates](#installez-les-templates)
  - [Ajoutez une carte par équipements](#ajoutez-une-carte-par-équipements)
  - [Utilisation de la carte](#utilisation-de-la-carte)
    - [Couleur de l'icône](#couleur-de-licône)
    - [Badge](#badge)
    - [Action sur la carte](#action-sur-la-carte)
- [Les contributions sont les bienvenues !](#les-contributions-sont-les-bienvenues)

> ![Nouveau](https://github.com/jmcollin78/solar_optimizer/blob/main/images/new-icon.png?raw=true) _*Nouveautés*_
> * **release 3.2.0** :
>   - ajout d'un capteur optionnelle de la puissance nette instantanée chargée ou déchargée dans la batterie. Elle vient s'ajouter à la puissance nette consommée. En effet si la puissance de charge de la batterie est de la puissance disponible pour les équipements. Le capteur doit remonter une valeur en watt, positive si la batterie se décharge et négative si la batterie charge.
> * **release 3.0.0** :
>   - ajout d'une IHM de configuration des équipmements.
>   - ⚠️ l'installation de la release 3.0.0 nécessite une procédure particulière. Voir la procédure ci-dessous [ici](#procédure-de-migration-dune-version-2x-vers-la-3x).
> * **release 2.1.0** :
>    - ajout d'une durée minimale d'allumage en heure creuses. Permet de gérer les équipements qui doivent avoir un minimum d'allumage par jour comme les chauffes-eau ou les chargeurs (voitures, batteries, ……). Si l'ensoleillement n'a pas durée d'atteindre la durée requise, alors l'équipement s'allumera pendant les heures creuses. Vous pouvez en plus définir à quelle heure les compteurs d'allumage sont remis à zéro ce qui permet de profiter des toutes les heures creuses
> * **release 2.0.0** :
>    - ajout d'un appareil (device) par équipement piloté pour regrouper les entités,
>    - ajout d'un compteur de temps d'allumage pour chaque appareil. Lorsque le switch commandé passe à 'Off', le compteur de temps est incrémenté du temps passé à 'On', en secondes. Ce compteur est remis à zéro tous les jours à minuit.
>    - ajout d'un maximum de temps à 'On' dans la configuration (en minutes). Lorsque cette durée est dépassée, l'équipement n'est plus utilisable par l'algorithme (is_usable = off) jusqu'au prochain reset. Cela offre la possibilité, de ne pas dépasser un temps d'allumage maximal par jour, même lorsque la puissance solaire est disponible.
>    - pour profiter de cette nouvelle info, n'oubliez pas de mettre à jour le decluterring template (en fin de ce fichier)
>    - cette release ouvre la porte a des évolutions plus conséquentes basé sur le temps d'allumage (avoir un minimum journalier par exemple) et prépare le terrain pour l'arrivée de la configuration via l'interface graphique.

# Qu'est-ce que Solar Optimizer ?
Cette intégration va vous permettre de maximiser l'utilisation de votre production solaire. Vous lui déléguez le contrôle de vos équipements dontl'activation peut être différée dans le temps (chauffe-eau, pompe de piscine, charge de véhicle électrique, lave-vaisselle, lave-linge, etc) et elle s'occupe de les lancer lorsque la puissance produite est suffisante.

Elle tente en permanence de minimiser l'import et l'export d'énergie en démarrant, stoppant, modifiant la puissance allouée à un équipement.

2 types d'équipements sont gérés :
1. les équipements commandés par un switch (un service d'une manière générale) qui ont une puissance consommée fixe et pré-déterminée,
2. les équipements dont la puissance de consommation est réglable (Tesla, Robotdyn). En réglant la puissance allouée à ces équipements, Solar Optimizer aligne la consommation sur la production au plus près.

L'idéal est d'avoir au moins un équipement dont la puissance est ajustable dans la liste des équipements gérés par Solar Optimizer.

# Comment fonctionne-t-elle ?
Le fonctionnement est le suivant :
1. à interval régulier (paramétrable), l'algorithme simule des modifications des états des équipements (allumé / éteint / puissance allouée) et calcule un coût de cette configuration. Globalement le coût est le `a * puissance_importée + b * puissance_exportée`. La coefficients a et b sont calculés en fonction du cout de l'électricité au moment du calcul,
2. l'algorithme garde la meilleure configuration (celle qui a un cout minimum) et cherche d'autres solutions, jusqu'à ce qu'un minimum soit atteint.
3. la meilleure configuration est alors appliquée.

L'algorithme utilisé est un algorithme de type recuit simulé dont vous trouverez une description ici : https://fr.wikipedia.org/wiki/Recuit_simul%C3%A9

## Anti-bagot
Pour éviter les effets de bagottements d'un cycle à l'autre, un délai minimal d'activation est paramétrable par équipements : `duration_min`. Par exemple : un chauffe-eau doit être activé au moins une heure pour que l'allumage soit utile, la charge d'une voiture électrique doit durer au moins deux heures, ...
De façon similaire, une durée minimale de désactivation peut être spécifiée dans le paramètre `duration_stop_min`.

## Utilisabilité
A chaque équipement configuré est associé une entité de type switch nommé `enable` qui permet d'autoriser l'algorithme à utiliser l'équipement. Si je veux forcer la chauffe du ballon d'eau chauffe, je mets son switch sur off. L'algorithme ne le regardera donc pas, le chauffe-eau repasse en manuel, non géré par Solar Optimizer.

Par ailleurs, il est possible de définir une règle d'utilisabilité des équipements. Par exemple, si la voiture est chargée à plus de 90%, l'algorithme considère que l'équipement qui pilote la charge de la voiture doit être éteint. Cette régle est définit sous la forme d'un template configurable qui vaut True si l'équipement est utilisable.

Si une batterie est spécifiée lors du paramétrage de l'intégration et si le seuil `battery_soc_threshold` est spécifié, l'équipement ne sera utilisable que si le soc (pourcentage de charge de la batterie) est supérieur ou égal au seuil.

Un temps d'utilisation maximal journalier est paramétrable en facultatif. Si il est valorisé et si la durée d'utilisation de l'équipement est dépasée, alors l'équipement ne sera pas utilisable par l'algorithme et laisse donc de la puissance pour les autres équipements.

Un temps d'utilisation minimal journalier est aussi paramétrable en facultatif. Ce paramètre permet d'assurer que l'équipement sera allumé pendant une certaine durée minimale. Vous spécifiez à quelle heure commence les heures creuses, (`offpeak_time`) et la durée minimale en minutes (`min_on_time_per_day_min`). Si à l'heure indiquée par `offpeak_time`, la durée minimale d'activation n'a pas été atteinte, alors l'équipement est activé jusqu'au changement de jour (paramètrable dans l'intégration et 05:00 par défaut) ou jusqu'à ce que le maximum d'utilisation soit atteint (`max_on_time_per_day_min`) ou pendant toute la durée des heures creuses si `max_on_time_per_day_min` n'est pas précisé. Vous assurez ainsi que le chauffe-eau ou la voiture sera chargée le lendemain matin même si la production solaire n'a pas permise de recharger l'appareil. A vous d'inventer les usages de cette fonction.

Ces 5 règles permettent à l'algorithme de ne commander que ce qui est réellement utile à un instant t. Ces règles sont ré-évaluées à chaque cycle.

# Installation

## Procédure de migration d'une version 2.x vers la 3.x
La version 3.0.0 amène une IHM de configuration qui permet d'ajouter facilement des nouveaux équipements à contrôler et de changer facilement leur configuration.

Cette procédure, ne doit être déroulée que si vous avez déjà installée et configurée une version 2.x.

L'installation de la v 3.0.0 impose de recréer tous les équipements via l'IHM et de supprimer la configuration du fichier `configuration.yaml`. La procédure à suivre est la suivante, elle doit être suivie scrupuleusement :
1. allez dans Paramètres / Intégration, sélectionnez "Solar Optimizer" et supprimez l'appareil "Solar Optimizer". L'intégration "Solar Optimizer" ne doit plus être visible,
2. supprimez la configuration qui est dans votre fichier `configuration.yaml`,
3. lancez HACS, recherchez "Solar Optimizer" et faite l'installation de la version 3.0.0,
4. Allez dans Paramètres / Intégration et cliquez sur "Ajouter une intégration" et sélectionnez "Solar optimizer",
5. Vous arrivez sur la page de configuration des paramètres communs décrites [ici](#configurer-lintégration-pour-la-première-fois)


## HACS installation (recommendé)

1. Installez [HACS](https://hacs.xyz/). De cette façon, vous obtenez automatiquement les mises à jour.
2. Ajoutez ce repository Github en tant que repository personnalisé dans les paramètres HACS.
3. recherchez et installez "Solar Optimizer" dans HACS et cliquez sur "installer".
4. Redémarrez Home Assistant.
5. Ensuite, vous pouvez ajouter l'intégration de Solar Optimizer dans la page d'intégration. Vous ne pouvez installer qu'une seule intégration Solar Optimizer.

## Installation manuelle
Une installation manuelle est possible. Elle n'est pas recommandée et donc elle ne sera pas décrite ici.

# La configuration
## Configurer l'intégration pour la première fois
Lors de l'ajout de l'intégration Solar Optimizer, la page de paramétrage des paramètres communs s'ouvre :

![common configuration page](images/config-common-parameters.png)

Vous devez spécifier :
1. **une période de rafraichissement** en secondes. Plus la période est courte et plus le suivi sera précis mais plus la charge du votre serveur sera importante ; les calculs sont en effet gourmands en charge CPU. 5 minutes (donc 300 sec) est une bonne valeur moyenne,
2. le sensor qui donne **la consommation nette instantanée** du logement (elle doit être négative si la production dépasse la consommation). Ce chiffre est indiqué en Watt,
3. le sensor qui donne **la production photovoltaïque instantanée** en Watt aussi (elle est forcément positive ou nulle),
4. un sensor ou input_number qui donne **le cout du kwh importé** (requis: nombre strictement positif),
5. un sensor ou input_number qui donne **le prix du kwh exporté** (requis: nombre strictement positif). On peut utiliser la même valeur/sensor que l'importée si pas de contrat de revente. Ne pas mettre 0 sinon ça fausse trop l'algorithme,
6. un sensor ou input_number qui donne **la valeur de la taxe applicable sur les kwh exportée** en pourcentage (chiffre positif ou 0 si vous ne revendez pas ou ne connaissez pas cette valeur). Cette valeur dépend de votre contrat. Elle n'est pas déterminante dans l'algorithme donc une valeur de 0 est tout à fait adaptée,
7. un sensor facultatif qui donne **l'état de charge d'une éventuelle batterie solaire** en pourcentage. Si vous n'avez pas de batterie dans votre installation solaire, laissez ce champ vide,
8. un sensor qui donne la **puissance nette instantanée de charge de la batterie**. Elle doit être exprimée en watt et doit être négative si la batterie charge et positive si la batterie se décharge. Cette valeur sera ajoutée à la puissance net consommée. Si la puissance consommée nette est de -1000 w (vente de 1000 w) mais que la batterie charge de -500 w, cela veut dire que le surplus utilisable par l'algorithme est de 1500 w.
9. **l'heure de début de journée**. A cette heure les compteurs d'uitlisation des équipements sont remis à zéro. La valeur par défaut est 05:00. Pour bien faire, elle doit être avant la première production et le plus tard possible pour les activations en heures creuses.


A part l'état de charge de la batterie solaire, ces informations sont nécessaires à l'algorithme pour fonctionner, elles sont donc toutes obligatoires. Le fait que ce soit des sensor ou input_number permet d'avoir des valeurs qui sont réévaluées à chaque cycle. En conséquence le passage en heure creuse peut modifier le calcul et donc les états des équipements puisque l'import devient moins cher. Donc tout est dynamique et recalculé à chaque cycle.

## Configurer les équipements
Chaque équipements pilotable doit ensuite être configuré en ajoutant une nouvelle intégration via la bouton "Ajouter un équipement" disponible dans la page de l'intégration :

![common configuration page](images/config-add-device.png)

Le menu suivant s'affiche alors vous permettant de choisir un équipement simple qui va fonctionner en on/off ou un équipement dont la puissance est variable (pour suivre la puissance disponible) :

![device type](images/config-device-type.png)

### Configurer un équipement simple (on/off)
Un équipement simple est un commande uniquement par un allumage / extinction (un switch). Si l'algorithme décide de l'allumer, l'équipement est allumé et sinon il est éteint. Il se configure de la façon suivante :

![simple device configuration](images/config-simple-device.png)

Vous devez spécifier les attributs suivant :

| attribut                  | valable pour                            | signification                                                                                                                                                                                                                                | exemple                                               | commentaire                                                                                                                                                                                                                                    |
| ------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                    | tous                                    | Le nom de l'équipement.                                                                                                                                                                                                                      | VMC sous-sol                                          | Le nom est utilisé pour nommé les entités de cet équipement.                                                                                                                                                                                   |
| `entity_id`               | tous                                    | l'entity id de l'équipement à commander                                                                                                                                                                                                      | switch.vmc_sous_sol                                   | Peut être un `switch`, un `input_boolean`, un `humidifier`, un `climate`, un `fan`, un `select` ou un `light`. Si l'entité n'est pas un `switch`, les champs `activation_service` et `deactivation_service` doivent être adaptés               |
| `power_max`               | tous                                    | la puissance maximale consommée par l'équipement lorsqu'il est allumé en watts                                                                                                                                                               | 250                                                   | -                                                                                                                                                                                                                                              |
| `check_usable_template`   | tous                                    | Un template qui vaut True si l'équipement pourra être utilisé par Solar Optimizer. Un template commence par {{ et doit se terminer par }}.                                                                                                   | {{ is_state('cover.porte_garage_garage', 'closed') }} | Dans l'exemple, Sonar Optimizer n'essayera pas de commander la "VMC sous-sol" si la porte du garage est ouverte. Laissez {{ True }} si vous ne vous servez pas de ce champ                                                                     |
| `active_template`         | tous                                    | Un template qui vaut True si l'équipement si l'équipement est actif. Un template commence par {{ et doit se terminer par }}.                                                                                                                 | {{ is_state('climate.clim_salon', 'cool') }}          | Dans l'exemple, l'équipement de type `climate` sera vu par Solar Optimizer comme actif si son état est `cool`. Laissez vide pour les équipements pour lesquels l'état par défaut 'on' / 'off' est valable (les switchs et input_boolean)       |
| `duration_min`            | tous                                    | La durée en minute minimale d'activation                                                                                                                                                                                                     | 60                                                    | La VMC sous-sol s'allumera toujours pour une heure au minimum                                                                                                                                                                                  |
| `duration_stop_min`       | tous                                    | La durée en minute minimale de desactivation. Vaut `duration_min` si elle n'est pas précisée                                                                                                                                                 | 15                                                    | La VMC sous-sol s'éteindra toujours pour 15 min au minimum                                                                                                                                                                                     |
| `action_mode`             | tous                                    | le mode d'action pour allumer ou éteindre l'équipement. Peut être "action_call" ou "event" (*)                                                                                                                                               | action_call                                           | "action_call" indique que l'équipement s'allume et s'éteint via une action. Cf. ci-dessous. "event" indique qu'un évènement est envoyé lorsque l'état doit changer. Cf. (*)                                                                    |
| `activation_service`      | uniquement si action_mode="action_call" | le service a appeler pour activer l'équipement sous la forme "domain/service[/parameter:value]"                                                                                                                                              | switch/turn_on                                        | l'activation déclenchera le service "switch/turn_on" sur l'entité "entity_id". La syntaxe acceptée est la suivante : domain/action[/parameter:value]                                                                                           |
| `deactivation_service`    | uniquement si action_mode="action_call" | le service a appeler pour désactiver l'équipement sous la forme "domain/service[/parameter:value]"                                                                                                                                           | switch/turn_off                                       | la désactivation déclenchera le service "switch/turn_off" sur l'entité "entity_id". La syntaxe acceptée est la suivante : domain/action[/parameter:value]                                                                                      |
| `battery_soc_threshold`   | tous                                    | le pourcentage minimal de charge de la batterie pour que l'équipement soit utilisable                                                                                                                                                        | 30                                                    | Dans cet exemple, l'équipement ne sera utilisable par l'algorithme si la batterie solaire n'est pas chargée à au moins 30%. Nécessite le renseignement de l'entité d'état de charge de la batterie dans les paramètres communs. Cf. ci-dessus. |
| `max_on_time_per_day_min` | tous                                    | le nombre de minutes maximal en position allumé pour cet équipement. Au delà, l'équipement n'est plus utilisable par l'algorithme                                                                                                            | 10                                                    | L'équipement sera allumé au maximum 10 minutes par jour                                                                                                                                                                                        |
| `min_on_time_per_day_min` | tous                                    | le nombre de minutes minimale en position allumé pour cet équipement. Si lors du démarrage des heures creuses, ce minimum n'est pas atteint alors l'équipement sera allumé à concurrence du début de journée ou du `max_on_time_per_day_min` | 5                                                     | L'équipement est sera allumé au minimum 5 minutes par jour ; soit pendant la production solaire, soit pendant les heures creuses                                                                                                               |
| `offpeak_time`            | tous                                    | L'heure de début des heures creuses au format hh:mm                                                                                                                                                                                          | 22:00                                                 | L'équipement pourra être allumé à 22h00 si la production de la journée n'a pas été suffisante                                                                                                                                                  |

## Configurer un équipement avec une puissance variable
Ce type d'équipement permet moduler la puissance consommée par l'équipement en fonction de la production solaire et de ce que décide l'algorithme. Vous avez ainsi une sorte de routeur solaire logiciel qui permet, par exemple, de moduler la charge d'une voiture électrique avec uniquement le surplus de production.

Tous les paramètres décrits [ici](#configurer-un-équipement-simple-onoff) s'applique et douvent être complétés par ceux-ci :

| attribut                      | valable pour                    | signification                                                 | exemple                      | commentaire                                                                                                                                                                                                                                                                                              |
| ----------------------------- | ------------------------------- | ------------------------------------------------------------- | ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `power_entity_id`             | équipement à puissance variable | l'entity_id de l'entité gérant la puissance                   | `number.tesla_charging_amps` | Le changement de puissance se fera par un appel du service `change_power_service` sur cette entité. Elle peut être un `number` ou un `input_number`                                                                                                                                                      |
| `power_min`                   | équipement a puissance variable | La puissance minimale en watt de l'équipement                 | 100                          | Lorsque la consigne de puissance passe en dessous de cette valeur, l'équipement sera éteint par l'appel du `deactivation_service`. Ce paramètre fonctionne avec `power_max` pour définir l'interval possible de variation de la puissance                                                                |
| `power_step`                  | équipement a puissance variable | Le pas de puissance en watt                                   | 10                           | Pour une voiture mettre 230 (230 v x 1 A)                                                                                                                                                                                                                                                                |
| `change_power_service`        | équipement a puissance variable | Le service à appeler pour changer la puissance                | `"number/set_value"`         | -                                                                                                                                                                                                                                                                                                        |
| `convert_power_divide_factor` | équipement a puissance variable | Le diviseur a appliquer pour convertir la puissance en valeur | 50                           | Dans l'exemple, le service "number/set_value" sera appelé avec la `consigne de puissance / 50` sur l'entité `entity_id`. Pour une Tesla sur une installation tri-phasée, la valeur est 660 (230 v x 3) ce qui permet de convertir une puissance en ampère. Pour une installation mono-phasé, mettre 230. |

## Exemples de configurations
Les exemples ci-dessus sont à adapter à votre cas.

### Commande d'une recharge de Tesla
Pour commander la recharge d'une voiture de type Tesla avec modulation de l'intensité de charge, si la batterie solaire est chargée à 50%, en tri-phasé avec recharge en heures creuses à partir de 23h00, voici les paramètres :

```yaml
  name: "Recharge Tesla"
  entity_id: "switch.tesla_charger"
  # 3 x 230 v
  power_min: 690
  # 18 x 230 v
  power_max: 4140
  power_step: 690
  check_usable_template: "{{ is_state('input_select.charge_mode', 'Solaire') and is_state('binary_sensor.tesla_wall_connector_vehicle_connected', 'on') and is_state('binary_sensor.tesla_charger', 'on') and states('sensor.tesla_battery') | float(100) < states('number.tesla_charge_limit') | float(90) }}"
  # 2 heures
  duration_min: 120
  # 15 min stop
  duration_stop_min: 15
  # Power management
  power_entity_id: "number.tesla_charging_amps"
  # 5 min
  duration_power_min: 5
  action_mode: "service_call"
  activation_service: "switch/turn_on"
  deactivation_service: "switch/turn_off"
  change_power_service: "number/set_value"
  convert_power_divide_factor: 690
  battery_soc_threshold: 50
  min_on_time_per_day_min: 300
  offpeak_time: "23:00"
```

En monophasé, remplacez les 690 par des 230. Vous devez adapter, la puissance maximale et le `check_usable_template` au minimum.

### Commande d'une climatisation
Pour allumer une climatisation si la température est supérieure à 27° :
```yaml
    name: "Climatisation salon"
    entity_id: "climate.clim_salon"
    power_max: 1500
    check_usable_template: "{{ states('sensor.temperature_salon') | float(0) > 27 }}"
    active_template: "{{ states('climate.vtherm', 'cool') }}"
    # 1 h minimum
    duration_min: 60
    action_mode: "service_call"
    activation_service: "climate/set_hvac_mode/hvac_mode:cool"
    deactivation_service: "climate/set_hvac_mode/hvac_mode:off"
```

### Commande du preset d'une climatisation
Pour changer le preset d'une climatisation si la température est supérieure à 27° :

```yaml
    name: "Climatisation salon"
    entity_id: "climate.clim_salon"
    power_max: 1500
    check_usable_template: "{{ states('sensor.temperature_salon') | float(0) > 27 }}"
    active_template: "{{ is_state_attr('climate.clim_salon', 'preset_mode', 'boost') }}"
    # 1 h minimum
    duration_min: 60
    action_mode: "service_call"
    activation_service: "climate/set_preset_mode/preset_mode:boost"
    deactivation_service: "climate/set_preset_mode/preset_mode:eco"
```

### Commande d'un deshumidificateur
Pour allumer un déhumidificateur si l'humidité dépasse un seuil pour au moins une heure par jour avec possibilité d'allumage en heures creuses :

```yaml
  name: "Dehumidification musique"
  entity_id: "humidifier.humidifier_musique"
  power_max: 250
  # 1 h
  duration_min: 60
  duration_stop_min: 30
  check_usable_template: "{{ states('sensor.humidite_musique') | float(50) > 55 }}"
  action_mode: "service_call"
  activation_service: "humidifier/turn_on"
  deactivation_service: "humidifier/turn_off"
  max_on_time_per_day_min: 180
  min_on_time_per_day_min: 60
  offpeak_time: "02:00"
```

## Configurer l'algorithme en mode avancé
La configuration avancée permet de modifier la configuration de l'algorithme. Il n'est pas conseillé d'y toucher mais cette fonction reste disponible pour des besoins spécifiques. L'algorithme est un algorithme de type recuit simulé qui cherche des configurations (combinaisons de on/off) et procède à une évaluation d'une fonction de coût à chaque itération.
A chaque itération, l'algorithme échange de façon aléatoire l'état de certains équipements et évalue la fonction de cout. Si l'évaluation est meilleure que la prédédente elle est gardée. Si elle est plus forte, elle peut être gardée en fonction d'une "température". Cette température va baisser au fur et à mesure des itérations ce qui va permettre de converger vers une solution quasi optimale.

Pour utiliser la configuration avancée, vous devez :

- ajouter la ligne suivante dans votre `configuration.yaml`:

  ```solar_optimizer: !include solar_optimizer.yaml```

- et créez un fichier au même niveau que le `configuration.yaml` avec les informations suivantes :

```yaml
algorithm:
  initial_temp: 1000
  min_temp: 0.1
  cooling_factor: 0.95
  max_iteration_number: 1000
```

Les paramètres influent de la manière suivante :
- initial_temp : la température initiale. Des valeurs de la fonction de coût jusqu'à 1000 sont acceptées dans les premières itération. Si vous avez des grosses puissances, ce paramètres peut être augmenter. Si vous n'avez que des petites puissances, il peut être baissé,
- min_temp : la temperature minimale. En fin de recherche de solution optimale, seulement des variations de 0.1 seront acceptées. Ce paramètre ne devrait pas être modifié,
- cooling_factor : à chaque itération la temperature est multipliée par 0,95 ce qui assure une descente lente et progressive. Mettre une valeur plus petite, va forcer l'algorithme a converger plus vite au détriment de la qualité de la solution. Une solution moins bonne sera trouvée plus vite. A l'inverse, mettre une valeur plus forte (et strictement inférieure à 1) va engendrer des temps de calcul plus long, mais la solution sera meilleure.
- max_iteration_number : le nombre maximal d'itérations acceptables. Mettre en nombre plus faible peut dégrader la qualité de la solution mais va raccourcir le temps de calcul si aucune solution stable n'est trouvée.

Les valeurs par défaut conviennent à des configurations avec une vingtaine d'équipements (donc avec beaucoup de possibilités). Si vous n'avez que quelques équipements, disons moins de 5, et pas d'équipements avec une puissance variable, vous pourriez utiliser ce jeu de paramètres (non testés) :

```yaml
algorithm:
  initial_temp: 1000
  min_temp: 0.1
  cooling_factor: 0.90
  max_iteration_number: 300
```

Vous ne devriez pas constater de différence dans la qualité des solutions trouvées mais l'algorithme ira plus vite et sera beaucoup moins gourmand en ressources CPU.
Tout changement dans la configuration avancée nécessite un arrêt / relance de l'intégration (ou de Home Assistant) pour être pris en compte.

# Entités disponibles
## L'appareil "configuration"
L'intégration, une fois correctement configurée, créée un appareil (device) nommé 'configuration' qui contient plusieurs entités :
1. un sensor nommé "total_power" qui est le total de toutes les puissances des équipements commandés par Solar Optimizer,
2. un sensor nommé "best_objective" qui est la valeur de la fonction de coût (cf. fonctionnement de l'algo). Plus la valeur est faible et plus la solution trouvée est bonne,
3. un sensor nommé "power_production" qui est la dernière valeur de la production solaire lissée (si l'option a été choisie) prise en compte,
3. un sensor nommé "power_production_brut" qui est la dernière valeur de la production solaire brute prise en compte.

![Configuration entités](images/entities-configuration.png)

La reconfiguration de cet appareil permet de configurer Solar Optimizer.

## Les appareils

1. un switch nommé `switch.enable_solar_optimizer_<name>`. Si le switch est "Off", l'algorithme ne considérera pas cet équipement pour le calcul. Ca permet de manuellement sortir un équipement de la liste sans avoir à modifier la liste. Ce switch contient des attributs additionnels qui permettent de suivre l'état interne de l'équipement vu de l'algorithme,
2. un sensor nommé `sensor.on_time_today_solar_optimizer_<name>` qui donne la durée d'activation depuis la remise à zéro (cf. raz_time)
3. un switch nommé `switch.solar_optimizer_<name>` qui reflète l'état d'activation demandé par Solar Optimizer

![Simple appareil entités](images/entities-simple-device.png)

Ce dernier switch possède des attributs consultables via Outils de developpement / Etats :

![Configuration entités](images/entities-attributes.png)

1. `is_enabled` : true si l'appareil est autorisé par l'utilisateur dans le calcul,
2. `is_active` : true si l'appareil est actif,
3. `is_usable` : true si l'appareil peut être utilisé par l'algorithme,
4. `can_change_power` : true si la puissance peut être adaptée,
5. `current_power` : la puissance courante de l'appareil,
6. `requested_power` : la puissance demandée par Solar Optimizer,
7. `duration_sec` : la durée d'allumage en secondes,
8. `duration_power_sec` : la durée d'un changement de puissance en secondes,
9. `next_date_available` : à quelle date et heure l'équipement sera de nouveau disponible pour l'algorithme,
10. `next_date_available_power` : à quelle date et heure le changement de puissance de l'équipement sera de nouveau disponible pour un changement,
11. `battery_soc_threshold` : l'état de charge minimal de la batterie solaire pour que l'équipement soit utilisable par l'algorithme,
12. `battery_soc` : l'état de charge courant de la batterie solaire.

# Les évènements
Solar Optimizer produit des évènements à chaque allumage ou extinction d'un appareil. Cela vous permet de capter ces évènements dans une automatisation par exemple.

`solar_optimizer_state_change_event` : lorsqu'un équipement change d'état. Le contenu du message est alors le suivant :
```
event_type: solar_optimizer_state_change_event
data:
  action_type: [Activate | Deactivate],
  requested_power: <la nouvelle puissance demandée si disponible>,
  current_power: <la puissance demandée si disponible>,
  entity_id: <l'entity_id de l'appareil commandé>,
```

`solar_optimizer_change_power_event` : lorsqu'un équipement change de puissance. Le contenu du message est alors le suivant :
```
event_type: solar_optimizer_state_change_event
data:
  action_type: [ChangePower],
  requested_power: <la nouvelle puissance demandée si disponible>,
  current_power: <la puissance demandée si disponible>,
  entity_id: <l'entity_id de l'appareil commandé>,
```

`solar_optimizer_enable_state_change_event` : lorsque le switch `enable` d'un équipement change d'état. Le contenu du message est alors le suivant :
```
event_type: solar_optimizer_enable_state_change_event
data:
  device_unique_id: prise_vmc_garage
  is_enabled: false
  is_active: true
  is_usable: false
  is_waiting: true
```

Vous pouvez contrôler la réception et le contenu des évènements dans Outils de développement / Evènements. Donnez le nom de l'évènement à écouter :

![écoute d'évènements](images/event-listening.png)

Un exemple d'automatisation qui écoute les évènements :

```yaml
alias: Gestion des events de Solar Optimizer
description: Notifie les modifiations de status de Solar Optimizer
mode: parallel
max: 50
triggers:
  - event_type: solar_optimizer_change_power_event
    id: power_event
    trigger: event
  - event_type: solar_optimizer_state_change_event
    id: state_change
    trigger: event
conditions: []
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: power_event
        sequence:
          - data:
              message: >-
                {{ trigger.event.data.action_type }} pour entité {{
                trigger.event.data.entity_id}}     avec requested_power {{
                trigger.event.data.requested_power }}. (current_power is {{
                trigger.event.data.current_power }})
              title: ChangePower Event de Solar Optimizer
            enabled: false
            action: persistent_notification.create
          - if:
              - condition: template
                value_template: >-
                  {{ trigger.event.data.entity_id == switch.cloucloute_charger
                  }}
            then:
              - data:
                  message: On demande a changer la puissance de Cloucloute
                  title: Changement de puissance
                  notification_id: cloucloute-power-change
                action: persistent_notification.create
              - data:
                  value: >-
                    {{ (trigger.event.data.requested_power | float(0) / 660) |
                    round(0) }}
                target:
                  entity_id: number.cloucloute_charging_amps
                action: number.set_value
      - conditions:
          - condition: trigger
            id: state_change
        sequence:
          - data:
              message: >-
                {{ trigger.event.data.action_type }} pour entité {{
                trigger.event.data.entity_id}}     avec requested_power {{
                trigger.event.data.requested_power }}. (current_power is {{
                trigger.event.data.current_power }})
              title: StateChange Event de Solar Optimizer
            action: persistent_notification.create
```

# Créer des modèles de capteur pour votre installation
Votre installation peut nécessiter de créer des capteurs spécifiques qui doivent être configurer [ici](README-fr.md#configurer-lintégration-pour-la-première-fois). Les règles sur ces capteurs sont importantes et doivent être scrupuleusement respectées pour un bon fonctionnement de Solar Optimizer.
Voici mes templates de capteurs (valable pour une installation Enphase uniquement):

Fichier `configuration.yaml` :
```
template: !include templates.yaml
```

Fichier `templates.yaml` :
```
- sensor:
    - name: "Total puissance produite instantanée (W)"
      icon: mdi:solar-power-variant
      unique_id: total_power_produite_w
      device_class: power
      unit_of_measurement: "W"
      state_class: measurement
      state: >
        {% set power = [states('sensor.envoy_122307065303_current_power_production') | float(default=0), 0] | max %}
        {{ power | round(2) }}
      availability: "{{ is_number(states('sensor.envoy_122307065303_current_power_production')) }}"
    - name: "Total puissance consommée net instantanée (W)"
      unique_id: total_power_consommee_net_w
      unit_of_measurement: "W"
      device_class: power
      state_class: measurement
      state: >
        {%- set power_net = states('sensor.envoy_122307065303_current_net_power_consumption') | float(default=0) -%}
        {{ power_net }}
      availability: "{{ is_number(states('sensor.envoy_122307065303_current_net_power_consumption')) }}"
```

A adapter à votre cas bien sûr.

# Une carte pour vos dashboards en complément
En complément, les codes Lovelace suivant permet de controller chaque équipement déclaré.
Les étapes à suivre sont :
1. Avec HACS, installez les plugins nommés `streamline-card`, `expander-card` et `mushroom-template` si vous ne les avez pas déjà,
2. Installez les templates pour `streamline` en tête de votre code Lovelace,
3. Installez une carte par équipement géré par Solar Optimizer qui référence le template `streammline``

## Installez les plugins
Lisez la documentation du plugin [ici](https://github.com/brunosabot/streamline-card) pour vous familiariser avec cet excellent plugin.
Suivez la procédure d'installation qui consiste à installer un nouveau dépôt Github de type `Dashboard` et à installer le plugin.

Vous devez avoir dans la partie "Téléchargé" vos plugins de visibles :

![HACS Plugin](images/install-hacs-streamline.png)

Faites de même avec les plugins `expander-card` et `mushroom-template`.

## Installez les templates
Pour installer les templates vous devez aller sur votre dashboard, vous mettre en édition et cliquer sur les trois points dans le menu en haut à droite :

![dahsboard edit](images/dashboard-edit.png)

puis

![dashboard edit 2](images/dashboard-edit2.png)

puis

![dashboard edit 3](images/dashboard-edit3.png)

Vous arrivez alors en édition manuelle de votre dashboard Lovelace.

Attention : le yaml est susceptible. L'indentation doit être scrupuleusement respectée.

Copier/coller le texte ci-dessous (cliquez sur le bouton copier pour tout prendre sans risque) tout au début 1 ligne, 1 colonne.

```yaml
# A mettre en début de page sur le front
streamline_templates:
  managed_device_power:
    default: null
    card:
      type: custom:expander-card
      expanded: false
      title-card-button-overlay: true
      title-card:
        type: custom:mushroom-template-card
        primary: '{{ state_attr(''[[device]]'', ''device_name'') }}'
        secondary: >-
          [[secondary_infos]] ({{ state_attr('[[on_time_entity]]',
          'on_time_hms') }} / {{ state_attr('[[on_time_entity]]',
          'max_on_time_hms')}} )
        icon: '[[icon]]'
        badge_icon: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}mdi:power-sleep{% elif
          is_state_attr('[[device]]','is_enabled', True) %}mdi:check{% else
          %}mdi:cancel{% endif %}
        badge_color: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}#003366{% elif is_state_attr('[[device]]', 'is_usable', True)
          and is_state_attr('[[device]]', 'is_enabled', True) %}green {% elif
          is_state_attr('[[device]]', 'is_enabled', False) %}red {% elif
          is_state_attr('[[device]]','is_waiting', True) %}orange {% elif
          is_state_attr('[[device]]', 'is_usable', False) or
          state_attr('[[device]]', 'is_usable') is none %}#A0B0FF{% else
          %}blue{% endif %}
        entity: '[[device]]'
        icon_color: >-
          {% if is_state('[[device]]', 'on')%}orange{% else %}lightgray{% endif
          %}
        tap_action:
          action: toggle
        hold_action:
          action: more-info
        double_tap_action:
          action: none
      cards:
        - type: custom:mushroom-chips-card
          chips:
            - type: entity
              entity: '[[enable_entity]]'
              double_tap_action:
                action: more-info
              tap_action:
                action: toggle
              hold_action:
                action: more-info
              icon_color: green
              content_info: name
        - type: markdown
          content: >-
            **Prochaine dispo** : {{ ((as_timestamp(state_attr('[[device]]',
            'next_date_available')) - as_timestamp(now())) / 60) | int }}
            min<br> **Prochaine dispo puissance**: {{
            ((as_timestamp(state_attr('[[device]]',
            'next_date_available_power')) - as_timestamp(now())) / 60) | int }}
            min<br> **Utilisable** : {{ state_attr('[[device]]', 'is_usable')
            }}<br> **Est en attente**  : {{ state_attr('[[device]]',
            'is_waiting') }}<br> **Est forcé en heures creuses**  : {{
            state_attr('[[on_time_entity]]', 'should_be_forced_offpeak') }}<br>
            **Heures creuses**  : {{ state_attr('[[on_time_entity]]',
            'offpeak_time') }}<br> **Puissance requise** : {{
            state_attr('[[device]]', 'requested_power') }} W<br> **Puissance
            courante** : {{ state_attr('[[device]]', 'current_power') }} W
          title: Infos
        - type: history-graph
          hours: 24
          entities:
            - entity: '[[device]]'
            - entity: '[[enable_entity]]'
            - entity: '[[power_entity]]'
  managed_device:
    default: null
    card:
      type: custom:expander-card
      expanded: false
      title-card-button-overlay: true
      title-card:
        type: custom:mushroom-template-card
        primary: '{{ state_attr(''[[device]]'', ''device_name'') }}'
        secondary: >-
          [[secondary_infos]] (max. {{ state_attr('[[device]]', 'power_max') }}
          W -  {{ state_attr('[[on_time_entity]]', 'on_time_hms')}} / {{
          state_attr('[[on_time_entity]]', 'max_on_time_hms')}} )
        icon: '[[icon]]'
        badge_icon: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}mdi:power-sleep{% elif
          is_state_attr('[[device]]','is_enabled', True) %}mdi:check{% else
          %}mdi:cancel{% endif %}
        badge_color: >-
          {% if is_state_attr('[[on_time_entity]]','should_be_forced_offpeak',
          True) %}#003366{% elif is_state_attr('[[device]]', 'is_usable', True)
          and is_state_attr('[[device]]', 'is_enabled', True) %}green {% elif
          is_state_attr('[[device]]', 'is_enabled', False) %}red {% elif
          is_state_attr('[[device]]','is_waiting', True) %}orange {% elif
          is_state_attr('[[device]]', 'is_usable', False) or
          state_attr('[[device]]', 'is_usable') is none %}#A0B0FF{% else
          %}blue{% endif %}
        entity: '[[device]]'
        icon_color: >-
          {% if is_state('[[device]]', 'on')%}orange{% else %}lightgray{% endif
          %}
        tap_action:
          action: toggle
        hold_action:
          action: more-info
        double_tap_action:
          action: none
      cards:
        - type: custom:mushroom-chips-card
          chips:
            - type: entity
              entity: '[[enable_entity]]'
              double_tap_action:
                action: more-info
              tap_action:
                action: toggle
              hold_action:
                action: more-info
              icon_color: green
              content_info: name
        - type: markdown
          content: >-
            **Prochaine dispo** : {{ ((as_timestamp(state_attr('[[device]]',
            'next_date_available')) - as_timestamp(now())) / 60) | int }}
            min<br> **Utilisable** : {{ state_attr('[[device]]', 'is_usable')
            }}<br> **Est en attente**  : {{ state_attr('[[device]]',
            'is_waiting') }}<br> **Est forcé en heures creuses**  : {{
            state_attr('[[on_time_entity]]', 'should_be_forced_offpeak') }}<br>
            **Heures creuses**  : {{ state_attr('[[on_time_entity]]',
            'offpeak_time') }}<br> **Puissance requise** : {{
            state_attr('[[device]]', 'requested_power') }} W<br> **Puissance
            courante** : {{ state_attr('[[device]]', 'current_power') }} W
        - type: history-graph
          hours: 24
          entities:
            - entity: '[[device]]'
            - entity: '[[enable_entity]]'
            - entity: '[[power_entity]]'
```

Vous devez avoir une page qui ressemble à ça :

![dashboard edit 4](images/dashboard-edit4.png)

Cliquez alors sur Enregistrer puis Terminer. Les templates sont maintenant installés, il ne reste plus qu'à les utiliser.

## Ajoutez une carte par équipements

Pour utiliser les templates installés à l'étape précédente, vous devez :
1. Editer un dashboard ou vous voulez ajouter la carte,
2. cliquer sur 'Ajouter une carte' en bas à droite,
3. sélectionner la carte nommée Streamline Card comme ceci :

![dashboard edit 4](images/add-card-1.png)

4. remplir les champs de la façon suivante :

![dashboard edit 4](images/add-card-2.png)

Vous devez choisir le template `managed_device` pour un équipement non muni d'une modulation de puissance ou `managed_device_power` sinon.
Saisissez ensuite les différents attributs.
Un exemple complet pour un équipement 'non power' :

![dashboard edit 4](images/add-card-3.png)

et pour un équipement avec modulation de puissance :

![dashboard edit 4](images/add-card-4.png)

Vous obtiendrez alors un composant permettant d'interagir avec l'équipement qui ressemble à ça :

![Lovelace equipements](https://github.com/jmcollin78/solar_optimizer/blob/main/images/lovelace-eqts.png?raw=true)

## Utilisation de la carte
La carte ainsi obtenue permet de voir l'état d'utilisation de l'équipement et d'interagir avec lui. Ouvrez la carte en appuyant sur le 'V' et vous obtenez ça :

![use card 1](images/use-card-1.png)

### Couleur de l'icône

| Couleur | Signification     | Exemple                              |
| ------- | ----------------- | ------------------------------------ |
| Gris    | Equipement éteint | ![use card 2](images/use-card-2.png) |
| Jaune   | Equipement allumé | ![use card 3](images/use-card-3.png) |

### Badge

| Icone / Couleur  | Signification                                                      | Exemple                                         |
| ---------------- | ------------------------------------------------------------------ | ----------------------------------------------- |
| Coche verte      | Equipement éteint en attente de production                         | ![use card 4](images/use-card-green-check.png)  |
| Coche bleue      | Equipement éteint non disponible (`check-usable` renvoie faux)     | ![use card 4](images/use-card-blue-check.png)   |
| Coche orange     | Equipement éteint en attente du délai enttre 2                     | ![use card 4](images/use-card-orange-check.png) |
| Annulation rouge | Equipement éteint non autorisé par l'utilisation `enable` est faux | ![use card 4](images/use-card-red-cancel.png)   |
| Lune Bleu nuit   | Equipement allumé en heures creuses                                | ![use card 4](images/use-card-blue-moon.png)    |

### Action sur la carte
Cliquez sur la carte de l'équipement et ça forcera son allumage ou son extinction.
Cliquez sur le bouton `Enable` et ça autorisera ou non l'utilisation de l'équipement par l'algorithme de Solar Optimizer.

# Les contributions sont les bienvenues !

Si vous souhaitez contribuer, veuillez lire les [directives de contribution](CONTRIBUTING.md)

***

[solar_optimizer]: https://github.com/jmcollin78/solar_optimizer
[buymecoffee]: https://www.buymeacoffee.com/jmcollin78
[buymecoffeebadge]: https://img.shields.io/badge/Buy%20me%20a%20beer-%245-orange?style=for-the-badge&logo=buy-me-a-beer
[commits-shield]: https://img.shields.io/github/commit-activity/y/jmcollin78/solar_optimizer.svg?style=for-the-badge
[commits]: https://github.com/jmcollin78/solar_optimizer/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacs_badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://forum.hacf.fr/
[license-shield]: https://img.shields.io/github/license/jmcollin78/solar_optimizer.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Joakim%20Sørensen%20%40ludeeus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/jmcollin78/solar_optimizer.svg?style=for-the-badge
[releases]: https://github.com/jmcollin78/solar_optimizer/releases
