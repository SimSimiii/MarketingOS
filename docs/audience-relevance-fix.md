# Diagnostic et correction de la pertinence audience

## Causes confirmées dans le code (état du 8 septembre 2026)

Le dépôt était propre au début; aucun changement de branche ou de worktree.
README.md et docs/external-review-brief.md ont été lus, puis confrontés au code.

- Sélection → découverte : `AudienceSegment.as_segment` dans `market/demand.py`
  copie `who` dans `Segment.situation`. Cette description est une hypothèse de
  découverte, pas une biographie attestée du destinataire.
- Recherche → campagne : `marketing/intelligence.py` résout les recherches persistées
  pour cette audience. L'adaptation remplaçait le nom sélectionné par le nom de la
  recherche et copiait la situation en texte seul, perdant grounding et références.
  En absence de situation recherchée, elle conserve le fallback compilé/découvert.
- Produit/audience → stratégie : `Strategist.build` transmet déjà le dossier et la
  recherche. Les dossiers actuels influencent orientation, preuves et objections;
  les dossiers périmés sont signalés et consultatifs. Ce câblage n'était pas absent.
  Les observations transmises conservaient le grounding, mais pas leurs références.
- Stratégie → écriture : les briefs et le segment adapté atteignent le writer. Des
  champs comme felt_need/status_quo orientent fortement vers un vécu actuel. Le
  nom choisi était aussi susceptible d'être remplacé par le choix du Strategist.
- Profil → lecteur : `personas_for` concaténait toujours nom et situation. L'audit
  historique était donc encore exact sur ce point. Aucun brief commercial n'est
  fourni à BlindReader; lui fournir le dossier complet aurait créé une fuite.
  Les deux variantes ajoutaient un scénario de scepticisme sans le nommer comme tel.
- Réécriture → sélection : le lecteur avait un veto de compréhension, mais aucun
  verdict de reconnaissance de situation. Pull, approbation du critique, preuves et
  duel pouvaient donc sélectionner une copie fluide sur une prémisse déplacée.
  Le duel pouvait aussi passer outre la compréhension; les comparaisons sont alignées.
- Rapport : `pipeline._build_report` choisissait `assess(...).asks[0]`, indépendamment
  des obstacles des lecteurs. Le compilateur crée la question des témoignages quand
  cette preuve manque. Cela explique le mécanisme de recommandation observé.
- Chiffres : opens_in_100/clicks_in_100 sont émis par le modèle; une table Python
  transforme les clics simulés en pull. Aucun résultat d'envoi réel ne les calibre.

Le texte fourni ne permet pas d'attribuer sa description précise à une ligne de
recherche ou de découverte historique : le snapshot d'exécution n'a pas été identifié.
On ne peut pas confirmer quels templates ou quelles données ont produit cet email.
L'applicabilité sémantique des citations n'est pas prouvée par leur vérification textuelle.

## Comportement modifié

Le nom sélectionné est conservé, la situation garde son grounding et ses références,
et les problèmes documentés restent dans le profil indépendant. Les instructions de
stratégie, écriture et critique distinguent vécu établi, risque et hypothèse; une
source sur quelques membres n'établit ni universalité ni vécu du destinataire.
Les apprentissages antérieurs sont explicitement des simulations, pas des faits audience.

Le lecteur renseigne situation_matches (vrai/faux/inconnu), relevance_feedback,
assumed_experiences et problem_now, séparément de compréhension et pull. Un décalage
substantiel signalé empêche landed, alimente le feedback de réécriture et intervient
avant la préférence stylistique dans les comparaisons. Les protections de preuves,
gates et budgets restent en place. Un décalage non résolu est livré avec réserve.
Les anciens rapports sans ces champs restent lisibles et ne deviennent pas des échecs.

La recommandation privilégie le décalage puis les obstacles au CTA des lectures finales.
Elle demande de consulter les informations vérifiées ou de combler la lacune précise;
les attentes du lecteur ne sont jamais présentées comme des preuves produit. La critique
et l'écriture peuvent utiliser une documentation vérifiée déjà disponible au lieu d'une
FAQ. Aucun nouveau modèle, agent, table ou lancement automatique de recherche.

L'interface et le rendu des lectures nomment les simulations IA et les notes non
calibrées. Les fréquences sont conservées dans les données historiques mais retirées
comme prévisions de l'affichage. Les vieux textes déjà persistés ne sont pas réécrits.

## Comparaison sémantique reproductible

Depuis `backend/` :

```powershell
.venv/Scripts/python.exe -m app.evaluation.relevance_probe --dry-run
.venv/Scripts/python.exe -m app.evaluation.relevance_probe --run --out eval/relevance-after.json
```

