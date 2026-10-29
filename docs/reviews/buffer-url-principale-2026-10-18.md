# Buffer — audit réel depuis la seule URL principale

18 octobre 2026. **Parcours interrompu par le quota Claude à la carte des audiences.**
Le fournisseur annonce une remise à zéro à **22 h 50, Europe/Paris**.
Il n'existe encore ni recherche, ni dossier, ni email pour ce cas. Aucune note ne
leur est attribuée. Les étapes terminées sont conservées et ne doivent pas être
relancées pour reprendre le parcours.

## Protocole

Marque fraîchement créée : **Buffer**, ID 188d51d8-c720-42d9-9aba-c893292c6675.
Entrée système unique : **https://buffer.com/**. Aucun lien d'aide, texte de preuve,
argument ou CTA ajouté manuellement. La consultation indépendante de la homepage
a uniquement servi au choix de marque. Aucun changement du générateur ni correction
manuelle de ses résultats pendant ce test.

Cas : [buffer-root-url](../optimization/buffer-root-url/).
Preset balanced, stratégie auto, première audience de la carte à retenir telle quelle,
demande générique d'un seul email d'acquisition en anglais. Aucun envoi.
Les segments inférés par le compilateur ne remplacent pas la carte encore absente.

Chaque note sur 10 est un jugement éditorial sur la couverture, la fidélité et
l'utilité. Ce ne sont ni des métriques du modèle ni des prédictions commerciales.
L'email sera évalué sur la grille stable 25/20/20/15/10/10 après génération effective.

## Notes par étape

| Étape | Résultat | Note |
|---|---|---:|
| Import depuis la homepage | 12 documents, 17 148 mots, tarifs et études de cas découverts seuls | **7/10** |
| Compilation Knowledge | 501 citations présentes dans les sources ; garantie synthétique trompeuse ; 16 min 20 s | **6,5/10** |
| Catalogue des capacités | 276 entrées sourcées, mais faits d'entreprise et fonctions tierces admis | **3/10** |
| Competitors | Six alternatives pertinentes ; quatre sites lus, 127 affirmations vérifiées par le système | **7,5/10** |
| Positioning | 147 lectures, dont 143 comparaisons inconnues ; rapprochements sémantiquement incorrects | **3,5/10** |
| Carte Audiences | Échec fournisseur au premier appel : quota de session épuisé | Non notée |
| Sélection de la première audience | Aucune carte produite ; pas de substitution manuelle | Non exécutée |
| Research audience | Dépend de la carte et de la sélection | Non exécutée |
| Relevance dossier | Dépend de la recherche | Non exécutée |
| Campagne et email final | Aucun lancement, aucun brouillon, aucun envoi | Non exécutés |
| Rendu ordinateur/mobile et destination du CTA | Aucun email à inspecter | Non exécutés |

Positioning et Competitors utilisent le même scan : une seule opération a été exécutée.

## Import — couverture commerciale utile, documentation incomplète

Le système a trouvé la page principale, transparent-pricing, la page de prix HTML,
pricing.md, une liste d'études de cas avec deux pages de pagination, quatre études
détaillées (Atena, PostIQ, Kuhns, WriteStack) et About.
Il n'a importé aucune page de support.buffer.com ou developers.buffer.com, pourtant
liés depuis la homepage. Le crawl borné ne garantit pas leur lecture.

Les listes/paginations occupent trois des douze emplacements. Le texte représente
173 760 caractères, notamment à cause des liens longs. Bonne couverture des offres
et témoignages, mais pas une lecture technique exhaustive.
Trace : steps/20261018T172619344024Z-ingest.json.

## Knowledge — présence des citations et exactitude des synthèses sont distinctes

501 faits retenus sur 511 candidats ; dix citations non retrouvées rejetées.
Un contrôle indépendant gratuit retrouve **501/501 verbatims** dans leur document
identifié après normalisation. Cela vérifie la présence des mots, pas toutes leurs
interprétations.

Les tarifs sont correctement différenciés : Free 0 USD, Essentials à partir de
6 USD par mois et par canal en mensuel, Team à partir de 12 USD ; les équivalents
annuels de 5 et 10 USD sont accompagnés de leur facturation annuelle.
Le plafond Free de dix publications programmées par canal est présent avec son
remplissage après publication.

**Défaut confirmé :** la synthèse des garanties contient « Keep your three free
channels if you upgrade from the Free plan ». Or E238, issu de pricing.md et de
la FAQ HTML, dit explicitement qu'en passant au payant **chaque canal est facturé,
y compris ceux connectés auparavant sur Free**. La synthèse est trompeuse alors
que le ledger contient la bonne règle. L'étape déclare zéro gap malgré ce défaut.

La compilation dure **979,8 secondes**. Le compilateur rapporte 16 lectures
d'extraction ; un calcul préalable sur les réponses brutes de l'API donnait
17 lots, qui ne sont pas exactement son corpus interne.
Contrôles : compilation-review.json, synthesis-review.json.
Artefacts : steps/20261018T174302219696Z-capture.json.

## Catalogue — filtrage produit insuffisant

Les 276 entrées dérivées ont toutes des références résolues. Mais elles comprennent
**20 faits de catégorie company et 21 faits de scope unknown**.
Exemples : règles de recrutement de Buffer (E1), identité du CEO (E4), fonctions
de WriteStack pour les créateurs Substack (E22). Ce sont des faits réels,
mais ils ne constituent pas tous des capacités de Buffer.

