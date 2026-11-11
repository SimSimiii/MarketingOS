# MarketingOS — verdict d’utilité au 5 novembre 2026

**Verdict : vendable.** MarketingOS apporte une utilité suffisante pour vendre le service de préparation, génération et retouche d’emails à un indépendant, une agence ou un responsable marketing qui produit plusieurs campagnes à partir de marques documentées.

Les six scénarios fixés sur trois marques sont jugés utilisables avec une relecture normale de marque et des retouches locales facultatives. La séquence systeme.io qui échouait auparavant est complète et son troisième email possède désormais un argument étayé. Le verdict vient des textes et du parcours réellement vérifiés. La volonté de payer est estimée à partir de cette utilité ; aucun paiement client n’a été observé.

| Scénario conservé | Livraison | Revue éditoriale /100 | Résultat |
| --- | --- | --- | --- |
| Papier, acquisition | 1/1 | 88 | Utilisable ; formulation à personnaliser normalement. |
| Papier, considération | 1/1 | 87 | Utilisable ; rédaction et preuves cohérentes. |
| systeme.io, acquisition affiliée | 1/1 | 83 | Utilisable ; rôle indépendant et portée de la plateforme conservés. |
| systeme.io, séquence affiliée | 3/3 | 85 | Trois décisions utiles : vente physique, suivi des inscriptions, capacités d’une formule. Versions choisies et export vérifiés. |
| Loops, acquisition | 1/1 | 89 | Deux intégrations distinctes expliquées avec leurs conditions et un guide officiel. |
| Loops, considération | 1/1 | 88 | Choix SMTP/Hook étayé, conditions techniques préservées, digression supprimée par une retouche facultative. |

Les notes sont un jugement éditorial sur la grille fixée. Les trois premiers scénarios gardent leurs livrables historiques ; ils ne deviennent pas de nouvelles générations. Aucun changement d’audience vers un cas plus facile, ajout manuel d’une URL documentaire, rédaction manuelle d’un livrable ou forçage factuel n’a servi à valider les six cas ordinaires.

Les huit emails choisis passent les [contrôles déterministes actuels](../optimization/acceptance-2026-11-01/all-selected-deterministic-checks.json). La [séquence exportée](../optimization/acceptance-2026-11-01/systeme-sequence/final-export.txt), ses [textes et HTML](../optimization/acceptance-2026-11-01/systeme-sequence/final-selected/result.json), le [contrôle de copie/export](../optimization/acceptance-2026-11-01/systeme-sequence/final-ui-check.json) et les [rendus](../optimization/acceptance-2026-11-01/systeme-sequence/final-selected/render-check.json) sont conservés. Les versions ordinateur et mobile ont été inspectées.

## Corrections qui expliquent le résultat

Le problème des bénéfices sous-exploités avait plusieurs causes concrètes dans le code.

- La récupération confondait deux preuves de frais différents lorsqu’elles partageaient la même citation. L’identité tient maintenant compte de la revendication, du périmètre, des conditions et du niveau de vérification ; un identifiant exact cité reste attaché à sa preuve.
- Des étapes autorisées de configuration étaient placées dans `must_not_say`. Elles sont désormais conservées dans `claim_conditions`, distinctes des interdictions et transmises aux rédacteurs, réécritures et propositions.
- L’anti-répétition des preuves supprimait une source nécessaire à un autre argument. Dans le plan capturé, E72/E13/E119 devenaient E119/E72 ; le bénéfice entier était ensuite vidé. La [reproduction sur le plan sauvegardé](../optimization/acceptance-2026-11-01/systeme-sequence/captured-support-dependency-replay.json) montre que les trois dépendances restent maintenant présentes et autorisées, sous le plafond existant. Cette correction déterministe a été vérifiée sans racheter une campagne complète.
- La reprise de stratégie reçoit les arguments et les textes réellement conservés, ainsi que les positions à réparer. Les étapes de migration qualifient un bénéfice ; elles ne remplacent plus à elles seules une raison d’acquisition.
- Les propositions sont vérifiées contre tous les autres emails choisis, y compris ceux placés plus loin dans la séquence. L’acceptation repasse les contrôles avec le contexte courant et les choix sont sérialisés dans le processus. La [preuve HTTP](../optimization/acceptance-2026-11-01/systeme-sequence/selection-recheck-proof.json) montre qu’une ancienne proposition auparavant propre est refusée après le changement d’un autre email. La version choisie reste intacte. Aucune gate factuelle ou de répétition n’a été affaiblie.

