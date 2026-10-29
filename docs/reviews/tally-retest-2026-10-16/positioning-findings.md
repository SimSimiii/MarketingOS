# Retest du positionnement — données Tally réelles

Vérification locale sans appel modèle, sans crawl, sans écriture dans la base et sans modification du code produit. Les exports proviennent de la marque `Tally--Test` et contiennent l'email « Put Tally before your automation ».

## Résultat

Les corrections retirent plusieurs conclusions injustifiées, mais le positionnement Tally n'est pas encore fiable dans son ensemble.

| Symptôme de l'analyse externe | Statut observé |
| --- | --- |
| Deux témoignages considérés identiques parce que classés `proof` | Corrigé pour la comparaison testée. La reconstruction réelle ne classe plus les sept preuves Tally en `table_stakes`. |
| Une absence devient « Where the field is ahead of us » | Formulation corrigée. La vue dit maintenant que l'information est inconnue et ne prouve aucune supériorité. |
| Devises, périodes et unités explicitement incompatibles | Corrigé dans les cas simples testés : euro/dollar, mois/an, utilisateur/espace. |
| Domaines personnalisés et retrait de marque absents de `control` malgré la documentation | Toujours défaillant, confirmé sur les vrais faits Tally et sur deux reproductions synthétiques. |
| Conditions commerciales nécessaires à la comparaison | Partiel. `billed annually` est reconnu ; `billed yearly`, `annual payment required` et `facturé annuellement` sont ignorés quand le contexte structuré n'est pas renseigné. |
| Comparaison d'un concurrent publiée par Tally | Toujours défaillant dans la sélection des affirmations de la marque, même avec un contexte structuré explicite. |
| Vocabulaire ordinaire des formulaires pénalisé | Corrigé pour le cas testé : `form`, `submissions`, `data`, `integrations`, `free` n'entraînent aucune suggestion de réécriture. |
| Synthèse liée à l'audience et au workflow précis | Partiel. `build()` ne reçoit aucune audience et produit un inventaire de propositions, sans calculer le prix du workflow retenu ni prioriser ses critères. |

## Trois défaillances reproductibles

### 1. Le contrôle de marque reste classé ailleurs et évincé de la sélection

Le corpus réel contient notamment :

- `E296` : « Pro plan removes Tally branding so forms are fully your own », avec la citation de la page tarifaire « Remove Tally branding. Hide all branding and make your forms truly your own. »
- `E297` : « Pro plan allows hosting forms on a custom (sub)domain for branded links », avec la citation « Custom domains. Host forms on your custom (sub)domain to create branded links. »

Ces deux faits sont classés `other` puis écartés par le plafond global de 30 affirmations. `E126`, « Tally supports custom domains for forms », est classé `breadth` à cause de `supports`. La reconstruction actuelle conserve **six lignes concurrentes `control/exposed/unknown`, sans aucune affirmation Tally sur cet axe**.

Même avec un seul fait, le problème existe : la phrase synthétique « Use a custom domain for your forms » est classée `other` dans notre corpus ; la même phrase étiquetée `control` chez un concurrent devient une absence de notre côté. La comparaison exige une égalité d'axe avant de regarder la proposition.

Causes : `positioning.py:546` (vocabulaire de contrôle), `positioning.py:561` (classification), `positioning.py:382` et `positioning.py:412` (classement et plafond), `claims.py:216` (égalité d'axe obligatoire).

### 2. Une condition annuelle explicite peut disparaître de la comparaison

Reproduction synthétique : même résumé « Pro plan costs $29 per user per month » dans les deux affirmations ; seule la citation de la première ajoute une obligation annuelle.

| Ajout dans la citation | Résultat actuel |
| --- | --- |
| `billed annually` | `potential_difference` — correct |
| `billed yearly` | `equivalent` — incorrect |
| `annual payment required` | `equivalent` — incorrect |
| `facturé annuellement` | `equivalent` — incorrect |

Le contexte structuré permettrait de conserver la condition, mais les **380 faits du corpus Tally sauvegardé ont `context: null`**. Le parseur de secours n'identifie que quelques formulations littérales ; il ne transforme pas une condition non reconnue en information inconnue.

Cause : `claims.py:304` (`_conditions`).

### 3. Les prix des concurrents deviennent nos propres arguments

La reconstruction réelle sélectionne **neuf affirmations sur Typeform, Jotform ou Google Forms parmi les trente affirmations censées représenter Tally**, par exemple :

- « Google Forms charges $14+/month for its AI form builder » ;
- « Typeform charges $39+/month for unlimited responses » ;
- « Jotform requires a $34+/month plan for conditional logic ».

Elles viennent de `https://tally.so/help/compare` et apparaissent comme `price/open/unknown` dans **notre** positionnement. Leur simple lecture ne vérifie pas les tarifs chez ces concurrents.

La reproduction synthétique ajoute explicitement `subject='Typeform'`, `source_kind='vendor_comparison'` et `claim_scope='comparison'`. Le défaut reste présent : `claims_from_knowledge()` retient la comparaison comme une affirmation de Tally. De plus, le rendu stratégique utilise `claim.text`, ce qui ne reprend pas l'avertissement d'attribution fourni par `Claim.render()`.

Causes : `positioning.py:367` (sélection de nos affirmations), `positioning.py:82` (rendu sans contexte). La protection de `compare_claims()` fonctionne lorsqu'une paire est effectivement comparée, mais ne protège pas cette sélection préalable.

## Volume et utilité de la synthèse

Sur les données exactes :

- Carte sauvegardée : **10 catégories**.
- Carte reconstruite avec le code actuel : **158 propositions**.
- Nos 30 affirmations : **18 prix, 7 preuves, 5 autres**, aucun élément `control`, `breadth` ou `effort`.
- Section stratégique : **5 459 → 47 623 caractères**, en appliquant le rendu actuel à la carte sauvegardée puis à la carte reconstruite.

Le nombre d'appels ne change pas, mais `strategist.py:333` injecte cette section entière. Ce constat mesure un volume de texte, pas un coût ni une latence de modèle : aucun appel réel n'a été effectué. La hausse d'environ 8,7 fois pour cette section et la faible priorité donnée aux capacités pertinentes restent contraires à l'objectif d'aider à décider avec moins de vérifications.

## Vérifications et fichiers

- Suites existantes ciblées : **89 tests réussis** (`test_positioning`, `test_positioning_integrity`, `test_proposition_comparisons`, `test_radar`, `test_sameness`).
- Probes d'acceptation séparées : **7 réussies, 8 échouées**, couvrant les trois causes restantes ci-dessus. Les échecs restent en dehors de la suite normale.
- `positioning_probe.py` : cas synthétiques explicitement identifiés et vérifications sur les exports réels.
- `positioning-probe.xml` : résultats détaillés du lancement pytest.
- `positioning-replay.json` : anciennes données, reconstruction actuelle, faits pertinents et briefs complets.

Commande depuis `backend/` :

```powershell
.venv/Scripts/python.exe -m pytest ../docs/reviews/tally-retest-2026-10-16/positioning_probe.py -q --tb=short
```
