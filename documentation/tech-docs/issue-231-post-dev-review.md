# Revue post-développement — Issue #231 : puissance modifiée pendant les heures creuses

## Synthèse actuelle

**2026-11-21 — Nouvelle revue indépendante : VALIDÉ AVEC RÉSERVES.** Recommandation technique : approuver sous réserves, sans attester une recette matérielle ni clore l'incident réel. **Aucun nouveau bug d'exécution bloquant ou élevé avéré dans le diff examiné.** Les lacunes de tests et de traçabilité ci-dessous restent visibles ; une suite verte ne suffit pas à établir la conformité intégrale aux AC.

**Approbation utilisateur du 2026-11-21 : revue approuvée avec ses réserves**, pour l'état examiné `e7492c8`. Les corrections F-1 à F-4 sont acceptées ; les réserves C-1 à C-4 et les limites de validation restent consignées pour suivi. Cette approbation termine la phase de revue post-développement, sans confirmer la résolution matérielle de l'incident ni autoriser des corrections supplémentaires, un commit, un déploiement ou la fermeture de l'issue GitHub.

### Référence et sources actuelles

- Branche : `issue-231-offpeak-power`, HEAD `e7492c89cb514366a113c9637c5542e86e8da8f7` (`e7492c8`, « Dev 2nd round »), également référence distante locale. Base et merge-base de `main` : `3a0278c7185e473e9685fc44a8010bd7cff3956b`. Worktree propre au début et avant l'édition du rapport ; cela ne signifie pas absence de diff.
- Comparaison `3a0278c...HEAD` : neuf fichiers, dont seulement deux fichiers de production, [coordinator.py](../../custom_components/solar_optimizer/coordinator.py) et [managed_device.py](../../custom_components/solar_optimizer/managed_device.py), les deux README, [test_power_device.py](../../tests/test_power_device.py) et les quatre documents de l'issue. Les états courants du test et du présent rapport ont été relus, sans rétablir d'ancien contenu utilisateur.
- Contrat : [spécifications](issue-231-specifications.md), [conception](issue-231-design.md), [revue amont](issue-231-review.md), puis code et tests actuels. Q-001 à Q-006 sont des décisions documentées : forçage effectif, temporisations respectées, un échantillonnage par cycle, planning sous HC et mesure hors HC, override prioritaire. La formulation initiale « toute la plage » n'est pas le contrat retenu.
- Lecture complémentaire : [test_logbook.py](../../tests/test_logbook.py), [test_min_on_time.py](../../tests/test_min_on_time.py), [test_override_scenarios.py](../../tests/test_override_scenarios.py), [switch.py](../../custom_components/solar_optimizer/switch.py#L250), [simulated_annealing_algo.py](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L117), consignes de contribution, options pytest et workflows CI. Les autres tests sont exécutés par la suite, pas tous audités ligne par ligne.
- **Source nouvelle vérifiée sur [l'issue publique](https://github.com/jmcollin78/solar_optimizer/issues/231)** : l'auteur déclare maintenant SO `3.10.0`, puissance min/max/pas `1440/4320/240 W`, consigne HC `3600 W`, diviseur `240`, temporisation puissance `5 min`, minimum quotidien `720 min`, fenêtre `00:38–06:38`. Ainsi `3600 / 240 = 15 A`, et non `power_max = 15 A`. Version et configuration ne sont plus entièrement inconnues comme dans la revue amont ; captures non examinées, journaux corrélés absents, cause H1/H2/H3 toujours non attribuée. Les identifiants et templates personnels ne sont pas recopiés ici.
- Autorisation : nouvelle revue et mise à jour du seul rapport existant. Aucun correctif de code/test/README, changement HA, dépendance, version, commit, branche ou sous-agent. Paramètre de modèle demandé : GPT-6.1 Sol ; modèle effectivement exécuté non attestable ici.

### F-1 à F-4 : statuts revérifiés

| Constat historique                      | Statut actuel et preuve                                                                                                                                                                                                                                                                                                                                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F-1 planning périmé                     | **Corrigé, clôturable.** [Synchronisation après chaque changement](../../custom_components/solar_optimizer/coordinator.py#L337), même hors HC. [Test à quatre cycles](../../tests/test_power_device.py#L426) : activation 600, baisse algo 300, entrée HC 600, puis aucune réémission ; commandes et plan assertés. Comparaison au plan sous HC et à la mesure hors HC conservée.                       |
| F-2 README français tronqué             | **Corrigé, clôturable.** README courant de 859 lignes, sections configurations/algorithme/entités/priorité/événements/actions/capteurs/carte/contributions présentes. Diff contre la base : +7/-5, pas de suppression massive. Préservation du contenu actuel, sans exiger une égalité aveugle avec la restauration historique.                                                                         |
| F-3 ancienne consigne en mode événement | **Corrigé, clôturable.** [Argument normalisé émis puis suivi](../../custom_components/solar_optimizer/managed_device.py#L332), pas d'écriture du plan par `_apply_action`. [Bus et contexte réels de test](../../tests/test_power_device.py#L14), [dix cas dans les deux modes](../../tests/test_power_device.py#L69), [deux cycles HC sans réémission](../../tests/test_power_device.py#L168) passent. |
| F-4 promesse README / logs              | **Corrigé pour les README, clôturable.** [Texte FR](../../README-fr.md#L243) et [EN](../../README.md#L259) concordent avec [les trois messages](../../custom_components/solar_optimizer/coordinator.py#L293) : consigne imposée, repli `power_max`, inapplicable avec `forcing` et `can_change_power`. Cela ne vaut pas couverture complète de REQ-010/AC-014.                                          |

### Constats actuels classés

**Moyen — C-1 : couverture HC encore partielle (ancien F-7, risque, pas bug reproduit).** Les tests [de stabilité](../../tests/test_power_device.py#L512) gardent la même solution ; [le gabarit dynamique](../../tests/test_power_device.py#L621) ne compte pas les rendus et n'exerce pas activation + changement avec un rendu différent à chaque accès. Manquent notamment T3 alterné, début/expiration de temporisation HC, sortie réelle à `raz_time`, override sur appareil variable en HC et trois appareils aux décisions distinctes. Les tests voisins prouvent certaines briques mais pas leur composition avec cette priorité. Impact : régression possible non détectée aux frontières. Suivi recommandé : scénarios ciblés dans le fichier existant, sans assimiler ces absences à des défauts avérés.

**Moyen — C-2 : REQ-010/AC-014 restent partiels, malgré F-4 corrigé.** [Le log inapplicable](../../custom_components/solar_optimizer/coordinator.py#L307) ne fournit que deux indicateurs, ni cible ni motif détaillé limite/temporisation/inactivité. [Le test de log](../../tests/test_power_device.py#L698) vérifie uniquement des sous-chaînes « imposed », nom et 600 ; pas les branches repli/inapplicable/erreur. Impact : corrélation d'une baisse réelle moins précise. Recommandation : traiter cette exigence de diagnostic dans un suivi autorisé, ou expliciter que les logs convenus ne couvrent que les indicateurs. Les noms configurés sont journalisés sans expurgation : aucune fuite de secret démontrée, mais aucune garantie d'anonymisation de noms privés ; expurger avant partage de journaux.

**Faible — C-3 : dette de typage introduite dans les nouveaux tests.** [Exemple](../../tests/test_power_device.py#L409) : `async_set(..., 0)` alors que HA attend `str`. L'analyse AST identifie 37 appels à état numérique dans les fonctions absentes de la base ; plusieurs diagnostics correspondants sont visibles. HA les accepte dans l'exécution actuelle, donc pas d'échec runtime. Recommandation ultérieure : états textuels, sans modifier les assertions fonctionnelles. Les autres usages numériques des tests préexistants ne sont pas imputés à ce patch.

**Faible — C-4 : clarification documentaire de REQ-004/AC-006 (F-6 requalifié).** [REQ-004](issue-231-specifications.md#L115) dit « ne doit pas forcer l'activation », [AC-006](issue-231-specifications.md#L212) « n'active pas l'appareil pour appliquer la consigne HC ». À l'inverse, [la conception § 2.2](issue-231-design.md#L41) conserve expressément les règles on/off, et [sa ligne appareil inactif](issue-231-design.md#L186) prévoit l'activation par le forçage existant. [BR-002](issue-231-specifications.md#L166) ne rend pas l'activation par SO obligatoire, mais n'interdit pas ce forçage ; Q-001 borne l'application au forçage vrai. L'activation dépend de `state or should_force_offpeak`, pas de la seule présence d'une consigne. **Pas de nouveau bug produit démontré ni demande de supprimer le forçage** ; la lecture absolue de REQ-004 reste incompatible avec la conception explicite. Suivi : préciser « appareil restant inactif après décision on/off, sans activation pour la seule consigne », et tester ce cas. AC-006 n'est pas déclaré couvert par les tests d'activation forcée.

**Observations — publication et documentation.** [Note FR 3.9.1](../../README-fr.md#L63), [note EN](../../README.md#L69), manifeste `3.9.0` et tags locaux jusqu'à `3.10.1.beta1` : alignement à prévoir lors de la publication, pas motif autonome de rejet d'un patch avant release. Lien local absent dans [README.md](../../README.md#L724), cible `README-en.md` ; préexistant dans `3a0278c` (ligne 722 vérifiée avec `git show`), à traiter hors correction HC. Le titre anglais de création de capteurs et l'omission de la phrase sur l'erreur de formulaire restent des écarts documentaires mineurs ; les tableaux de validité et le contrôle runtime demeurent documentés.

### Conformité actuelle aux exigences et règles

Légende : **testé** = scénario effectivement exécuté et assertions lues ; **lecture** = contrat vérifié dans le chemin de code, pas preuve runtime complète ; **partiel** = détail/cas manquant. Les décisions Q priment sur les formulations initiales restées inchangées.

| Exigence / règle | Évaluation actuelle                                                                                                                                                                     |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REQ-001          | Testé sur solutions actives/inactives et stabilité sous forçage ; pas de preuve exhaustive alternée T3 ni de puissance matérielle constante.                                            |
| REQ-002          | Repli 1000 testé sur activation ; constance du repli sur plusieurs cycles non testée.                                                                                                   |
| REQ-003          | Une lecture de `offpeak_setpoint` par cycle vérifiée dans le coordinateur ; rendu 600 puis 800 testé. Absence de variation intra-cycle établie par lecture, pas par compteur de rendus. |
| REQ-004          | Conforme à la décision on/off de conception par lecture ; clarification C-4 et test AC-006 manquants.                                                                                   |
| REQ-005          | Protections inchangées par lecture ; briques durée/fenêtre testées dans la suite, pas composition HC variable complète.                                                                 |
| REQ-006          | Retour à la comparaison mesure/algo par lecture ; pas de scénario de sortie `raz_time` variable HC dédié.                                                                               |
| REQ-007          | Garde `can_change_power` et non-émission vers switch testées ; suite de non-régression verte.                                                                                           |
| REQ-008          | Override et dispositifs fixes testés hors ce scénario ; exclusion `enable=False` de l'algorithme vérifiée ; composition HC variable non testée.                                         |
| REQ-009          | Stabilité testée, plan après baisse hors HC testé, mesure indisponible simulée. Conforme à Q-004/Q-005, sans nouvelle décision à demander.                                              |
| REQ-010          | Partiel : C-2, confidentialité limitée à ce que montre le code.                                                                                                                         |
| BR-001           | Priorité HC sur la valeur testée, bornée au forçage vrai par Q-001.                                                                                                                     |
| BR-002           | Appareil actif non activé par SO servi selon le même chemin, par lecture ; forçage effectif requis selon Q-001. Ne signifie pas « toute activation forcée interdite ».                  |
| BR-003           | Corps de validation identique à la base et alias conservé ; quelques rejets testés (type switch, formulaire, runtime), pas toute la matrice de valeurs.                                 |
| BR-004           | Priorités des protections conservées par lecture ; `max_on_time_offpeak_min` coupe le forçage, pas nécessairement le fonctionnement décidé par l'algo (conception § 5).                 |
| BR-005           | Fenêtre enroulante et fin du forçage testées sur switch dans [test_min_on_time.py](../../tests/test_min_on_time.py#L596) ; sortie de consigne HC variable par lecture seulement.        |

### Critères et matrice de tests courants

| AC     | Couverture réellement constatée                                                                                                                                 |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-001 | Partiel : trois cycles stables, scénarios d'entrée, deux cycles événement ; pas trois cycles alternant ON/OFF/ON ni garantie hors forçage (Q-001).              |
| AC-002 | Testé : algo actif 100, consigne 600 émise ; événements réellement observés.                                                                                    |
| AC-003 | Partiel : repli testé un cycle sur appareil initialement inactif, pas constant sur trois cycles actifs.                                                         |
| AC-004 | Testé : consigne 600, non remplacée par `power_max=1000`.                                                                                                       |
| AC-005 | Rendu variable testé ; unicité intra-cycle par lecture, pas assertion discriminante du nombre d'accès.                                                          |
| AC-006 | Non testé sur appareil restant arrêté sans forçage ; clarification C-4.                                                                                         |
| AC-007 | Partiel : décision limite testée, pas arrêt d'un appareil variable à consigne HC dans le coordinateur.                                                          |
| AC-008 | Temporisation générale variable testée dans `test_power_device`, pas début de plage HC dédié.                                                                   |
| AC-009 | Lecture seulement pour la sortie de plage ; aucune preuve dédiée à `raz_time`.                                                                                  |
| AC-010 | Testé : switch sans commande de puissance ; pas test complet T13.                                                                                               |
| AC-011 | Partiel : scénarios override exécutés sur switches sans plage HC ; pas appareil variable HC.                                                                    |
| AC-012 | Partiel : rejet formulaire sous `power_min`, configuration switch et runtime invalide testés ; hors maximum, palier, non-fini et non-positif non tous assertés. |
| AC-013 | Testé : stabilité et plan différent de mesure simulée ; réception physique de la consigne non prouvée.                                                          |
| AC-014 | Partiel : C-2 ; repli, inapplicable, motif détaillé et erreur non assertés.                                                                                     |

| T   | Statut au regard du scénario exact de conception                                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | Testé : algo 100, plan/courant 600, aucune émission, test de logs.                                                                                      |
| T2  | Testé : courant/plan 100, émission 600.                                                                                                                 |
| T3  | Non testé : alternance trois cycles ON/OFF/ON. Le test F-1 à quatre cycles n'est pas ce scénario.                                                       |
| T4  | Testé : inactif + algo ON, activation et changement 600.                                                                                                |
| T5  | Partiel : repli un cycle, pas trois.                                                                                                                    |
| T6  | Partiel : gabarits constant/variable testés, compteur de rendus absent.                                                                                 |
| T7  | Testé : inactif + algo OFF, activation par forçage.                                                                                                     |
| T8  | Non testé à l'entrée HC ; briques temporisation générale testées.                                                                                       |
| T9  | Partiel : compteur réel et limite testés dans [test_min_on_time.py](../../tests/test_min_on_time.py#L350), pas consigne variable/arrêt au coordinateur. |
| T10 | Partiel : horloge enroulante testée sur switch, pas émission de consigne variable HC.                                                                   |
| T11 | Partiel : override testé hors HC ; composition demandée non testée.                                                                                     |
| T12 | Partiel : valide à l'initialisation puis invalide avant le cycle testé, pas deux cycles valide/invalide ni assertion du log d'erreur.                   |
| T13 | Partiel : switch/power testés, pas troisième variable non forcé ni trois décisions distinctes dans un même cycle.                                       |
| T14 | Partiel : plan 600 et repli courant 100 simulés sur un cycle ; pas reconstruction réelle d'une mesure indisponible après une première émission.         |

Décompte AST : 18 fonctions de tests de puissance actuelles contre 6 à la base ; 29 cas paramétrés exécutés dans ce fichier, plus 3 cas logbook. Les douze cas F-3 sont bien présents ; aucun décompte historique « huit » ou « dix tests ajoutés » n'est utilisé comme preuve actuelle.

### Validations de cette nouvelle revue

Environnement **terminal**, sans attestation de l'interpréteur sélectionné par Pylance : Python `3.14.10`, pytest `9.0.3`, HA `2026.9.4`, plugin pytest HA `0.13.367`. Skill Python fact-grounded lu ; outils Pylance avancés non disponibles, faits obtenus via diagnostics éditeur, lecture, AST et exécution. `rg` absent : première recherche CLI échouée, poursuivie avec outils de recherche disponibles. Aucun changement d'environnement.

| Commande / contrôle effectué                                                                                                                                                      | Résultat actuel                                                                                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `rtk pytest tests/test_power_device.py tests/test_logbook.py -q -p no:cacheprovider`                                                                                              | **32 passés**, 0 échec (1,13 s).                                                                                                                                                                                                                                                                                                                                                                                               |
| `rtk pytest tests -q -p no:cacheprovider -rs`                                                                                                                                     | **201 passés, 0 échec, 11 ignorés** (5,47 s). Les détails `-rs` sont masqués par RTK.                                                                                                                                                                                                                                                                                                                                          |
| `rtk proxy python -m pytest tests -q -p no:cacheprovider -rs 2>&1 \| rtk proxy grep -E 'SKIPPED\|passed\|failed\|skipped\|warning\|Warning\|short test summary\|^ERROR\|^FAILED'` | Reprise uniquement pour récupérer les détails perdus (également absents de `rtk recall`) : **201 passés, 11 ignorés** (5,79 s). Motif : tests non déterministes, 6 cas [test_nominal.py](../../tests/test_nominal.py#L200), 5 cas [test_priority.py](../../tests/test_priority.py#L148). Aucun avertissement pytest signalé dans cette sortie.                                                                                 |
| `get_errors`, trois Python modifiés, puis fichier de tests seul                                                                                                                   | **112 diagnostics annoncés**, dont 67 dans le test ; réponses limitées à 50 résultats. `float(None)` et annotations `int` dans ManagedDevice existaient dans la base ; `Unknown` reste visible sur `current_power`, comme documenté au § 12. Diagnostics numériques sur les nouveaux tests : C-3. **Pas d'affirmation « aucun nouveau diagnostic » sur égalité de nombres** ; baseline éditeur complète non exécutée sur main. |
| `rtk proxy python -c ...`, parsing AST des trois fichiers et comparaison du test au blob `3a0278c`                                                                                | Syntaxe valide ; fonctions et 37 nouveaux appels numériques relevés sans fichier écrit.                                                                                                                                                                                                                                                                                                                                        |
| `rtk proxy python -c ...`, action isolée avec service simulé levant `RuntimeError` et diviseur 10                                                                                 | `change_requested_power(600)` tente une valeur service 60 ; exception absorbée, événement envoyé, `current_power=600`, plan encore 100. Avertissement HA `install_as_voluptuous ... shadowing an already-imported voluptuous` observé à l'import ; pas un échec du test, pas masqué dans cette conclusion.                                                                                                                     |
| `rtk proxy git diff --check 3a0278c...HEAD`                                                                                                                                       | Aucun défaut d'espaces du diff committé.                                                                                                                                                                                                                                                                                                                                                                                       |
| `rtk proxy python -c ...`, UTF-8, structure et cibles inline/de référence des README et du rapport                                                                                | Avant édition : 79 cibles locales contrôlées, une absente (`README-en.md`), aucune ancre de ligne hors fichier ; autres cibles présentes. Parseurs Markdown recherchés non installés : contrôle limité de cibles, pas lint Markdown ni validation des ancres de titres ou URLs réseau.                                                                                                                                         |
| Après édition : `rtk proxy git diff --check`, contrôle UTF-8/liens du rapport, `rtk proxy git status --short`                                                                     | Aucun défaut d'espaces ; 88 cibles locales du rapport présentes, ancres de ligne dans les bornes, une seule synthèse actuelle ; seul ce rapport modifié.                                                                                                                                                                                                                                                                       |

Non exécutés : Black (non installé, aucune installation autorisée), lint complet, baseline Pylance main exhaustive, couverture, `hassfest`/HACS, CI parallèle/timeout, recette HA réelle et charge/concurrence. La CI prévoit des tests parallèles et la couverture ; la validation locale est séquentielle. Aucune consultation de `.storage`, secrets ou état HA, aucune commande physique.

### Risques résiduels et suivi

- **F-5 / Q-004-Q-005 : décision déjà actée, pas à rouvrir.** Le plan compare les dernières demandes SO, pas une confirmation matérielle. Une commande perdue ou un changement externe peut rester sans correction pendant le forçage ; les exceptions de service déjà absorbées à la base ne constituent pas un nouveau défaut autonome attribué au patch. La preuve isolée précise le suivi optimiste F-3 ; le coordinateur synchronise ensuite le plan après le retour de l'await, qui n'est pas une preuve de succès matériel.
- `_current_power` est optimiste après commande, puis reconstruit avant l'algorithme au cycle suivant ([coordinator.py](../../custom_components/solar_optimizer/coordinator.py#L189)). Le snapshot préactivation reste à 0, l'événement d'activation porte 0 et le changement suivant porte 500 ([test existant](../../tests/test_power_device.py#L1056)). Activation, arrêt à 0, repli `None`, deux modes, cibles et contextes ont été examinés ; aucun changement de schéma d'événement, entité ou migration. Conversion service inchangée, bus en W ; aucun succès matériel garanti.
- **R1 accepté par conception** : bilan algorithmique du cycle différent de la consigne appliquée en HC. Le plan synchronisé ne modifie pas rétroactivement la solution ; l'algorithme relit le courant au cycle suivant, pas le seul plan. Ampleur multi-appareils non mesurée, #230 non résolue.
- Lifecycle HA, listeners, traductions, config entries, services et `unique_id` ne sont pas modifiés par ce diff. Aucun ajout de dépendance, persistance HC, I/O bloquante ou migration ; aucun test de course annulation/commande concurrente ou de charge, donc pas de garantie nouvelle sur ces sujets.
- **Clôturable : F-1, F-2, F-3, F-4.** Suivi restant précis : compléter les tests de frontière/composition C-1 ; clarifier portée de traçabilité et expurgation C-2 ; états textuels C-3 ; formulation/test appareil restant inactif C-4 ; aligner numéro de release lors de la publication et suivre le lien README absent ; corréler les commandes et mesures du scénario 3.10.0 avant clôture de l'incident.

La présente synthèse remplace les verdicts, matrices et décisions encore ouvertes des sections historiques ci-dessous pour l'état `e7492c8`. Elle ne déclenche ni correction, ni déploiement, ni approbation métier ; les modifications correctives et vérifications supplémentaires restent soumises au processus d'autorisation de l'orchestrateur.

## Historique des revues et corrections

**Les § 1 à 10 décrivent exclusivement la revue initiale sur `a5180a3` ; les § 11 à 13 consignent les corrections et reprises antérieures. Leurs rejets, échecs et réserves ne sont pas le verdict actuel.** Leur contenu et les modifications utilisateur sont conservés comme historique, avec les requalifications ci-dessus.

## 1. Périmètre et référence

| Champ                  | Valeur                                                                                                               |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Issue                  | [#231](https://github.com/jmcollin78/solar_optimizer/issues/231)                                                     |
| Branche / commit       | `issue-231-offpeak-power` — `a5180a3` « Development ok » (base de comparaison : `main` @ `3a0278c`)                  |
| Date de revue          | 2026-11-21                                                                                                           |
| Environnement          | Python 3.14.10, pytest via `rtk pytest`                                                                              |
| Documents de référence | [spécifications](issue-231-specifications.md), [conception](issue-231-design.md), [revue amont](issue-231-review.md) |
| Contrainte             | Aucune modification de code, configuration ou test. Le dépôt est resté propre (`git status` vide).                   |

Fichiers inspectés : [coordinator.py](../../custom_components/solar_optimizer/coordinator.py), [managed_device.py](../../custom_components/solar_optimizer/managed_device.py), [simulated_annealing_algo.py](../../custom_components/solar_optimizer/simulated_annealing_algo.py) (lecture seule, aucune modification attendue), [test_power_device.py](../../tests/test_power_device.py), [README.md](../../README.md), [README-fr.md](../../README-fr.md), [manifest.json](../../custom_components/solar_optimizer/manifest.json).

Le diff `main...HEAD` modifie aussi les trois documents `issue-231-*` et les deux README (voir § 5).

## 2. Décision proposée

**Décision historique sur `a5180a3` : REJETÉ — corriger avant approbation. Voir la synthèse actuelle pour `e7492c8`.**

Motifs : un défaut élevé reproduit (consigne HC jamais appliquée à l'entrée du forçage dans un scénario réaliste), la perte d'environ 600 lignes de `README-fr.md`, et neuf scénarios de la matrice de conception sans test. Le cœur du correctif (suppression de `not state`, résolution unique par cycle) est correct et les 188 tests passent.

## 3. Validations exécutées

| Commande                                                       | Résultat                                                                                                                                                                                                                                                                                            |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rtk pytest tests/test_power_device.py -q`                     | 16 passés, 0 échec                                                                                                                                                                                                                                                                                  |
| `rtk pytest tests -q` (suite complète)                         | **188 passés, 0 échec, 11 ignorés** (le motif des 11 tests ignorés n'a pas été analysé)                                                                                                                                                                                                             |
| Diagnostics éditeur (`get_errors`) sur les 3 fichiers modifiés | Uniquement des avertissements de typage (`None` non assignable, `float`/`int`). Les lignes ajoutées ([managed_device.py L806-L807](../../custom_components/solar_optimizer/managed_device.py#L806)) reprennent le code préexistant de `offpeak_power`. Aucune erreur nouvelle de nature différente. |
| Reproduction isolée (copie temporaire hors dépôt, supprimée)   | Deux défauts confirmés (F-1, F-3)                                                                                                                                                                                                                                                                   |

Non exécuté : couverture de code (`htmlcov/` présent mais non régénéré), tests sur une instance Home Assistant réelle, `hassfest`, lint de formatage.

## 4. Conformité (REQ / BR / AC)

Légende : **Conforme** = vérifié par lecture et par test ; **Conforme (lecture)** = vérifié par lecture, sans test dédié ; **Partiel** ; **Non conforme**.

### 4.1 Exigences

| ID                                     | Verdict            | Preuve                                                                                                                                                                                                                                                                                                                        |
| -------------------------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REQ-001 consigne HC constante          | **Partiel**        | `not state` supprimé : [coordinator.py L277-L279](../../custom_components/solar_optimizer/coordinator.py#L277). Vérifié par `test_offpeak_forcing_overrides_active_algorithm_power`. **Non conforme** si le planning est obsolète (F-1) ou en mode `event` (F-3).                                                             |
| REQ-002 repli `power_max`              | Conforme           | [managed_device.py L803-L804](../../custom_components/solar_optimizer/managed_device.py#L803) ; cas paramétré `None → 1000` (un seul cycle, solution inactive).                                                                                                                                                               |
| REQ-003 gabarit échantillonné 1×/cycle | Conforme           | `offpeak_setpoint` lu une fois ([coordinator.py L282](../../custom_components/solar_optimizer/coordinator.py#L282)) et réutilisé par `activate` et `change_requested_power` ; `test_offpeak_dynamic_template_resampled_once_per_cycle`.                                                                                       |
| REQ-004 uniquement appareil actif      | **Partiel**        | Hors forçage, aucune consigne HC n'est émise. Mais un appareil inactif avec forçage vrai est activé (comportement #186 conservé, T4/T7 de la conception), ce qui contredit la lecture littérale de REQ-004 / AC-006 (voir F-6).                                                                                               |
| REQ-005 limites et temporisations      | Conforme (lecture) | Le forçage reste conditionné à `check_usable(False)` et aux compteurs ([managed_device.py L722-L745](../../custom_components/solar_optimizer/managed_device.py#L722)), non modifiés. Aucun test coordinateur pour `duration_power_min` / `max_on_time_*` (voir § 6).                                                          |
| REQ-006 sortie de plage                | Conforme (lecture) | Hors forçage, comparaison à la mesure (`current_power`) : une seule commande ([coordinator.py L329](../../custom_components/solar_optimizer/coordinator.py#L329)). Non testé.                                                                                                                                                 |
| REQ-007 appareils `switch`             | Conforme           | Garde `can_change_power` ; `test_offpeak_forcing_does_not_affect_switch_device` ; suite complète verte.                                                                                                                                                                                                                       |
| REQ-008 non-régression                 | Conforme (lecture) | Un appareil `enable=False` est exclu de la solution ([simulated_annealing_algo.py L117](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L117)) et donc de la boucle du coordinateur. Aucun test de surcharge manuelle en heures creuses ajouté.                                                           |
| REQ-009 pas de ré-émission             | **Partiel**        | Pas de ré-émission en état stable (`test_offpeak_forcing_no_reemission_when_already_applied`). Mais la comparaison au planning peut **supprimer** une émission nécessaire (F-1) et retire l'auto-correction par la mesure (F-2).                                                                                              |
| REQ-010 journalisation                 | **Partiel**        | Les logs `debug` existent ([L293](../../custom_components/solar_optimizer/coordinator.py#L293), [L301](../../custom_components/solar_optimizer/coordinator.py#L301), [L307](../../custom_components/solar_optimizer/coordinator.py#L307)) mais le motif « non applicable » se limite à `forcing` et `can_change_power` (F-5). |

### 4.2 Règles métier

| ID     | Verdict            | Preuve                                                                                                                                                                                                                     |
| ------ | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BR-001 | **Partiel**        | Même réserve que REQ-001.                                                                                                                                                                                                  |
| BR-002 | Conforme           | Le forçage active l'appareil sans dépendre de `state` ([coordinator.py L320-L325](../../custom_components/solar_optimizer/coordinator.py#L320)).                                                                           |
| BR-003 | Conforme           | Validation à l'initialisation ([managed_device.py L266-L272](../../custom_components/solar_optimizer/managed_device.py#L266)) et au runtime ; `test_offpeak_power_is_rejected_for_standard_device`, `test_config_flow.py`. |
| BR-004 | Conforme (lecture) | Limites et temporisation via `should_be_forced_offpeak` ; la valeur HC prime seulement quand le forçage est vrai.                                                                                                          |
| BR-005 | Conforme (lecture) | Fenêtre enroulante déjà gérée ([managed_device.py L736-L745](../../custom_components/solar_optimizer/managed_device.py#L736)), non modifiée ; tests existants de `test_min_on_time.py`.                                    |

### 4.3 Critères d'acceptation

| AC     | Verdict                               | Test (`tests/test_power_device.py`)                                                                                                         | Passe |
| ------ | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ----- |
| AC-001 | Partiel                               | `..._activates_inactive_device_with_setpoint`, `..._no_reemission_when_already_applied` (3 cycles, solution constante)                      | Oui   |
| AC-002 | Couvert                               | `..._overrides_active_algorithm_power`                                                                                                      | Oui   |
| AC-003 | Partiel                               | cas paramétré `None → 1000` ; un seul cycle, solution inactive                                                                              | Oui   |
| AC-004 | Couvert                               | cas paramétré `600`                                                                                                                         | Oui   |
| AC-005 | Couvert                               | `..._dynamic_template_resampled_once_per_cycle`                                                                                             | Oui   |
| AC-006 | **Non couvert**                       | aucun                                                                                                                                       | —     |
| AC-007 | **Non couvert** (niveau coordinateur) | décision seule dans `test_min_on_time.py`                                                                                                   | —     |
| AC-008 | **Non couvert**                       | aucun                                                                                                                                       | —     |
| AC-009 | **Non couvert**                       | aucun                                                                                                                                       | —     |
| AC-010 | Couvert                               | `..._does_not_affect_switch_device`                                                                                                         | Oui   |
| AC-011 | **Non couvert**                       | aucun (le contrat est vérifié par lecture uniquement)                                                                                       | —     |
| AC-012 | Couvert                               | `test_offpeak_power_is_rejected_for_standard_device`, `test_invalid_offpeak_power_template_does_not_interrupt_cycle`, `test_config_flow.py` | Oui   |
| AC-013 | Couvert                               | `..._no_reemission_when_already_applied`, `..._uses_planned_value_when_measurement_unavailable`                                             | Oui   |
| AC-014 | Partiel                               | `..._logs_decision` vérifie seulement « imposed » ; ni repli, ni « non applicable »                                                         | Oui   |

## 5. Constats

### Élevés (bloquants pour l'approbation)

**F-1 — Planning obsolète : consigne HC non émise à l'entrée du forçage (REQ-001, REQ-009)** — *vérifié par reproduction isolée.*
- Emplacement : [coordinator.py L329-L331](../../custom_components/solar_optimizer/coordinator.py#L329) combiné à [L343](../../custom_components/solar_optimizer/coordinator.py#L343).
- Cause : `device.requested_power` n'est mis à jour que par `activate`, `deactivate` et, désormais, le chemin de forçage. Hors forçage, un `change_requested_power` décidé par l'algorithme laisse le planning inchangé. À l'entrée du forçage, la comparaison au planning peut donc égaler la consigne HC alors que la puissance réelle est différente.
- Scénario reproduit (mocks, `offpeak_power=600`) : cycle 1 activation par l'algorithme à 600 (planning 600) ; cycle 2 l'algorithme baisse à 300 (émission 300, planning resté à 600) ; cycle 3 forçage vrai, mesure 300 : **aucune commande**, l'appareil reste à 300 pendant la plage. Résultat : `change_requested_power` attendu 1 fois avec 600, attendu 0 fois.
- Condition de déclenchement : planning obsolète égal à la consigne HC, par exemple appareil resté actif entre deux plages, dernier forçage à `offpeak_power` puis changement de puissance par l'algorithme. Le § 8.1 de la conception demandait de garder le planning aligné sur la valeur appliquée ; le code ne le fait que sous forçage. La matrice de conception (§ 7.3, « Entrée offpeak, appareil actif : 100 ≠ 600 ») suppose un planning fidèle qui n'est pas garanti.
- Correction recommandée : mettre à jour le planning à chaque `change_requested_power` effectif (hors forçage aussi), ou comparer la cible à la fois au planning et à la mesure quand la mesure est valide. Ajouter un test de ce scénario.

**F-2 — `README-fr.md` tronqué : environ 600 lignes perdues** — *vérifié.*
- Emplacement : commit `5dc4b08`. `main` : 857 lignes ; branche : 243 lignes (`git diff --numstat` : +5 / −619).
- Les sections « Exemples de configurations », « Configurer l'algorithme en mode avancé », « Entités disponibles », « La gestion de la priorité », « Les évènements », « Les actions », « Créer des modèles de capteur », « Carte Lovelace officielle » et « Les contributions » ont disparu ; le fichier s'arrête au paragraphe `offpeak_power`.
- Impact : régression documentaire majeure pour les utilisateurs francophones.
- Correction recommandée : restaurer `README-fr.md` depuis `main` puis y réappliquer uniquement la note de release et le paragraphe sur `offpeak_power`.

### Moyens

**F-3 — Mode `event` : la consigne HC n'est jamais transmise (REQ-001)** — *vérifié par reproduction isolée ; cause préexistante, effet aggravé.*
- Emplacement : [managed_device.py L330-L345](../../custom_components/solar_optimizer/managed_device.py#L330) : en mode `event`, `_announce_action` et `do_event_action` reçoivent `self._requested_power` (planning du cycle précédent) et non l'argument `requested_power`.
- Reproduction (appareil `event`, forçage vrai, planning 100, consigne HC 600) : événement émis avec `requested_power=100` ; le planning passe ensuite à 600 ; le cycle suivant n'émet plus rien. La valeur 600 n'est jamais envoyée.
- Impact : les intégrations pilotées par événement ne reçoivent jamais la consigne HC. Avant le correctif, l'événement portait déjà une mauvaise valeur, mais la comparaison à la mesure provoquait de nouvelles émissions.
- Correction recommandée : utiliser l'argument `requested_power` dans la branche `event` (et pour `_current_power` en fin de `_apply_action`), avec un test dédié. Décision à prendre : traiter dans cette issue ou dans une issue séparée.

**F-4 — Écart documentation / code sur les logs (REQ-010, AC-014)**
- Le paragraphe ajouté à [README.md L259](../../README.md#L259) et au README-fr annonce un log `debug` « non applicable » avec son motif (appareil inactif, temporisation, limite atteinte), émis « tant que le forçage est actif ». Le code journalise `forcing=%s, can_change_power=%s` ([coordinator.py L307](../../custom_components/solar_optimizer/coordinator.py#L307)), sans motif, et uniquement lorsque le forçage est faux.
- Correction recommandée : aligner le texte sur le comportement réel ou enrichir le log (cause : limite, temporisation, appareil non utilisable).

**F-5 — Perte d'auto-correction sous forçage (Q-004/Q-005, risque résiduel)**
- Comparer au planning plutôt qu'à la mesure est une décision utilisateur documentée. Conséquence : si la commande n'a pas été prise en compte par l'appareil ou si une automatisation tierce modifie la puissance (hypothèse H3 de la revue amont), Solar Optimizer ne corrige plus pendant le forçage. Risque accepté en principe ; à confirmer en connaissance de F-1.

**F-6 — Divergence spécification / conception sur l'appareil inactif (REQ-004, AC-006)**
- Spécifications : le système « n'active pas l'appareil pour appliquer la consigne HC ». Conception (T4, T7) et code : un appareil inactif avec forçage vrai est activé avec la consigne HC. Décision humaine requise ; aucun test AC-006.

**F-7 — Couverture de la matrice de conception insuffisante** (détail § 6).

### Faibles et observations

- **F-8** : 8 tests ont été ajoutés, et non 10 comme annoncé dans la demande de revue.
- **F-9** : `test_offpeak_setpoint_validation` ne teste que le repli `power_max` et l'alias ; aucune valeur invalide n'est vérifiée (nom trompeur par rapport à BR-003).
- **F-10** : le log « off-peak setpoint not applicable » est émis à chaque cycle pour chaque appareil hors forçage, y compris les `switch` ; bruit en niveau `debug`.
- **F-11** : les tests patchent `is_active` et `should_be_forced_offpeak` au niveau de la classe et fixent `_current_power` directement. Ils n'exercent donc ni l'horloge réelle, ni la fenêtre enroulante, ni `set_current_power_with_device_state`.
- **F-12** : [README.md](../../README.md) a perdu la phrase « Invalid values are reported by the form and are not saved… » (également absente de `README-fr.md`), et le titre « Creating Sensor Templates… » est passé de `#` à `##` sans lien avec l'issue. Les tableaux ont été réalignés (bruit de diff).

### Documentation et version

- Note de release « 3.9.1 » présente dans README.md et README-fr.md ; contenu cohérent entre les deux langues.
- [manifest.json](../../custom_components/solar_optimizer/manifest.json) indique toujours `3.9.0`, donc incohérent avec la note 3.9.1. Les tags du dépôt vont jusqu'à `3.10.1.beta1` alors que le manifeste de `main` reste à `3.9.0` : la numérotation de la note (3.9.1) est probablement obsolète. **Décision humaine requise** sur le numéro de version.

## 6. Matrice de conception T1-T14

| Réf. | Statut          | Test                                                               |
| ---- | --------------- | ------------------------------------------------------------------ |
| T1   | Partiel         | variante avec solution à 600, pas de test algo=100 / mesure=600    |
| T2   | Couvert         | `..._overrides_active_algorithm_power`                             |
| T3   | **Non couvert** | multi-cycles alternés                                              |
| T4   | Couvert         | `..._activates_inactive_device_with_setpoint`                      |
| T5   | Partiel         | cas paramétré, un cycle                                            |
| T6   | Couvert         | `..._dynamic_template_resampled_once_per_cycle`                    |
| T7   | Couvert         | cas paramétré existant (inactif, algo OFF)                         |
| T8   | **Non couvert** | `duration_power_min` en début de plage                             |
| T9   | **Non couvert** | `max_on_time_offpeak_min` (niveau coordinateur)                    |
| T10  | **Non couvert** | fenêtre enroulante                                                 |
| T11  | **Non couvert** | surcharge manuelle                                                 |
| T12  | Partiel         | test existant ; pas de bascule valide → invalide ni de log `error` |
| T13  | Partiel         | switch testé dans un cycle séparé (limite du patch de classe)      |
| T14  | Couvert         | `..._uses_planned_value_when_measurement_unavailable`              |

Bilan : 5 couverts, 4 partiels, 5 non couverts.

## 7. Revue de qualité

- **Points positifs** : changement localisé au point de sélection ; source de vérité unique `offpeak_setpoint` avec alias rétrocompatible ; `offpeak_power_configured` évite de dupliquer la logique de repli ; erreurs de configuration capturées sans interrompre le cycle ; aucune donnée sensible dans les logs ; commentaires brefs ; algorithme inchangé.
- **Synchronisation de `old_requested_power`** : correcte sous forçage (activation et changement, [L337-L339](../../custom_components/solar_optimizer/coordinator.py#L337)) ; non maintenue hors forçage (cause de F-1).
- **Edge cases** : appareil inactif (activation avec consigne HC) ; gabarit invalide (`error` + `continue`, appareil sauté, sa clé absente de `calculated_data`, comportement préexistant) ; mesure indisponible (planning utilisé) ; `switch` (garde `can_change_power`).
- **Régression `switch`** : non détectée (suite complète verte, branche non empruntée).

## 8. Risques résiduels

1. F-1 non corrigé : consigne HC non appliquée en heures creuses dans un scénario courant.
2. F-3 : appareils pilotés par événement non servis.
3. F-5 : absence de correction si la commande est perdue ou modifiée en externe.
4. R1 (conception) : divergence entre bilan de l'algorithme et puissance appliquée pendant le forçage, latence d'un cycle.
5. Cause réelle de l'incident #231 toujours non confirmée (H2/H3 non exclues) ; les tests sont une reproduction synthétique.
6. Comportement réel Home Assistant non vérifié (aucune recette).

## 9. Décisions humaines nécessaires

- Numéro de version et contenu de la note de release (3.9.1 vs tags 3.10.x).
- AC-006 : un appareil inactif avec forçage vrai doit-il être activé ? (aligner spécification ou conception).
- F-3 : correction du mode `event` dans cette issue ou séparément.
- F-5 : acceptation de la perte d'auto-correction sous forçage.

## 10. Actions de suivi (après autorisation)

1. Restaurer `README-fr.md` depuis `main` et y réappliquer la note et le paragraphe `offpeak_power` (F-2).
2. Corriger le planning obsolète (F-1) et ajouter le test de non-régression correspondant.
3. Statuer sur F-3 ; corriger `_apply_action` en mode `event` avec test.
4. Aligner les logs et la documentation (F-4) ; ajouter les tests AC-001 multi-cycles, AC-006, AC-007, AC-008, AC-009, AC-011 et T10, T12 (extension), T13.
5. Vérifier la version du manifeste et la note de release (§ 9).
6. Relancer `rtk pytest tests -q` puis soumettre une nouvelle revue.

## 11. Addendum du 2026-11-21 — corrections autorisées F-1 / F-2 / F-4

Cet addendum consigne uniquement les corrections explicitement autorisées sur `issue-231-offpeak-power`, HEAD `a5180a3`, référence `main` @ `3a0278c`. Les constats et validations ci-dessus restent l'historique de la revue initiale ; il ne s'agit ni d'une approbation globale ni d'une validation finale de l'issue.

- **F-1 corrigé** : [coordinator.py L337](../../custom_components/solar_optimizer/coordinator.py#L337) synchronise le planning après le succès de chaque `await change_requested_power`, y compris hors forçage. Comparaison au planning sous HC (Q-004/Q-005), comparaison à la mesure hors forçage, résolution unique de `offpeak_setpoint`, temporisations et branches activate/deactivate conservées. Un seul test ajouté au fichier existant : [test_power_device.py L211](../../tests/test_power_device.py#L211), activation à 600 → baisse algo à 300 hors HC → entrée HC à 600 → cycle stable sans émission ; commandes et planning vérifiés à chaque étape. Avant correction, échec au deuxième cycle : commande 300 envoyée mais planning 600 au lieu de 300 ; après correction, les quatre cycles passent. Aucun test existant remplacé.
- **F-2 corrigé** : fin de [README-fr.md L245](../../README-fr.md#L245) restaurée depuis `3a0278c`, sans remplacement du préfixe courant. Contrôle exact : 616 lignes ajoutées, texte restauré identique à la référence, 859 lignes au total ; note #231, paragraphe `offpeak_power` et tout contenu courant préservés hors phrase F-4. UTF-8 valide, 31 titres, 19 liens inline et 13 définitions de référence conservés ; les 11 cibles locales existent (pas de vérification réseau).
- **F-4 corrigé uniquement dans la documentation** : [README-fr.md L243](../../README-fr.md#L243) et [README.md L259](../../README.md#L259) décrivent les logs `debug` existants : consigne imposée, repli `power_max` sans `offpeak_power`, ou « non applicable » avec `forcing` et `can_change_power`. Les motifs inactif/temporisation/limites et la restriction de journalisation au seul forçage ne sont plus annoncés. Aucune extension des logs ; règle métier et comportement hors forçage/sortie de plage inchangés.

### Preuves exécutées

| Commande / contrôle                                                                                                                | Résultat                                                                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rtk pytest tests/test_power_device.py::test_offpeak_forcing_updates_planning_after_algorithm_power_change -q -p no:cacheprovider` | Avant correction : 1 échec (`600 != 300`, planning) ; après : 1 passé.                                                                                                             |
| `rtk pytest tests/test_power_device.py -q -p no:cacheprovider`                                                                     | 17 passés.                                                                                                                                                                         |
| `rtk pytest tests -q -p no:cacheprovider`                                                                                          | 189 passés, 0 échec, 11 ignorés.                                                                                                                                                   |
| `rtk proxy python -c ...` (contrôles documentaires en lecture seule)                                                               | Égalité stricte restauration/préfixe hors F-4, UTF-8, liens et concordance des trois messages de logs : validés. Une ligne vide manquante détectée puis rétablie avant validation. |
| `get_errors` sur les deux fichiers Python touchés                                                                                  | 94 diagnostics avant et après ; messages affichés préexistants (dont le typage de `set_requested_power`), aucun nouveau diagnostic observé.                                        |
| `rtk proxy git diff --check` ; état Git et diff Python                                                                             | Aucun défaut d'espaces ; périmètre limité au coordinateur, au seul test ajouté, aux deux README et au présent addendum.                                                            |

### F-3 et décisions restantes

**F-3 non corrigé, décision toujours en attente.** Lecture de [managed_device.py L332](../../custom_components/solar_optimizer/managed_device.py#L332), [do_event_action L116](../../custom_components/solar_optimizer/managed_device.py#L116) et [const.py L28](../../custom_components/solar_optimizer/const.py#L28), confirmée par `rtk proxy python -c ...` avec objet isolé et bus simulé, sans fichier ajouté ni instance HA : `change_requested_power(600)` avec planning initial 100 annonce et transmet encore 100. L'événement de commande est **`solar_optimizer_change_power_event`** ; champs : `action_type="ChangePower"`, `requested_power=100`, `current_power=100`, `entity_id` (aucun champ `power`). L'annonce distincte **`solar_optimizer_action`** ([L349](../../custom_components/solar_optimizer/managed_device.py#L349)) contient `device_name`, `entity_id`, `action`, `service` et `requested_power` ; en mode event, `service=None` et la valeur annoncée est également 100. En mode `action_call`, l'argument reçu est au contraire passé au service ([L322](../../custom_components/solar_optimizer/managed_device.py#L322)), puis à l'événement de confirmation ([L105](../../custom_components/solar_optimizer/managed_device.py#L105)). La synchronisation F-1 après l'await ne change pas ce payload event.

F-5, F-6/AC-006, les autres constats, l'extension de la matrice et les décisions de version restent non traités ; aucune décision supplémentaire n'est prise. Aucun changement d'algorithme, spécifications, dépendances, configuration ou environnement HA ; aucune branche, aucun commit, déploiement, rechargement ou redémarrage. La suite verte ne prouve ni la réception matérielle des commandes ni la résolution globale de l'issue.

## 12. Addendum du 2026-11-21 : correction autorisée F-3

Autorisation explicite dans ce tour : « Oui fait la correction F3. Garde le modèle GPT-6.1 Sol. » Le paramètre de modèle demandé est GPT-6.1 Sol ; ce rapport n'atteste pas le modèle effectivement exécuté. Travail sur `issue-231-offpeak-power`, sans sous-délégation. Cet addendum remplace uniquement le statut « F-3 non corrigé » du § 11 ; les autres constats restent l'historique de la revue. Les résultats rouges ci-dessous décrivent l'étape historique avant adaptation des assertions. **Validation finale après reprise (§ 13) : 201 passés, 0 échec, 11 ignorés ; aucune approbation globale.**

### Correction et causalité

- **F-3 corrigé dans le code** : trois substitutions dans [managed_device.py](../../custom_components/solar_optimizer/managed_device.py#L332). L'annonce `solar_optimizer_action` et la commande `solar_optimizer_change_power_event` utilisent désormais l'argument normalisé `requested_power`, et [l'affectation finale de `_current_power`](../../custom_components/solar_optimizer/managed_device.py#L347) conserve cette consigne après commande. Le repli `requested_power=None` vers le plan est inchangé ; `_apply_action` ne modifie pas `_requested_power`. Le coordinateur reste responsable du planning avec `set_requested_power` (correction F-1 préservée).
- **Régression avant/après** : [test_event_change_power_uses_explicit_setpoint](../../tests/test_power_device.py#L14) appelle réellement `change_requested_power(600)`, avec plan et puissance interne initiale à 100. Avant correction : échec sur l'annonce à 100 au lieu de 600. Après : annonce et commande à 600, payload `current_power=100`, `action_type="ChangePower"`, cible `input_boolean.fake_device_a` inchangée, contexte commun et annonce à l'origine du contexte ; puissance interne 600 et plan encore 100 après l'appel. Aucun mock de `_apply_action` ou `change_requested_power`.
- **Couverture complémentaire dans le fichier existant** : `test_apply_action_uses_normalized_setpoint` couvre les modes `event` et `action_call`, activation avec repli ou consigne explicite, désactivation à 0, changement de puissance avec repli ou consigne explicite. Annonces, payloads, contexte, puissance interne et plan vérifiés ; en mode service, appel simulé contrôlé avec cible et valeur attendues, sans preuve de réception ou de succès matériel.
- **Deux cycles HC** : `test_offpeak_event_setpoint_is_emitted_once` garde les vrais appels de commande et émissions du bus. Avec algorithme à 100, plan initial 100 et consigne HC 600, le premier cycle émet réellement 600 puis synchronise le plan à 600 ; le second n'émet ni annonce ni commande. Puissance interne et plan restent à 600, solution simulée de l'algorithme inchangée à 100. Les décisions HC/activité, la solution et la reconstruction de mesure sont simulées sur une seule instance ; ce n'est pas une recette de la fenêtre horaire ni du matériel.

### Preuves exécutées

| Commande / contrôle                                                                                                                                                                                          | Résultat réellement constaté                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `rtk pytest tests/test_power_device.py::test_event_change_power_uses_explicit_setpoint -q -p no:cacheprovider`                                                                                               | Avant correction : 1 échec (`requested_power=100` au lieu de 600). Après les trois substitutions : 1 passé ; après l'assertion explicite de présence du contexte : 1 passé.                                                                                                                                                          |
| `rtk pytest tests/test_power_device.py -q -p no:cacheprovider -k 'event_change_power_uses_explicit_setpoint or apply_action_uses_normalized_setpoint or offpeak_event_setpoint_is_emitted_once'`             | Premier essai complémentaire : 2 passés, 10 échecs de montage du mock (`ServiceRegistry.async_call` en lecture seule sur l'instance). Après utilisation du patch de classe existant dans les tests voisins : 12 passés.                                                                                                              |
| `rtk pytest tests/test_power_device.py tests/test_logbook.py -q -p no:cacheprovider`                                                                                                                         | 31 passés, 1 échec : `test_power_device`, assertion de puissance interne décrite ci-dessous.                                                                                                                                                                                                                                         |
| `rtk pytest tests -q -p no:cacheprovider`                                                                                                                                                                    | 200 passés, 1 échec, 11 ignorés. Référence documentée après F-1 : 189 passés, 11 ignorés ; les 12 nouveaux cas passent, un test antérieur devient incompatible avec le suivi interne corrigé.                                                                                                                                        |
| `get_errors` sur les deux fichiers Python touchés, avant et après                                                                                                                                            | 85 diagnostics initialement et au contrôle final. Un nouveau diagnostic temporaire du test (`last_context` potentiellement `None`) corrigé par assertion explicite ; aucun nouveau diagnostic final observé. Les diagnostics préexistants restent, dont le typage de `current_power` ; son union inférée inclut désormais `Unknown`. |
| `rtk proxy git diff --check` et diff Python                                                                                                                                                                  | Aucun défaut d'espaces ; production limitée aux trois substitutions F-3, tests uniquement ajoutés au fichier existant en plus du changement F-1 antérieur.                                                                                                                                                                           |
| `rtk proxy git diff --no-index --check /dev/null documentation/tech-docs/issue-231-post-dev-review.md` ; `rtk proxy head -n 209 documentation/tech-docs/issue-231-post-dev-review.md \| rtk proxy sha256sum` | Aucun défaut d'espaces du rapport non suivi ; les 209 lignes antérieures conservent exactement leur empreinte initiale `f486208e6b9e41ed6c7743d804f9b16a4fc9bb1aa2027db2e940fd443803607f`.                                                                                                                                           |
| `rtk proxy sha256sum README-fr.md README.md custom_components/solar_optimizer/coordinator.py documentation/tech-docs/issue-231-post-dev-review.md`                                                           | Avant ajout de cet addendum : les quatre empreintes sont identiques à celles du début de ce tour.                                                                                                                                                                                                                                    |
| `rtk proxy awk 'NR < 14 {print; next} /^@pytest.mark.parametrize\("offpeak_power, expected_power"/ {original=1} original {print}' tests/test_power_device.py \| rtk proxy sha256sum`                         | Hors nouveaux tests F-3, contenu strictement identique à l'état initial : `8440fcad93df382494346f184445e4e445fdaad36c1bd4924609e210e3a027bb`. Aucun test ou assertion antérieurs supprimés, modifiés ou ignorés.                                                                                                                     |

### Limite de validation et réserves (état historique avant reprise)

**État historique : la suite complète n'était pas verte. Validation finale après reprise (§ 13) : 201 passés, 0 échec, 11 ignorés.** [test_power_device](../../tests/test_power_device.py#L1055) attend encore `current_power == 0` après une commande à 500, alors que la correction autorisée de l'affectation finale donne 500. Cette assertion est laissée intacte pour respecter la préservation explicite des tests actuels ; aucune modification du code n'est ajoutée pour rétablir l'ancien comportement. Le test contient également une attente `current_power=0` pour le changement de puissance suivant l'activation : elle n'est pas atteinte dans cette exécution. L'adaptation de ces attentes liées au suivi interne demanderait de lever cette contrainte ; aucune compatibilité globale n'est revendiquée.

F-1/F-2/F-4 et toutes les modifications utilisateur préexistantes sont préservés, notamment les deux README dans leur état au début de ce tour. Aucune correction des temporisations ou cibles event, de F-5, F-6/AC-006, des autres constats ou de la matrice globale. Aucun changement de configuration, état HA, dépendances, version, spécifications, conception ou algorithme ; aucune instance HA réelle, branche, commit, migration, déploiement, rechargement ou redémarrage. F-5, R1 et l'attribution de l'incident restent ouverts ; émission sur le bus de test ne signifie ni réception matérielle ni succès d'une commande externe.

## 13. Suivi du 2026-11-21 : validation finale F-3 après adaptation autorisée des assertions

**Résultat final mesuré : 201 passés, 0 échec, 11 ignorés. L'échec local de `test_power_device` est résolu ; aucune approbation globale de l'issue.** Les échecs et contrôles du § 12 restent les preuves historiques, et non l'état courant.

L'autorisation est clarifiée : préserver les tests existants interdit leur suppression, leur remplacement ou l'affaiblissement de leur couverture, mais autorise l'adaptation des assertions qui codifiaient le bug F-3. Le modèle demandé reste GPT-6.1 Sol ; le modèle exécuté ne peut pas être attesté ici. Aucun sous-agent n'a été lancé lors de cette reprise.

### Assertions adaptées et sémantique conservée

- [Puissance interne du résultat](../../tests/test_power_device.py#L1056) : `calculated_data["power_device_a"].current_power` attend désormais 500, et non 0. Après activation à 500, [l'affectation finale de `_apply_action`](../../custom_components/solar_optimizer/managed_device.py#L347) conserve l'argument normalisé de la commande, plutôt que le planning encore à 0 avant la synchronisation du coordinateur.
- [Payload du changement de puissance](../../tests/test_power_device.py#L1092) : `current_power` attend désormais 500. Cet événement est émis immédiatement après l'activation, lorsque la puissance interne vaut déjà 500 ; sa consigne reste 500.
- L'événement d'activation conserve `current_power=0`, car il précède la mise à jour interne. `best_solution[0]["current_power"]` conserve aussi 0, car il s'agit du snapshot algorithmique préactivation. Cibles, services, contextes, méthodes, nombre d'événements et autres assertions sont inchangés. Aucun test retiré, remplacé, ignoré ou rendu moins strict.

### Validations exécutées lors de la reprise

| Commande / contrôle                                                                  | Résultat réellement constaté                                                                                                                                                                            |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rtk pytest tests/test_power_device.py::test_power_device -q -p no:cacheprovider`    | 1 passé, immédiatement après l'adaptation des deux assertions.                                                                                                                                          |
| `rtk pytest tests/test_power_device.py tests/test_logbook.py -q -p no:cacheprovider` | 32 passés, 0 échec.                                                                                                                                                                                     |
| `rtk pytest tests -q -p no:cacheprovider`                                            | **201 passés, 0 échec, 11 ignorés.**                                                                                                                                                                    |
| `get_errors` sur `test_power_device.py` et `managed_device.py`                       | 85 diagnostics, comme au dernier contrôle du § 12 ; aucun nouveau diagnostic observé sur les deux assertions modifiées. Les diagnostics de typage préexistants ne sont pas corrigés dans cette reprise. |

Modifications propres à cette invocation : exactement deux valeurs d'assertion dans le test existant et le présent suivi documentaire, avec signalement du résultat final auprès de l'état rouge historique. Les trois substitutions F-3 en production et les 12 cas ajoutés précédemment restent inchangés, tout comme F-1/F-2/F-4 et les modifications utilisateur des README, notamment README-fr. Aucun autre code, commentaire inline, algorithme, spécification, conception, configuration, dépendance, version ou environnement HA modifié ; aucune branche, aucun commit, déploiement, rechargement ou redémarrage.

F-5, F-6/AC-006, les décisions de version et les autres réserves restent non traités. La suite verte valide les scénarios de test, pas la réception matérielle des commandes ni la résolution globale de l'issue.
