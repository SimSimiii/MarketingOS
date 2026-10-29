# Corrections et nouvelle validation

État : retests réels en cours. Les notes précédentes 71/84/84/86 restent historiques ; aucune note n'est relevée sur la seule base des tests.

| Défaut constaté | Correction du système | Vérification disponible |
|---|---|---|
| Besoin principal remplacé par un problème secondaire | Évaluation sourcée du besoin définissant l'audience ; un besoin partiel ne devient plus une recommandation commerciale | Tests de contrat ; nouveaux dossiers systeme conservés, avec refus intermédiaires |
| CTA « fiche produit » vers la homepage | Destination vérifiée exigée dans la stratégie et absence de repli silencieux au rendu | Tests stratégie et persistance ; nouvel email à inspecter |
| Articles RTINGS réduits aux menus | Lecture bornée des narratifs publics dans les données inertes ; contenu réservé exclu | Article diagnostic : 2 627 → 7 248 caractères ; nouvel import normal avec guide TV substantiel |
| Prix systeme remplis de null | Rendu public optionnel et borné, sans session utilisateur ni formulaires ; lacune explicite si indisponible | Import depuis la homepage et Knowledge v3 avec quatre offres et leurs limites |
| Parcours concurrent hors sujet | Priorité des liens tenant compte du domaine produit et de la raison du profilage | Tests gratuits ; nouveau scan RTINGS à examiner |
| Familles ecommerce et tarifs mal explorés | Diversité des collections ; vrais segments de chemin pour les tarifs | Tests : les produits « bold-plans » ne deviennent plus des pages de prix |
| Avertissements perdus sur import identique | Rafraîchissement des indicateurs de collecte de la même URL sans modifier ses faits | Tests et nouvel import CABAIA avec lacune de crawl visible |
| Métalangage d'audit dans les emails | Instructions rédacteur/critique centrées sur la décision du lecteur | Nouveaux emails à inspecter |
| Langue HTML anglaise imposée | Langue déclarée par le rédacteur, repli de détection pour l'historique, validation de l'attribut | Tests français et attribut invalide ; nouvel asset à inspecter |
| Preuves françaises écartées par un besoin anglais | Concepts de récupération FR/EN, distincts des contrôles de véracité | Rejeu exact systeme : E49 et E13 désormais présentes, sans perdre les 48 faits sélectionnés auparavant |

La sélection de mécanismes peut dépasser légèrement son budget souple lorsque les conditions des faits imposés le remplissent. Le rejeu systeme conserve 50 faits au lieu de 48. Il n'ajoute aucun appel modèle et ne change pas les règles de vérification des citations.

Validation technique A20 : **2 003 tests backend réussis**, Ruff propre. Frontend : lint, typecheck et **29 tests réussis**. Les logs complets sont conservés dans `.audit-session/`.

Les compilations CABAIA et RTINGS interrompues le 27 octobre sont conservées comme interruptions. Aucun email n'était actif au redémarrage du 28 octobre. Une sauvegarde SQLite précède chaque rechargement ; la branche reste `master`.

Limites maintenues : les prix systeme capturés ne suffisent pas à associer automatiquement chaque montant à une période ; plusieurs pages CABAIA restent illisibles ; les résultats de conversion et la volonté de payer ne sont pas mesurés. Les anciennes sorties et les refus ne sont pas modifiés.
