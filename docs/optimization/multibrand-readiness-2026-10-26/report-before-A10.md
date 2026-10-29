# Validation multi-marques — bilan du 27 octobre 2026

**Verdict : NO_GO pour la confirmation d’une bêta autonome fiable. Tu peux inviter ton ami à un test exploratoire accompagné, en annonçant qu’une revue des faits, des liens et du texte reste nécessaire.**

Quatre nouvelles marques ont parcouru le système depuis leur seule homepage ; chacune a maintenant un email réel. Cela montre que le parcours dépasse le premier cas de test. La qualité commerciale reste irrégulière : **0 cas complet sur 4 satisfait le protocole**, qui en exigeait au moins trois, dont un e-commerce physique et une promotion par affilié indépendant. Un email RTINGS franchit le seuil éditorial, mais ne rachète pas un amont insuffisant.

Ces notes sont mon jugement de revue sur les artefacts réels. Elles ne mesurent ni les conversions, ni la volonté de payer. Les lectures simulées du moteur restent à 6/10 et sont signalées comme non calibrées ; elles ne dictent pas les notes ci-dessous.

## Périmètre et méthode

CABAIA (FR, accessoires), Papier (EN, papeterie personnalisée), systeme.io (FR, promotion par un affilié indépendant), RTINGS (EN, éditeur affilié/abonnement). Une homepage par marque, aucun fait, lien documentaire ou CTA ajouté manuellement au générateur ; première audience exacte conservée, un email d’acquisition, stratégie auto, balanced. Maximum deux jobs modèles simultanés. Aucun email ou message envoyé.

Le protocole préalable fixe 85/100 pour un email utile, un amont utile et sourcé, et une consultation réelle des rendus et destinations. Les défauts, échecs de quota, premières versions et reprises restent archivés. Ce n’est pas un A/B intégral sur un code inchangé : les amendements A1–A9 décrivent les corrections avant retest. RTINGS a fait l’objet d’une génération diagnostique normale `{}` malgré DISCOVERY_ONLY ; le reçu conserve generated_despite_recommendation=true et override_explicit=false. Aucun generate_anyway pour obtenir un succès.

## Notes des étapes

Les notes de compilation RTINGS portent sur le périmètre abonnement réellement collecté, pas sur une couverture satisfaisante de ses articles. Une bonne note de dossier peut récompenser ses réserves factuelles sans établir un fit commercial.

| Étape /10 | CABAIA | Papier | systeme.io | RTINGS |
|---|---:|---:|---:|---:|
| Import initial conservé | 4 | 6 | 6,5 | 4 |
| Import après extraction corrigée | 7 | 7 | 6,5 | 4 |
| Compilation Knowledge | 7 | 8,5 | 7,5 | 8 |
| Catalogue de capacités | 7,5 | 8 | 8 | 7 |
| Concurrents | 7,5 | 8 | 8 | 4,5 |
| Positionnement | 8 | 7,5 | 7,5 | 6 |
| Carte d’audiences actuelle | 5 | 6 | 7,5 | 6 |
| Recherche d’audience | 6 | 5 | 8 | 2 |
| Dossier de pertinence | 8 | 8 | 8,5 | 7 |
| Génération / livraison | 6 | 7 | 8 | 7 |
| Consultation / destination / rendu | 5 | 8 | 8 | 8 |

| Email /100 | CABAIA | Papier | systeme.io | RTINGS |
|---|---:|---:|---:|---:|
| Historique des emails livrés | 71 | 82 → 84 | 79 → 83 → 84 | 86 |
| Dernier état du moteur | À revoir | À revoir | À revoir | À revoir, diagnostic |
| Cas complet validé | Non | Non | Non | Non |

Le premier run CABAIA a livré zéro email : il reste **non noté**, sans note de zéro fabriquée. Les grilles détaillées sont dans chaque email-review-N.json. Les quatre derniers emails et leurs rendus 1280/390 ont été inspectés, sans débordement horizontal.

## Ce qui reste à corriger, et dans quelle phase

**Priorité 0 — audience, dossier et stratégie.** CABAIA choisit une promesse centrale ordinateur + déjeuner + gourde dans un seul sac sans preuve du chargement simultané. Le dossier expose correctement cette lacune, mais la recommandation GO_NARROW et la stratégie continuent trop loin avec ce critère. Il faut distinguer une réserve secondaire d’un besoin définissant le segment : une sous-audience admissible doit résoudre ce besoin, pas seulement porter un nom plus général. Les témoignages de 2021, isolés, ne prouvent pas une demande actuelle.

