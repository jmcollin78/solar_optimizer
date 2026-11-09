# Revue de l'issue #222 - Compteur journalier non synchronisé après redémarrage

## Référence et statut

- Issue : [#222 - Device forced at offpeak_time after a Home Assistant restart although min_on_time_per_day_min is already reached](https://github.com/jmcollin78/solar_optimizer/issues/222).
- Revue effectuée le 9 novembre 2026.
- Issue ouverte, créée par @saucekorn69 le 6 novembre 2026, étiquettes `bug` et `question`, sans assigné ni jalon ; un commentaire de @Zedas030 consulté.
- Révision locale examinée : `main`, commit `2f819a36553f51e58f7928f57571ece4325ff895`, identique à la référence citée dans le commentaire. Arbre de travail initialement propre.
- Statut du processus : rapport approuvé par l'utilisateur le 9 novembre 2026 (« Je confirme. Go pour spec/design ») ; phase de spécification et de conception autorisée. Aucun développement autorisé ni effectué.

## Résumé fidèle de l'issue

@saucekorn69 utilise Solar Optimizer 3.9.0 et Home Assistant 2026.11.0 avec un appareil tout ou rien : minimum journalier de 120 minutes, début des heures creuses à 02:00, durée minimale d'activation de 60 minutes, durée minimale d'arrêt de 30 minutes et remise à zéro à 05:00, sans maximum journalier configuré.

Après un redémarrage de Home Assistant alors que l'appareil est éteint, le capteur de durée quotidienne retrouve la bonne valeur, mais l'appareil est malgré tout forcé pendant les heures creuses. Deux occurrences sont rapportées : 6 h 50 déjà comptabilisées avant un redémarrage le 2 novembre à 18:37, puis 2 h 10 avant un redémarrage le 4 novembre à 22:18. Dans les deux cas, l'appareil fonctionne de 02:03 à 03:08 la nuit suivante. Une nuit sans redémarrage préalable ne présente pas le problème.

Le comportement attendu est la restauration du compteur utilisé par les décisions métier, pas seulement de la valeur affichée. L'auteur propose de transmettre la valeur restaurée à `ManagedDevice.set_on_time`. Il indique avoir utilisé un gabarit pour le minimum journalier, alimenté par un capteur `history_stats` indépendant, comme contournement.

@Zedas030 confirme le chemin de code décrit et signale que le même compteur intervient dans le maximum journalier : après redémarrage, un appareil ayant déjà atteint son plafond peut redevenir utilisable par l'optimiseur.

## Sources et éléments vérifiés

### Sources GitHub

- Description et commentaire de l'issue, obtenus via l'outil GitHub.
- [Métadonnées de l'issue](https://api.github.com/repos/jmcollin78/solar_optimizer/issues/222) et [chronologie accessible](https://api.github.com/repos/jmcollin78/solar_optimizer/issues/222/timeline) : deux événements d'étiquetage et le commentaire précité ; aucun renvoi vers un correctif ou une autre issue dans les éléments retournés.
- Aucun doublon ni correctif lié n'est établi par ces sources. Une recherche exhaustive de toutes les issues, branches et pull requests du dépôt n'a pas été réalisée ; leur absence ne peut donc pas être affirmée.

### Code local

- [Initialisation du compteur interne](../../custom_components/solar_optimizer/managed_device.py#L207) : chaque nouveau `ManagedDevice` démarre avec `_on_time_sec = 0`.
- [Restauration du capteur](../../custom_components/solar_optimizer/sensor.py#L247) : `async_added_to_hass` initialise la valeur à zéro, restaure éventuellement la valeur numérique et `last_datetime_on`, puis calcule les attributs et publie l'état, sans appeler `set_on_time`.
- [Actualisation du compteur](../../custom_components/solar_optimizer/sensor.py#L308) : `_refresh_on_time` quitte immédiatement si l'appareil est inactif et que `last_datetime_on` est absent. Le minuteur ne synchronise donc pas le compteur interne dans ce cas.
- [Affectation métier](../../custom_components/solar_optimizer/managed_device.py#L450) : `set_on_time` affecte directement `_on_time_sec`, sans commander l'appareil.
- [Maximum journalier](../../custom_components/solar_optimizer/managed_device.py#L478) : `check_usable` interdit l'utilisation lorsque `_on_time_sec >= max_on_time_per_day_sec`.
- [Forçage heures creuses](../../custom_components/solar_optimizer/managed_device.py#L520) : `should_be_forced_offpeak` compare ce même compteur aux seuils minimum, maximum journalier et maximum des heures creuses.
- [Application de la décision](../../custom_components/solar_optimizer/coordinator.py#L239) : le coordinateur peut allumer l'appareil lorsque `should_be_forced_offpeak` est vrai, même si la solution d'optimisation ne demande pas l'allumage.
- [Attributs du capteur](../../custom_components/solar_optimizer/sensor.py#L375) : `update_custom_attributes` expose notamment `should_be_forced_offpeak`, calculé à partir du compteur métier.
- [Manifeste](../../custom_components/solar_optimizer/manifest.json) : la version locale est également 3.9.0.
- Tests consultés : [minimum journalier](../../tests/test_min_on_time.py), [maximum et comptage](../../tests/test_max_on_time.py), [fixtures](../../tests/conftest.py). Aucun test de restauration d'une durée non nulle sur appareil inactif n'a été identifié dans ces tests.

### Vérifications exécutées sans modifier le code

Commande des tests existants :

```bash
rtk proxy env PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/test_min_on_time.py tests/test_max_on_time.py
```

Résultat : **16 tests réussis en 0,78 seconde**. Ils ne constituent pas une preuve d'absence de régression de restauration, puisque le scénario manquant n'y est pas couvert.

Une reproduction isolée a également été exécutée avec l'interpréteur sélectionné par VS Code via Pylance, sans fichier de test ajouté. Elle appelle les méthodes réelles de restauration et d'actualisation du capteur, ainsi que `ManagedDevice.check_usable`, `set_on_time` et `should_be_forced_offpeak`. Les abonnements Home Assistant, la lecture de l'état persistant, la publication et les autres dépendances sont simulés ; aucune instance Home Assistant en fonctionnement n'est sollicitée.

Conditions : appareil inactif, `last_datetime_on = None`, heure courante 02:03, remise à zéro 05:00, minimum 7 200 secondes, autres conditions d'utilisation satisfaites.

| Valeur restaurée  | Compteur interne après restauration et actualisation inactive | Forçage avant synchronisation | Forçage après appel explicite à `set_on_time` |
| ----------------- | ------------------------------------------------------------- | ----------------------------- | --------------------------------------------- |
| 24 600 s / 6 h 50 | 0 s                                                           | Oui                           | Non                                           |
| 7 800 s / 2 h 10  | 0 s                                                           | Oui                           | Non                                           |
| 7 200 s / 2 h     | 0 s                                                           | Oui                           | Non                                           |
| 7 140 s / 1 h 59  | 0 s                                                           | Oui                           | Oui                                           |

Pour chaque valeur, fixer le maximum journalier à la durée restaurée montre aussi que `check_usable(False)` reste vrai avec le compteur interne à zéro et devient faux avec le compteur synchronisé.

**Conclusion établie :** le défaut de synchronisation et ses conséquences sur les décisions minimum/maximum sont reproduits avec les méthodes réelles dans un environnement isolé. Ce n'est pas une reproduction complète d'un redémarrage Home Assistant ou d'une commande physique d'allumage.

## Pertinence et recommandation

**Recommandation : retenir l'issue comme bogue, avec une correction localisée de la restauration et des tests de non-régression.**

Le diagnostic proposé par l'auteur est confirmé sur la révision examinée. L'affichage peut être correct alors que les décisions utilisent zéro ; le risque ne se limite donc pas à un problème visuel ou aux seules heures creuses. La correction est cohérente avec l'architecture existante, qui synchronise déjà le compteur lors des actualisations et de la remise à zéro.

La durée observée de 65 minutes est compatible avec la durée minimale d'activation et la cadence d'optimisation rapportées. Son déroulement exact n'a pas été reproduit ; aucun journal d'exécution de l'installation n'est fourni.

## Périmètre proposé

### Inclus

- Synchroniser le compteur interne de `ManagedDevice` avec la valeur du capteur dès la fin de la restauration.
- Effectuer cette synchronisation après la lecture de la valeur et de ses attributs, mais **avant** `update_custom_attributes()` et `async_write_ha_state()`, afin de publier une décision cohérente dès le premier état.
- Appliquer le même chemin à la valeur de repli zéro, même lorsqu'aucun état exploitable n'a été restauré.
- Garantir par des tests que la restauration préserve les décisions aux seuils minimum et maximum, y compris les égalités, sans empêcher les activations légitimes lorsque le minimum n'est pas atteint.
- Préserver le comptage actif, le traitement existant des états non restaurables et la remise à zéro quotidienne.

### Exclus

- Modifier l'algorithme d'optimisation, les services d'activation, les temporisations ou la définition des heures creuses.
- Refondre la persistance ou ajouter un second stockage du compteur.
- Reconstituer le temps d'activité pendant l'arrêt de Home Assistant.
- Définir une nouvelle politique pour une remise à zéro survenue pendant cet arrêt ; ce cas connexe doit faire l'objet d'une analyse distincte si nécessaire.
- Modifier la configuration utilisateur, les dépendances, les traductions, le frontend ou un environnement Home Assistant réel.

## Correction recommandée et alternatives

1. **Synchronisation au point de restauration, recommandée.** Utiliser le setter existant avec la valeur finalement retenue, hors de la branche conditionnelle de restauration. Avantages : traite la source de l'incohérence, faible surface de modification, aucun stockage supplémentaire. Limite : ne résout pas les questions temporelles volontairement exclues.
2. **Synchronisation seulement dans l'actualisation périodique.** Peut résorber l'écart, mais laisse une fenêtre pendant laquelle une décision peut être prise sur zéro ; déplacer l'appel avant le retour anticipé ne garantit pas la cohérence du premier état publié. Non retenu.
3. **Lecture directe de l'état du capteur dans les décisions métier.** Évite une copie interne, mais crée un couplage aux entités et à leur disponibilité, avec une refonte disproportionnée. Non retenu.
4. **Persistance indépendante du compteur métier.** Pourrait fournir une autre source à restaurer, mais duplique les données et introduit des risques de divergence et de migration. Non retenu.
5. **Gabarit utilisant `history_stats`, contournement rapporté.** Peut éviter certains forçages avec un calcul adapté, mais la configuration exacte n'est pas fournie et son efficacité n'a pas été vérifiée. Il ajoute une dépendance utilisateur et ne corrige pas directement le compteur ni la protection par maximum journalier.

## Impacts et risques

Les probabilités ci-dessous sont conditionnelles au scénario et non des estimations de fréquence dans le parc installé.

| Domaine                     | Impact ou risque                                                                           | Gravité                           | Probabilité / confiance                                                         | Mesure proposée                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------ | --------------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Fonctionnel, minimum        | Activation indue après redémarrage malgré un minimum atteint                               | Élevée                            | Reproduite dans les conditions isolées décrites                                 | Restaurer le compteur métier avant publication ; tests au-dessus et à égalité du minimum |
| Fonctionnel, maximum        | Appareil réadmis dans l'optimisation malgré un plafond atteint                             | Élevée                            | Décision erronée reproduite ; activation réelle conditionnelle à l'optimisation | Tester `check_usable` à égalité et au-dessus du maximum après restauration               |
| Exploitation et énergie     | Consommation supplémentaire ; durée de marche additionnelle dépendante de la configuration | Modérée à élevée selon l'appareil | Plausible ; occurrences rapportées par l'auteur                                 | Corriger la cause et confirmer une recette de redémarrage en environnement de test       |
| Cohérence des attributs     | Première publication de `should_be_forced_offpeak` calculée avec zéro                      | Modérée                           | Attendue si la synchronisation est placée trop tard                             | Placer le setter avant `update_custom_attributes` et tester la première publication      |
| Régression du comptage      | Double ajout de durée, perte de valeur ou modification de la remise à zéro                 | Modérée                           | Faible avec une simple affectation ; à vérifier                                 | Tests de comptage actif et de remise à zéro existants, plus restauration                 |
| Compatibilité               | Modification du schéma ou du format persistant                                             | Faible                            | Non attendue avec la solution proposée                                          | Réutiliser la valeur existante en secondes et le setter ; aucune migration               |
| Sécurité et confidentialité | Aucun nouveau flux de données, service, droit ou secret                                    | Faible                            | Aucun impact supplémentaire identifié                                           | Ne pas inclure les secrets ou journaux privés dans les tests ou le rapport               |

La correction ne nécessite aucune nouvelle dépendance. La documentation utilisateur ne devrait pas nécessiter de changement de configuration ; une note de correction dans le support de publication utilisé par le projet est recommandée au moment de la livraison.

## Hypothèses, inconnues et décisions nécessaires

### Hypothèses et limites

- Le scénario principal reste dans le même cycle de comptage : redémarrage avant 02:00 et remise à zéro à 05:00. C'est cohérent avec les occurrences rapportées.
- Les valeurs restaurées numériques utilisées dans la reproduction sont valides et exprimées en secondes.
- Les conditions autres que la durée autorisent l'utilisation de l'appareil ; elles ont été simulées pour isoler le défaut.
- Ni le redémarrage complet, ni les horodatages exacts des activations, ni une installation physique n'ont été reproduits.
- L'absence de concurrence entre restauration et tout premier calcul d'optimisation n'a pas été démontrée de bout en bout ; le test d'intégration devra vérifier la cohérence au premier calcul suivant la restauration.

### Décisions validées

1. Diagnostic retenu et synchronisation au point de restauration approuvée avec le rapport.
2. Périmètre incluant le maximum journalier, affecté par la même cause, sans refonte des autres règles.
3. Comptabilisation pendant l'arrêt et remise à zéro manquée pendant cet arrêt exclues du périmètre.

Aucune question fonctionnelle bloquante n'est identifiée pour ce périmètre restreint. Les limites de vérification ci-dessus devront rester explicites lors de la conception et de la recette.

## Critères d'acceptation proposés

1. Après restauration d'une durée valide sur un appareil éteint et sans `last_datetime_on`, la valeur du capteur et le compteur métier sont identiques avant la première publication.
2. En heures creuses, une durée restaurée supérieure ou égale au minimum n'autorise aucun forçage lié à ce minimum, si les autres conditions restent inchangées.
3. Une durée inférieure au minimum conserve le forçage attendu lorsque toutes les autres conditions l'autorisent.
4. Une durée restaurée supérieure ou égale au maximum journalier rend l'appareil inutilisable pour l'optimisation ; une durée inférieure ne le bloque pas pour ce motif.
5. L'actualisation périodique d'un appareil éteint ne remet pas à zéro le compteur restauré et ne provoque aucune activation.
6. Sans état précédent, avec `unknown`, `unavailable` ou un texte non numérique géré par le chemin actuel, la valeur de repli zéro est synchronisée sans introduire de nouvelle exception.
7. Les attributs initiaux, notamment `should_be_forced_offpeak`, utilisent la durée restaurée ; un premier calcul d'optimisation après restauration ne repart pas de zéro.
8. La restauration d'un appareil actif, le comptage existant et la remise à zéro quotidienne restent compatibles avec le comportement actuel, sans double comptage ajouté par la synchronisation.
9. Des tests persistants de restauration sont ajoutés dans les modules de test existants appropriés ; les 16 tests ciblés actuellement réussis restent verts. La reproduction isolée de cette revue ne remplace pas ces tests.

## Suite du processus et passage au développement

1. Approbation explicite de ce rapport et autorisation de passer à la spécification et à la conception obtenues le 9 novembre 2026.
2. Confier les spécifications au sous-agent `Rédacteur de spécifications`, puis la conception au sous-agent `Conception logicielle détaillée` ; faire converger périmètre, exigences, critères et solution testable, au maximum en trois cycles.
3. Présenter les documents convergents, les décisions et les risques résiduels ; obtenir une nouvelle autorisation explicite de développement.
4. Déléguer alors seulement l'implémentation au sous-agent `Développement d’intégrations Home Assistant`, avec le rapport, les spécifications, la conception et les critères validés.

Le passage au développement exige ces deux validations humaines, des documents complets et convergents, et l'absence de question bloquante. La première validation est acquise ; la validation des résultats de spécification et de conception reste à obtenir. Aucun fichier de code, de configuration ou de dépendances n'a été modifié.