Le correctif précédent reste insuffisant quand le compilateur classe un fait
tiers unknown ou capability. Il faut contrôler le propriétaire et le type du fait.
Les descriptions de portée et la visibilité internal restent présentes, sans
rendre le catalogue fonctionnellement propre.
Traces : capability-profile.json, capability-review.json.

Le catalogue se dérive automatiquement au lancement du mapping. Avant cela,
son GET rendait 404 et conseillait de compiler, alors que Knowledge v1 existait
déjà : le diagnostic mérite également d'être clarifié.

## Competitors — pertinents, justifications mieux sourcées, couverture partielle

Alternatives : Hootsuite, Later, Metricool, Sprout Social, Meta Business Suite,
et tableur avec publication manuelle. Le statu quo tableur est pertinent sans site
à profiler. Meta est resté illisible et non vérifié.

Quatre profils contiennent 127 affirmations dont les citations ont passé le
contrôle du système. Les justifications acceptées citent les pages concurrentes
et nos identifiants de preuve, avec le statut source_linked_hypothesis.
Les différences de tarification par siège, canal ou marque sont explicitées.

Réserve : la justification Sprout résume ses prix à 199–399 USD par siège, alors
que sa capture comporte aussi un niveau Essentials inférieur. Les récits de
découverte ne doivent pas être repris comme des vérités de marché.
Scan : **317,8 secondes**, cinq appels terminés.
Trace terminale : steps/20261018T174739822443Z-poll.json.
Profils : steps/20261018T174829950157Z-capture.json.

## Positioning — résultat trop lexical pour conseiller un angle

147 lectures : 26 territoires open, 117 exposed, quatre contested.
143 comparaisons unknown, quatre potential_difference.
Les avertissements conservent l'incertitude et n'affirment pas une exclusivité.

Mais le chiffre d'affaires mensuel de WriteStack est classé sur l'axe prix ;
les ventes historiques d'AJ&Smart issues des réseaux sociaux sont rapprochées
des prix d'abonnement Later/Sprout. Ces objets ne sont pas comparables, même
assortis d'une réserve temporelle. Un plafond d'API se retrouve aussi sur l'axe
speed sans avantage démontré.

Open/exposed reflètent surtout l'absence de proposition équivalente capturée.
Il faut filtrer sujet, type de mesure, unité et sens avant de comparer.

## Blocage et reprise

Le mapping a échoué le 18 octobre à 17:50:12 UTC, au stade de découverte des
candidats. Message exact du fournisseur :

> Claude Code rate limit: You've hit your session limit · resets 10:50pm (Europe/Paris).

Zéro appel terminé est comptabilisé pour ce job ; cela ne démontre pas une
consommation exactement nulle de la tentative refusée. Celle-ci reste inconnue.
**Aucune note d'audience ou d'email ne peut être déduite des étapes précédentes.**

Après remise à zéro, reprendre le **même cas à map**, avec la révision explicite
quota-reset, puis attendre done et capturer avant select-first, research, dossier,
campaign, advice et génération. Ne pas importer, compiler ou scanner à nouveau.

Commande de reprise depuis la racine :
backend/.venv/Scripts/python.exe -X utf8 scripts/audit_brand_flow.py map --case docs/optimization/buffer-root-url/case.json --revision quota-reset

Les recherches utilisent l'instance existante 8006. Le worker préparé
run-current-worker.py utilise le même CampaignService et son précontrôle normal
avec le code courant ; **il n'a pas été exécuté**. Les scripts de rendu et de
contrôle CTA/UI sont prêts, mais n'ont produit aucune vérification.
Ne pas confondre préparation et exécution.

## Quota et verdict provisoire

| Opération | Appels terminés | Jetons entrants rapportés | Jetons sortants rapportés |
|---|---:|---:|---:|
| Compilation | 19 | 284 031 | 299 181 |
| Scan partagé marché | 5 | 141 402 | 71 318 |
| Mapping refusé | 0 terminé ; consommation inconnue | inconnus | inconnus |
| **Total connu terminé** | **24** | **425 433** | **370 499** |

Total connu : **795 932 jetons rapportés**. Compteurs d'adaptateur, pas facture API
ni volume de texte unique. L'abonnement est partagé ; ce test n'explique pas à lui
seul l'épuisement de la session.

L'ingestion autonome et les profils concurrents sont utiles. La synthèse des offres,
le périmètre des capacités et la comparaison de positionnement présentent encore
des défauts importants. **Ce test ne permet pas de conclure à la qualité du
parcours complet ou de l'email Buffer.**

Priorités : contrôler les résumés contre leurs preuves, filtrer les capacités par
propriétaire/type, comparer des objets réellement comparables, puis terminer
l'audit restant après remise à zéro du quota.


## Correctifs ultérieurs du mécanisme

Les défauts ont été traités dans le code ; voir [le rapport de correction](buffer-corrections-2026-10-18.md).
Les notes ci-dessus décrivent le test initial et restent inchangées. Le rejeu gratuit
de ses données vérifie les contrôles, sans constituer une nouvelle génération d'email
ou une validation complète du parcours qui reste arrêté au quota.
