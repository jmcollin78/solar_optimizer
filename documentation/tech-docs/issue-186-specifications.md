# Spécification fonctionnelle / Functional specification

## 1. Titre et métadonnées / Title and metadata

| Élément / Item                                       | Valeur / Value                                                                                        |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Nom / Name                                           | Issue #186 - Puissance et durée spécifiques aux heures creuses / Off-peak-specific power and duration |
| Version                                              | 1.0                                                                                                   |
| Statut / Status                                      | Spécification du périmètre validé / Validated-scope specification                                     |
| Date                                                 | 2026-10-10                                                                                            |
| Propriétaire / Owner                                 | Projet Solar Optimizer                                                                                |
| Référence / Reference                                | GitHub issue [#186](https://github.com/jmcollin78/solar_optimizer/issues/186)                         |
| Rapport validé / Validated review                    | [issue-186-review.md](issue-186-review.md)                                                            |
| Version actuelle vérifiée / Verified current version | `3.8.4`                                                                                               |

---

# Version française

## 2. Contexte et objectifs

Lorsqu'une activation est forcée par les heures creuses, un appareil à puissance variable peut être activé sans recevoir de nouvelle consigne de puissance. Pour un équipement qui remet sa puissance à zéro lorsqu'il est éteint, cette activation ne produit alors pas l'effet attendu.

L'objectif est de rendre ce forçage fonctionnel et configurable, tout en conservant le comportement existant par défaut :

- permettre une puissance spécifique aux heures creuses uniquement pour les appareils à puissance variable ;
- envoyer explicitement cette puissance lors de l'activation forcée par les heures creuses ;
- utiliser `power_max` lorsqu'aucune puissance heures creuses n'est configurée ;
- permettre une durée maximale spécifique aux heures creuses pour tout appareil géré ;
- utiliser `max_on_time_per_day_min` lorsqu'aucune durée maximale heures creuses n'est configurée ;
- conserver la durée minimale existante comme objectif d'arrêt du forçage en heures creuses.

Le périmètre porte sur le comportement fonctionnel, la configuration, la validation, les tests et la documentation de cette évolution. Il ne prescrit pas les noms exacts des nouvelles clés de configuration ni leur implémentation interne.

## 3. Acteurs et cas d'utilisation

### Acteurs

- **Utilisateur Home Assistant** : configure un appareil, ses limites de puissance et ses durées, puis peut observer le fonctionnement en heures creuses.
- **Solar Optimizer** : détermine si le forçage en heures creuses s'applique, transmet la puissance requise et arrête le forçage selon les durées configurées.
- **Appareil géré** : reçoit l'activation, la désactivation et, lorsqu'il est à puissance variable, la consigne de puissance.

### Cas d'utilisation nominal : appareil à puissance variable

1. L'utilisateur configure un appareil à puissance variable et, éventuellement, une puissance heures creuses.
2. Une période d'heures creuses déclenche un forçage alors que la durée minimale quotidienne n'est pas atteinte.
3. Solar Optimizer active l'appareil et lui transmet explicitement la puissance heures creuses configurée.
4. Si cette puissance n'est pas configurée, Solar Optimizer transmet `power_max`.
5. Le forçage cesse lorsque la durée minimale est atteinte, sous réserve de la durée maximale heures creuses applicable.

### Cas d'utilisation nominal : appareil sans puissance variable

1. L'utilisateur configure éventuellement une durée maximale heures creuses.
2. Une période d'heures creuses déclenche le forçage selon le comportement existant.
3. Le forçage vise l'atteinte de la durée minimale existante et ne doit pas exposer une configuration de puissance heures creuses propre aux appareils à puissance variable.

## 4. Exigences fonctionnelles

- **FR-001** — Le système doit permettre de configurer une puissance heures creuses optionnelle uniquement pour un appareil à puissance variable.
- **FR-002** — Lorsqu'un appareil à puissance variable est activé parce que le forçage heures creuses s'applique, le système doit transmettre explicitement une consigne de puissance à l'appareil.
- **FR-003** — Lorsque la puissance heures creuses n'est pas configurée pour un appareil à puissance variable, le système doit utiliser `power_max` comme puissance transmise.
- **FR-004** — Le système doit permettre de configurer une durée maximale heures creuses optionnelle pour tout appareil géré, qu'il soit à puissance variable ou non.
- **FR-005** — Lorsque la durée maximale heures creuses n'est pas configurée, le système doit utiliser `max_on_time_per_day_min` comme limite applicable aux heures creuses.
- **FR-006** — Pendant le forçage en heures creuses, le système doit conserver la durée minimale existante comme objectif d'arrêt : la durée maximale heures creuses ne doit pas remplacer cet objectif.
- **FR-007** — Le système doit appliquer la durée maximale heures creuses comme limite supérieure du fonctionnement forcé pendant la période d'heures creuses, selon les règles de priorité définies ci-dessous.
- **FR-008** — Le système doit conserver le comportement actuel des configurations existantes qui ne renseignent aucune nouvelle valeur.
- **FR-009** — Le système doit distinguer l'absence d'une valeur optionnelle d'une valeur invalide et signaler une valeur invalide lors de la configuration ou de sa validation.
- **FR-010** — La documentation française et anglaise doit expliquer les deux réglages, leur portée, leurs valeurs par défaut et leur interaction avec la durée minimale existante.
- **FR-011** — La livraison doit incrémenter la version mineure de l'intégration et annoncer l'évolution dans l'en-tête des README français et anglais.

## 5. Règles métier

- **BR-001** — Une puissance heures creuses ne peut être associée qu'à un appareil à puissance variable ; elle ne doit pas être proposée ni interprétée pour un appareil à puissance fixe ou standard.
- **BR-002** — La puissance transmise lors d'une activation forcée en heures creuses est la puissance heures creuses configurée lorsqu'elle existe ; sinon, c'est `power_max`.
- **BR-003** — La puissance heures creuses doit respecter les bornes et la cohérence applicables aux puissances de l'appareil, notamment la relation attendue avec `power_max` ; les bornes exactes restent à fixer en conception et doivent être documentées.
- **BR-004** — La durée maximale heures creuses est applicable à tous les appareils gérés, y compris ceux qui ne sont pas à puissance variable.
- **BR-005** — En l'absence de durée maximale heures creuses, la valeur effective est `max_on_time_per_day_min`, ce qui préserve la configuration et le comportement actuels.
- **BR-006** — La durée minimale existante reste la cible d'arrêt du forçage en heures creuses ; une durée maximale distincte limite la durée autorisée mais ne transforme pas la cible minimale.
- **BR-007** — Une durée maximale heures creuses doit être compatible avec les contraintes de durée déjà applicables à l'appareil ; les bornes exactes, ainsi que le traitement d'une incohérence avec la durée minimale, doivent être définis et validés avant implémentation.
- **BR-008** — Les valeurs absentes utilisent les valeurs de repli définies par cette spécification ; aucune nouvelle valeur par défaut silencieuse différente ne doit être introduite.

## 6. Contraintes fonctionnelles, compatibilité et documentation attendue

### Configuration et validation

- Les noms exacts des nouvelles clés sont des décisions de conception et ne sont pas imposés par cette spécification.
- La configuration doit rendre visible qu'une puissance heures creuses concerne exclusivement les appareils à puissance variable.
- La durée maximale heures creuses doit être disponible pour tous les types d'appareils concernés par le forçage.
- Les champs optionnels doivent accepter l'absence de valeur et appliquer les replis `power_max` ou `max_on_time_per_day_min` selon le cas.
- Une valeur non numérique, négative, hors borne ou incohérente avec les limites existantes doit être refusée ou signalée par une erreur de validation explicite ; le choix entre validation bloquante et message d'erreur doit être fixé en conception, sans accepter silencieusement la valeur.
- La spécification ne fixe pas les bornes numériques exactes. Elles doivent être cohérentes avec les bornes existantes et être identiques dans le flux de configuration, la validation et la documentation.

### Compatibilité ascendante

- Une configuration existante sans puissance heures creuses doit continuer à utiliser `power_max` lors du forçage d'un appareil à puissance variable.
- Une configuration existante sans durée maximale heures creuses doit continuer à utiliser `max_on_time_per_day_min`.
- Aucun appareil existant ne doit devenir invalide uniquement parce que les nouvelles options sont absentes.
- Aucune migration manuelle ne doit être nécessaire pour bénéficier des valeurs de repli.
- Les appareils non variables ne doivent pas recevoir de nouvelle consigne de puissance spécifique aux heures creuses.

### Documentation et livraison

- La documentation utilisateur FR doit décrire le paramétrage, les valeurs par défaut, la durée minimale comme objectif et les erreurs attendues ; la documentation EN doit fournir le même contenu avec les mêmes identifiants.
- `README-fr.md` et `README.md` doivent annoncer l'évolution dans leur en-tête pour la release concernée.
- La release doit incrémenter le numéro de version mineure de l'intégration ; le numéro exact de release relève de la gestion de version et n'est pas fixé ici.
- Les tests ciblés du forçage heures creuses et les tests de non-régression doivent accompagner la livraison.

## 7. Erreurs, validation et limites

- Une puissance heures creuses renseignée pour un appareil qui n'est pas à puissance variable doit être rejetée, ignorée avec un message explicite, ou rendue impossible par l'interface ; le comportement retenu doit éviter toute interprétation silencieuse.
- Une puissance heures creuses invalide ou incompatible avec `power_max` doit produire une erreur de validation compréhensible et ne doit pas être envoyée à l'appareil.
- Une durée maximale heures creuses invalide ou incompatible avec les contraintes de durée existantes doit produire une erreur de validation compréhensible et ne doit pas être appliquée silencieusement.
- L'absence d'une valeur optionnelle n'est pas une erreur : elle déclenche le repli défini par **BR-002** ou **BR-005**.
- Le comportement d'un appareil qui refuse la consigne de puissance reste soumis au comportement existant de l'appel à l'appareil ; cette issue ne définit pas une nouvelle stratégie de reprise.
- Cette évolution ne crée pas de gestion de l'énergie stockée, de chauffe anticipée ou de pilotage énergétique interne à un chauffe-eau.

## 8. Critères d'acceptation

- **AC-001** — Pour un appareil à puissance variable avec une puissance heures creuses configurée, une activation forcée en heures creuses envoie exactement cette puissance au lieu de laisser la consigne à zéro ou non définie.
- **AC-002** — Pour un appareil à puissance variable sans puissance heures creuses configurée, une activation forcée en heures creuses envoie `power_max`.
- **AC-003** — La configuration d'un appareil non variable ne propose pas de puissance heures creuses ; si une valeur est fournie par un autre moyen, elle est traitée selon une validation explicite et ne modifie pas le comportement de puissance de cet appareil.
- **AC-004** — Pour un appareil quelconque avec une durée maximale heures creuses configurée, le forçage s'arrête au plus tard à cette limite pendant les heures creuses.
- **AC-005** — Pour un appareil quelconque sans durée maximale heures creuses configurée, le système applique `max_on_time_per_day_min` comme limite heures creuses.
- **AC-006** — Dans un scénario où la durée minimale n'est pas atteinte et où la durée maximale autorise encore le fonctionnement, le forçage continue jusqu'à l'atteinte de la durée minimale ; la durée maximale ne devient pas la cible de durée.
- **AC-007** — Dans un scénario où la durée maximale heures creuses est atteinte avant la durée minimale, le système respecte la limite maximale et le résultat observable est documenté comme tel ; aucune prolongation au-delà de cette limite n'est effectuée.
- **AC-008** — Les valeurs existantes sans nouvelles options produisent le même comportement qu'avant l'évolution, notamment les replis `power_max` et `max_on_time_per_day_min`.
- **AC-009** — Une valeur de puissance ou de durée non numérique, négative, hors borne ou incohérente est refusée ou signalée par une erreur de validation ; elle n'est pas appliquée silencieusement.
- **AC-010** — Les tests couvrent au minimum un appareil variable avec et sans puissance heures creuses, un appareil non variable, chaque repli de durée et l'interaction entre durée minimale et maximale.
- **AC-011** — La documentation FR et EN décrit les options, les valeurs par défaut, les règles de validation et la compatibilité ascendante avec des identifiants et un contenu équivalents.
- **AC-012** — La version mineure de l'intégration est incrémentée et l'évolution est annoncée dans l'en-tête des README FR et EN de la release.

## 9. Fonctions non prises en compte

- La puissance heures creuses pour les appareils à puissance fixe ou standard.
- Une refonte générale de l'algorithme d'optimisation solaire ou de la priorisation des appareils.
- Une modification de la durée minimale existante ou son remplacement par la durée maximale heures creuses.
- Une nouvelle logique de stockage, de chauffe anticipée ou de gestion de l'énergie d'un chauffe-eau.
- La définition, dans cette spécification, des noms exacts des clés, des fichiers ou des structures techniques de configuration.
- Le changement des bornes historiques sans justification fonctionnelle distincte.
- Une stratégie nouvelle de reprise lorsqu'un appareil refuse une consigne de puissance.
- Une migration obligatoire des configurations existantes.

## 10. Évolutions futures proposées

- Ajouter une aide contextuelle dans le flux de configuration pour expliquer les valeurs de repli et les interactions entre les durées.
- Évaluer séparément une validation dynamique des capacités de puissance exposées par chaque intégration Home Assistant.
- Ajouter des diagnostics dédiés lorsqu'un appareil refuse la puissance forcée ou atteint sa limite maximale avant la durée minimale.
- Réexaminer les règles de priorité entre durée minimale quotidienne, durée maximale quotidienne et durée maximale heures creuses sur la base de retours d'utilisation.

## 11. Hypothèses, questions ouvertes et traçabilité

### Faits établis

- Le rapport validé indique qu'une activation forcée par `should_be_forced_offpeak` peut ne pas transmettre de puissance lorsque l'état algorithmique n'est pas actif.
- Le rapport indique qu'aucune option de puissance spécifique aux heures creuses n'existe actuellement.
- Le rapport indique qu'une absence de durée maximale utilise actuellement une limite interne de 24 heures et que la durée minimale est la cible d'arrêt du forçage.
- Le périmètre validé retient `power_max` comme repli de puissance et `max_on_time_per_day_min` comme repli de durée maximale heures creuses.

### Hypothèses retenues

- « Appareil à puissance variable » désigne le type d'appareil déjà distingué par la configuration actuelle ; cette spécification ne redéfinit pas ce type.
- « Puissance transmise explicitement » signifie qu'une consigne est fournie lors de l'activation forcée, même si l'état de solution algorithmique ne demande pas une activation solaire ordinaire.
- Les durées sont exprimées dans les unités déjà utilisées par les réglages existants ; aucune nouvelle unité n'est introduite.

### Questions ouvertes non bloquantes pour le périmètre

- Quels noms exacts donner aux deux nouvelles clés de configuration ?
- Quelles bornes exactes appliquer aux deux valeurs et quelle règle explicite appliquer lorsqu'une durée maximale heures creuses est inférieure à la durée minimale ?
- La validation doit-elle bloquer l'enregistrement ou afficher une erreur au moment de l'utilisation ?

Ces questions relèvent de la conception et de la validation technique. Elles ne bloquent pas la définition du comportement fonctionnel validé, mais doivent être résolues avant l'implémentation.

### Traçabilité

| Élément                                                        | Source vérifiée                                                                                                                                              |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Besoin, décisions et exclusions                                | [Rapport de revue de l'issue #186](issue-186-review.md), sections « Périmètre proposé », « Impacts et risques » et « Faits confirmés »                       |
| Chemin de forçage heures creuses                               | [coordinator.py](../../custom_components/solar_optimizer/coordinator.py), symbole `should_be_forced_offpeak` cité et vérifié dans le rapport                 |
| Gestion des durées et valeur par défaut actuelle               | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py), comportement de durée cité et vérifié dans le rapport                        |
| Configuration des puissances                                   | [config_schema.py](../../custom_components/solar_optimizer/config_schema.py), absence actuelle d'une option heures creuses citée et vérifiée dans le rapport |
| Version actuelle                                               | [manifest.json](../../custom_components/solar_optimizer/manifest.json), version `3.8.4`                                                                      |
| En-têtes de documentation à mettre à jour lors de la livraison | [README-fr.md](../../README-fr.md) et [README.md](../../README.md)                                                                                           |

---

# English version

## 2. Context and objectives

When an activation is forced by off-peak hours, a variable-power device may be activated without receiving a new power setpoint. For equipment that resets its power to zero when switched off, that activation then has no effective result.

The objective is to make this forcing behavior functional and configurable while preserving the current defaults:

- allow an off-peak power setting only for variable-power devices;
- explicitly send that power when activation is forced by off-peak hours;
- use `power_max` when no off-peak power is configured;
- allow an off-peak maximum duration for every managed device;
- use `max_on_time_per_day_min` when no off-peak maximum duration is configured;
- keep the existing minimum duration as the stopping target for off-peak forcing.

The scope covers the functional behavior, configuration, validation, tests, and documentation for this change. It does not prescribe the exact names of the new configuration keys or their internal implementation.

## 3. Actors and use cases

### Actors

- **Home Assistant user**: configures a device, its power limits and durations, then observes off-peak behavior.
- **Solar Optimizer**: determines whether off-peak forcing applies, sends the required power, and stops forcing according to the configured durations.
- **Managed device**: receives activation, deactivation, and, for variable-power devices, the power setpoint.

### Nominal use case: variable-power device

1. The user configures a variable-power device and, optionally, an off-peak power.
2. An off-peak period triggers forcing while the daily minimum duration has not been reached.
3. Solar Optimizer activates the device and explicitly sends the configured off-peak power.
4. If that power is not configured, Solar Optimizer sends `power_max`.
5. Forcing stops when the minimum duration is reached, subject to the applicable off-peak maximum duration.

### Nominal use case: non-variable device

1. The user optionally configures an off-peak maximum duration.
2. An off-peak period triggers forcing according to the existing behavior.
3. Forcing targets the existing minimum duration and must not expose a variable-device-specific off-peak power setting.

## 4. Functional requirements

- **FR-001** — The system shall allow an optional off-peak power to be configured only for a variable-power device.
- **FR-002** — When a variable-power device is activated because off-peak forcing applies, the system shall explicitly send a power setpoint to the device.
- **FR-003** — When no off-peak power is configured for a variable-power device, the system shall use `power_max` as the transmitted power.
- **FR-004** — The system shall allow an optional off-peak maximum duration to be configured for every managed device, whether variable-power or not.
- **FR-005** — When no off-peak maximum duration is configured, the system shall use `max_on_time_per_day_min` as the applicable off-peak limit.
- **FR-006** — During off-peak forcing, the system shall preserve the existing minimum duration as the stopping target; the off-peak maximum duration shall not replace that target.
- **FR-007** — The system shall apply the off-peak maximum duration as the upper limit for forced operation during off-peak hours, according to the business rules below.
- **FR-008** — The system shall preserve the current behavior of existing configurations that provide neither new value.
- **FR-009** — The system shall distinguish an absent optional value from an invalid value and shall report an invalid value during configuration or validation.
- **FR-010** — French and English documentation shall explain both settings, their scope, their defaults, and their interaction with the existing minimum duration.
- **FR-011** — The release shall increment the integration's minor version and announce the change in the French and English README headers.

## 5. Business rules

- **BR-001** — Off-peak power may be associated only with a variable-power device; it shall neither be offered nor interpreted for a fixed-power or standard device.
- **BR-002** — The power sent during a forced off-peak activation is the configured off-peak power when present; otherwise it is `power_max`.
- **BR-003** — Off-peak power shall respect the bounds and consistency constraints applicable to the device's power settings, including the expected relationship with `power_max`; exact bounds remain a design decision and shall be documented.
- **BR-004** — Off-peak maximum duration applies to all managed devices, including non-variable devices.
- **BR-005** — When no off-peak maximum duration is configured, the effective value is `max_on_time_per_day_min`, preserving existing configuration and behavior.
- **BR-006** — The existing minimum duration remains the stopping target for off-peak forcing; a separate maximum duration limits the permitted time but does not change the minimum-duration target.
- **BR-007** — An off-peak maximum duration shall be compatible with existing device-duration constraints; exact bounds and the handling of inconsistency with the minimum duration shall be defined and validated before implementation.
- **BR-008** — Missing values use the defaults defined by this specification; no different silent default shall be introduced.

## 6. Functional constraints, compatibility, and expected documentation

### Configuration and validation

- The exact names of the new keys are design decisions and are not imposed by this specification.
- Configuration shall make clear that off-peak power is exclusive to variable-power devices.
- Off-peak maximum duration shall be available for every device type concerned by forcing.
- Optional fields shall accept an absent value and apply the `power_max` or `max_on_time_per_day_min` fallback as applicable.
- A non-numeric, negative, out-of-range, or inconsistent value shall be rejected or reported through an explicit validation error; the design choice between blocking validation and an error message shall be settled during design, and the value shall not be silently accepted.
- This specification does not set exact numeric bounds. They shall be consistent with existing bounds and identical across configuration flow, validation, and documentation.

### Backward compatibility

- An existing configuration without off-peak power shall continue to use `power_max` when forcing a variable-power device.
- An existing configuration without an off-peak maximum duration shall continue to use `max_on_time_per_day_min`.
- No existing device shall become invalid solely because the new options are absent.
- No manual migration shall be required to benefit from the fallback values.
- Non-variable devices shall not receive a new off-peak-specific power setpoint.

### Documentation and delivery

- French and English user documentation shall describe configuration, defaults, the minimum duration as the target, and expected errors; both versions shall contain the same content with the same identifiers.
- `README-fr.md` and `README.md` shall announce the change in their headers for the relevant release.
- The release shall increment the integration minor version; the exact release number belongs to release management and is not fixed here.
- Targeted off-peak forcing tests and regression tests shall accompany the release.

## 7. Errors, validation, and limitations

- Off-peak power provided for a non-variable device shall be rejected, ignored with an explicit message, or made impossible by the interface; the selected behavior shall avoid silent interpretation.
- Invalid off-peak power or power inconsistent with `power_max` shall produce an understandable validation error and shall not be sent to the device.
- Invalid off-peak maximum duration or duration inconsistent with existing duration constraints shall produce an understandable validation error and shall not be silently applied.
- An absent optional value is not an error; it triggers the fallback defined by **BR-002** or **BR-005**.
- A device refusing the power setpoint remains subject to the existing device-call behavior; this issue does not define a new retry strategy.
- This change does not create stored-energy management, anticipatory heating, or internal water-heater energy control.

## 8. Acceptance criteria

- **AC-001** — For a variable-power device with configured off-peak power, a forced off-peak activation sends exactly that power instead of leaving the setpoint at zero or undefined.
- **AC-002** — For a variable-power device without configured off-peak power, a forced off-peak activation sends `power_max`.
- **AC-003** — Configuration for a non-variable device does not offer off-peak power; if a value is supplied by another means, it is handled through explicit validation and does not change that device's power behavior.
- **AC-004** — For any device with configured off-peak maximum duration, forcing stops no later than that limit during off-peak hours.
- **AC-005** — For any device without configured off-peak maximum duration, the system applies `max_on_time_per_day_min` as the off-peak limit.
- **AC-006** — In a scenario where the minimum duration has not been reached and the maximum duration still permits operation, forcing continues until the minimum duration is reached; the maximum duration does not become the duration target.
- **AC-007** — In a scenario where the off-peak maximum duration is reached before the minimum duration, the system respects the maximum limit and documents the observable result; no operation beyond that limit occurs.
- **AC-008** — Existing values without the new options produce the same behavior as before the change, including the `power_max` and `max_on_time_per_day_min` fallbacks.
- **AC-009** — Non-numeric, negative, out-of-range, or inconsistent power or duration values are rejected or reported through a validation error and are not silently applied.
- **AC-010** — Tests cover at least a variable-power device with and without off-peak power, a non-variable device, each duration fallback, and the interaction between minimum and maximum durations.
- **AC-011** — French and English documentation describes options, defaults, validation rules, and backward compatibility with equivalent identifiers and content.
- **AC-012** — The integration minor version is incremented and the change is announced in the French and English README headers for the release.

## 9. Functions out of scope

- Off-peak power for fixed-power or standard devices.
- A general redesign of the solar optimization algorithm or device prioritization.
- Changing the existing minimum duration or replacing it with the off-peak maximum duration.
- New storage, anticipatory-heating, or water-heater energy-management logic.
- Defining exact key names, files, or technical configuration structures in this specification.
- Changing historical bounds without a separate functional justification.
- A new retry strategy when a device rejects a power setpoint.
- Mandatory migration of existing configurations.

## 10. Proposed future enhancements

- Add contextual help in the configuration flow explaining fallback values and duration interactions.
- Separately assess dynamic validation of power capabilities exposed by each Home Assistant integration.
- Add dedicated diagnostics when a device rejects forced power or reaches its maximum before the minimum duration.
- Reassess priority rules between daily minimum duration, daily maximum duration, and off-peak maximum duration based on usage feedback.

## 11. Assumptions, open questions, and traceability

### Established facts

- The validated review states that activation forced by `should_be_forced_offpeak` may fail to transmit power when the algorithmic solution state is not active.
- The review states that no off-peak-specific power option currently exists.
- The review states that an absent maximum duration currently uses an internal 24-hour limit and that the minimum duration is the stopping target for forcing.
- The validated scope selects `power_max` as the power fallback and `max_on_time_per_day_min` as the off-peak maximum-duration fallback.

### Retained assumptions

- “Variable-power device” means the device type already distinguished by current configuration; this specification does not redefine that type.
- “Explicitly transmitted power” means that a setpoint is provided during forced activation even when the algorithmic solution state does not request an ordinary solar activation.
- Durations use the units already used by existing settings; no new unit is introduced.

### Open questions that do not block the scope

- What exact names should be given to the two new configuration keys?
- What exact bounds should apply to both values, and what explicit rule should apply when an off-peak maximum duration is lower than the minimum duration?
- Should validation block saving or report an error when the value is used?

These questions belong to design and technical validation. They do not block the definition of the validated functional behavior, but they must be resolved before implementation.

### Traceability

| Item                                        | Verified source                                                                                                                                      |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Need, decisions, and exclusions             | [Issue #186 review report](issue-186-review.md), “Proposed scope”, “Impacts and risks”, and “Confirmed facts” sections                               |
| Off-peak forcing path                       | [coordinator.py](../../custom_components/solar_optimizer/coordinator.py), `should_be_forced_offpeak` symbol cited and verified in the review         |
| Duration handling and current default       | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py), duration behavior cited and verified in the review                   |
| Power configuration                         | [config_schema.py](../../custom_components/solar_optimizer/config_schema.py), current absence of an off-peak option cited and verified in the review |
| Current version                             | [manifest.json](../../custom_components/solar_optimizer/manifest.json), version `3.8.4`                                                              |
| Documentation headers to update at delivery | [README-fr.md](../../README-fr.md) and [README.md](../../README.md)                                                                                  |