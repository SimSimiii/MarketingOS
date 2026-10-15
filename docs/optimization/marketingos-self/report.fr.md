# MarketingOS testé sur lui-même

**Verdict du 15 octobre : un test privé accompagné est justifié ; une disponibilité commerciale sans relecture ne l'est pas.** Deux emails anglais sont livrés avec le modèle GPT par défaut. Relecture interne : 84/100, avec une petite retouche nécessaire pour distinguer compte vide et campagne déjà générée. Les [versions relues](gpt-enriched/email-1.reviewed.en.txt) et [second email relu](gpt-enriched/email-2.reviewed.en.txt) sont séparées des originaux ; les avertissements automatiques restent sauvegardés. Le compte de Mehdi dispose de 50 exécutions et d'un guide anglais.

Test local commencé le 14 octobre 2026, repris le 15 octobre. Le corpus décrit le produit actuel : génération d'emails fondée sur les sources, recherche de marché et relecture indépendante. Les anciennes promesses d'orqAgent n'ont pas été réutilisées. La cible de la campagne est un testeur SaaS invité, disposant déjà d'un compte ; aucune inscription publique, offre gratuite, tarification ou preuve client n'est inventée.

## Concurrents

Le scan a découvert Jasper, Copy.ai, Hoppy Copy, HubSpot Marketing Hub, Mailchimp et ChatGPT. Cinq profils ont été documentés, avec 118 affirmations vérifiées ; ChatGPT n'a pas été lu et a été exclu des comparaisons calculées. Durée : environ 3 min 06. Estimation interne des appels locaux : 0,936 USD, sans facture API.

