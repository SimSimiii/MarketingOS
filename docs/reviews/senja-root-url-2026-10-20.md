# Senja — audit du parcours depuis la homepage

**Verdict du cas au 22 octobre 2026 : sorties exploitables après revue normale de marque ; interface non vérifiée.** Le dernier email inspecté, run 14, atteint **88/100**. Il explique la collecte vidéo, la transcription et le widget, ainsi que le premier pas et les limites de l’essai gratuit. Les sorties amont sont utiles dans leurs périmètres documentés. Le signal applicatif reste `degraded / needs_review=true`, avec une note de lecteur simulé de 6 : ce verdict éditorial indépendant ne modifie ni ce statut ni les assets. Il ne constitue pas une validation générale du produit. Les notes mesurent la qualité éditoriale inspectée, pas une conversion ou une volonté de payer observée.

Entrée unique : **https://senja.io/**. Marque `62a1ac57-1ee2-4674-8c31-c4fbebb8477d`, campagne `a79f8375-e557-4861-990e-3a5fdf35ea2a`. Première audience exacte conservée : « A course creator or coach who needs student results on camera before the next cohort launch ». Le dossier recommande un périmètre étroit d'opérateurs de cohortes. Aucun guide, fait ou CTA ajouté par l'évaluateur au générateur, aucun changement pour une audience plus facile, aucun `generate_anyway`, aucune retouche des résultats historiques, aucun envoi.

## Notes de chaque étape

| Étape | Note /10 | Résultat inspecté et limite pratique |
|---|---:|---|
| Import |7,5|10 documents issus du crawl corrigé depuis la homepage, puis 7 découverts par les récupérations officielles normales. Documentation liée et guides plats suivis ; certains 403 et le budget borné limitent la couverture.|
| Knowledge v5 |8,5|243/243 citations correspondent aux documents stockés ; les 9 derniers faits ont aussi été retrouvés sur 5 pages officielles. Plans, prix mensuels, limites et contradictions distingués. Les déclarations vendeur ne deviennent pas des résultats clients mesurés.|
| Catalogue v3 |8|152 capacités atomiques dérivées ; les 9 références nécessaires à la première audience sont valides. Granularité encore lourde pour une lecture humaine.|
| Concurrents |8|5 concurrents directs, 21 pages, 149 claims : Testimonial.to, Famewall, Trust, Vocal Video, Trustmary. Alternatives DIY séparées. Couverture inégale : Trust n'a que 3 claims ; aucune performance commerciale établie.|
| Positionnement |8|0 différence documentée, 24 propositions non appariées conservées comme hypothèses. Adoption classée en preuve ; bruit numérique retiré du vocabulaire. Une absence de capture concurrente n'établit pas une exclusivité.|
| Audiences v2 |8|7 audiences conservées dans le même ordre. Compatibilité produit réévaluée en un appel fermé après recompilation, sans nouvelle recherche marché. Situations et méthodes proposées restent des hypothèses.|
| Recherche v3 |7,5|5 pages lisibles, 3 problèmes, 2 voix de créateurs, 25/25 citations uniques retrouvées indépendamment. Chaque problème reste à source unique ; 5 URL indisponibles, dates anciennes ou inconnues explicites. La vidéo avant lancement imminent n'est pas une situation empiriquement établie.|
| Dossier v3 |8,5|Courant : Knowledge v5, recherche v3, catalogue v3, interprétation 9. 24 faits classés, 3 PARTIAL, 3 silences. GO_NARROW pour les cohortes ; aucune hausse des réponses, authenticité ou ventes promise.|
| Transmission à la campagne |8,5|Preuves, fits et réserves transmis ; détails opérationnels autorisés accessibles au-delà du classement prioritaire. Fermeture des résumés et provenance cible/hypothèse confirmées. Conditions du CTA effectivement utilisées au run 14 ; contrôle de continuité courant réussi.|
| Email run 14 |8,8|Collecte par formulaire/lien, vidéo sans compte, transcription/widget, Free : 1 formulaire / 15 témoignages. Utilisable après revue normale et personnalisation légère ; bénéfice tardif, répétition et template accessoire à alléger. `needs_review=true` et lecteur simulé à 6 conservés.|
| Rendu et destination |9|Les 12 générations ayant livré un email ont été inspectées à 1280 et 390 px. CTA unique, pas de débordement constaté. Destination réelle : inscription Senja, visitée sans soumission.|
| Interface MarketingOS |Non vérifiée|Dernier essai : localhost:3000 refuse la connexion. Les vraies routes API, SQLite et providers tournent via ASGI, sans mocks ni lifespan ; cela ne prouve pas le fonctionnement navigateur ou le rechargement des anciens serveurs.|

Le résultat demandé couvre toutes les étapes. Les notes amont restent stables parce que leurs sorties n'ont pas changé pendant les dernières corrections de campagne. La recherche est utilisable pour une stratégie exploratoire étroite, pas pour affirmer une prévalence des problèmes ou une intention d'achat.

