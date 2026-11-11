# Contrôles de contenu par IA — correction v31

**Le blocage CleanShot est corrigé : la même campagne livre désormais un email, avec une relecture IA sourcée, en 5 appels modèles.** Les deux brouillons auparavant rejetés sont acceptés par le nouveau relecteur ; cinq variantes incorrectes ou interdites sont refusées. Sept essais comportementaux réels sur sept correspondent à l’attendu.

Cette intervention applique la demande explicite de confier le sens aux modèles et de limiter les veto en code aux propriétés mécaniques. Elle remplace la précédente politique « seuls les contrôles déterministes bloquent ». Branche master conservée, aucun worktree, aucun envoi ni déploiement. Skill appliquée : [campaign-optimization](../../.agents/skills/campaign-optimization/SKILL.md).

## Ce qui décide maintenant

Un [relecteur indépendant](../../backend/app/marketing/grounding.py), rôle claim_reviewer, lit le texte complet avec les citations, conditions, restrictions et consignes du brief. Son [prompt fermé au web](../../backend/prompts/claim_reviewer.md) lui demande d’évaluer chaque affirmation matérielle : fonctions qualitatives, prix, unité, période, offre, propriétaire, citations, compatibilité, résultats et situation du destinataire. Il distingue fait soutenu, contradiction et incertitude. Il doit ancrer ses constats dans des passages exacts et citer les sources utilisées.

Le code conserve : champs requis, merge fields configurés, limites explicites du canal, présence des identifiants et citations référencés, identité exacte du texte/contexte approuvé, décompte des livrables, budgets, délais et annulation. Le code ne décide pas si « SCIM » est du texte crié ou si « The Pro plan » désigne un autre plan. Les citations présentes sont une condition d’intégrité ; leur implication sémantique est jugée par le modèle.

Les anciens contrôles lexicaux ne sont plus exécutés comme juges de livraison dans la génération et les modifications. Ils restent des instruments de diagnostic/évaluation, notamment pour l’analyse gratuite d’un texte collé. Les compteurs de preuves restent visibles mais ne peuvent plus opposer un veto lexical à une réécriture. La sélection s’appuie sur les relectures et préférences des modèles. Seuls les doublons de texte intégralement identiques sont éliminés mécaniquement ; deux arguments partageant un objet ou une ouverture restent évaluables.

Les préférences stylistiques restent des avis. Les assertions non soutenues ou contradictoires et les violations explicites de consignes peuvent demander correction. Une absence ou une réponse invalide du relecteur ne devient pas une approbation. Les verdicts IA restent probabilistes ; ce dispositif ne constitue pas une garantie de vérité.

## Parcours couverts et conservation des versions

- Chaque candidat et réécriture reçoit son propre contrôle de sources, avant sa sélection.
- Un nouvel objet/aperçu choisi est relu avec son corps ; s’il échoue, la version déjà relue est conservée.
- Une modification locale utilise le même relecteur sans relancer la campagne, sans emprunter le score de lecture à froid de l’original.
- Un reçu est lié au texte exact, au brief et aux informations factuelles. Un changement de texte, de conditions ou de permissions ne réutilise pas son ancien verdict. Une vue d’audience seule, absente du prompt de contrôle, ne rend plus ce reçu artificiellement périmé.
- Les anciens emails sans reçu IA valable obtiennent une première revue de leur original lors d’un ajustement. Leur nouvelle proposition est contrôlée séparément. Un original non soutenu reste conservé dans l’historique mais sa restauration est refusée proprement ; un original approuvé reste restaurable.
- Acceptation et restauration ne rachètent pas de relecture lorsque leur reçu est encore valable. Les traces et reçus sont persistés avec les versions et événements existants.

Un essai réel a révélé pendant l’intégration que l’ancien reçu englobait aussi une vue d’audience non envoyée au relecteur, provoquant une erreur de restauration. Le reçu porte maintenant sur ses vraies entrées ; la migration des reçus précédents exige de reproduire leur ancien contexte exact. L’API retourne une erreur contrôlée lorsqu’une restauration n’est pas admissible. Le rejeu réel restaure désormais l’original avec HTTP 200 et le bon contenu.

