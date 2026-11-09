# Spécification fonctionnelle / Functional specification

## 1. Titre et métadonnées / Title and metadata

| Élément / Item                                     | Valeur / Value                                                                                                                                                                                                                                                                                                                                                                                                                |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nom / Name                                         | Issue #222 - Cohérence du compteur journalier après restauration / Daily counter consistency after restoration                                                                                                                                                                                                                                                                                                                |
| Version                                            | 1.0                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Date                                               | 2026-11-09                                                                                                                                                                                                                                                                                                                                                                                                                    |
| Propriétaire / Owner                               | Projet Solar Optimizer / Solar Optimizer project                                                                                                                                                                                                                                                                                                                                                                              |
| Statut / Status                                    | Troisième et dernier cycle documentaire clos : accord de fond acquis au deuxième, aucun désaccord fonctionnel ; version finale confirmée par les deux spécialistes ; approbation humaine des résultats en attente / Third and final documentation cycle closed: substantive agreement reached at the second cycle, no functional disagreement; final version confirmed by both specialists; human approval of results pending |
| Autorisation / Authorization                       | Revue approuvée le 2026-11-09 : « Je confirme. Go pour spec/design ». Développement non autorisé / Review approved on 2026-11-09. Development not authorized                                                                                                                                                                                                                                                                  |
| Conception / Design                                | [Conception bilingue v1.0 / Bilingual design v1.0](issue-222-design.md), lue intégralement et relue pour convergence / read in full and reviewed for convergence                                                                                                                                                                                                                                                              |
| Besoin / Need                                      | [Issue #222](https://github.com/jmcollin78/solar_optimizer/issues/222)                                                                                                                                                                                                                                                                                                                                                        |
| Source de décision / Decision source               | [Rapport approuvé / Approved review](issue-222-review.md)                                                                                                                                                                                                                                                                                                                                                                     |
| Convention documentaire / Document convention      | [Spécification voisine / Neighboring specification](issue-212-specifications.md)                                                                                                                                                                                                                                                                                                                                              |
| Sources locales analysées / Analyzed local sources | [sensor.py](../../custom_components/solar_optimizer/sensor.py), [managed_device.py](../../custom_components/solar_optimizer/managed_device.py), [coordinator.py](../../custom_components/solar_optimizer/coordinator.py), [test_min_on_time.py](../../tests/test_min_on_time.py), [test_max_on_time.py](../../tests/test_max_on_time.py) ; passages et symboles en section 10 / inspected portions and symbols in section 10  |

---

# Version française

## 2. Contexte et objectifs

Après un redémarrage, la durée quotidienne affichée peut être restaurée correctement alors que le compteur métier reste à zéro. Un appareil éteint sans intervalle de comptage en cours peut alors être forcé en heures creuses malgré un minimum atteint, ou redevenir utilisable malgré un maximum atteint.

L'objectif est de rendre la durée restaurée immédiatement opposable aux décisions métier et aux attributs initiaux. Le périmètre porte sur la fin de la restauration du capteur de durée, y compris son repli zéro, sans changer les règles de durée ni le cycle de comptage.

L'écart observé est l'absence de synchronisation à cet instant, et non une erreur démontrée de persistance. Les garanties portent sur la première publication et le premier calcul suivant la restauration terminée, pas sur tout calcul éventuellement antérieur.

## 3. Acteurs et cas d'utilisation

- **Utilisateur Home Assistant** : conserve sa configuration et redémarre Home Assistant ; aucune nouvelle action ou option n'est requise.
- **Home Assistant** : fournit l'état antérieur disponible et accueille l'état publié du capteur.
- **Solar Optimizer** : restaure la durée, expose les attributs et décide de l'utilisation ou du forçage de l'appareil.

Déroulement nominal :

1. Home Assistant ajoute le capteur de durée d'un appareil, notamment après redémarrage.
2. Le capteur retient la durée restaurable, ou le repli zéro selon les traitements existants, et restaure les attributs actuellement pris en charge.
3. Le compteur métier reçoit cette durée définitive avant le calcul des attributs initiaux et avant la publication.
4. Le premier calcul d'optimisation suivant la restauration applique les seuils existants à cette durée, et non au zéro d'initialisation.

Variantes : minimum atteint ou non atteint, maximum atteint ou non atteint, état antérieur absent ou non exploitable par le chemin actuel, appareil actif. Les résultats attendus sont détaillés en section 7.

## 4. Exigences fonctionnelles

- **FR-001** : Le système doit rendre le compteur métier égal à la durée définitive du capteur dès la fin de la restauration de la valeur et de ses attributs, avant le calcul des attributs initiaux et avant toute publication par cette fin de restauration.
- **FR-002** : Le système doit utiliser cette même durée pour les attributs initiaux, notamment la décision de forçage en heures creuses, et pour le premier calcul d'optimisation suivant la restauration terminée, sans attendre une actualisation périodique ni une transition de l'appareil.
- **FR-003** : Le système doit refuser le forçage lié au minimum journalier lorsque la durée restaurée est supérieure ou égale à ce minimum ; en dessous, il doit conserver la possibilité de forçage selon toutes les autres conditions existantes.
- **FR-004** : Le système doit rendre l'appareil inutilisable pour l'optimisation lorsque la durée restaurée est supérieure ou égale au maximum journalier ; en dessous, ce maximum ne doit pas à lui seul interdire l'utilisation.
- **FR-005** : Le système doit conserver la durée restaurée lors d'une actualisation périodique d'un appareil inactif sans intervalle en cours ; la synchronisation et cette actualisation ne doivent pas déclencher d'activation par elles-mêmes.
- **FR-006** : Le système doit synchroniser également le repli zéro déjà prévu, avec ou sans état antérieur, sans nouvelle exception pour les valeurs actuellement gérées : état absent, valeur `None`, `unknown`, `unavailable` et texte non numérique.
- **FR-007** : Le système doit préserver le comportement actuel de restauration d'un appareil actif, de comptage et de remise à zéro quotidienne, sans ajouter ni perdre de durée du seul fait de la synchronisation.

## 5. Règles métier

- **BR-001** : La référence commune doit être la valeur définitive retenue par le capteur, exprimée en secondes, après la conversion et l'arrondi existants ; la synchronisation doit remplacer le compteur métier, non lui ajouter cette valeur.
- **BR-002** : Le minimum doit rester une condition stricte de forçage : durée inférieure au minimum. L'égalité doit exclure ce forçage ; elle ne doit pas interdire une activation légitime issue de l'optimisation normale.
- **BR-003** : Le maximum journalier doit rester une interdiction inclusive : durée supérieure ou égale au maximum. Cette interdiction doit prévaloir sur une éventuelle insuffisance au regard du minimum. En dessous du maximum, les autres restrictions doivent rester applicables.
- **BR-004** : Un minimum non atteint ne doit pas suffire à autoriser le forçage : la plage d'heures creuses, l'utilisabilité contrôlée par le chemin existant et le plafond des heures creuses doivent rester applicables, sans modification de leur traitement actuel. La correction ne doit commander directement aucun appareil.

## 6. Contraintes fonctionnelles

- La configuration, les unités, les seuils, les temporisations, la définition des heures creuses et le format persistant doivent rester compatibles sans migration ni intervention utilisateur.
- La décision validée impose la synchronisation au point de restauration, après la valeur et ses attributs, avant `update_custom_attributes()` puis `async_write_ha_state()`, y compris hors de la branche `if old_state`. Le setter existant `ManagedDevice.set_on_time` est le point d'affectation retenu par la revue ; ce repère ne prescrit aucune refonte.
- La cohérence initiale exigée ne doit pas être interprétée comme une réorganisation des publications périodiques ou de la remise à zéro.
- Aucun nouvel accès, secret, flux de données, droit, service, API ou dépendance ne doit être introduit. Aucune contrainte réglementaire supplémentaire n'est établie par les sources.
- Aucune disponibilité globale avant la fin de restauration ni absence de concurrence au démarrage n'est démontrée. Un verrou de démarrage n'est pas autorisé dans ce périmètre.

## 7. Critères d'acceptation

**Statut : critères et recettes futurs, non exécutés dans cette phase documentaire.** Les contrôles de décision doivent isoler les seuils en rendant les autres conditions favorables, sauf indication contraire. Les valeurs sont en secondes, dans un même cycle de comptage sans remise à zéro intermédiaire.

| Identifiant | Scénario et résultat vérifiable                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001      | Étant donné un appareil éteint sans `last_datetime_on` et une durée restaurable non nulle, vérifier à l'entrée du calcul des attributs initiaux, puis à la publication, que le compteur métier est égal à la valeur définitive du capteur. Ne déclencher aucune actualisation pour obtenir cette égalité.                                                                                                                                                                                                                              |
| AC-002      | À 02:03, avec début des heures creuses à 02:00, remise à zéro à 05:00 et minimum de 7 200 s, restaurer séparément 24 600, 7 800 et 7 200 s. Le forçage doit être faux dès les attributs initiaux et rester faux au premier calcul après restauration. Les plafonds doivent être non bloquants pour isoler le minimum.                                                                                                                                                                                                                  |
| AC-003      | Dans les mêmes conditions favorables, restaurer 7 140 s pour un minimum de 7 200 s : le forçage doit être vrai. Vérifier aussi qu'une condition existante défavorable, par exemple hors plage d'heures creuses, continue de le bloquer malgré ce minimum non atteint.                                                                                                                                                                                                                                                                  |
| AC-004      | Pour un maximum journalier de 7 200 s et un minimum non bloquant, restaurer séparément 7 140, 7 200 et 7 800 s : `check_usable(False)` doit retourner respectivement vrai, faux et faux lorsque les autres conditions autorisent l'utilisation. À égalité et au-dessus, la décision d'utilisabilité employée par l'optimisation doit respecter ce plafond.                                                                                                                                                                             |
| AC-005      | Après restauration d'une durée non nulle sur appareil éteint sans `last_datetime_on`, déclencher l'actualisation périodique : le capteur et le compteur métier doivent conserver cette durée ; aucun appel d'activation ne doit en résulter.                                                                                                                                                                                                                                                                                           |
| AC-006      | Tester séparément l'absence d'ancien état et un ancien état de valeur `None`, `unknown`, `unavailable` ou texte non numérique, sans attribut de date malformé. Avant attributs et publication, les deux compteurs doivent être à zéro ; ces entrées ne doivent pas introduire de nouvelle exception.                                                                                                                                                                                                                                   |
| AC-007      | Après restauration, vérifier ensemble la valeur publiée, l'attribut initial `should_be_forced_offpeak` et le premier calcul d'optimisation. Pour 7 800 s restaurées, minimum 7 200 s, appareil inactif et solution normale ne demandant pas l'allumage, aucune activation de forçage ne doit être appelée. Pour 7 140 s et toutes les conditions favorables, le chemin normal de forçage doit rester possible.                                                                                                                         |
| AC-008      | Restaurer une durée valide et un `last_datetime_on` valide sur appareil actif : la synchronisation doit reprendre la durée sans ajout ni modification de l'horodatage. À l'actualisation suivante, l'intervalle doit être compté selon le comportement actuel, une seule fois ; une répétition au même instant ne doit pas l'ajouter de nouveau. Déclencher ensuite la remise à zéro quotidienne et vérifier les compteurs à zéro et la poursuite du comptage selon le comportement actuel, sans durée ajoutée par la synchronisation. |
| AC-009      | Lors d'un développement ultérieurement autorisé, ajouter des tests persistants de restauration dans les modules existants appropriés couvrant AC-001 à AC-008 et maintenir verts les 16 cas ciblés cités dans le rapport. La reproduction isolée ne doit pas remplacer cette couverture.                                                                                                                                                                                                                                               |

La recette complémentaire proposée consiste à redémarrer un environnement Home Assistant de test avec durée persistée connue et à observer le premier état puis le premier calcul après restauration. Elle complète les tests ciblés sans constituer un préalable physique bloquant au correctif local ; son responsable, son environnement et sa planification restent à convenir avant son exécution, après autorisation. Elle n'est ni exécutée ni autorisée par la présente tâche documentaire et n'impose aucune commande physique. Un allumage physique et la durée exacte des occurrences rapportées ne sont pas certifiés.

## 8. Fonctions non prises en compte

- Modification de l'algorithme d'optimisation, des services, de leurs priorités générales, des temporisations ou de la définition des heures creuses : aucune modification nécessaire au diagnostic retenu.
- Nouveau stockage, persistance indépendante, migration, API, verrou de démarrage, configuration, traduction, frontend ou dépendance : extension disproportionnée et non autorisée.
- Nouvelle validation ou normalisation de `NaN`, de l'infini, des valeurs négatives ou des dates malformées : aucune nouvelle politique décidée ; ne pas assimiler ces cas au repli zéro déjà géré.
- Reconstitution du temps pendant l'arrêt et remise à zéro manquée pendant cet arrêt : politiques temporelles distinctes, explicitement exclues. La préservation du comptage existant ne vaut pas validation de ces politiques.
- Garantie sur les calculs précédant la fin de restauration et réorganisation générale des attributs périodiques : non démontrées et hors périmètre.
- Développement, ajout de tests et lancement Home Assistant dans cette phase : non autorisés. Les mises à jour documentaires de suivi, notamment du rapport pour consigner la validation et la convergence, sont autorisées à l'orchestrateur et ne valent pas autorisation de développement.

## 9. Évolutions futures proposées

- Analyser séparément le temps pendant l'arrêt et la remise à zéro manquée si un besoin utilisateur est confirmé ; décider d'abord la durée attendue et les cas limites.
- Étudier séparément la politique des valeurs atypiques ou des dates invalides si nécessaire ; aucune normalisation implicite n'est retenue ici.
- Si la recette révèle une décision avant la fin de restauration, soumettre le besoin de garantie de démarrage à convergence et approbation explicite avant toute extension, notamment un verrou.

Ces possibilités ne sont pas des exigences actuelles ni des conditions cachées de livraison du correctif restreint.

## 10. Hypothèses, questions ouvertes et traçabilité

### Faits et preuves

- Lecture locale : `ManagedDevice.__init__` initialise `_on_time_sec` à zéro ; `TodayOnTimeSensor.async_added_to_hass` restaure la valeur et l'horodatage sans appeler le setter ; `_refresh_on_time` retourne immédiatement si l'appareil est inactif sans horodatage. `set_on_time` est une affectation sans commande.
- Lecture locale : `check_usable` interdit l'utilisation à partir du maximum ; `should_be_forced_offpeak` exige notamment une durée strictement inférieure au minimum. `update_custom_attributes` lit cette décision. Le traitement de la meilleure solution dans le coordinateur peut allumer l'appareil sur cette décision même sans demande d'allumage de la solution normale.
- Lecture locale : le test `test_nominal_use_min_on_time_exceeded` vérifie un minimum dépassé sans restauration non nulle ; les passages de comptage de [test_max_on_time.py](../../tests/test_max_on_time.py) vérifient notamment 13 s puis 68 s, une remise à zéro et 12 minutes comptées ensuite. Ils ne constituent pas une recette de redémarrage.
- **Preuves exécutées avant ce tour, consignées dans le rapport, non réexécutées ici** : 16 tests ciblés réussis ; reproduction isolée avec méthodes réelles et entrées/sorties simulées. Pour le minimum 7 200 s, 24 600, 7 800 et 7 200 s passent d'un forçage vrai avant setter à faux après ; 7 140 s reste vrai. La décision maximum a également été reproduite. Aucun test persistant n'a été ajouté et aucun redémarrage Home Assistant réel n'a été validé.

### Hypothèses retenues

- Le scénario principal reste dans le même cycle de comptage, sans heure de remise à zéro manquée ; les durées numériques des scénarios sont valides et les dates utilisées sont bien formées.
- Les conditions autres que celle isolée sont favorables ; l'absence de forçage ne signifie pas l'interdiction de toute activation légitime.
- La garantie du premier calcul commence après la fin de restauration ; aucune hypothèse de verrouillage global n'est ajoutée.

### Décisions et questions ouvertes

- Décisions reprises du rapport : synchronisation au point de restauration, traitement du repli zéro, couverture du maximum et conservation des règles existantes. Aucune divergence fonctionnelle ni contradiction bloquante connue pour ce périmètre.
- **Relecture effectuée :** après la relecture croisée du deuxième passage, le rédacteur a relu intégralement les spécifications et la [conception bilingue v1.0 actuelle](issue-222-design.md). Au troisième et dernier cycle, les deux spécialistes ont confirmé la version finale après correction des seules mentions documentaires de suivi ; aucune exigence, règle métier, aucun critère d'acceptation, aucune solution ni aucun test n'est modifié. Les confirmations du concepteur sur cette version ont été reçues et sont consignées ici par l'orchestrateur.
- **Même périmètre :** confirmé par les deux spécialistes au deuxième cycle et reconfirmé par le rédacteur pour cette version au troisième : synchronisation après restauration, avant attributs initiaux et publication, sans verrou ni garantie avant restauration ; maintien du comptage actif, de la RAZ et du traitement des entrées déjà gérées.
- **Couverture complète :** confirmée par les deux spécialistes au deuxième cycle et reconfirmée par le rédacteur pour cette version au troisième : FR-001 à FR-007, BR-001 à BR-004 et AC-001 à AC-009, correspondant aux neuf critères du rapport ; la conception les relie aux vérifications futures T-01 à T-09.
- **Absence de contradiction bloquante :** les deux spécialistes n'en ont relevé aucune au deuxième cycle entre les spécifications, la conception et le périmètre du rapport approuvé ; le rédacteur reconfirme ce constat pour cette version au troisième cycle. Les corrections de suivi n'introduisent aucun désaccord fonctionnel.
- **Faisabilité et testabilité :** confirmées par les deux spécialistes au deuxième cycle et reconfirmées par le rédacteur pour cette version au troisième : solution techniquement réalisable et testable sur les chemins locaux examinés, avec le setter existant et les observations prévues par la conception. Les tests persistants restent futurs ; les 16 cas réussis et la reproduction isolée restent des preuves antérieures, sans nouvelle preuve d'exécution ni de redémarrage HA réel.
- Le responsable, l'environnement et la planification de la recette de redémarrage complémentaire restent à convenir avant son exécution autorisée ; cette question n'est pas bloquante pour la convergence ni un préalable physique indispensable au correctif local. Aucune preuve de bout en bout n'est disponible ici.
- Toute nécessité apparente d'une garantie avant restauration, d'une nouvelle validation de données ou d'une politique temporelle doit devenir une question de convergence, non une exigence implicite.
- L'accord de fond et la convergence des deux spécialistes sont acquis au deuxième cycle. Le troisième et dernier cycle de clôture documentaire est terminé, sans désaccord fonctionnel : le rédacteur et le concepteur ont explicitement confirmé sur la version finale le même périmètre, la couverture complète, l'absence de contradiction bloquante et la faisabilité/testabilité. L'approbation humaine des résultats et une nouvelle autorisation humaine explicite restent nécessaires avant développement ; le développement n'est toujours pas autorisé.

### Traçabilité des neuf critères du rapport

Les numéros de la première colonne renvoient à la section « Critères d'acceptation proposés » du [rapport approuvé](issue-222-review.md). Les repères de code sont des sources vérifiées, non une prescription de refonte.

| Critère du rapport | Exigences / règles                         | Critère de ce document | Sources vérifiées                                                                                                                                                                                                                              |
| ------------------ | ------------------------------------------ | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1                  | FR-001, BR-001                             | AC-001                 | [sensor.py](../../custom_components/solar_optimizer/sensor.py) : `TodayOnTimeSensor.async_added_to_hass` ; [managed_device.py](../../custom_components/solar_optimizer/managed_device.py) : `set_on_time`                                      |
| 2                  | FR-003, BR-002                             | AC-002                 | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py) : `should_be_forced_offpeak`                                                                                                                                    |
| 3                  | FR-003, BR-004                             | AC-003                 | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py) : `should_be_forced_offpeak`, `check_usable`                                                                                                                    |
| 4                  | FR-004, BR-003                             | AC-004                 | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py) : `check_usable`                                                                                                                                                |
| 5                  | FR-005                                     | AC-005                 | [sensor.py](../../custom_components/solar_optimizer/sensor.py) : `_refresh_on_time`, `_on_update_on_time`                                                                                                                                      |
| 6                  | FR-006, BR-001                             | AC-006                 | [sensor.py](../../custom_components/solar_optimizer/sensor.py) : `async_added_to_hass`                                                                                                                                                         |
| 7                  | FR-002                                     | AC-007                 | [sensor.py](../../custom_components/solar_optimizer/sensor.py) : `update_custom_attributes` ; [coordinator.py](../../custom_components/solar_optimizer/coordinator.py) : branche `should_force_offpeak` du traitement de la meilleure solution |
| 8                  | FR-007, BR-001                             | AC-008                 | [sensor.py](../../custom_components/solar_optimizer/sensor.py) : restauration, `_refresh_on_time`, `_on_midnight` ; [test_max_on_time.py](../../tests/test_max_on_time.py) : comptage et remise à zéro                                         |
| 9                  | FR-001 à FR-007 ; exigence de vérification | AC-009                 | [test_min_on_time.py](../../tests/test_min_on_time.py), [test_max_on_time.py](../../tests/test_max_on_time.py) ; résultats antérieurs dans le rapport                                                                                          |

