# SavvyCal — audit depuis la seule URL principale

19 octobre 2026, heure de Paris. **Test terminé : génération en échec, zéro email livré.**

Ce rapport conserve le test initial. Une correction ultérieure du mécanisme,
suivie d'une relance à entrées identiques livrant 1/1 email à revoir, est décrite
dans [le rapport de correction](savvycal-material-veto-fix-2026-10-19.md).

Le parcours a été exécuté depuis la homepage jusqu'à une vraie génération. La
recherche et le dossier sont utilisables, mais la chaîne ne remplit pas la
demande d'un email : après trois brouillons, une recherche officielle et une
nouvelle stratégie, elle retire le résultat pour un manque de matériel invoqué
par le critique. Aucun résultat ni fait produit n'a été retouché pour terminer
le test. Aucun code de production n'a été changé pendant cet audit.

Entrée unique : https://savvycal.com/. Nouvelle marque :
d495350c-c622-4bba-b634-a53ba44bbcd5.
Première audience proposée par la carte, demande générique d'un email d'acquisition
en anglais, stratégie auto et preset balanced. Aucun fait, sous-lien ou CTA ajouté
par l'évaluateur aux données du système. Aucun email envoyé.

Le code courant utilise les routes API réelles dans un worker ASGI persistant,
sans serveur réseau ni lifespan. Les handlers, contrôles, services, modèle et DB
sont ceux de l'application. Les scripts audit_brand_flow.py et optimize_campaign.py
restent les opérateurs de capture. Les serveurs ouverts ne sont pas redémarrés.
Ce protocole teste les fonctions courantes ; il ne prouve pas leur activation dans
un ancien processus de serveur. La consultation de l'exécution a aussi été
vérifiée sur le vrai frontend et son proxy, sans interception des requêtes.

Cas et traces : [savvycal-root-url-2026-10-19](../optimization/savvycal-root-url-2026-10-19/).

| Étape | Note | Faits et limites |
|---|---:|---|
| Import autonome | 7,5/10 | 11 pages, 3 986 mots ; docs/developers et trois guides détaillés ; texte des prix sans liaison explicite à la facturation annuelle et FAQ repliée non lue |
| Compilation Knowledge | 7/10 | 114/114 citations retrouvées ; fonctions et restrictions Premium comprises ; montants des plans absents du ledger malgré leur présence dans le résumé et aucun gap signalé |
| Catalogue de capacités | 7/10 | 89 capacités liées au ledger ; doublons et inférences de colonnes tarifaires encore étiquetées verified |
| Concurrents | 8/10 | Cinq fournisseurs plausibles, 132 affirmations vérifiées ; prix Calendly absents et une comparaison API/DNS fragile |
| Positionnement | 5,5/10 | Zéro différence documentée annoncé honnêtement ; rapprochement sémantique faible, doublons et granularité classée comme vitesse |
| Carte d'audiences | 6,5/10 | Six segments, neuf pages vérifiées ; contre-arguments explicites, mais angle « free tier » incohérent avec l'activation payante |
| Recherche de la première audience | 7/10 | Six sources, cinq problèmes, huit expressions ; quatre échecs signalés, faible corroboration et dates manquantes explicites |
| Relevance dossier | 7,5/10 | Cinq correspondances PARTIAL, GO_NARROW ; limites et Premium conservés, mais quelques étiquettes open et une formulation de nouveauté restent ambiguës |
| Génération et livraison | 2/10 | 25 appels, 5 min 59 s, trois brouillons ; dernier brouillon sans échec automatique, puis retrait pour missing_material ; zéro email livré |
| Restitution du résultat | 6/10 | Écran lisible sur 1440/390 px, aucun débordement ni erreur JS ; message « avant les brouillons » inexact et score 0,0 trompeur faute de livrable |
| Qualité de l'email final / rendu HTML | Non notée | Aucun asset livré ; les brouillons de diagnostic ne remplacent pas un email final |

Notes éditoriales sur 10 : couverture, fidélité et utilité. Email final sur 100,
grille 25/20/20/15/10/10. Aucun score avant résultat inspecté ; aucune prédiction
de conversion réelle. Les lecteurs simulés seront distingués de cette revue.

## Vérification indépendante des prix

La page de prix affiche par défaut la facturation annuelle (bouton Annual activé).
Les prix visibles sont 10 et 17 USD/utilisateur/mois ; le bouton Monthly affiche
12 et 20 USD. Le texte importé n'explicite pas ce lien. La FAQ ouverte dans le
navigateur précise que l'inscription et les sondages de rendez-vous sont gratuits,
mais qu'activer des liens de réservation exige de payer. Le remboursement est
possible pendant les trente premiers jours.

