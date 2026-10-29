# Carrd — audit et corrections depuis la homepage

## 19 octobre 2026 — exécution de marketingos-brand-audit

Demande : créer une skill pour créer une marque, exécuter tout le parcours,
noter les étapes et corriger les défauts, puis commencer à l'exécuter.
Skill personnelle créée : C:/Users/oussa/.codex/skills/marketingos-brand-audit/SKILL.md.
Marque nouvelle : Carrd, nom absent de la liste des marques existantes.
Une consultation indépendante de la homepage pour choisir la marque révèle
la redirection de carrd.co vers carrd.com. Entrée fournie au système : uniquement
https://carrd.com/, sans faits, prix, doc ou CTA transmis par l'évaluateur.

Parcours : import, compilation, scan commun marché, carte/catalogue, première
audience exacte, recherche, dossier, un email d'acquisition anglais en auto/balanced.
Notes /10 par étape ; email /100 selon grille 25/20/20/15/10/10. Rien n'est
noté avant inspection. Aucun envoi. Corriger les mécanismes observés puis retester
les étapes touchées, en conservant tous les baselines et les entrées inchangées.

Même branche conservée, changements antérieurs préservés. La session de la skill
emploie les routes réelles du code courant sans startup/init_db/reaper ni serveur
réseau ; elle ne prouve pas un rechargement des serveurs ouverts. Les helpers du
dépôt restent opérateurs des snapshots et de la campagne, un seul écrivain par cas.

## Défaut d'import observé — baseline conservé
L'import initial contient douze pages et 7 058 mots. L'inspection indépendante
de la même homepage montre trois headers : une navigation du site, un résumé
produit dans section#about, et le titre/texte tarifaire dans section#pro.
Le code supprimait les trois sans distinction. Le baseline perd donc « Optional:
Go Pro », le prix annuel affiché et la phrase qui rattache la liste aux fonctions
Pro. Les plans détaillés ont été lus sur une autre page ; cela ne justifie pas
la perte de contexte de la homepage. Note initiale d'import : 6,5/10.

Cause avant modification : _REMOVED_TAGS contient header globalement. Hypothèse :
préserver les headers de sections/articles/main et les héros comportant du texte
éditorial, tout en retirant la navigation et les bannières de menu sans contenu.
Test attendu : prix/période et restriction Pro présents après extraction, sans
réintroduire nav/script/footer. Rejouer gratuitement sur la capture HTML indépendante,
puis refaire uniquement l'import/compilation avec révision, sans URL supplémentaire.
La compilation initiale en cours sera collectée avant l'arrêt du worker ; sa version
restera historique. Aucun asset ou fait stocké n'est corrigé à la main.

## Correction d'import validée et reprise
124 tests d'ingestion, Ruff, 1 754 tests backend, lint/TypeScript et 28 tests
frontend passent. Rejeu libre sur HTML initial : 3 134 à 3 514 caractères,
prix/période et scope Pro retrouvés. Après fin et capture de la compilation v1,
worker arrêté puis réouvert sur le code corrigé (sans serveur ni lifespan).
Réimport normal avec revision content-headers, même homepage seule : douze pages,
7 440 mots, prix et restriction Pro présents. Note import corrigé : 8/10.
La persistance conserve trois anciennes versions de pages ; il s'agit de douze
URL distinctes et quinze documents, pas de quinze pages découvertes. Pas de
suppression ou remplacement manuel du corpus. Les textes anciens sont des
sous-ensembles sans prix contradictoire ; contexte complété par la lecture normale.

Compilation initiale : 122/122 citations retrouvées, cinq candidats rejetés,
onze appels. Prix 9/19/49 USD par an attribués aux bons plans ; Basic gratuit,
essai Pro de sept jours sans carte et restriction Pro Standard des formulaires
correctement séparés. Deux gaps utiles : pas de preuve client ni de résultat
mesuré. Note baseline Knowledge : 8/10. Une nouvelle compilation normale est
requise par le changement de sources ; revision content-headers lancée.

## Défaut de CTA documenté avant correction
Le dernier run SavvyCal conservé prévoit /signup mais rend la homepage dans
le bouton. Cause confirmée : style_for_action ne récupère que des URL absolues,
alors que les actions officielles de Carrd sont également /build, /signup, /pro.
Reproduction déterministe attendue, sans génération payante : un chemin relatif
présent dans l'offre doit devenir son URL absolue sur le domaine de la marque ;
un chemin inventé, ambigu ou changeant d'hôte doit conserver le fallback. Les
URL explicites de l'utilisateur restent prioritaires. Ne pas éditer les assets
SavvyCal ni ajouter de cta_url au cas Carrd. Tests de rendu texte/HTML, puis
chargement du code corrigé dans la session après compilation terminale.

