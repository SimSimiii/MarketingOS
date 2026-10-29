# Validation du 29 octobre — état de reprise

**La confirmation commerciale générale reste refusée. Un seul parcours complet est validé à ce stade : systeme.io, email 88/100.** Le protocole exige trois cas complets sur quatre, dont un ecommerce physique et un affilié indépendant. Un test exploratoire accompagné avec un ami reste approprié ; une promesse de fonctionnement autonome sur toutes les marques ne l'est pas.

Les scores historiques CABAIA71, Papier84 et RTINGS86 restent attachés à leurs anciens emails. Aucun score ne monte à cause des tests logiciels. Le nouvel email systeme88 appartient à un autre corpus automatiquement collecté ; ce n'est pas un A/B strict.

| Marque | Résultat actuel | Phase restant à améliorer |
|---|---|---|
| systeme.io | Email88/100 réellement inspecté, completed, needs_review=false ; dossier v6/interprétation16 courant, besoin principal addressed | Revue ordinaire de marque ; périodes des montants payants non établies, logistique avancée hors portée |
| CABAIA | Dernier email historique71/100 ; refus documentaire conservé | Collecte des fiches et preuve qu'un même sac couvre ordinateur, déjeuner et bouteille ; ne pas remplacer par trois accessoires séparés |
| Papier | Knowledge472faits, dossier v2/interprétation16 addressed, GO_NARROW sans override ; nouveau test email en cours | Recherche d'audience : deux sources Obsidian périphériques, un problème mono-source, pas de demande professionnelle papier16semaines corroborée |
| RTINGS | Knowledge176faits avec guide TV ; recherche6pages/4problèmes ; dossier v3/interprétation16 partial, DISCOVERY_ONLY | Lire et vérifier les opérations des outils de comparaison, taille/distance et tableau de résultats ; ne pas inventer leur fonctionnement ou la couverture de variantes |

## Corrections vérifiées

A21 conserve des diagnostics de collecte sans secrets d'URL. A22 autorise une seule recherche sur d'autres hôtes quand toutes les premières pages sont illisibles : au maximum20URLs et3appels. A23 rejette les contrôles d'accès explicites et les recherches sans observation vérifiée. Aucun captcha n'est résolu. A24 conserve les faits éditoriaux utiles avec leur propriétaire tiers et réserve des preuves pour le besoin principal. Le dossier RTINGS conserve néanmoins ses vraies lacunes.

A25 ajoute une vérification explicite des questions produit du dossier courant, avant génération : recherche officielle, fetch Python, citations vérifiées, persistance commune au pipeline puis réévaluation. Budget annoncé : jusqu'à2appels pour les faits et1pour le dossier. Sans fait vérifié, Knowledge et dossier restent inchangés ; aucune génération d'email n'est lancée. Le bouton et le contrat API sont ajoutés. Les tests vérifient notamment l'absence de dépense sans dossier courant, la persistance réelle et l'absence d'invention quand la recherche est vide.

Validation A25 sur disque : **2013 tests backend réussis**, Ruff propre ; frontend lint, typecheck et **30 tests réussis**. Logs : `.audit-session/backend-tests-corrections-A25.txt` et `.audit-session/frontend-A25.txt`. Ces tests utilisent des fournisseurs scriptés et ne prouvent pas le comportement réel d'A25.

## Activation et reprise

Le serveur principal sur8000 reste sur **A24**. Le contrôle automatique d'approbation a rejeté la commande groupant sauvegarde et redémarrage avec le motif `blocked by policy`, sans autre détail. Aucun arrêt n'a eu lieu. Aucun worker ASGI ni autre port n'a été lancé pour contourner ce refus. **A25 est implémenté et testé localement, mais son retest réel RTINGS reste à faire.**

Après résolution de ce blocage d'activation : vérifier tous les jobs terminaux et sauvegarder SQLite, activer A25, puis utiliser sur le cas RTINGS `dossier_options.verify_product_gaps=true` et `audit dossier --revision official-product-verification-A25`. Ne fournir aucun lien documentaire ni fait manuel. Capturer le reçu terminal, retirer l'option, et suivre l'éventuelle demande normale de réévaluation des mêmes audiences si leurs références de capacités deviennent inconnues. Ne pas forcer une campagne si le refus demeure.

## Choix des modèles

Les fonctions textuelles testées fonctionnent avec les sélections locales OpenAI. Les résultats de recherche dépendent encore fortement de la lisibilité et de la pertinence des sources : les deux sources Papier sont lisibles mais hors du besoin exact. La tentative Claude a échoué sur une session OAuth expirée, ce qui mesure la disponibilité du fournisseur, pas sa qualité. Pas de preuve d'une supériorité générale d'OpenAI, ni de justification pour supprimer Claude partout. Les rôles exigeant encore web_fetch et la lecture d'images restent hors du périmètre validé. Aucune préférence globale, clé API ou facturation par crédits n'est modifiée.