La signature fournie est préservée sans inventer une personne, une commission ou une expérience produit. Les conditions qui changent la promesse restent dans les emails ; les interdictions internes ne deviennent pas une liste systématique de réserves.

## Parcours et valeur payante observés

La préparation des sources, les connaissances compilées et le contexte de marché/audience sont réutilisables d’une campagne à l’autre. Le parcours sans personnalisation reste disponible : la campagne testée indique « Nothing set — the system decides » et génère sans sélection obligatoire de faits ni consigne supplémentaire.

La révision d’un email final réutilise son contexte et achète normalement un seul appel. Les différences sont visibles ; accepter, refuser, demander un autre ajustement et garder l’original ont été parcourus dans l’interface. La séquence finale utilise cinq appels de retouche locale sur deux emails : raccourcissement, retrait d’un prix sans période confirmée, précision du preview et suppression d’une reprise de formulation. Son argument et ses liens restent ceux du plan final. Les anciens scores de lecture sont absents des versions éditées ; les propositions ont leurs propres contrôles. Le statut et le rapport historiques du run sont conservés.

Quatre témoins directs avec le même modèle et le contexte déjà préparé produisent aussi de bons textes. La valeur payante établie est donc le travail de préparation et de réutilisation, les préférences cadrées, la traçabilité, les contrôles et les versions exportables. Une supériorité générale de prose n’est pas démontrée.

## Vérifications, appels et cas limites

La [validation](../optimization/acceptance-2026-11-01/validation.json) comprend les contrôles réels des huit emails, les rendus, l’interface, Ruff, ESLint, TypeScript et `git diff --check`. **59 tests ciblés passent**, après le constat d’utilité fonctionnelle, avec un avertissement de dépendance. La suite complète n’a pas été relancée, conformément à la priorité donnée par l’utilisateur. Les 2 177 tests complets antérieurs restent historiques et ne sont pas présentés comme une validation des derniers changements.

Le [décompte](../optimization/acceptance-2026-11-01/metrics-final.json) conserve **au moins 804 appels terminés** pour toute l’investigation : 741 en campagnes, 48 en préparation capturée, quatre témoins et onze propositions. Un ancien compteur de carte d’audiences manque ; le total exact reste inconnu. Le dernier run complet de séquence utilise 92 appels, les cinq propositions finales un appel chacune. Les montants en dollars sont des estimations de catalogue ; les providers utilisés facturent les abonnements CLI et aucun solde API n’a été activé. Le temps humain économisé et la marge ne sont pas mesurés.

Les cas limites ne sont pas ajoutés au dénominateur des six cas ordinaires. Le cas sans matière avait été arrêté avec zéro appel. CABAIA conserve une recommandation prudente et aujourd’hui périmée ; l’interface demande une confirmation. Un essai supplémentaire a été lancé par erreur en supposant que l’API refuserait cette recommandation : son contrat API est consultatif et enregistre le lancement malgré l’avis. L’annulation a été demandée, deux appels de stratégie restent comptés, aucun email n’a été retenu comme réussite pour ce cas. Cet essai et l’erreur d’opérateur restent archivés.

Les changements restent sur la branche courante `master`. La base utilisée pour l’audit est la copie SQLite séparée et conservée. Aucun email n’a été envoyé et aucun déploiement n’a été réalisé. L’arrêt des essais facturés vient du résultat utilisable atteint, pas d’un épuisement de quota. Les échecs et anciens verdicts restent dans les états, journaux et l’[archive du bilan précédent](acceptance-2026-11-01-history-2026-11-02.md).
