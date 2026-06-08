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

**Comportement par défaut** : tous les blocs sont fermés au premier chargement de la carte. L'état ouvert/fermé de chaque bloc est persisté dans le `localStorage` du navigateur sous la clé `solar-optimizer-card-collapsed` et restauré automatiquement à la prochaine visite.

## Les statuts d'un équipement

Chaque bloc équipement affiche un badge de statut et une bordure gauche colorée. Ces deux signaux sont **indépendants** :

### Bordure gauche — état physique

| Couleur                    | Signification                                                 |
| -------------------------- | ------------------------------------------------------------- |
| Verte (`--success-color`)  | L'équipement est **physiquement allumé**                      |
| Orange (`--warning-color`) | L'équipement est **en attente** d'une prochaine disponibilité |
| Grise (`--divider-color`)  | L'équipement est **physiquement éteint**                      |

La bordure gauche reflète **toujours** l'état physique réel du switch, indépendamment de l'état de contrôle SO. En cas de gestion SO désactivée (`!isEnabled`), un fond gris clair est superposé via la classe `so-device-card-disabled`, mais la couleur de la bordure reste celle de l'état physique.

### Badge de statut — état de contrôle SO

| Badge         | Couleur           | Condition                              | Signification                                                                   |
| ------------- | ----------------- | -------------------------------------- | ------------------------------------------------------------------------------- |
| **ACTIF**     | Vert              | `isEnabled && isActive`                | Géré par SO et physiquement allumé                                              |
| **MANUEL**    | Ambre (`#f59e0b`) | `!isEnabled && isActive`               | Physiquement allumé mais gestion SO désactivée — l'utilisateur a repris la main |
| **ATTENTE**   | Orange            | `isEnabled && !isActive && isWaiting`  | Géré par SO, en attente d'un prochain créneau                                   |
| **INACTIF**   | Gris              | `isEnabled && !isActive && !isWaiting` | Géré par SO et physiquement éteint                                              |
| **DÉSACTIVÉ** | Gris              | `!isEnabled && !isActive`              | Gestion SO désactivée et équipement éteint                                      |

Le statut `MANUEL` est le signal critique : il indique que l'équipement consomme de l'énergie mais que Solar Optimizer n'en a pas le contrôle.

## Les informations secondaires

Chaque bloc équipement peut afficher une ligne d'information personnalisée, configurée via l'option `secondary_info`. Cette information est rendue **au-dessus** des indicateurs Utilisable / En attente / HC forcées, uniquement lorsque le bloc est déplié.

La valeur est un template évalué côté client supportant :
- `{{ states('entity_id') }}` → état de l'entité
- `{{ state_attr('entity_id', 'attribute') }}` → valeur d'un attribut

### Option de configuration

| Paramètre        | Type     | Valeur par défaut | Description                   |
| ---------------- | -------- | ----------------- | ----------------------------- |
| `secondary_info` | `object` | `null`            | Map de `device_id → template` |

La clé est l'identifiant de l'équipement (partie après `switch.solar_optimizer_`).

Exemple YAML :
```yaml
type: custom:solar-optimizer-card
secondary_info:
  lave_linge: "{{ states('sensor.lave_linge_programme') }}"
  borne_ve: "{{ state_attr('sensor.borne_ve', 'status') }}"
```

Si la clé n'est pas renseignée pour un équipement, rien n'est affiché.

## La barre d'historique d'activation

Chaque équipement dispose d'une barre horizontale d'historique d'activation, **toujours visible** (même lorsque la carte est pliée), placée juste en dessous de la barre de puissance.

- Les segments de couleur (`--success-color`) correspondent aux périodes d'activation (état `on`).
- Les segments gris correspondent aux périodes d'inactivité (état `off`).
- La barre couvre les N dernières heures (24h par défaut).
- Un label sous la barre indique : `Historique d'activation – Nh`.
- Les données sont récupérées via l'API History de Home Assistant et mises en cache 5 minutes.
- L'apparence imite les barres d'historique natives des `binary_sensor` de Home Assistant.