Ces observations d'évaluation sont sauvegardées dans pricing-browser.json et les
captures associées, **sans être fournies au compilateur ou aux autres rôles**.
Elles servent à juger les omissions et les éventuelles affirmations en aval.

## Compilation

Le contrôle gratuit retrouve 114 citations sur 114 dans leur document d'origine.
Le compilateur a rejeté deux candidats non vérifiables ; leurs contenus ne sont
pas conservés dans ce snapshot, donc on ne leur attribue pas une cause plus précise.
La garantie de remboursement de trente jours est conservée comme telle. Les
domaines personnalisés sont correctement rattachés à Premium, et les guides sur
les buffers et le group mode ont été compris.

La faiblesse commerciale reste visible : Basic et Premium portent 10 et 17 USD
dans le résumé sans expliciter la cadence annuelle, et aucun montant monétaire
n'est présent dans le ledger. Les gaps sont pourtant vides. Les indices de
réduction annuelle sont séparés, sans liaison complète aux prix. Le système doit
donc éviter de transformer ces valeurs en prix de facturation mensuelle.
Trace de contrôle : knowledge-review.json. Six appels terminés, 7 min 34 s,
80 759 jetons entrants et 91 674 sortants rapportés. Compteurs d'adaptateur,
pas facture API ni volume de texte unique.

## Marché et catalogue

Le scan commun Positioning/Competitors termine en 5 min 06 s, avec six appels
terminés. Calendly, Cal.com, Acuity Scheduling, Doodle et Google Calendar sont
des alternatives plausibles. Le sixième choix est le statu quo email/Slack,
conservé sans inventer de site. Les cinq profils apportent 132 affirmations
retrouvées dans les pages capturées. Les raisons de comparaison citent les deux
côtés et restent des hypothèses, pas des preuves de préférence acheteur.

Les limites sont précises : les prix Calendly ne sont pas capturés ; opposer
l'API Cal.com aux faits SavvyCal sur DNS et HubSpot compare mal les fonctions.
La promotion Google commence le 1er novembre 2026, donc ses montants ne sont pas
des prix courants au 19 octobre. Le système conserve les dates ; il ne faut pas
les perdre en aval.

Le positionnement annonce correctement zéro différence documentée et trente
propositions propres non rapprochées, à vérifier. Il évite ainsi une conclusion
d'exclusivité injustifiée. Mais les 162 lectures produisent peu de comparaison
utile : les incréments de créneaux de 15/30/60 minutes deviennent un argument de
vitesse, les formulations équivalentes « sans carte bancaire » restent séparées
et plusieurs garanties/témoignages se répètent.

Le catalogue v3 contient 89 capacités atomiques liées au ledger. Aucun effectif
ni fonctionnalité d'un outil tiers n'a été observé comme capacité propre. Les
doublons restent nombreux et des inclusions de plans inférées de l'absence d'une
croix portent encore l'état verified : une citation présente ne démontre pas
que les colonnes du tableau ont été correctement attribuées.

## Audience choisie

Première ligne exacte : « A bootstrapped software founder who sends his own calendar
link to clients, partners and investors and winces slightly every time he pastes it ».
Elle vise une petite entreprise logicielle, un fondateur qui prend lui-même ses
rendez-vous et plusieurs types de liens. Aucun autre segment n'a été préféré.

La carte termine en 11 min 13 s avec deux appels, six segments et neuf pages
récupérées. Zéro explore_first, deux review_first, quatre hypothesis. La
compatibilité produit est justifiée, mais les besoins viennent surtout de
comparatifs. Le seul exemple d'usage personnel est un coach no-code, adjacent au
fondateur logiciel décrit. Population, conversion et réduction des échanges
restent inconnues ; les communautés proposées ne sont pas toutes consultées.

Deux incohérences persistent dans le résultat stocké. L'angle dit « use the free
tier », alors que ses propres contre-arguments et unknowns demandent de revoir
ce chemin puisque l'activation des liens est payante. La note de découverte
parle encore de citations issues de snippets à confirmer, tandis que la note de
validation confirme les pages récupérées. Ces résultats n'ont pas été retouchés.

## Recherche approfondie

