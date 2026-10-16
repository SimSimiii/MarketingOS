# Décision produit — 13 octobre 2026

## Recommandation

Recruter maintenant cinq personnes correspondant à une même cible, puis commencer par deux séances accompagnées. Terminer une qualification ciblée du parcours distant avant de leur ouvrir les comptes. Priorité au premier email utile, exact et récupérable ; différer les nouveaux grands modules.

Cette note repose sur une nouvelle lecture de résultats locaux sauvegardés, des journaux de qualification et des preuves du déploiement. Aucune nouvelle génération ni nouvel envoi n'a été effectué dans cette revue. Les scores historiques sont des jugements éditoriaux internes, jamais des conversions observées. Les générations historiques via CLI ne qualifient pas à elles seules la qualité du nouveau chemin API/Lambda.

## Éléments examinés

| Élément | Observation | Conséquence |
|---|---|---|
| Plausible, run `f2e0a144-8936-47bb-9136-af932b92f7d7` | Email lisible, objectif précis, prérequis d'installation explicite. Il ressemble encore à une explication de documentation ; peu de tension commerciale. Note historique 85/100. | Bon candidat pour un pilote SaaS simple, après revue de marque. Tester si le destinataire y trouve davantage de valeur qu'avec son outil habituel. |
| Buffer, run `6f450dc7-5046-4204-93ff-14e93d82d84e` | Situation de changement de planning concrète, exemple client, limite du plan gratuit et action cohérente. Note historique 87/100. | Cas étroit utilisable ; ne pas étendre ce verdict à tous les emails Buffer ou à toutes les fonctionnalités. |
| iFixit, run `22f5e0eb-591f-40be-b453-a1369b1c23fd` | Trois emails livrés, mais généralisation incorrecte des exclusions de garantie. Note historique 74/100 ; correction ciblée vérifiée ensuite, sans nouvelle séquence complète. | Le statut « terminé » ne suffit pas. Revalider les conditions et exceptions avant un pilote produit physique. |
| National Trust | Absence de sources suffisantes sur les lieux et restrictions ; résultat `needs_input`. | Refus utile, mais le produit doit dire précisément quoi ajouter et permettre de reprendre facilement. |
| Analyse concurrentielle Plausible, instantané du 30 septembre | Quatre concurrents lus, citations et sources conservées. Plusieurs chiffres de conversion de Plausible sont classés dans l'axe « price ». | Défaut sémantique visible dans cet instantané ; vérifier sa présence dans le code/résultat courant avant correction. La présence d'une citation ne rend pas une comparaison pertinente. |
| Recherche d'audience Plausible | Contre-arguments et limites sont explicités, y compris l'absence de témoignages indépendants pour certaines cibles. | Point positif. Présenter les segments comme des hypothèses, avec les preuves et incertitudes visibles. |
| Déploiement du 13 octobre | Tests automatisés et diagnostics AWS passés ; accès aux deux fournisseurs validé. Aucune campagne réelle produite sur ce chemin lors du déploiement. | Infrastructure qualifiée à ce niveau, qualité réelle en production encore à vérifier sur un petit échantillon. |

Sources locales : `cross-brand-validation/{plausible,buffer-flexible}/runs/`, `cross-brand-validation/plausible/{market,audience}.json`, `pilot-readiness/ifixit/quality-8.md`, `pilot-readiness/{ifixit,national-trust}/state.json`, et `../deployments/2026-10-12.md`.

## Avant la première séance distante

1. Vérifier le parcours complet avec un compte invité : connexion, import de quelques sources, brief, génération, retour après fermeture de page, export. Vérifier avec un second compte que les données du premier restent inaccessibles. Les tests automatiques existent ; cette étape qualifie le parcours réellement déployé.
2. Qualifier un email SaaS en français si les premiers testeurs sont francophones, puis une séquence courte. Relire chaque affirmation, restriction et destination du CTA. Les validations historiques examinées concernent surtout l'anglais.
3. Échantillonner l'analyse concurrentielle : contrôler cinq affirmations importantes dans leurs sources, la comparabilité des offres, le classement des axes, les dates et les limites de couverture. « Aucun angle libre trouvé » doit rester relatif aux concurrents/pages examinés.
4. Mesurer la durée et la consommation de tout le parcours, y compris première compilation, recherches et essais échoués. Les estimations historiques de CLI ne sont pas des factures de l'API actuelle.
5. Écarter du pilote l'analyse d'images encore non adaptée au workflow et les cas complexes de garantie. Prévoir un message clair pour les sources insuffisantes et les livraisons partielles.

