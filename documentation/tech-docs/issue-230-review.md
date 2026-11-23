# Rapport d'analyse de l'issue #230

## 1. Conclusion

**Le signalement est pertinent et son mecanisme est reproduit dans le code local. Deux problemes doivent cependant etre separes : une solution HC non executable, et une consommation individuelle inconnue.**

Le premier peut etre corrige sans capteur individuel : l'optimiseur ne doit pas simuler l'arret d'un appareil que le coordinateur maintiendra allume. Une charge deja active et verrouillee contribue de facon constante au bilan ; sa puissance nominale s'annule entre la reference et les solutions candidates.

Le second ne peut pas etre resolu exactement avec les seules informations actuellement utilisees. Un contacteur ferme ne prouve pas qu'une resistance chauffe. Il faut une mesure ou une information supplementaire pour connaitre cette consommation, ou limiter les decisions qui dependent d'une economie incertaine sans chercher a la mesurer.

**Recommandation revisee : combiner le verrouillage des appareils actifs forces HC avec l'interdiction d'activer un appareil dans un cycle comportant l'arret d'un autre.** Cette piste proposee par l'utilisateur ne requiert ni capteur individuel ni attente d'une nouvelle mesure globale. La mesure individuelle reste une amelioration facultative. La confirmation par mesure globale est ecartee comme solution de base en raison de delais trop dependants de l'installation.

Revue approuvee par l'utilisateur le 21 novembre 2026 ; les [specifications et taches unitaires](issue-230-specifications.md) ont ensuite ete approuvees et le developpement autorise. Au moment de cette revue initiale, aucun code de production, test existant ou parametre Home Assistant n'avait ete modifie.

## 2. Sources et perimetre

