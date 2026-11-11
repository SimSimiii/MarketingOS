# MarketingOS en situation d’usage — Simple Analytics

**Verdict personnel — je ne paierais pas aujourd’hui pour le parcours complet testé.** J’ai obtenu un email que je garderais après une courte retouche. En tant que responsable acquisition, j’attendais aussi du parcours qu’il m’aide à choisir l’audience à traiter en premier et qu’il réunisse les preuves décisives avant que je doive les chercher moi-même. Sur ce cas, la carte ne recommandait aucune audience en priorité et le dossier laissait ouvertes des questions auxquelles le site de la marque apportait déjà des réponses.

## Conditions

Nouvelle marque dans une base locale isolée. Une seule URL saisie dans l’interface, la [page d’accueil de Simple Analytics](https://www.simpleanalytics.com/). Brief d’un email d’acquisition en anglais, premier segment affiché, génération automatique, preset Balanced. Aucun fait, document, lien d’action ou consigne de rédaction ajouté à la génération initiale. Génération depuis le bouton de l’interface avec la recommandation municipale `GO_NARROW`. Appels réels via les abonnements configurés. Branche `master`, état de travail existant sur `6b6e87f`. Aucun email envoyé.

## Parcours et mesures

| Étape | Durée du traitement | Appels | Note | Ce que l’étape a apporté |
| --- | ---: | ---: | ---: | --- |
| Import | ~10 s | 0 | 7/10 | Onze pages et environ 7 600 mots, dont tarifs, guides et cas client. L’interface a demandé de ressaisir l’URL. Elle a omis les pages sur les données collectées et le DPA. |
| Compilation | 9 min 58 s | 8 | 8/10 | 162 faits et 14 citations candidates écartées. L’essai autonome et le comparatif accompagné sont distingués. Un écart de couverture reste signalé. |
| Catalogue | Dérivé avec la carte | 0 supplémentaire | 7/10 | 82 capacités dérivées et 162 affirmations indexées. Utile pour relier l’offre au besoin, avec les limites des pages capturées. |
| Concurrents | 6 min 13 s avec le positionnement | 7 partagés | 8/10 | Six concurrents crédibles, dont GA4, Matomo, Plausible et Fathom. |
| Positionnement | Même opération | Inclus | 5/10 | 27 pistes à vérifier et zéro différence documentée. Bonne prudence sur l’exclusivité, faible aide au choix d’un angle. |
| Carte d’audiences | 13 min 11 s | 2 | 5/10 | Sept audiences concrètes, aucune à explorer en priorité. J’ai pris la première comme prévu. |
| Recherche de l’audience | 5 min 9 s | 2 | 6/10 | Six pages lisibles et quatre indisponibles. Le sujet des services tiers sur les sites municipaux est réel. Les sources mêlent une étude de 2026, des publications plus anciennes et des dates inconnues. L’étude ne renseigne pas l’installation actuelle d’un destinataire. |
| Dossier | 2 min 6 s | 1 | 7/10 | Un besoin relié aux capacités. La recommandation resserre la cible aux municipalités. Le dossier signale le manque d’information sur le DPA dans le corpus, alors qu’une page officielle décrit la possibilité d’examiner et de signer un accord fourni par le client sous conditions. |
| Génération avec la base réutilisée | 4 min 23 s | 26 | 7/10 | Un email sur un demandé. Contrôles bloquants réussis. La critique reste ouverte et l’interface affiche « Drafts Need Review ». |
| Ajustement et consultation | 19 s pour la proposition | 1 tentative | 8/10 | Comparaison, acceptation, original conservé. Copie texte et HTML et téléchargement de la version sélectionnée vérifiés. Trois alertes consultatives restent trompeuses. |

Environ **46 min** de la création à la première livraison et **48 min** jusqu’à l’acceptation et à l’export. Ce temps écoulé inclut l’audit, les transitions et l’attente des tâches. Les cinq traitements de préparation cumulent environ 36 min 37 s. Ils demandent plusieurs déclenchements et actualisations manuelles. Le temps actif de revue humaine n’a pas été chronométré séparément.

20 appels de préparation, 26 de génération et une tentative d’ajustement. La compilation a utilisé Sonnet et Opus. Les jobs de marché ont utilisé Sonnet ou Opus selon le rôle. La campagne Balanced a utilisé GPT-5.6 Sol. Le produit estime le coût de la campagne à 2,62 USD et celui des quatre jobs de marché à 7,06 USD. Le total estimé est incomplet, faute d’estimation capturée pour la compilation et l’ajustement. Ces valeurs sont des estimations de l’application, distinctes de la facture d’abonnement.

## Email et décision de revue

**Objet livré** — « Analytics without cookies or fingerprinting data ». MarketingOS a trouvé un angle crédible pour un premier contact. Une équipe web ou privacy peut examiner le code du script avant d’envisager une évaluation. Le bouton arrive sur une documentation qui explique la configuration et renvoie vers GitHub. Ce contrôle a été effectué indépendamment de la génération. Le guide est pertinent pour inspecter le script. Les traitements côté serveur sont détaillés sur une page distincte, absente de l’import. [Guide du script](https://docs.simpleanalytics.com/script) · [Données collectées](https://www.simpleanalytics.com/data-collection)

Le corps original faisait 134 mots. Il répétait l’intérêt d’inspecter le script et tirait une conclusion sur le consentement que je ne reprendrais pas telle quelle dans ce message. J’ai demandé, via **Adjust**, une version plus courte et directe qui ouvre sur ce que l’équipe peut mesurer, conserve le lien et retire la conclusion juridique. La version acceptée fait 98 mots, ouvre sur la mesure des pages vues et garde le code accessible. Elle est utilisable comme premier contact technique après une revue habituelle. La rédaction reste sobre et la dernière phrase répète un peu le rôle de la documentation.

La proposition a passé ses propres contrôles bloquants et ne porte pas le score de lecture de l’original dans ses métadonnées. Trois alertes consultatives demandent une revue inutile. L’une traite l’action d’inspection comme indisponible malgré la destination vérifiée. Les deux autres signalent l’absence des preuves E80 et E48 alors que le texte exprime bien les caractéristiques de confidentialité et cite les scripts open source sur GitHub. L’écran conserve par ailleurs le 7/10 de la campagne initiale. Ce score de lecteurs simulés ne mesure que le brouillon d’origine.

| Grille éditoriale | Original | Version acceptée |
| --- | ---: | ---: |
| Faits /25 | 18 | 22 |
| Audience et offre /20 | 15 | 16 |
| Spécificité et argument /20 | 12 | 14 |
| Cohérence sujet, corps et action /15 | 14 | 14 |
| Rendu /10 | 9 | 9 |
| Absence d’abus et de répétition /10 | 7 | 9 |
| **Total /100** | **75** | **84** |

Le rendu de chaque version a été vérifié à 390 et 1 280 px dans Chromium. L’email reprend le rose de la marque et conserve un bouton lisible. Les boutons de copie et de téléchargement de l’application ont fourni le contenu attendu. Le rendu dans les clients email et les résultats d’envoi restent hors périmètre.

## Décision en tant qu’acheteur

La partie pour laquelle je vois de la valeur est le passage du corpus à un angle concret, puis à un email révisable, exportable et accompagné d’une vraie destination. Le frein à l’achat est le travail qui reste avant ce résultat. Après avoir attendu et déclenché chaque étape, je dois encore décider seul où commencer et retrouver des pages qui répondent aux objections de l’audience retenue. Le site de la marque publie les détails de collecte et sa politique de signature d’un DPA fourni par le client. Leur absence a eu un effet visible sur ce dossier et sur l’objection des lecteurs simulés. [Données collectées](https://www.simpleanalytics.com/data-collection) · [DPA de Simple Analytics](https://www.simpleanalytics.com/data-processing-agreement)

Ce jugement porte sur le parcours depuis une marque vierge et un email, avec les réglages observés. Aucune nouvelle campagne n’a été lancée pour mesurer l’usage récurrent. Aucune modification de code ni suite de tests unitaires dans cet essai.

## Pièces du test

- [Email original](../optimization/simpleanalytics-root-url-2026-11-05/runs/db87f85c-44f6-4141-9c93-68ee25bd0b9f/email-1.txt) et [version acceptée](../optimization/simpleanalytics-root-url-2026-11-05/runs/db87f85c-44f6-4141-9c93-68ee25bd0b9f/email-selected.txt).
- [Rendu mobile de la version acceptée](../optimization/simpleanalytics-root-url-2026-11-05/runs/db87f85c-44f6-4141-9c93-68ee25bd0b9f/email-selected-390.png) et [export de l’application](../optimization/simpleanalytics-root-url-2026-11-05/runs/db87f85c-44f6-4141-9c93-68ee25bd0b9f/marketingos-selected.txt).
- [Comparaison dans l’interface](../optimization/simpleanalytics-root-url-2026-11-05/ui-adjustment-proposal.png) et [grille commerciale](../optimization/simpleanalytics-root-url-2026-11-05/commercial-review.json).
