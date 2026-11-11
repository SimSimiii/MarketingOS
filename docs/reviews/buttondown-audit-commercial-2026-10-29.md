# Buttondown — premier audit avec la skill commerciale révisée

29 octobre 2026. Entrée unique : `https://buttondown.com/`. Un email d’acquisition en anglais, première audience exacte, stratégie auto, preset balanced. Aucun envoi effectué.

## Résultat

**Un email utilisable après revue normale et retouches légères, mais une plateforme commercialement non validée sur ce seul essai.** Le résultat applicatif reste `degraded`, `needs_review=true` : les contrôles déterministes passent, le critique conserve des réserves éditoriales. Elles ne sont pas supprimées de l’historique.

Le message explique un mécanisme précis : donner à un éditeur les droits de rédaction sans lui donner automatiquement le droit d’envoyer. La destination permet de vérifier cette séparation. Il ne promet ni gain de temps mesuré, ni suppression de tous les risques, ni prix inventé. La mention Professional est présente dans la documentation actuelle ; le prix exact et le rapport entre plan et add-on restent à clarifier.

Les principales retouches de revue concernent une répétition sur l’envoi et une formulation assez technique. Le texte n’atteint pas encore une voix de marque particulièrement mémorable. Ces limites ne justifient pas de racheter une génération pour améliorer marginalement une note ; aucun asset n’a été réécrit manuellement pour embellir l’audit.

## Skill modifiée et utilisée

La skill `marketingos-brand-audit` conserve le parcours et ses captures. Elle ajoute une référence commerciale, un protocole fixé avant génération, une grille durable et trois verdicts distincts : qualité du livrable, maturité du parcours observé, validation commerciale. Les données absentes restent inconnues. Aucun prix, marge ou intérêt acheteur n’est inventé.

Sa fiche de lancement a été mise à jour et `quick_validate.py` a réussi. L’audit a effectivement exécuté les routes actuelles via le helper ASGI de la skill, sans listener ni lifespan. Il **ne valide pas le parcours frontend**, l’inscription, le paiement ou la capacité d’un utilisateur à réaliser seul ces opérations.

## Notes des étapes

Notes éditoriales après inspection, non prédictives d’une conversion. Les inventaires volumineux sont vérifiés par échantillonnage, pas intégralement.

| Étape | Note /10 | Observation et limite |
|---|---:|---|
| Import | 8 | Douze pages, 11 382 mots, tarifs et documentation découverts automatiquement. Le widget des tarifs contient du bruit numérique. |
| Compilation | 8 | 366 preuves, profil de marque, voix et CTA documentés. Contradictions de packaging conservées ; liste de gaps vide malgré ces ambiguïtés décrites ailleurs. |
| Catalogue | 8 | Capacités atomiques reliées aux preuves et limites ; échantillon inspecté et références du dossier contrôlées. |
| Concurrents | 8 | Six alternatives plausibles : Substack, Ghost, beehiiv, Kit, Mailchimp, Gmail. |
| Positionnement | 7 | Pas de fausse exclusivité tirée d’une absence de capture. Peu de différences directement actionnables ; vocabulaire partagé parfois générique. |
| Audiences | 7 | Six audiences, aucune priorité d’exploration suffisamment étayée. Première audience conservée, besoin compatible mais achat hypothétique. |
| Recherche | 7 | Sept sources récupérées, trois problèmes retenus, huit éléments invérifiables écartés. Constats souvent historiques ou mono-source. |
| Dossier | 8 | Quinze faits classés, deux problèmes ADDRESSED et un PARTIAL, réserves de portée conservées. |
| Génération/livraison | 8 | Un email livré, contrôles propres, deux réécritures, demande de revue éditoriale explicite. |
| Consultation du livrable | 8 | Texte, HTML, captures 1280/390 et vraie destination inspectés. Pas de débordement horizontal observé. |
| Interface utilisateur | Non notée | Aucun parcours frontend observé ; les commandes internes ne mesurent pas l’effort client. |

Grille email /100 : faits **24/25**, audience/offre **17/20**, spécificité/argument **14/20**, objet-corps-CTA **12/15**, rendu **9/10**, absence de promesses abusives/répétitions **8/10**. Total : **84/100**. Un seul run noté ; aucune amélioration avant/après revendiquée. Le score simulé de l’application est distinct : 8/10, non calibré.