## Corrections des mécanismes

- **Collecte et compilation :** priorité aux guides d'onboarding et slugs plats, conservation des headers éditoriaux utiles, blocs tarifaires avec plan/période et conflits conservés. Les 403 restent des échecs de lecture ; ni budget ni citations n'ont été forcés.
- **Analyse marché :** résumé public issu des assessments, adoption distincte de vitesse, absence concurrente distincte d'exclusivité. Après nouvelle Knowledge, le recheck de compatibilité conserve les audiences/preuves et utilise le catalogue courant, sans alias manuel.
- **Recherche :** organization/workflow/need structurés traités comme hypothèses ; pistes de carte refetchées dans le budget existant, dates et sources uniques visibles. La recherche initiale à 4,5/10, surtout centrée sur une fatigue de lancement ancienne, est remplacée normalement par une recherche sur la collecte de témoignages à 7,5/10.
- **Dossier → campagne :** fits ADDRESSED v2 conservés avec leurs limites. Un fait non classé comme argument peut soutenir un mécanisme ou une condition officielle ; les WITHHOLD, faits non vérifiés et résultats clients hors contrat restent exclus. Le dossier a été régénéré normalement après changement d'interprétation.
- **Fermeture factuelle :** la liste autorisée s'applique aussi aux résumés de plans, free_entry et réponses d'objections. Une condition « sans carte bancaire » vraie mais hors contrat s'était glissée dans le run 9 par ces résumés ; la correction ferme cette voie sans modifier sa licence ou l'ancien email. Run 11–13 : fuite absente.
- **Cible et provenance :** l'audience exacte sélectionnée contraint le brief. Le need détaillé de la carte, qui mélangeait but et méthode de récompense, reste une hypothèse de stratégie ; les désirs issus de la recherche restent distincts. Le run 12 a révélé ma précédente surcorrection qui imposait les récompenses ; elle a été retirée. Run 13 : parcours vidéo central sans méthode imposée ni checklist administrative.
- **Revue :** la critique sélectionne au plus 6 faits dans un index compact des seuls faits autorisés ; le code transmet leurs citations/conditions complètes à la réécriture. Les lecteurs restent froids. Aucun nouvel appel pour cette sélection ; contexte de critique plus long.
- **Replan fermé :** les supporting_evidence_ids structurés atteignent désormais la reprise de stratégie déjà bornée et budgétée. Les faits interdits restent exclus ; aucune recherche supplémentaire pour des faits connus. Validé sur rejeu et tests scriptés ; les runs 12–13 n'ont pas activé ce chemin, donc aucune confirmation live annoncée pour cette branche.
- **Livraison :** un brouillon propre survit à une panne tardive, y compris pendant le replan. Une révision finale non résolue reste visible sans bloquer le draft. Les erreurs de prix après une clause avec tiret/conjonction ont été corrigées ; mauvais plan et période restent refusés.
- **Conditions de l'action validées :** lorsqu'un CTA nomme un seul plan, jusqu'à 6 faits canoniques de ce plan sont présentés dans les appels existants de rédaction et critique. Le rejeu réel retrouve E41/E146/E148/E156/E183 ; ni E96, comparaison, ni E182, service de migration gratuit, ne sont admis. Pas de nouvel appel ni de nouvelle permission par cette sélection. Le run 14 utilise effectivement les deux limites essentielles : un formulaire, jusqu’à 15 témoignages.

Les corrections portent sur le générateur et ses transmissions. Les snapshots, dossiers et emails antérieurs restent intacts. Les sorties amont inchangées sont réutilisées ; les nouveaux essais évaluent le comportement du modèle sur les mêmes données pertinentes.

## Évolution des emails

Grille stable /100 : faits 25, audience/offre 20, spécificité/argument 20, sujet-corps-CTA 15, rendu 10, retenue/répétitions 10. Aucun score sans email. Les changements de corpus et de provider sont des conditions différentes, pas une expérimentation contrôlée attribuant tout gain au code.