**Priorité 0 — décision, CTA et destination effective.** Le bouton CABAIA « Voir la fiche produit » ouvre réellement la homepage, vérifiée dans le navigateur. Le résolveur effaçait une URL choisie lorsqu’une action connue n’avait pas d’URL canonique ; ce défaut générique est corrigé et testé avec conservation des contrôles de source. Le raw plan du run n’étant pas sauvegardé, je ne prétends pas que cette perte était son unique cause. Le dernier correctif est chargé, mais l’ancien asset reste inchangé et aucune nouvelle campagne ne le valide encore. Il reste à empêcher une destination manquante de devenir silencieusement une homepage sous un libellé spécifique. Papier et systeme.io demandent également une personnalisation/inscription avant de rendre la décision suffisamment tangible ; la clarification de prompt a peu changé ce choix.

**Priorité 1 — collecte et recherche de marché.** Six pages RTINGS sur huit rendent surtout des menus dans le collecteur, alors que l’article public est lisible dans le navigateur. La page tarifs systeme.io contient 248 `null` ; les offres payantes restent illisibles. Le scan RTINGS dérive vers l’achat automobile chez Consumer Reports. Il faut contrôler la substance et la pertinence des pages récupérées, puis tester un mécanisme générique de récupération pour les pages publiques concernées. Les faits vus indépendamment dans le navigateur n’ont pas été injectés pour sauver ces cas.

**Priorité 1 — rédaction.** Le contexte livres/auteurs revient après correction, mais les ouvertures restent formulées comme un exercice d’évaluation interne. Papier laisse encore passer « documented parts—not a broad promise ». Il faut produire une raison concrète d’agir, conserver une limite lorsqu’elle change la décision, et garder les commentaires de vérification dans le rapport. Le £25 Papier est bien sourcé ; sa réserve « hors brief » est distincte d’une invention de prix.

**Priorité 2 — livraison et exploitation.** Les emails français portent encore lang=en. Le routage par job fonctionne, mais les limites d’usage et les reprises supplémentaires restent une friction. systeme.io a nécessité une réévaluation normale de carte pour réparer une référence de capacité mal recopiée, puis une recherche/dossier frais. Aucun alias manuel ou changement d’audience. L’email d’affiliation utilise une URL publique vérifiée, sans lien de suivi ni conditions de rémunération inventés ; un usage réel demandera l’identité et le lien propres à l’affilié.

Ces défauts justifient le NO_GO même sans l’incident de quota. Il serait peu utile de répéter les mêmes campagnes avant de résoudre leurs causes.

## Corrections et validation

- Extraction : texte commercial des formulaires conservé, images remplacées par leurs descriptions accessibles, liens et exemples de code préservés. Les quatre homepages ont été réimportées normalement. Caractères CABAIA 242409 → 149582, Papier 188828 → 85038, systeme.io 92248 → 71817, RTINGS 29279 → 25705. CABAIA passe de 10107 caractères non lus à zéro.
- Knowledge : suppression du faux gap de prix lorsqu’un prix existe dans le registre, y compris pour les artefacts en cache ; aucune donnée source ajoutée.
- Modèles : sélection locale compile/scan/map, capacités réelles recherche + lectures Python, vérification des citations conservée ; rôles fetch non compatibles toujours refusés.
- Isolation : sous-processus Codex privé des skills/instructions et outils inutiles de la machine ; Web explicitement désactivé pour les rôles fermés. Sonde bornée conservée, sans prétendre prouver une isolation universelle.
- Stratégie/rédaction : conservation du contexte d’audience dans les alternatives et clarification du prochain pas documenté ; amélioration modeste, pas de passage du seuil sur Papier/systeme.io.
- Contrôles : nom canonique exact en capitales exempté, autres capitales et chiffres toujours contrôlés ; URL sourcée préservée pour une action sans URL, avec priorité aux URL canoniques et à celles fixées par l’utilisateur.

**1 972 tests backend passent**, Ruff app/tests propre. Frontend modifié précédemment : lint et typecheck passent, 29 tests passent ; aucune modification frontend depuis ces contrôles. Log complet de la dernière suite dans .audit-session/backend-tests-epoch7.txt. Aucun ruff format, changement de branche ou commit.

Tous les workers d’audit ont été arrêtés proprement avec active=[]. Après sauvegarde SQLite et vérification d’absence d’exécutions actives, le serveur principal a été rechargé sur le même port : santé OK, schémas des modèles locaux présents, faux gap CABAIA absent, quatre résultats persistés intacts. Le précédent refus automatique du redémarrage est donc résolu par une opération plus limitée sur le PID identifié. Les notes mesurent toujours les vrais assets produits avant le dernier correctif déterministe.

## Appels, temps et limites de comparaison

Huit tentatives de campagne, sept emails livrés sur quatre marques, un échec sans asset : **225 appels modèles terminés**. Les dernières campagnes prennent environ quatre à cinq minutes ; voir le tableau exact ci-dessous. Les étapes amont conservent séparément 136 appels terminés, en incluant baselines et reprises, pas seulement les versions retenues. Deux sondes de profil et une sonde d’isolation sont séparées. Les coûts USD sont des estimations théoriques du logiciel, pas des débits carte ou le quota restant.