## Compilation v2 et CTA
Compilation v2 terminée : 15 appels, 199 217 jetons entrants et 105 639 sortants, 135/135 citations retrouvées dans leurs documents. Note 8/10 : offre et conditions utiles, voix apprise, manque de preuve client explicite. La homepage dit Pro dès 19/an tandis que le détail propose Lite à 9/an ; employer les noms de plans. Le corpus conserve trois versions historiques.
59 tests CTA/rendu et Ruff passent ; suite backend complète en cours. Le worker a été arrêté après collecte terminale puis réouvert sur le correctif CTA avant le scan marché. Les anciens serveurs restent inchangés.

Validation complète après CTA : 1 762 tests backend passent (322,51 s, deux avertissements de dépréciation préexistants), Ruff passe. Frontend inchangé : lint/TypeScript et 28 tests déjà passés. Skill revalidée, script de rendu réutilisable ajouté ; sa syntaxe Node passe.

## Reprise du 20 octobre
Le mapping initial a échoué au quota Claude, aucun appel terminé ni carte produite. Reprise demandée par l’utilisateur après le créneau de reset annoncé. Code de production identique au dernier manifest, étapes terminées conservées. Nouvelle session locale sans listener/lifespan ; seuls les jobs interrompus seront relancés avec révision.
Scan marché évalué : concurrents 7/10, positionnement 7/10. Six alternatives plausibles, quatre sites lus, 105 claims vérifiés ; Linktree et Wix explicitement non lus. Pas de fausse exclusivité, mais beaucoup de bruit Notion AI/agents et aucune différence documentée.

Catalogue : 7/10, 56 capacités produit reliées au ledger v2. Pas de faux employé issu des templates ni de fonction attribuée à Carrd alors qu’elle appartient à un tiers. Réserve : doublons sémantiques et conditions tarifaires parfois peu précises sur les index. Cartographie en cours : premier appel Opus de 425 s, 367 508 jetons entrants dont 301 003 en cache, 23 706 sortants. Latence élevée à évaluer sur résultat terminal. Interface localhost:3000 indisponible lors du contrôle de reprise ; aperçu HTML prévu séparément.

Carte terminée : 6,5/10, sept audiences et zéro promue prioritaire car preuve limitée/contre-preuves. 13 min 11 s, trois appels (dont correction de réponse structurée) pour deux étapes logiques, cinq pages réellement récupérées. La première est le créateur de newsletter/maker avant lancement, compatible avec les formulaires et domaines Carrd mais sensible aux alternatives gratuites ; usage observé ne prouve pas achat. Sélection exacte index 0 conservée, recherche autorisée par le système et lancée. La prose de découverte reste plus affirmative que certaines évaluations validées : ne pas la prendre pour une preuve.

Recherche v1 : 7,5/10. Neuf sources réellement récupérées, sept problèmes, deux éléments non vérifiables écartés. Sources anciennes datées et avertissements d’inférence présents ; des posts 2026 complètent les sources historiques. Limites : concentration Indie Hackers, plusieurs problèmes à source unique et quelques généralisations. Le dossier doit écarter toute promesse de générer la demande, convertir la waitlist ou envoyer les newsletters, fonctions non établies pour Carrd. Dossier lancé sur cette recherche, sans ajout de preuve.

Contrôle indépendant de la recherche : neuf URL refetchées sans ajout au système, 30 citations uniques retrouvées, zéro citation manquante (research-quotation-review.json). Dates originales distinctes des dates de récupération. Le témoignage de la carte sur l’usage Carrd est daté de mai 2022 ; aucun signe d’achat actuel n’en est déduit.

## Défaut de sélection du dossier avant modification
Baseline dossier : 7/10, silences corrects sur envoi d’email/conversion/normes HN, fit partiel sur formulaires et analytics. Défaut confirmé : tous les 56 items du catalogue sont passés comme références obligatoires à select_evidence. Résultat : 60 faits au lieu du plafond 48, presque seulement des capacités ; aucun prix annuel bien que le coût soit une objection. Le dossier reconnaît cette absence dans son extrait.
Hypothèse : rendre obligatoires seulement les références des capacités requises par cette audience, et laisser la sélection diversifiée compléter le budget. Rejeu gratuit du corpus courant : 48 faits, prix Pro Standard 19/an, Lite 9/an et Plus 49/an présents, quatre capacités requises préservées. Mettre à jour la version d’interprétation, tests de saturation de catalogue et d’ordre, puis régénérer seulement le dossier avec révision explicite. Ne changer ni Knowledge ni audiences/recherche ni dossier stocké.