### Option de configuration

| Paramètre       | Type     | Valeur par défaut | Description                                         |
| --------------- | -------- | ----------------- | --------------------------------------------------- |
| `history_hours` | `number` | `24`              | Durée en heures de la fenêtre d'historique affichée |

Exemple YAML :
```yaml
type: custom:solar-optimizer-card
history_hours: 48
```

## Les actions
Chaque bloc représentant un équipement sera équipé des boutons d'actions suivants:
1. Un bouton enable : un bouton permettant d'enable l'équipement,
2. Un bouton start/stop : un bouton permettant d'activer/desactiver l'équipement manuellement.

## La fonction "timed activation" (activation forcée minutée)

Cette fonction permet à l'utilisateur de forcer l'activation d'un équipement pour une durée déterminée, indépendamment de l'algorithme Solar Optimizer.

### Comportement général

- Lors du déclenchement de l'activation forcée :
  - l'entité `enable` du managed device est mise sur `false`,
  - l'équipement est physiquement allumé,
  - le badge de statut affiche **MANUEL** (conforme aux règles de statut existantes : `!isEnabled && isActive`).
- L'appui sur le bouton **STOP** stoppe l'activation forcée, éteint l'équipement et annule le timer.
- Lorsqu'une activation forcée est active, l'appui sur le bouton **Enable** ne relance pas le timer ; il remet simplement l'entité `enable` à `true` et l'activation forcée est annulée.

### Sélecteur de durée

Un sélecteur est affiché **à côté du bouton START**, dans la zone des actions de chaque équipement.

**Durées disponibles :** `1h`, `4h`, `12h`, `24h`.

Le sélecteur a deux états visuels distincts :

| État                           | Affichage                                                                                           |
| ------------------------------ | --------------------------------------------------------------------------------------------------- |
| **Aucune activation active**   | Liste déroulante (ou boutons discrets) permettant de choisir la durée avant d'appuyer sur **START** |
| **Activation forcée en cours** | Affichage en lecture seule du **temps restant** — en heures si ≥ 1 h, en minutes si < 1 h           |

Lorsqu'aucune durée n'est sélectionnée et que l'utilisateur appuie sur **START**, le démarrage forcé est effectué **sans limite de temps** (comportement actuel inchangé).

### Service backend

Un service Home Assistant dédié est exposé pour déclencher ou arrêter la fonction timed activation :

```yaml
# Déclenchement
service: solar_optimizer.start_device
data:
  device_id: <identifiant du managed device>
  duration: <durée en heures : 1, 4, 12 ou 24>

# Arrêt
service: solar_optimizer.stop_device
data:
  device_id: <identifiant du managed device>
```

### Persistance du timer

- Le timer est géré **en backend** (côté intégration Python Solar Optimizer).
- La date/heure de fin de l'activation forcée est **persistée** (via les attributs de l'entité ou un storage dédié) de sorte qu'un redémarrage de Home Assistant restaure le timer avec la valeur restante correcte.
- L'entité expose un attribut `forced_end_time` (timestamp ISO 8601) que la carte lit pour calculer et afficher le temps restant.

### Attribut exposé par le backend

| Attribut          | Type                | Description                                                                    |
| ----------------- | ------------------- | ------------------------------------------------------------------------------ |
| `forced_end_time` | `string` (ISO 8601) | Heure de fin de l'activation forcée. `null` si aucune activation forcée active |

### Exemple de rendu

```
[ ENABLE ]   [ 4h ▾ ]  [ START ]
```

Quand l'activation est en cours :

```
[ ENABLE ]   [ 3h 27min ]  [ STOP ]
```

Quand moins d'une heure reste :

```
[ ENABLE ]   [ 43 min ]  [ STOP ]
```