---

# English version

## 2. Context and objectives

After a restart, the displayed daily duration may be restored correctly while the business counter remains zero. An inactive device with no ongoing counting interval may then be forced during off-peak hours despite having met its minimum, or become usable again despite having reached its maximum.

The objective is to make the restored duration immediately effective for business decisions and initial attributes. The scope covers the end of duration-sensor restoration, including its zero fallback, without changing duration rules or the counting cycle.

The observed gap is missing synchronization at that point, not a demonstrated persistence error. Guarantees cover the first publication and the first calculation after completed restoration, not any calculation that might occur beforehand.

## 3. Actors and use cases

- **Home Assistant user**: keeps the existing configuration and restarts Home Assistant; no new action or option is required.
- **Home Assistant**: supplies the available previous state and receives the published sensor state.
- **Solar Optimizer**: restores duration, exposes attributes and decides whether to use or force the device.

Nominal flow:

1. Home Assistant adds a device's duration sensor, notably after a restart.
2. The sensor retains the restorable duration, or the zero fallback according to existing handling, and restores the attributes currently supported.
3. The business counter receives this final duration before initial attributes are calculated and before publication.
4. The first optimization calculation after restoration applies existing thresholds to this duration rather than the initialization zero.

Variants: minimum met or unmet, maximum reached or not reached, previous state missing or unusable through the current path, active device. Expected outcomes are detailed in section 7.

