# Support inbox sequence validation

## 2026-09-19 — preset Balanced 1483e4cc interrompu

- Qualité : **non notée**, 0/2 livrables. Meilleur score inchangé : **91/100**
  sur Fast ; Maximum reste à 87/100.
- Le routeur a bien utilisé le nouveau modèle par défaut GPT-5.6 Sol. Après cinq
  rôles et $1.6495 estimés, le critique a rencontré la limite d'usage Codex sur
  trois tentatives ; reprise annoncée à 20:49. Il s'agit d'un blocage de quota,
  pas d'un verdict sur la qualité Balanced.
- La configuration Balanced est vérifiée par les tests de routage et utilise le
  même modèle déjà vendable sur Fast et Maximum. Sa génération réelle peut être
  reprise après le reset avec `optimize_campaign.py run --case
  docs/optimization/orqagent-support/case.json`, après avoir remis le preset
  Balanced pour cette seule validation.
- La campagne de travail est restaurée à son preset Maximum après ce contrôle.

## 2026-09-19 — preset Fast 5dc4bc0c validé

- Qualité : **91/100**, nouveau meilleur score observé (+4 face à Maximum
  GPT-5.6 Sol). Grille : faits 24/25, clarté 19/20, argument 17/20,
  continuité 14/15, finition/rendu 9/10, surpromesses/répétitions 8/10.
- Forces : distinction immédiate entre brouillon et envoi ; mécanisme précis et
  étayé ; second email propose un essai honnête, inclut explicitement la limite
  de justesse et fournit une action réalisable. Les deux emails se complètent.
- Défaut restant : aucune preuve client disponible et CTA encore générique ; le
  panel simulé reste à 6/10. Ces limites n'empêchent pas une vente après revue
  de marque ordinaire.
- Preuves : 2/2 emails, aucune violation, neuf rôles, estimation $3.1807 ; liens
  signup corrects. Rendu mobile 390 px inspecté : texte, bouton et pied de page
  lisibles, sans chevauchement visible. Tests : 1 256 backend, Ruff, lint et
  TypeScript propres.
- Verdict : Fast atteint le seuil vendable sur ce scénario. Balanced reste à
  valider ; Maximum conserve 87/100.

## 2026-09-19 — validation des modèles par défaut des trois plans

- Demande : configurer Fast, Balanced et Maximum avec des modèles ayant produit
  des résultats vendables. Seul GPT-5.6 Sol a franchi le seuil sur un livrable
  réellement inspecté (run Maximum 16c49a58, 87/100) ; il devient donc le modèle
  de campagne par défaut des trois presets. Les différences de prix et de délai
  restent portées par le nombre de variantes, lectures et révisions.
- Hypothèse : conserver le modèle validé évite qu'un plan moins cher dégrade le
  savoir-faire rédactionnel ; Fast peut néanmoins rester sous le seuil faute de
  critique et de sélection suffisante. Balanced doit offrir un compromis vendable.
- Changement prévu et réalisé dans `app/marketing/policy.py`, avec libellés UI
  corrigés pour ne plus promettre de « modèles moins chers » ou « meilleurs modèles ».
  Aucun nouveau rôle ni appel par preset.
- Attendu observable : chaque rôle de campagne résout vers `gpt-5.6-sol` sur les
  trois presets sans choix manuel ; tests de routage propres. Exécuter ensuite Fast
  et Balanced sur les mêmes entrées et noter séparément leurs livrables. Maximum
  garde son résultat validé existant.

## 2026-09-19 — itération OpenAI 16c49a58, cas validé

- Qualité : **87/100** sur la piste OpenAI, soit +17 points indicatifs face au
  run Claude 3cc88cb7. Le changement de fournisseur rend les scores non
  comparables au sens strict. Meilleurs scores : OpenAI 87, Claude 70.
  Grille : faits 24/25, clarté 18/20, argument 16/20, continuité 13/15,
  finition/rendu 9/10, absence de surpromesses/répétitions 7/10.
- Forces : l'email 1 explique l'approbation, les expéditeurs ignorés et la limite
  de 24 h sans faux dilemme ; l'email 2 propose un test vérifiable sur un document
  connu, avec formats, contexte conversationnel, moins de deux minutes et absence
  de carte soutenus par E11/E50/E130/E39. Produit et action sont clairs.
- Défaut restant : les deux textes restent sobres et sans preuve client ; le panel
  simulé les évalue à 6/10 et le rapport marque `landed: false`. Cela limite la force
  persuasive, mais ne crée ni défaut matériel ni promesse non étayée pour ce CTA
  d'essai. La source elle-même ne contient aucun cas client à utiliser.
- Preuves : 2/2 emails, aucune violation, 24 rôles, estimation $16.9441 ; CTA signup
  corrects. HTML inspecté sur bureau et à 390 px : lecture, boutons et pieds de page
  sans chevauchement ni débordement visible. Comparaison sauvegardée dans
  `compare-3cc88cb7-16c49a58.json`. Modèles de campagne restaurés aux valeurs par
  défaut après le run.
