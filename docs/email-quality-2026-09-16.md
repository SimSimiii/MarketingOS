# Qualité des emails : diagnostic et correction

## Périmètre et run retrouvé

Le cas fourni correspond à l'asset `c09bf05c08c4466ca0d6f93cdc3936b7`, campagne
`f4f360d04d0a45199168a1ffa5fc10e5`, exécution
`206cf172c82c4ab2843a84815ab30175`, démarrée le 15 septembre 2026 à 21:54 UTC.
Inspection SQLite en lecture seule : demande, brief, métadonnées de l'email,
lectures, critique, événements et Evidence Ledger version 5. Aucun démarrage de
l'application contre cette base, aucune régénération de la campagne historique.

La demande était une **annonce de lancement à des non-clients**, preset `maximum`.
L'audience sélectionnée était **Ops or IT generalist standing up an internal Slack
answer-bot over company docs**. Le dossier de pertinence V2 était enregistré comme
actuel; le Claims Contract et ses restrictions existaient déjà. La campagne avait
été livrée `degraded` : lecture insuffisamment convaincante, puis révision moins
bien reçue. Il ne s'agissait donc pas d'un succès qualité déclaré sans réserve.

## Causes confirmées

| Point | Observation et origine |
| --- | --- |
| Deux promesses | Le brief choisit le suivi des coûts comme différenciation concurrentielle, tout en ouvrant le problème des réponses au handbook. Il suppose notamment la future question du manager sur les coûts. Cette priorité ne découle pas à elle seule de l'audience documentée. `prompts/strategist.md`, `marketing/briefs.py`. |
| Métriques avant intérêt | Le troisième choix d'ouverture dans `marketing/craft.py` demandait explicitement de laisser le lecteur comprendre seul la signification du fait concret. Le signal `solution_aware` dans `knowledge/artifacts.py` encourageait aussi une différenciation immédiate et supposait un workflow manuel. |
| Liaison ambiguë | Le writer a produit « That is what a question … on the way back ». Deux lecteurs et le critique l'ont signalée. La note était quatrième, après trois corrections prioritaires; le plafond de révision limitait les edits transmis. Ce plafond est conservé. |
| Audience | L'audience visait bien un assistant interne. Les lecteurs ont reconnu le projet, mais distingué les hypothèses supplémentaires : stack DIY précise, coûts déjà prioritaires, production déjà en place. Ce n'est pas la preuve d'un mauvais segment choisi. Le critique recevait surtout la description enrichie du Strategist, sans le segment documenté et son stade directement. `marketing/critic.py`. |
| DIY impossible | `why_it_fails` affirmait que l'assemblage ne gardait aucun compte. Un choix d'ouverture et des exemples de prompts invitaient à affirmer ce que l'approche « cannot do ». Un travail à implémenter pouvait ainsi devenir une impossibilité. |
| Coût par réponse | **Pas de conclusion « aucune preuve »** : E12 décrit des métriques agrégées, E53 les tokens et la latence par run, E73 un **coût USD estimé dans la réponse API par run**, E97 des messages de canal comptés comme runs. Leur combinaison ne prouve pas à elle seule un coût exact tout compris présenté auprès de chaque réponse Slack. Le critique historique proposait déjà E73, mais sans résoudre entièrement cette différence de surface et de qualification. |
| Sans configuration | E12 autorise le suivi Analytics sans configuration supplémentaire. Le fragment initial omettait le sujet Analytics; l'installation OAuth apparaît plus loin. La portée pouvait se lire trop largement, sans que l'absence de toute configuration soit démontrée. |
| Fin répétitive | La répétition de « one policy, one channel » et de « no card » est déjà dans les champs BODY et PS persistés du writer. `render_html.py` sépare le callout, ajoute le lien CTA, la signature et le PS; il n'invente pas ces phrases. Le critique avait identifié la répétition, mais la révision a perdu et le premier candidat a été conservé. |
| WHAT'S NEW | Champ `eyebrow` produit par le writer, avec cet exemple dans le prompt broadcast. La demande de lancement autorisait une annonce; le corps n'explicitait pas le lancement. Surtout, `render_email()` omettait le label dans le texte lu par les évaluateurs et contrôles. |

Deux défauts de transmission supplémentaires ont été confirmés dans le code,
sans les attribuer abusivement à ce run : le critique recevait l'idée d'origine
même après sélection d'une alternative; une réparation du format du writer
remplaçait la tâche initiale et perdait ainsi les consignes de révision.

## Modifications

