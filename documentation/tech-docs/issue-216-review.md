# Revue de l'issue #216 - Carte Solar Optimizer trop large sur smartphone

## Références

- Issue : [#216 - The SO Card is too large on smarphone screen](https://github.com/jmcollin78/solar_optimizer/issues/216)
- Branche liée par GitHub : [216-the-so-card-is-too-large-on-smarphone-screen](https://github.com/jmcollin78/solar_optimizer/tree/216-the-so-card-is-too-large-on-smarphone-screen)
- État consulté : issue ouverte, libellée `bug`, sans assigné, jalon, commentaire, pull request ni critère d'acceptation explicite.

## Résumé fidèle

L'issue signale que la carte Lovelace Solar Optimizer est trop large sur un écran de smartphone et déborde de l'écran. Une capture d'écran accompagne le signalement. Le comportement attendu est implicite : la carte doit rester intégralement visible et utilisable à la largeur disponible dans le tableau de bord mobile.

## Sources et éléments vérifiés

### Issue GitHub

- Le titre et la description décrivent un débordement horizontal de la carte sur smartphone.
- GitHub associe une branche de travail à l'issue, mais la comparaison avec `main` ne contient aucun changement. Aucun correctif existant n'est donc disponible pour revue.

### Dépôt local

- La carte est implémentée dans `custom_components/solar_optimizer/frontend/solar-optimizer-card.js` sous forme d'un composant autonome injectant ses styles CSS.
- Le corps de la carte et `ha-card` utilisent déjà `width: 100%` et `box-sizing: border-box`; la cause n'est donc pas une largeur fixe du conteneur principal.
- La grille des statistiques impose trois colonnes égales, sans règle responsive. Cinq statistiques y sont affichées.
- L'en-tête d'un équipement juxtapose sans retour à la ligne le groupe nom/statut et le groupe sélecteur de durée, bouton START/STOP et commutateur d'activation. Les actions n'autorisent pas non plus le retour à la ligne.
- La grille d'informations détaillées impose deux colonnes. Le nom d'équipement ne peut pas se réduire explicitement ni couper un mot long.
- Aucune règle `@media` n'est présente dans la feuille de style de la carte.
- Les spécifications exigent que la carte prenne toute la largeur disponible dans Home Assistant, sans définir de comportement mobile plus précis.

## Pertinence et recommandation

**Recommandation : retenir une correction responsive CSS localisée dans la carte, accompagnée d'une recette visuelle sur mobile.**

Le défaut est cohérent avec l'implémentation et a un impact direct sur l'usage principal de la carte. La correction ne nécessite ni changement de l'intégration Python, ni migration de configuration, ni dépendance supplémentaire.

## Périmètre proposé

### Inclus

- Adapter la mise en page de la carte à une largeur de tableau de bord mobile.
- Permettre le retour à la ligne ou l'empilement des actions d'un équipement lorsque l'espace horizontal manque.
- Préserver l'accessibilité et les actions existantes : activation, durée forcée, START/STOP, repli, reset et priorité.
- Vérifier l'absence de défilement horizontal aux largeurs mobiles représentatives.

### Exclus

- Modifier la logique métier Python ou les services Home Assistant.
- Réduire artificiellement l'échelle de la carte, tronquer les libellés ou masquer des actions.
- Modifier le schéma de configuration de la carte.
- Refaire l'identité visuelle complète de la carte.

## Solution recommandée

Ajouter des règles responsive ciblées dans le style du composant, avec un seuil à valider visuellement autour de `600px` :

1. Remplacer la grille fixe des statistiques par une grille fluide, par exemple `repeat(auto-fit, minmax(120px, 1fr))`. Elle passe naturellement de trois à deux, puis une colonne lorsque nécessaire, sans espace perdu sur grand écran.
2. Autoriser `flex-wrap` dans l'en-tête et les actions des équipements. Sous le seuil mobile, placer les actions sur leur propre ligne, alignées à droite ou étirées sur la largeur disponible selon le rendu le plus lisible.
3. Donner `min-width: 0` au groupe textuel et appliquer `overflow-wrap: anywhere` au nom de l'équipement afin qu'un nom long ne force jamais le débordement.
4. Passer la grille d'informations détaillées à une seule colonne sous le seuil mobile.
5. Identifier par des classes CSS les groupes aujourd'hui stylés en ligne qui doivent changer de disposition en mobile, plutôt que de cibler leur position DOM. Cela limite les régressions lors d'une évolution du rendu.

Cette solution maintient les informations et commandes visibles, évite un comportement dépendant du navigateur et reste entièrement circonscrite au frontend.

## Alternatives examinées

1. **Uniquement ajouter `overflow-x: auto` au conteneur**
   - Avantage : modification très courte.
   - Inconvénient : laisse la carte difficile à lire et les commandes moins accessibles; ne répond pas au besoin d'une carte utilisable sur smartphone.

2. **Réduire les tailles de police et de padding sur mobile sans modifier la structure**
   - Avantage : faible effort.
   - Inconvénient : ne résout pas les noms longs, le temps restant, la traduction française ou le cumul de contrôles; dégrade la lisibilité.

3. **Masquer des statistiques ou actions sur mobile**
   - Avantage : garantit une largeur réduite.
   - Inconvénient : retire des fonctions nécessaires et introduit une différence fonctionnelle injustifiée entre desktop et mobile.

4. **Recomposer entièrement le rendu HTML pour le mobile**
   - Avantage : contrôle maximal de la présentation.
   - Inconvénient : coût, risque de divergences entre deux rendus et surface de régression nettement supérieurs. À ne retenir que si les règles CSS ciblées sont insuffisantes.

## Impacts et risques

| Domaine                    | Impact / risque                                                                                     | Gravité | Probabilité             | Mesure proposée                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------- | ------- | ----------------------- | ----------------------------------------------------------------------------------- |
| Fonctionnel                | Une action peut devenir invisible, se chevaucher ou devenir difficile à activer sur écran étroit.   | Élevée  | Élevée avant correction | Vérifier chaque action et chaque état de la carte à 320, 360 et 390 px.             |
| Régression desktop         | Le retour à la ligne peut modifier le rendu large si les sélecteurs CSS sont trop généraux.         | Modérée | Faible                  | Limiter les règles de réorganisation au media query; vérifier à partir de 768 px.   |
| Internationalisation       | Les libellés français, souvent plus longs, peuvent révéler un débordement absent en anglais.        | Modérée | Élevée                  | Recetter en français et en anglais avec le nom d'équipement le plus long plausible. |
| Timed activation           | Le badge de temps restant non sécable et le sélecteur de durée peuvent élargir le groupe d'actions. | Modérée | Moyenne                 | Tester les états sans durée, avec sélecteur, et avec activation forcée active.      |
| Accessibilité              | Un ordre visuel modifié peut rendre les commandes ambiguës.                                         | Modérée | Faible                  | Conserver l'ordre DOM et les titres existants; contrôler les zones tactiles.        |
| Sécurité / confidentialité | Aucun impact identifié.                                                                             | Faible  | Faible                  | Aucun traitement complémentaire.                                                    |

## Hypothèses et questions ouvertes

### Hypothèses

- La carte est utilisée dans une colonne Lovelace de largeur proche de la largeur du viewport sur smartphone.
- Une largeur de 320 px reste une cible de compatibilité minimale raisonnable.
- La correction doit conserver toutes les informations plutôt que privilégier une vue condensée configurable.

### Questions ouvertes

1. Les cibles de recette doivent-elles inclure des téléphones très étroits inférieurs à 320 px, ou 320 px est-il le minimum accepté ?
2. À petite largeur, les actions doivent-elles être alignées à droite sur une seconde ligne, ou réparties sur toute la largeur pour privilégier les zones tactiles ?
3. La capture montre-t-elle aussi un débordement en mode édition de la carte ? Le signalement actuel ne permet pas de le confirmer.

## Critères d'acceptation proposés

1. À des largeurs de viewport de 320, 360 et 390 px, aucun défilement horizontal n'est créé par `solar-optimizer-card`.
2. Les cinq statistiques restent lisibles sans chevauchement ni texte rogné.
3. Pour un équipement au nom long, le nom, le badge, le sélecteur ou badge de durée, START/STOP et l'interrupteur restent visibles et activables.
4. Les détails repliés et dépliés restent lisibles, y compris la grille d'informations, la barre d'historique, RESET et le sélecteur de priorité.
5. Le rendu desktop à partir de 768 px conserve la disposition actuelle, sauf amélioration sans effet fonctionnel.
6. Les contrôles continuent d'appeler les mêmes services et entités Home Assistant qu'avant la correction.
7. La recette couvre thèmes clair et sombre, français et anglais, ainsi que les états actif, en attente et activation forcée minutée.

## Suite proposée

Après approbation de ce rapport, produire une spécification fonctionnelle et une conception technique convergentes de la correction responsive. Aucun développement ne doit démarrer avant validation explicite de ces résultats.