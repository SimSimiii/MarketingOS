# Plausible — vérification des cinq améliorations de fiabilité

Suivi de l'[audit initial](plausible-url-principale-2026-10-18.md), le 18 octobre
2026. Les corrections portent sur les mécanismes. Les anciennes sorties restent
dans les snapshots ; aucun texte de dossier, fait ou email n'est remplacé à la main.
Entrée de marque inchangée : `https://plausible.io/`, sans URL d'aide ajoutée.

## Modifications et vérifications

| Point | Changement | Résultat constaté |
| --- | --- | --- |
| Catalogue produit | Capacités atomiques issues des faits réellement compilés, attribution et limites conservées, identifiants liés à l'affirmation citée. Retrait des anciens automatismes propres aux agents, maintien des limites utilisateur. | 200 faits de capacité sur Plausible ; disparition des faux `knowledge_base` et `agent_api_keys`. Tests également sur un four et une boutique, sans appel modèle supplémentaire. |
| Recherche | Dates extraites du HTML récupéré ou de l'URL datée ; date inconnue conservée ; signalement des sources historiques, contenus dupliqués et problèmes provenant d'une seule source. Réserves transmises à la campagne. | Recherche v2 réelle : huit sources, un problème retenu, quatre éléments rejetés. Article GDS du 27/03/2023 daté par son URL ; sept dates inconnues. Problème explicitement historique, inféré et non corroboré indépendamment. |
| Offre et tarifs | Digest préservant les sections commerciales tardives ; récupération conservatrice des prix laissés vides, avec provenance, plan, période et conditions. Les conflits restent vides. | Starter 9 $, Growth 14 $, Business 19 $ par mois remontent avec la condition du palier de 10 000 pages vues. Le digest du corpus enregistré retrouve les trois montants. Pas de recompilation payante nécessaire pour vérifier ce correctif. |
| Concurrents | Hypothèse de découverte séparée de la justification réconciliée ; références contrôlées aux deux produits ; contexte ciblé sur la comparaison et offres tarifaires ; repli vers une URL publique réellement découverte. | Scan final : cinq hypothèses référencées. Fathom : tarif par volume et non fixe ; Simple Analytics : chevauchement sur les identifiants ; Umami : auto-hébergement commun aux deux produits. GA4 reste illisible sans nouvelle découverte. Les unités tarifaires et les limites de l'extrait de douze faits exigent encore une lecture éditoriale. |
| Quota et états | Cache d'extraction lié aux captures, faits, lead, schéma et prompt ; contexte de découverte plus compact ; état du processus séparé de la qualité des brouillons. | Rescan réel : quatre fiches réutilisées, une capture Umami modifiée, un appel modèle au lieu de cinq. L'ancien run terminé affiche « Drafts need review », sans modifier son résultat historique. |

« Vérifié » signifie ici que la citation correspond au matériau récupéré et que
ses références se résolvent. Cela ne prouve ni la vérité indépendante d'une promesse
fournisseur, ni la justesse universelle d'une interprétation comparative.

## Carte d'audiences régénérée

Sept segments ; chacun possède maintenant cinq ou six capacités requises, contre
zéro auparavant. Les faits requis sont documentés. Les réserves commerciales et
les contre-exemples demeurent : aucune audience n'est automatiquement déclarée
prioritaire. Le premier segment présente notamment des migrations vers des solutions
gratuites et des objections tarifaires. La compatibilité des faits produit ne
garantit pas à elle seule l'adéquation du plan, du budget ou des achats publics.

La carte a consommé deux appels, 467 947 jetons rapportés contre 685 963 lors du
premier essai, et environ dix minutes. Les pages retrouvées diffèrent : cette baisse
observée ne mesure pas isolément l'effet du contexte compact. Les compteurs incluent
les entrées cachées et ne représentent ni des jetons tous nouveaux ni une facture API.

L'audience publique EU/UK du premier audit reste présente et conserve son nom exact.
Elle est gardée pour la suite afin de comparer la même situation de lecteur. Sa
définition a évolué : la recherche doit être renouvelée, sans masquer ce changement.

## Validation et limites opérationnelles

Backend : 1 732 tests passent, deux avertissements de dépendances ; Ruff `app tests`
propre. Frontend : lint et typage propres, 28 tests passent. Le dernier test de
migration préserve aussi une limite utilisateur `unsupported` portée par un ancien
catalogue ; la suite complète passe après ce correctif.

Navigateur : onglets Competitors et Audiences visibles, aucun `pageerror` ; état
de revue de l'ancien email contrôlé. Captures dans
`docs/optimization/plausible-root-url/after-crawler-fix/ui-functional/`.

Une interruption a arrêté les serveurs après le scan comparatif terminé en base.
Ses cinq fiches ont été récupérées intactes, mais ses statistiques terminales,
locales au processus, n'avaient pas été capturées : elles restent indisponibles.
Les autres compteurs sont conservés dans les réponses terminales horodatées.

Le contrôle automatique a refusé des redémarrages du backend et la création d'une
autre instance HTTP (« blocked by policy »). Les processus existants sont laissés
en place. La dernière génération utilise le même `CampaignService.start_execution`
dans un worker ponctuel, sans serveur, lifespan ni modification du résultat.
Son ID est enregistré immédiatement et les sorties sont collectées par `resume`.
Les dernières règles de filtre/stratégie nécessitent encore un rechargement normal
du serveur avant les prochains lancements depuis l'interface.