## 4. Functional requirements

- **FR-001**: The system shall make the business counter equal to the sensor's final duration as soon as restoration of the value and its attributes completes, before calculating initial attributes and before any publication performed by this restoration completion.
- **FR-002**: The system shall use this same duration for initial attributes, including the off-peak forcing decision, and for the first optimization calculation after completed restoration, without waiting for a periodic refresh or a device transition.
- **FR-003**: The system shall reject forcing related to the daily minimum when restored duration is greater than or equal to that minimum; below it, the system shall preserve the possibility of forcing subject to all other existing conditions.
- **FR-004**: The system shall make the device unusable for optimization when restored duration is greater than or equal to the daily maximum; below it, this maximum alone shall not prevent use.
- **FR-005**: The system shall retain restored duration during a periodic refresh of an inactive device with no ongoing interval; synchronization and this refresh shall not themselves trigger activation.
- **FR-006**: The system shall also synchronize the existing zero fallback, with or without a previous state, without introducing a new exception for currently handled values: missing state, `None` value, `unknown`, `unavailable` and non-numeric text.
- **FR-007**: The system shall preserve current active-device restoration, counting and daily-reset behavior, without adding or losing duration solely because of synchronization.

## 5. Business rules

- **BR-001**: The shared reference shall be the final value retained by the sensor, expressed in seconds, after existing conversion and rounding; synchronization shall replace the business counter rather than add this value to it.
- **BR-002**: The minimum shall remain a strict forcing condition: duration below the minimum. Equality shall exclude this forcing; it shall not prohibit legitimate activation resulting from normal optimization.
- **BR-003**: The daily maximum shall remain an inclusive prohibition: duration greater than or equal to the maximum. This prohibition shall take precedence over a possible shortfall against the minimum. Below the maximum, other restrictions shall remain applicable.
- **BR-004**: An unmet minimum alone shall not authorize forcing: the off-peak window, usability checked by the existing path and the off-peak cap shall remain applicable, with their current handling unchanged. The correction shall not directly command any device.