Correction de sélection validée : 48 tests ciblés, Ruff et 1 764 tests backend passent (145,94 s). Aucun changement frontend ni contrat API. Les quatre capacités requises restent épinglées, le catalogue entier cesse d’évincer les décisions commerciales. Dossier version d’interprétation 7 en cours de génération normale ; aucun résultat modifié à la main.

Dossier corrigé v2 : 8/10 (+1), interprétation 7, 28 faits classés, sept fits et trois silences. Pro Standard 19/an maintenant LEAD et formulaires conditionnés au bon plan ; Plus 49/an et essai présents. Aucun résultat de conversion ni envoi d’email promis. Fit hébergement versus embed conservé partiel. Campagne créée sans CTA ajouté ; précontrôle conservé avant lancement.

# Diagnostic pendant le run initial, avant correction

Le run 7f217580-283d-4294-a617-e701d691f7d7 rejette le premier brouillon malgré
« Pro Standard costs $19 per year » et un essai Pro documenté de sept jours.
Le brouillon stocké et les événements restent inchangés. Ce journal séparé évite
de concurrencer les écritures du runner dans state.json et journal.md.

Causes confirmées dans ledger.py : le normaliseur conserve le trait d'union dans
l'unité de 7-day au lieu de canoniser days ; le parseur de prix ne capture que
le dernier mot Standard alors que la provenance nomme Pro Standard.

Correction attendue : comparer les mêmes durées singulier/pluriel/trait d'union ;
reconnaître un nom complet de plan connu du prix dans la phrase qui le tarifie.
Ne pas confondre deux plans partageant Standard, ni une durée différente, ni un
montant mensuel avec un montant annuel. Tests et rejeu gratuits des brouillons
capturés, aucune modification du dossier ou d'un asset. Le run en cours garde
le code qu'il a chargé ; collecter son état terminal avant arrêt de la session.

Validation après modification : 76 tests ciblés, Ruff et 1 771 tests backend passent. Les deux brouillons initiaux passent le rejeu gratuit sans aucune modification. Baseline réel terminé en échec, 15 appels terminés et une tentative expirée reprise, zéro asset ; email non noté, livraison 0/10. Reprise sur les mêmes entrées après chargement du nouveau code ; ne pas retoucher les résultats initiaux.

## Interruption du provider : diagnostic avant modification
Run 2 terminé : zéro asset, 21 appels terminés, 517785 jetons entrants, 34763 sortants, estimation 2.871 USD. Les contrôles numériques corrigés passent sur les vrais brouillons ; une réécriture lue à 8/10 gagne le duel puis disparaît quand une critique suivante échoue au quota GPT. Email livré non noté, livraison 0/10. Cause : CraftLoop ne retourne son outcome et ne publie son champion qu’après tous les appels facultatifs. Hypothèse : conserver un champion déjà contrôlé si un ProviderError interrompt la suite, retourner un outcome explicitement interrompu, arrêter le pipeline sans nouveaux appels et exposer le défaut dans le rapport. Aucune version bloquée ne doit être livrée. Le quota dur Codex doit être classé non réessayable, contrairement aux erreurs réseau transitoires. Tests scriptés avant toute nouvelle génération. Critère utilisateur réaffirmé : toutes les étapes doivent être utiles et fiables, un mail seul ne suffit pas. Carrd reste une régression incomplète, une autre marque neuve suivra.

Correction interruption/quota validée gratuitement : 97 tests pipeline/provider/runtime, suite complète 1780 tests, puis 27 tests runtime/stepped dont les deux nouveaux cas de bout en bout. Un échec de critique ou réécriture conserve le champion ayant passé les contrôles et expose une revue interrompue ; un brouillon non conforme reste exclu. Le run arrête les appels suivants et la version par étapes sérialise aussi l’interruption. Le vrai message turn.failed du CLI passe par le runtime sans seconde tentative. Ruff passe. Aucun asset Carrd injecté ou reconstruit à la main. Reprise réelle sur nouvelle marque Senja, parcours global.