Le frontend local a utilisé temporairement le backend 8006 ; son proxy et l'API
directe exposaient bien le même job, sans routage simulé. La configuration locale
initiale est rétablie à la fin de l'audit. Les serveurs lisent la même base et
l'interface peut afficher le nouvel email ; cela ne recharge pas leur code Python.

## Suite de la validation

Le dossier v3 est courant, interprétation 6 : trente faits, aucun rejet, six
normalisations. Il met en tête E203/E39/E4/E41/E325/E7 (confidentialité, mécanisme,
hébergement européen), et écarte l'opinion SEO E318. Le problème historique reçoit
une réponse partielle avec les conditions Business, le plafond de 600 requêtes/h
de l'API et l'export brut réservé à Enterprise. Recommandation `GO_NARROW`, limitée
aux équipes gouvernementales nationales ou décentralisées, sans contournement.

La première génération après ces changements a révélé un autre défaut : son plan
primaire était correct, mais le filtre anti-spam classait **DPIA** comme du texte
crié. Le bon brouillon n'était donc pas lu ; l'alternative sur les permissions
était conservée et manquait la contrainte de consentement. Le dossier ou le plan
initial n'ont pas été retouchés. L'acronyme a rejoint le vocabulaire métier admis,
avec les vrais tests de texte crié maintenus. Le rejeu du brouillon original ne
présente plus de blocage. Les instructions stratégiques conservent également la
contrainte d'éligibilité dans chaque alternative et choisissent une action possible
avant une approbation ou un déploiement non établis.

| Email, piste « fiabilité » | Avant correction du filtre | Après correction |
| --- | --- | --- |
| ID | `d87e4e46-cb56-4a02-821d-8f8dc32a793e` | `e14d43af-13ea-4f5c-8063-4a9511033dab` |
| Évaluation éditoriale du coordinateur | 72/100 | **89/100** |
| Argument | Permissions et partage, contrainte centrale omise | Analytics sans cookies, mécanisme documenté et traitement européen |
| Action | Essai nécessitant une évaluation de workflow | Démo publique sans compte avant une revue formelle |
| Appels modèle terminés | 7 | 26 |
| Résultat | `degraded`, à revoir | `completed`, `needs_review=false`, `landed=true` |

Le dernier email est compris et jugé pertinent par les lecteurs simulés (8/10).
Les contrôles passent, aucune réserve non résolue ne subsiste dans le rapport.
Une réécriture non préférée a été abandonnée. Le rendu 1280/390 est lisible sans
débordement ; le lien a réellement ouvert le tableau de bord avec des données,
HTTP 200, dans un contexte sans connexion. Aucun email n'a été envoyé.

Grille stable : 24/19/14/14/9/9 sur 25/20/20/15/10/10. C'est un jugement
éditorial, pas une mesure de conversion. Un accès plus direct aux justificatifs
techniques et de protection des données renforcerait encore l'argument ; les
réserves des lecteurs sur ce point restent conservées. Le seuil d'un brouillon
utilisable après revue de marque et personnalisation ordinaires est atteint
pour ce cas. La nouvelle définition/recherche distingue cette piste de l'ancien
85/100 ; aucun gain causal de quatre points sur cet ancien email n'est revendiqué.

## Rectification des compteurs et coût observé

Les anciens 17 et 9 « appels » étaient des **groupes d'agents**. Le recompte des
événements `model_call_finished`, vérifié par les sommes de jetons du timeline,
donne **38 puis 26 appels modèle**. Le bilan antérieur est donc rectifié de 69 à
107 appels terminés, sans changer ses jetons, copies ou scores. Le helper expose
désormais `model_calls` et `agent_groups`, et laisse inconnu un ancien journal
sans événements d'appel.

Le suivi fonctionnel ajoute 50 appels capturés et 2 080 302 jetons rapportés,
diagnostics et deux emails inclus. Un scan terminé n'a pas de statistiques
terminales récupérables ; ses cinq fiches persistées ne permettent pas d'inventer
ses jetons ni ses éventuelles reprises. Le total connu des deux audits est
157 appels et 5 894 895 jetons, plus cette opération et la tentative refusée
au quota. Ce n'est pas le coût d'un parcours ordinaire sans diagnostic.

Le gain de cache est mesuré : quatre extractions évitées, un appel au lieu de
cinq. Les dépenses de toutes les étapes ne baissent pas : le dossier enrichi
représente environ 163 000 jetons rapportés contre 50 549 auparavant. Le dernier
email représente 583 401 jetons en 26 appels, contre 591 489 en 26 appels pour
l'ancien meilleur email, avec des entrées de recherche différentes. Aucune
réduction générale de quota n'est déduite de ces seuls essais.

## Livrables

[Email HTML final](../optimization/plausible-root-url/after-crawler-fix/runs/e14d43af-13ea-4f5c-8063-4a9511033dab/email-1.html)
· [Texte](../optimization/plausible-root-url/after-crawler-fix/runs/e14d43af-13ea-4f5c-8063-4a9511033dab/email-1.txt)
· [Rendu mobile](../optimization/plausible-root-url/after-crawler-fix/runs/e14d43af-13ea-4f5c-8063-4a9511033dab/email-390.png)
· [Compteurs](../optimization/plausible-root-url/after-crawler-fix/functional-usage-summary.json).

Les snapshots, diagnostics et décisions se trouvent dans le
[journal](../optimization/plausible-root-url/after-crawler-fix/journal.md) et
l'[état durable](../optimization/plausible-root-url/after-crawler-fix/state.json).