- [Issue #230](https://github.com/jmcollin78/solar_optimizer/issues/230), ouverte par @jmcollin78 : un arret simule libere la puissance configuree meme si l'appareil ne consomme rien ; un autre appareil peut alors etre active, notamment pendant les HC sans disposer lui-meme d'un forcage HC. Aucun commentaire n'a ete renvoye par l'outil GitHub.
- [PR #228](https://github.com/jmcollin78/solar_optimizer/pull/228), de @quentinFch : exemple d'un chauffe-eau de 2 400 W, active mais a temperature, avec 1 500 W de consommation indiquee et 8 W de production. Proposition d'exclusion des appareils forces en HC.
- [PR #229](https://github.com/jmcollin78/solar_optimizer/pull/229), de @jmcollin78 : annulation de #228. Son texte n'explique pas les raisons techniques de l'annulation ; ne pas les deduire du seul revert.
- Revision locale examinee : `bc3697d`, branche `230-do-not-liberate-power-when-a-device-is-turned-off-and-doesnt-consume-power`, arbre initialement propre. Le [manifeste](../../custom_components/solar_optimizer/manifest.json) annonce 3.9.0 ; cela ne renseigne pas la version installee chez le declarant.
- La branche contient deja des evolutions relatives a #231. Les constats ci-dessous portent sur cette revision locale, pas sur une installation historique reconstituee.

Dans le code, la consommation du logement est une **puissance nette reseau**, positive a l'import et negative a l'export, comme indique dans le [README](../../README-fr.md#L175). La reproduction interprete donc les 1 500 W comme un import net. Si le chiffre du declarant designe une consommation brute, il faut le convertir avant comparaison.

## 3. Mecanisme verifie

### 3.1 Puissance nominale, consigne et mesure sont distinctes

La [reconstruction de la puissance courante](../../custom_components/solar_optimizer/managed_device.py#L449) attribue `power_max` a un appareil fixe actif sans `power_entity_id`. Un chauffe-eau actif de puissance nominale 2 400 W est donc represente a 2 400 W, meme lorsque son thermostat coupe la resistance.

Le [schema de configuration](../../custom_components/solar_optimizer/config_schema.py#L76) propose deja `measured_power_entity_id`. Mais cette [propriete](../../custom_components/solar_optimizer/managed_device.py#L858) et le [README](../../README-fr.md#L218) precisent que son usage est uniquement l'affichage. Un appel reel a `set_current_power_with_device_state`, avec cette mesure a zero, conserve 2 400 W et ne consulte pas le capteur.

Pour un appareil variable, `power_entity_id` peut etre une entite de consigne, convertie en watts ; ce n'est pas necessairement une mesure physique de consommation.

### 3.2 L'objectif soustrait un budget, pas une consommation observee

La [fonction objectif](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L207) calcule :

$$
P_{net,predit}(S)=P_{net,mesure}+B(S)-B(S_0)
$$

avec $B(S)$ la somme des `requested_power` des appareils dont `state=True`, definie dans [consommation_equipements](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L274).

L'arret d'un appareil represente a 2 400 W produit ainsi une variation de -2 400 W. Si sa consommation physique etait zero, l'economie reelle est zero : le modele fabrique 2 400 W de disponibilite.

### 3.3 Le plan HC peut etre contredit a l'application

La [preparation des equipements](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L117) ne verrouille pas les appareils forces en HC. La [permutation](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L329) peut donc simuler leur arret lorsqu'ils sont utilisables et hors temporisation.

Le [coordinateur](../../custom_components/solar_optimizer/coordinator.py#L274) consulte ensuite `should_be_forced_offpeak` et refuse l'arret si le forcage est vrai. Il peut cependant allumer les autres appareils choisis grace a cette economie inexistante. Ce defaut de coherence existe **meme si l'appareil HC consomme effectivement sa puissance nominale**, puisque l'arret simule n'est pas execute.

Attention : [should_be_forced_offpeak](../../custom_components/solar_optimizer/managed_device.py#L722) depend des durees et de l'utilisabilite, pas seulement de l'heure. Verrouiller toute la nuit modifierait le contrat ; il faut partager la decision effective du cycle entre optimiseur et coordinateur.

## 4. Reproduction deterministe

Deux executions Python via l'interpreteur selectionne par VS Code ont termine avec code retour zero. Elles importent les classes reelles et utilisent des appareils factices, sans service HA ni commande materielle.

Premier controle : chauffe-eau fixe actif de 2 400 W, utilisable, hors temporisation et force HC ; radiateur fixe inactif de 1 000 W, utilisable et sans forcage HC. Import net 1 500 W, production 8 W, prix d'achat 0,25, prix de vente 0,10, taxe zero, poids des priorites zero. Deux permutations sont imposees : arret du chauffe-eau, puis allumage du radiateur.

| Chauffe-eau simule | Radiateur simule | Import net predit | Objectif calcule |
| ------------------ | ---------------- | ----------------: | ---------------: |
| Actif              | Inactif          |           1 500 W |     1 071,428571 |
| Inactif            | Inactif          |            -900 W |       257,142857 |
| Inactif            | Actif            |             100 W |        71,428571 |
| Actif              | Actif            |           2 500 W |     1 785,714286 |

Le recuit retourne effectivement **chauffe-eau inactif, radiateur actif a 1 000 W**, avec un objectif de 71,428571. Si le chauffe-eau reste alimente mais consomme zero, et si le radiateur consomme les 1 000 W supposes, l'import apres application serait **2 500 W**, pas 100 W, a environnement constant.

Controles supplementaires passes :

1. Une mesure individuelle a zero configuree dans `measured_power_entity_id` ne modifie pas le budget actuel d'un appareil fixe : il reste a 2 400 W.
2. Une charge HC active maintenue constante dans reference et candidats laisse une variation de +1 000 W pour le seul allumage du radiateur ; l'objectif augmente, donc cette activation n'est plus avantageuse dans ce cas.
3. Exclure cette charge de facon coherente de la reference et des candidats produit egalement +1 000 W. La coherence de la difference, et non la valeur absolue du budget fixe, est determinante.
4. Injecter directement `current_power=0` pour un appareil variable actif conduit actuellement a une solution initiale inactive. Remplacer aveuglement la consigne par la mesure introduirait donc un autre defaut.
5. Un petit modele de projection distingue maintien, arret et activation : avec une consommation initiale connue a zero, maintien et arret predisent 1 500 W, tandis que l'allumage du radiateur predit 2 500 W. C'est une verification arithmetique de la proposition, pas une implementation validee.

Ces controles prouvent le mecanisme local de l'algorithme. Ils ne constituent ni une reproduction de l'installation du declarant, ni un test complet du coordinateur, ni une preuve de convergence pour tous les tirages du recuit. Au moment de cette revue initiale, la suite pytest complete n'avait pas ete executee et aucune correction fonctionnelle n'etait livree. Un avertissement d'import Home Assistant/voluptuous a ete emis, sans echec d'execution.

## 5. Pourquoi le probleme general est difficile

Le compteur reseau ne donne que la somme des consommations, corrigee de la production et des flux de batterie. Un meme total peut correspondre a un chauffe-eau au repos et d'autres charges actives, ou a un chauffe-eau qui chauffe avec un environnement different. La production connue ne permet toujours pas de decomposer les consommations individuelles.

Le changement de consommation d'un appareil apres une commande est une information **contre-factuelle** : combien aurait-il consomme sans cette commande ? Un thermostat, un cycle de lavage, une limite de charge ou une variation de tension rendent la relation consigne/consommation non constante.

L'objection de l'issue est donc juste pour une suppression uniforme des economies : si tous les arrets deviennent gratuits sans jamais ameliorer l'objectif, celui-ci ne peut plus identifier les arrets utiles. Mais cela ne signifie pas qu'un arret d'appareil consommant zero devrait ameliorer l'objectif : **l'absence de gain est alors physiquement correcte**. Les egalites doivent etre traitees par une politique explicite, par exemple preferer moins de commandes, sans inventer une economie.

Changer de solveur ou augmenter les iterations ne corrige pas une information manquante : un meilleur solveur optimiserait plus efficacement le meme modele errone.

## 6. Propositions de solution

### A. Rendre les contraintes HC explicites dans l'optimiseur

Avant le recuit, produire un instantane des decisions effectives : etat observe, forcage, possibilite d'arret, possibilite de variation et consigne imposee. Reutiliser cet instantane a l'application.

Un appareil deja actif et force ne doit pas pouvoir etre eteint dans un candidat ; un appareil variable force doit conserver la consigne HC effectivement applicable. Il vaut mieux representer cet etat comme contraint que confondre "non pilotable par le recuit" et "inactif".

**Pourquoi cela fonctionne sans mesure :** pour une charge fixe deja active et inchangee, $B_i(S)-B_i(S_0)=0$. La puissance absolue inconnue n'engendre pas une fausse economie. Le controle de la section 4 confirme ce point pour le cas signale.

**Limites :** si l'appareil est initialement eteint puis force allume, ou si une consigne change a l'entree HC, sa contribution n'est plus constante. Il faut compter la charge nouvelle a partir de l'etat observe avant commande ; construire la reference apres avoir deja impose le nouvel etat masquerait cette variation. Une simple exclusion n'est donc pas une solution complete a ces transitions.

Les priorites et le total expose meritent aussi un contrat explicite : garder une charge verrouillee dans leur calcul peut modifier le classement des charges libres et rendre le total different des commandes finales. Ne pas soustraire une seconde fois une charge deja incluse dans le compteur global.

La description de #228 parle d'un verrouillage `state=False`, mais son diff renvoye par GitHub conserve `is_active` pour un appareil force. Ces representations sont differentes ; il faut repartir d'un contrat clair plutot que reappliquer la PR telle quelle.

### B. Exploiter une consommation individuelle fiable

Reutiliser l'identifiant `measured_power_entity_id` existant, apres decision explicite sur le changement de son contrat actuellement "affichage seulement". Ne pas detourner `power_entity_id`, qui peut representer une consigne.

**Contrainte de compatibilite confirmee : la mesure individuelle doit rester optionnelle.** Solar Optimizer ne cree pas ce capteur : il pourrait exploiter une entite externe deja disponible. Aucune configuration existante ne doit devenir invalide ni exiger un nouvel equipement de mesure. L'absence de capteur, ou sa perte de disponibilite, doit laisser l'appareil pilotable par la strategie sans mesure ; elle ne vaut jamais consommation nulle.

Cette proposition est une amelioration facultative, pas une resolution suffisante de #230 : si elle est appliquee seule, les appareils sans mesure conservent exactement le probleme de consommation inconnue.

Separer au moins l'etat commande, la consigne en watts, la consommation observee et l'estimation apres action. Pour un appareil fixe, au voisinage de l'instant de mesure : maintien sans changement -> consommation observee ; arret -> environ zero ; nouvelle activation -> estimation nominale ou modele specifique.

L'objectif utilise alors :

$$
P_{net,predit}(S)=P_{net,mesure}+\sum_i\left(\widehat P_i(S)-P_{i,observe}\right)
$$

Le maintien d'un appareil actif mais au repos ne le refacture pas a sa puissance nominale. Son arret ne libere rien. Sa prochaine activation est une decision distincte qui doit etre budgetee. Pour un appareil variable, l'effet d'une nouvelle consigne exige un modele adapte ; une regle proportionnelle n'est pas universellement vraie.

**Limites :** mesure perimee, unite W/kW, indisponibilite, valeurs non finies, veille, latence, reprise spontanee du thermostat. Une indisponibilite doit redevenir "inconnue", jamais zero. Le schema actuel interdit certains capteurs au selecteur mais ne suffit pas a valider leur fraicheur. Un capteur de zero ne constitue ni une demande d'arret, ni une garantie que l'appareil restera au repos.

### C. Confirmation par mesure globale : piste ecartee

La proposition initiale consistait a executer les arrets admissibles, attendre une mesure nette globale nouvelle et suffisamment stabilisee, puis recalculer les activations depuis cette reference.

**Piste rejetee par l'utilisateur le 21 novembre 2026 : le delai de la prochaine mesure peut etre long et depend beaucoup de l'installation.** Faire de cette arrivee une condition de reprise introduirait une attente non maitrisee et pourrait rendre l'optimisation inutilisable. Un delai fixe ou un delai maximal ne corrige pas cette limite sans abandonner la confirmation elle-meme.

Cette piste n'est donc plus recommandee pour #230. La proposition F separe les commandes par cycles sans exiger le rafraichissement du compteur. Elle n'a pas pour autant la meme garantie qu'une mesure fraiche ; ses limites doivent etre explicites.

### D. Modele prudent de l'incertitude

Pour un appareil actif sans mesure, representer la consommation possible dans un intervalle, par exemple $[0,P_{max}]$ pour une charge fixe. Son arret apporte une variation comprise entre $-P_{max}$ et zero ; zero est l'economie minimale garantie dans ce modele.

Dans l'exemple, l'arret du chauffe-eau et l'allumage du radiateur donnent une variation totale comprise entre -2 400 W et +1 000 W. Le modele nominal retient -1 400 W ; le modele prudent voit que l'import pourrait augmenter de 1 000 W.

Il est possible d'ajouter un filtre d'admission conservateur aux nouvelles charges ou d'evaluer le cout maximal des scenarios compatibles. Avec un objectif penalisation import/export, le pire cout n'est pas toujours celui d'une seule borne choisie arbitrairement : il faut evaluer les extremites pertinentes.

**Avantage :** n'invente pas une economie certaine et peut etre introduit sans nouvel equipement. **Limite :** certains arrets ont le meme cout prudent que le maintien ; le recuit seul peut alors manquer des economies reelles. Annoncer explicitement cette perte d'optimalite. Cette piste reste une alternative, non une exigence supplementaire de F ; elle ne couvre pas automatiquement les reprises spontanees des charges inchangees.

### E. Information de fonctionnement ou apprentissage

Une information native fiable, telle que l'etat de chauffe ou l'etat du chargeur, peut ameliorer l'estimation sans wattmetre individuel. Elle doit rester distincte de l'etat du contacteur et ne pas confondre une pause temporaire avec la fin d'un cycle.

Une estimation statistique a partir des variations globales est egalement possible, mais sensible aux changements simultanes et aux cycles. Ce serait une estimation assortie d'une confiance, pas une mesure ni une economie garantie.

Si une information auxiliaire HA est necessaire, privilegier un helper natif adapte, par exemple `threshold` pour un seuil avec hysteresis ; les statistiques ou filtres peuvent aider a observer la stabilite. Aucun helper ne peut deduire de maniere certaine la consommation individuelle a partir du seul total. L'inference probabiliste n'est pas recommandee comme condition unique pour autoriser une nouvelle charge.

### F. Ne pas melanger arrets et activations dans un cycle

**Piste proposee par l'utilisateur le 21 novembre 2026, en complement de A : ne jamais activer un appareil dans le meme cycle lorsqu'un autre est arrete.** Elle traite le transfert fictif de puissance entre appareils sans rendre une nouvelle mesure obligatoire. Les configurations sans capteur individuel doivent continuer a fonctionner.

La [boucle actuelle d'application](../../custom_components/solar_optimizer/coordinator.py#L267) execute les commandes equipement par equipement. La nouvelle regle doit porter sur le plan complet, et non sur un drapeau mis a jour seulement apres le premier arret : un appareil a activer pourrait apparaitre avant celui a arreter.

Deroulement propose, encore a concevoir et a tester dans le coordinateur :

1. Construire les candidats en maintenant l'etat actif des appareils forces HC et en interdisant leur arret dans l'optimiseur, conformement a A.
2. Revalider le plan a partir d'un instantane des etats et contraintes. Identifier tous les arrets admissibles avant toute commande ; un maintien d'appareil deja actif n'est pas une activation.
3. Si ce plan contient au moins un arret, conserver les arrets et ecarter les activations de ce cycle, quel que soit l'ordre des appareils. Une tentative d'arret en echec ne doit pas liberer les activations ainsi ecartees.
4. Ne pas mettre les activations ecartees en attente pour les rejouer automatiquement. Au prochain cycle habituel, reconstruire la reference depuis les etats observes et recalculer un nouveau plan, avec les valeurs de capteurs alors disponibles, meme si la mesure nette n'a pas ete rafraichie.
5. Distinguer le plan du recuit du plan effectivement applique dans les valeurs exposees. L'objectif de la solution mixte ne decrit pas le resultat apres suppression des activations.

Dans le cas HC deja actif de #228, A empeche directement l'arret fictif du chauffe-eau. Hors forcage, si le recuit propose arret du chauffe-eau puis activation du radiateur, F laisse le radiateur eteint pour ce cycle. Au suivant, si l'etat arrete du chauffe-eau est observe, son budget initial devient zero : un nouvel allumage du radiateur ne peut plus reutiliser la soustraction de ses 2 400 W. Avec un import toujours mesure a 1 500 W, cet allumage serait predit a 2 500 W, meme si le compteur renvoie encore l'ancienne valeur.

**Compromis :** un remplacement pourtant legitime d'une charge par une autre prend au moins un cycle supplementaire ; des arrets repetes peuvent retarder davantage les activations. En contrepartie, aucun delai d'attente du compteur n'est introduit. La regle conserve l'objectif nominal pour rechercher les arrets utiles, mais filtre les commandes simultanees qui exploiteraient leur economie incertaine.

**Limites :** separer les cycles ne rend pas une mesure perimee exacte et ne garantit pas l'absence de tout import, notamment si d'autres charges, la production ou la batterie changent. La correction du cas au cycle suivant suppose aussi que l'etat de l'appareil arrete soit effectivement observe ; un retour d'etat lent ou un echec de commande doit etre teste. La regle ne remplace pas A : un arret simule puis refuse en HC ne doit jamais financer d'autres candidats.

**Decisions utilisateur confirmees le 21 novembre 2026 pendant la specification :** la regle porte uniquement sur les allumages/arrets, pas sur les augmentations/diminutions de consigne d'un appareil restant actif. Les transferts par variation de puissance restent une limite connue. Une activation forcee HC d'un appareil initialement eteint est egalement reportee lorsque le cycle comporte un arret : aucune exception HC a la separation n'est retenue. Les tests doivent aussi couvrir les retours d'etat retardes et les arrets precedant le recuit, notamment les expirations de timers.

## 7. Choix propose

| Proposition                                        | Sans mesure individuelle          | Resout le cas HC deja actif | Traite l'incertitude generale                                                        | Effort relatif                           |
| -------------------------------------------------- | --------------------------------- | --------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------- |
| A. Contraintes HC coherentes                       | Oui                               | Oui, sous contrat explicite | Non                                                                                  | Localise, transitions a tester           |
| B. Mesure et projection separees                   | Non, sauf information equivalente | Avec A                      | Oui pour l'observation instantanee, prediction encore incertaine                     | Moyen                                    |
| C. Confirmation globale, ecartee                   | Oui                               | Avec A                      | Observation possible, delai non maitrise                                             | Non retenue                              |
| D. Incertitude conservatrice                       | Oui                               | Avec A                      | Oui, en acceptant une perte d'optimalite                                             | Moyen selon l'objectif                   |
| E. Etat natif ou apprentissage                     | Selon l'appareil                  | Avec A                      | Partiellement                                                                        | Variable, apprentissage plutot important |
| F. Arrets et activations dans des cycles distincts | Oui                               | Avec A                      | Evite le transfert fictif dans le meme cycle, sans garantir la fraicheur des mesures | Localise, plans et transitions a tester  |

Direction conseillee : **A + F**, avec tests d'entree/sortie HC, des plans complets et des cycles successifs, sans attente du compteur ni modification implicite des durees. **B reste facultative**, lorsque la mesure existe ; D et E restent des alternatives ou evolutions, non des prealables. C est ecartee.

Le critere de resolution doit inclure les configurations sans aucun capteur individuel et les installations mixtes. Ajouter seulement B ne satisfait pas ce critere. F est une proposition pour eviter l'exploitation d'un arret dans le meme cycle, encore a concevoir et a valider dans le coordinateur ; A traite la divergence HC pour une charge active inchangee, sans requerir de mesure individuelle.

Preserver les configurations ne signifie pas conserver toutes les decisions erronees du modele nominal. F peut retarder d'un ou plusieurs cycles un remplacement de charge et D peut perdre des occasions d'optimisation. Ces compromis doivent etre explicites et testes ; ne pas promettre simultanement la suppression de tous les effets d'une mesure perimee et une reactivite strictement identique sans information supplementaire.

Ne pas imposer "aucun allumage hors HC pendant la nuit" : un appareil sans forcage peut legitimement utiliser un surplus reel, notamment selon la batterie et la politique existante. L'anomalie est l'origine fictive de la disponibilite, pas l'absence de configuration HC du radiateur.

## 8. Criteres de verification pour une future implementation

Les tests devront etre deterministes, dans les fichiers existants, avec permutations imposees ou enumeration des quelques candidats du scenario. Une graine seule ne doit pas remplacer les assertions sur le bilan et les commandes.

1. Cas de #228 : chauffe-eau force HC deja actif, consommation physique zero, radiateur eteint ; ni arret fictif utilisable ni activation financee par cet arret.
2. Meme cas avec consommation nominale reelle : l'interdiction d'arret HC doit produire le meme effet sur les candidats admissibles.
3. Entree HC avec appareil initialement eteint, et appareil variable dont la consigne HC change : la charge nouvelle est comptee depuis l'etat observe, sans double comptage ni reference reconstruite apres commande.
4. Hors forcage, appareil actif a consommation zero : son arret ne cree pas de surplus. Avec consommation connue non nulle, l'arret peut au contraire ameliorer l'objectif.
5. Maintien d'un appareil a mesure zero : pas d'arret automatique, pas de conversion de zero en `power_min`, pas de refacturation fictive a `power_max`.
6. Mesure absente, invalide ou perimee, W/kW, veille et latence : repli explicite vers une consommation inconnue, pas vers zero.
7. Separation des cycles : les deux ordres de liste arret/activation et activation/arret, plusieurs arrets, maintien d'appareils deja actifs, arret en echec, retour d'etat retarde et absence de rejouement automatique des activations ecartees.
8. Temporisations, limites quotidiennes, fin du forcage et priorites : candidats conformes aux commandes effectivement autorisees ; aucune protection existante contournee.
9. Cout equivalent : stabilite des commandes et absence d'oscillation ou d'essais repetes sur une charge cyclique.
10. Coherence des valeurs exposees : distinguer consigne totale, consommation mesuree et prevision ; ne pas afficher un ancien plan comme l'etat effectivement applique.
11. Compatibilite sans mesure individuelle : configurations existantes acceptees sans nouveau champ obligatoire, appareils toujours pilotables, parc mixte et perte du capteur traites par la strategie sans mesure. Verifier que l'ajout facultatif d'une mesure n'est pas la condition de resolution du cas sans capteur.
12. Deux cycles avec mesure nette inchangee : apres arret effectivement observe du chauffe-eau, la reference ne contient plus ses 2 400 W et le radiateur ne peut pas beneficier a nouveau de cette economie fictive. Aucun rafraichissement du compteur n'est exige pour lancer le nouveau calcul.
13. Plans sans arret : activations permises selon l'objectif et les contraintes habituelles. Tester les arbitrages retenus pour les variations de puissance et pour une activation forcee HC concomitante a un arret.

## 9. Resultat du developpement

Les specifications ont ete approuvees avant le demarrage. T01 a ete constate rouge sur les deux variantes avant toute correction de production, puis passe avec les deux ordres d'appareils. L'implementation partage un instantane de cycle entre recuit et application, verrouille les appareils effectivement forces en HC, decide les arrets et activations sur le plan complet, et reporte les activations du cycle comportant un arret sans attente de mesure ni rejeu automatique. Les activations forcees HC suivent la meme regle ; les changements de puissance d'un appareil qui reste actif sont preserves. Le diagnostic distingue les activations differees du plan brut, et le capteur individuel reste facultatif et reserve a l'affichage.

Validation finale : `rtk pytest tests -q -p no:cacheprovider` donne 213 tests passes, 0 echec et 11 ignores. Aucun changement de version, aucune configuration Home Assistant ni recette sur l'installation reelle n'a ete effectue ; cette derniere requiert une autorisation distincte.