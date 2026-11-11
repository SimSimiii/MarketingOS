# Validation de MarketingOS sur ChartMogul

**Verdict. Je ne paierais pas pour ce premier parcours en autonomie.** La préparation par défaut s’est arrêtée sur deux réponses JSON invalides du cartographe. Après une reprise limitée à cette étape, MarketingOS a livré un email validé sur les faits et exportable. Il reste à relire avant de l’utiliser pour la cible finance choisie.

J’ai fourni uniquement le nom et la [page d’accueil de ChartMogul](https://chartmogul.com/). J’ai utilisé l’API locale des parcours de création, de préparation et de génération en mode Fast. La reprise a changé uniquement le modèle de cartographie, de Sonnet à GPT-5.6 Sol. Le premier résultat est conservé. Les exports proviennent des assets livrés par l’API.

| Étape | Note | Observation |
|---|---:|---|
| Collecte | 7/10 | Sept pages, dont la présentation des métriques, l’analyse IA et un cas client. La page des tarifs ne figure pas parmi les documents initiaux. |
| Knowledge | 7/10 | 22 faits retenus. Les chiffres issus de tableaux de démonstration sont identifiés comme exemples dans les conditions. L’email ne les reprend pas. |
| Concurrence et positionnement | 7/10 | Baremetrics profilé avec 22 affirmations vérifiées. Aucune différence exclusive établie. |
| Carte d’audiences | 5/10 | Deux réponses JSON invalides au premier passage. La reprise a fourni deux hypothèses, dont les responsables financiers et fondateurs qui préparent des rapports pour leur conseil. |
| Recherche et dossier | 6/10 | Quatre sources accessibles, aucun problème ni verbatim d’acheteur vérifié. Le dossier a néanmoins établi un usage cohérent autour des données de facturation et du revenu récurrent. |
| Génération | 7/10 | Un email livré après la reprise. Les deux lecteurs simulés ont donné 6/10 et demandaient comment contrôler ou rapprocher les chiffres avant de les reprendre dans un rapport. La réécriture a été bloquée. Le premier brouillon validé a été conservé. |
| Export | 8/10 | Texte et HTML disponibles. Les rendus à 390 et 1 280 pixels n’ont pas de débordement horizontal. Le bouton libellé « Try Pro free for 14 days » ouvre l’accueil, où il faut cliquer sur « Start for free » pour atteindre l’inscription. |

L’email relie l’import des données de facturation à un modèle de revenu récurrent. Il s’appuie sur l’exemple attribué à OneVision et mentionne Stripe et Paddle comme sources. Il n’explique pas comment le lecteur contrôle les chiffres obtenus, une question qui compte avant de les utiliser devant un conseil. La réécriture a surtout remplacé le témoignage par une liste de clients et a introduit une implication sur l’accès pendant l’essai que le contrôleur a refusée. [Brouillons et décisions](../optimization/chartmogul-cold-v36-validation-2026-11-10/runs/1b109447-df76-4a54-80d3-4a1da780925f/timeline.json)

La proposition d’essai de 14 jours figure dans les sources produit. Le bouton livré est indirect. La page d’accueil affiche une action générique qui mène au formulaire d’essai. La page tarifaire décrit également un parcours d’essai après une prise de contact. J’ai vérifié les pages séparément de la génération. [Page produit](https://chartmogul.com/product-led-growth/) · [Formulaire d’essai](https://app.chartmogul.com/sign_up/1) · [Tarifs](https://chartmogul.com/pricing/)

L’email livré obtient **75/100** sur ma grille (25/25 sur les faits, 14/20 sur l’audience et l’offre, 13/20 sur l’argument, 9/15 sur la continuité, 8/10 sur le rendu et 6/10 sur la concision). La correction de Missive a bien distingué une question d’audience décisive d’un détail facultatif sur son rejeu. Ici, le premier email restait trop peu explicite sur la vérification des chiffres et son bouton ajoutait une étape.

Le premier passage a pris 2 min 46 s et huit appels. La reprise de la carte a utilisé deux appels en 3 min 27 s. La fin de la préparation a pris 3 min 3 s et quatre appels. La génération a pris 5 min 31 s et huit appels. Cela représente **22 appels et 14 min 46 s de traitement cumulé**, pour 4,66 USD estimés par l’application sur abonnement. Le temps humain actif et les conversions ne sont pas mesurés.

[Premier passage](../optimization/chartmogul-cold-v36-validation-2026-11-10/prepare-final.json) · [Reprise de la carte](../optimization/chartmogul-cold-v36-validation-2026-11-10/map-recovery-v36.json) · [Dossier après reprise](../optimization/chartmogul-cold-v36-validation-2026-11-10/steps/20261110T002345303370Z-capture.json) · [Email texte](../optimization/chartmogul-cold-v36-validation-2026-11-10/runs/1b109447-df76-4a54-80d3-4a1da780925f/email-1.txt) · [Email HTML](../optimization/chartmogul-cold-v36-validation-2026-11-10/runs/1b109447-df76-4a54-80d3-4a1da780925f/email-1.html)
