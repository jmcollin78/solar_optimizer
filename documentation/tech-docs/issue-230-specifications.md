# Specifications fonctionnelles - Issue #230

## 1. Statut et sources

- Reference : [issue #230](https://github.com/jmcollin78/solar_optimizer/issues/230).
- Date : 2026-11-21. Revue et specifications approuvees par l'utilisateur ; developpement autorise.
- Source fonctionnelle : [revue approuvee](issue-230-review.md), propositions A + F, et decisions utilisateur recueillies pendant la specification.
- Decisions confirmees : separation des allumages/arrets uniquement ; report egalement des activations forcees HC ; aucun capteur individuel obligatoire ; aucune attente de nouvelle mesure globale.
- Sources techniques : [coordinateur](../../custom_components/solar_optimizer/coordinator.py), [recuit](../../custom_components/solar_optimizer/simulated_annealing_algo.py), [appareil gere](../../custom_components/solar_optimizer/managed_device.py), [tests de puissance](../../tests/test_power_device.py), [tests de duree minimale](../../tests/test_min_on_time.py) et [tests d'activation temporisee](../../tests/test_timed_activation.py).
- Langues : contrat principal francais ; synthese normative anglaise en section 8, avec les memes identifiants.

## 2. Objectif et perimetre

Empecher qu'un appareil soit allume grace a une economie fictive obtenue par l'arret simule d'un autre appareil, notamment un chauffe-eau actif dont la resistance ne consomme plus ou dont l'arret est interdit par le forcage HC.

La correction combine deux mecanismes : maintenir les appareils actifs forces HC dans les candidats du recuit ; separer les arrets et les allumages effectifs entre cycles. Elle ne cherche pas a deduire exactement la consommation individuelle sans mesure.

Inclus : preparation des candidats HC, decision d'application du plan complet, activations ordinaires et forcees HC, arrets deja commandes pendant le cycle, recalcul au cycle suivant et diagnostic des activations ecartees.

Exclus : utilisation de `measured_power_entity_id` par le recuit, nouveau schema de configuration, attente ou frequence imposee de mesure, apprentissage de consommation, modele probabiliste, nouveau solveur, refonte des priorites, carte Lovelace et nouvelles regles de compteur journalier. La mesure individuelle pourra etre une evolution facultative ulterieure.

Les diminutions et augmentations de puissance d'un appareil qui reste actif ne sont pas assimilees a des arrets/allumages. Les transferts incertains par variation de consigne restent donc une limite connue, hors correction binaire de cette issue.

## 3. Definitions

| Terme               | Definition fonctionnelle                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cycle               | Une execution du rafraichissement du coordinateur, y compris le traitement initial des expirations de timers et l'application du plan.            |
| Etat observe        | Etat actif/inactif issu du mecanisme existant de l'appareil ; il ne prouve pas une consommation physique non nulle.                               |
| Forcage HC effectif | Decision `should_be_forced_offpeak`, avec ses conditions existantes d'utilisabilite, de duree et d'horaire ; ce n'est pas toute la plage horaire. |
| Arret admissible    | Commande actif -> inactif autorisee apres application des contraintes ; une baisse de puissance conservant l'etat actif n'en est pas un.          |
| Activation          | Commande inactif -> actif, qu'elle provienne du recuit ou du forcage HC. Le maintien d'un appareil actif n'en est pas une.                        |
| Activation ecartee  | Activation non commandee dans ce cycle ; ce n'est ni une activation appliquee ni une commande a rejouer automatiquement.                          |
| Plan calcule        | Resultat brut du recuit, avec son objectif et son total de puissance nominale.                                                                    |
| Plan d'application  | Decisions effectives apres contraintes HC et separation des arrets/allumages. Il peut differer du plan calcule.                                   |

## 4. Regles de gestion

### RG-001 - Compatibilite sans mesure individuelle

Aucun capteur individuel, champ requis ou migration ne doit etre ajoute pour beneficier de la correction. Le capteur d'affichage existant conserve son contrat. Les configurations sans capteur et les installations mixtes doivent rester utilisables.

### RG-002 - Aucune attente du compteur

Le cycle et les cycles suivants utilisent les valeurs disponibles selon le fonctionnement actuel. Aucun rafraichissement, delai minimal, delai maximal de confirmation ou nouvelle frequence de mesure n'est impose. Les conditions existantes d'abandon lorsque les donnees globales indispensables sont invalides restent applicables.

### RG-003 - Decision HC coherente dans un cycle

Les faits utilises pour calculer puis appliquer le plan doivent etre coherents : etat observe, forcage HC, possibilites de commande et consigne HC. La consigne dynamique HC doit conserver son echantillonnage existant une fois par cycle. Un changement de contrainte detecte avant une commande doit etre revalide, sans autoriser une activation financee par un arret devenu interdit.

### RG-004 - Interdiction d'arret simule pendant le forcage HC

Pour un appareil gere, actif et effectivement force HC, l'etat doit rester actif dans la solution initiale, les voisins admissibles et la meilleure solution. Le recuit ne doit ni le representer comme inactif pour l'exclure ni simuler son arret pour liberer son budget.

Pour un appareil variable force HC, la consigne candidate doit respecter la consigne HC effective deja prevue par le coordinateur ; le recuit ne doit pas compter sur une consigne qu'il ne pourra pas appliquer. Cela ne doit pas reintroduire de variation ou de re-emission abusive corrigee pour #231.

### RG-005 - Reference de puissance avant les commandes

La reference de comparaison doit conserver l'etat et la puissance de planification observes avant l'application des nouvelles commandes. Une charge fixe active et inchangee contribue de facon constante : elle ne libere rien entre reference et candidats. L'allumage d'une charge initialement inactive ou le passage a une nouvelle consigne HC ne doit pas etre masque par une reference reconstruite comme si la commande avait deja ete appliquee.

Il ne faut ni soustraire deux fois une charge deja incluse dans la mesure globale ni convertir une absence de mesure individuelle en consommation nulle. Le budget nominal reste une estimation, pas une mesure physique.

### RG-006 - Decision sur le plan complet avant application

Avant toute activation issue du plan, le systeme doit identifier tous les arrets admissibles du cycle, quel que soit l'ordre des appareils. Le resultat ne doit pas dependre de la position de l'appareil a arreter dans la liste. Un appareil deja inactif avec une cible inactive ne constitue pas un arret.

### RG-007 - Aucune activation dans un cycle comportant un arret

Si au moins un arret admissible doit etre commande, toutes les activations du cycle doivent etre ecartees. Les arrets restent commandes selon les contraintes existantes. Le maintien des autres appareils deja actifs reste autorise.

La regle est stricte : une activation forcee HC d'un appareil initialement inactif est egalement ecartee. Elle pourra etre redeterminee au cycle suivant. La presence d'un capteur individuel ne dispense pas de cette regle.

### RG-008 - Arrets precedant le recuit et erreurs de commande

Un arret commande plus tot dans le meme cycle, notamment par expiration d'une activation temporisee, doit aussi interdire les activations ulterieures de ce cycle. Le recalcul apres cet arret ne doit pas effacer cette information.

Le blocage des activations est decide avant les tentatives d'arret. L'echec d'un arret ou son retour d'etat retarde ne doit pas rouvrir les activations dans ce cycle. La gestion existante des exceptions de service ne doit pas etre remplacee par une simulation de succes.

### RG-009 - Pas de commande associee a une activation ecartee

Un appareil variable dont l'activation est ecartee ne doit recevoir ni activation ni commande de puissance liee a cette activation, y compris en forcage HC. Sa consigne planifiee et ses temporisations ne doivent pas etre mises a jour comme si l'activation avait eu lieu. Aucun evenement d'action appliquee ne doit etre emis pour cette activation non executee.

### RG-010 - Portee binaire et contraintes existantes

Les changements de puissance des appareils restant actifs conservent leurs regles actuelles, y compris lorsque le cycle comporte un arret d'un autre appareil. Si une decision conduit effectivement a l'extinction, elle est classee comme arret, meme pour un appareil variable.

La correction ne doit pas contourner les durees minimales, les limites quotidiennes, les conditions d'utilisabilite, les commandes manuelles, les desactivations de gestion ou les protections de l'appareil. Apres cessation du forcage HC effectif, l'optimisation normale reprend avec RG-007 toujours applicable.

### RG-011 - Nouveau calcul, pas de replay

Au cycle habituel suivant, les candidats et la reference sont reconstruits depuis les etats effectivement observes. Aucune liste d'activations ecartees n'est rejouee. Si l'arret du chauffe-eau est observe, son budget initial devient zero, meme si la mesure nette est inchangee.

Si l'arret n'est pas encore observe, le systeme ne doit pas fabriquer un etat inactif pour accrediter une economie. Les cycles continuent normalement ; une nouvelle decision d'arret admissible maintient le blocage selon RG-007. Aucun delai de confirmation impose n'est ajoute.

### RG-012 - Plans et diagnostic distincts

Le resultat brut du recuit ne doit pas etre modifie silencieusement pour representer les commandes appliquees. Les champs existants `best_solution`, `best_objective` et `total_power` conservent leur sens de resultat du recuit ; leur compatibilite doit etre preservee.

Le diagnostic du cycle doit distinguer les actions commandees des activations ecartees, avec le motif de separation des cycles. Il ne doit pas presenter l'objectif du plan mixte comme celui des commandes reellement appliquees, ni une consigne nominale comme une consommation mesuree. Reutiliser les journaux ou attributs adaptes existants ; aucun changement de carte n'est requis.

### RG-013 - Pas d'arret, comportement d'activation conserve

En l'absence d'arret du cycle, les activations ordinaires et forcees HC restent autorisees selon leurs conditions habituelles. La correction n'interdit pas un allumage legitime d'un appareil sans configuration HC lorsque l'objectif le justifie.

## 5. Criteres d'acceptation

| ID     | Scenario et resultat attendu                                                                                                                                                                                                          | Regles                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| AC-001 | Chauffe-eau fixe 2 400 W actif force HC, radiateur 1 000 W inactif, import net 1 500 W, production 8 W, sans mesure individuelle : le recuit ne propose pas l'arret du chauffe-eau et aucune activation du radiateur n'est commandee. | RG-001, RG-004, RG-005         |
| AC-002 | Meme scenario hors forcage, plan proposant arret du chauffe-eau et activation du radiateur : seule la commande d'arret est appliquee. Les deux ordres de liste donnent le meme resultat.                                              | RG-006, RG-007                 |
| AC-003 | Plusieurs arrets et activations, avec des appareils maintenus actifs : les arrets sont commandes, les activations ecartees, les maintiens preserves.                                                                                  | RG-006, RG-007                 |
| AC-004 | Un arret accompagne une activation forcee HC : activation HC ecartee dans ce cycle, y compris sa commande de puissance associee. Sans arret, elle est autorisee.                                                                      | RG-007, RG-009, RG-013         |
| AC-005 | Un timer provoque une commande d'arret avant le recuit : une activation proposee ensuite reste ecartee.                                                                                                                               | RG-008                         |
| AC-006 | Un arret echoue ou son etat tarde a revenir : aucune activation n'est liberee dans le cycle ; aucune reussite ou puissance liberee n'est fabriquee.                                                                                   | RG-008, RG-011                 |
| AC-007 | Au cycle suivant l'arret observe, mesure nette toujours a 1 500 W : budget initial du chauffe-eau zero ; aucun replay du radiateur et aucun allumage finance par les anciens 2 400 W. Le calcul n'attend pas de mesure nouvelle.      | RG-002, RG-005, RG-011         |
| AC-008 | Plan sans arret : les allumages habituels restent possibles, meme si un appareil deja inactif a encore une cible inactive.                                                                                                            | RG-006, RG-013                 |
| AC-009 | Appareil variable deja actif : baisse ou hausse de consigne seule ne declenche pas RG-007 ; une vraie extinction le fait. Un allumage ecarte ne recoit aucune commande de puissance.                                                  | RG-009, RG-010                 |
| AC-010 | Entree/sortie HC, minimum quotidien atteint, temporisations, override et appareil desactive : maintien des contrats existants et absence de blocage au-dela du forcage effectif. Consigne HC et reference restent coherentes.         | RG-003, RG-004, RG-005, RG-010 |
| AC-011 | Capteur individuel absent, present ou indisponible : configuration acceptee sans modification et memes regles de separation ; pas d'utilisation nouvelle du capteur d'affichage.                                                      | RG-001, RG-007                 |
| AC-012 | Plan brut mixte filtre : plan brut inchange, diagnostic des activations ecartees distinct, aucune action appliquee annoncee pour une activation bloquee.                                                                              | RG-009, RG-012                 |

Les tests utilisent des entites et services simules de l'environnement HA de test, jamais l'installation reelle. La correction limite une decision fondee sur une economie fictive ; elle ne garantit pas l'absence de tout import lorsque les mesures sont perimees ou que les charges changent spontanement.

## 6. Realisation en taches unitaires

L'ordre ci-dessous est obligatoire pour T01 : **d'abord constater le rouge, ensuite corriger, puis obtenir le vert sans affaiblir les assertions du test de regression**. Les autres tests sont ajoutes avant ou avec la petite correction qu'ils encadrent. Les noms proposes ne designent pas des tests deja crees ou executes.

### T01 - Ecrire et constater le test de regression rouge

- Surface : [tests de puissance](../../tests/test_power_device.py), en reutilisant `init_solar_optimizer_central_config`, `create_managed_device` et les helpers d'entites de test.
- Ecrire `test_issue_230_no_activation_from_phantom_released_power`, avec deux variantes : chauffe-eau force HC et chauffe-eau non force. Entites initiales : chauffe-eau actif de 2 400 W, radiateur inactif de 1 000 W ; aucun capteur individuel. Fixer l'heure, les durees et les disponibilites pour isoler ces variantes.
- Executer le vrai `recuit_simule` via le vrai cycle du coordinateur. Import net 1 500 W, solaire 8 W, batterie neutre, achat 0,25, vente 0,10, taxe zero et poids de priorite zero. Neutraliser uniquement le lissage dans ce scenario pour conserver la production de 8 W.
- Rendre le recuit deterministe avec deux iterations : selection de l'arret du chauffe-eau lorsqu'il est un candidat admissible, puis du radiateur. Si le chauffe-eau devient verrouille apres correction, le selecteur doit choisir un candidat encore admissible au lieu de lever une erreur. Fixer aussi le tirage d'acceptation des voisins moins bons. Ne pas remplacer le recuit par un resultat fabrique ni modifier sa fonction objectif.
- Collecter les commandes ou evenements apres initialisation. Assertion centrale : **aucune commande d'activation du radiateur**. Variante HC : chauffe-eau maintenu actif et aucun arret commande. Variante non HC : commande d'arret du chauffe-eau attendue et radiateur maintenu inactif.
- Executer ce test avant toute correction de production et conserver la sortie d'echec. Le rouge attendu est une assertion sur l'activation indebite du radiateur, pas une erreur de fixture, de selection aleatoire ou de service. Si le test passe deja, investiguer la baseline avant de commencer la correction.
- Commande ciblee : `rtk pytest tests/test_power_device.py -q -k issue_230_no_activation_from_phantom_released_power`.
- Sortie de tache : test rouge reproductible, non ignore et non marque `xfail`. Le meme test doit passer apres T03 et T05 ; ne pas retirer les assertions, les variantes ou remplacer la reproduction reelle par un mock de recuit pour le rendre vert.

### T02 - Preparer une decision coherente pour le cycle

- Identifier les faits necessaires avant l'application du plan : etats observes, contraintes HC, consigne effective et arrets deja commandes dans ce cycle. Reutiliser les abstractions existantes ; ne pas creer de cadre de planification general.
- Tests unitaires : faits communs au calcul et a l'application ; gabarit HC echantillonne une seule fois ; arret initial memorise sans faire disparaitre son effet sur les activations suivantes.
- Criteres : RG-003 et RG-008. Cette tache ne pretend pas encore rendre toutes les variantes de T01 vertes.

### T03 - Verrouiller les candidats HC et conserver une reference correcte

- Corriger la preparation des equipements et la selection de voisins dans le [recuit](../../custom_components/solar_optimizer/simulated_annealing_algo.py), sans changer le solveur ni inventer une consommation mesuree.
- Tests unitaires : charge fixe active forcee inchangee ; variante variable a consigne HC ; entree HC d'un appareil initialement inactif ; nouvelle consigne HC comptee depuis la reference observee ; sortie du forcage ; candidat HC actif meme si son budget courant vaut zero.
- Criteres : AC-001 et partie algorithmique d'AC-010. La variante HC de T01 doit devenir verte ; la variante hors HC peut rester rouge jusqu'a T05.

### T04 - Decider la separation sur l'ensemble du plan

- Introduire la plus petite decision testable permettant de classifier arret, activation, maintien et variation de puissance avant toute commande. Tenir compte d'un arret deja commande plus tot dans le cycle.
- Tests unitaires parametrises : ordre arret/activation et ordre inverse ; plusieurs arrets ; cible inactive d'un appareil deja inactif ; maintien ; activation HC ; baisse/hausse de consigne sans extinction.
- Criteres : AC-002, AC-003, AC-008 et classification d'AC-009. Decision identique independamment de l'ordre de la liste et sans muter le resultat brut du recuit.

### T05 - Appliquer les arrets et ecarter toutes les activations du cycle

- Brancher la decision T04 dans le [coordinateur](../../custom_components/solar_optimizer/coordinator.py). Ne pas se contenter d'un drapeau modifie au fil de la boucle de commandes.
- Tests unitaires de commandes : aucune activation ordinaire ou HC dans un cycle avec arret ; activations possibles sans arret ; appareil variable bloque sans `activate` ni `change_requested_power`, sans mise a jour fictive de consigne ou temporisation.
- Criteres : AC-002 a AC-004, AC-008 et AC-009. **Les deux variantes inchangees de T01 doivent maintenant etre vertes.**

### T06 - Verifier le recalcul au cycle suivant sans mesure nouvelle

- Ajouter un test de deux cycles dans le fichier de test deja utilise. Apres la commande d'arret du premier cycle, simuler explicitement son retour d'etat ; conserver la mesure nette a 1 500 W au second cycle.
- Verifier : budget initial du chauffe-eau zero, aucune execution automatique de l'ancienne activation, aucun allumage fictivement finance et absence d'attente du compteur. Tester aussi un nouveau plan legitime sans arret pour eviter un blocage permanent.
- Criteres : AC-007 et AC-008. Reutiliser le vrai recuit pour le scenario de reference ; un resultat controle est permis pour isoler uniquement l'absence de replay.

### T07 - Couvrir les expirations, echecs et retours d'etat lents

- Reutiliser les [tests temporises](../../tests/test_timed_activation.py) pour un arret avant recuit et les helpers locaux pour simuler une erreur d'arret ou un etat restant actif.
- Verifier que le blocage tient dans le cycle courant, que l'exception conserve son traitement existant et que le cycle suivant observe l'etat reel sans fabriquer un succes ni exiger une mesure fraiche.
- Criteres : AC-005 et AC-006. Aucune nouvelle commande materielle ou temporisation de confirmation.

### T08 - Distinguer les activations ecartees du plan brut

- Ajouter ou reutiliser un diagnostic approprie du coordinateur sans changer la carte ni la signification des champs existants du recuit.
- Tests unitaires : plan calcule inchange apres filtrage ; motif de blocage identifiable ; absence d'annonce d'activation appliquee et de consigne planifiee nouvelle pour un appareil bloque.
- Criteres : AC-012. Les diagnostics ne doivent pas attribuer au plan applique le cout du plan mixte non execute.

### T09 - Verifier les frontieres et la compatibilite

- Completer les fichiers existants plutot que dupliquer les fixtures : debut/fin du forcage, limites quotidiennes, temporisations, appareils desactives, override, consignes variables HC, modes service/evenement et capteur d'affichage absent/present/indisponible.
- Criteres : AC-009 a AC-011, avec preservation des acquis #231. Ne pas ajouter l'exploitation algorithmique du capteur individuel.
- Executer les tests touches, puis la suite configuree : `rtk pytest tests -q -p no:cacheprovider`. Tout echec hors perimetre doit etre rapporte, pas contourne ni corrige sans analyse.

### T10 - Documenter le comportement et clore la correction

- Mettre a jour les [instructions utilisateur francaises](../../README-fr.md) et [anglaises](../../README.md) : aucune mesure individuelle requise, pas d'allumage lors d'un cycle avec arret, HC initialement inactif egalement reporte, cout d'au moins un cycle pour un remplacement de charge et limite des variations de puissance.
- Verifier les liens documentaires, la coherence FR/EN et la tracabilite des AC. Joindre la preuve rouge initiale de T01 et sa preuve verte finale.
- Aucun changement de version, commit, publication, configuration HA ou recette materielle n'est implique sans autorisation distincte.

### Dependances et portes de validation

| Etape | Dependances                               | Preuve minimale                                                    |
| ----- | ----------------------------------------- | ------------------------------------------------------------------ |
| T01   | Aucune correction de production prealable | Echec d'assertion attendu et reproductible sur les deux variantes. |
| T02   | T01 rouge etabli                          | Tests des faits de cycle et du forcage.                            |
| T03   | T02                                       | Tests de verrouillage et reference ; variante HC de T01 verte.     |
| T04   | T02                                       | Tests de classification, sans commandes.                           |
| T05   | T03, T04                                  | T01 entierement vert et tests de commandes.                        |
| T06   | T05                                       | Deux cycles sans mesure nouvelle et sans replay.                   |
| T07   | T05                                       | Expiration, echec et retour d'etat lent.                           |
| T08   | T05                                       | Diagnostic distinct du resultat brut.                              |
| T09   | T06, T07, T08                             | Tests touches et suite complete, ecarts documentes.                |
| T10   | T09                                       | Documentation coherente et preuves rouge/vert conservees.          |

## 7. Definition de termine

La correction est terminee lorsque les AC-001 a AC-012 sont verifies, T01 a ete observe rouge puis vert sans affaiblissement, les configurations existantes restent valides, les tests touches et les controles du depot sont passes ou leurs blocages explicitement rapportes, et la documentation FR/EN explique la nouvelle separation et ses limites. Aucun succes d'une reproduction synthetique ne remplace les tests du vrai chemin coordinateur/recuit.

Les essais exposes dans la revue sont des preuves exploratoires anterieures. T01 a ensuite ete observe rouge sur les variantes avec et sans forcage HC avant toute correction de production, puis vert dans les quatre combinaisons de forcage et d'ordre des appareils. Les tests de cycles, d'expiration, d'echec de commande, de diagnostic et de variation de puissance ont ete ajoutes. La suite complete compte 213 tests passes, aucun echec et 11 ignores ; le bilan est consigne dans la revue de developpement.

## 8. English normative summary

Status: the review and specifications are approved; development is authorized. T01 was observed failing on both off-peak and ordinary variants before the production fix, then passing with both device orders. Scope: combine active off-peak constraints with cycle-wide start/stop separation. Individual power measurements remain optional and are not newly consumed by the algorithm. No fresh-meter wait is introduced.

| Rule   | English contract                                                                                                                                        |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RG-001 | Existing configurations must work without an individual consumption sensor; the display sensor contract is unchanged.                                   |
| RG-002 | Use available global readings without waiting for an update; preserve existing invalid-input handling.                                                  |
| RG-003 | Optimization and application must use consistent cycle facts and a single effective off-peak setpoint evaluation.                                       |
| RG-004 | An active device under effective off-peak forcing must remain active in initial, neighboring and best solutions; honor its applicable setpoint.         |
| RG-005 | Preserve the observed planning baseline before new commands; unchanged locked loads cancel out and new loads must not disappear into the baseline.      |
| RG-006 | Classify the whole plan before commands; results must be independent of device order.                                                                   |
| RG-007 | Any admissible stop forbids every start in that cycle, including forced off-peak starts; existing active devices may remain active.                     |
| RG-008 | Stops commanded earlier in the cycle also count; a failed stop or delayed state report must not reopen blocked starts.                                  |
| RG-009 | A blocked start must not issue its associated power command, applied-action event or fictitious planning/timer update.                                  |
| RG-010 | Power changes on devices remaining active are outside the binary restriction; actual turn-offs count as stops and existing protections remain in force. |
| RG-011 | Recalculate from observed states next cycle without replaying skipped starts or waiting for fresh power readings.                                       |
| RG-012 | Preserve raw optimizer result semantics and separately diagnose commanded and skipped actions.                                                          |
| RG-013 | With no stop in the cycle, ordinary and forced off-peak starts follow their existing eligibility rules.                                                 |

Acceptance IDs AC-001 to AC-012 in section 5 are authoritative in both languages. Delivery tasks T01 to T10 and their dependencies are shared: first commit to a deterministic failing regression test of the real optimizer/coordinator path, then make the unchanged test pass through small, independently tested corrections. T01 covers both forced-off-peak and ordinary-stop variants. It must fail on the unwanted radiator start, not on an artificial mock or setup error, and must not be skipped or marked as an expected failure.

Confirmed decisions: start/stop separation does not extend to power increases/decreases on devices remaining active; a forced off-peak start is also postponed when the cycle contains a stop. Trade-offs: a valid device replacement takes at least one extra cycle; repeated stops may postpone starts further. Stale measurements and spontaneous load changes remain limitations, so this is not a guarantee against every grid import.