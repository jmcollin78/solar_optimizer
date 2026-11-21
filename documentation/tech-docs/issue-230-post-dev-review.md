# Revue post-developpement - Issue #230

## 1. Decision proposee

**Approuver sous reserve du risque accepte ci-dessous.** La suite passe et l'essentiel des criteres est implemente. Le coordinateur ne revalide pas une contrainte HC capturee au debut du cycle avant chaque arret; l'utilisateur a explicitement confirme que cette verification en cours de cycle n'est pas necessaire et accepte cette limite.

Cette decision humaine leve la demande de correction pour ce point. Aucun changement de code n'est demande par cette revue.

## 2. Perimetre et reference

- Issue : [#230](https://github.com/jmcollin78/solar_optimizer/issues/230).
- Reference examinee : commit `2a310a4d28cfed16cdebee6ed2cb281dc1fc958d` (`Development ok`), parent `4db12d3`.
- Branche : `230-do-not-liberate-power-when-a-device-is-turned-off-and-doesnt-consume-power`.
- Arbre de travail : propre au debut de la revue.
- Exigences : [specifications approuvees](issue-230-specifications.md), RG-001 a RG-013 et AC-001 a AC-012.
- Fichiers du commit : `coordinator.py`, `simulated_annealing_algo.py`, `test_power_device.py`, `test_timed_activation.py`, les README francais/anglais et les documents de revue/specification #230.

La comparaison `origin/main...HEAD` inclut egalement des changements anterieurs #231. Les constats ci-dessous portent sur le commit `2a310a4` et son parent direct, pas sur ces changements anterieurs.

## 3. Constat

### Moyen - Le forcage HC n'est pas revalide avant la commande d'arret (risque accepte)

**Emplacements :** [instantane de cycle](../../custom_components/solar_optimizer/coordinator.py#L246), [lecture de la decision HC pendant l'application](../../custom_components/solar_optimizer/coordinator.py#L334), [condition et commande d'arret](../../custom_components/solar_optimizer/coordinator.py#L363).

Le coordinateur capture `should_be_forced_offpeak` dans `cycle_states`, classe le plan a partir de cette valeur, puis reutilise le meme instantane pour chaque commande. Apres une commande precedente, l'`await` peut laisser d'autres taches Home Assistant modifier l'etat ou une condition temporelle avant le traitement de l'appareil suivant. L'arret est alors execute sans relire sa contrainte HC effective.

RG-003 exige que tout changement de contrainte detecte avant une commande soit revalide. Dans le scenario ou un arret etait admissible lors de l'instantane mais le forcage HC devient effectif avant cet arret, le coordinateur peut quand meme appeler `deactivate()`, en violation du forcage. Les activations resteront bloquees par le plan initial, ce qui evite le transfert de puissance mais ne corrige pas l'arret devenu interdit.

**Decision utilisateur (2026-11-21) :** ce risque est accepte; il n'est pas necessaire d'ajouter une revalidation en cours de cycle. Cette acceptation porte sur ce comportement precis et ne change pas les autres exigences ni les resultats de tests rapportes.

## 4. Points positifs et autres observations

- T01 utilise le vrai recuit et le vrai coordinateur; il a ete constate rouge avant les changements de production, puis vert dans les deux modes HC et les deux ordres d'appareils.
- Les tests ajoutent les arrets multiples, les maintiens, l'activation HC reportee, l'absence de commande de puissance associee, les expirations de timer, les erreurs/retards d'arret, le recalcul sans replay et la variation de puissance d'un appareil restant actif.
- Le plan brut du recuit n'est pas mute par le filtrage; les activations differees sont journalisees et ne sont pas rejouees automatiquement.
- La mesure individuelle reste optionnelle, sans attente d'une nouvelle mesure globale ni migration de configuration.
- Aucun autre defaut bloquant ou eleve n'a ete etabli dans le perimetre examine.

## 5. Validations et limites

- `rtk pytest tests -q -p no:cacheprovider` : **213 passes, 0 echec, 11 ignores**.
- Diagnostics VS Code sur les quatre fichiers Python examines : aucun diagnostic rapporte.
- `rtk git show --check --oneline HEAD` : aucun probleme de whitespace signale.
- Controle Black non execute : le binaire et le module Python `black` ne sont pas installes dans l'environnement (`No module named black`).
- HACS et Hassfest ne sont pas executes localement; ils figurent dans le workflow PR. Le workflow `pull.yml` desactive son propre job tests, mais `testus.yaml` execute la suite sur les pull requests; la suite a ete lancee localement ici.
- Aucun test ni essai sur une installation Home Assistant reelle; les tests utilisent l'environnement simule du depot.

La couverture ne comprend pas le changement d'une contrainte HC entre la capture de l'instantane et l'application d'une commande; cette limite est acceptee par l'utilisateur. La mesure nette stale et les variations spontanees de charge restent egalement des limites fonctionnelles documentees de la solution.

## 6. Actions suivantes et decision humaine

1. Aucune correction de code n'est demandee pour le risque accepte.
2. Conserver cette decision avec le dossier #230; les tests et validations listes ci-dessus restent les preuves de la revue.

La recommandation est l'approbation sous reserve de ce risque accepte; elle ne constitue pas une approbation de release ni une recette sur l'installation reelle.