# Validation de MarketingOS sur Transistor

**Verdict. Je ne paierais pas pour le parcours tel qu’il a fonctionné sur Transistor.** MarketingOS a trouvé un angle pertinent pour les agences, puis a livré zéro email. Le résultat du rejeu Screen Studio ne se confirme pas sur ce premier essai.

Le test utilise le parcours « Prepare a first campaign » de MarketingOS. La marque et sa [page d’accueil](https://transistor.fm/) sont les deux seules informations saisies. Le premier essai conserve l’objectif prérempli, l’audience choisie automatiquement et le mode Fast. Les pages liées proviennent de la collecte automatique. Aucun fait, CTA ou réglage de modèle n’a été fourni manuellement.

| Étape | Note | Observation |
|---|---|---|
| Collecte | 8/10 | Huit pages dont l’accueil, les prix, les fonctions vidéo, des cas clients et la documentation sur les abonnés privés. Certaines pages liées restent hors couverture. |
| Knowledge | 8/10 | 34 faits citables. L’essai de 14 jours, l’absence de prix par émission supplémentaire et les différences entre les forfaits sont visibles. Douze entrées très techniques portent sur l’API. |
| Capacités | 7/10 | 19 capacités dérivées. Le catalogue aide à séparer l’hébergement de plusieurs émissions des conditions de publication vidéo et des accès par client. |
| Concurrence | 7/10 | Trois alternatives identifiées. Buzzsprout est le seul concurrent profilé dans le parcours court, avec 20 affirmations vérifiées. |
| Positionnement | 7/10 | Aucune différence exclusive établie. Les 27 propositions sans correspondance dans la capture restent à vérifier. |
| Carte d’audiences | 7/10 | Deux hypothèses utiles. Les réseaux et agences gérant plusieurs émissions arrivent en tête. La carte s’appuie surtout sur des sources de la marque. |
| Recherche d’audience | 5/10 | Deux sources lisibles sur quatre. Une page de la marque décrit un usage agence et une revue tierce le compare aux tarifs par émission. Aucun problème ni verbatim de première main n’a passé la vérification. |
| Dossier de pertinence | 8/10 | L’autorisation de générer est limitée à l’hébergement de plusieurs émissions sous un même compte, avec une action d’essai documentée. La séparation des accès entre clients reste à confirmer dans le périmètre du dossier. |
| Génération et livraison | 3/10 | Deux brouillons, tous deux bloqués. La réécriture préserve le bénéfice multiémission. Aucun email final. |
| Consultation et export | Échec de livraison | L’interface affiche « Delivered 0 of 1 email ». Le lien choisi ouvre une page publique d’inscription. Le rendu et les exports restent non évaluables. |

[Capture des analyses et du dossier](../optimization/transistor-cold-v34-validation-2026-11-09/steps/20261109T113905090014Z-capture.json) · [Journal de préparation](../optimization/transistor-cold-v34-validation-2026-11-09/prepare-final.json)

## Ce qui a bloqué

Le brief proposait d’ouvrir un essai de 14 jours et d’y créer une nouvelle émission pour évaluer la gestion de plusieurs podcasts. E23 établit l’essai et E24 le fait qu’ajouter une émission n’entraîne pas de frais par podcast. Les deux citations ne prouvent pas ensemble la disponibilité du parcours multiémission pendant l’essai. La page d’inscription confirme l’essai et présente les offres, tandis que les conditions officielles prévoient que certaines fonctions peuvent être indisponibles pendant l’essai. [Inscription officielle](https://dashboard.transistor.fm/signup) · [Conditions officielles](https://transistor.fm/terms/)

Le premier brouillon annonce le prix Starter et le plafond de téléchargements au niveau du compte. Les documents déjà importés contiennent le montant de 19 USD par mois, le rythme de facturation mensuel et les 20 000 téléchargements audio mensuels. La citation E13 fournie au contrôleur se limite au titre de l’offre et à la publication audio. Les conditions officielles définissent le plafond au niveau du compte. Cette dernière vérification a été faite séparément et n’a pas alimenté le run. [Tarifs officiels](https://transistor.fm/pricing/) · [Documents capturés](../optimization/transistor-cold-v34-validation-2026-11-09/documents-initial.json)

La réécriture retire le tarif et le plafond et garde l’argument multiémission, que le contrôleur confirme. Le contrôleur traite encore l’inscription à l’essai comme une promesse d’accès au scénario multiémission. Il considère également le tarif, le plafond et la création d’une émission comme des exigences du brief. Les deux lecteurs simulés ont compris l’offre et se disaient prêts à agir, avec des notes de 8/10 et 7/10. Tous deux voulaient comprendre les accès par client. Aucun email n’est noté sur 100 puisque les deux brouillons sont bloqués. [Brouillons et décisions](../optimization/transistor-cold-v34-validation-2026-11-09/runs/3fd73d86-9641-4ac2-891f-f764bce5a6f9/timeline.json)

Le point à corriger est la transmission des preuves entre le brief, le rédacteur et le contrôleur. Le plan doit distinguer les conditions obligatoires des détails dont la formulation s’applique uniquement s’ils sont mentionnés. Il doit joindre les citations exactes pour les conditions qu’il impose et séparer l’inscription de tout usage précis qui n’a pas été établi pour l’essai. Le test conserve le premier résultat avec le code v34.

## Effort et durée

La préparation a pris 6 min 10 s et 12 appels modèles. La génération a pris 6 min 9 s et 8 appels, avec réutilisation de la Knowledge. Total de traitement de 12 min 19 s et de 3,83 USD estimés par l’application sur les abonnements configurés. Le temps humain actif n’a pas été mesuré. Le parcours observé couvre la création, la préparation, la génération et la consultation de l’échec dans l’interface. [Résultat enregistré](../optimization/transistor-cold-v34-validation-2026-11-09/runs/3fd73d86-9641-4ac2-891f-f764bce5a6f9/result.json) · [Grille commerciale](../optimization/transistor-cold-v34-validation-2026-11-09/commercial-review.json)
