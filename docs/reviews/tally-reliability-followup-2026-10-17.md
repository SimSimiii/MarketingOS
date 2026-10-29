# Corrections après le rejeu Tally — 17 octobre 2026

Les défauts reproduits ont été corrigés dans le générateur commun, sans règle
conditionnée au nom de Tally. Les dix exports sources sont inchangés, empreintes
vérifiées. Le contrôle porte sur les données enregistrées ; il ne certifie pas
l'état actuel des sites des fournisseurs.

## Causes et effets

| Avant, constaté dans les données | Après |
| --- | --- |
| Des tarifs Typeform/Jotform, cités dans une comparaison Tally, devenaient des promesses propres à Tally. | Filtrage du sujet et du type de source, y compris pour les anciens artefacts sans contexte. Zéro sujet concurrent dans les 30 faits propres sélectionnés. |
| Le plafond de faits privilégiait les prix ; domaines et suppression de marque disparaissaient du contrôle. | Sélection diversifiée ; 3 faits de contrôle retenus. Les vues Market et campagne utilisent le corpus produit actuel, sans réécrire le scan historique. |
| Catégories communes et conditions commerciales différentes étaient assimilées. | Comparaisons par proposition ; conditions annuelles, unités, devises et périmètres conservés. Absence de capture = inconnue. |
| Une citation disant « easier to handle » soutenait une interprétation disant « complicates handling ». | Détection bornée d'inversions de direction : citation conservée, interprétation marquée inférée et à revoir, exclue du comportement actuel établi. Avertissement visible dans Research. |
| Un besoin non relié au webhook survivait dans le bénéfice, le mécanisme et le CTA après rejet de sa prémisse. | Normalisation cohérente des champs dépendants ; annonce fonctionnelle possible, sans prétendre résoudre le besoin initial. Parcours natif et webhook personnalisé distingués dans les consignes existantes. |
| Les fallbacks et sous-segments qualifiés se perdaient avant la lecture et le rapport. | Sous-segment propagé à la stratégie et au lecteur ; audience effective dans le résultat, en respectant une audience explicitement fixée par l'utilisateur. |
| « now available », abonnement présenté comme prix d'une fonctionnalité, résultat client généralisé. | Contrôles de portée et avertissements contextualisés, même pour le corpus ancien. Les violations chiffrées objectives bloquent ; les interprétations discutables restent des avis. |
| Le modèle produisait des nombres imaginaires de clics et d'ouvertures. | Nouveaux contrats lecteur et objet : appréciation éditoriale directe sur 10, explicitement non calibrée. Anciens champs lisibles pour l'historique, sans les demander aux nouvelles évaluations. |
| Proof séparait la collecte externe des faits déjà connus. | Les deux sont consultables dans Proof, avec tri par mots de l'argument envisagé. Les statuts et conditions ne changent pas avec l'ordre d'affichage. |

## Vérifications

- **1 671 tests backend réussis**, aucun échec ; deux avertissements de dépendances.
- **27 tests frontend réussis** ; lint, TypeScript et build statique réussis.
- Ruff `app tests`, contrat API généré et migrations aller/retour sur SQLite
  temporaire réussis. La base applicative n'a pas été migrée ou modifiée.
- Les **15 sondes originales de positionnement** passent ; les **8 contrôles
  de portée des faits** sont présents. Régressions promues dans la suite normale,
  avec le cas capturé et des produits/offres synthétiques contrastés.
- Le rejeu de chaîne confirme le retrait de l'ancien besoin non lié, de la
  justification CSV inventée et du pourcentage « estimated to bite ». Il confirme
  aussi le nom du lecteur réellement utilisé dans les notes finales.

## Coûts et portée de la validation

Aucun appel de modèle supplémentaire dans la génération automatique. Le contrôle
de portée, le réexamen des anciens artefacts et le classement de navigation sont
déterministes. Proof charge les connaissances compilées via une lecture API.
Sur le corpus sauvegardé, le contexte de positionnement pour la requête explicite
studios/domaines mesure **5 993 caractères**, contre **47 623** dans le rejeu
précédent, soit environ **87 % de réduction de ce seul contexte**. Cela ne mesure
pas une réduction équivalente de la facture ou de la durée totale.

