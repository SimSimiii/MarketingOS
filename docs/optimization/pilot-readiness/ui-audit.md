# Audit local du parcours — 5 octobre 2026

Branche : master. Aucun commit, push, merge ou déploiement effectué.

## Parcours observés dans le navigateur

| Parcours | Résultat et preuve |
| --- | --- |
| Marque neuve | iFixit créé depuis le dialogue ; redirection vers Sources ; scope de la marque affiché |
| Import URL | `https://www.ifixit.com/Store` lu ; 12 pages officielles visibles, titres et nombre de mots présents |
| Marque sans compilation | Indication de génération fraîche ; puis compilation v1 réutilisable après le premier run |
| Création libre | Brief et compteur 1–12 emails ; brief vide refusé avec message lisible |
| Sauvegarde avant dépense | Campagne `18419d1e-1141-47a7-ac6e-e26051355ccf` enregistrée avec contrat de 3 emails, bon CTA et **0 exécution** ; estimation 32–233 appels, sans recompiler |
| Liste | Filtre de marque, recherche Buffer et états Never run / Running / Failed / Completed observés |
| Run actif | Accès à la page de suivi, détail du compilateur et logs/reprises du fournisseur visibles |
| Run terminé | Historique Buffer rouvert ; email, score explicitement simulé et doute du lecteur visibles |
| Copie texte | Copy all a placé 915 caractères dans le presse-papiers, objet attendu en première ligne |
| Copie HTML | Design et Copy HTML testés ; href `https://buffer.com/pricing` présent |
| Mobile | 375 × 812 : formulaire et résumé de livraison relus visuellement ; pas de débordement horizontal du document |

## Corrections

- L'interface ne proposait que lancement, panier et LinkedIn. Ajout de **Custom emails**,
  avec brief explicite et compteur repris par le contrat déterministe du backend.
- Création immédiate suivie d'un lancement : l'estimation arrivait après la dépense,
  et un échec de lancement pouvait conduire l'utilisateur à recréer la campagne.
  Les boutons enregistrent désormais le brief puis ouvrent la page où l'estimation
  et **Run campaign** sont disponibles. Le besoin d'override reste vérifié à ce stade.
- Noms blancs acceptés : trim et refus côté API ; validation du dialogue marque ;
  précision que le site enregistré n'est pas encore importé comme source.
- Résumé mobile : la note prenait presque toute la largeur et réduisait le texte
  de livraison à une colonne de quelques mots. Disposition verticale sur petit écran.
- Runner d'optimisation : `inspect` arrêtait une marque neuve au 404 de compilation
  absente. Cette absence est maintenant enregistrée comme contexte manquant ; les
  autres erreurs continuent de stopper l'inspection.
- Run National Trust : copie exacte du CTA et de la signature à la fin du corps.
  Format clarifié dans le prompt ; retrait conservateur des seuls blocs finaux identiques
  aux champs séparés, qui restent rendus une fois. Aucun gate factuel désactivé.

- Livraison partielle : la page du run et son historique signalent « Partial delivery » ou « Needs review » au lieu de présenter un arrêt avec résultat incomplet comme terminé sans réserve. Le nombre livré et le motif restent visibles.
- Public personnalisé : le public saisi par l’utilisateur atteint les lecteurs de contrôle ; une biographie déduite de la compilation ne le remplace plus. Deux tests couvrent cette transmission et le comportement sans public explicite.

- Rapport de manque de preuves : la recommandation et les questions conservent le besoin précis qui a bloqué le run, au lieu de demander par défaut des témoignages sans rapport avec ce besoin. Test ciblé puis suite complète propre.

- Récupération de preuves : les faits déjà connus gardent leur identifiant canonique après dédoublonnage ; le plan ne reçoit plus de références supprimées. Compteurs de faits vérifiés et de nouveaux faits distingués.
- Échec pendant récupération : seuls les emails sans manque de preuve bloquant sont conservés par le traitement d’erreur, comme sur le chemin normal. Régression vérifiant le cas zéro livraison et le maintien d’un second email propre.

- Arrêts de quota/durée/annulation : le même filtre retire les manques de preuve bloquants, tout en conservant le motif d’arrêt, les questions utiles et les autres emails.
- Planification de séquence : instructions corrigées pour ne pas réserver au dernier email un prix connu indispensable à la décision du premier ; arguments distincts et contexte commercial nécessaire restent compatibles. Le critique évalue la consultation demandée, sans exiger automatiquement une évaluation d’achat complète. Validation réelle en cours.

## Vérifications

Backend : 1 403 tests passent, Ruff `app tests` propre. Deux avertissements existants
de dépendances. Frontend : lint et typage propres, 12 tests passent, build statique
réussi. Les tests couvrent notamment authentification, isolation de compte, renouvellement
et révocation des sessions, reprises et erreurs terminales fournisseur, garde de budget,
annulation et conservation de livraisons partielles.

Les modifications de schémas n'ajoutent pas de colonne : pas de migration nécessaire.
Les serveurs de développement doivent charger le code corrigé avant une séance pilote.

## Limites de l'audit

Navigateur local avec authentification non obligatoire. Les parcours multi-comptes
ont été vérifiés par tests automatisés, pas sur un hébergement distant. Le rendu HTML
a été examiné dans le navigateur ; il ne constitue pas un test Outlook/Gmail réel.
Pas de vraie mesure d'ouverture, de clic, de conversion ou d'achat. Pas d'envoi d'email.
Les coûts sont des estimations enregistrées, pas des factures.

## Captures

- `screenshots/custom-campaign-mobile.jpg`
- `screenshots/saved-brief-estimate.jpg`
- `screenshots/run-summary-mobile.jpg`
- `screenshots/partial-delivery.jpg`

Le kit de séance et le formulaire de retour se trouvent dans `pilot-kit.md`.
Les résultats de génération et les verdicts restent dans les dossiers de cas.

## Reprise du 6 octobre

Le prix vérifié de l’offre explicitement nommée est désormais conservé dans les
preuves disponibles au rédacteur et au critique, avec correspondance du nom et du prix
cité, exclusions respectées et inventaire limité à 15 faits. Aucun appel supplémentaire.
Le replay des 913 faits iFixit retrouve E556 dans les trois slots ; la génération
réelle est en cours. La page live parle maintenant de brouillons relus plutôt que
de prétendre que tous ont réussi la lecture à froid. Vérifications finales :
1403 tests backend, Ruff propre ; frontend typage et 12 tests propres, lint propre.

Le lien choisi dans le brief est transporté en code jusqu’au rédacteur et au critique ;
une preuve récupérée ne remplace plus cette destination par son propre guide.
59 vérifications ciblées incluant le forecast passent ; la suite finale compte 1403 tests.
La relecture distingue une ressource réellement promise et absente d’un argument
que le lecteur trouve peu convaincant. La validation réelle correspondante reste
dans le cas iFixit. Backend et frontend de cette reprise écoutent uniquement 127.0.0.1.