La collecte fournit des pistes utiles, mais la carte de positionnement ne prouve pas une différence exclusive. Elle propose le contrôle/export comme territoire ouvert, alors que les sources HubSpot décrivent la copie du texte et que [Hoppy Copy propose l'export vers son propre ESP](https://www.hoppycopy.co/). L'affirmation HubSpot a été classée sous l'effort, et l'export Hoppy a été omis du profil. Absence dans la carte ne signifie donc pas absence chez les concurrents. Ne pas utiliser « seul outil permettant l'export » dans le marketing.

Autre limite : des réserves du corpus — génération de plusieurs minutes, qualité non établie dans tous les secteurs, absence de garantie de conversion — sont rangées dans des familles de bénéfices. Ces catégories nécessitent une revue humaine. La promesse à explorer reste une rédaction traçable et une relecture indépendante ; son exclusivité et sa valeur commerciale restent à démontrer.

## Audience

La carte propose six segments : dirigeants de services B2B, fondateurs SaaS, responsables marketing e-commerce, copywriters indépendants, petites boutiques Shopify et testeurs invités. Aucun n'est classé comme immédiatement prêt à explorer ; un est à revoir et cinq restent des hypothèses. La compatibilité est inconnue pour les six.

Les citations, alternatives et contre-indications aident à construire des entretiens, mais ne valident ni la demande ni les biographies proposées. Par exemple, le fondateur SaaS travaillant tard et écrivant mal ses emails est une hypothèse de persona, pas un fait utilisable dans un email adressé à une personne. Certains commentaires de justification sont aussi plus affirmatifs que les champs normalisés. Le brief du test interdit ces suppositions.

Durée : environ 11 min 51. Estimation interne locale : 2,979 USD. Ce délai mérite d'être observé avec Mehdi avant de décider si une optimisation de la recherche est prioritaire. Les deux opérations de marché totalisent 3,915 USD selon la table interne, qui n'est pas une facture API.

## Emails en anglais

Brief : deux emails pour des testeurs invités, première action simple — se connecter, ajouter une offre réelle et demander un email — puis expliquer la revue des faits et les retours du lecteur. CTA : https://app.orqagent.com/login/. Mode Balanced ; connaissance compilée réutilisée, 23 éléments de preuve. Aucun contournement de la vérification de préparation.

La première tentative, `8bf6417a-dc63-4be7-af8d-7fa6b10d3bff`, a échoué après la stratégie : quota du CLI Codex épuisé, aucun email livré. Elle n'est pas notée. Estimation interne : 0,3924 USD. Le quota disponible a été vérifié le 15 octobre, puis le même brief a été relancé sous `9dadde91-9495-467e-92fa-59a86a4ba030`.

Cette reprise a aussi échoué : 12 min 37, 16 étapes de rôle, zéro livrable, 8,5553 USD d'estimation interne. Le critique exigeait une durée de préparation mesurée pour une invitation ne promettant aucun délai, et traitait le lien de connexion comme s'il devait afficher un résultat déjà prêt. La recherche complémentaire a épuisé le budget de jetons. Cette tentative n'est pas notée non plus : les préférences des lecteurs pour des versions intermédiaires ne constituent pas une livraison.

Correction en cours de validation : distinguer un souhait de réassurance d'une preuve requise par la promesse réelle, et demander une formulation conditionnelle si l'état du compte n'est pas établi. Les fonctionnalités et les délais effectivement promis doivent toujours être documentés. Le README indique maintenant explicitement que la relecture indépendante est faite par un modèle IA ; le corpus original de ce cas est conservé pour comparer la génération après correction.

Une tentative intermédiaire a été annulée après stratégie (0,4711 USD d'estimation interne), car le serveur gardait l'ancien prompt en mémoire. Après redémarrage, `a3b246e4-4210-4cef-acdb-894712fdad58` a livré un email sur deux en 6 min 55, avec une estimation de 3,9772 USD. La fausse escalade de recherche a disparu, mais le second email répétait six mots de la présentation du produit et a été bloqué. Le fichier `partial-email-1.en.txt` conserve le premier livrable. Aucun score de campagne complète n'est attribué ; sa revue de séquence reste en attente.

La règle de rédaction a ensuite été clarifiée pour varier aussi la présentation du produit dans chaque email. Le contrôle de répétition reste actif ; aucun appel de modèle n'est ajouté par la correction. La suite backend après cette modification : 1 488 tests réussis, deux avertissements existants.

La lecture du résultat dans l'interface a révélé une durée à zéro et un rapport final absent après actualisation. Le composant conserve maintenant la réponse finale pour afficher ces deux données. Vérification navigateur : durée de 6 min 55, mention explicite d'un email livré sur deux et problème de contrat visible ; lint, typecheck et 17 tests frontend réussis. Commit `c0355a7`. L'aperçu HTML du premier email est lisible sur écran étroit avec le bon lien ; la carte de titre de la refonte locale reste trop serrée sur ce format. Ce constat local n'établit pas le rendu dans les logiciels de messagerie.

Le run `247f2de7-bc42-445c-80b2-a30300f9003a` n'a plus rencontré le blocage de répétition. Il a toutefois révélé une vraie lacune de source : le corpus original ne documentait pas l'accès utilisateur aux faits compilés et aux retours du lecteur. Une annulation coopérative a été demandée pendant la recherche publique ; l'appel en cours s'est terminé avant l'arrêt. Un email a été préservé, mais la séquence reste incomplète. Estimation interne de cette tentative : 14,9206 USD. Elle n'est pas notée comme campagne complète.

Ces écrans ont ensuite été ouverts et vérifiés dans le navigateur local. `verified-review-source.en.md` précise les deux pages distinctes, l'identité IA du lecteur et le parcours d'un compte vide. La compilation v2 contient 41 éléments de preuve. Un cas séparé dans `claude-enriched/` conserve le même brief et Balanced, mais utilise Claude Opus sur abonnement : le forfait Codex atteignait 92 % de sa fenêtre courte. Ce résultat ne sera pas présenté comme une comparaison à modèle et corpus constants, ni comme une validation du modèle API de production.

Les builds console `fef45ad0-403d-4be4-843a-e800e42adc12` et API `99c28668-a18b-4521-a1bf-021a83ba07c2` ont réussi. Les corrections d'affichage et de prompts (`c0355a7`, `97db8de`) sont en production. Les contrôles HTTP après déploiement donnent 200 pour l'application et la santé API, 401 pour les campagnes anonymes.

### Résultat Claude / corpus complété

Le run `920b9fc9-3b24-4dfa-8add-873ed013b29b` a livré les deux emails en 17 min 35, avec 20 étapes de rôle, 431 566 jetons d'entrée et 112 803 de sortie, estimation interne de 7,3087 USD. Aucun problème de contrat n'est signalé. Les fichiers anglais sont dans `claude-enriched/email-1.en.txt` et `email-2.en.txt`, avec leurs HTML.

**Relecture interne : 72/100, résultat insuffisant tel quel.** Grille : faits 19/25, audience/offre 16/20, argument 14/20, continuité 11/15, rédaction/rendu 7/10, promesses/répétitions 5/10. Forces : produit compréhensible, lecteur explicitement simulé par IA, bon lien, fonctions de revue documentées. Défauts : le premier email affirme que chaque phrase est traçable à une source et que cette revue n'a pas d'équivalent dans un simple prompt. Les sources décrivent un mécanisme, sans prouver ces garanties ou cette exclusivité. Son objet introduit aussi une comparaison de cinq emails en un après-midi, étrangère au petit test demandé. Les évaluations automatiques de 7/10 ne remplacent pas cette vérification.

Ces défauts ont conduit à préciser le cadrage et le critique : préserver la fonction documentée sans promettre une vérification universelle ou une supériorité non établie. Le modèle GPT par défaut est de nouveau disponible ; le cas `gpt-enriched/` utilise le même brief et le corpus v2, avec une notation séparée du cas Claude. Les versions livrées précédemment restent intactes.

### Résultat GPT par défaut / corpus complété

Le run `62cbd16d-85ab-44a7-93c7-d4a6cb56fd6f` a livré les deux emails en **8 min 45**, avec 18 étapes de rôle et **45 appels de modèle terminés**. Pas de problème de quantité ; la relecture automatique conserve toutefois une réserve d'audience sur le second message. Estimation interne : 4,7266 USD. Avec les tarifs API consultés, le simple recalcul des 917 842 jetons d'entrée (648 704 en cache) et 68 484 de sortie donne **2,71 USD avec ce cache, 5,04 USD sans sa remise**. Ce sont des équivalents de jetons CLI, pas des factures API ni des prédictions garanties du même parcours sur Lambda. Le détail est dans `gpt-enriched/api-token-replay.json`.

| Critère de relecture | Note | Constat sur les originaux générés |
|---|---:|---|
| Exactitude et sources | 24/25 | Mécanisme décrit sans garantie de correction universelle ; fonctions de revue documentées |
| Audience et offre | 17/20 | Invitation SaaS compréhensible ; second email suppose trop facilement un résultat disponible |
| Argument et spécificité | 15/20 | Une offre et un email pour juger la copie ; rédaction encore un peu abstraite |
| Objet, corps et CTA | 12/15 | Objets cohérents et lien correct ; transition créer puis revoir à conditionner |
| Rédaction et rendu | 9/10 | Anglais lisible, texte et HTML disponibles |
| Promesses et répétitions | 7/10 | Exclusivité et comparaison d'après-midi supprimées ; réserve sur l'état du compte conservée |
| **Total interne** | **84/100** | Jugement de relecture, distinct des 8/10 simulés |

Les originaux sont `gpt-enriched/email-{1,2}.en.{txt,html}`. Le second email implique encore qu'une campagne est prête. Une retouche éditoriale courte précise : si un run est terminé, inspecter son rapport et Knowledge ; sinon, commencer par une offre et demander un email. Le CTA devient « Sign in to your workspace ». Cette retouche ne résulte pas d'une nouvelle génération : elle est identifiée dans `editorial-review.json`, avec des fichiers `email-{1,2}.reviewed.en.{txt,html}` séparés. Les deux versions relues passent les contrôles déterministes sans blocage, avec le bon lien en texte et HTML. Le statut automatique d'origine reste `degraded` et son objection n'a pas été effacée.

Ce cas est utilisable après relecture normale de marque et cette retouche mineure. Il ne démontre pas que les séquences générées n'exigent plus aucune correction. Le score Claude de 72 et le score GPT de 84 appartiennent à des modèles différents : ils ne mesurent pas à eux seuls l'effet causal du prompt.

## Ce que je recommande maintenant

1. Faire le premier essai de Mehdi sur **une offre réelle et un email anglais**, avec le [guide anglais](../friend-preflight/tester-guide.en.md). Le laisser essayer, puis l'aider au premier blocage. Observer aussi la première génération réelle sur le workflow Lambda ; ce parcours n'a pas encore été validé de bout en bout dans cet audit local.
2. Noter son temps d'attente, son temps de retouche, une erreur factuelle et une phrase qu'il conserve. Tester ensuite une offre SaaS puis une offre d'affiliation s'il en a une dont il connaît les conditions. Un seul ami expert peut révéler des problèmes ; son avis ne prouve pas la demande générale.
3. Prioriser ensuite les défauts observés : délai/coût, recherche qui classe mal des arguments de concurrence, et suivi qui suppose une action antérieure non vérifiée. L'absence d'une revendication dans une carte doit rester une inconnue, pas une preuve d'exclusivité.
4. Garder les avertissements de revue visibles. L'interface ne doit pas transformer une détection lexicale manquée en certitude d'absence de preuve ; ce texte a été corrigé dans `748274b`, validé par lint, typecheck et les 17 tests frontend.
5. Différer les nouveaux canaux et l'envoi automatique. Une fonction de retouche ciblée n'est prioritaire que si le temps d'édition de Mehdi confirme ce besoin. La première décision porte sur la valeur réelle du parcours existant.

Les cinq tentatives du corpus original et les deux cas enrichis totalisent environ **40,35 USD d'estimations internes locales** ; le scan et la carte ajoutent environ 3,92 USD, soit 44,27 USD hors compilations. Ce n'est pas une dépense API. Les essais échoués et annulés sont inclus, sans confondre étapes de rôle, appels terminés et requêtes internes des outils. Le [budget de test API](../friend-preflight/api-test-budget.fr.md) reste une provision distincte, hors AWS et taxes.

Déploiement final confirmé : API `53c2ba2` et console `748274b`, builds réussis. Les contrôles après le dernier build donnent 200 pour l'application et la santé API, 401 pour les campagnes anonymes. Preuves : `api-claim-scope-build.json`, `console-evidence-warning-build.json`, `production-http-final.json`. Les autres changements locaux de refonte de l'interface ont été préservés et exclus de ces commits.

## Corrections et périmètre de validation

La vérification des outils web consultait le fournisseur par défaut au lieu du modèle réellement routé pour le rôle. Correction déployée dans `3c16ee0` ; cinq tests de régression et suite complète de 1 488 tests réussis. Aucun appel de modèle supplémentaire introduit.

La session de production a été corrigée séparément : le frontend utilise maintenant `/api` sur son propre domaine. Le login, la navigation et le rechargement du navigateur ont conservé la session. Le compte de Mehdi dispose de 50 exécutions mensuelles partagées entre les différents travaux, et d'un guide anglais.

Ces résultats locaux ne valident pas encore une campagne réelle complète sur le workflow Lambda de production. Ils ne prouvent pas non plus la volonté de payer ni les performances commerciales des emails. Le premier essai de Mehdi doit vérifier ce parcours et relever le temps total, la fidélité aux sources et les corrections nécessaires avant utilisation.
