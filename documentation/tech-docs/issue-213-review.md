# Revue de l’issue #213 et de la PR #214

## Références

- Issue : [#213 — on_time counter is inverted when check_active_template depends on a sensor updated after the switch](https://github.com/jmcollin78/solar_optimizer/issues/213)
- Pull request associée : [#214 — Fix on_time counter inverted when check_active_template depends on a lagging sensor](https://github.com/jmcollin78/solar_optimizer/pull/214)
- État consulté : issue et PR ouvertes, sans label, assigné, revue ni contrôle CI affiché.

## Résumé fidèle

L’issue signale un défaut du capteur journalier `on_time` lorsqu’un `check_active_template` dépend d’une entité mise à jour après l’entité pilotée, par exemple un capteur de puissance après la commutation d’un contacteur.

Au changement du switch, le template reflète alors encore l’ancienne valeur. Le compteur déduit à tort une transition inverse : il mémorise une heure de début lors de l’arrêt, puis comptabilise une période d’arrêt comme une période d’activité. Après le reset quotidien, cela peut immédiatement dépasser `max_on_time_per_day_min`, empêcher toute nouvelle activation et empêcher le forçage en heures creuses.

La PR #214 remplace la détection de transitions par un échantillonnage : elle crédite l’intervalle écoulé si le périphérique était actif lors du précédent contrôle, puis démarre un nouvel intervalle seulement s’il est actuellement actif. Cet échantillonnage est exécuté sur changement d’état de l’entité sous-jacente et chaque minute. Les changements du switch sont donc traités immédiatement ; seule une variation ultérieure d’une dépendance du template, sans nouvel événement du switch, est observée au prochain passage périodique, au plus tard une minute après.

## Sources et éléments vérifiés

### Issue et PR

- L’issue fournit un scénario reproductible avec un chauffe-eau, un capteur de puissance retardé, `max_on_time_per_day_min: 180` et un reset à 06:00.
- Son auteur propose explicitement un échantillonnage de `is_active` à chaque changement de l’entité sous-jacente et chaque minute.
- Le propriétaire indique que, pour un switch classique, l’usage d’un `check_active_template` peut être évité ; cette remarque constitue un contournement, mais ne réfute pas le défaut du compteur pour les configurations existantes ou les équipements à état actif distinct.
- La PR contient deux commits et modifie deux fichiers : `sensor.py` et `test_max_on_time.py` (+143 / -32 selon GitHub). Elle déclare que la suite complète donne 89 tests passants et 11 ignorés. Cette exécution n’a pas été reproduite localement dans cette revue.

### Dépôt local

- `TodayOnTimeSensor._on_state_change` évalue actuellement `self._device.is_active` de manière synchrone dans le callback de changement de l’entité surveillée et utilise `_old_state` pour dériver les transitions. Le mécanisme correspond à la cause décrite.
- `ManagedDevice.is_active` rend le `check_active_template` ; il peut donc dépendre d’une autre entité actualisée plus tard.
- L’actualisation périodique ne crédite actuellement du temps que si `_last_datetime_on` est défini et que `is_active` est vrai. Elle ne corrige pas une heure de départ déjà inversée.
- Le test local couvre le cas nominal de mise en marche, arrêt, actualisation périodique et reset, mais pas le décalage entre switch et capteur de puissance. La PR ajoute un test de régression pour ce cas.
- La documentation indique que le template actif est facultatif lorsque l’état `on`/`off` de l’entité correspond à son activité réelle, notamment pour les switches et input booleans.

## Pertinence et recommandation

**Recommandation : retenir la correction de la PR #214, sous réserve d’une revue ciblée et de l’exécution indépendante des tests.**

Le défaut est reproductible en lecture du code actuel, touche une fonction de sécurité fonctionnelle (`max_on_time_per_day_min`) et peut rendre un équipement indisponible pendant une journée entière. Le correctif est localisé, suit la proposition de l’issue et est accompagné d’un test de régression explicitant le scénario défaillant.

## Périmètre proposé

### Inclus

- Corriger le comptage journalier de `TodayOnTimeSensor` lorsque l’évaluation de l’activité est retardée par rapport au changement de l’entité sous-jacente.
- Conserver le comportement du compteur pour les équipements dont l’activité suit immédiatement l’entité sous-jacente.
- Ajouter et maintenir le test de régression avec un capteur de puissance retardé.

### Exclus

- Modifier la sémantique générale de `check_active_template`.
- Interdire le template actif sur les switches.
- Modifier le moteur d’optimisation, les stratégies de puissance ou les seuils configurés.
- Migration de configuration ou modification de dépendances.

## Impacts et risques

| Domaine                    | Impact / risque                                                                                                                                                                                                                                              | Gravité | Probabilité                                     | Mesure proposée                                                                                 |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Fonctionnel                | Le bug actuel peut comptabiliser plusieurs heures d’arrêt comme activité et bloquer l’équipement pour la journée.                                                                                                                                            | Élevée  | Élevée pour les templates retardés              | Intégrer le correctif avec le test de régression.                                               |
| Précision du compteur      | Les changements du switch sont traités immédiatement. Un décalage, borné par l’intervalle périodique d’une minute, subsiste uniquement si une dépendance de `check_active_template` change après le switch sans provoquer de nouvel événement de ce dernier. | Faible  | Élevée pour les templates à dépendance retardée | Vérifier que cette borne est acceptable près des limites quotidiennes.                          |
| Régression                 | La nouvelle routine est appelée à la fois sur événement et périodiquement ; une double comptabilisation doit être exclue.                                                                                                                                    | Modérée | Faible à modérée                                | Exécuter les tests existants et ajouter, si nécessaire, un test sur événements très rapprochés. |
| Persistance / reset        | `last_datetime_on` est restauré et réinitialisé quotidiennement ; un état intermédiaire incohérent pourrait se propager après redémarrage.                                                                                                                   | Modérée | Faible                                          | Vérifier explicitement arrêt, reset puis redémarrage dans les tests ou en recette.              |
| Performance                | L’évaluation du template est déjà périodique ; la factorisation ne crée pas de nouvel intervalle.                                                                                                                                                            | Faible  | Faible                                          | Contrôler l’absence de travail supplémentaire non borné.                                        |
| Sécurité / confidentialité | Aucun impact identifié : modification locale de comptage, sans nouvelle entrée ni transmission de données.                                                                                                                                                   | Faible  | Faible                                          | Aucun traitement additionnel.                                                                   |
| Compatibilité              | Aucun changement de schéma ou d’API exposée identifié.                                                                                                                                                                                                       | Faible  | Faible                                          | Valider contre les versions Home Assistant prises en charge.                                    |

## Alternatives examinées

1. **Retirer `check_active_template` pour les switches concernés**
   - Avantage : contournement immédiat pour les équipements dont le switch reflète réellement l’activité.
   - Inconvénient : ne couvre ni les installations où le switch ne reflète pas l’activité physique, ni les autres domaines d’entités ; ne corrige pas la fragilité de la logique actuelle.

2. **Écouter aussi les dépendances du template**
   - Avantage : détection potentiellement plus précise que la minute.
   - Inconvénient : les dépendances de template et leur écoute sont plus complexes ; risque de couplage et de régressions supérieur. Ce n’est pas la solution proposée par la PR.

3. **Adopter l’échantillonnage périodique de la PR**
   - Avantage : correctif local, robuste vis-à-vis de l’ordre d’arrivée des événements, comportement compréhensible et testé par le scénario signalé.
   - Inconvénient : précision bornée par la fréquence de l’intervalle.

## Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses

- L’observation, au plus tard à la minute suivante, d’un changement retardé d’une dépendance de `check_active_template` est acceptable pour l’affichage de `on_time` et l’application des seuils quotidiens.
- Le template actif peut légitimement dépendre d’entités distinctes de l’entité pilotée.

### Questions ouvertes

1. La borne d’une minute, uniquement pour les changements retardés des dépendances du template, est-elle acceptable pour les cas proches de `max_on_time_per_day_min` ?
2. Faut-il compléter la documentation pour déconseiller `check_active_template` sur un switch lorsque son état suffit, tout en précisant que les templates retardés sont pris en charge ?
3. La PR doit-elle inclure un test de persistance après redémarrage, ou la couverture existante est-elle considérée suffisante ?

### Décisions nécessaires

- Valider l’adoption de l’approche d’échantillonnage de la PR plutôt qu’un suivi des dépendances des templates.
- Décider si une mise à jour documentaire fait partie de cette correction.

## Critères de passage au développement

1. Le périmètre ci-dessus est approuvé.
2. Les questions bloquantes, en particulier l’acceptabilité de la précision à une minute, reçoivent une décision.
3. Les tests existants et le nouveau test de régression sont exécutés avec succès dans l’environnement cible.
4. Une revue confirme que l’arrêt, le reset quotidien et les changements d’état rapprochés ne conduisent pas à une double comptabilisation.

## Suite proposée

Après approbation de ce rapport, produire une spécification fonctionnelle et une conception technique convergentes, puis demander une autorisation explicite avant tout développement ou intégration.

## Décision de suivi

Le demandeur ne valide pas l’ouverture des phases de spécification et de conception. Il prévoit de valider directement la PR #214. Aucune étape de développement ni modification du code n’est engagée dans le cadre de cette revue.