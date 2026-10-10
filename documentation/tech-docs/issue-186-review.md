# Revue de l'issue #186 - Forcer la puissance pendant les heures creuses

## Référence et résumé fidèle

- Issue : [#186](https://github.com/jmcollin78/solar_optimizer/issues/186), ouverte par @M3c4tr0x le 7 janvier.
- Statut : ouverte, libellé `enhancement`, sans assignation, jalon ni pull request associé.

L'auteur utilise un chauffe-eau dont la consigne de puissance repasse à `0` lorsqu'il est éteint. En journée, Solar Optimizer active l'appareil et transmet une puissance, puis la réajuste. Lors de l'activation forcée en heures creuses, l'appareil est bien allumé mais aucune consigne de puissance n'est transmise ; il ne chauffe donc pas.

L'issue regroupe deux sujets :

1. transmettre une puissance lors d'une activation en heures creuses pour un appareil à puissance variable, idéalement 100 % ou une valeur configurable ;
2. confirmer et, si nécessaire, formaliser le comportement de la durée en heures creuses lorsque `min_on_time_per_day_min`, `offpeak_time` et aucune durée maximale sont configurés.

## Sources et éléments vérifiés

- Description et discussion de l'issue #186, y compris les réponses de @jmcollin78 et @M3c4tr0x.
- `custom_components/solar_optimizer/coordinator.py` : l'activation peut être forcée par `should_be_forced_offpeak`, mais l'appel de changement de puissance exige que l'état retourné par l'algorithme soit actif.
- `custom_components/solar_optimizer/managed_device.py` : une durée maximale non configurée reçoit la valeur par défaut de 24 h ; le forçage en heures creuses s'arrête lorsque la durée minimale est atteinte, sous réserve de ne pas atteindre la durée maximale.
- `custom_components/solar_optimizer/config_schema.py` : aucune option ne permet de configurer une puissance spécifique aux heures creuses.

## Pertinence et recommandation

**Recommandation : retenir, sous réserve de valider le comportement fonctionnel de la puissance.**

Le défaut de consigne rend le mode heures creuses inopérant pour les appareils dont l'allumage ne restaure pas une puissance non nulle. Le besoin est cohérent avec les équipements déjà pris en charge à puissance variable.

## Périmètre proposé

Inclure :

- l'envoi d'une consigne explicite quand une activation est forcée par les heures creuses pour un appareil à puissance variable ;
- une puissance heures creuses optionnelle, uniquement pour les appareils à puissance variable ; si elle est absente, appliquer `power_max` afin de préserver le comportement attendu ;
- une durée maximale heures creuses optionnelle par appareil ; si elle est absente, utiliser `max_on_time_per_day_min` afin de préserver le fonctionnement actuel ;
- la couverture de tests du scénario et la documentation de la configuration concernée ;
- la documentation des valeurs par défaut et des interactions entre durées quotidiennes et heures creuses.
- la mise à jour de la documentation utilisateur en français et en anglais ;
- l'incrément de la version mineure de l'intégration ;
- l'ajout, dans l'en-tête de chaque README, d'une mention de cette évolution pour la release correspondante.

Exclure :

- une refonte générale de l'algorithme solaire ;
- le pilotage de l'énergie stockée d'un chauffe-eau, qui reste une logique utilisateur distincte.

## Impacts et risques

| Risque                                                         | Gravité | Probabilité | Mesure                                                                                                                         |
| -------------------------------------------------------------- | ------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Puissance forcée inadaptée à certains appareils                | Moyenne | Faible      | La puissance heures creuses n'est disponible que pour les appareils à puissance variable ; à défaut, `power_max` est appliqué. |
| Absence de durée maximale : activation diurne sans fin         | Élevée  | Moyenne     | Avertir dans la documentation et conserver/valider la limite par défaut actuelle.                                              |
| Régression de la temporisation entre changements de puissance  | Moyenne | Faible      | Ajouter des tests ciblés du cycle heures creuses.                                                                              |
| Évolution non visible ou configuration ambiguë après livraison | Moyenne | Moyenne     | Mettre à jour les README, les guides de configuration et l'annonce de release.                                                 |

## Alternatives examinées

- Automatisation Home Assistant externe : contournement déjà employé par l'auteur ; flexible, mais duplique une responsabilité de l'intégration.
- Configurer `max_on_time_per_day_min` égal à la durée minimale : rejeté par l'auteur, car cela limite le stockage solaire diurne ou remplit excessivement le ballon la nuit.
- Envoyer systématiquement `power_max` pendant les heures creuses : solution simple et cohérente avec la discussion, mais moins flexible que la solution retenue.
- Ajouter une puissance et une durée maximale spécifiques aux heures creuses : **solution retenue** ; elle répond aux usages de chauffe-eau tout en conservant les valeurs actuelles par défaut.

## Hypothèses, décisions et questions ouvertes

### Faits confirmés

- L'absence actuelle de consigne en activation forcée découle de la condition sur l'état de la solution algorithmique.
- Sans durée maximale configurée, la limite interne est de 24 h, et non une absence de limite.
- La durée minimale est bien la cible d'arrêt du forçage en heures creuses.

### Décisions actées

1. Un appareil à puissance variable peut définir une puissance spécifique à appliquer lors d'une activation en heures creuses.
2. Sans puissance heures creuses configurée, l'intégration applique `power_max`.
3. Tout appareil géré peut définir une durée maximale spécifique aux heures creuses.
4. Sans durée maximale heures creuses configurée, l'intégration utilise `max_on_time_per_day_min`.

### Questions ouvertes

- La spécification devra déterminer les noms de champs, leurs bornes et la validation de cohérence avec les puissances et durées existantes.
- Le risque déjà existant d'absence de durée maximale quotidienne devra être documenté pour les équipements sans arrêt de sécurité autonome.
- La release devra incrémenter la version mineure et présenter l'évolution dans l'en-tête des README français et anglais.

## Passage à la spécification et à la conception

Après validation de ce rapport, la spécification définira le contrat des nouveaux réglages et les exigences documentaires de release. La conception établira le chemin d'exécution, les tests de non-régression et les fichiers de versioning à modifier.