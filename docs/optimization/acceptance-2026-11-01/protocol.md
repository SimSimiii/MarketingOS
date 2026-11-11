# Audit d'acceptation borné — protocole arrêté avant les nouvelles générations

Client hypothétique : responsable marketing d'une petite entreprise, capable de vérifier les faits de sa marque mais ne souhaitant pas écrire lui-même toute la campagne.
Promesse : à partir des informations de la marque, obtenir une campagne cohérente, fondée sur ces informations, vérifiable, ajustable et exportable après une revue normale.
Décision : utilité technique suffisante pour proposer cette offre à la vente ; volonté de payer et rentabilité demeurent des questions distinctes. Aucun client réel ni taux de conversion requis pour terminer cet audit technique.

## Échantillon fixé

1. Papier : un email d'acquisition, connaissances et audience existantes.
2. Papier : un email de considération, même audience, lecteur connaissant déjà la marque.
3. systeme.io : un email d'acquisition, audience existante, expéditeur affilié indépendant.
4. systeme.io : séquence de trois emails d'acquisition, même audience et même transparence d'affiliation ; aucune interaction antérieure inventée.
5. Loops : un email d'acquisition depuis la seule homepage https://loops.so/ ; première audience exacte de la nouvelle carte.
6. Loops : un email de considération pour cette même audience, sans recompilation inutile.
7. Limite : besoin CABAIA ordinateur + repas + gourde insuffisamment étayé ; lire le précontrôle sans le forcer.
8. Limite : demande sur une marque sans connaissances ; vérifier le diagnostic et l'action possible sans générer une promesse fictive.

Les cas ordinaires refusés restent dans le dénominateur ; pas de remplacement par une audience ou une marque plus facile. Si Loops est bloqué en préparation, ses deux cas ne sont pas déclarés réussis.

## Conditions

Amendement du 2 novembre : après le premier bilan, l’utilisateur a explicitement
demandé de poursuivre les corrections et les essais jusqu’au seuil d’acceptation
ou à l’épuisement des quotas. Les plafonds d’une génération et de deux retouches
ci-dessous décrivent donc le protocole initial, conservé comme baseline. Les
nouvelles itérations sont archivées séparément ; les six cas, leur dénominateur,
la définition d’une retouche mineure et le seuil de cinq réussites ne changent pas.
Les plafonds de temps, de tokens et de propositions propres au produit restent
appliqués. Aucun résultat initial n’est effacé ni remplacé par un cas plus facile.

- Code courant, branche courante, copie SQLite séparée migrée normalement. Les données d'audit peuvent être créées dans cette copie seulement.
- Preset balanced, stratégie auto, modèles du preset ; modèles explicites locaux aux jobs de préparation lorsque nécessaire, conservés dans les snapshots. Plafonds de temps/tokens du dépôt conservés.
- Une génération par cas ordinaire ; pas de boucle d'optimisation pour améliorer la note. Un défaut technique découvert est documenté ; une correction éventuelle crée une nouvelle révision sans effacer le résultat initial.
- Préparation Loops : un import homepage avec découverte normale, une compilation, un scan, une carte, une recherche de la première audience, un dossier ; pas de liens de documentation injectés manuellement.
- Deux retouches réelles supplémentaires au maximum (Papier et systeme.io), avec les budgets bornés existants ; acceptation/refus/export vérifiés dans l'interface.
- Trois comparaisons directes maximum : même modèle, même demande, même audience et connaissances compilées que le système, mais un seul appel de rédaction. Donner aussi le dossier au témoin évite de le désavantager ; cette comparaison isole la rédaction et ne mesure pas un gain humain de préparation.
- Compter appels, réparations, retries, durées et coût estimé ; distinguer abonnement réel et estimation monétaire.
- Utiliser les helpers existants pour les snapshots. Une commande d'installation ou de migration propre à l'audit ne compte pas comme une étape client ; une intervention nécessaire pour terminer une tâche produit, oui.
- Aucun envoi ni déploiement. Pas de changement de réglages globaux.

## Acceptation

- Au moins 5/6 cas ordinaires utilisables avec retouches mineures. Une retouche mineure conserve l'argument, les preuves, l'offre et l'action ; elle ne réécrit pas l'essentiel. Lister les modifications nécessaires, sans inventer une durée humaine observée.
- Aucune erreur factuelle majeure observée dans les livrables acceptés : prix/plan, compatibilité, preuve, promesse ou destination trompeuse. Une erreur majeure observée bloque l'acceptation de la version évaluée même si les gates passent.
- Pas d'intervention en code/base nécessaire à l'utilisateur pour terminer le parcours observé.
- Ajustements conservant les faits et contraintes ; original et historique disponibles ; copie/export de la version choisie.
- Les deux cas limites sont clairement identifiés, avec une suite raisonnable, sans forçage pour les faire réussir.
- Le parcours réel UI et les artefacts exportés sont observés séparément des API. L'autonomie d'un utilisateur novice reste non mesurée : l'opérateur est un agent technique.
- La comparaison directe doit identifier un avantage concret (moins de reprises matérielles, meilleures preuves/contraintes, séquence plus exploitable, ou préparation/réutilisation observable). Une jolie UI ou davantage d'appels ne suffit pas. Si aucun avantage n'apparaît, l'utilité différentielle reste non établie.

Les seuils sont des règles de décision de cet audit, pas une norme universelle. Les notes des lecteurs simulés, les notes éditoriales du coordinateur et le statut degraded ne sont pas des veto commerciaux automatiques. Les défauts substantiels qu'ils signalent sont vérifiés sur pièces. Les tests de code ne prouvent pas la valeur produit.

Fin de l'audit : rendre accepté, refusé sur défauts précis, ou incomplet sur blocage externe/preuve manquante. Ne pas ajouter une nouvelle exigence de perfection après lecture des résultats.
