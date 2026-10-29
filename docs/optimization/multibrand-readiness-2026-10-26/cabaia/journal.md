# CABAIA — validation multi-marques, 26 octobre 2026

Protocole fixé avant essais : ../protocol.json. Une seule homepage, https://www.cabaia.fr/. Scénario ecommerce, langue fr. Aucun ajout de fait produit, de documentation ou de CTA. Première audience exacte, échecs conservés. Baseline avant correction. Aucun envoi.

## Import baseline
8 documents, 21846 mots. Les pages produit conservent un long panier, recommandations, auth et chrome avant la description. Risque de confusion entre prix/SKU ; à vérifier dans la compilation, sans correction préalable.

## Extraction epoch1
Normal homepage-only re-import, 8 documents. 242,409 → 149,582 characters (38.3% less). No source links injected. Product-source code frozen in ../code-manifest-epoch1.json. Initial imports retained.

## Quota checkpoint
Claude Code returned a session-limit failure during the systeme.io corrected compilation, reset reported as 05:20 Europe/Paris. No additional paid steps started after this refusal. All downstream stages and emails remain unvalidated; do not infer success from imports or old artifacts. No automatic resumption scheduled.

## Knowledge v2 review
385 facts,15 calls,777.34seconds. E11745EUR price, E119 dated delivery estimate, E124 lifetime for lunch bag, and limited collaboration2-year conditions preserved separately. Structured plans empty and gap falsely says no price; baseline compilation7/10. Catalogue7.5/10: current verified product atoms but repetitive cross-sell assortment. Local-only A2 replay removes false gap with identical ledger/offer/version; no model calls or DB writes. Live server remains epoch1 after restart denial.

## OpenAI scan review
5 finished GPT calls.4/6 alternatives profiled (Eastpak/Rains/Hindbag plus keeping/repairing owned bag as status quo); Fjallraven and UNIQLO unreadable and explicit unverified. Quotes source-scoped; doubtful facts dropped. Rains collection counts not mistaken for product waterproof claims or full price range.0 documented exclusive differences,30 unmatched captures unknown, no unsupported superiority. Competitors7.5/10 (partial coverage); positioning8/10 (conservative useful comparison including status quo). Same Knowledge v2 after deterministic gap refresh has no false price gap in current-code API; no facts changed. Next map pending because global two-job cap: systeme map and Papier compilation active.

## Audience research failure and normal readiness
Map7 candidates but first has no external evidence/findability/venue in fetched corpus; all remain hypotheses. Map5/10 (one readable page, weak actionable support). Exact first commuter selected, researchable=true. Research locating31.7s completed1 GPT call;10 URLs no useful readable text; no research row, no dossier. Research2/10 as a workflow outcome, not a claim model hallucinated facts. Advice DISCOVERY_ONLY/override_required=true. No generate_anyway. Preserve failure, no easier audience.

## Bounded source-selection vendor control
GPT locating call found10 URLs but local fetch returned no useful text; no source URLs were retained in an auditable research row. Compare one explicit Claude Sonnet research job with identical first commuter audience and same Python reader on27Oct. No manual URLs, no easier segment, no global model change. This is a practical non-strict control: live search/time/provider can change selected sources, so neither outcome establishes universal model superiority. Retain GPT failure in denominator and compare job counters/durations/source coverage.

## Upstream review 27 October
Sonnet control completed: 3 readable sources, four single-source historical problems, 8 dropped claims. GPT previous zero-source failure preserved. Dossier limits combined lunch/laptop/bottle capacity and does not claim anti-discoloration. GO_NARROW Office commuters, not validated full one-bag result.
Scores: {'recherche': 6, 'dossier': 8}. No email scored at this checkpoint.

## Email 1 — non noté, aucune livraison
Run ef8e19b8 : 19 appels, échec déterministe après réparation, zéro asset. « 37 » sans preuve reste bloqué à juste titre ; le texte final refusé n’est pas exposé dans les artefacts, ne pas inventer son contexte. Faux positif reproductible : spam_gate ne reçoit pas le nom documenté de la société, interdit CABAIA jusque dans la signature tandis que clarity exige de nommer la marque. Hypothèse A7 : exempter uniquement les occurrences exactes du nom canonique transmis par BusinessProfile, avec frontières de mot ; conserver les autres capitales et les contrôles numériques. Tests gratuits contrastifs puis même campagne. Aucune note email fabriquée sur un asset absent.

## Email 2 — 71/100, à revoir
Exact work-bag specs and return scope; no invented combined capacity; Canonical brand no longer blocks, actual desktop/mobile render clean. Défauts : Subject asks decisive combined-load question the evidence cannot answer; CTA says product sheet but actual URL is homepage; Optional official material recovery failed on usage limit; no new evidence obtained. Meilleur comparable : 71. Run 8c17fb09-c07e-4537-8a07-7cf9e9988124, vrais assets/rendus conservés.

## Bilan de ce lot
Meilleur email 71/100 ; cas complet non validé. Dernier correctif CTA déterministe : tests, pas de nouvelle mesure de qualité email.1972 tests backend et Ruff passent. Worker arrêté proprement, serveur principal rechargé après sauvegarde et absence de jobs. Pas de nouvel essai inchangé : les lacunes amont/décisionnelles restent explicites dans le rapport global.

## Retest A20 — 29 octobre
Nouvel email non noté : le dossier courant exige un override, non utilisé. Ancien meilleur71 reste historique ; aucun nouvel asset acheté. La recherche v2 apporte7sources/6problèmes, mais l'usage simultané ordinateur+repas+gourde n'est pas établi pour un modèle actuel. Les refus de lecture des collections restent visibles. Le dossier distingue composants et besoin combiné ; il ajoute aussi deux préférences secondaires qu'il ne faut pas traiter comme exigences universelles. Voir retest-A20-review.json. Cas non passant ; prochaine phase : vérification officielle ciblée, sans promettre la compatibilité.

## Dossier courant A24 / interprétation16
v3 besoin principal partial : cumul ordinateur/déjeuner/bouteille non établi dans un même sac. Aucune nouvelle génération ; historique71 conservé. Voir dossier-review-A24.json. A25 testé localement, retest réel différé car activation rejetée automatiquement.
