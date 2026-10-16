# Plausible signup-goal evaluation

Inputs and official sources prepared on 2026-09-30. Quality grid: factual support 25, audience and offer clarity 20, specific persuasive argument 20, subject/body/CTA continuity 15, polish/rendering 10, unsupported promises or repetition 10.


The audience map and audience research completed (6 fetched sources, 4 verified problems). The positioning scan failed at the Claude Code session limit, so no V2 relevance dossier exists. Generate as an explicitly recorded audience-level hypothesis using the campaign's GPT subscription preset; this tests copy quality, not qualified market fit.


## Iteration 1 — below_sellable_bar

**79/100** (first scored iteration; best 79, run 47646674-abb6-49fe-8a87-1ad7202cc62d). Official goal-conversion facts are correctly explained and the CTA reaches the exact guide. Desktop and true 375px mobile HTML render without horizontal overflow. Remaining defect: The email spends its opening on configuration, assumes trial signup as the recipient situation, and does not show a valuable decision that justifies setup. Evidence: 1/1 delivered; clean gates; simulated pull 5/10; one reader mismatch; $3.9805 estimated; E68/E70 verified on Plausible official guide. Next: Lead with the business question answered by goal attribution; state the setup boundary and condition trial use.

## Iteration 2 — below_sellable_bar, qualified-market track

**83/100** (new dossier track; first score on this track, best 83, run 7f298688-93bc-45b8-9f93-341305f159e1; the earlier unqualified score was 79). The opening now explains the decision value: conversions by referrer and entry page. The confirmation-page versus custom-event path is conditional and factual, with one exact official-guide CTA; true 375px mobile rendering has no overflow. Readers still cannot tell whether the guide helps them assess their existing site before adopting Plausible, and the message remains mainly configuration guidance. Evidence: 1/1 clean delivered, simulated pull 6/10, all readers understood and found it relevant, $3.8762 estimated; the new dossier says GO_NARROW. Next: make the pre-adoption assessment useful in the email and avoid implying that signup attribution measures paid customers.


## Itération 3 — préparation (2026-10-02, coordinateur Claude, validation croisée)

Conditions changées : tous les rôles sur Opus (quota Codex épuisé) ; correctifs issus du cas `buffer-flexible` : marge de 3 ouvertures avant de remplacer l'objet, objets sans fausse familiarité, rédacteur sans P.S. de non-promesse ni absolu non étayé, stratège qui ne décrit pas un mécanisme plus précisément que les faits assignés. Dossier de pertinence inchangé (encore « current », construit avant les correctifs de contrat, qui ne s'appliqueront qu'à sa reconstruction). Hypothèse : les correctifs de prompts se transfèrent sans régression ; le défaut connu (email perçu comme un mode d'emploi, valeur avant installation peu claire) n'est pas ciblé par ces correctifs, donc un gain n'est pas attendu sur ce point. Score comparable sur la piste existante, avec le modèle noté comme variable confondue.

## Itération 3 — 80/100 (meilleur reste 83)

