# Spécification fonctionnelle / Functional specification

## 1. Titre et métadonnées / Title and metadata

| Élément / Item                   | Valeur / Value                                                                                          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Nom / Name                       | Issue #212 - Ajout du domaine `water_heater` / Add the `water_heater` domain                            |
| Version                          | 1.1                                                                                                     |
| Statut / Status                  | Spécification du périmètre validé / Validated-scope specification                                       |
| Date                             | 2026-10-10                                                                                              |
| Propriétaire / Owner             | Projet Solar Optimizer                                                                                  |
| Référence / Reference            | GitHub issue [#212 - Add water_heater domain](https://github.com/jmcollin78/solar_optimizer/issues/212) |
| Rapport de revue / Review report | [issue-212-review.md](issue-212-review.md)                                                              |

---

# Version française

## 2. Contexte et objectifs

Solar Optimizer permet de configurer un appareil géré à partir d'une liste fermée de domaines Home Assistant. Le domaine `water_heater` n'est actuellement pas sélectionnable dans le schéma de configuration d'un appareil géré standard, alors que le mécanisme générique d'appel de services peut déjà transmettre un paramètre de service.

L'objectif est de permettre la sélection d'une entité `water_heater` comme appareil géré standard et de piloter ses modes de fonctionnement avec les services configurés par l'utilisateur, notamment `water_heater.set_operation_mode`. La fonctionnalité doit répondre au besoin de piloter directement l'entité du chauffe-eau, sans imposer une entité switch supplémentaire.

Le périmètre ne modifie ni l'algorithme d'optimisation, ni la syntaxe générique des services, ni le modèle d'appareil à puissance variable.

## 3. Utilisateurs et cas d'utilisation

### Acteurs

- **Utilisateur Home Assistant** : sélectionne l'entité `water_heater`, renseigne les services d'activation et de désactivation et les modes attendus par son intégration.
- **Solar Optimizer** : applique les actions d'activation et de désactivation selon sa décision d'optimisation.
- **Intégration Home Assistant du chauffe-eau** : reçoit les appels de service et détermine si le mode demandé est accepté.

### Cas d'utilisation nominal

1. L'utilisateur ajoute ou configure un appareil de type standard.
2. Le formulaire propose une entité du domaine `water_heater`.
3. L'utilisateur configure, par exemple, `water_heater/set_operation_mode/operation_mode:eco` pour l'activation et `water_heater/set_operation_mode/operation_mode:off` pour la désactivation.
4. Solar Optimizer déclenche l'action d'activation ou de désactivation.
5. Home Assistant reçoit un appel ciblant l'entité configurée, avec `operation_mode` comme donnée de service et la valeur configurée.

## 4. Exigences fonctionnelles

- **FR-001** — Le système doit autoriser le domaine Home Assistant `water_heater` dans le sélecteur d'entité de `managed_device_schema`.
- **FR-002** — Le système ne doit pas ajouter le domaine `water_heater` dans `power_managed_device_schema` dans le cadre de cette évolution.
- **FR-003** — Le système doit réutiliser le format générique de service existant `domaine/service[/clé:valeur]` pour les actions d'activation et de désactivation.
- **FR-004** — Lorsqu'un service configuré est `water_heater/set_operation_mode/operation_mode:<mode>`, le système doit appeler le service Home Assistant `set_operation_mode` du domaine `water_heater`, cibler l'entité sélectionnée et transmettre `{"operation_mode": "<mode>"}`.
- **FR-005** — Le système doit permettre de configurer une seule entité `water_heater` pour un appareil géré standard, conformément au modèle existant d'un appareil par configuration.
- **FR-006** — Le système ne doit pas imposer une liste globale de modes (`eco`, `automatic`, `off`, etc.). Les valeurs doivent rester configurables pour respecter les modes exposés par chaque intégration de chauffe-eau.
- **FR-007** — Le système doit conserver le comportement existant des autres domaines et des autres paramètres d'appareil.

## 5. Règles métier

- **BR-001** — Une entité `water_heater` ajoutée par cette évolution est un appareil géré standard à puissance fixe ou prédéterminée; elle n'est pas un appareil à puissance variable par défaut.
- **BR-002** — Le domaine et le service configurés doivent correspondre à l'entité et aux capacités de l'intégration Home Assistant utilisées par l'utilisateur.
- **BR-003** — Les modes d'activation et de désactivation sont indépendants et peuvent être différents; le mode de désactivation n'est pas implicitement déduit du mode d'activation.
- **BR-004** — La validité métier d'un mode est déterminée par l'intégration du chauffe-eau, pas par Solar Optimizer.

## 6. Contraintes fonctionnelles, compatibilité et documentation attendue

### Contraintes et compatibilité

- La fonctionnalité doit être compatible avec les versions de Home Assistant prises en charge qui exposent le domaine et la constante `water_heater.DOMAIN`.
- L'entité doit être sélectionnable dans le flux de configuration du type d'appareil standard; le type d'appareil à puissance variable reste inchangé.
- Aucun nouveau secret, accès réseau, traitement de données personnelles ou dépendance ne doit être introduit.
- Le changement doit rester compatible avec les configurations existantes et ne doit pas nécessiter de migration des entrées déjà créées.

### Documentation attendue

- La documentation utilisateur française et anglaise doit indiquer que `water_heater` est utilisable comme appareil standard.
- `README-fr.md` et `README.md` doivent ajouter `water_heater` à la liste des domaines compatibles pour un appareil standard.
- Ces deux README doivent contenir un exemple YAML complet, dans leur section d'exemples de configuration, utilisant `entity_id: "water_heater.<nom>"`, `water_heater/set_operation_mode/operation_mode:eco` à l'activation et `water_heater/set_operation_mode/operation_mode:off` à la désactivation.
- Elle doit préciser que les modes disponibles dépendent de l'intégration Home Assistant du chauffe-eau.
- Cet exemple doit présenter `eco` et `off` comme des valeurs indicatives, non comme une liste de modes imposée.

## 7. Erreurs et limites

- Le formulaire ne valide pas que l'intégration de l'entité expose effectivement `set_operation_mode` ni que le mode choisi est supporté.
- Une déclaration de service ne respectant pas le format générique existant reste une erreur de configuration; elle n'est pas corrigée ou réinterprétée par cette évolution.
- Si Home Assistant refuse le service ou le mode, l'appel peut échouer selon le comportement existant de l'appel générique; Solar Optimizer ne fournit pas de catalogue ni de conversion des modes.
- L'extension ne permet pas de piloter simultanément un `water_heater` et un switch distinct pour le même appareil.
- L'extension ne fournit pas d'interface dédiée à la sélection ou à la traduction des modes.

## 8. Critères d'acceptation

- **AC-001** — Dans le formulaire de configuration d'un appareil standard, une entité `water_heater.<nom>` est acceptée par le sélecteur; une entité `water_heater` n'est pas rendue disponible par le formulaire d'appareil à puissance variable.
- **AC-002** — Un test d'intégration crée un appareil géré avec l'entité `water_heater.fake_device_a` et une configuration d'activation `water_heater/set_operation_mode/operation_mode:eco`.
- **AC-003** — Lors de l'activation de cet appareil, le test vérifie un appel `water_heater.set_operation_mode` ciblant `water_heater.fake_device_a` avec `{"operation_mode": "eco"}`.
- **AC-004** — Lors de la désactivation, avec `water_heater/set_operation_mode/operation_mode:off`, le test vérifie le même service et la même cible avec `{"operation_mode": "off"}`.
- **AC-005** — Le test d'intégration démontre que le domaine, le service, la cible et la donnée `operation_mode` sont transmis sans modification par le format générique existant.
- **AC-006** — Les tests ciblés pertinents passent, ainsi que la suite de tests concernée, sans régression observable sur les appareils existants.
- **AC-007** — La documentation utilisateur contient l'exemple de configuration et l'avertissement sur les modes propres à l'intégration du chauffe-eau.

## 9. Fonctions non prises en compte

- Ajout de `water_heater` à `power_managed_device_schema`.
- Modulation, mesure ou optimisation de la puissance spécifique d'un chauffe-eau.
- Gestion simultanée de plusieurs entités pour un appareil Solar Optimizer.
- Nouvelle syntaxe de service, validation anticipée des modes ou interface dédiée aux modes.
- Modification de l'algorithme d'optimisation, du frontend, des dépendances, de la configuration existante ou des services Home Assistant.
- Conversion automatique entre les modes propres à différentes intégrations de chauffe-eau.

## 10. Évolutions futures proposées

- Ajouter une validation ou une aide contextuelle des services et modes exposés par l'entité, si Home Assistant fournit ces informations de manière fiable.
- Ajouter des exemples dédiés aux principales intégrations de chauffe-eau, sans transformer ces exemples en liste obligatoire de modes.
- Évaluer séparément un éventuel besoin de modulation de puissance; cette décision nécessiterait une nouvelle analyse fonctionnelle et ne relève pas de l'issue #212.

## 11. Hypothèses, questions ouvertes et traçabilité

### Faits établis

- Le rapport de revue indique que `managed_device_schema` est le filtre du formulaire standard et que `water_heater` en est absent.
- Le rapport indique que `power_managed_device_schema` ne doit pas être étendu.
- `ManagedDevice.do_service_action` accepte le format `domaine/service/clé:valeur`, construit les données de service et cible l'`entity_id` configuré.
- `tests/test_non_switch_device.py` vérifie déjà le même contrat avec `climate.set_hvac_mode` et constitue le modèle du test demandé.
- Le manifeste local déclare la version de l'intégration Solar Optimizer `3.8.1`; la version minimale de Home Assistant n'est pas déclarée dans le fichier consulté.

### Hypothèses retenues

- Les versions de Home Assistant supportées exposent `homeassistant.components.water_heater.DOMAIN`.
- Un test peut vérifier les appels de service avec une entité simulée, sans charger une intégration physique de chauffe-eau.
- Les modes `eco` et `off` servent d'exemple de test et ne constituent pas une liste normative pour toutes les intégrations.

### Questions ouvertes

- La version minimale exacte de Home Assistant à certifier pour l'import de `water_heater.DOMAIN` doit être confirmée avant livraison.

Aucune question ouverte ne bloque la définition du périmètre fonctionnel validé.

### Traçabilité

| Élément                                | Source vérifiée                                                                                                |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Besoin et limites de l'issue           | [Rapport de revue #212](issue-212-review.md), sections « Référence et résumé fidèle » et « Périmètre proposé » |
| Filtre des entités standard            | [`managed_device_schema`](../../custom_components/solar_optimizer/config_schema.py)                            |
| Exclusion du type à puissance variable | [`power_managed_device_schema`](../../custom_components/solar_optimizer/config_schema.py) et rapport de revue  |
| Format et transmission des services    | [`do_service_action`](../../custom_components/solar_optimizer/managed_device.py)                               |
| Flux de configuration standard         | [`async_step_device`](../../custom_components/solar_optimizer/config_flow.py)                                  |
| Modèle de test d'intégration           | [`test_climate_device`](../../tests/test_non_switch_device.py)                                                 |
| Compatibilité déclarée                 | [`manifest.json`](../../custom_components/solar_optimizer/manifest.json)                                       |

---

# English version

## 2. Context and objectives

Solar Optimizer configures a managed device from a closed list of Home Assistant domains. The `water_heater` domain is currently not selectable in the configuration schema for a standard managed device, although the generic service-call mechanism can already transmit a service parameter.

The objective is to allow a `water_heater` entity to be selected as a standard managed device and to control its operating modes through user-configured services, in particular `water_heater.set_operation_mode`. The feature must directly control the water-heater entity without requiring an additional switch entity.

The scope changes neither the optimization algorithm, nor the generic service syntax, nor the variable-power device model.

## 3. Users and use cases

### Actors

- **Home Assistant user**: selects the `water_heater` entity and configures activation and deactivation services and the modes supported by the user's integration.
- **Solar Optimizer**: applies activation and deactivation actions according to its optimization decision.
- **Water-heater Home Assistant integration**: receives the service calls and determines whether the requested mode is accepted.

### Nominal use case

1. The user adds or configures a standard device.
2. The form offers an entity from the `water_heater` domain.
3. The user configures, for example, `water_heater/set_operation_mode/operation_mode:eco` for activation and `water_heater/set_operation_mode/operation_mode:off` for deactivation.
4. Solar Optimizer triggers the activation or deactivation action.
5. Home Assistant receives a call targeting the selected entity, with `operation_mode` as service data and the configured value.

## 4. Functional requirements

- **FR-001** — The system shall allow the Home Assistant `water_heater` domain in the entity selector of `managed_device_schema`.
- **FR-002** — The system shall not add the `water_heater` domain to `power_managed_device_schema` as part of this change.
- **FR-003** — The system shall reuse the existing generic service format `domain/service[/key:value]` for activation and deactivation actions.
- **FR-004** — When a configured service is `water_heater/set_operation_mode/operation_mode:<mode>`, the system shall call the Home Assistant `set_operation_mode` service in the `water_heater` domain, target the selected entity, and pass `{"operation_mode": "<mode>"}`.
- **FR-005** — The system shall allow one `water_heater` entity to be configured for one standard managed device, consistently with the existing one-entity-per-device model.
- **FR-006** — The system shall not impose a global list of modes (`eco`, `automatic`, `off`, etc.). Values shall remain configurable to match the modes exposed by each water-heater integration.
- **FR-007** — The system shall preserve the existing behavior of other domains and other device parameters.

## 5. Business rules

- **BR-001** — A `water_heater` entity added by this change is a standard managed device with fixed or predetermined power; it is not a variable-power device by default.
- **BR-002** — The configured domain and service shall match the entity and capabilities of the Home Assistant integration used by the user.
- **BR-003** — Activation and deactivation modes are independent and may differ; the deactivation mode shall not be implicitly derived from the activation mode.
- **BR-004** — The water-heater integration, not Solar Optimizer, determines whether a mode is valid.

## 6. Functional constraints, compatibility, and expected documentation

### Constraints and compatibility

- The feature shall be compatible with supported Home Assistant versions exposing the `water_heater` domain and the `water_heater.DOMAIN` constant.
- The entity shall be selectable in the standard-device configuration flow; the variable-power device type shall remain unchanged.
- No new secret, network access, personal-data processing, or dependency shall be introduced.
- The change shall remain compatible with existing configurations and shall not require migration of existing entries.

### Expected documentation

- The French and English user documentation shall state that `water_heater` can be used as a standard device.
- `README-fr.md` and `README.md` shall add `water_heater` to the list of supported standard-device domains.
- Both README files shall contain a complete YAML example in their configuration-examples section, using `entity_id: "water_heater.<name>"`, `water_heater/set_operation_mode/operation_mode:eco` for activation, and `water_heater/set_operation_mode/operation_mode:off` for deactivation.
- It shall state that available modes depend on the water-heater's Home Assistant integration.
- The example shall present `eco` and `off` as illustrative values, not as a mandatory mode list.

## 7. Errors and limitations

- The form does not validate that the entity's integration exposes `set_operation_mode` or that the selected mode is supported.
- A service declaration that does not follow the existing generic format remains a configuration error; this change does not repair or reinterpret it.
- If Home Assistant rejects the service or mode, the call may fail according to the existing generic-call behavior; Solar Optimizer provides no mode catalog or conversion.
- The change does not control a `water_heater` and a separate switch simultaneously for the same device.
- The change does not provide a dedicated interface for selecting or translating modes.

## 8. Acceptance criteria

- **AC-001** — In the standard-device configuration form, a `water_heater.<name>` entity is accepted by the selector; a `water_heater` entity is not made available by the variable-power device form.
- **AC-002** — An integration test creates a managed device with entity `water_heater.fake_device_a` and activation configuration `water_heater/set_operation_mode/operation_mode:eco`.
- **AC-003** — When the device is activated, the test verifies a `water_heater.set_operation_mode` call targeting `water_heater.fake_device_a` with `{"operation_mode": "eco"}`.
- **AC-004** — On deactivation, with `water_heater/set_operation_mode/operation_mode:off`, the test verifies the same service and target with `{"operation_mode": "off"}`.
- **AC-005** — The integration test demonstrates that the domain, service, target, and `operation_mode` data are passed unchanged through the existing generic format.
- **AC-006** — The relevant focused tests and the relevant test suite pass with no observable regression for existing devices.
- **AC-007** — User documentation contains the configuration example and the warning that modes are specific to the water-heater integration.

## 9. Out of scope

- Adding `water_heater` to `power_managed_device_schema`.
- Water-heater-specific power modulation, measurement, or optimization.
- Configuring multiple entities for one Solar Optimizer device.
- A new service syntax, early mode validation, or a dedicated mode interface.
- Changes to the optimization algorithm, frontend, dependencies, existing configuration, or Home Assistant services.
- Automatic conversion between modes from different water-heater integrations.

## 10. Proposed future enhancements

- Add validation or contextual help for services and modes exposed by the entity, if Home Assistant provides this information reliably.
- Add examples for major water-heater integrations without turning those examples into a mandatory mode list.
- Assess a possible power-modulation need separately; such a decision would require a new functional analysis and is outside issue #212.

## 11. Assumptions, open questions, and traceability

### Established facts

- The review report states that `managed_device_schema` filters the standard form and that `water_heater` is absent from it.
- The report states that `power_managed_device_schema` shall not be extended.
- `ManagedDevice.do_service_action` accepts the `domain/service/key:value` format, builds service data, and targets the configured `entity_id`.
- `tests/test_non_switch_device.py` already verifies the same contract with `climate.set_hvac_mode` and is the model for the requested test.
- The local manifest declares Solar Optimizer version `3.8.1`; the minimum Home Assistant version is not declared in the inspected file.

### Retained assumptions

- Supported Home Assistant versions expose `homeassistant.components.water_heater.DOMAIN`.
- A test can verify service calls with a simulated entity without loading a physical water-heater integration.
- `eco` and `off` are test examples and do not form a normative list for all integrations.

### Open questions

- The exact minimum Home Assistant version to certify for importing `water_heater.DOMAIN` must be confirmed before delivery.

No open question blocks the definition of the validated functional scope.

### Traceability

| Item                            | Verified source                                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Issue need and limits           | [#212 review report](issue-212-review.md), “Reference and faithful summary” and “Proposed scope” sections   |
| Standard entity filter          | [`managed_device_schema`](../../custom_components/solar_optimizer/config_schema.py)                         |
| Variable-power exclusion        | [`power_managed_device_schema`](../../custom_components/solar_optimizer/config_schema.py) and review report |
| Service format and transmission | [`do_service_action`](../../custom_components/solar_optimizer/managed_device.py)                            |
| Standard configuration flow     | [`async_step_device`](../../custom_components/solar_optimizer/config_flow.py)                               |
| Integration-test model          | [`test_climate_device`](../../tests/test_non_switch_device.py)                                              |
| Declared compatibility          | [`manifest.json`](../../custom_components/solar_optimizer/manifest.json)                                    |