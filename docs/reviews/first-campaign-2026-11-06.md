# Parcours de première campagne — validation du 6 novembre 2026

Le nouveau parcours se lance depuis l’aperçu de la marque. Il utilise l’URL enregistrée ou les sources existantes, prépare les faits, lit un nombre réduit d’alternatives et compare des hypothèses d’audience. La progression se rafraîchit dans l’interface. Une recommandation positive prépare un brief d’un email en preset Fast. L’utilisateur vérifie l’audience avant de générer.

La vérification officielle traite jusqu’à trois questions produit qui peuvent changer la recommandation, même si elles apparaissent dans les réserves du dossier. Elle ne fait entrer dans Knowledge que les affirmations reliées à des citations lues sur les pages officielles. Les contrôles d’envoi, les contraintes de portée des affirmations et le parcours de campagne manuel restent disponibles.

## Résultats avec les abonnements configurés

| Marque | Résultat observé | Temps et appels du passage indiqué |
| --- | --- | --- |
| Simple Analytics, données du premier audit réutilisées | La vérification a trouvé la politique officielle de signature d’un DPA fourni par le client et le statut de l’audit de sécurité. Le dossier municipal reste `DISCOVERY_ONLY` car la procédure des acheteurs qui exigent un accord standard ou une certification achevée reste indéterminée. | 5 min 07 s, 4 appels après reprise |
| Buttondown, données des premières étapes réutilisées | 13 faits officiels récupérés au cours de deux passages, notamment sur le domaine d’envoi et les cadences RSS. Le dernier dossier reste `DISCOVERY_ONLY` car il traite l’existence d’un modèle de résumé sans Jinja comme une condition du besoin étudié. | 6 min 10 s, 4 appels après reprise |
| Papier, depuis la page d’accueil | Deux pistes examinées. La seule citation directe en faveur de l’usage d’un agenda était de 2019 et ne suffisait pas à établir un signal d’achat actuel. Le parcours a indiqué de revoir l’audience. | 4 min 27 s, 8 appels au premier passage complet |
| Papier, recherche recentrée sur des achats observables | Compilation et premières recherches effectuées. Le quota Claude Code a interrompu la lecture suivante. | 2 min 02 s, 5 appels terminés |
| Simple Analytics, audience GA4 issue de la carte compacte | Les deux pages officielles manquantes au premier audit sont présentes dans l’import. Le quota Claude Code a interrompu la synthèse de la recherche d’audience lors de la reprise. | 24 s, 1 appel terminé lors de la reprise |

La première version séquentielle s’arrêtait autour de 8 à 10 minutes sans recommandation. La compilation compacte a supprimé l’appel séparé de préparation des hypothèses d’audience et le scan concurrentiel peut se dérouler pendant la cartographie. Une première reprise des liens de la carte avait également perdu les distinctions entre sources. Le chemin révisé réutilise uniquement les citations directes et fraîches qui passent les contrôles ou lance une recherche bornée de sources primaires.

## Contrôles du livrable

Le texte accepté lors de l’audit du 5 novembre a été rejoué contre les contrôles du dépôt. Les preuves E80 et E48 sont reconnues dans le texte, et le bouton d’inspection correspond à l’action documentée du brief. Les trois alertes consultatives de cet essai ont disparu. La consigne de rédaction place désormais le bénéfice concret avant le lien qui permet de le vérifier. Les motifs de revue apparaissent dans l’écran du run et les résultats de l’original sont distingués de ceux d’une version ajustée.

Les essais ont confirmé l’import, la reprise, la récupération officielle, le contrôle de recommandation et l’affichage du quota. Aucun de ces essais n’a produit un nouvel email par le parcours de première campagne. Le délai cible de dix minutes jusqu’à l’export et la qualité d’un nouveau premier jet restent à mesurer. Le quota de session Claude Code a indiqué une réinitialisation à 5 h 30, heure de Paris. Aucun email n’a été envoyé.

## Reprendre les essais

Les sources et les dossiers sont enregistrés dans les bases locales isolées des essais, dont les chemins figurent dans les fichiers d’état. Après la réinitialisation du quota, redémarrer le serveur avec la même base et rouvrir **Prepare campaign** pour réutiliser ces étapes. Pour une recommandation positive, ouvrir **Review and generate email**, vérifier l’avis avant le lancement, puis contrôler le texte, le bouton et l’export dans l’interface.

- [Simple Analytics et la piste municipale](../optimization/simpleanalytics-warm-first-campaign-2026-11-06/latest-preparation.json)
- [Simple Analytics et la piste GA4](../optimization/simpleanalytics-v2-first-campaign-2026-11-06/ui-quota-stop.png)
- [Buttondown](../optimization/buttondown-first-campaign-2026-11-06/latest-preparation.json)
- [Papier et l’arrêt faute de preuve récente](../optimization/papier-v3-first-campaign-2026-11-06/before-scope-fix-latest-preparation.json)
- [Papier et l’arrêt sur quota](../optimization/papier-v4-first-campaign-2026-11-06/ui-quota-stop.png)
