# Vérification MarketingOS — 8 novembre 2026

Arrêt des appels modèles : quota Claude Code atteint pendant la récupération de preuves Buttondown. Le fournisseur annonce une réinitialisation le 8 novembre à 06:50, Europe/Paris. Les bases et traces sont conservées. Aucun envoi ni déploiement ; branche master inchangée. Base de travail isolée : C:/Users/oussa/AppData/Local/Temp/marketingos-audit-nov08-9822e33988814c50ab7baefe229063eb.sqlite.

## Ce qui a changé

- Les montants dont les modalités de paiement sont explicitement inconnues restent à confirmer : sélection utilisateur, contrat de copie et corpus brut ne les rendent pas vérifiés.
- Le contrôle couvre aussi les captures contenant Pay monthly et Pay yearly sans état sélectionné rattaché au montant. Le compilateur peut affirmer à tort « option mensuelle affichée » : ce libellé ne suffit plus. La protection s’applique à la compilation, à la récupération officielle et à la lecture des anciens artifacts en cache. Des modalités explicitement citées restent utilisables. Aucune nouvelle compilation modèle n’est requise pour protéger les données existantes.
- Les citations peuvent reprendre les mots visibles de liens Markdown. Seules les destinations dans la source sont ignorées : une URL inventée dans la citation reste refusée. Les références de provenance utilisent la même comparaison.
- Le chercheur officiel reçoit jusqu’à 8 000 caractères de passages pertinents déjà capturés, comme pistes d’URL à refetcher. Une fonction absente du ledger peut donc être retrouvée sur une page déjà ingérée. Le budget reste de deux appels de recherche/extraction.
- La décision de pertinence conserve le niveau Deep en mode resserré. Une recommandation déjà GO/GO_NARROW ne rachète pas une recherche pour des questions facultatives. Les exigences réellement nécessaires restent bloquantes si leur support est inconnu.
- Le choix de l’argument privilégie un usage opérationnel prouvé. Une intégration peut être proposée conditionnellement sans supposer que le destinataire l’utilise déjà. La gratuité soutient l’usage ; tester l’interface ne doit pas remplacer sa valeur. Les détails de code sont réservés aux messages d’implémentation.

Version finale d’interprétation : 27. Les anciens essais de récupération antérieurs au contexte source v26 peuvent être réexaminés une fois ; les autres reçus sur les mêmes entrées restent réutilisables.

## Résultats réels

| Piste | Préparation | Génération | Résultat examiné |
| --- | --- | --- | --- |
| Tally, piste de diagnostic et correction | Démarrage initial : 18 appels, 13 min 31 s, sans campagne ; reprises distinctes conservées | 5 appels, 2 min 32 s, puis un ajustement local en un appel | Email utilisable après revue normale ; version raccourcie acceptée, original et historique conservés |
| Nouveau Tally, réellement vierge, v25 | Homepage seule ; 14 appels, 6 min 44 s ; objectif par défaut, aucune configuration de faits/audience/modèle | 5 appels, 2 min 36 s | Parcours complet atteint, argument trop générique : 72/100, non accepté comme résultat payant |
| Même Tally, même ledger et même audience, après correction | Un dossier reconstruit en un appel, sans nouvelle source | 5 appels, 2 min 26 s | Usage Pro concret : travail partagé, retrait de la marque Tally, lien personnalisé. 83/100 après lecture et contrôle des sources |
| Buttondown, reprise de sources sauvegardées la veille | Baseline 20 appels ; reprises v24/v25/v26 séparées. Dernière reprise : 5 appels terminés puis échec de quota | Aucun email de cette nouvelle piste | La preuve d’envoi API reste à récupérer et valider en réel ; ne pas forcer l’audience « hors de toute politique de plateforme » |

Les notes /100 sont mon jugement éditorial selon la grille fixe du skill, pas une mesure de conversion. Le nouveau Tally conserve un statut applicatif needs_review : son lecteur simulé reste à 6/10 et réclame un prix exact. Le prix affiché sans base de facturation certaine n’a pas été inventé pour améliorer ce verdict. Le bouton mène à la tarification.