Ne pas multiplier les générations identiques. Chaque nouveau run doit répondre à une question : français, séquence, fidélité des conditions, compatibilité API ou parcours distant.

## Pilote proposé

- Cible initiale suggérée : cinq fondateurs ou responsables marketing de petits SaaS B2B ayant une campagne réelle à préparer. C'est une hypothèse de cible fondée sur les cas les mieux qualifiés, pas une preuve de marché.
- Deux séances accompagnées d'abord ; corriger les obstacles observés, puis trois autres séances avec moins d'aide.
- Demande : « À partir de vos pages et de votre offre, préparez un email que vous envisageriez réellement d'utiliser. » Observer sans dicter les clics.
- Réserver 30–45 minutes de manipulation/relecture ; traiter séparément l'attente de génération. Aucun envoi à une liste de destinataires n'est requis.
- Recueillir les changements exacts du texte, minutes de retouche, aides nécessaires, erreurs factuelles, compréhension de la recherche et intention de réutilisation.
- Comparer le résultat à leur méthode habituelle avec les mêmes sources et le même brief. L'ordre des résultats peut être alterné pour limiter le biais.
- À la fin, proposer un second usage concret. L'usage répété et, plus tard, un achat réel informent davantage qu'une réponse polie à « paieriez-vous ? ».

Le recours à un petit groupe sert à trouver des problèmes qualitatifs ; il ne permet pas d'estimer un taux de satisfaction représentatif. Références : [NN/g](https://www.nngroup.com/articles/how-many-test-users/) et [GOV.UK, tests accompagnés](https://www.gov.uk/service-manual/user-research/using-moderated-usability-testing).

Seuils de décision proposés, à fixer avant les séances : aucune fuite entre comptes, aucune affirmation matérielle fausse dans les livrables relus, quatre participants sur cinq récupèrent leur résultat avec au plus une aide, et trois sur cinq jugent le texte utilisable après moins de dix minutes de retouche par email. Ce sont des objectifs de pilote, pas des résultats acquis. Examiner aussi les raisons des échecs plutôt que la seule moyenne.

## Priorités de développement

| Priorité | Amélioration | Pourquoi / condition |
|---|---|---|
| Avant pilote | Exactitude des comparaisons et conservation des restrictions | La recherche doit conduire à une décision défendable, pas seulement produire des citations. Rejouer un cas courant avant de conclure qu'un défaut historique persiste. |
| Avant pilote | Parcours de sources insuffisantes et statut partiel compréhensibles | L'utilisateur doit savoir ce qui manque, ce qui est déjà utilisable et comment continuer. Améliorer l'existant, sans créer un second système de statut. |
| Avant élargissement | Consommation, attente et erreurs visibles | Comprendre le coût réel de service et les budgets ; vérifier les plafonds avant d'augmenter le nombre de testeurs. |
| Après les deux premières séances | Retour attaché à un email ou à une affirmation | Capturer précisément « faux », « trop générique », « mauvaise cible » et le changement attendu ; rester léger. |
| Si la réécriture globale gêne les utilisateurs | Révision ciblée d'un passage, préservant les parties approuvées | Réduire le coût et les régressions par rapport à une régénération complète. |
| Si un outil d'envoi revient chez plusieurs testeurs | Une seule intégration d'export adaptée | Le copier/export actuel suffit pour apprendre ; choisir l'intégration à partir des usages. |
| Plus tard | Envoi automatique, CRM complet, nouveaux canaux, nombreuses variantes, tableau de ROI | Charge et complexité prématurées avant preuve d'utilité récurrente. Un tableau de ROI sans données réelles serait trompeur. |

L'ordre recommandé est : qualification ciblée du parcours déployé, deux utilisateurs réels, corrections observées, trois utilisateurs supplémentaires, puis décision sur une bêta plus autonome. Ne pas attendre une perfection abstraite ; ne pas assimiler tests techniques et valeur commerciale démontrée.
