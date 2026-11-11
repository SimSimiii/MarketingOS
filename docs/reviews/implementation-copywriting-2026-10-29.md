# Correctifs issus des recherches — 29 octobre 2026

## Modifications intégrées

- Extraction des montants avec symbole après le chiffre, y compris les petits prix, les décimales françaises et les milliers séparés par des espaces ou espaces insécables.
- Normalisation conservant la virgule décimale à une ou deux positions : `29,90` ne devient plus `2990`. Les milliers anglais restent pris en charge.
- Extraction des citations entre guillemets français et des durées françaises, avec équivalences d’unités françaises/anglaises.
- Reconnaissance Unicode des noms accentués dans le contrôle de clarté, y compris les accents décomposés.
- Acronymes administratifs français légitimes exemptés du contrôle des majuscules.
- Compréhension des nombres français écrits jusqu’à douze dans le contrat de campagne, avec mots pivots pour éviter de confondre des raisons et des emails.
- Conservation du pied de page et du lien de désinscription explicitement fournis dans le HTML simple et l’alternative texte.
- Suppression du scénario systématique de surcharge de boîte mail dans les prompts de rédaction, lecture, inbox et duel.
- Instructions de rédaction renforcées sur la pertinence de la preuve, la portée des résultats clients et des prix, les conditions matérielles de l’offre et l’absence de psychologie inventée.

Les appels, rôles, schémas persistés et migrations ne changent pas. Les prompts sont modifiés sans nouvelles variables Jinja. Le volume de réécriture réel peut toutefois évoluer quand des faux rejets disparaissent ou que des erreurs auparavant invisibles sont détectées.

## Couverture et limites

Une nouvelle suite de régression couvre les défauts français reproduits, les équivalences légitimes et les faux rapprochements numériques. Les tests du rendu couvrent la présence des informations explicites dans les deux formats et les deux tiers HTML.

Ce correctif ne constitue pas la réalisation intégrale des lots de conception du plan consolidé. Restent notamment le contrat d’offre complet avec locale explicite et traitement des formats ambigus, les références éditoriales bilingues, la mesure des juges, les diagnostics éditoriaux dans l’interface et le versionnement de l’artefact final. La qualité persuasive des nouveaux prompts n’est pas démontrée par des tests scriptés ; elle nécessite une évaluation comportementale dédiée.

Aucune campagne réelle ni appel modèle facturé n’est utilisé pour valider ces modifications.

## Deuxième incrément : portée des prix et changements tardifs

- Les symboles et noms de devises sont normalisés ensemble : `29 EUR`, `29 euros`, `29 €` et `€29` désignent le même montant ; les devises différentes restent distinctes.
- Le rattachement d’un prix à un plan reconnaît les montants dont le symbole suit le nombre. Il réutilise les contrôles existants de période, unité, produit et restrictions.
- Les formulations françaises `engagement annuel`, `facturation annuelle`, `paiement annuel` et `contrat annuel` sont reconnues comme conditions de paiement annuel.
- Le choix d’un objet ne peut plus ajouter de défaut bloquant sous prétexte que le brouillon possédait déjà un autre défaut. Les contrôles portent sur la paire objet–aperçu avec le corps conservé.
- Une amélioration portant uniquement sur l’aperçu est désormais appliquée.
- Les commentaires du code ne présentent plus le jugement sur l’ancienne paire objet–corps comme une validation du nouvel ensemble, ni les préférences simulées comme des ouvertures mesurées.

Les tests ajoutés vérifient la conservation des conditions d’offre, la séparation des plans et périodes, l’équivalence des devises et le filtrage des changements tardifs. Le versionnement complet des évaluations et artefacts demeure un chantier distinct ; ce correctif ne prétend pas réaliser une nouvelle lecture du message final sans appel supplémentaire.

Validation du deuxième incrément : **2 047 tests backend réussis**, deux avertissements de dépréciation de dépendances ; lint `ruff check app tests` réussi. Les 31 tests ciblés d’intégrité française et d’intégrité de l’objet final réussissent également.

## Validation exécutée

- Suite backend complète : **2 037 tests réussis**, deux avertissements de dépréciation de dépendances.
- Sous-ensemble marketing et connaissances : **946 tests réussis**.
- Lint `ruff check app tests` : réussi.
- Tests ciblés intégrité française, rendu et forecast : **76 tests réussis**.
- `judge_bench --dry-run` : exécuté sans appel modèle ; cette préparation ne mesure pas la qualité du juge.