Le premier appel est gratuit. Le second utilise les mêmes ModelSession, routage et
BlindReader que le pipeline, pour trois lectures (quota réel), sans campagne ni recherche.
`relevance_cases.json` contient le texte fourni, une variante de premier lancement et
une audience explicitement en production. Les capacités de la variante sont des hypothèses
autorisées pour cette fixture, tirées du cas fourni, pas une vérification actuelle d'orqAgent.
Ne pas réutiliser cette fixture comme Evidence Ledger produit.

Examiner les trois sorties ensemble : le décalage de situation devrait être expliqué
sur le texte observé pour la première feature; la variante adaptée devrait moins
présupposer de vécu; le même reporting ne devrait pas être rejeté automatiquement pour
l'audience en production. Les objections techniques peuvent subsister dans les trois.
Comparer les raisons et les expériences supposées, pas une formulation ou un score exact.
Conserver plusieurs sorties si l'on veut mesurer la variance. Un seul passage ne calibre
ni le jugement ni les taux commerciaux. Le probe ne valide pas la génération complète.

Pour régénérer la campagne réelle, reprendre la même marque, la sélection exacte, la
requête, les sources, le preset et les modèles depuis l'interface, sans relancer la
recherche. Conserver auparavant le rapport et les versions des artifacts/dossier pour
comparer les prémisses, citations, objections et réserves. La requête originale et les
identifiants d'exécution manquent dans le cas fourni : une reproduction strictement
identique de ce run n'est donc pas possible à partir du texte seul.

## Limites

Les tests scriptés prouvent le passage des données, les priorités et la compatibilité,
pas une amélioration du jugement. Aucun appel réel n'a été exécuté pour cette correction.
Le classement des obstacles reste déterministe : fréquence des réponses identiques,
puis ordre du panel; il ne regroupe pas sémantiquement les paraphrases. Le conseil
oriente vers la source ou la lacune, mais ne vérifie pas automatiquement un nouveau document.
Un seul signal explicite de décalage substantiel impose une réserve; cela peut être
conservateur avec les variantes de scepticisme. L'incertitude n'est pas un veto.
Les données audience anciennes peuvent toujours être inexactes et leur adéquation reste
une responsabilité du modèle. Les instructions améliorent ce contrôle sans le garantir.

## Vérifications exécutées

- Suite backend complète : 1091 tests passent (76,48 s), deux avertissements de dépréciation.
- Dernier passage ciblé lecteur/pertinence/contexte audience : 45 tests passent.
- Frontend : `npm run lint` et `npx tsc --noEmit` passent.
- Ruff `app tests` : uniquement le SIM102 préexistant dans `app/ai/openai_provider.py`.
- `git diff --check` : aucune erreur de whitespace.
- `relevance_probe --dry-run` : succès, aucun appel réel.
- Pas de vérification visuelle dans un navigateur ni de comparaison avec modèles réels.

## Suivi : lectures réelles et frontière des sources

Deux passages réels supplémentaires ont été exécutés (six lectures au total), conservés
séparément dans `backend/eval/relevance-source-boundary.json` et
`backend/eval/relevance-source-boundary-final.json`. Le résultat utilisateur précédent
`relevance-after.json` est intact.

Le prompt demande désormais de distinguer profil, email et inconnues dans tous les champs,
y compris les objections. Un défaut du probe a aussi été corrigé : les textes étaient
placés dans le body avec CTA et signature vides, générant une flèche artificielle. Les
champs sont désormais renseignés. Un test couvre ce rendu. Ce changement signifie que le
dernier passage n'isole pas l'effet du prompt de celui du rendu : ne pas comparer les scores
comme une expérience contrôlée.

Résultat sémantique NON VALIDÉ : les nouvelles consignes ne suffisent pas. Sur le passage
final, le texte initial obtient situation_matches=null pour la première feature, tandis que
biggest_doubt invente encore une absence d'incidents. Sur l'audience production, le lecteur
classe comme profile-supported des exports manuels et des réparations après incidents qui
ne sont pas spécifiés. La variante adaptée reste reconnue comme pertinente mais les obstacles
produit subsistent. Les verdicts de production varient entre les passages. Aucun de ces
résultats ne constitue une validation commerciale ni une preuve de fiabilité du juge.

Une correction plus forte devrait séparer explicitement les prémisses et leurs citations
source dans le schéma de la lecture existante, puis contrôler leur traçabilité, sans ajouter
un rôle ou une recherche. Même une citation textuellement valide ne prouverait pas son
implication sémantique : ce point demanderait une nouvelle comparaison ciblée. Le présent
suivi ne prétend pas avoir résolu cette limite.