## 6. Functional constraints

- Configuration, units, thresholds, timing constraints, off-peak definitions and the persisted format shall remain compatible without migration or user intervention.
- The approved decision requires synchronization at restoration, after the value and its attributes, before `update_custom_attributes()` followed by `async_write_ha_state()`, including outside the `if old_state` branch. The existing `ManagedDevice.set_on_time` setter is the assignment point retained by the review; this reference prescribes no redesign.
- Required initial consistency shall not be interpreted as reorganizing periodic or daily-reset publications.
- No new access, secret, data flow, permission, service, API or dependency shall be introduced. No additional regulatory constraint is established by the sources.
- Neither global availability before completed restoration nor absence of startup concurrency has been demonstrated. A startup lock is not authorized within this scope.

## 7. Acceptance criteria

**Status: future criteria and acceptance checks, not executed in this documentation phase.** Decision checks shall isolate thresholds by making other conditions favorable unless otherwise stated. Values are in seconds, within one counting cycle without an intervening reset.

| Identifier | Scenario and verifiable outcome                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001     | Given an inactive device without `last_datetime_on` and a nonzero restorable duration, verify on entry to initial-attribute calculation, then at publication, that the business counter equals the sensor's final value. Do not trigger a refresh to obtain this equality.                                                                                                                                                                                                 |
| AC-002     | At 02:03, with off-peak hours starting at 02:00, reset at 05:00 and minimum 7,200 s, separately restore 24,600, 7,800 and 7,200 s. Forcing shall be false from initial attributes onward and remain false at the first calculation after restoration. Caps shall be non-blocking to isolate the minimum.                                                                                                                                                                   |
| AC-003     | Under the same favorable conditions, restore 7,140 s against a 7,200 s minimum: forcing shall be true. Also verify that an unfavorable existing condition, such as being outside the off-peak window, still blocks forcing despite this unmet minimum.                                                                                                                                                                                                                     |
| AC-004     | For a daily maximum of 7,200 s and a non-blocking minimum, separately restore 7,140, 7,200 and 7,800 s: `check_usable(False)` shall return true, false and false respectively when other conditions allow use. At equality and above, the usability decision used by optimization shall respect this cap.                                                                                                                                                                  |
| AC-005     | After restoring a nonzero duration on an inactive device without `last_datetime_on`, trigger the periodic refresh: sensor and business counter shall retain that duration; no activation call shall result.                                                                                                                                                                                                                                                                |
| AC-006     | Separately test no previous state and a previous state whose value is `None`, `unknown`, `unavailable` or non-numeric text, without a malformed date attribute. Before attributes and publication, both counters shall be zero; these inputs shall not introduce a new exception.                                                                                                                                                                                          |
| AC-007     | After restoration, jointly verify the published value, initial `should_be_forced_offpeak` attribute and first optimization calculation. For 7,800 s restored, minimum 7,200 s, an inactive device and a normal solution not requesting activation, no forced activation shall be called. For 7,140 s and all favorable conditions, the normal forcing path shall remain possible.                                                                                          |
| AC-008     | Restore a valid duration and valid `last_datetime_on` on an active device: synchronization shall retain the duration without addition or timestamp modification. At the next refresh, the interval shall be counted according to current behavior, once only; repeating at the same instant shall not add it again. Then trigger the daily reset and verify zero counters and continued counting according to current behavior, without duration added by synchronization. |
| AC-009     | During subsequently authorized development, add persistent restoration tests in appropriate existing modules covering AC-001 through AC-008 and keep the 16 focused cases cited in the review passing. The isolated reproduction shall not replace this coverage.                                                                                                                                                                                                          |

