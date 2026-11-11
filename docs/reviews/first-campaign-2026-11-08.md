# Validation finale MarketingOS — 8 novembre 2026

**Verdict d’utilité : vendable comme outil de préparation et de rédaction d’emails sourcés, avec une revue de marque normale avant copie/envoi.** Les vérifications restantes ont abouti sur Buttondown et sur une nouvelle marque Tally créée depuis sa seule homepage. Les emails livrés donnent une raison concrète d’utiliser le produit et conservent les conditions qui limitent leurs affirmations.

Les essais utilisent les abonnements configurés, une base SQLite isolée et la branche master. Aucun envoi de message, formulaire publié ou déploiement. Les essais antérieurs interrompus sont conservés dans [le rapport historique](first-campaign-2026-11-08-quota-history.md).

## Résultats réels acceptés

| Cas | Préparation | Génération | Revue finale |
| --- | --- | --- | --- |
| Buttondown, reprise des sources sauvegardées | 5 appels ; 201 s | 3 appels ; 127 s | 87/100 ; sans alerte de revue restante |
| Nouveau Tally, parcours homepage seule | 12 appels ; 347 s | 3 appels ; 118 s | 85/100 ; sans alerte de revue restante |

Ces notes /100 sont ma revue éditoriale sur la grille fixe : support factuel, audience/offre, argument, continuité, présentation et absence de promesses indues. Les lecteurs simulés de l’application donnent respectivement 8/10 et 7/10 ; leurs scores ne prédisent pas une conversion.

Tally a parcouru ingestion, compilation, marché, carte d’audience, recherche, dossier et génération sur le code v28, sans reprise, choix manuel de faits, consigne libre, sélection de modèle, URL documentaire ajoutée ou passage forcé. L’objectif prérempli a été conservé. Temps d’exécution cumulé : environ 7 min 45 s ; le temps écoulé observé comprend aussi une pause d’inspection entre préparation et lancement. Le temps actif du client n’a pas été mesuré séparément.

Buttondown est une reprise, dont le temps n’est pas présenté comme un premier démarrage. Le scénario « sortir de toute politique de plateforme » est resté non autorisé ; le système a retenu le scénario développeur effectivement supporté.

### Buttondown

[Email livré](../optimization/buttondown-cold-v3-first-campaign-2026-11-07/resume-2026-11-08/email-v28.html) · [Texte](../optimization/buttondown-cold-v3-first-campaign-2026-11-07/resume-2026-11-08/email-v28.txt)

L’email explique comment garder la construction du contenu dans son code et déléguer l’envoi planifié à Buttondown. L’endpoint, le jeton API, le statut scheduled, la date future et la disponibilité sur le plan gratuit ont été confrontés à la documentation effectivement capturée. Le bouton ouvre cette documentation, sans exécuter de requête Buttondown. La destination publique répond et propose bien les exemples Python, Ruby, JavaScript et cURL.

Le défaut qui bloquait la préparation est fermé : la récupération automatique a trouvé les documents d’envoi/planification et intégré les preuves manquantes. La citation de texte visible dans des liens Markdown est désormais reconnue sans autoriser un lien inventé.

### Tally

[Email livré](../optimization/tally-cold-v28-first-campaign-2026-11-08/email-v28.html) · [Texte](../optimization/tally-cold-v28-first-campaign-2026-11-08/email-v28.txt)

L’argument porte sur un formulaire qui adapte les questions au type de demande, avec des exemples de branches facturation, onboarding et technique configurées par l’équipe. Les preuves E8/E3 couvrent la logique conditionnelle et l’offre gratuite sous fair usage. E9 fournit la connexion Zapier, proposée seulement si la destination appropriée existe. Aucun outil installé ni problème vécu n’est attribué au destinataire ; l’ouverture est conditionnelle.

Le créateur de formulaire, la documentation de logique conditionnelle et celle de Zapier ont été consultés indépendamment pour vérifier la destination et les fonctions décrites. Ces consultations n’ont pas fourni de nouvelles données au générateur. Aucun temps gagné, taux de réponse ou intégration native supplémentaire n’a été promis.

## Étapes amont examinées

| Étape Tally | Note /10 | Résultat |
| --- | --- | --- |
| Ingestion | 7,5 | Huit pages automatiques ; homepage partielle explicitement signalée |
| Connaissances | 8 | 22 faits citables ; facturation EUR incertaine classée à confirmer |
| Capacités | 8 | Logique conditionnelle, routage et offre distingués ; limites conservées |
| Concurrence | 7 | Un concurrent lu sur quatre pages ; tarifs contradictoires retirés des synthèses fiables |
| Positionnement | 7,5 | Propositions non appariées à vérifier, sans conclusion d’exclusivité |
| Carte d’audience | 8 | Trois situations distinctes ; preuves et hypothèses séparées |
| Recherche | 8 | Cas vendeur inféré ; observations GitLab/Workfront citées avec limites de date et corroboration |
| Dossier | 8 | GO_NARROW pour l’usage supporté ; aucune entreprise qualifiée inventée |
| Email | 8,5 | Usage concret, conditions utiles, un seul prochain pas |
| Consultation/export | 9 | Copies, téléchargement et rendus vérifiés |

Le passage de page produit à observation sur les acheteurs est corrigé dans le normaliseur commun aux nouvelles recherches et aux données sauvegardées : une liste de fonctions ne prouve pas l’adoption ou le contexte d’un acheteur. Les citations sont conservées comme hypothèses ; les vraies observations de poste et les paroles d’acheteurs restent utilisables. Aucun appel modèle ajouté.

La revue finale a aussi détecté des synthèses Typeform incohérentes, par exemple 28 $/mois en paiement annuel associés à 468 $/an. Un contrôle déterministe, avec tolérance d’arrondi d’affichage et sans mélange de devises ou d’unités, retire ces affirmations et la synthèse tarifaire affectée, puis signale la vérification nécessaire. Trois affirmations contradictoires ont été retirées sur les données réelles sauvegardées ; l’historique brut est intact. Cette dernière correction ne demande pas une nouvelle génération : aucun des deux emails ne cite ces prix concurrents.

## Consultation et modification facultative

Pour les deux nouveaux emails, copie texte, copie HTML et téléchargement texte concordent avec l’asset choisi. Les rendus ont été inspectés à 390 et 1280 pixels sans débordement. Les quelques répétitions et la ponctuation de code littérale de Buttondown relèvent de la finition de marque habituelle.

L’ajustement Tally testé dans la piste précédente demeure sélectionné après redémarrage : original intact, historique conservé, copie HTML de la version acceptée conforme. Le score de lecture est nul sur cette version modifiée ; le verdict de l’original ne valide pas la réécriture. Les contrôles déterministes avaient été repassés sur la proposition.

## Vérifications du dépôt

**2 257 tests backend passent**, Ruff app/tests propre. Frontend : lint et TypeScript propres, **37 tests passent**. Les cinq régressions sur la portée des sources et les six régressions sur la cohérence des totaux annuels complètent la suite précédente. Aucun schéma API public ni migration ajouté dans cette reprise.

[Sortie backend complète](backend-tests-2026-11-08-complete.txt) · [Métriques](first-campaign-2026-11-08-final-metrics.json) · [Revue de cas Tally](../optimization/tally-cold-v28-first-campaign-2026-11-08/commercial-review.json)

La base d’audit et les traces restent disponibles pour inspection. Les montants USD affichés par l’application sont des estimations de consommation ; les appels ont utilisé les abonnements configurés. L’existence de paiements clients n’est pas mesurée par cet audit d’utilité.