L'essai qualitatif utilise une base jetable, le corpus sauvegardé et la demande
initiale, mais un dossier reconstruit et une politique de revue limitée : un
candidat, un lecteur, critique et au plus une réécriture. Il est donc distinct
d'une comparaison contrôlée avec l'ancienne campagne balanced. Plafond partagé :
12 tentatives fournisseur, 350 000 jetons rapportés vérifiés entre appels,
1 200 secondes. Les résultats réels et l'éventuel blocage sont consignés dans
`docs/optimization/tally-reliability/state.json` et `journal.md`.

## Résultat qualitatif réel et dernier ajustement

L'essai a terminé en **7 tentatives, 335 136 jetons rapportés et 201,47 secondes**.
L'équivalent tarifaire calculé par le catalogue est d'environ **2,40 USD** ;
l'exécution utilise l'abonnement, cette estimation n'est pas une facture.
Un e-mail est livré avec le statut **dégradé** et une appréciation simulée de
**6/10**, sans prédiction de conversion. Mon examen éditorial donne **76/100**
sur la grille fixée avant l'essai, dans une piste distincte de l'ancien run.
Ce cas n'atteint pas encore la qualité visée pour une acquisition froide.

Avant : « Tally is now available… », création de formulaire présentée comme
évaluation d'une intégration, puis configuration de l'endpoint remise à plus tard.
Après : « A closer look at Tally webhooks », capacité documentée, limite de
10 secondes et bouton vers le guide webhook. Le texte est plus cohérent et plus
prudent, mais reste un inventaire technique avec une raison d'agir trop faible.
Les rendus bureau et mobile à 390 px ont été inspectés ; le mobile ne déborde pas
et le bouton mène bien à la source autorisée.

La lecture brute a ensuite révélé que le guide contient déjà un **Example webhook
event**, absent du registre compilé. Le modèle n'avait pas cette ressource lors
de la réécriture. La correction finale fournit des extraits existants pertinents
aux appels déjà prévus de critique et de réécriture, en gardant le lecteur aveugle
et les restrictions de revendications. Le rejeu gratuit de la question Tally
retrouve cette section en 4 252 caractères ; les tests vérifient la transmission,
les sources et l'absence de recherche supplémentaire. L'effet de cette dernière
correction sur le texte généré **n'a pas été réévalué avec un modèle** : aucun
gain de score supplémentaire n'est revendiqué.

Ce contexte est plafonné à 6 000 caractères d'extraits par appel concerné. Il
ajoute des jetons aux appels existants — ordre de grandeur estimé de 1 000 à
3 000 par appel, selon le contenu et le tokenizer — pour éviter de traiter une
source déjà présente comme une information manquante. Il n'ajoute pas d'appel
et ne démontre pas une économie nette. Le conseil automatique de passer à un
preset plus coûteux a aussi été remplacé par une priorité donnée au diagnostic
de l'obstacle et à la vérification du matériau existant.

Les livrables et la grille détaillée sont dans
`docs/optimization/tally-reliability/runs/20261017T030855006005Z/` et
`docs/optimization/tally-reliability/review/`.

## Limites

Retrouver les mots d'une citation ne prouve toujours pas toutes ses implications.
Les vérifications de sens sont ciblées et ne remplacent pas une lecture humaine.
Le tri de Proof rapproche des mots, sans constituer un moteur d'implication
sémantique. Une preuve fonctionnelle ne démontre ni adoption ni résultat client.
Les versions de dossier antérieures à l'interprétation 3 sont à reconstruire ;
les données historiques restent consultables. La migration locale/déployée reste
une opération distincte avant utilisation des nouveaux champs persistés.

Un bon résultat isolé ne validerait que ce cas. Aucun taux de réponse, de clics,
de conversion ou de volonté réelle de payer n'est déduit des tests ou des lecteurs
simulés.
