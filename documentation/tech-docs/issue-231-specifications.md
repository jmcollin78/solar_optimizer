# Spécifications fonctionnelles — Issue #231 : puissance modifiée pendant les heures creuses

## Métadonnées

| Champ             | Valeur                                                                                                                                                                                                                                                                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Référence         | Issue [#231](https://github.com/jmcollin78/solar_optimizer/issues/231)                                                                                                                                                                                                                                                                                      |
| Date              | 2026-11-21                                                                                                                                                                                                                                                                                                                                                  |
| Statut            | Brouillon — en attente d'approbation (aucune phase de développement autorisée)                                                                                                                                                                                                                                                                              |
| Langue principale | Français                                                                                                                                                                                                                                                                                                                                                    |
| Rédacteur         | Agent de spécifications (mode FR/EN)                                                                                                                                                                                                                                                                                                                        |
| Sources analysées | `documentation/tech-docs/issue-231-review.md`, `custom_components/solar_optimizer/managed_device.py`, `custom_components/solar_optimizer/coordinator.py`, `custom_components/solar_optimizer/simulated_annealing_algo.py`, `custom_components/solar_optimizer/config_schema.py`, `custom_components/solar_optimizer/const.py`, `tests/test_power_device.py` |

> **Avertissement de périmètre** : ce document décrit le **contrat fonctionnel attendu**. Il ne présuppose ni ne démontre que la cause de l'incident #231 est une de celles listées dans la revue (H1/H2/H3). L'attribution de la cause au signalement réel reste suspendue aux informations manquant (version, configuration, journaux). Les règles ci-dessous s'appliquent **quel que soit** le chemin de code qui, dans la version en production, a produit la variation de puissance rapportée.

---

## 1. Contexte et objectifs

### 1.1 Problème

Pendant une plage d'heures creuses (offpeak), un utilisateur observe qu'un appareil à puissance variable (type `power`) voit sa puissance appliquée chuter de la valeur configurée (`offpeak_power`, équivalente à 15 A dans le signalement) vers la puissance minimale (`power_min`), de manière répétée. L'objectif est de garantir que, pendant les heures creuses, la puissance effectivement appliquée à un appareil variable **en fonctionnement** est strictement constante et égale à la consigne de heures creuses, conformément à la règle métier précisée par l'utilisateur.

### 1.2 Valeur attendue

- Prévisibilité de l'énergie délivrée pendant la plage d'heures creuses (pas de variation parasite vers le minimum).
- Respect explicite de la règle : « En offpeak et sur un device typé `power`, la puissance utilisée doit être `offpeak_power` et ne doit pas varier. »
- Presque pas de régression sur les appareils à puissance fixe, les commandes manuelles et les autres mécanismes de gestion.

### 1.3 Périmètre fonctionnel

Le périmètre porte sur **la période d'heures creuses** (entre `offpeak_time` et `raz_time`, éventuellement enroulant), **et pas uniquement** sur les cycles où la décision de forçage est vraie. Il couvre :

- La sélection de la consigne de puissance pour un appareil variable en fonctionnement pendant la période.
- La constance de cette consigne d'un cycle à l'autre.
- Les interactions avec les limites de durée, les temporisations de disponible, l'activation/arrêt et la transition hors offpeak.
- Le traitement de `offpeak_power` absent (repli sur `power_max`) ou dynamique (gabarit).

### 1.4 Hors périmètre

Les éléments suivants sont explicitement **exclus** de ce périmètre et de leurs justifications connues :

- Refonte générale de l'optimiseur (algorithme de recuit simulé, objectifs multi-appareils) : seule l'interaction avec la nouvelle règle est à garantir, sans autorisation de refondre l'algorithme.
- Résolution de l'issue #230 (calcul de puissance disponible / bilan de puissance).
- Modification du compteur journalier d'heures (durée allumée cumulée) ou des règles de remise à zéro au `raz_time`.
- Ajout d'une commande matérielle ou modification de l'installation Home Assistant de l'utilisateur.
- Attribution définitive de la cause de l'incident #231 (dépend des données manquantes).

> L'analyse de l'interaction entre la nouvelle règle et l'optimiseur reste nécessaire pour éviter une régression ; cela ne constitue pas une autorisation de refondre l'algorithme.

---

## 2. Acteurs et cas d'utilisation

| Acteur                                  | Description                                                                                                                            |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Utilisateur / propriétaire              | Configure la période d'heures creuses et la consigne `offpeak_power` ; s'attend à ce que la puissance soit constante pendant la plage. |
| Solar Optimizer (système)               | Calcule une solution d'optimisation puis détermine la puissance à appliquer par appareil à chaque cycle.                               |
| Appareil géré (type `power`)            | Entité à puissance variable pilotée par un service de changement de puissance.                                                         |
| Appareil géré (type `switch`)           | Entité à puissance fixe, non concernée par la variation de puissance.                                                                  |
| Utilisateur / une automatisation tierce | Peut commander manuellement l'appareil (surcharge manuelle) ou, dans l'incident, modifier la puissance en externe.                     |

### 2.1 Cas d'utilisation — Consigne HC constante sur appareil variable actif

- **Préconditions** : l'appareil est de type `power`, activé ; une plage d'heures creuses est configurée (`offpeak_time`) et atteinte ; `offpeak_power` est configuré (ou le repli s'applique) et valide. L'appareil est en fonctionnement (active).
- **Déclencheur** : chaque cycle de calcul du coordinateur pendant la plage.
- **Déroulement nominal** : à chaque cycle, la consigne appliquée à l'appareil est `offpeak_power` ; aucune variation vers `power_min` ni autre valeur n'a lieu du seul fait de l'algorithme.
- **Résultat attendu** : l'appareil reste à `offpeak_power` ; l'énergie délivrée sur la plage correspond à cette puissance constante, sur l'intervalle où l'appareil est actif.

### 2.2 Cas d'utilisation — Arrêt pendant la plage

- **Préconditions** : mêmes que 2.1.
- **Déclencheur** : une limitation de durée (par ex. `max_on_time_per_day_min` ou `max_on_time_offpeak_min`) est atteinte, ou l'appareil cesse d'être utilisable.
- **Résultat attendu** : l'appareil peut être arrêté et n'est pas maintenu allumé pendant toute la plage. La consigne `offpeak_power` ne s'applique **que** lorsque l'appareil est actif ; un appareil arrêté ne reçoit pas de consigne de puissance.

### 2.3 Cas d'utilisation — Fin de la plage offpeak

- **Préconditions** : l'appareil tourne à `offpeak_power` en fin de plage.
- **Déclencheur** : l'heure atteint `raz_time` (fin de la plage, éventuellement avec remise à zéro du compteur journalier).
- **Résultat attendu** : l'appareil redevient sous le contrôle de l'algorithme ; la consigne redevient celle de la solution d'optimisation (non plus forcée à `offpeak_power`). Ce retour est défini de manière contrôlée (voir REQ-006).

### 2.4 Cas d'utilisation — Surcharge manuelle

- **Préconditions** : pendant la plage, l'utilisateur change manuellement l'état ou la puissance de l'appareil en respectant les réglages de l'option de prise en compte des modifications manuelles.
- **Résultat attendu** : le mécanisme existant de surcharge manuelle continue de fonctionner et prend la priorité selon son contrat existant ; la règle de consigne HC constante ne doit pas la court-circuiter.

---

## 3. Exigences fonctionnelles

> Formulation impérative et vérifiable. Chaque exigence porte un identifiant stable, **identique** dans la version française et la version anglaise.

### REQ-001 — Consigne de puissance HC imposée et constante

Pendant la période d'heures creuses, pour tout appareil à puissance variable **en fonctionnement** :

Le système doit appliquer une consigne de puissance strictement égale à `offpeak_power` et **ne doit pas** laisser cette consigne varier d'un cycle à l'autre du seul fait de l'algorithme d'optimisation.

Critères d'acceptation liés : AC-001, AC-002, AC-004.

### REQ-002 — `offpeak_power` absent ou illégal : repli défini

Lorsque `offpeak_power` n'est pas configuré, le système doit utiliser le repli actuel, `power_max`, comme consigne de puissance HC. Ce repli doit satisfaire la même exigence de constance que REQ-001 pendant la plage. Une `offpeak_power` configurée mais invalide est traitée au moment de l'initialisation selon le contrat actuel (voir BR-003 et AC-012).

Critères d'acceptation liés : AC-003.

### REQ-003 — `offpeak_power` dynamique (gabarit)

Lorsque `offpeak_power` est fourni sous forme de gabarit (template) dont la valeur peut varier au fil du temps, le système doit définir de manière explicite et documentée **comment la valeur est échantillonnée** (à quelle fréquence de cycle, à quel instant) afin de rester cohérent avec l'exigence de constance de REQ-001. La valeur dynamique ne doit pas produire de variation incontrôlée au sein d'un même cycle ni de saut non justifié sans événement déclencheur.

Critères d'acceptation liés : AC-005.

> **Décision (Q-003, validée le 2026-11-21)** : la valeur du gabarit est ré-échantillonnée **une fois par cycle** du coordinateur (pas figée sur toute la plage) ; la valeur obtenue est réutilisée dans le cycle pour `activate` et `change_requested_power`, garantissant l'absence de variation intra-cycle.

### REQ-004 — Application uniquement sur appareil actif

La consigne `offpeak_power` ne s'applique **que** lorsque l'appareil est actif (en fonctionnement). Le système ne doit pas forcer l'activation de l'appareil **ni** maintenir une consigne de puissance lorsque l'appareil est arrêté, indisponible ou que sa décision d'utilisabilité est fausse.

Critères d'acceptation : AC-006.

### REQ-005 — Respect des limites et des temporisations

L'exigence de consigne constante ne dispense pas le système de respecter les durées et protections déjà configurées pour l'appareil, notamment `min_on_time_per_day_min`, `max_on_time_per_day_min`, `max_on_time_offpeak_min` et la temporisation de disponibilité de changement de puissance (`duration_power_min`). Le système doit définir explicitement, pour chaque limite, si :
- la limite peut faire cesser le fonctionnement de l'appareil **et donc** stopper l'application de la consigne HC ;
- la temporisation de puissance peut retarder ou empêcher le passage initial à `offpeak_power` en début de plage.

Critères d'acceptation : AC-007, AC-008.

### REQ-006 — Transition à la sortie de la plage offpeak

À la fin de la plage d'heures creuses (`raz_time`), le système doit remettre l'appareil variable sous le contrôle de l'algorithme d'optimisation de manière **définie et contrôlée** : la consigne redevient la solution de l'optimiseur, sans discontinuité non documentée ni commande de puissance contradictoire en double.

Critères d'acceptation : AC-009.

### REQ-007 — Non-régression des appareils à puissance fixe

Les appareils à puissance fixe (type `switch`) ne sont **pas** concernés par les exigences REQ-001 à REQ-006. Le système doit continuer de les gérer conformément à leur comportement actuel (allumage/arrêt, pas de variation de puissance).

Critères d'acceptation : AC-010.

### REQ-008 — Non-régression des mécanismes existants

Le système doit continuer de garantir le fonctionnement correct des mécanismes suivants, indépendamment des modifications apportées pour les heures creuses : commandes manuelles / surcharge manuelle, arrêt par l'utilisateur, gestion des appareils non utilisables, multi-appareils, et validation des erreurs de configuration.

Critères d'acceptation : AC-011, AC-012.

### REQ-009 — Absence de ré-émission abusive de consigne

Le système ne doit pas ré-émettre de commande de changement de puissance à `offpeak_power` à chaque cycle lorsqu'elle est déjà appliquée (état stable), afin d'éviter des changements parasites et de se conformer à l'exigence de constance. Le système doit définir une politique de comparaison entre la consigne actuellement active et la cible `offpeak_power` avant d'émettre une commande.

Critères d'acceptation : AC-013.

### REQ-010 — Diagnostic et traçabilité

Le système doit journaliser à un niveau suffisant la décision « consigne HC imposée / repli / inapplicable » et la justification (forçage, disponibilité, limite atteinte), afin de permettre la corrélation entre consignes envoyées et puissance effectivement mesurée. Ces journaux ne doivent pas exposer de donnée sensible non anonymisée.

Critères d'acceptation : AC-014.

---

## 4. Règles métier

> Identifiants `BR-00x`, identiques dans les deux versions linguistiques.

- **BR-001** : `offpeak_power` est la **seule** consigne de puissance valide pour un appareil variable en fonctionnement au cours d'une plage d'heures creuses. Toute autre valeur (notamment `power_min` ou une valeur intermédiaire) produite par l'algorithme est écartée pendant la plage.
- **BR-002** : Le forçage d'activation n'est pas un prérequis de l'application de la consigne HC, mais l'appareil actif est. C'est-à-dire : même si l'appareil n'a pas été activé par le coordinateur, s'il est actif pour une autre raison (par ex. activé manuellement ou par une automatisation tierce), la consigne HC s'applique à la puissance, tant que l'appareil est en fonctionnement.
- **BR-003** : Le repli est `power_max` lorsque `offpeak_power` est absent. La validation de `offpeak_power` impose que `power_min ≤ offpeak_power ≤ power_max` et, lorsqu'il est défini explicitement, que la distance à `power_min` soit un multiple de `power_step`. En cas de validation erronée, `ConfigurationError` doit être levé **à l'initialisation** (contrat actuel) et non à l'exécution.
- **BR-004** : Les limites `max_on_time_per_day_min`, `max_on_time_offpeak_min` et `min_on_time_per_day_min`, ainsi que la temporisation `duration_power_min`, ont **priorité absolue** sur l'application de la consigne HC pour les décisions d'activation/desactivation. En revanche, sur la valeur de puissance à appliquer tant que l'appareil est effectivement actif, la consigne HC a priorité sur la valeur intermédiaire de l'algorithme.
- **BR-005** : À la sortie de la plage offpeak (`raz_time`), le système revient au comportement « règle de l'algorithme ». Si la plage enroule au-delà de minuit (`offpeak_time >= raz_time`), la plage est considérée comme continue dans le sens horaire (de `offpeak_time` à `raz_time` via minuit), ce qui correspond au comportement actuel du système.

---

## 5. Contraintes fonctionnelles

- **Sécurité / confidentialité** : tout journal produit pour tracer la décision (voir REQ-010) doit être anonymisé ; aucun identifiant, aucun secret, aucune donnée privée non nécessaire ne doit figurer dans les journaux ou dans les extraits fournis aux diagnostics.
- **Énergie** : aucune commande réelle d'appareil physique ne doit être exécutée dans le cadre des tests de spécification (uniquement des actions simulées) ; l'analyse doit pouvoir s'appuyer sur les journaux et non sur un appareil réel.
- **Compatibilité** : le repli `offpeak_power → power_max` doit rester disponible et non casser les configurations existantes. Toute modification de contrat entre le comportement documenté pour l'issue #186 (priorité à l'algorithme) et le présent contrat doit être clairement communiquée (note de version et mise à jour de la documentation utilisateur).
- **Disponibilité** : une panne ou indisponibilité de l'entité de mesure de puissance ne doit pas bloquer la décision de consigne HC ; le repli actuel (voir `set_current_power_with_device_state`) doit être conservé, mais **peut** être complété par une décision explicite de la consigne cible (voir Q-004).

---

## 6. Critères d'acceptation

Chaque critère est observable de manière discriminante. « Simuler » signifie tester sur des entrées et actions simulées du coordinateur / de l'appareil géré, sans commande matérielle.

### AC-001 — Appareil variable actif, consigne HC configurée, plusieurs cycles

- **Préconditions** : appareil `power` actif ; `offpeak_power` configuré et valide ; plage offpeak atteinte ; forçage HC réellement vrai ou non (les deux cas doivent être testés, voir Q-001).
- **Action** : exécuter N ≥ 3 cycles de calcul du coordinateur.
- **Résultat attendu** : sur chaque cycle, la consigne appliquée à l'appareil est strictement égale à `offpeak_power` ; aucune variation vers `power_min` ni vers autre valeur au sein des cycles testés.

### AC-002 — Appareil variable actif, consigne HC supérieure à la demande de l'algorithme

- **Préconditions** : comme AC-001 **et** la solution de l'algorithme (simulée) demande `power_min` (ou toute valeur inférieure à `offpeak_power`).
- **Résultat attendu** : malgré la solution de l'algorithme à `power_min`, la consigne appliquée reste `offpeak_power` et non `power_min`. (Critère discriminant du path H1.)

### AC-003 — `offpeak_power` non configuré

- **Préconditions** : appareil `power` actif ; `offpeak_power` absent dans la configuration ; `power_max` valide ; plage offpeak en cours.
- **Résultat attendu** : la consigne HC appliquée est `power_max` (repli), **constante** sur les cycles.

### AC-004 — `offpeak_power` configuré, repli vers `power_max` non requis

- **Préconditions** : `offpeak_power` configuré et valide.
- **Résultat attendu** : la consigne appliquée est `offpeak_power`, **pas** `power_max`.

### AC-005 — `offpeak_power` fourni par gabarit (template)

- **Préconditions** : `offpeak_power` est un gabarit qui peut changer au fil des cycles.
- **Résultat attendu** : le comportement est conforme à la décision retenue dans Q-003 (valeur échantillonnée une fois en début de plage **ou** à chaque cycle), et **jamais** une variation non justifiée n'est observée à l'intérieur d'un cycle donné.

### AC-006 — Appareil arrêté

- **Préconditions** : appareil `power` **inactif** ; plage offpeak en cours.
- **Résultat attendu** : aucune consigne de puissance n'est émise vers l'appareil (pas d'appel au service de changement de puissance) ; le système n'active pas l'appareil **pour** appliquer la consigne HC.

### AC-007 — Limite de durée atteinte pendant la plage

- **Préconditions** : la durée allumée cumulée de l'appareil atteint `max_on_time_offpeak_min` (ou `max_on_time_per_day_min`) pendant la plage offpeak alors que l'appareil est actif.
- **Résultat attendu** : l'appareil cesse d'être actif ; la consigne HC n'est plus appliquée après l'arrêt ; aucune nouvelle activation forcée par la consigne HC.

### AC-008 — Temporisation de changement de puissance en début de plage

- **Préconditions** : l'appareil vient de changer de puissance juste avant `offpeak_time` ; `duration_power_min` non écoulée.
- **Résultat attendu** : la consigne HC n'est appliquée qu'après expiration de `duration_power_min`, conformément à la décision prise dans Q-002 ; tant que la temporisation court, le système ne doit pas émettre de changement de puissance.

### AC-009 — Sortie de la plage offpeak

- **Préconditions** : l'appareil a été à `offpeak_power` pendant la plage ; le champ `raz_time` est atteint.
- **Résultat attendu** : à partir du cycle suivant la sortie de la plage, la consigne appliquée est redéterminée par l'algorithme (plus forcée à `offpeak_power`), sans double commande contradictoire dans le même cycle.

### AC-010 — Non-régression appareil à puissance fixe

- **Préconditions** : appareil `switch` actif ; plage offpeak en cours.
- **Résultat attendu** : le comportement de l'appareil `switch` est identique à celui avant toute modification (pas de variation de puissance, aucune notion de `offpeak_power` appliquée).

### AC-011 — Non-régression surcharge manuelle

- **Préconditions** : la surcharge manuelle est activée ; l'utilisateur change manuellement l'état ou la puissance de l'appareil pendant la plage offpeak.
- **Résultat attendu** : le mécanisme de surcharge manuelle continue d'interrompre la gestion Solar Optimizer selon son contrat existant ; la consigne HC n'est pas ré-appliquée tant que la surcharge n'est pas levée.

### AC-012 — Erreur de validation de configuration

- **Préconditions** : une configuration `offpeak_power` hors de la plage valide (`< power_min`, `> power_max`, pas multiple de `power_step`, non finie, ≤ 0) est fournie.
- **Résultat attendu** : `ConfigurationError` est levée **à l'initialisation** (contrat actuel) ; le système ne tente pas d'appliquer une valeur invalide à l'exécution.

### AC-013 — Pas de ré-émission abusive en état stable

- **Préconditions** : l'appareil est déjà à `offpeak_power` ; la consigne HC cible est `offpeak_power` ; la mesure et la consigne coïncident.
- **Résultat attendu** : sur le cycle courant, **aucun** appel au service de changement de puissance (pas de ré-émission). Le système émet une commande uniquement si la valeur courante diffère de la cible, selon la politique définie dans Q-005.

### AC-014 — Journalisation de la décision

- **Préconditions** : tous les cas des critères AC-001 à AC-013.
- **Résultat attendu** : pour chaque décision de consigne HC (appliquée, repli, non-appliquée), une entrée journalisante identifie l'appareil, la valeur cible, et la raison (forçage, limite atteinte, temporisation, appareil inactif, etc.), sans exposer de donnée sensible non anonymisée.

---

## 7. Hypothèses et contrainte connues

> Séparation explicite entre hypothèses de travail (non démontrées) et faits vérifiés dans le code local.

### 7.1 Hypothèses retenues (non démontrées, à confirmer)

- **H001** : la valeur « 15 A » rapportée dans l'issue correspond à la valeur maximale effective de l'appareil (probablement `power_max` exprimée en ampères, non convertie en W), mais la version exacte et la configuration complète de l'appareil (conversion de puissance, `power_step`, etc.) restent inconnues. Les scénarios testés doivent donc couvrir les configurations typiques sans dépendre d'un jeu de valeurs exact.
- **H002** : le début de la plage à 00:38 rapporté par l'utilisateur correspond au champ `offpeak_time` et la remise à zéro à 06:38 correspond au champ `raz_time`. La plage correspond donc à une fenêtre de 00:38 à 06:38 au sens strict (sans enroulement au-delà de minuit dans le signalement).
- **H003** : « plusieurs passages à la puissance minimale » correspondent à des cycles distincts du coordinateur où la valeur `effective_requested_power` envoyée a réellement été `power_min`, et non à des oscillations de mesure. (Hypothèse de cause locale : H1/H2/H3 de la revue.)

### 7.2 Faits vérifiés dans le code local (sans interprétation)

- Le schéma de configuration `power_managed_device_schema` déclare `power_min` (défaut 220), `power_max` (requis), `power_step` (défaut 220), `offpeak_power` (facultatif), `offpeak_time` (facultatif), `max_on_time_offpeak_min` (facultatif), `min_on_time_per_day_min` (facultatif), `max_on_time_per_day_min` (facultatif), et `duration_power_min` (facultatif).
- La propriété `offpeak_power` de l'appareil géré **lève** `ConfigurationError` si la valeur est non finie, ≤ 0, inférieure à `power_min`, supérieure à `power_max`, ou (lorsqu'elle est explicitement configurée) non alignée sur `power_step` à partir de `power_min`. Sinon, en l'absence de configuration, elle renvoie `power_max` (repli).
- La décision `should_be_forced_offpeak` est **fausse** si l'appareil n'est pas utilisable (`check_usable(False)` faux), si `offpeak_time` est absent, ou si l'une des durées cumulées (`on_time_sec >= max_on_time_per_day_sec`, `>= max_on_time_offpeak_sec`, ou pas `< min_on_time_per_day_sec`) n'est pas satisfaite — c'est-à-dire que le forçage peut cesser **dans la plage**, notamment lorsque le minimum quotidien a déjà été atteint.
- La fenêtre horaire utilisée par `should_be_forced_offpeak` gère l'enroulement lorsque `offpeak_time >= raz_time` (plage enroulant via minuit), conformément à BR-005.
- Le coordinateur n'applique la consigne `offpeak_power` que si **le forçage est vrai, l'état de la solution est inactif** (`not state`) **et** l'appareil peut changer de puissance (`can_change_power`). La consigne de l'algorithme (valeur `requested_power`) prévaut sinon. La modification de la puissance n'est émise que si elle diffère de la puissance courante ou si l'appareil vient d'être activé (`not is_active`).
- Le `is_waiting` (attente après changement d'état) peut empêcher la modification de puissance de l'appareil, même si la solution de l'algorithme le souhaite ; `is_waiting` est distinct de `check_usable`.
- La reconstruction de la puissance courante (à partir de l'état de l'appareil ou de la mesure réelle) **retombe** sur `power_min` pour un appareil variable lorsque l'entité de puissance est absente, `unknown` ou `unavailable`, même si l'appareil est actif et censé être à `offpeak_power`. (Voir Q-004.)
- L'algorithme de recuit simulé peut produire une `requested_power` égale à `power_min` (par exemple lors d'une activation simulée, où `requested_power` est initialisé à `power_min`), ce qui est une source de la valeur « basse » observée si la consigne HC n'est pas imposée (H1).
- Le test `tests/test_power_device.py` en local simule un forçage vrai et une solution inactive pour vérifier la consigne configurée ou son repli ; il **ne** couvre pas le cas de solution **active** ni le maintien de la consigne sur plusieurs cycles.

### 7.3 Limites des sources analysées

- Aucune capture de l'issue n'a été examinée visuellement.
- La version exacte installée par l'auteur n'a pas été identifiée (le manifeste local indique 3.9.0, mais l'environnement réel est inconnu).
- Aucun test ni reproduction réelle n'a été exécuté ; les constats sont le résultat d'une lecture statique.
- La revue ne permet ni de confirmer ni d'infirmer le chemin de code effectivement exercé lors de l'incident ; les hypothèses H1/H2/H3 restent ouvertes.

---

## 8. Points ouverts nécessitant une décision

> Chaque point est formulé pour être résolu **avant** le développement. Chaque décision doit être consignée ci-dessous ou dans un document annexe référencé par les spécifications.

### Q-001 — Lien entre la règle fonctionnelle et `should_be_forced_offpeak`

La règle métier de l'utilisateur est formulée en termes de **période d'heures creuses** (entre `offpeak_time` et `raz_time`). Or le code local n'impose la consigne `offpeak_power` que lorsque `should_be_forced_offpeak` **est vrai** — ce qui peut cesser avant la fin de la plage (par ex. si `on_time_sec >= min_on_time_per_day_sec`, ou si l'appareil n'est pas utilisable).

- **Option A** : appliquer la règle strictement sur la **période** (plage) ; dans ce cas, il faut garantir la consigne HC **même** si `should_be_forced_offpeak` est faux dans la plage.
- **Option B** : conserver le lien avec `should_be_forced_offpeak` **et** documenter que la consigne ne peut pas être appliquée si l'appareil n'est pas « forcible » (par ex. minimum atteint). Dans ce cas, la règle est écartée et il n'y a pas de garantie de constance sur toute la plage.

> **Décision (utilisateur, 2026-11-21) : Option B retenue.** La règle est ancrée sur `should_be_forced_offpeak` : la consigne `offpeak_power` est imposée **tant que** le forçage est vrai. Conséquences documentées (conception § 5, R3) : si `min_on_time_per_day_min` est atteint avant la fin de la plage, ou si la temporisation `duration_power_min` court, le forçage est faux et la consigne HC ne s'applique pas — l'utilisateur accepte cet écart à la formulation initiale en termes de période.

### Q-002 — Temporisation de puissance au début de la plage

Si `duration_power_min` est encore en cours au démarrage de la plage, la consigne `offpeak_power` ne **peut** pas être appliquée immédiatement sans enfreindre la temporisation.

- **Option A** : retarder l'application de la consigne HS jusqu'à expiration de `duration_power_min`, sans action pendant l'attente.
- **Option B** : appliquer la consigne HS **immédiatement** en annulant la temporisation en cours (risque d'enfreindre la protection de l'appareil).

> **Décision (utilisateur, 2026-11-21) : Option A retenue.** La temporisation est respectée ; aucun changement de puissance n'est émis tant que `duration_power_min` court (le forçage est faux pendant l'attente, via `check_usable(False)`).

### Q-003 — Échantillonnage d'une `offpeak_power` dynamique (gabarit)

Si `offpeak_power` est un gabarit :

- **Option A** : échantillonner la valeur **une seule fois** à l'entrée de la plage et la figer jusqu'à la fin de la plage.
- **Option B** : ré-échantillonner la valeur à **chaque cycle** du coordinateur.
- **Option C** : échantillonner à un rythme défini (par ex. une fois par heure).

> **Décision (Q-003, validée le 2026-11-21)** : la valeur du gabarit est ré-échantillonnée **une fois par cycle** du coordinateur (pas figée sur toute la plage) ; la valeur obtenue est réutilisée dans le cycle pour `activate` et `change_requested_power`, garantissant l'absence de variation intra-cycle.

### Q-004 — Repli en cas de mesure indisponible

Le repli actuel de la reconstruction de la puissance courante (sur `power_min` si mesure indisponible) crée un **risque de confusion** avec la consigne HC : le système pourrait croire qu'il est déjà à `power_min` et donc considérer que la consigne HS n'est pas appliquée, et ré-émettre. Ou au contraire le repli peut masquer un problème.

- **Option A** : conserver le repli actuel et s'appuyer uniquement sur la comparaison consigne cible vs consigne courante (planning), sans s'appuyer sur la mesure.
- **Option B** : ajouter un repli « consigne HC » distinct qui considère la mesure indisponible comme « la consigne HS reste appliquée » tant qu'aucun changement de puissance n'est émis.

> **Décision (utilisateur, 2026-11-21) : Option A retenue.** Le repli de reconstruction est conservé ; lors du forçage actif, la comparaison d'émission porte sur la dernière valeur planifiée et non sur la mesure. Voir conception `issue-231-design.md` § 4.2 et § 11 (R2).

### Q-005 — Politique de ré-émission en état stable

La règle « pas de ré-émission en état stable » (REQ-009) peut entrer en tension avec la reconstruction de la puissance, si la mesure est indisponible : le système comparerait `offpeak_power` à `power_min` (repli) et **ré-émettrait** alors même que l'appareil est déjà à `offpeak_power`.

- **Option A** : ne ré-émets que si la consigne **planifiée** (dernière valeur demandée par SO) diffère de la cible, en ignorant la mesure.
- **Option B** : ré-émets si **toute** source (mesure OU planning) indique une valeur différente.

> **Décision (utilisateur, 2026-11-21) : Option A retenue, en cohérence avec la décision Q-004**, et limitée au chemin de forçage actif : hors forçage, le comportement existant (comparaison à la mesure) est conservé.

### Q-006 — Priorité avec une surcharge manuelle pendant la plage

La surcharge manuelle peut co-exister avec la consigne HS. Le comportement actuel (selon `respect_manual_changes`) **peut** ou **ne peut pas** céder la main à l'utilisateur.

> **Décision (utilisateur, 2026-11-21) : la surcharge manuelle conserve la priorité selon son contrat existant.** La consigne HC n'interrompt pas une surcharge en cours ; lorsque le verrou de surcharge est actif (`enable=False`), aucune commande SO n'est émise.

---

## 9. Traçabilité

| Référence                               | Emplacement vérifié                                         | Fait supportant                                                                                |
| --------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Option `offpeak_power`                  | `config_schema.py` — `power_managed_device_schema`          | Option facultative, type `str`                                                                 |
| Défauts `power_min`, `power_step`       | `config_schema.py`                                          | Défaut 220 pour `power_min` et `power_step`                                                    |
| Défaut `raz_time`                       | `const.py`                                                  | `DEFAULT_RAZ_TIME = "05:00"`                                                                   |
| Repli `offpeak_power → power_max`       | `managed_device.py` — propriété `offpeak_power`             | Valeur par défaut si non configurée                                                            |
| Validation de `offpeak_power`           | `managed_device.py` — propriété `offpeak_power`             | `ConfigurationError` si invalide                                                               |
| Décision de forçage HC                  | `managed_device.py` — `should_be_forced_offpeak`            | Dépend de `check_usable(False)` et des durées cumulées                                         |
| Fenêtre enroulante                      | `managed_device.py` — `should_be_forced_offpeak`            | Gestion `offpeak_time >= raz_time`                                                             |
| Temporisation de puissance              | `managed_device.py` — `reset_next_date_available_power`     | Mise à jour lors d'un changement de puissance                                                  |
| Reconstruction de la puissance courante | `managed_device.py` — `set_current_power_with_device_state` | Repli sur `power_min` si mesure indisponible                                                   |
| Application de la consigne HC           | `coordinator.py` — boucle sur la solution                   | Sélection `effective_requested_power` si forçage vrai + solution inactive + `can_change_power` |
| Algorithme : activation à `power_min`   | `simulated_annealing_algo.py` — `permuter_equipement`       | `requested_power = power_min` lors d'une activation simulée                                    |
| Test existant                           | `tests/test_power_device.py`                                | Vérifie la consigne HC configurée ; ne couvre pas le cas de solution active                    |

> Aucune ligne de code n'est citée ici sans avoir été lue localement. Aucune référence n'est inventée.

---

## 10. English Summary

### 10.1 Metadata

The following section is the **English counterpart** of this document, with the same requirements, business rules and acceptance criteria (identical identifiers), written for stakeholders who read English.

### 10.2 Context and objectives

The user has reported that during a defined off-peak window, a variable-power device (type `power`) is observed to have its applied power drop — repeatedly — from the configured setpoint `offpeak_power` (15 A in the report) to `power_min`. The expected contract, made explicit by the user, is:

> "During off-peak hours, for a `power`-typed device with variable power, the applied power must be `offpeak_power` and must not vary."

The functional scope of this specification covers the **off-peak period** (between `offpeak_time` and `raz_time`, potentially wrapping across midnight), and **not** only the cycles where the off-peak forcing decision evaluates to true. It covers:

- Selection of the power setpoint for a variable-power device **in operation** during the off-peak period.
- Constancy of that setpoint from one cycle to the next.
- Interactions with duration limits, availability timeouts, start/stop, and the transition out of off-peak.
- Handling of `offpeak_power` when absent (fallback to `power_max`) or dynamic (template).

Out of scope: general refactoring of the optimiser, resolution of issue #230, changes to the daily on-time counter or the reset at `raz_time`, addition of hardware-level commands, or changes to the user's Home Assistant installation.

### 10.3 Actors and use cases

- **User / owner**: configures the off-peak window and the `offpeak_power` setpoint; expects the applied power to be constant during the window.
- **Solar Optimizer (system)**: computes an optimisation solution and determines the power to apply for each device at every cycle.
- **Managed device (`power` type)**: variable-power entity driven by a change-power service.
- **Managed device (`switch` type)**: fixed-power entity, **not** affected by power variation.
- **User or third-party automation**: may manually command the device (manual override), or, in the reported incident, modify the power externally.

Use cases mirror the French version (2.1–2.4): constant off-peak setpoint on an active variable-power device; stop during the window (limits); exit from the off-peak window at `raz_time`; manual override preserved.

### 10.4 Functional requirements

- **REQ-001** — Imposed and constant off-peak setpoint. During the off-peak period, for every variable-power device **in operation**, the system shall apply a power setpoint strictly equal to `offpeak_power` and shall **not** allow that setpoint to vary from one cycle to the next solely because of the optimisation algorithm.
- **REQ-002** — `offpeak_power` absent or invalid: defined fallback. When `offpeak_power` is not configured, the system shall use the current fallback, `power_max`, as the off-peak setpoint. This fallback must satisfy the same constancy requirement as REQ-001 during the window. A configured but invalid `offpeak_power` is handled at initialisation time per the current contract (see BR-003 and AC-012).
- **REQ-003** — Dynamic (template) `offpeak_power`. When `offpeak_power` is provided as a template whose value may vary over time, the system must explicitly define **how the value is sampled** (at which cycle frequency, at which point) so that it remains consistent with the constancy requirement of REQ-001. A dynamic value shall not produce an uncontrolled variation within a same cycle. *(Awaiting decision — see Q-003.)*
- **REQ-004** — Application on active devices only. The `offpeak_power` setpoint applies **only** while the device is in operation. The system shall not force activation of the device **nor** maintain a power setpoint when the device is stopped, unavailable, or not usable.
- **REQ-005** — Respect of limits and timeouts. The constant-setpoint requirement does **not** exempt the system from respecting the configured durations and protections for the device, notably `min_on_time_per_day_min`, `max_on_time_per_day_min`, `max_on_time_offpeak_min` and the power-change availability timeout (`duration_power_min`). The system must define explicitly, for every limit, whether the limit may stop the device operation — and therefore stop the application of the off-peak setpoint — and whether the power timeout may delay or prevent the initial switch to `offpeak_power` at the start of the window.
- **REQ-006** — Transition on exit from the off-peak window. At the end of the off-peak window (`raz_time`), the system shall return the variable-power device under the control of the optimisation algorithm in a **defined and controlled** manner: the setpoint becomes the optimiser solution again, without undocumented discontinuity or contradictory duplicate command within the same cycle.
- **REQ-007** — No regression for fixed-power devices. Fixed-power devices (type `switch`) are **not** affected by REQ-001 through REQ-006. The system shall continue to manage them per their current behaviour (on/off, no power variation).
- **REQ-008** — No regression of existing mechanisms. The system shall continue to guarantee correct operation of manual commands / manual override, user stop, unavailable devices, multi-device management, and configuration validation errors.
- **REQ-009** — No spurious re-issuance of the setpoint. The system shall not re-issue a change-power command to `offpeak_power` on every cycle when the setpoint is already applied (stable state). The system shall define a comparison policy between the currently active setpoint and the target `offpeak_power` before issuing a command.
- **REQ-010** — Diagnostics and traceability. The system shall log at a sufficient level the "off-peak setpoint imposed / fallback / not applicable" decision and its justification (forcing, availability, reached limit), so that issued setpoints can be correlated with measured power. These logs must not disclose un-redacted sensitive data.

### 10.5 Business rules (identical identifiers as FR)

- **BR-001** — `offpeak_power` is the **only** valid power setpoint for an in-operation variable-power device during the off-peak window. Any other value (notably `power_min` or an intermediate value) produced by the algorithm is disregarded during the window.
- **BR-002** — Forcing activation is **not** a precondition for applying the off-peak setpoint; the device being in operation is. That is: even if the device was not activated by the coordinator, if it is in operation for another reason (manually or by a third-party automation, for instance), the off-peak setpoint is applied to the power, as long as the device is operating.
- **BR-003** — The fallback is `power_max` when `offpeak_power` is absent. The validation of `offpeak_power` requires `power_min ≤ offpeak_power ≤ power_max` and, when explicitly configured, that the distance from `power_min` be a multiple of `power_step`. On validation error, a `ConfigurationError` shall be raised **at initialisation** (current contract) and not at runtime.
- **BR-004** — The limits `max_on_time_per_day_min`, `max_on_time_offpeak_min`, `min_on_time_per_day_min` and the timeout `duration_power_min` have **absolute priority** over off-peak setpoint application for start/stop decisions. However, on the value of power to apply while the device is effectively in operation, the off-peak setpoint has priority over the algorithm's intermediate value.
- **BR-005** — On exit from the off-peak window (`raz_time`), the system returns to the "algorithm rule" behaviour. If the window wraps past midnight (`offpeak_time >= raz_time`), the window is considered continuous in the hourly sense (from `offpeak_time` to `raz_time` via midnight), matching the current system behaviour.

---

## 10.6 Constraints

- **Security / privacy**: any log produced for tracing (REQ-010) must be redacted; no identifier, secret, or unnecessary private data shall appear in logs or diagnostics excerpts.
- **Energy**: no real physical device command shall be executed within the specification tests (simulated actions only); analysis must be able to rely on logs, not on a real device.
- **Compatibility**: the `offpeak_power → power_max` fallback shall remain available and shall not break existing configurations. Any contract change between the documented behaviour for issue #186 (algorithm priority) and the present contract must be clearly communicated (release note and user documentation update).
- **Availability**: a failure or unavailability of the power measurement entity must not block the off-peak setpoint decision; the current fallback (see `set_current_power_with_device_state`) may be kept, but **may** be complemented by an explicit target setpoint decision (see Q-004).

### 10.7 Acceptance criteria (mirrors AC-001–AC-014, identical identifiers)

The English version mirrors the French acceptance criteria **one-for-one**: each `AC-xxx` has the same preconditions, actions, expected results, and discriminant intent. The details are intentionally not re-listed here to avoid divergence; the French section 6 is authoritative and the identifiers are identical.

### 10.8 Assumptions and known constraints

- **H001** — the "15 A" reported in the issue corresponds to the effective maximum value of the device (likely `power_max` expressed in amperes, not yet converted to watts); the exact version and the full device configuration (power conversion, `power_step`, etc.) remain unknown.
- **H002** — the reported 00:38 start corresponds to the `offpeak_time` field and the 06:38 reset to the `raz_time` field. The window is therefore a strict 00:38-to-06:38 interval (no wrap-around past midnight in the report).
- **H003** — the "multiple drops to the minimum power" correspond to distinct coordinator cycles where the `effective_requested_power` actually sent was `power_min`, not measurement oscillations. (Local cause hypotheses: H1/H2/H3 from the review.)
- **Verified facts (static reading only)**: see the French section 7.2 and 7.3 for the exact list (identical facts, translated on demand). No line of code is cited without having been read locally.

### 10.9 Open questions requiring decision (mirrors Q-001–Q-006, identical identifiers)

All questions have been resolved by user decision on 2026-11-21 (see the French section 8 for the full rationale; identifiers are identical, the French version is the authoritative source):

- **Q-001 — Option B selected**: the rule is anchored on `should_be_forced_offpeak`; the setpoint is enforced **only while** forcing is true. Documented consequence: if `min_on_time_per_day_min` is reached before the end of the window (or while `duration_power_min` is running), forcing is false and the off-peak setpoint does not apply.
- **Q-002 — Option A selected**: the `duration_power_min` timeout is respected; no power-change command is issued while the timeout is running.
- **Q-003 — Re-sampled once per coordinator cycle** (not frozen for the whole window); no additional persisted state; intra-cycle constancy guaranteed by single per-cycle resolution reused for `activate` and `change_requested_power`; inter-cycle changes are attributable to the template and logged (AC-014).
- **Q-004 — Option A selected**: when forcing is active and the measurement is unavailable, the emission comparison is made against the last **planned** value instead of the measurement.
- **Q-005 — Option A selected**, consistent with Q-004 and limited to the active-forcing path: without forcing, existing behaviour (comparison against the measurement) is preserved.
- **Q-006 — Manual override keeps priority per its existing contract**: the off-peak setpoint does not interrupt an active override; while the override lock is active (`enable=False`), no SO command is issued.