| Marque / dernière tentative | Appels terminés | Durée | Livré | Note |
|---|---:|---:|---:|---:|
| cabaia | 23 | 258.48 s | 1/1 | 71/100 |
| papier | 35 | 310.93 s | 1/1 | 84/100 |
| systeme | 24 | 249.22 s | 1/1 | 84/100 |
| rtings | 28 | 300.24 s | 1/1 | 86/100 |

Un appel facultatif de recherche officielle CABAIA a été refusé avec une limite d’usage et une reprise annoncée « 6:08 AM » sans zone précisée. Les autres campagnes ont ensuite continué à réussir leurs appels ; ce refus isolé ne prouve pas un épuisement global. Aucune reprise automatique, achat de crédits ou modification de facturation.

## OpenAI partout ?

**Je recommande de conserver le choix par étape, avec OpenAI pour le parcours textuel testé et une option Claude pour la recherche ; aucune supériorité générale n’est établie.** Les campagnes utilisaient déjà OpenAI. Papier/RTINGS ont compilé leurs connaissances et exécuté leurs jobs sur GPT ; CABAIA/systeme.io gardent de la Knowledge Claude et sont des parcours mixtes. La recherche CABAIA GPT n’avait trouvé aucun texte utile ; le contrôle Sonnet sur la même audience a obtenu trois sources, anciennes et peu corroborées. Cela défend une option de recherche, pas une conclusion universelle sur les fournisseurs.

Les deux sondes de profil GPT renseignent mieux les prix, avec aussi une garantie initialement trop généralisée. Les lectures Python et les contrôles de preuve restent indispensables. 19 rôles sur 21 acceptent désormais GPT dans le catalogue ; Proof et recherche de prospects exigeant fetch restent exclus, et la lecture d’images n’est pas validée ici. Aucune préférence globale modifiée. Voir openai-comparison.md pour les sources et limites.

## Invitation proposée, non envoyée

« J’ai une version test qui part du lien d’un site pour préparer une marque, analyser son audience et produire un brouillon d’email. J’aimerais la tester avec toi sur un cas e-commerce et un cas d’affiliation. Les résultats demandent encore une revue des faits et des liens. On peut faire le premier essai ensemble. »

L’objectif du premier essai : voir où tu dois intervenir et si le brouillon est utile dans ton activité. Ce test exploratoire est possible maintenant ; il ne doit pas être présenté comme une version autonome déjà validée.

## Artefacts réels

- **cabaia** : [texte](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/cabaia/runs/8c17fb09-c07e-4537-8a07-7cf9e9988124/email-1.txt), [HTML](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/cabaia/runs/8c17fb09-c07e-4537-8a07-7cf9e9988124/email-1.html), [ordinateur](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/cabaia/runs/8c17fb09-c07e-4537-8a07-7cf9e9988124/email-1-1280.png), [mobile](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/cabaia/runs/8c17fb09-c07e-4537-8a07-7cf9e9988124/email-1-390.png).
- **papier** : [texte](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/papier/runs/a4e390d6-795c-410d-9ef6-b00d44521e6d/email-1.txt), [HTML](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/papier/runs/a4e390d6-795c-410d-9ef6-b00d44521e6d/email-1.html), [ordinateur](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/papier/runs/a4e390d6-795c-410d-9ef6-b00d44521e6d/email-1-1280.png), [mobile](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/papier/runs/a4e390d6-795c-410d-9ef6-b00d44521e6d/email-1-390.png).
- **systeme** : [texte](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/systeme/runs/58dd52d4-0560-4313-9023-dd6a0f7dc7a5/email-1.txt), [HTML](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/systeme/runs/58dd52d4-0560-4313-9023-dd6a0f7dc7a5/email-1.html), [ordinateur](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/systeme/runs/58dd52d4-0560-4313-9023-dd6a0f7dc7a5/email-1-1280.png), [mobile](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/systeme/runs/58dd52d4-0560-4313-9023-dd6a0f7dc7a5/email-1-390.png).
- **rtings** : [texte](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/rtings/runs/f7f36279-dca7-47c4-bb69-8e7f8b79aa1b/email-1.txt), [HTML](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/rtings/runs/f7f36279-dca7-47c4-bb69-8e7f8b79aa1b/email-1.html), [ordinateur](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/rtings/runs/f7f36279-dca7-47c4-bb69-8e7f8b79aa1b/email-1-1280.png), [mobile](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/rtings/runs/f7f36279-dca7-47c4-bb69-8e7f8b79aa1b/email-1-390.png).

[Protocole](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/protocol.json) · [Journal](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/journal.md) · [Comparaison modèles](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/openai-comparison.md) · [Compteurs campagnes](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/email-run-counters.json) · [Activation du serveur](C:/Users/oussa/Desktop/Workspace/projects/MarketingOS/docs/optimization/multibrand-readiness-2026-10-26/server-activation.json).