- Réutilisation de `CampaignBrief`, `EmailBrief`, `Critique.Edit`, `GateReport` et
  Campaign Evaluation. Aucun nouveau rôle, schéma métier, table ou appel de production.
- Le writer reçoit l'interprétation de campagne. Le critique reçoit aussi le
  segment documenté, son stade, l'orientation et l'idée réellement sélectionnée.
  Les prompts précisent promesse principale, bénéfices de soutien, transitions,
  comparaison DIY, portée des claims et cohérence annonce/titre/corps/CTA.
- Les choix d'ouverture autorisent l'orientation produit immédiate; une ouverture
  technique reste possible pour une audience à qui ces métriques parlent. Les
  exemples de comparaison et la consigne de réparation sont harmonisés.
- `render_review()` assemble tous les champs de texte qui peuvent être livrés
  en texte ou HTML de marque, label compris. Il alimente lecteur, critique,
  duel, revue de séquence, révision, contrôles et évaluation qualitative.
  Une modification du label ne peut plus être considérée comme une révision inchangée.
  Le rendu de livraison demeure identique; le template n'ajoute aucun nouveau texte.
- `copy_review_gate()` produit des **alertes consultatives**, avec passage et
  correction attendue, pour certaines extensions de coût/configuration/DIY et
  répétitions entre corps, CTA et PS. Ni l'audience, ni une préférence de style,
  ni une répétition intentionnelle ne deviennent un nouveau blocage.
- Les contrôles existants sur chiffres, citations, URL et capacités interdites
  restent exécutés sur les révisions. Les consignes initiales et l'essai rejeté
  restent disponibles lors d'une réparation du format, sans augmenter les retries.
- Campaign Evaluation compare aussi les faits répétés entre corps, CTA et PS,
  et transmet les preuves et contrats déjà présents à son évaluateur qualitatif.
  Signature, identité et coordonnées du footer ne comptent pas comme répétition marketing.

## Vérification

Depuis `backend/` :

```powershell
.venv/Scripts/python.exe -m ruff check app tests
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m app.evaluation.campaign_quality_bench --campaign assistant-buyer --campaign agent-operator --campaign existing-user-announcement --campaign slack-launch-observed --out ../.scratch/email-quality/deterministic
```

Résultat final : **1 238 tests réussis**, deux avertissements de dépréciation
Starlette/AnyIO, lint sans erreur, `git diff --check` sans erreur de whitespace.
Le dry-run de `app.evaluation.judge_bench` a également été exécuté sans appel modèle.
Les tests de forecast, retries, budgets, cancellation et sélection font partie de
la suite complète; aucun changement de ces limites n'était nécessaire.

Les tests ajoutés vérifient des comportements et flux : preuve agrégée versus coût
par réponse, devise, estimation et surface API; portée de configuration; comparaison
DIY; label réellement évalué; répétition créée par assemblage HTML; exclusion du
footer; contexte reçu par le critique; feedback conservé après réparation; rejet
d'une nouvelle somme non prouvée dans la révision. Une preuve explicite du coût
par réponse est le contrôle positif. Les tests ne prétendent pas mesurer la qualité
du modèle en simulant une bonne réponse.

Les quatre nouvelles fixtures sont dans `backend/eval/fixtures/campaign_quality/`.
Trois sont synthétiques, avec leurs preuves explicites et deux variantes éditoriales;
la quatrième préserve l'email réellement retrouvé et un extrait identifié de ses preuves.
Le verdict offline `UNSAFE` de cette dernière provient d'un ancien détecteur de faits
sur le destinataire; ce résultat lexical n'établit pas à lui seul un mensonge historique.

### Évaluation qualitative réelle

Le provider Claude configuré a répondu via son SDK. Un probe limité utilise les
composants réels `ConversionCritic → EmailWriter.revise → run_all`, sur la même
fixture `assistant-buyer`, avec le même brief, preuves, demande, absence de lecture
simulée préalable et routage `sonnet` dans les deux versions. La base avant changement
correspond au backend de `2257b531338066e05f15a214cd5b1941e8cfb61d`, copié localement
sans branche ni worktree. Ce probe **n'est pas une campagne complète** et n'exécute
ni recherche, ni compilation, ni sélection de candidats.

Une première comparaison puis une seconde révision après harmonisation des derniers
exemples de prompts sont conservées, pour ne pas masquer la variance. Des revues
anonymisées distinctes comparent aussi les trois cas contrastés. La première passe
a préféré `answers-first`, `metrics-first`, `explicit-change` et la révision `after`.
Ces préférences sont des observations de modèle, pas des prévisions de conversion.

