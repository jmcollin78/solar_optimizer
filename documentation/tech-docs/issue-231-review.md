# Revue de l'issue #231 - Variation de puissance pendant les heures creuses

## Référence et statut

- Issue : [#231 - Power is modified during off-peak period](https://github.com/jmcollin78/solar_optimizer/issues/231), ouverte par @adrienbadts le 21 novembre 2026 ; étiquettes `bug`, `question` et `P1`.
- Revue du 21 novembre 2026. Rapport en attente d'approbation ; aucune phase de spécification, conception ou développement n'est autorisée à ce stade.
- Le manifeste local indique la version 3.9.0. Le commit local et son éventuelle différence avec le dépôt distant n'ont pas été vérifiés ; la version réellement installée par l'auteur est inconnue.

## Signalement et sources

L'auteur indique un début des heures creuses à 00:38 et une remise à zéro à 06:38. Il dit avoir configuré la puissance maximale, correspondant à 15 A, mais constate plusieurs passages à la puissance minimale pendant cette période. Il indique que le fonctionnement solaire était satisfaisant l'été. Il ne donne ni numéro de version précis ni configuration textuelle complète.

Dans son [commentaire](https://github.com/jmcollin78/solar_optimizer/issues/231#issuecomment-7060175831), le mainteneur demande la version et la configuration de l'appareil et évoque une modification récente du forçage de puissance. L'issue contient deux captures ; elles n'ont pas été examinées visuellement dans cette revue. Les valeurs et constats ci-dessus proviennent du texte, pas d'une interprétation des captures. Les [métadonnées](https://api.github.com/repos/jmcollin78/solar_optimizer/issues/231) et la [chronologie](https://api.github.com/repos/jmcollin78/solar_optimizer/issues/231/timeline) ne déclarent aucun lien de développement direct.

Travaux connexes identifiés :

- [Issue #186](https://github.com/jmcollin78/solar_optimizer/issues/186) et [PR #219](https://github.com/jmcollin78/solar_optimizer/pull/219), fusionnée : puissance spécifique au forçage et repli sur `power_max` ; la PR annonce la version 3.9.0.
- [PR #228](https://github.com/jmcollin78/solar_optimizer/pull/228), fusionnée : exclusion des appareils forcés de l'optimisation, puis annulée par la [PR #229](https://github.com/jmcollin78/solar_optimizer/pull/229). L'[issue #230](https://github.com/jmcollin78/solar_optimizer/issues/230) décrit un problème connexe de calcul de puissance disponible. Son lien causal avec #231 n'est pas établi.
- La recherche consultée n'établit aucun doublon précis ; elle n'est pas exhaustive et ne permet pas d'exclure d'autres travaux.

## Éléments vérifiés dans le code local

1. [Décision de forçage](../../custom_components/solar_optimizer/managed_device.py#L722) : la fenêtre ne suffit pas. `should_be_forced_offpeak` dépend aussi de l'utilisabilité et des durées cumulées, notamment d'une durée inférieure au minimum quotidien. Une fois le minimum atteint, l'optimisation reprend même avant 06:38.
2. [Utilisabilité](../../custom_components/solar_optimizer/managed_device.py#L680) : pour un appareil variable, `check_usable(False)` vérifie notamment la date de disponibilité d'un changement de puissance. Une temporisation peut donc rendre le forçage faux pendant la fenêtre. La [temporisation](../../custom_components/solar_optimizer/managed_device.py#L427) est mise à jour lors d'un changement de puissance.
3. [Coordinateur](../../custom_components/solar_optimizer/coordinator.py#L275) : la consigne HC n'est sélectionnée que si le forçage est vrai, la solution de l'algorithme est inactive et l'appareil est variable. Si la solution est active, la consigne de l'algorithme prévaut, y compris lorsque le forçage est vrai ; elle peut être envoyée si elle diffère de la puissance courante.
4. [Algorithme](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L117) : le code local consulté ne verrouille pas les appareils forcés ; sa [permutation](../../custom_components/solar_optimizer/simulated_annealing_algo.py#L307) peut choisir une puissance variable ou allumer à `power_min` lorsque les conditions le permettent.
5. [Puissance courante](../../custom_components/solar_optimizer/managed_device.py#L450) : elle est reconstruite à chaque cycle à partir de l'état de l'appareil et de l'entité de puissance, avec un repli sur `power_min` pour un appareil variable lorsque cette entité manque ou est indisponible. Une valeur observée à la baisse peut donc aussi relever de la mesure, de sa conversion ou d'une commande externe.
6. La [conception #186](issue-186-design.md#61-pseudocode-de-décision) donnait explicitement priorité à la consigne de l'algorithme lorsque sa solution était active. Le comportement constaté au point 3 correspond à cette conception : il ne faut pas le présenter comme une violation démontrée de cette ancienne décision.
7. Le [test existant](../../tests/test_power_device.py#L14) simule une solution inactive et un forçage vrai pour vérifier la consigne configurée ou son repli. Il ne démontre ni le maintien de la consigne sur plusieurs cycles, ni le cas d'une solution active. Les tests de durée couvrent la décision HC, sans démontrer le scénario signalé de puissance.

Ces constats résultent d'une lecture statique. Aucun test ni reproduction réelle n'a été exécuté ; les captures et l'installation de l'auteur n'ont pas été inspectées. Ils ne prouvent pas que Solar Optimizer a effectivement envoyé la commande minimale dans son cas.

## Pertinence et recommandation

**Recommandation : retenir le signalement pour investigation prioritaire et demander des précisions avant de conclure à un bogue ou d'engager une implémentation.** La baisse rapportée peut compromettre l'énergie délivrée pendant la plage attendue. Un chemin de code peut produire une consigne inférieure à la consigne HC, mais il dépend de la version et d'états qui ne sont pas connus pour l'incident.

Le 21 novembre 2026, l'utilisateur précise la règle attendue : **pendant les heures creuses, la puissance utilisée par un appareil à puissance variable doit être `offpeak_power` et ne doit pas varier**. Cette règle doit figurer explicitement dans les futures spécifications et être vérifiée. Elle est distincte de l'attribution de la cause de l'incident signalé, qui reste à confirmer.

Hypothèses distinctes à départager :

- **H1, priorité de l'optimiseur** : forçage réellement vrai, solution active et puissance demandée inférieure à `offpeak_power`. Le coordinateur peut alors transmettre cette puissance inférieure. Un test du coordinateur avec ces entrées et les actions simulées vérifie le chemin ; les journaux corrélés à l'incident sont nécessaires pour l'attribuer au cas réel.
- **H2, forçage inactif pendant la plage horaire** : minimum déjà atteint, limite ou disponibilité non satisfaite, notamment temporisation de puissance. L'optimiseur reprend alors la main ; il faut relever les états et dates de disponibilité au moment de la baisse.
- **H3, commande ou observation extérieure** : modification par une autre automatisation, limitation du matériel, mesure indisponible ou conversion. Les événements de service et l'historique de l'entité permettent de différencier consigne envoyée et puissance réellement mesurée.

## Périmètre proposé et décisions

Le périmètre fonctionnel demandé porte sur la période d'heures creuses, et pas uniquement sur les cycles où `should_be_forced_offpeak` est vrai : pour un appareil à puissance variable en fonctionnement pendant cette période, la puissance utilisée doit être `offpeak_power` et rester constante. Cette règle ne signifie pas, à elle seule, que l'appareil doit être allumé pendant toute la plage ni que ses protections peuvent être ignorées. Elle modifierait la priorité précédemment documentée pour #186 si l'algorithme demande une autre puissance.

Les spécifications et la conception devront déterminer les interactions avec les limites, les temporisations, l'activation et l'arrêt, sans présumer que la puissance doit rester appliquée à un appareil arrêté ou indisponible. Il faudra également préciser le traitement de `offpeak_power` absent ou issu d'un gabarit dont la valeur varie pendant la période : le repli actuel est `power_max`, mais une valeur dynamique doit être conciliée avec l'exigence de constance. Ces points restent ouverts avant développement.

Exclus du périmètre proposé : refonte générale de l'optimiseur, résolution de #230, changement du compteur journalier ou des règles de remise à zéro, ajout d'une commande matérielle ou modification de l'installation Home Assistant. L'analyse de l'interaction avec l'optimiseur et les autres appareils reste nécessaire pour éviter une régression ; elle ne vaut pas autorisation de refondre cet algorithme.

## Alternatives et contournements

1. **Maintenir la consigne HC pendant la période d'heures creuses**, conformément à la règle précisée : exige de définir les interactions avec les limites et temporisations et peut changer la consommation ainsi que la solution réelle par rapport à la solution calculée.
2. **Priorité à la consigne HC pendant le seul forçage effectif** : intervention potentiellement plus localisée, mais insuffisante pour la règle précisée lorsque le forçage cesse avant la fin de la période.
3. **Conserver la priorité de l'optimiseur et clarifier la documentation** : préserve la décision #186, mais ne garantit pas la puissance constante demandée.
4. **Exclure les appareils forcés de l'optimisation** : piste liée à #228, mais cette PR a été annulée et #230 expose une difficulté de bilan de puissance. Ne pas la réappliquer sans analyse spécifique et validation.
5. **Pilotage externe ou réglage temporaire** : éventuellement envisageable selon l'appareil, mais aucun contournement sûr et vérifié n'est établi. Une automatisation concurrente peut provoquer des commandes contradictoires ; ne pas la recommander sans analyse de l'installation.

## Impacts et risques

Les probabilités sont conditionnelles aux scénarios, pas des estimations de fréquence dans le parc.

| Domaine                       | Risque                                                                                                                          | Gravité                                           | Probabilité / confiance                   | Mesure proposée                                                                                                            |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Fonctionnel et énergie        | Consigne plus faible, énergie délivrée insuffisante ou durée accrue                                                             | Moyenne à élevée selon l'appareil                 | Baisse rapportée ; cause non confirmée    | Corréler consignes, état HC et puissance réelle ; test multicyle                                                           |
| Consommation et coût          | Priorité HC accrue même sans surplus solaire                                                                                    | Moyenne à élevée selon l'installation             | Possible si la priorité est modifiée      | Documenter le contrat et tester les limites et transitions                                                                 |
| Optimisation multi-appareils  | Solution calculée et puissance effectivement appliquée divergent ; impact sur d'autres charges                                  | Moyenne à élevée                                  | Plausible ; ampleur non mesurée           | Tests multi-appareils et analyse de #228/#230 avant tout changement                                                        |
| Temporisations et protections | Maintien interrompu, commandes répétées ou priorité excessive sur les contraintes                                               | Élevée selon l'appareil                           | Possible ; comportement attendu à décider | Tester délais, limites et erreurs ; respecter les protections de l'appareil                                                |
| Compatibilité et migration    | Modification de comportement pour les configurations existantes                                                                 | Moyenne                                           | Prévisible si la priorité change          | Pas de migration présumée ; communiquer la modification et conserver le repli                                              |
| Sécurité et confidentialité   | Journaux/configurations peuvent contenir identifiants et données privées ; puissance plus élevée peut solliciter l'installation | Moyenne à élevée selon les données et le matériel | Conditionnelle                            | Anonymiser les diagnostics ; ne pas contourner les protections électriques ni commander un appareil réel pendant l'analyse |
| Tests et exploitation         | Un test isolé ne prouve ni le comportement matériel ni l'origine de l'incident                                                  | Moyenne                                           | Certaine pour l'analyse actuelle          | Tests ciblés puis recette autorisée adaptée, sans imposer de commande physique                                             |

Aucune nouvelle dépendance n'est envisagée. Une modification de contrat nécessiterait une mise à jour de la documentation utilisateur et une note de version ; la nécessité d'une migration ou d'une configuration supplémentaire dépend de la solution retenue.

## Informations à obtenir

1. Version exacte de Solar Optimizer, canal stable/bêta ou révision, version Home Assistant et présence éventuelle des changements #219, #228 et #229.
2. Configuration anonymisée complète de l'appareil et du coordinateur : `offpeak_power`, `power_min`, `power_max`, `power_step`, conversion et entité de puissance, services, durées minimum et maximum, temporisations, gabarits, fréquence de calcul, horaires et fuseau.
3. Horodatages précis des baisses, évolution du compteur quotidien, de `should_be_forced_offpeak`, de l'état et de la disponibilité de l'appareil ; valeurs de consigne et puissance réellement mesurée.
4. Journaux de débogage et événements de services autour d'au moins une baisse, en masquant les données sensibles ; présence éventuelle d'automatisations ou d'un contrôle matériel concurrent.
5. Précisions sur le traitement des temporisations, des limites, d'un appareil arrêté et d'une `offpeak_power` absente ou dynamique, sans remettre en question la règle de puissance constante pendant les heures creuses.

Les points 1 à 4 conditionnent l'attribution de la cause au signalement. Le point 5 doit être résolu dans les spécifications et la conception avant de démarrer un développement. Si les informations de l'incident ne sont pas disponibles, une reproduction synthétique peut valider une hypothèse locale mais ne doit pas être présentée comme une reproduction de l'incident.

## Vérifications et critères proposés

Après décision du contrat et validation des documents, prévoir dans les tests existants :

1. Un test discriminant du coordinateur avec forçage vrai, appareil variable déjà actif, solution active à `power_min` et consigne HC supérieure ; observer les actions réellement demandées. Vérifier également l'activation d'un appareil inactif et la solution inactive.
2. Plusieurs cycles alternant solutions actives et inactives, avec valeur HC configurée, repli `power_max`, gabarit valide ou invalide, et mesure de puissance indisponible ; vérifier les commandes et éviter les réémissions abusives selon la politique retenue.
3. Tests avec décisions HC réelles : entrée et sortie de fenêtre, égalité aux durées minimale et maximale, disponibilité et temporisation avant/après changement de puissance. Vérifier la puissance constante pendant la période HC même lorsque le forçage effectif cesse, selon les règles d'arrêt et de protection retenues.
4. Non-régression des appareils fixes, des erreurs de validation, des commandes manuelles et des scénarios multi-appareils pertinents pour le bilan de puissance. Vérifier l'interaction avec #230 sans prétendre le résoudre.
5. Exécuter les tests ciblés et les vérifications applicables du dépôt ; une recette en environnement Home Assistant de test ne peut avoir lieu qu'avec autorisation et conditions convenues.

## Suite du processus

1. Approbation explicite du présent rapport et autorisation de produire spécifications et conception, en y inscrivant la règle de puissance constante précisée par l'utilisateur.
2. Après accord, faire converger les deux documents avec les sous-agents désignés. Toute divergence non résolue est soumise à l'utilisateur.
3. Avant développement : résoudre les questions restantes sur les limites, temporisations et valeurs HC, obtenir une reproduction discriminante adaptée au périmètre, la convergence des documents et l'autorisation explicite de l'utilisateur. La cause réelle de l'incident reste à confirmer auprès de son auteur.