The proposed supplementary acceptance check is to restart a Home Assistant test environment with a known persisted duration and observe the first state and first calculation after restoration. It complements focused tests without constituting a blocking physical prerequisite for the local fix; its owner, environment and scheduling remain to be agreed before execution, following authorization. It is neither executed nor authorized by this documentation task and requires no physical command. Physical activation and the exact duration of reported occurrences are not certified.

## 8. Out of scope

- Changes to the optimization algorithm, services, their general priorities, timing constraints or off-peak definitions: not needed for the retained diagnosis.
- New storage, independent persistence, migration, API, startup lock, configuration, translations, frontend or dependency: disproportionate and unauthorized extension.
- New validation or normalization of `NaN`, infinity, negative values or malformed dates: no new policy decided; these cases shall not be equated with the already handled zero fallback.
- Reconstruction of activity during downtime and a reset missed during downtime: distinct temporal policies, explicitly excluded. Preserving existing counting does not validate these policies.
- Guarantees for calculations before completed restoration and general reorganization of periodic attributes: not demonstrated and outside scope.
- Development, adding tests and starting Home Assistant in this phase: not authorized. Documentary follow-up updates, including review updates recording validation and convergence, are authorized for the orchestrator and do not authorize development.

## 9. Proposed future enhancements

- Separately analyze activity during downtime and missed resets if a user need is confirmed; first decide expected duration and boundary cases.
- Separately assess policies for atypical values or invalid dates if needed; no implicit normalization is retained here.
- If acceptance checks reveal a decision before completed restoration, submit the startup-guarantee need for convergence and explicit approval before any extension, particularly a lock.

