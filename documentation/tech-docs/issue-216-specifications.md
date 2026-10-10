# Spécification fonctionnelle - Issue GitHub #216

## 1. Métadonnées

- **Nom** : Adaptation responsive de la carte Solar Optimizer sur smartphone
- **Identifiant** : ISSUE-216
- **Version** : 1.0
- **Statut** : Spécification et conception convergentes ; validation finale utilisateur requise avant développement
- **Date** : 2026-10-10
- **Propriétaire** : Non défini dans les sources
- **Sources analysées** :
  - [Rapport de revue de l'issue #216](issue-216-review.md)
  - [Spécifications de la carte Solar Optimizer](../../tech-docs/so-card-specifications.md)
  - [Composant frontend de la carte](../../custom_components/solar_optimizer/frontend/solar-optimizer-card.js)

## 2. Objectif et contexte

L'issue #216 signale que la carte Solar Optimizer déborde horizontalement sur un écran de smartphone. Ce débordement peut rendre une partie des informations ou des commandes inaccessible.

L'objectif est de rendre la carte entièrement visible et utilisable dans la largeur disponible d'un tableau de bord Home Assistant sur smartphone, tout en conservant les informations, les commandes, les états et les comportements existants.

La correction validée est localisée au frontend de la carte, dans sa présentation HTML/CSS. Elle ne modifie ni la logique métier, ni les services Home Assistant, ni la configuration de la carte.

## 3. Acteurs et cas d'utilisation

### Acteurs

- **Utilisateur du tableau de bord Home Assistant** : consulte l'état global et l'état de ses appareils, puis utilise les commandes de la carte.
- **Carte Solar Optimizer** : présente les informations et relaie les actions existantes vers les entités et services Home Assistant.

### Cas d'utilisation principal

1. L'utilisateur ouvre un tableau de bord Home Assistant sur un smartphone.
2. La carte occupe la largeur disponible sans créer de défilement horizontal.
3. L'utilisateur consulte les cinq statistiques globales et la liste des appareils.
4. L'utilisateur peut replier ou déplier un appareil, utiliser le chevron global et accéder à toutes les commandes disponibles.
5. L'utilisateur peut réaliser les mêmes actions qu'à une largeur desktop : activation de la gestion, démarrage ou arrêt, activation minutée, remise à zéro et changement de priorité lorsque ces contrôles sont disponibles.

## 4. Périmètre

### Inclus

- Adaptation responsive de la disposition de la carte à partir d'une largeur minimale acceptée de 320 px.
- Réorganisation des cinq statistiques globales afin qu'elles restent lisibles dans la largeur disponible.
- Réorganisation de l'en-tête de chaque appareil afin que le nom, le statut et toutes les actions restent visibles.
- Retour à la ligne ou empilement des actions sur mobile, selon l'espace disponible.
- Adaptation de la grille des informations détaillées à une colonne sur mobile.
- Gestion des noms d'appareils longs sans provoquer de débordement horizontal.
- Conservation des informations, contrôles, libellés, états, traductions et services existants.
- Vérification visuelle et fonctionnelle aux largeurs 320, 360 et 390 px, ainsi qu'à partir de 768 px.

### Exclus

- Toute modification du backend Python, des services Home Assistant, des entités, des attributs ou de la logique métier.
- Toute modification du schéma ou des options de configuration de la carte.
- Toute modification des dépendances, de Home Assistant ou de l'intégration.
- Toute fonctionnalité masquée, supprimée ou remplacée par une vue condensée sur mobile.
- Toute réduction artificielle de l'échelle de la carte ou dégradation volontaire de la lisibilité.
- Toute refonte générale de l'identité visuelle ou du rendu de la carte.
- Toute garantie de rendu pour une largeur inférieure à 320 px.

## 5. Exigences fonctionnelles

### Présentation globale

- **FR-001** — Le système doit afficher la carte dans toute la largeur disponible de la colonne Home Assistant, sans provoquer de débordement horizontal à partir de 320 px.
- **FR-002** — Le système doit afficher les cinq statistiques globales sans chevauchement, rognage de texte ni perte d'information à 320, 360 et 390 px.
- **FR-003** — Le système doit réorganiser les statistiques selon l'espace disponible, sans imposer une grille de trois colonnes lorsque celle-ci rend le contenu illisible.

### Appareils et actions

- **FR-004** — Le système doit conserver visibles le nom de l'appareil, son badge de statut, sa puissance courante/maximale et les commandes disponibles.
- **FR-005** — À une largeur mobile, le système doit placer la zone d'actions sur une ligne dédiée lorsque la juxtaposition avec le nom et le statut ne tient pas dans la largeur disponible.
- **FR-006** — La zone d'actions doit pouvoir se répartir sur plusieurs lignes si nécessaire ; aucun contrôle ne doit être masqué ou rendu inaccessible pour résoudre le débordement.
- **FR-007** — La présentation mobile doit conserver l'ordre d'interaction existant des contrôles : durée ou temps restant, START/STOP, puis activation/désactivation de la gestion, sous réserve de la disposition visuelle nécessaire à la largeur.
- **FR-008** — Le système doit permettre l'utilisation de l'activation/désactivation, de START/STOP et de l'activation forcée minutée dans les mêmes conditions fonctionnelles qu'à une largeur desktop.
- **FR-009** — Un nom d'appareil long doit pouvoir se réduire ou se couper à un emplacement approprié sans élargir la carte ni recouvrir le badge ou les actions.

### Détails et états

- **FR-010** — Lorsque les détails d'un appareil sont affichés, le système doit présenter les informations détaillées sur une colonne à une largeur mobile afin d'éviter leur compression illisible.
- **FR-011** — Les informations secondaires, indicateurs, disponibilités, historique, graphique de puissance, bouton RESET et sélecteur de priorité doivent rester accessibles lorsqu'ils sont disponibles dans l'état courant.
- **FR-012** — Les états plié, déplié, actif, en attente, inactif, désactivé et manuel doivent conserver leur signification et leur signal visuel existants.
- **FR-013** — Le chevron individuel, le chevron global et la persistance de l'état plié/déplié doivent conserver leur comportement existant.

## 6. Exigences non fonctionnelles

- **NFR-001** — La correction doit être limitée à la présentation frontend HTML/CSS de la carte.
- **NFR-002** — La correction ne doit modifier aucun appel de service, identifiant d'entité, attribut lu ou donnée affichée.
- **NFR-003** — La présentation doit rester utilisable avec les libellés français et anglais, notamment lorsque les traductions françaises sont plus longues.
- **NFR-004** — La présentation doit être vérifiée avec les thèmes clair et sombre.
- **NFR-005** — Les zones d'action doivent rester distinctes, lisibles et activables au clavier et au toucher ; aucun chevauchement ne doit empêcher l'activation d'un contrôle.
- **NFR-006** — À partir de 768 px, la disposition desktop actuelle doit être conservée, sauf différence purement corrective sans impact fonctionnel.

## 7. Comportements responsive requis

| Largeur de la zone disponible | Comportement attendu                                                                                                                                                                                                                           |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 320 à 359 px                  | Les statistiques sont réorganisées en colonnes adaptées. Le nom et le statut peuvent occuper leur propre ligne. Les actions occupent une ligne dédiée et peuvent se répartir sur plusieurs lignes. Les détails sont présentés sur une colonne. |
| 360 à 599 px                  | La carte reste entièrement visible. Les statistiques, l'en-tête et les détails s'adaptent à la largeur sans débordement. Les actions restent toutes visibles.                                                                                  |
| 600 à 767 px                  | La mise en page peut utiliser davantage d'espace, tout en conservant le retour à la ligne si la largeur réelle de la colonne l'exige.                                                                                                          |
| 768 px et plus                | La disposition desktop existante est préservée et les contrôles restent fonctionnellement identiques.                                                                                                                                          |

La compatibilité minimale retenue est **320 px**. Le comportement en dessous de 320 px n'est pas garanti et ne constitue pas un critère d'acceptation. Cette décision clôt la question ouverte correspondante du rapport de revue.

La présentation mobile des actions est arrêtée comme suit : **les actions sont regroupées dans une zone dédiée sous l'identité de l'appareil, avec retour à la ligne autorisé ; elles restent toutes visibles et activables, sans réduction forcée des libellés ni masquage**. Cette décision clôt la seconde question ouverte non bloquante du rapport.

## 8. Cas limites

- Un nom d'appareil très long ne doit pas forcer la largeur de la carte.
- Les libellés français longs ne doivent pas déplacer un contrôle hors de la zone visible.
- Le badge de temps restant doit rester visible lorsqu'une activation forcée minutée est active.
- Le sélecteur de durée doit rester utilisable lorsqu'aucune activation forcée n'est active.
- Les cinq statistiques doivent rester lisibles même lorsque les valeurs affichées sont longues ou contiennent `N/A`.
- Les appareils sans changement de puissance, sans seuil SOC ou sans sélecteur de priorité ne doivent pas créer de colonne vide ni de débordement.
- Les états actif, en attente, activation forcée, plié et déplié doivent être testés séparément.
- Les cartes contenant plusieurs appareils ne doivent pas cumuler de débordement horizontal.
- Le thème sombre et le thème clair ne doivent pas modifier la disponibilité des contrôles.

## 9. Critères d'acceptation

- **AC-001** — Aux largeurs 320, 360 et 390 px, la carte ne crée aucun défilement horizontal dans le tableau de bord.
- **AC-002** — Aux mêmes largeurs, les cinq statistiques globales sont visibles, lisibles et non superposées.
- **AC-003** — Avec un nom d'appareil long, le nom, le badge, le contrôle de durée ou temps restant, START/STOP et l'interrupteur d'activation restent visibles et utilisables.
- **AC-004** — À 320 px, les actions sont présentées sous l'identité de l'appareil et peuvent occuper plusieurs lignes sans être masquées ni recouvrir une autre information.
- **AC-005** — Un appareil plié conserve ses informations et commandes prévues ; le dépliage rend accessibles les indicateurs, informations, historique, RESET et priorité lorsqu'ils existent.
- **AC-006** — Le chevron individuel et le chevron global continuent de plier et déplier les appareils, et l'état persiste comme avant.
- **AC-007** — Les commandes mobiles déclenchent les mêmes entités et services que les commandes desktop, sans modification backend observable.
- **AC-008** — Les scénarios en français et en anglais passent aux largeurs 320, 360 et 390 px.
- **AC-009** — Les scénarios en thème clair et en thème sombre passent aux mêmes largeurs.
- **AC-010** — Les états actif, en attente, inactif, désactivé, manuel et activation forcée minutée restent compréhensibles et utilisables.
- **AC-011** — À partir de 768 px, aucun contrôle ni aucune information n'est perdu et la disposition desktop reste équivalente à l'existant.
- **AC-012** — Aucune configuration, dépendance, entité ou service Home Assistant n'est modifié par la correction.

## 10. Stratégie de recette

La recette doit être réalisée sur la carte réellement rendue dans un tableau de bord Home Assistant, avec des données représentatives de plusieurs appareils.

1. **Préparer les variantes** : français et anglais ; thème clair et thème sombre ; un appareil et plusieurs appareils ; nom court et nom long.
2. **Vérifier les largeurs** : exécuter les scénarios à 320, 360, 390, 600 et 768 px au minimum.
3. **Vérifier la structure** : rechercher tout débordement horizontal, chevauchement, texte rogné ou contrôle hors écran.
4. **Vérifier les actions** : activer/désactiver la gestion, démarrer, arrêter, sélectionner une durée, observer un temps restant, réinitialiser le temps de marche et modifier la priorité lorsque ces contrôles sont disponibles.
5. **Vérifier les états** : couvrir les états physique et de contrôle décrits dans les spécifications de la carte, y compris l'état manuel et l'attente.
6. **Vérifier le pliage** : tester le pliage individuel, le pliage global et la restauration après rechargement.
7. **Vérifier la non-régression** : confirmer que les appels de service, les entités et les données affichées restent inchangés ; aucun test backend ou changement Home Assistant n'est requis dans le cadre de cette correction.

La recette est réussie uniquement si tous les critères AC-001 à AC-012 sont satisfaits. Un échec lié à une largeur inférieure à 320 px est hors du périmètre accepté ; un échec à 320 px ou plus bloque l'acceptation.

## 11. Hypothèses, questions ouvertes et traçabilité

### Hypothèses retenues

- La carte est utilisée dans une colonne Home Assistant dont la largeur peut être proche de celle du viewport mobile.
- Les informations et commandes existantes doivent rester disponibles sur mobile.
- La correction responsive peut être traitée dans le composant frontend sans évolution de contrat backend.

### Questions ouvertes non bloquantes décidées

- **Largeur minimale** : 320 px est le minimum accepté ; les largeurs inférieures sont hors garantie.
- **Actions mobiles** : elles sont regroupées sur une ligne dédiée sous l'identité de l'appareil, avec retour à la ligne autorisé et sans masquage.

### Questions non couvertes par le rapport

- Le rapport ne permet pas de confirmer si le débordement apparaît également dans le mode d'édition de la carte. Ce mode n'est donc pas un critère d'acceptation de cette spécification.

### Traçabilité

- Le débordement constaté, les causes probables et le périmètre frontend sont établis dans `documentation/tech-docs/issue-216-review.md`.
- Les informations, commandes, états, pliage et activation minutée de la carte sont décrits dans `tech-docs/so-card-specifications.md` et vérifiés dans `custom_components/solar_optimizer/frontend/solar-optimizer-card.js`.
- La présente spécification formalise uniquement la correction responsive validée ; elle ne constitue pas une demande de modification du backend.
