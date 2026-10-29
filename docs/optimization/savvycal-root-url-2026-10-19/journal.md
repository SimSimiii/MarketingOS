# SavvyCal — audit complet depuis la homepage

## 19 octobre 2026 — protocole initial

Nouvelle demande utilisateur : nouvelle marque, parcours complet, notes de chaque étape.
Entrée unique : https://savvycal.com/. La consultation indépendante de cette homepage
a uniquement servi à choisir la marque, sans fournir ses faits ou liens au générateur.
Carte des audiences normale, première audience exacte, recherche, dossier, un email
d'acquisition en anglais, preset balanced et stratégie auto. Aucun envoi.

Notes éditoriales sur 10 pour couverture, fidélité et utilité. Email : grille stable
25/20/20/15/10/10, sans prédiction de conversion réelle. Aucun score avant résultat inspecté.

Les serveurs 8000/8006 ouverts utilisent encore un ancien code. Le worker de test
charge le code courant et appelle les routes réelles via HTTPX ASGITransport, sans
listener réseau, startup, init_db ou reaper. Le helper audit_brand_flow.py reste
l'opérateur des étapes et des snapshots ; optimize_campaign.py collecte la campagne.
Le transport seul change : mêmes schémas, handlers, services, providers, DB et contrôles.
Les jobs restent dans ce worker persistant pour permettre leur lecture et capture.
Aucune campagne active détectée avant lancement. Branche master conservée.

## Import — 7,5/10
11 pages, 3 986 mots, 30 978 caractères ; docs/developers et trois guides détaillés trouvés seuls. Prix Basic 10 USD/utilisateur/mois et Premium 17 dans le texte, mais cadence de facturation non explicitement liée ; icônes de comparaison et réponses FAQ absentes. Couverture utile, pas exhaustive.

## Compilation — 7/10
114 citations sur 114 retrouvées, deux candidats non vérifiables rejetés. 6 appels, 80 759 jetons entrants / 91 674 sortants rapportés ; 7 min 34 s. Fonctionnalités, group mode, buffers et restriction Premium des domaines compris ; garantie de remboursement trente jours conservée. Aucun montant dans le ledger malgré Basic/Premium chiffrés dans le résumé ; liaison annuelle absente et aucun gap commercial signalé. Ne pas confondre garantie de remboursement et essai gratuit. Aucun résultat retouché.

## Scan marché et catalogue
Concurrents 8/10 : cinq fournisseurs crédibles et le statu quo manuel ; 132 affirmations vérifiées dans les captures. Six appels, 5 min 06 s. Justifications bilatérales conservées comme hypothèses. Prix Calendly non capturés ; comparaison API Cal.com avec DNS/HubSpot peu convaincante ; promotion Google future conservée avec ses dates.

Positionnement 5,5/10 : 162 lectures, aucune différence documentée et trente propositions propres non rapprochées, explicitement à vérifier. Pas de fausse exclusivité. Mais la granularité des créneaux est classée « speed », des paraphrases « sans carte bancaire » ne sont pas rapprochées et plusieurs propositions se répètent.

Catalogue 7/10 : 89 capacités atomiques, dérivation v3, références du ledger présentes, pas d'effectifs ni de fonctions tierces observés. Des doublons et des inférences de colonnes tarifaires restent étiquetés verified malgré les icônes absentes. La présence d'une citation ne démontre pas la bonne attribution de colonne. Aucun résultat corrigé à la main.

## Carte d'audiences — 6,5/10
Six audiences ; zéro explore_first, deux review_first et quatre hypothesis. Neuf pages récupérées, deux appels, 11 min 13 s. Première audience exacte conservée : fondateur bootstrappé qui envoie lui-même ses liens à ses clients, partenaires et investisseurs. Compatibilité produit étayée ; besoin surtout issu de comparatifs, exemple d'usage d'un coach no-code adjacent, population inconnue. Le diagnostic et les contre-arguments disent clairement que l'activation de liens est payante ; l'angle brut contient pourtant encore « use the free tier ». Défaut de synchronisation angle/validation consigné avant la recherche ; aucun résultat modifié. Une note historique dit encore que les citations sont des snippets, contrairement à validation_note qui confirme neuf pages récupérées. Vérifier l'effet dans dossier/stratégie/email, sans confondre présence d'une source et validation de tout le portrait.

## Recherche — 7/10
Six sources, cinq problèmes, huit expressions, quatre échecs de fetch annoncés, deux appels et quatre minutes. Dates inconnues et faible corroboration explicitement signalées ; plusieurs sources HN ne sont pas comptées comme corroboration indépendante. Limites : messages de créateurs de produits concurrents, correspondance démographique non démontrée, P1/P5 proches. Contrôle indépendant du fil 29260468 : date visible novembre 2021 et avis contradictoires, dont une objection à l'efficacité d'une jolie interface contre la gêne sociale. Source : https://news.ycombinator.com/item?id=29260468. Les deux autres contrôles web HN reçoivent 429 ; ne pas prétendre les avoir relus indépendamment. Observations conservées séparément, non injectées. Dossier lancé sur la première audience sans aucune modification des résultats.

## Dossier — 7,5/10
Un appel, 3 min 05 s, trente faits classés, cinq correspondances PARTIAL avec limites explicites, GO_NARROW pour bootstrapped B2B SaaS. Ne promet ni changement de perception ni priorisation automatique par identité du booker. Domaines Premium correctement conditionnés, preuves grosses équipes/assistant/group mode/round robin/novelty écartées. Limites restantes : certains faits territory=open malgré zéro différence concurrentielle démontrée ; E24 autorisé avec sa formulation first-of-its-kind malgré avertissement de ne pas la répéter ; trente faits restent une large sélection pour un email. Aucun résultat retouché ; campagne normale sur l'audience exacte avec restriction automatique du dossier, sans override.

