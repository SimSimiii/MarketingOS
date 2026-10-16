# Pilot hardening — 16 October 2026

## Changes

Earlier emails now reach the writer as drafts, not as sent messages or recipient
activity records. Strategy, drafting and sequence review distinguish a proposed
progression from a confirmed behavioural trigger. Unknown completion calls for
conditional wording and supported creation steps. Explicit user-supplied
purchase or activation context must be retained. The sequence reviewer now sees
the original user request, rather than just its strategic interpretation.

Completed processes with degraded output now expose a review flag in campaign
lists and execution history. Dashboard tasks, campaign filters, brand campaign
lists, history badges and the run header use that distinction. Existing stored
results determine the flag: no migration, model call or rewriting of old emails
is needed. Completed processing is still represented separately from an editorial
warning. A newer clean run clears the campaign's old warning.

The preceding captured-claims correction is recorded separately in
`autonomous-hardening-2026-10-16.md` and commit `1e068ad`.

## Verification and limits

- Final local backend suite: 1,531 passed, two dependency deprecation warnings.
  Ruff passed for `app tests scripts`. API schema checks and disposable database
  migration checks passed. Frontend lint, typecheck and all 17 tests passed.
- Added eight HTTP review-status cases and three recipient-context/routing cases.
- Scripted tests verify propagation and routing, not real model compliance.
- Existing Lambda tests exercise duplicate delivery, replay without rebilling,
  interruption recovery, cancellation, budgets and invocation deadlines.
- Locally observed the saved GPT pilot display “Needs review”, two emails and
  8:45 elapsed time. Its first email renders in the sandboxed HTML preview.
- Downloaded the two-email text file through the browser. The 2,151-byte file
  contains both expected subjects and the intended login destination.
- Completed a local first-use path: created brand
  `64a0ec96-12ff-4212-b51d-a19477b4bfdf`, saved one pasted English source,
  created and edited draft campaign `7068dafc-6fa4-44af-a88f-35a565c50e34`,
  reloaded it, and inspected the forecast. Its execution history is empty;
  creating and editing the brief did not start a generation. Minor English
  copy fixes remove a misleading website-only instruction and an internal role
  name, and use singular “email” for a one-email request.
- Session renewal, temporary sign-in errors and the retry action are English.
- The copy button acknowledged success. Browser clipboard inspection returned
  an empty value, so clipboard contents were not independently verified.
- A second local backend on port 8012 confirmed the saved GPT pilot has
  `last_run_status=completed` and `last_run_needs_review=true`; the saved Claude
  pilot has no warning. The existing backend on port 8000 was left running.
- No new end-to-end campaign or external research was used. After the free
  checks, two standalone writer probes used the subscription CLI (not the API).
  Unknown progress produced an explicit conditional route; confirmed completion
  produced a direct report-review CTA. Both raw outputs and call usage are in
  `recipient-activity-probe-2026-10-16/`. This small sample does not establish
  reliability across products or audience types.
- The unknown-progress probe exposed a quote gate false positive: a documented
  screen title ended with a comma inside its quotation marks. Quote licensing
  now tolerates only terminal sentence punctuation; changed words, internal
  punctuation and unsupported numbers remain checked. Nine regression cases
  cover that boundary. Rechecking the saved probes required no model calls:
  both have zero blocking issues; unknown progress retains one advisory about
  the CTA wording differing from the offer sheet's “Sign in”.

Local browser checks use the current working UI, which also contains pre-existing
visual edits. Only this task's functional changes are staged for deployment.
Build and deployment results are recorded in the accompanying verification JSON.