Deux appels, quatre minutes. Six sources lisibles sur dix tentatives, cinq
problèmes et huit expressions vérifiées, zéro citation non vérifiable conservée.
Les quatre échecs, les problèmes sur une seule source et les dates inconnues
sont explicitement signalés. Deux pages HN sur le même domaine ne deviennent
pas deux confirmations indépendantes : la corroboration reste bornée à un.

La qualification reste imparfaite : des messages de créateurs de produits
concurrents sont traités comme des voix terrain, les problèmes P1/P5 recouvrent
le même thème d'étiquette, et l'appartenance exacte au segment n'est pas prouvée.
Le contrôle indépendant retrouve une date visible pour le fil principal,
novembre 2021, alors que le résultat stocké indique unknown. Ce fil contient
aussi des avis favorables aux liens et une objection explicite à l'idée qu'une
meilleure interface résolve la gêne sociale. Cela limite l'angle, sans invalider
l'existence de la gêne. [Discussion source](https://news.ycombinator.com/item?id=29260468).
Cette vérification reste dans independent-research-review.json et n'est pas
injectée dans la génération.

## Dossier de pertinence

Un appel, 3 min 05 s, trente faits classés. Les cinq problèmes sont PARTIAL et
les réserves sont utiles : une superposition de calendriers ne prouve pas un
changement de perception ; les buffers et limites ne prouvent pas un tri selon
l'importance du booker ; un domaine personnalisé ne résout pas toute la gêne
sociale. Les conditions Premium sont conservées. Des preuves sur les grosses
équipes, l'assistant, le group mode et le round robin sont écartées pour ce cas.

La recommandation GO_NARROW limite le ciblage au bootstrapped B2B SaaS. Aucun
prospect individuel n'est qualifié, ce qui est cohérent avec un email de segment.
Deux limites de transmission restent à surveiller : des faits portent encore
territory=open malgré zéro différence documentée dans le scan, et E24 figure
dans les affirmations autorisées avec sa formulation de nouveauté, alors que
son classement demande de ne pas répéter « first of its kind ».

## Génération : échec réel de livraison

Campagne : f36d2fa6-808c-466a-8839-29118112e4df.
Exécution : 43b2b74b-6e43-47a2-8dae-3772d0cfff2a.
La préparation confirme GO_NARROW, dossier current, can_generate=true,
override_required=false. Knowledge est réutilisée ; aucune recompilation et
aucun generate_anyway. Le cadrage bootstrapped B2B SaaS est effectivement
présent dans le brief. La prévision annonce un email et 2–76 appels ; la
génération en utilise 25, dans cette fourchette très large.

Déroulement observé, pas scénario reconstitué :

1. Deux brouillons, « Control when your link books » et « Propose times in the
   message », sont écrits puis lus par trois lecteurs chacun. Tous deux
   reçoivent environ 6/10. La comparaison côte à côte préfère le second.
2. Le critique demande un exemple de snippet et du parcours destinataire avant
   inscription. Il qualifie ce manque de missing_material. La recherche
   officielle trouve une description et des captures, mais ne valide pas le
   type de prévisualisation recherché. Elle ne prétend pas l'avoir résolu.
3. Le système reconstruit la stratégie une fois et rédige « A free poll for
   meeting times ». Un second candidat identique est éliminé avant lecture.
   Ce brouillon restreint la gratuité aux sondages et passe tous les contrôles
   automatiques. Les trois lecteurs simulés restent autour de 6/10.
4. Le critique exige maintenant des éléments sur ce que reçoivent les votants,
   la nécessité de leur créer un compte et une démonstration avant inscription.
   Cette nouvelle qualification missing_material retire le brouillon de la
   livraison. Le pipeline termine needs_input ; l'API persiste status=failed,
   outcome_status=failed. Le rapport annonce delivered=0, promised=1.

Extrait du dernier **brouillon non livré**, 108 mots au total :

> When several people need to settle on a time, use a free SavvyCal meeting poll.
> Add candidate times, then invite everyone to vote on the options that work best
> for them.

Il précise ensuite que les sondages sont « free and ad-free », et demande de
créer un compte pour essayer ce format. Il ne promet ni aperçu avant inscription,
ni absence de compte pour les votants. Le critique déclare pourtant E64 non
dépensé, alors que le brouillon reprend précisément la gratuité sans publicité
portée par E64. C'est une contradiction observable dans les traces, pas une
inférence fondée seulement sur sa note.