These possibilities are neither current requirements nor hidden delivery conditions for the limited correction.

## 10. Assumptions, open questions and traceability

### Facts and evidence

- Local inspection: `ManagedDevice.__init__` initializes `_on_time_sec` to zero; `TodayOnTimeSensor.async_added_to_hass` restores value and timestamp without calling the setter; `_refresh_on_time` returns immediately for an inactive device without a timestamp. `set_on_time` is an assignment without a command.
- Local inspection: `check_usable` prohibits use at or above the maximum; `should_be_forced_offpeak` requires, among other conditions, duration strictly below the minimum. `update_custom_attributes` reads this decision. Best-solution processing in the coordinator can activate the device on this decision even without an activation request from the normal solution.
- Local inspection: `test_nominal_use_min_on_time_exceeded` checks an exceeded minimum without nonzero restoration; counting portions of [test_max_on_time.py](../../tests/test_max_on_time.py) check notably 13 s then 68 s, a reset and 12 minutes counted afterward. They are not restart acceptance checks.
- **Evidence executed before this turn, recorded in the review, not rerun here**: 16 focused tests passed; isolated reproduction with real methods and simulated inputs/outputs. Against minimum 7,200 s, 24,600, 7,800 and 7,200 s change from forcing true before the setter to false afterward; 7,140 s remains true. The maximum decision was also reproduced. No persistent test was added and no real Home Assistant restart was validated.