## Itération 1 — baseline de génération et diagnostic
Exécution 43b2b74b-6e43-47a2-8dae-3772d0cfff2a : API failed, pipeline needs_input, 0/1 email. Trois brouillons, une recherche officielle et un replan. Le dernier brouillon « A free poll for meeting times » passe les gates et ne promet pas d'aperçu avant inscription ou d'absence de compte votant. Le critique exige ces éléments puis le mécanisme missing_material retire le résultat. Il déclare E64 non dépensé malgré « free and ad-free » dans le texte. Qualification éditoriale devenue veto : cause à traiter avant une nouvelle génération, sans forcer la sortie ni ajouter une URL manuellement. 25 appels terminés, dix groupes d'agents, 5 min 59 s. Total du parcours : 42 appels, environ 42 minutes entre création et fin de génération.

### Note qualité
Itération 1 : **non notée /100**, aucun email livré ; meilleur score du cas indisponible.
Forces : connaissances et dossier réellement chargés ; gratuité restreinte aux polls, aucune donnée participant inventée.
Défaut principal : l'exigence de démonstration du critique bloque un brouillon passant les contrôles automatiques.
Preuves : result.json, timeline.json, diagnostic-events.json ; trois brouillons conservés, assets vide.
Verdict : seuil vendable non atteint. Baseline conservé ; distinguer manque factuel essentiel et réserve de persuasion avant tout nouvel essai payant.

## Interface — 6/10 et clôture du test
Vrai frontend/proxy, desktop 1440 et mobile 390 : HTTP 200, pas d'erreur JS ni débordement, captures inspectées. « Needs your answers » et 0/1 visibles. Défauts : message « before generating drafts » faux après trois brouillons, moyenne vide affichée 0,0 et nombreuses notes répétées. Le premier critère d'attente du script omettait Needs your answers ; corrigé et relecture réussie. Ce timeout initial n'était pas un échec produit. Lien prévu /signup HTTP 200 avec formulaire et OAuth ; aucune inscription. Aucun asset HTML final, rendu email non évaluable. Worker arrêté après tous états terminaux, code de production et anciens serveurs inchangés. Rapport : docs/reviews/savvycal-url-principale-2026-10-19.md.

## Itération 2 — correction autorisée du veto de livraison
Demande utilisateur : « alors fix ça », avec évaluation de l'utilité du mécanisme.
Cause : l'étiquette missing_material du critique est transformée en retrait d'outcomes par pipeline.py, y compris en annulation/erreur et dans craft_one. Elle retire un texte passant les gates pour une préférence de démonstration non promise. La recherche bornée et le replan restent utiles, pas ce veto global.
Hypothèse avant modification : conserver les brouillons qui passent les gates, conserver leur réserve explicite et leur statut degraded/needs_review, puis laisser les vérifications déterministes bloquer les violations. Les refus de préflight sans matière exploitable restent inchangés. Calibrer aussi le critique sur la différence affirmation/démonstration souhaitée, sans inventer de faits.
Résultat attendu : à entrées identiques, un email accessible et marqué à revoir si la réserve persiste ; aucune fausse approbation, aucune relance aveugle des scans, aucune modification du baseline. Vérifier les chemins normal, récupération en échec, annulation et exécution par étape, puis régénérer SavvyCal sur le code modifié.

Correction implémentée : retrait du veto de livraison sur l'étiquette éditoriale missing_material dans CraftLoop et les parcours normal/par étape/annulation/erreur. Les gaps restent dans unresolved, landed=false et le conseil avant envoi ; la récupération et les gates n'ont pas été désactivées. Prompt du critique : exiger une dépendance réelle à une affirmation ou une ressource promise, pas une démonstration seulement souhaitée avant inscription. Aucun appel modèle ajouté.
Validation gratuite avant relance : Ruff OK ; 1 749 tests backend OK (dont régression sondages SavvyCal, étapes avec assets et needs_review, échecs de récupération, annulation, refus de chiffres non sourcés et préflight) ; lint/TypeScript OK et 28 tests frontend OK. Deux warnings de dépréciation backend, warnings de type de module Node préexistants. Même campagne, mêmes sources et audience, dossier encore current et GO_NARROW sans override. Relance réelle autorisée pour mesurer le comportement modifié, pas pour remplacer le baseline.

### Note qualité — itération 2
Run f3b1420d-d6a1-4010-b4fa-fcdc8b9fe6e4 : **78/100**, meilleur du cas 78 ; pas de delta contre l'itération 1 non notée faute d'asset.
Un email livré en texte/HTML, gates passées et E9/E108/E109 dépensés ; offre compréhensible et rendu propre à 1280/390 px.
Réserve : pertinence de l'angle opérationnel et engagement du signup ; lien rendu vers la homepage malgré /signup prévu, constaté sans retoucher l'asset.
10 appels, 2 min 48 s, completed/degraded/needs_review ; UI réelle confirme texte accessible et « Drafts Need Review ». Le critique route argument, pas missing_material ; la rétention sous classification missing_material persistante est prouvée par les tests scriptés.
Verdict de portée : mécanisme demandé corrigé et vérifié, seuil de copie prête à envoyer non revendiqué. Qualité commerciale et résolution du CTA restent une suite distincte ; pas de relance payante identique pour masquer ces limites.
Rapport : docs/reviews/savvycal-material-veto-fix-2026-10-19.md. Worker arrêté après collecte, anciens serveurs inchangés et baseline intact.