Le passage de 72 à 83 porte sur le même ledger, la même audience et le même objectif. Le dossier a aussi été reconstruit : cela ne mesure pas isolément l’effet d’une phrase du prompt. Le premier démarrage complet ne doit pas être confondu avec cette reprise.

Avant : « You can build it before deciding whether Tally suits the job. » L’email dépensait seulement E1, la capacité gratuite.
Après : « With Tally Pro, your team can maintain intake and survey forms together, then present them without Tally branding and under your own branded link. » Il dépense R1, E16 et E17. Le montant ambigu n’est pas affirmé.

## Vérification du parcours

La copie UI et le téléchargement contiennent la version choisie. Les deux derniers emails ont été rendus et inspectés à 390 et 1280 pixels sans débordement. L’ajustement Tally a repassé ses propres contrôles déterministes ; son score de lecteur reste nul, distinct de celui de l’original. L’original et l’historique sont préservés.

Le CTA de création a été ouvert indépendamment : il affiche bien le créateur de formulaire Tally. Aucun formulaire n’a été publié. La tarification et ses boutons mensuel/annuel ont été consultés séparément de la matière fournie au générateur. Le montant mensuel facturé 25 € constaté dans cette inspection n’a pas été ajouté manuellement au ledger.

La piste vierge a consommé 6 min 44 s de préparation et 2 min 36 s de génération, soit environ 9 min 20 s d’exécution. Le temps écoulé observé est plus long à cause de la consultation intercalée. Le temps actif du client n’a pas été mesuré séparément. Les estimations USD de l’application ne sont pas la facturation réelle des abonnements.

## Limites à résoudre à la reprise

1. Recherche d’audience : une situation est classée grounded en citant seulement une liste d’intégrations sur une page vendeur. Ce passage prouve des fonctions, pas l’existence observée d’un responsable ops/CS ni son organisation actuelle. La carte et le dossier indiquent heureusement une hypothèse, avec zéro problème acheteur de première main ; le label de l’observation doit être corrigé aussi. La revue de toutes les étapes reste incomplète pour cette raison.
2. Buttondown : le rejet de sa citation API visible a été reproduit puis corrigé sans modèle. Le dernier probe accepte maintenant cette citation réelle. La récupération de l’affirmation dans le ledger, puis l’email, n’a pas été achevée avant l’épuisement du quota.
3. Après ces deux points, valider un parcours vierge avec l’ensemble du code final. Ne pas présenter la piste Tally v25 ou la reprise après changement comme un premier démarrage inchangé de v27.

Verdicts séparés : les deux derniers livrables Tally sont utilisables après une revue normale ; la validation globale du parcours final est inachevée ; l’existence d’acheteurs payants n’a pas été mesurée. Aucun des scores de qualité ne doit être relevé par les tests de code.

## Contrôles techniques

La suite backend finale passe : **2 246 tests**, en 4 min 18 s. La dernière protection passe aussi 80 contrôles ciblés ; la sortie complète est enregistrée dans backend-tests-2026-11-08-final.txt. Ruff app/tests propre. Frontend : lint et TypeScript propres, 37 tests passent. Aucun champ API public ni migration ajouté dans cette itération.

## Traces

- [Dernier email Tally](../optimization/tally-cold-v25-first-campaign-2026-11-08/email-v26.html)
- [Comparaison et état Tally](../optimization/tally-cold-v25-first-campaign-2026-11-08/state.json)
- [Revue de toutes les étapes](../optimization/tally-cold-v25-first-campaign-2026-11-08/commercial-review.json)
- [Version Tally ajustée et choisie](../optimization/tally-cold-first-campaign-2026-11-08/selected-email.html)
- [Blocage précis Buttondown](../optimization/buttondown-cold-v3-first-campaign-2026-11-07/resume-2026-11-08/preparation-v26-quota-blocked.json)
- [Derniers probes gratuits sur les sources réelles](../optimization/tally-cold-v25-first-campaign-2026-11-08/free-final-source-probes.json)
- [Suite backend finale](backend-tests-2026-11-08-final.txt)