### Retained assumptions

- The main scenario stays within one counting cycle with no missed reset; numeric scenario durations are valid and dates used are well formed.
- Conditions other than the isolated one are favorable; no forcing does not mean all legitimate activation is prohibited.
- The first-calculation guarantee starts after completed restoration; no global-locking assumption is added.

### Decisions and open questions

- Decisions retained from the review: synchronization at restoration, zero-fallback handling, maximum coverage and preservation of existing rules. No known functional divergence or blocking contradiction for this scope.
- **Review completed:** following the second-pass cross-review, the specification author reread the specifications and the [current bilingual design v1.0](issue-222-design.md) in full. At the third and final cycle, both specialists confirmed the final version after correcting documentary follow-up statements only; no requirement, business rule, acceptance criterion, solution or test is changed. The designer's confirmations for this version have been received and are recorded here by the orchestrator.
- **Same scope:** confirmed by both specialists at the second cycle and reconfirmed by the specification author for this version at the third: synchronization after restoration, before initial attributes and publication, without a lock or pre-restoration guarantee; preservation of active counting, daily reset and handling of already supported inputs.
- **Complete coverage:** confirmed by both specialists at the second cycle and reconfirmed by the specification author for this version at the third: FR-001 through FR-007, BR-001 through BR-004 and AC-001 through AC-009, corresponding to all nine review criteria; the design maps them to future checks T-01 through T-09.
- **No blocking contradiction:** both specialists identified none at the second cycle between the specifications, design and approved review scope; the specification author reconfirms this finding for this version at the third cycle. Follow-up corrections introduce no functional disagreement.
- **Feasibility and testability:** confirmed by both specialists at the second cycle and reconfirmed by the specification author for this version at the third: a technically feasible and testable solution on the inspected local paths, using the existing setter and the observations planned in the design. Persistent tests remain future work; the 16 passing cases and isolated reproduction remain prior evidence, without new execution evidence or a real HA restart.
- Ownership, environment and scheduling of the supplementary restart acceptance check remain to be agreed before its authorized execution; this question neither blocks convergence nor constitutes an indispensable physical prerequisite for the local fix. No end-to-end evidence is available here.
- Any apparent need for a pre-restoration guarantee, new data validation or a temporal policy shall become a convergence question, not an implicit requirement.
- Substantive agreement and convergence between both specialists were reached at the second cycle. The third and final documentation closure cycle is complete, with no functional disagreement: the specification author and designer explicitly confirmed the same scope, complete coverage, absence of blocking contradiction and feasibility/testability on the final version. Human approval of results and a new explicit human authorization are still required before development; development remains unauthorized.

