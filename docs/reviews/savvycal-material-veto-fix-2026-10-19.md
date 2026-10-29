# Correction du veto éditorial sur les brouillons

Demande : corriger l'absence d'email livré et expliquer l'utilité du mécanisme.

Le critique, la recherche de matériel officiel et le replan borné sont utiles.
Le veto global de livraison ne l'est pas : une préférence de preuve plus forte
peut être mal classée comme fait manquant. Ce classement modèle ne doit pas
effacer un brouillon ayant passé les contrôles déterministes.

## Comportement corrigé

- Les gates bloquantes restent actives, ainsi que le préflight lorsqu'aucune
  matière exploitable ne permet d'écrire.
- Le critique peut toujours demander une révision, un autre argument ou du
  matériel vérifié. La recherche officielle et le replan restent bornés.
- Une réserve persistante de matériel reste dans le rapport et rend le texte
  « à revoir », sans supprimer le brouillon qui passe les gates.
- Le parcours normal, l'exécution par étapes, l'annulation et la récupération
  en erreur suivent la même règle de conservation des brouillons.
- Le prompt distingue une affirmation ou ressource effectivement promise
  d'un aperçu préalable seulement souhaité par un lecteur simulé.

Les contrôles automatiques ne garantissent pas toute la vérité sémantique.
Conserver une réserve et demander une revue explicite reste nécessaire ; le
résultat n'est pas présenté comme approuvé lorsque le point n'est pas résolu.
Aucun appel modèle supplémentaire ni changement de schéma/API/base de données.

## Validation gratuite

- 1 749 tests backend passent, dont la régression inspirée du sondage SavvyCal.
- Le test par étapes vérifie la persistance des textes/HTML et `needs_review`.
- Les tests couvrent aussi la récupération infructueuse et l'annulation ; les
  contrôles existants continuent de refuser les chiffres non sourcés et le
  préflight sans contenu exploitable.
- Ruff, lint frontend, TypeScript et 28 tests frontend passent.

Deux warnings backend de dépréciation et les warnings Node de type de module
ne sont pas des échecs de ces vérifications.

## Comparaison réelle

Baseline conservé : `43b2b74b-6e43-47a2-8dae-3772d0cfff2a`, 25 appels, 5 min 59 s,
trois brouillons et zéro email livré. Email non noté, car absent.

Nouvelle exécution : `f3b1420d-d6a1-4010-b4fa-fcdc8b9fe6e4`.
Même campagne, même demande, même première audience, mêmes sources, dossier
current et GO_NARROW sans override. Seul le générateur est corrigé ; les
résultats du baseline ne sont ni réécrits ni promus manuellement.

La relance livre **1 email sur 1**, avec texte et HTML. Le processus termine
completed, l'issue est degraded et needs_review=true. L'interface réelle affiche
« Drafts Need Review », le texte copiable et le téléchargement ; aucun blocage
demandant de nouvelles réponses. Aucune dérogation de génération.

| Mesure | Baseline | Après correction |
|---|---:|---:|
| Emails livrés | 0/1 | 1/1 |
| Appels modèle terminés | 25 | 10 |
| Durée | 5 min 59 s | 2 min 48 s |
| Groupes d'agents | 10 | 4 |
| Évaluation éditoriale de l'asset | Non notée, absent | 78/100, à revoir |

Le nouveau critique classe la réserve en argument, sans demander de nouvelle
ressource ni de replan. La réduction d'appels est observée sur ce cas ; elle
n'est pas garantie pour toutes les campagnes. La protection contre un futur
mauvais classement missing_material est démontrée par les tests scriptés, qui
forcent précisément ce classement jusqu'au bout, et par le test de persistance
à travers plusieurs étapes. Ne pas attribuer à la seule conservation un effet
que la nouvelle classification a aussi produit pendant la relance réelle.

## Revue de l'email livré

Sujet : « Put rules around open slots ». L'email explique le délai de préavis,
le respect des plages réservées et les plafonds de réunions par jour/semaine/mois.
Il nomme SavvyCal et son offre. E9, E108 et E109 sont tous assignés et dépensés ;
aucun échec bloquant, ni tarif ou résultat chiffré inventé. Les lecteurs simulés
comprennent l'offre et donnent 6/10, ce qui reste une réserve éditoriale.

Le critique conteste la pertinence de l'angle de protection du calendrier pour
le fondateur retenu, davantage décrit par sa gêne à envoyer un lien. Le besoin
opérationnel existe dans la recherche P2 mais son applicabilité à chaque membre
de ce segment n'est pas acquise. Le rapport conserve cette limite. Le CTA
« créer un compte » reste aussi un engagement dont l'intérêt est imparfaitement
établi pour cette personne.

Grille stable : faits 24/25 ; audience/offre 14/20 ; spécificité/argument 14/20 ;
sujet-corps-CTA 10/15 ; rendu 9/10 ; promesses/répétitions 7/10 : **78/100**.
Jugement de revue du livrable, pas mesure de conversion ni validation de toute
l'application. Pas de delta chiffré contre un baseline qui n'avait aucun asset.
Meilleur score du cas : itération 2, 78/100.

Rendu vérifié visuellement à 1280 et 390 px, sans débordement. Lien réellement
livré : https://savvycal.com/, HTTP 200, homepage correcte. Il diffère toutefois
du /signup prévu au brief : limite distincte de résolution du CTA à traiter,
pas un lien réparé dans le résultat. Aucun formulaire soumis ni email envoyé.
Le mécanisme de livraison demandé est corrigé ; l'email conserve des points
à revoir avant envoi, et le seuil de copie prête à envoyer n'est pas revendiqué.

Assets et preuves :
`docs/optimization/savvycal-root-url-2026-10-19/runs/f3b1420d-d6a1-4010-b4fa-fcdc8b9fe6e4/` :
`email-1.txt`, `email-1.html`, `email-1280.png`, `email-390.png`, `result.json`,
`timeline.json`, `render-check.json`, `cta-check.json`, `ui-check.json`.

Les routes réelles du code courant s'exécutent dans un worker ASGI sans listener
ni lifespan, conformément au protocole de ce cas. Les anciens serveurs ne sont
pas rechargés ; le test ne prouve pas l'activation du correctif dans leur mémoire.
Le worker a été arrêté après collecte du résultat terminal. Branche master conservée.