Exécution `b4b906e3-d44f-4ffa-a440-d2da21f957dd`, Opus. Les correctifs venus de Buffer se transfèrent sans régression : objet honnête, pas de P.S. défaitiste, rien d'inventé ; l'email ouvre sur le résultat utile (sources et pages d'entrée des inscriptions, E68) plutôt que sur la configuration. Défaut principal : il est écrit pour un utilisateur existant alors que la demande présente Plausible à un prospect. « Without a code change » et « pageviews are already collected » (E71) ne valent qu'après installation du script (E35) ; les trois lecteurs l'ont relevé. Preuves : 1/1, propre, pull 6/10, 9 appels, 2,2742 USD.

Diagnostic avant correction : aucune règle du rédacteur ne distingue un fait écrit pour les clients (documentation) de ce qu'il signifie pour un non-client. Hypothèse : une règle dans `writer.md` — présenter le produit à un non-utilisateur, c'est dire que ces faits décrivent la situation après adoption et nommer l'étape documentée qui vient d'abord — supprime l'ambiguïté. Résultat attendu : l'email dit qu'après l'ajout du script Plausible, un objectif de type page vue ne demande aucun code supplémentaire.

## Itération 4 — 72/100 (meilleur reste 83)

Exécution `22dfb06b-6bb8-4552-b68c-3162495b8416`. Le correctif « faits clients lus par un non-client » a déplacé l'argument vers une vraie valeur avant installation : la démo publique avec de vraies inscriptions (E29), présentée honnêtement. Mais le bouton dit « View live demo » et pointe vers le guide `goal-conversions` choisi par l'utilisateur ; la première étape de configuration demandée a disparu ; la première ligne du corps répète l'objet. Preuves : 1/1, propre, pull 7/10, 9 appels, 2,066 USD ; `href` vérifié dans `email.html`.

Diagnostic avant correction : `campaign.cta_url` n'atteint que le rendu HTML (`style_for_action`) ; ni `CampaignRequest` ni le contexte du stratège ne le contiennent, donc le plan choisit librement une action de l'offre puis le bouton est redirigé. Correctif : `CampaignRequest.cta_url`, rendu dans `render_context()` (« l'action de chaque email doit décrire ce que le lecteur trouve sur cette page »), transmis par les deux constructions de l'orchestrateur ; tests ajoutés ; 1 383 tests, Ruff propre. Résultat attendu : un CTA vers le guide, avec la première étape demandée.

## Itération 5 — 83/100 (= meilleur)

Exécution `48c8f8b4-8e58-4920-a4b9-c12f5b01d6ae`. Le correctif `cta_url` a tenu : « Read the goal-conversions guide » pointe vers le guide, et la première étape demandée (objectif page vue sur la page de confirmation, E70/E71) est revenue. Défaut restant : toujours écrit pour un utilisateur existant (« no code changes, since Plausible collects pageviews automatically » sans le script E35) ; les trois lecteurs demandent si cela les concerne. La règle de `writer.md` n'a pas pris. Preuves : 1/1, propre, pull 6/10, 9 appels, 2,247 USD.

Correction : porter la règle dans le contrat d'étape suivante du stratège (`strategist.md`) ; pour un lecteur qui n'utilise pas encore le produit, `next_step_limit` ou `mechanism` doit nommer l'étape d'adoption documentée qui précède un bénéfice côté utilisateur. Le brief rendu au rédacteur la portera.

## Itération 6 — 74/100 (meilleur reste 83)

Exécution `420b68e1-da5a-4072-92e7-72bcac15bbcd`. Le prérequis d'adoption apparaît enfin, mais en P.S. défaitiste (« seeing your own numbers takes Plausible running on your site ») : l'avoir routé par `next_step_limit` a réveillé le défaut corrigé sur Buffer. L'angle (« votre total compte des bots ») présume l'outil actuel du lecteur, ce que la demande interdit. Pull 5/10, 9 appels, 2,4167 USD.

Correction : le prérequis va dans `mechanism` comme condition positive (« une fois son script sur votre site, … ») et non dans `next_step_limit` ; `writer.md` précise qu'il s'énonce dans le corps, jamais comme une non-promesse.

## Itération 7 — 80/100 (meilleur reste 83) — arrêt des relances sur cette demande

Exécution `4c209489-4d1e-4977-ac23-5ad629a07f82`. L'argument le plus spécifique à ce jour : une inscription qui se termine sans nouvelle page échappe à un objectif page vue, d'où l'événement personnalisé (E65) ; prérequis énoncé comme condition dans le corps, sans P.S. ; CTA conforme au guide. Restent : le script Plausible n'est toujours pas nommé comme première étape, et « Most signup tracking keys on a page load » est une généralisation non étayée. Pull 6/10, 9 appels, 2,0108 USD.

Décision : les itérations 3 à 7 oscillent entre 72 et 83 et chaque correctif déplace le défaut ; la variance d'un run à l'autre domine. La tension vient de la demande elle-même : elle envoie un prospect lire un guide de configuration. L'itération 4 a trouvé l'étape avant adoption la plus forte (démo publique avec de vraies inscriptions, E29). Changer le CTA de la demande relève de l'utilisateur ; aucune nouvelle génération n'est achetée sans cette décision.

## Reprise — 2026-10-05, OpenAI

Audit des modifications Claude : conservation des corrections de contrat, du passage de cta_url au stratège et des protections objet/affirmations. Retour des presets à gpt-5.6-sol et du fournisseur local de secours à OpenAI. Reprise explicitement autorisée par le skill : le précédent arrêt sans seuil atteint est historique. Hypothèse : les règles déjà ajoutées sur le prérequis et la destination peuvent fonctionner avec le modèle OpenAI ; une génération sur les mêmes entrées le vérifie. Nouvelle piste openai_resume_2026_10_05, non comparable aux scores Opus. Aucun changement de CTA requis pour cette première mesure.

Validation de la reprise : 1 383 tests passent, Ruff app/tests propre, git diff --check sans défaut de contenu. Les préférences locales /settings sont désormais openai / gpt-5.6-sol ; presets restaurés à la version validée de HEAD. Connexion Codex via ChatGPT vérifiée.

## Iteration 8 — 85/100, sellable in the requested scope

New OpenAI track (not comparable to Opus): first and best score 85, execution f2e0a144-8936-47bb-9136-af932b92f7d7. Grid 25/17/11/13/9/10. The conditional prerequisite now appears in the claim itself; the reader can check their confirmation URL first. E67/E68/E71 support the reported conversion breakdown; the button links to the exact requested guide. Argument is functional and restrained; the non-pageview route is left to the guide. No material false claim or broken CTA. Mobile 375px reviewed, no overflow. 8 GPT calls, $5.0589 estimated; 1383 tests pass and Ruff is clean. Verdict: usable after normal brand review for this introduction. Next: check transfer to Buffer on the restored GPT default. Historical quality_best remains 83 on its earlier track; new track best is 85.