### Traceability to the review's nine criteria

Numbers in the first column refer to the approved [review](issue-222-review.md), section “Critères d'acceptation proposés”. Code references are verified sources, not redesign prescriptions.

| Review criterion | Requirements / rules                            | Document criterion | Verified sources                                                                                                                                                                                                                |
| ---------------- | ----------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1                | FR-001, BR-001                                  | AC-001             | [sensor.py](../../custom_components/solar_optimizer/sensor.py): `TodayOnTimeSensor.async_added_to_hass`; [managed_device.py](../../custom_components/solar_optimizer/managed_device.py): `set_on_time`                          |
| 2                | FR-003, BR-002                                  | AC-002             | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py): `should_be_forced_offpeak`                                                                                                                      |
| 3                | FR-003, BR-004                                  | AC-003             | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py): `should_be_forced_offpeak`, `check_usable`                                                                                                      |
| 4                | FR-004, BR-003                                  | AC-004             | [managed_device.py](../../custom_components/solar_optimizer/managed_device.py): `check_usable`                                                                                                                                  |
| 5                | FR-005                                          | AC-005             | [sensor.py](../../custom_components/solar_optimizer/sensor.py): `_refresh_on_time`, `_on_update_on_time`                                                                                                                        |
| 6                | FR-006, BR-001                                  | AC-006             | [sensor.py](../../custom_components/solar_optimizer/sensor.py): `async_added_to_hass`                                                                                                                                           |
| 7                | FR-002                                          | AC-007             | [sensor.py](../../custom_components/solar_optimizer/sensor.py): `update_custom_attributes`; [coordinator.py](../../custom_components/solar_optimizer/coordinator.py): `should_force_offpeak` branch in best-solution processing |
| 8                | FR-007, BR-001                                  | AC-008             | [sensor.py](../../custom_components/solar_optimizer/sensor.py): restoration, `_refresh_on_time`, `_on_midnight`; [test_max_on_time.py](../../tests/test_max_on_time.py): counting and reset                                     |
| 9                | FR-001 through FR-007; verification requirement | AC-009             | [test_min_on_time.py](../../tests/test_min_on_time.py), [test_max_on_time.py](../../tests/test_max_on_time.py); prior results in the review                                                                                     |