- Verdict : la séquence est utilisable après revue de marque ordinaire et atteint
  le seuil vendable pour ce scénario. Avec le cas Slack anglais déjà validé, le
  produit atteint le seuil sur les deux scénarios testés. Cela ne mesure ni demande,
  ni clics, ni volonté de payer ; le cas support reste une validation de robustesse.

## 2026-09-19 — retest Claude 4cf24ca0 interrompu

- Qualité : **non notée** ; aucun livrable, 0/2 emails. Meilleur score comparable
  inchangé : **70/100** (run 3cc88cb7, itération 1).
- Les corrections et 1 256 tests réussis précèdent le run. Celui-ci a atteint la
  lecture du premier email, puis la limite de session Claude à 15:47 UTC ; remise
  à zéro annoncée à 20:30 Paris. Neuf rôles, estimation $3.1461.
- Prochaine action : valider immédiatement les mêmes corrections avec le fournisseur
  OpenAI déjà pris en charge et configuré, sur les mêmes contenu, audience et politique.
  Ce score formera une piste séparée, non comparable au run Claude, car le modèle change.

## 2026-09-19 — itération de reprise, run 3cc88cb7

- Qualité : **70/100**, première note comparable et meilleur score actuel : 70.
  Grille : faits 18/25, clarté 17/20, argument 14/20, continuité 12/15,
  finition 5/10 (HTML non encore inspecté visuellement), absence de surpromesses 4/10.
- Forces : deux angles distincts, produit identifiable, CTA signup correct dans les
  deux HTML ; approbation et archive soutenues par E102/E105/E104.
- Défauts : « la seule façon ... rédiger chaque réponse soi-même » exclut à tort
  relecture et modèles ; « Les questions ... peuvent être rédigées » confond les
  objets. E51 indique un accès au contexte, pas la justesse de la réponse ; E59
  dit « can cite specific facts », pas une citation systématique des passages.
- Tests : 1 256 réussis, Ruff propre. Run complet en 565 s, estimation $7.0135.
  Verdict : correction nécessaire avant validation du cas.
- Hypothèse avant correction : préciser dans les consignes existantes la différence
  entre rédaction et validation, possibilité et garantie, indicateur d'accès et
  preuve de justesse. Ajouter une relecture sémantique acteur/action/objet.
  Aucun nouvel appel modèle. Attendu : promesses bornées, français naturel,
  suppression du faux dilemme, mêmes deux raisons d'essayer.

## 2026-09-19 — reprise après épuisement du quota

- Le run 1283bf9c est déjà collecté : aucun email livré, échec du critique avec
  `Claude Code rate limit`, réinitialisation annoncée le 18 septembre à 20:20 Paris.
  Note qualité : non notée ; meilleur score : non établi pour ce scénario.
- Le service local a été redémarré. La disponibilité réelle du quota sera vérifiée
  par la reprise du scénario, après l'heure de réinitialisation ; aucun défaut
  rédactionnel ne peut être conclu de l'absence de livrables.
- Reprendre les mêmes entrées, sans correction spéculative. Prévision : 26–123
  appels, connaissances réutilisées. L'override reste justifié par le test du
  workflow documenté de brouillon/approbation, sans prétendre valider la demande.
- Évaluer les deux emails livrés avec la grille /100 du skill, conserver le
  score et publier le bilan dans la conversation. Le cas Slack reste validé.

## 2026-09-17 — scenario fixed before launch

- Second scenario uses the existing support audience, French copy and two emails,
  to test transfer beyond a single English Slack announcement. Same brand sources.
- The signup CTA URL is already in the saved offer sheet. No invented product proof
  or customer results are added. Input is saved in input.json.
- Review grid: factual support; audience fit; offer, benefit and action clarity;
  argument specificity; subject/body/CTA continuity; unsupported promises and
  repetition; HTML rendering; status, duration and estimated cost.
- Evidence to inspect includes E93 (inbox integration), E102/E111 (approval queue
  default), E105 (archive boundary) and E39 (no card). These are review references,
  not extra hints added to the campaign request.
- Authorization: user requests autonomous optimization with subscription quota
  until commercially usable outputs, without a total cycle/generation cap.
- Pending: create and launch after assessing the current Slack retest. No run yet.

## Readiness decision before generation

- API permits generation but requires an override: no current V2 recommendation
  establishes product-to-audience fit. Reviewed stored assessment: persona volumes
  and staffing are not established, and shipment tracking requires integrations the
  product does not license. These are review constraints, not facts to invent.
- Recorded override reason: Validate French two-email generation for a plausible support use case supported by documented inbox drafting/approval features E93/E102/E111. No current V2 fit recommendation exists, so this is a generator robustness scenario, not evidence of audience demand. Do not treat the candidate persona counts or live order-status needs as established product fit.
- Product documentation licenses the narrow drafting/approval workflow; reviewing
  whether the generator respects that boundary is useful despite missing market-fit
  validation. No external messages or campaign sends are authorized or performed.
