# Carrd — exécution de marketingos-brand-audit

19 octobre 2026, heure de Paris. **Audit en cours.**

Skill créée et utilisée : `marketingos-brand-audit`, installée dans
`C:/Users/oussa/.codex/skills/marketingos-brand-audit/`.
Son opérateur local a passé Ruff et des contrôles gratuits : verrou exclusif,
conservation d'une commande pending, refus des doublons et fin sur réponse.

Nouvelle marque Carrd : dc0e5850-4cae-4b63-9cd5-29cd07590949.
Entrée unique : https://carrd.com/. Aucun sous-lien ou fait transmis par
l'évaluateur. Première audience exacte, un email d'acquisition anglais,
auto/balanced. Notes /10 par étape ; email /100, grille 25/20/20/15/10/10.
Aucune prédiction de conversion ; aucun envoi.

Le code courant appelle les vraies routes, providers et DB dans une session
ASGI sans serveur ni lifespan. Les serveurs ouverts ne sont pas rechargés.
Les résultats initiaux resteront conservés après toute correction.

| Étape | Note | Faits vérifiés et limites |
|---|---:|---|
| Import initial | 6,5/10 | 12 pages, 7 058 mots ; plans et guide Signup Form ; perte des headers éditoriaux, dont prix annuel et restriction Pro de la homepage |
| Import corrigé | 8/10 | Même homepage, 12 pages et 7 440 mots ; prix annuel et portée Pro restaurés par le crawler |
| Compilation initiale | 8/10 | 122/122 citations retrouvées ; prix/plans annuels et essai distingués, gaps de preuve explicites ; nouvelle compilation après correction en cours |

Cas et snapshots : `docs/optimization/carrd-root-url-2026-10-19/`.

## Correction 1 : préserver les headers éditoriaux

La page possède un header de navigation et des headers à l'intérieur des
sections produit et Pro. L'ancien extracteur supprimait tous ces éléments,
donc aussi le prix annuel affiché et la phrase « Pro-exclusive features ».
La capture initiale reste conservée. La correction préserve le texte des
headers de section/article/main et les héros éditoriaux ; la navigation,
les scripts et les bannières de menu sans contenu restent supprimés.

124 tests d'ingestion passent ; Ruff passe. Un rejeu gratuit sur le HTML
sauvegardé passe de 3 134 à 3 514 caractères et retrouve le prix, la période
et la restriction Pro, sans ajouter d'information manuelle au système.
1 754 tests backend, lint/TypeScript et 28 tests frontend passent également.
Le nouvel import confirme le contexte restauré. Il conserve trois anciennes
versions : quinze documents en base pour douze URL, sans effacer le baseline.

## Première compilation conservée

Onze appels. Les 122 citations du ledger sont retrouvées dans leurs documents,
avec cinq candidats non vérifiables rejetés. Les trois plans sont correctement
liés à leurs prix annuels et la restriction Pro Standard des formulaires est
comprise. La version gratuite et l'essai Pro sont séparés. Les absences de preuve
client et de résultat mesuré sont signalées, sans chiffre inventé pour les combler.
La compilation sur les sources complétées sera évaluée séparément.

## Compilation corrigée et correction des liens

Compilation v2 : 135/135 citations correspondent aux documents ; 15 appels. Note 8/10, avec réserve sur le libellé de départ Pro de la homepage (19/an) face au plan Lite détaillé (9/an). Les prix doivent rester liés au plan.

Le renderer ignorait les destinations officielles relatives choisies par le brief. Il les résout maintenant sur le domaine de la marque, seulement si documentées ; aucun chemin inventé ni ambigu. Validation : 59 tests CTA/rendu, Ruff et 1 762 tests backend passent. Le prochain mail réel utilisera ce mécanisme ; aucun asset historique n’a été retouché.


## Bilan global au 20 octobre — échec conservé, sans résultat retouché

| Étape | Note /10 | Évaluation du résultat réel |
|---|---:|---|
| Import corrigé | 8 | Douze URL, guides et plans lus ; headers restaurés |
| Knowledge corrigée | 8 | 135/135 citations retrouvées, prix/conditions et absences explicites |
| Catalogue | 7 | 56 capacités sourcées, doublons et restrictions parfois imprécises |
| Concurrents | 7 | Six alternatives, quatre sites lus, 105 claims vérifiés ; bruit Notion AI |
| Positionnement | 7 | Absence observée distincte d'exclusivité ; axes parfois peu pertinents |
| Audiences | 6,5 | Sept hypothèses, peu de sources et prose de découverte trop affirmative |
| Recherche de la première audience | 7,5 | Neuf sources, 30 citations contrôlées ; sources anciennes et concentration Indie Hackers |
| Dossier corrigé | 8 | Prix du plan adapté réintroduit par sélection automatique ; trois promesses non étayées écartées |
| Livraison | 0 | Deux runs, zéro asset : premier bloqué à tort sur les chiffres, second interrompu par quota |
| Email et rendu | Non notés | Aucun email livré ; un brouillon dans un log ne constitue pas une livraison |

Le premier run réalise 15 appels terminés, le second 21. Les corrections portent sur les mécanismes : sélection des preuves limitées aux capacités requises, conservation des noms complets de plans et normalisation des durées avec trait d’union, résolution des CTA officiels relatifs, et conservation explicite du champion contrôlé en cas de panne tardive. Les anciens résultats restent inchangés. Le second run confirme que les gates corrigées passent ; il révèle ensuite la perte du champion pendant une critique, défaut maintenant couvert par tests scriptés et par le parcours par étapes.

La suite complète passe à 1780 tests, plus les deux nouveaux scénarios d'intégration dans un lot ciblé de 27 tests. Cette validation du code ne relève pas les notes fonctionnelles. Carrd ne satisfait pas le critère global demandé : carte d'audiences trop faible et aucune livraison. Une nouvelle marque Senja fait l'objet d'un parcours complet, sans lui fournir de documentation ou faits manuels.
