# Revue de l’issue #212 — Ajouter le domaine `water_heater`

## Référence et résumé fidèle

- Issue : [#212 — Add water_heater domain](https://github.com/jmcollin78/solar_optimizer/issues/212)
- État consulté : ouverte ; étiquette `enhancement` ; aucun assigné, jalon, projet ni relation indiqués.
- Branche de développement liée dans l’issue : [`212-add-water_heater-domain`](https://github.com/jmcollin78/solar_optimizer/tree/212-add-water_heater-domain).

La demande est d’autoriser les entités du domaine Home Assistant `water_heater` lors de la configuration d’un appareil géré par Solar Optimizer. Le besoin porte en particulier sur l’utilisation du service `water_heater.set_operation_mode`, avec par exemple les modes `off`, `automatic` ou `eco`.

Le demandeur précise qu’il ne souhaite pas piloter deux entités : il veut sélectionner l’entité de chauffe-eau qui expose son mode de fonctionnement, plutôt qu’un switch distinct. Une solution de contournement par switch template a été proposée, mais l’auteur de l’issue confirme que l’ajout du domaine est la fonctionnalité recherchée.

## Sources et éléments vérifiés

### Issue GitHub

- La description demande explicitement l’ajout du domaine `water_heater`.
- Les commentaires convergent vers un périmètre limité à ce domaine ; l’issue a été rouverte et marquée comme amélioration après clarification.
- La branche liée existe, mais son fichier `config_schema.py` accessible publiquement conserve la même liste de domaines que le dépôt local : aucun changement fonctionnel n’y est encore visible.

### Dépôt local

- `managed_device_schema` dans `custom_components/solar_optimizer/config_schema.py` filtre les entités sélectionnables. Il inclut notamment `humidifier`, `climate`, `fan`, `light`, `select` et `button`, mais pas `water_heater`.
- `SolarOptimizerBaseConfigFlow.async_step_device` utilise directement ce schéma : le filtre du sélecteur est donc la cause du comportement signalé.
- `ManagedDevice.do_service_action` accepte déjà le format `domaine/service/cle:valeur` et transmet la clé-valeur comme données de service. Il peut ainsi appeler `water_heater/set_operation_mode/operation_mode:eco` sans modification du moteur d’appel.
- `tests/test_non_switch_device.py` couvre le précédent comparable `climate`, y compris les appels `set_hvac_mode` avec données de service. Ce test constitue l’ancrage adapté pour une régression `water_heater`.
- Le type d’appareil "powered device" ne sélectionne pas `select` ni `button` et ne doit pas être étendu implicitement : l’issue demande l’ajout d’un domaine pour l’appareil géré standard, sans contrôle variable de puissance.

## Pertinence et recommandation

**Recommandation : retenir.**

L’issue corrige une restriction de configuration sans modifier le comportement d’optimisation ni les interfaces de service. Elle permet un cas d’usage cohérent avec le support existant de `climate` et avec le mécanisme générique d’appel de services déjà en place. Le changement est local, faisable et testable.

## Périmètre proposé

### Inclus

- Ajouter la constante de domaine Home Assistant `water_heater` dans `custom_components/solar_optimizer/config_schema.py`.
- Autoriser ce domaine dans le sélecteur de `managed_device_schema`.
- Ajouter un test de régression couvrant la création d’un appareil `water_heater.*`, puis les appels d’activation et de désactivation via `water_heater.set_operation_mode` avec les données `operation_mode` attendues.
- Mettre à jour `README-fr.md` et `README.md` afin d'ajouter `water_heater` aux domaines des appareils standards et un exemple complet utilisant `water_heater/set_operation_mode/operation_mode:<mode>`.

### Exclus

- Ajouter `water_heater` au schéma `power_managed_device_schema` : les chauffe-eau ne sont pas dans le besoin exprimé de modulation de puissance et aucun contrat de puissance compatible n’est démontré.
- Gérer simultanément plusieurs entités pour un même appareil Solar Optimizer.
- Ajouter une interface dédiée aux modes de chauffe-eau ou modifier la syntaxe générique des services.
- Modifier les entrées de configuration déjà créées, les dépendances, le moteur d’optimisation ou la carte frontend.

## Impacts et risques

| Domaine                      | Impact ou risque                                                                                                                                                                                       | Gravité | Probabilité | Mesure proposée                                                                                   |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------- | ----------- | ------------------------------------------------------------------------------------------------- |
| Fonctionnel                  | L’utilisateur pourra sélectionner une entité `water_heater` et l’utiliser avec les services configurables existants.                                                                                   | Faible  | Élevée      | Test d’intégration ciblé sur activation et désactivation.                                         |
| Validation de configuration  | Le filtre UI est étendu, sans validation explicite de la disponibilité des services ou des modes choisis. Une faute dans le nom du service ou du mode est signalée par Home Assistant lors de l’appel. | Modérée | Moyenne     | Conserver la convention actuelle ; documenter un exemple.                                         |
| Compatibilité Home Assistant | La constante et le domaine `water_heater` doivent être disponibles sur toutes les versions de Home Assistant prises en charge par le projet.                                                           | Modérée | Faible      | Vérifier les contraintes de version du manifeste et exécuter la suite dans l’environnement cible. |
| Régression                   | Une importation ou une liste de domaines mal modifiée peut empêcher le chargement du flux de configuration.                                                                                            | Modérée | Faible      | Exécuter le test ciblé et la suite de tests concernée.                                            |
| Sécurité et confidentialité  | Aucun nouveau secret, accès réseau ou flux de données ; l’intégration pourra appeler des services d’un équipement supplémentaire configuré par l’utilisateur.                                          | Faible  | Faible      | Aucun traitement additionnel.                                                                     |
| Exploitation                 | La sémantique exacte des modes est propre à chaque intégration de chauffe-eau.                                                                                                                         | Faible  | Moyenne     | Laisser les services et valeurs configurables, sans imposer une liste de modes.                   |

## Alternatives examinées

1. **Switch template Home Assistant**
   - Avantage : utilisable sans modification de Solar Optimizer et peut traduire des modes vers `on`/`off`.
   - Inconvénient : ajoute une entité de maintenance, masque l’entité de chauffe-eau et ne répond pas directement au besoin d’utiliser son mode de fonctionnement.

2. **Autoriser tous les domaines dans le sélecteur**
   - Avantage : évite de futurs ajouts unitaires.
   - Inconvénient : expose des entités dont la gestion par activation/désactivation n’a pas de sens et dégrade le guidage du formulaire.

3. **Ajouter seulement `water_heater` au schéma d’appareil standard**
   - Avantage : répond exactement à la demande, préserve les limites du type à puissance variable et suit la liste fermée existante.
   - Inconvénient : de nouveaux domaines compatibles nécessiteront encore une évolution explicite.

La troisième option est recommandée.

## Hypothèses, décisions nécessaires et questions ouvertes

### Hypothèses

- Les versions de Home Assistant prises en charge exposent `homeassistant.components.water_heater.DOMAIN`.
- Les utilisateurs renseignent les services et paramètres correspondant à leur intégration de chauffe-eau, notamment `water_heater/set_operation_mode/operation_mode:eco` et son équivalent de désactivation.
- Le test peut vérifier les appels de service sans exiger un composant `water_heater` physique chargé dans le banc d’essai, comme le test `climate` existant.

### Questions ouvertes

1. Les modes par défaut attendus pour l’exemple (`eco`, `automatic`, `off`) sont-ils suffisamment représentatifs, sachant qu’ils varient selon l’intégration Home Assistant ?

Aucune de ces questions ne bloque l’implémentation minimale.

## Critères de passage au développement

1. Le périmètre limité à `managed_device_schema` est approuvé.
2. Un test de régression démontre que les appels `water_heater.set_operation_mode` reçoivent la cible et les données configurées.
3. Les README français et anglais citent le domaine `water_heater`, fournissent un exemple d'activation `eco` et de désactivation `off`, et précisent que les modes dépendent de l'intégration Home Assistant.
4. Le test ciblé et la suite de tests pertinente passent dans l’environnement cible.
5. La compatibilité de l’import `water_heater.DOMAIN` avec la version minimale de Home Assistant du projet est confirmée.

## Suite proposée

Après validation explicite de ce rapport, produire une spécification fonctionnelle et une conception technique convergentes, puis demander une autorisation explicite avant de commencer le développement.