## Budget

Un texte distinct ajoute normalement **un appel de revue**, avec au plus la correction JSON bornée habituelle du runtime. La réponse et le contexte sources sont bornés ; aucune boucle de recherche ni arbitrage récursif n’est ajouté. Le relecteur passe exclusivement par ModelSession et les abonnements configurés.

Le forecast inclut les candidats, réécritures, objet final, reprises de stratégie et modifications de séquence. Pour CleanShot Fast : **4–10 appels annoncés, 5 consommés**. Une modification locale reste limitée à deux passages rédacteur/relecteur ; un ancien original sans reçu peut nécessiter une revue initiale supplémentaire. Les processus restent bornés par leurs délais et les budgets existants.

## Sept essais modèles réels

Entrées issues des brouillons et sources conservés du cas initial. Aucun fait ni URL ajouté pour sauver une campagne.

| Cas | Résultat attendu | Résultat réel |
|---|---|---|
| Brouillon avec SCIM | Accepter | Accepté |
| Nom abrégé The Pro plan, termes annuels corrects | Accepter | Accepté |
| 10 $ facturés mensuellement au lieu d’annuellement | Refuser | Refusé, période incorrecte identifiée |
| Essai gratuit inventé de 30 jours | Refuser | Refusé, garantie de remboursement distinguée |
| Compatibilité Windows inventée | Refuser | Refusé, contradiction avec la FAQ |
| Attribution à MacPaw sans source | Refuser | Refusé, affiliation non étayée |
| Prix expressément exclu par la consigne | Refuser | Refusé, violation de consigne identifiée |

Ces sept cas ont consommé **7 réponses modèles**, sans appel supplémentaire pour le rejeu du texte et contexte identiques. Estimation applicative équivalente : **1,7071 $**, pas une facture API. [Quatre cas initiaux](../optimization/cleanshot-cold-v30-validation-2026-11-08/ai-review-v31.json) · [Trois cas supplémentaires](../optimization/cleanshot-cold-v30-validation-2026-11-08/ai-review-v31-additional.json).

## Campagne réelle après correction

Même marque, même campagne, même demande, mêmes connaissances et audience déjà persistées ; aucun nouveau choix de fait, CTA, source ou modèle injecté. La génération teste le comportement réel des modèles ; les vérifications de code utilisent les providers scriptés.

| Mesure | Avant, v30 | Après, v31 |
|---|---:|---:|
| Emails livrés | 0 / 1 | **1 / 1** |
| État / résultat | failed / failed | **completed / completed** |
| Réponses modèles | 6 | **5** |
| Durée génération | 3 min 38 s | **3 min 07 s** |
| Estimation applicative équivalente | 1,5766 $ | **1,1180 $** |
| Réécritures automatiques | 1 | **0** |

L’après comprend deux réponses de stratégie, un rédacteur, une revue de sources et une lecture à froid. Le coût moindre est une observation de ce cas, pas une économie garantie : le modèle a aussi choisi un texte et un CTA différents.

Objet livré : **Manage CleanShot access centrally**. L’email explique la gestion des accès dans Cloud, conserve 10 $/utilisateur/mois facturé annuellement et macOS 13+, puis invite à consulter la page tarifaire. Ce CTA demande moins d’engagement qu’un abonnement annuel immédiat. Le relecteur de sources approuve dix passages ; le lecteur simulé comprend l’offre, la juge pertinente et donne 7/10 d’intérêt. Ce score n’est pas une prévision de conversion.

Appréciation éditoriale du livrable : **83/100** — faits 24/25 ; audience/offre 16/20 ; spécificité/argument 12/20 ; cohérence objet-corps-CTA 13/15 ; rendu 9/10 ; absence de promesses abusives/répétitions 9/10. Les fonctions de gestion des accès restent répétées et le détail des contrôles admin mérite encore une revue de marque normale. Aucun résultat opérationnel non démontré n’est promis.

