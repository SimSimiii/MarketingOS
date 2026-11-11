# Validation indépendante CleanShot X — 8 novembre 2026

**Verdict : NON pour le parcours payant promis dans son état actuel.** Depuis une nouvelle marque et sa seule homepage, MarketingOS a consommé 23 réponses modèles et livré **0 email sur 1**. Je ne paierais pas pour ce résultat. Deux faux positifs déterministes ont empêché la livraison.

Ce test ne retire pas les réussites précédentes : il montre qu’elles ne suffisaient pas à établir la fiabilité générale. Aucun correctif ni seconde génération de rattrapage n’a été effectué ici.

## Conditions

Skills : [marketingos-brand-audit](C:/Users/oussa/.codex/skills/marketingos-brand-audit/SKILL.md) et [campaign-optimization](../../.agents/skills/campaign-optimization/SKILL.md), avec AGENTS.md et la procédure du dépôt.

Nouvelle marque **CleanShot X** ; seule entrée web : **https://cleanshot.com/**. Nom et homepage saisis dans la vraie interface. Objectif par défaut conservé : « Introduce our product to a new buyer with one clear next step. » Aucun fait, source secondaire, CTA, audience, modèle ou consigne ajouté par l’évaluateur. Pas de generate_anyway.

Le système a choisi d’abord support/dev utilisant des captures annotées. Après refus de ce segment, il a automatiquement essayé IT/admin. Aucun remplacement manuel pour faciliter le test. Campagne d’un email ; réglage courant **Fast**, modèles configurés inchangés. Forecast : **3–6 appels**, Knowledge réutilisée.

Branche **master** conservée ; empreintes identiques avant/après sur **448 fichiers app/prompts/frontend**. Le checkout était déjà modifié avant l’audit. Aucune modification de code produit pendant ce test. Base SQLite isolée copiée ; base de développement intacte. Aucun envoi, achat, inscription externe ou déploiement.

Marque : 90bbe18f-7b08-45fb-9a00-be1864cb6777. Campagne : bdeb06f6-9ee3-433e-9294-fdffc71064d2. Exécution : 258d1499-2d6d-431a-9270-f0c309a45661.

## Résultat terminal

API : **status=failed ; outcome_status=failed ; needs_review=false ; aucun asset**. L’absence de needs_review ne signifie pas réussite : aucun brouillon n’a été livré.

L’interface affiche « Failed », « Delivered 0 of 1 email », « Nothing was produced in this run ». Copie/export indisponibles. [Capture réelle](../optimization/cleanshot-cold-v30-validation-2026-11-08/ui-execution-failed.png).

Donc **email final non noté /100**. Aucun HTML livré, rendu mobile/ordinateur, export ou CTA livré à valider. Les brouillons de diagnostic ne sont pas des livrables et n’ont pas été transformés manuellement en email exportable.

## Causes reproduites gratuitement

1. **SCIM refusé comme texte crié.** Premier brouillon : le seul blocage est « SCIM is set in capitals ». Le protocole est cité dans la documentation officielle ; la liste d’exceptions du contrôle ignore SCIM. Rejeu sur le brouillon inchangé : contrôle factuel réussi, contrôle anti-majuscules bloquant.
2. **Nom abrégé du plan refusé.** La réécriture remplace SCIM par « Scim » et écrit « The Pro plan costs $10 per user/month, billed annually », après avoir nommé CleanShot Pro dans l’ouverture. La source officielle documente les mêmes montant, plan, unité et facturation annuelle. Le contrôle refuse pourtant le sujet tarifaire abrégé ; table d’alias dérivée vide. Rejeu : contrôle anti-majuscules réussi, contrôle factuel bloquant. C’est un faux positif de résolution du plan.
3. Les deux brouillons étant bloqués, la sélection finale conserve le premier rejeté et termine en échec. La correction doit préserver les vrais contrôles factuels ; livrer un texte bloqué ou tout désactiver serait une mauvaise résolution.

Preuves : [rejeu](../optimization/cleanshot-cold-v30-validation-2026-11-08/gate-replay.json), [script sans modèle](../optimization/cleanshot-cold-v30-validation-2026-11-08/diagnose_gates.py), [brouillon rejeté 1](../optimization/cleanshot-cold-v30-validation-2026-11-08/rejected-draft-1.txt), [brouillon rejeté 2](../optimization/cleanshot-cold-v30-validation-2026-11-08/rejected-draft-2.txt), [timeline](../optimization/cleanshot-cold-v30-validation-2026-11-08/runs/258d1499-2d6d-431a-9270-f0c309a45661/timeline.json).

Les deux lecteurs simulés comprennent l’offre et donnent 6/10 d’intérêt. Ce ne sont ni des scores de livrable ni des prédictions commerciales. Réserve utile : demander un abonnement annuel payant immédiatement est exigeant pour un nouvel acheteur IT sans détails de configuration. Ne pas inventer de compatibilité IdP, de procédure de déploiement ou d’essai gratuit pour la satisfaire.

## Appréciation par étape

Notes éditoriales après inspection ; pas des mesures de conversion.