**Diagnostic :** la lacune sur le parcours destinataire est une réserve
commerciale légitime. Dans ce cas, son passage en interdiction de livrer paraît
excessif : le brouillon ne fait pas les promesses non vérifiées que le critique
voudrait voir démontrées. Le code transforme l'étiquette du modèle en retrait
du résultat via `CraftLoop` et `_withhold_unresolved_material` /
`_stop_for_unresolved_material` dans pipeline.py. Les contrôles déterministes
du dernier brouillon passent ; cela ne prouve pas toute sa qualité, mais le
motif de retrait est distinct d'une violation identifiée dans son texte.

Ce cas ne passe donc pas le seuil de résultat vendable. La qualité finale sur
100 reste **non notée**, plutôt que d'attribuer une note à un livrable absent.
Les 6/10 concernent les lectures simulées des brouillons ; ni eux ni le 0,0
affiché à l'écran ne mesurent une réponse commerciale réelle.

Traces : `runs/43b2b74b-6e43-47a2-8dae-3772d0cfff2a/result.json`,
`timeline.json`, `diagnostic-events.json`, `logs.json`. Le timeline conserve les
trois textes complets et les deux briefs ; les brouillons ne sont pas exportés
comme des assets finalisés.

## Contrôle de l'interface et du lien prévu

Le vrai écran d'exécution répond HTTP 200 sur ordinateur (1440 px) et mobile
(390 px). Aucun débordement horizontal, aucune erreur JavaScript. Il affiche
« Needs your answers » et « Delivered 0 of 1 email ». Les captures ont été
inspectées visuellement. Deux défauts : « stopped before generating drafts »
contredit les trois brouillons du timeline ; le cadran Cold-read score 0,0/10
représente un ensemble vide de livrables, pas le résultat des lectures effectuées.
Les notes répétitives sur les dates prennent aussi beaucoup de place.

Le lien **prévu au brief**, résolu depuis /signup sur le domaine principal,
répond HTTP 200 : https://savvycal.com/signup. La page propose Google,
Microsoft, Fastmail ou prénom/nom/email/mot de passe. Aucune inscription ni
soumission de formulaire. Il s'agit du contrôle d'une destination envisagée,
pas d'un clic sur un email livré. Le rendu HTML d'un email final ne peut donc
pas être évalué. Voir `proposed-cta-check.json`, `failed-ui-check.json` et les
captures `failed-execution-viewport-1440.png` / `390.png` dans le dossier du run.

Le premier script de contrôle attendait les mots failed/needs input, alors que
le frontend affiche Needs your answers. Ce critère d'attente a été corrigé,
puis les mêmes lectures navigateur ont réussi. Ce timeout initial appartenait
au script d'audit, pas à l'application.

## Effort mesuré et suite prioritaire

| Opération | Appels terminés | Durée du job |
|---|---:|---:|
| Compilation | 6 | 7 min 34 s |
| Scan commun marché | 6 | 5 min 06 s |
| Carte d'audiences | 2 | 11 min 13 s |
| Recherche de l'audience | 2 | 4 min 00 s |
| Dossier | 1 | 3 min 05 s |
| Campagne, essais internes compris | 25 | 5 min 59 s |
| Total | **42** | Environ 42 min entre création et fin de génération, revue comprise |

La campagne compte quatre appels strategist, quatre email_writer, neuf
blind_reader, quatre preference_judge, deux conversion_critic et deux
material_researcher. Les dix groupes d'agents ne sont donc pas dix appels.
Les compteurs rapportent 1 584 103 jetons entrants et 292 661 sortants sur
l'ensemble, avec du cache et des tours internes ; ce n'est pas un volume de
texte unique. Les montants estimés des adaptateurs ne sont pas une facture API.
Métriques détaillées : stage-metrics.json et summary du run.

Priorité : distinguer un fait indispensable à une affirmation du brouillon
d'une démonstration commerciale souhaitable. Le second devrait susciter une
réserve explicite et une revue, sans devenir automatiquement une interdiction
de fournir un texte factuellement supporté. Revoir ensuite le choix du CTA avec
la proposition, puis la synchronisation des angles d'audience après validation.
Le binding prix/période et les dates HN restent des défauts de collecte précis.

Le baseline est conservé intégralement. Pas de relance payante identique, de
changement d'audience ou d'ajout manuel de documentation pour masquer l'échec.
Le worker de test a été arrêté après confirmation des états terminaux. Les
serveurs existants restent dans leur état initial. Les six fichiers de production
suivis par le manifeste n'ont pas changé pendant le test.
