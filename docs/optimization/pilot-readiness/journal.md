# Readiness correction journal

## 2026-10-05 — verified price context

Iteration 6 still labels the Pro Tech Toolkit price as absent. The offer sheet
contains $79.95 and the full ledger licenses it as E556, but the per-email slice
can omit it. The critic receives only that slice, and the writer's knowledge
explicitly prohibits facts outside it. Prompt changes alone did not fix this.

Hypothesis: when campaign orientation explicitly names a priced offer, include
its matching PRICE evidence in the bounded writer/critic slice as shared decision
context. Match both the exact offer name and its recorded price in the ledger;
never synthesize a fact from the offer sheet. Keep excluded ids excluded and the
15-entry cap. Preserve assigned argument evidence first. No new model call.
Regress multi-product confusion, forbidden evidence and missing ledger proof,
then replay the saved 910-fact case for E556. A completed real sequence is still
required before declaring iFixit sellable. Cancellation of iteration 6 is pending;
the runner retains exclusive ownership of its case state/journal until terminal.

## 2026-10-06 — verification and default configuration

Iteration 6 is terminal and recorded in its case journal: 2/3 retained, unscored.
The price replay passes on knowledge v3 (913 facts); E556 reaches all three slots,
with the product's own source preferred over catalogue/sidebar duplicates.
1401 backend tests pass after this correction, Ruff is clean. Iteration 7 is
running under OpenAI on the explicitly labelled recovered-source-v3 track.
The versioned Settings default and .env.example now also use OpenAI, matching
the already configured local environment and campaign presets. README's obsolete
“only Claude implemented” statement is corrected. Full tests are rerun for this
last configuration change. No provider billing mode or secret filter changed.

UI observation: draft cards can appear after a cold read whose verdict is weak.
The live page's “passed a cold read” wording therefore overstates approval.
Change it to “reviewed drafts” and ask the user to check feedback before use;
this is a label correction only, without any threshold or pipeline change.

## Fixed CTA destination — diagnosis before correction

Iteration 7's second slot asks to review a flex-extension guide, although the
user's fixed button points to the product page. `_recovered_next_step` can
replace a supported planned action with the recovered fact's source URL even
when the user chose a different destination. Writers also receive the freeform
request without the separately saved CTA URL; critics lack that fixed URL.
Hypothesis: preserve the planned action when the user fixed the destination,
carry that destination from the request into the stored campaign brief in code,
and show it explicitly to writers and critics. Evidence sources still license
claims; they do not choose the user's button. No new model call or disabled gate.
Regress primary and alternative recovered arguments plus writer/critic context;
review the actual rendered link and label in the following real sequence.

Iteration 7 terminal also diagnosed absence of a repair-to-tool decision aid or
smaller-kit comparison as missing material for a price/contents inspection CTA.
Neither resource is promised by that limited action. Keep genuine material gaps
binding when a claimed repair use, comparison or promised resource needs proof;
otherwise diagnose the unpersuasive value argument as copy/argument. This does
not approve weak copy: the cold panel and independent editorial review still
judge whether it earns the next step. Preserve all factual gates and never invent
the aid or comparison. Validate this routing clarification in iteration 8.

## 6 octobre — exceptions de garantie masquées par la sélection de preuves
Run iFixit 8 terminé (3/3, séquence revue), mais le troisième email dit que seuls les trois Opening Tools sont exclus. R15–R18 documentent aussi picks, spudgers et capuchon : le brief a sélectionné R14 et la règle générale R19, masquant les autres exceptions. Hypothèse : conserver les limites de garantie de la même source que les preuves assignées, dans la même enveloppe de 15 faits, et interdire de transformer des exemples en liste exhaustive. Vérifier par régression scriptée puis mesure ciblée du rédacteur/critique ; ne pas relancer une séquence entière pour cette seule question. Aucun verdict vendable pour le run 8.

L’aperçu final affiche aussi une conclusion excessive de substantiation : zéro correspondance est décrit comme aucune preuve vérifiable et aucune invention. Le texte 2 paraphrase pourtant un guide réel. Corriger le reçu pour décrire la limite du rapprochement automatique et inviter à la revue, sans modifier l’algorithme.