[Email livré, texte](../optimization/cleanshot-cold-v30-validation-2026-11-08/runs/19107648-aa8d-4e35-982a-bc898befef22/email-1.txt) · [HTML](../optimization/cleanshot-cold-v30-validation-2026-11-08/runs/19107648-aa8d-4e35-982a-bc898befef22/email-1.html) · [Mobile 390 px](../optimization/cleanshot-cold-v30-validation-2026-11-08/runs/19107648-aa8d-4e35-982a-bc898befef22/email-1-390.png) · [Ordinateur 1280 px](../optimization/cleanshot-cold-v30-validation-2026-11-08/runs/19107648-aa8d-4e35-982a-bc898befef22/email-1-1280.png).

Les deux rendus ont été inspectés, sans débordement horizontal. Le CTA réel https://cleanshot.com/pricing répond HTTP 200 et affiche Pro et la facturation annuelle. Aucun achat ni inscription. Ce contrôle navigateur ne valide pas tous les clients email.

## Ajustement local réel

Demande : raccourcir et rendre plus direct, en conservant les conditions annuelles et le prochain pas. Résultat : une proposition, **un passage rédacteur + une revue indépendante = 2 appels**, aucun nouveau lancement de campagne. Proposition approuvée, acceptation HTTP 200, original conservé. Son score de lecteur est bien null, celui de l’original reste 7 après restauration. Restauration HTTP 200, contenu original identique. Le nouveau reçu diffère de celui de l’ancien texte.

[Proposition et contrôle](../optimization/cleanshot-cold-v30-validation-2026-11-08/revision-proposal-v31.json) · [Acceptation](../optimization/cleanshot-cold-v30-validation-2026-11-08/revision-accepted-v31.json) · [Restauration](../optimization/cleanshot-cold-v30-validation-2026-11-08/revision-restored-v31.json).

**15 appels modèles observés pour cette intervention** : sept essais, cinq pour la campagne, deux pour la modification et un dernier contrôle du texte ajusté avec sa consigne locale explicite. Ce dernier contrôle est également approuvé ; les préférences locales atteignent maintenant le relecteur et le reçu est lié à cette demande. Les dollars affichés sont des estimations applicatives ; aucun fournisseur n’a été basculé vers une facturation sur solde API.

## Vérifications du dépôt

La suite complète finale a passé **2 280 tests backend**. Les derniers ajustements du parcours de modification sont aussi couverts par **19 tests ciblés**, tous passés. Résultat complet : [backend-tests-ai-review-v31-release.txt](backend-tests-ai-review-v31-release.txt). Frontend : 37 tests, lint et TypeScript valides. Ruff et schéma API à jour. Pas de migration de base requise : les reçus utilisent les champs JSON existants.

Les nouveaux tests vérifient notamment le refus d’une citation inventée, une affirmation qualitative non soutenue, l’indépendance des verdicts, la panne du relecteur, la restauration des anciens emails approuvés et le refus contrôlé des originaux non approuvés. Les anciens tests de veto lexical ont été adaptés pour fournir des décisions du modèle ou vérifier que le style reste non bloquant ; les contrôles factuels n’ont pas été simplement désactivés.

## Limites du périmètre

La recherche d’audience initiale reste archivée, y compris sa mauvaise association MacPaw. Les prompts de cartographie et de synthèse ont été renforcés sur l’identité et la pertinence des sources ; ce travail n’a pas relancé tout le scan de marché. Le nouveau relecteur refuse déjà l’attribution MacPaw dans le texte livré lors de l’essai dédié. Les anciens diagnostics gratuits et instruments de benchmark restent distincts de la décision de livraison.

Cette validation porte sur la nouvelle frontière code/IA et son intégration. Elle n’est ni un nouvel audit complet sur une autre marque ni une validation de demande acheteur, de conversion ou de rentabilité. État commercial réel : **not_validated**.

[Mesures complètes](../optimization/cleanshot-cold-v30-validation-2026-11-08/metrics-v31.json) · [Échec initial conservé](cleanshot-validation-2026-11-08.md).
