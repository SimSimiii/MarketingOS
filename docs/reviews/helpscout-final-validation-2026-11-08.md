# Dernière validation sans correction — Help Scout, 8 novembre 2026

Suivi : les corrections et le retest sur une nouvelle marque sont documentés dans [la validation Crisp](crisp-fixes-validation-2026-11-08.md). Le présent rapport conserve le constat avant correction.

**Verdict : je ne valide pas la vente du parcours minimal actuel « une homepage → un email exploitable ». Sur ce nouveau cas, je ne paierais pas pour le résultat obtenu : aucun email n’a été livré.** Les résultats utilisables Buttondown et Tally restent des réussites de cas. Mon verdict global précédent était trop large : ils ne suffisaient pas à établir la fiabilité du premier parcours sur une nouvelle marque.

Audit réalisé avec les skills marketingos-brand-audit et campaign-optimization. Aucune correction applicative, modification de prompt ou injection de sources pendant cet essai. Aucun quota épuisé ni défaut d’authentification n’explique l’arrêt.

## Protocole réellement suivi

Nouvelle marque **Help Scout**, entrée unique [homepage officielle](https://www.helpscout.com/), créée dans l’interface réelle. Nom et URL saisis ; objectif prérempli conservé : « Introduce our product to a new buyer with one clear next step. » Puis bouton **Prepare campaign**. L’opérateur n’a imposé aucune condition de migration, d’effectif constant ou de données Shopify. Stratégie et modèles par défaut ; aucune génération forcée.

Le code existant est resté sur master ; les données sont dans une copie SQLite isolée. Les sources, Knowledge, marché, audiences et écran final ont été consultés dans la vraie interface. Les APIs conservent les preuves. Un incident du harnais navigateur, qui attendait une URL sans slash final, a eu lieu après la création ; la marque déjà créée a été reprise sans doublon. Il n’explique pas l’échec applicatif ultérieur. Les durées ci-dessous excluent cette instrumentation.

## Résultat observable

| Mesure | Résultat |
| --- | --- |
| Préparation automatique | **10 min 08 s**, 608,401 s |
| Appels modèles achevés | **17** : 13 Sonnet, 4 Opus |
| Sources | 7 documents initiaux ; 12 documents finaux, 10 URL distinctes |
| Connaissances | 33 faits citables ; 64 cartes faits/contexte dans l’interface |
| Audiences | 3 hypothèses ; les 2 premières examinées automatiquement |
| Concurrence | 4 alternatives découvertes ; 0 profil vérifié |
| Campagnes créées pour cette marque | **0** |
| Emails livrés | **0** |
| État technique du job | done, erreur API vide |
| Quota/login | Aucun blocage |
| Estimation affichée | 2,973364 USD ; estimation de consommation, pas une facture API |

Les appels utilisent l’abonnement Claude Pro configuré. Le temps actif d’un utilisateur humain n’est pas mesuré par cette automatisation. Les 17 appels incluent compilation, découverte, validation, recherche, récupérations officielles et réévaluations. Aucune génération supplémentaire n’a été achetée pour fabriquer une réussite.

Preuves : [job complet](../optimization/helpscout-final-validation-2026-11-08/prepare-final.json), [métriques](../optimization/helpscout-final-validation-2026-11-08/final-metrics.json), [liste de campagnes vide](../optimization/helpscout-final-validation-2026-11-08/campaigns-final.json), [écran final réel](../optimization/helpscout-final-validation-2026-11-08/ui-final-no-email.png).

## Déroulement et point d’arrêt

1. L’import et la compilation trouvent une matière exploitable : boîte partagée, réponses IA fondées sur les connaissances, transfert à un humain, cas clients attribués et limites explicites. La lecture initiale resserrée laisse 19 307 caractères hors budget et le signale.
2. Le scan découvre Zendesk, Intercom, Front et une alternative Gmail/Hiver. Seul Zendesk est tenté pour le profilage borné ; son site reste illisible. L’application annonce correctement l’absence de comparaison vérifiée. Le positionnement concurrentiel n’est donc pas validé.
3. Première cible générée par le système : équipe e-commerce Shopify voulant absorber les questions de commande et croître sans embauche. La recherche récupère quatre fils Shopify Community. Une récupération officielle confirme les commandes dans la barre latérale et la facturation, **sans confirmer que l’IA peut lire ces données pour répondre aux questions de suivi**. Le refus de promettre cela est justifié.
4. Le parcours examine automatiquement une deuxième cible : responsable d’une petite équipe support SaaS. Cette cible comporte la condition « sans changement perturbant de l’outil de support », introduite par le système. Une nouvelle récupération trouve la migration Zendesk et un résultat client eCatholic. Les limites restent explicites : macros à recréer, durée non annoncée, taille exacte de l’équipe non établie.
5. Le dernier dossier conserve un problème **ADDRESSED** et plusieurs preuves **LEAD**, mais toute la cible reste **DISCOVERY_ONLY** à cause de cette condition de non-perturbation. La recommandation demande des preuves avant de traiter le cas comme une **outreach list**, alors que la demande porte sur un email.
6. L’interface termine sur **Check before drafting → Review audiences**. Aucun brief de campagne, email, aperçu, ajustement ou export n’est disponible pour cette marque. Ces étapes sont **non validées** dans cet audit. Il n’existe pas d’email auquel attribuer une note éditoriale.

[Dossier final et ses preuves](../optimization/helpscout-final-validation-2026-11-08/relevance-final.json) · [Audiences et historique de pertinence](../optimization/helpscout-final-validation-2026-11-08/audiences-final.json).

## Notes des étapes

Appréciations éditoriales de l’utilité des sorties observées ; aucune note ne prédit une conversion.

| Étape | Note /10 | Observation principale |
| --- | --- | --- |
| Import | 7,5 | Collecte automatique et récupération ciblée ; corpus partiel signalé |
| Connaissances | 7 | Sources et portée explicites ; prix des paliers sans mode de facturation explicite dans les cartes |
| Capacités | 6 | Trois capacités dérivées vérifiées ; catalogue encore étroit |
| Concurrents | 2 | Alternatives trouvées, aucun profil lu et vérifié |
| Positionnement | 2 | Absence de comparaison reconnue, aucune différence établie |
| Audiences | 5 | Trois situations distinctes ; les deux premières imposent des conditions ambitieuses générées par le système |
| Recherche | 7 | Citations vérifiées ; corroboration limitée ; pour SaaS, une seule source de revue sans date connue |
| Dossier | 5 | Frontières factuelles préservées ; aucun livrable borné proposé malgré des mécanismes supportés |
| Génération/livraison | Non noté — absent | Aucun email |
| Consultation | 5 | Faits et progression lisibles ; issue ouverte de recherche sans livrable |

## Points forts confirmés

- **Contexte construit depuis une URL.** Les pages et citations sont récupérées sans collecte manuelle ; les faits sont réutilisables et séparés du contexte.
- **Traçabilité des affirmations.** Les témoignages conservent client, date et portée. Une citation trouvée ne devient pas une preuve de résultat généralisable.
- **Vérification ciblée.** Les questions concrètes déclenchent une récupération officielle bornée, sauvegardée, avec conservation des inconnues.
- **Limites visibles.** Corpus partiel, concurrent illisible, accès des agents aux commandes distinct de l’accès de l’IA et limites de migration restent affichés.
- **Persistance.** Sources, connaissances et dossiers sont conservés ; l’arrêt ne détruit pas le travail réalisé.

Ces qualités constituent une base réelle. Elles ne remplacent pas le livrable attendu par le client.

## Défauts à corriger avant mon achat

**1. Une hypothèse de ciblage devient une condition obligatoire.** La préférence « pas de changement perturbant » n’était pas dans la demande utilisateur. Le système l’ajoute à la cible, puis bloque le parcours en essayant de la prouver. Le dossier connaît pourtant des mécanismes utiles et plusieurs faits exploitables. Mon diagnostic est une défaillance du choix de promesse et du repli commercial.

Correction à viser : distinguer les exigences explicites de l’utilisateur, qui restent impératives, des hypothèses commerciales générées par le système. Pour ces dernières, proposer un angle borné aux capacités démontrées lorsque cet angle reste utile au destinataire. Conserver les contrôles factuels : ne jamais promettre l’accès IA aux commandes, une migration indolore ou un effectif constant sans preuve. Ne pas simplement renommer le même usage non supporté pour contourner son refus.

**2. Une impasse après dix minutes.** Deux récupérations complémentaires et quatre passages de dossier aboutissent à une consigne ouverte de recherche. L’utilisateur qui veut un email ne reçoit ni email ni décision simple. Le statut technique done ne décrit pas une livraison réussie. Le parcours doit rendre un choix commercial compréhensible à partir du travail sauvegardé, sans reporter une enquête générale sur le client.

**3. La recherche concurrentielle ne rend rien quand un seul hôte échoue.** Quatre alternatives sont connues, aucune n’est vérifiée. Prévoir un repli borné vers une autre alternative, en indiquant la couverture réelle. Ce manque affecte la valeur du module marché ; il n’interdit pas à lui seul un email fondé sur les preuves de marque.

Ces points sont des conditions d’acceptation du parcours, pas des retouches cosmétiques à reporter automatiquement après les premiers tests utilisateurs. Aucune correction n’a été faite dans ce test, conformément à la demande de juger le produit actuel avant modification.

## Optimisations pouvant attendre

Après résolution du blocage : compacter les vues détaillées, affiner voix de marque et concision, améliorer la présentation des étapes, puis ajuster le budget des campagnes réutilisant les sources. Les retours de testeurs seront pertinents pour les prioriser quand un nouveau cas pourra réellement livrer son premier email. Aucun prix de vente ni paiement réel n’est mesuré ici.

## Vérifications et décision

Cet audit porte sur les modèles et l’interface réels ; aucun test unitaire ni banc payant supplémentaire n’a été lancé, puisqu’aucun code applicatif n’a changé. Les vérifications précédentes — 2 257 backend, 37 frontend, lint et TypeScript — restent une preuve de code distincte. Elles ne transforment pas cet échec de parcours en réussite produit. Aucun déploiement, envoi, achat de crédits ou changement de branche.

**Décision : je ne recommande pas encore de vendre la promesse du parcours minimal ni de demander aux premiers testeurs de résoudre cette impasse à ta place. Le prochain travail utile est la correction ciblée du choix de promesse et du repli, suivie d’un retest conservant ce cas d’échec.**