| Étape | /10 | Constat |
|---|---:|---|
| Import | 8 | Neuf pages pertinentes automatiques ; récupération ajoute trois captures dont des URLs répétées. Corpus lu partiellement sous budget. |
| Knowledge | 8 | 36 entrées de preuve ; UI : 35 citables, 67 cartes avec contexte. Basic/Pro, facturation et absence d’essai correctement séparés. |
| Catalogue | 7 | 10 capacités, 36 claims ; huit faits récupérés. Capture/annotation reste sous-exploitée dans le premier dossier. |
| Concurrents | 6 | Trois alternatives découvertes ; Shottr seul profilé sur quatre pages. Couverture étroite. |
| Positionnement | 6 | Aucune différence établie ; propositions non retrouvées explicitement inconnues, sans exclusivité inventée. |
| Audiences | 8 | Trois hypothèses plausibles et exclusions cohérentes ; aucune demande client démontrée. |
| Recherche d’audience | 4 | Sources peu adaptées ; premier segment : compilations concurrentes et problème technique très particulier. IT : zéro problème étayé et fils Jamf concernant d’autres produits. |
| Dossier | 7 | Refus de promesses non documentées ; périmètre factuel de premier email ouvert sans bypass. Premier segment encore refusé après récupération officielle. |
| Génération/livraison | 0 | Deux brouillons, deux faux positifs bloquants, aucun livrable. |
| Consultation | 4 | Échec visible ; score affiché 0.0 malgré absence d’email livré ; réserves techniques longues et répétées. |

Erreur amont concrète : la recherche parle de « MacPaw’s other product » et de « MacPaw-family » pour contextualiser CleanShot à partir de CleanMyMac. Le footer officiel CleanShot attribue le produit à **MTW/MakeTheWeb** ; MacPaw apparaît parmi les logos clients. L’association erronée atteint les notes du rapport final, même si les brouillons ne reprennent pas MacPaw. [Recherche conservée](../optimization/cleanshot-cold-v30-validation-2026-11-08/audiences-final.json).

Les artefacts bruts portent également des marqueurs source_metadata_changed_review_required après récupération tandis que l’UI présente des faits citables. Signal de cohérence à examiner ; pas une preuve de changement matériel des conditions. Les prix des brouillons ont été comparés séparément aux sources importées.

## Points solides

- Parcours minimal accessible sans configuration facultative.
- Sources et conditions conservées : Basic 35 $ une fois ; Pro 10 $/utilisateur/mois facturé annuellement ; remboursement 30 jours distinct d’un essai gratuit.
- Knowledge réutilisée sans recompilation pendant la campagne.
- Contraintes maintenues : Mac et Cloud, aucune compatibilité MDM/IdP inventée, situation du destinataire non présumée.
- Budget génération respecté : six réponses pour une borne haute de six. Échec et traces persistés ; aucun texte bloqué présenté comme validé.

## Mesures et incident externe

| Mesure | Résultat |
|---|---:|
| Préparation réussie après reprise | 17 réponses ; **9 min 41 s** |
| Génération | 6 réponses ; **3 min 38 s** ; 5 groupes d’agents |
| Total réponses terminées | **23** |
| Traitement préparation réussie + génération | **13 min 19 s** |
| Premier clic de préparation → état final | **18 min 55 s**, incident auth et pause d’inspection inclus |
| Tokens entrée / sortie | 502 523 / 78 682 |
| Équivalent tarifaire estimé par l’app | préparation 3,0820 $ + génération 1,5766 $ = **4,6586 $** |
| Emails livrés | **0 / 1** |

Les dollars sont des estimations applicatives. Les providers utilisent les abonnements configurés, pas un solde API. Ce n’est ni une facture constatée ni une mesure de marge. Temps humain actif non chronométré, donc non mesuré.

La première tentative a échoué avant toute réponse modèle : verrou OAuth Claude Code abandonné, pas quota épuisé. Après vérification de l’absence de processus Claude actif et du dossier vide, seul ce verrou local a été retiré. « Continue preparation » a réutilisé les pages. Aucun changement de credentials ou de facturation. Ce parcours n’est donc pas présenté comme ininterrompu. [Réparation](../optimization/cleanshot-cold-v30-validation-2026-11-08/auth-repair.json) ; mécanisme décrit dans le [dépôt Claude Code](https://github.com/anthropics/claude-code/issues/95236).

## Priorités avant une nouvelle validation

1. Reconnaître les acronymes techniques légitimes, en conservant le contrôle du texte promotionnel crié.
2. Résoudre les noms de plans abrégés non ambigus, en conservant les refus de mauvais plan, période et conditions.
3. Vérifier identité du produit et pertinence des sources avant les rapprochements de recherche.
4. Proportionner le CTA à l’information du nouvel acheteur via une action documentée.
5. En absence de livrable, afficher une note indisponible et une cause utile avant les détails techniques.

Revalidation attendue : rejeu gratuit sur ces brouillons puis même campagne après correctif et révision explicite, enfin autre marque indépendante. Conserver cet échec. Aucun correctif appliqué dans ce cas.

## Vérifications et limites

UI réelle + API, vrais appels modèles, sources officielles importées, deux brouillons et deux lectures, état terminal, capture visuelle et reproduction déterministe inspectés. Aucun TU relancé : aucun changement produit. Aucun rendu/export/CTA ne peut être déclaré validé sans asset. Ajustement après génération et séquence entière non testés ici. Validation acheteur réelle : **not_validated**.

[Mesures](../optimization/cleanshot-cold-v30-validation-2026-11-08/metrics.json) · [Grille commerciale](../optimization/cleanshot-cold-v30-validation-2026-11-08/commercial-review.json) · [État](../optimization/cleanshot-cold-v30-validation-2026-11-08/state.json).