La revue anonymisée finale préfère également **after**. Le statut de cette dernière
comparaison est `PASS`; il qualifie la revue simulée, pas une efficacité marketing
mesurée. Aucun blocage déterministe sur la révision finale de la fixture.

| Essai | Appels effectifs | Tokens, cache compris | Coût équivalent USD rapporté |
| --- | ---: | ---: | ---: |
| Critique + révision avant | 2 | 19 523 | 0,113069 |
| Première critique + révision après | 2 | 26 521 | 0,173556 |
| Critique + révision après harmonisation finale | 2 | 26 093 | 0,168809 |
| Trois contrastes + première comparaison anonymisée | 5 | 31 276 | 0,2023582 |
| Comparaison anonymisée finale | 1 | 5 017 | 0,029920 |
| **Total** | **12** | **108 430** | **0,6877122** |

Un appel supplémentaire du cas `existing-user-announcement` est une correction de
sortie structurée, dans le retry existant. Les valeurs USD proviennent de la
comptabilité des appels; le provider consomme l'abonnement Claude, pas une carte API.
Ce ne sont pas des montants facturés en supplément établis par cet essai. Le probe
après consomme davantage de tokens que celui avant : la correction n'est donc pas
présentée comme gratuite en tokens, même si elle n'ajoute aucun rôle ni appel prévu.

### Exemple avant/après réellement produit

Il s'agit de **Relay, produit synthétique de la fixture**, et des sorties des
composants de révision réels, pas d'une nouvelle campagne orqAgent ni d'une
illustration rédigée à la main. Sorties intégrales :
[avant](../.scratch/email-quality/before.json),
[après](../.scratch/email-quality/after.json),
[comparaison anonymisée](../.scratch/email-quality/live-final/revision-before-after.md).

Avant, la fin associait une portée trop large à une duplication du lien :

> Analytics tracks daily spend and token usage per model automatically, so the test does not need any extra setup on your end.
>
> Try a document question.
>
> Try a document question →

Après, le corps produit est :

> A policy question lands in Slack. Someone finds the document, copies the answer, and sends it. Next week it's the same question, from someone else.
>
> Relay is a platform for building agents that answer questions from uploaded documents in Slack. You upload the document, install Relay in Slack through OAuth, and pick the channel it should watch.
>
> Analytics tracks daily aggregate spend and token usage per model automatically — nothing extra to set up for that.
>
> Upload one policy, connect one channel, and ask it the question people keep asking. See what comes back.
>
> Try a document question →

Le résultat oriente l'offre avant la preuve secondaire, indique OAuth, conserve
l'agrégation quotidienne et supprime le doublon exact de CTA. Le scénario d'ouverture
reste une généralisation éditoriale; cet échantillon ne prouve pas que toute future
révision évitera les suppositions sur le destinataire.

Reproduction locale des probes (quota réel) :

```powershell
.venv/Scripts/python.exe ../.scratch/email-quality/compare_revision.py before
.venv/Scripts/python.exe ../.scratch/email-quality/compare_revision.py after
.venv/Scripts/python.exe ../.scratch/email-quality/review_contrasts.py
.venv/Scripts/python.exe ../.scratch/email-quality/review_contrasts.py --comparison-only
```

Les scripts, prompts avant changement, sorties complètes et relevés d'usage sont
conservés dans `.scratch/email-quality/`. Les fixtures synthétiques ne sont pas
une licence pour ajouter des capacités à orqAgent.

## Limites

Les alertes lexicales nouvelles sont volontairement étroites et anglophones. Elles
ne prouvent pas l'implication sémantique; une paraphrase correcte peut encore produire
une alerte de portée à vérifier. La critique demeure nécessaire pour les inférences,
pronoms, bénéfices concurrents et conditions que le code ne peut pas établir.

La boucle garde ses budgets, plafonds et sélection existants : une révision peut
encore perdre, et un défaut éditorial peut subsister sur une livraison dégradée.
Aucun renforcement marketing n'est supprimé automatiquement. Aucun changement
d'audience, aucun appel de génération ajouté. Les prompts et éventuelles réparations
transmettent davantage de texte, donc peuvent consommer davantage de tokens.

Les jugements live portent sur un petit échantillon et un seul modèle, sans contrôle
de seed ni mesure de variance robuste. Aucune donnée réelle d'ouverture, de clic ou
de conversion n'a été produite. Changements frontend préexistants préservés;
aucun commit ni push.