| Run | Conditions | Note | Appels | Jetons entrée / sortie | Résultat |
|---|---|---:|---:|---:|---|
|1|GPT, corpus initial|78|22|490953 / 12174|Argument générique, transmission dossier incomplète.|
|2|GPT, corpus initial|77|14|326391 / 8410|Transmission réparée, parcours élève encore flou.|
|3|GPT, corpus enrichi automatiquement|79|30|757533 / 18330|Faits récupérés ; CTA guide peu utile.|
|4|GPT, corpus encore enrichi|76|53|1343590 / 35224|Détails d'export connus mais exclus.|
|5|GPT|Non noté|1|46272 / 2983|Quota dur, aucun email.|
|6|Claude Opus/Sonnet, corpus courant|78|36|415968 / 82604|Coût et sortie vidéo mal expliqués.|
|7|Claude|79|22|248565 / 48793|Prix ajouté puis rejeté à tort ; ancien reçu de revue incorrect conservé comme historique.|
|8|Claude|79|29|402915 / 82927|Besoin vidéo rétabli puis contesté par une critique obéissant au brief.|
|9|Claude|83|36|393238 / 68408|Meilleur argument, mais fuite de résumé commercial hors contrat.|
|10|Claude|Non noté|1|45928 / 10366|Quota session, aucun email.|
|11|GPT, vue fermée|82|16|411987 / 10952|Fuite éliminée ; demande de replan ignorée malgré IDs structurés.|
|12|GPT, vue fermée|81|28|653121 / 16828|Récompenses imposées par hypothèse de découverte trop contraignante.|
|13|GPT, vue fermée|85|28|654564 / 16417|Parcours vidéo → transcription → widget cohérent ; conditions Free implicites.|
|14|GPT, vue fermée|88|35|794168 / 18742|Conditions Free et chemin de collecte concrets ; proposition exploitable avec retouches éditoriales légères.|

Dans le dernier groupe comparable : **82 → 81 → 85 → 88**. La qualité augmente au meilleur résultat, avec des régressions intermédiaires. Les appels multiples de panel, variantes et réécritures restent coûteux : un seul email prend environ 4–15 minutes selon les essais. Les estimations monétaires des rapports ne représentent pas une facturation API : les providers utilisent les abonnements CLI configurés. Run 14 : 35 appels, environ 4 min 22 s, estimation $1,3123. Le coût augmente face aux 28 appels du run 13 : la qualité progresse, l’efficacité de génération reste à améliorer. Aucune prétention à des résultats de campagne réels.

## Sorties et vérifications

- [Email actuel](../optimization/senja-root-url-2026-10-20/runs/aae5dccc-67a6-4d3d-8066-68b5c5df066a/email-1.txt), [HTML](../optimization/senja-root-url-2026-10-20/runs/aae5dccc-67a6-4d3d-8066-68b5c5df066a/email-1.html), captures [ordinateur](../optimization/senja-root-url-2026-10-20/runs/aae5dccc-67a6-4d3d-8066-68b5c5df066a/email-1-1280.png) et [mobile](../optimization/senja-root-url-2026-10-20/runs/aae5dccc-67a6-4d3d-8066-68b5c5df066a/email-1-390.png).
- [État durable](../optimization/senja-root-url-2026-10-20/state.json), [journal](../optimization/senja-root-url-2026-10-20/journal.md), [dernier snapshot complet](../optimization/senja-root-url-2026-10-20/steps/20261022T005048797375Z-capture.json).
- [Citations Knowledge](../optimization/senja-root-url-2026-10-20/knowledge-quotation-review-v5.json), [citations de recherche](../optimization/senja-root-url-2026-10-20/research-quotation-review-v3.json), [provenance cible/hypothèse](../optimization/senja-root-url-2026-10-20/target-provenance-replay.json), [replan fermé](../optimization/senja-root-url-2026-10-20/structured-replan-replay.json), [conditions du CTA](../optimization/senja-root-url-2026-10-20/active-action-plan-terms-replay.json).

**Validation finale : 1880 tests backend passent en 149,03 s**, 2 avertissements existants ; 102 tests ciblés, Ruff et schéma API passent. Frontend inchangé pendant ces dernières corrections : dernière validation, lint/typecheck et 29 tests passent. Le nouvel email et ses rendus ont ensuite été inspectés ; les 11 contrôles du [snapshot courant](../optimization/senja-root-url-2026-10-20/stage-integrity-review.json) passent. La troisième version n’a pas été préférée à la deuxième (0–4) : la version livrée est bien le choix du système, sans promotion manuelle d’un candidat.

La skill réutilisable est **marketingos-brand-audit**, avec la procédure du dépôt [brand-audit.md](../operations/brand-audit.md). Les vrais appels passent ici par un worker ASGI sans serveur réseau. Le contrôle automatique avait refusé le démarrage d'un serveur (« blocked by policy ») ; aucun autre port/shell n'a été utilisé pour réessayer ce démarrage. L'interface reste donc non vérifiée. Une réussite future de ce cas ne prouvera pas la qualité de toutes les marques ou fonctionnalités.


L’optimisation payante de ce cas s’arrête : aucune lacune matérielle connue dans l’essai étroit proposé ; les modifications restantes sont des retouches ordinaires. Il ne faut pas poursuivre les appels seulement pour atteindre le seuil du lecteur simulé ou satisfaire chaque demande d’aperçu. La recherche reste exploratoire, les performances commerciales inconnues. La priorité produit suivante est la régularité et le coût sur d’autres cas, ainsi que la vérification de l’interface lorsqu’elle sera accessible. Aucun suivi automatique n’est programmé.