## Coût et friction observés

| Phase | Appels terminés | Durée approximative |
|---|---:|---:|
| Compilation | 10 | 3 min 15 s |
| Scan partagé concurrents/positionnement | 7 | 4 min 26 s |
| Carte d’audiences | 2 | 3 min 4 s |
| Recherche audience | 2 | 1 min 18 s |
| Dossier | 1 | 36 s |
| Campagne réutilisant les connaissances | 28 | 3 min 37 s |
| Total | **50** | **Environ 20 min de création de marque à livraison**, dont intervalles de revue et pilotage |

Une première tentative de compilation a échoué sur une session OAuth Claude expirée, sans appel terminé. La reprise utilise `gpt-5.6-sol`, configuré localement au cas et à la campagne. Aucune préférence globale modifiée. La disponibilité des deux abonnements n’est donc pas établie.

Coût estimé de la campagne : **2,916 USD**. Somme des estimations disponibles pour marché, carte, recherche, dossier et campagne : **9,523422 USD**, **hors compilation** dont le snapshot n’expose pas de coût. Ce total partiel n’est ni une facture, ni une marge calculée, ni un prix de revient complet.

Les compteurs d’entrée des recherches incluent des tokens mis en cache ; ne pas les assimiler à autant de contexte neuf facturé au tarif plein. Les coûts monétaires estimés et la consommation de quota d’abonnement sont deux lectures différentes. Le temps actif de travail humain n’a pas été chronométré : il reste inconnu.

## Verdict commercial et prochaine priorité

- **Livrable :** utilisable après revue normale, avec retouches légères ; ne pas annoncer « prêt à envoyer sans vérification ».
- **Parcours API :** complet sur ce cas, avec reprise locale après échec d’authentification. Le chemin frontend reste non évalué.
- **Validation commerciale :** non établie. Aucun acheteur, paiement, envoi ou résultat commercial mesuré.

La prochaine amélioration à examiner est un **parcours court réutilisant les connaissances**, avec recherche approfondie et scan de marché proportionnés au besoin. Il faut comparer sa qualité et ses appels au baseline conservé, sans retirer silencieusement des étapes à ce protocole. La campagne seule représente déjà 28 appels : inspecter d’abord les réécritures, panels et comparaisons réellement utiles avant d’ajouter des rôles ou réduire la qualité des modèles.

Une offre pilote accompagnée peut être examinée à partir de ce résultat ; une offre autonome, rapide et rentable ne doit pas être déclarée validée. Un deuxième cas comparable sera nécessaire avant de généraliser la qualité observée.

## Preuves et livrables

- [Protocole du cas](../optimization/buttondown-root-url-2026-10-29/case.json)
- [Grille commerciale](../optimization/buttondown-root-url-2026-10-29/commercial-review.json)
- [Journal](../optimization/buttondown-root-url-2026-10-29/journal.md)
- [Résultat applicatif et métadonnées](../optimization/buttondown-root-url-2026-10-29/runs/1ac14504-1b1b-4a8b-b23a-286dea9e3796/result.json)
- [Email texte](../optimization/buttondown-root-url-2026-10-29/runs/1ac14504-1b1b-4a8b-b23a-286dea9e3796/email-1.txt)
- [Email HTML](../optimization/buttondown-root-url-2026-10-29/runs/1ac14504-1b1b-4a8b-b23a-286dea9e3796/email-1.html)
- [Capture mobile](../optimization/buttondown-root-url-2026-10-29/runs/1ac14504-1b1b-4a8b-b23a-286dea9e3796/email-1-390.png)
- [Capture ordinateur](../optimization/buttondown-root-url-2026-10-29/runs/1ac14504-1b1b-4a8b-b23a-286dea9e3796/email-1-1280.png)
- [Contrôles de rendu et liens](../optimization/buttondown-root-url-2026-10-29/runs/1ac14504-1b1b-4a8b-b23a-286dea9e3796/render-check.json)

La [documentation officielle de Teams](https://docs.buttondown.com/teams) a été consultée indépendamment pour vérifier la destination ; ses informations n’ont pas été ajoutées manuellement au générateur.
