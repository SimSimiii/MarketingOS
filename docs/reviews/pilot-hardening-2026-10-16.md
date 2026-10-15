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

- Added eight HTTP review-status cases and three recipient-context/routing cases.
- Scripted tests verify propagation and routing, not real model compliance.
- Existing Lambda tests exercise duplicate delivery, replay without rebilling,
  interruption recovery, cancellation, budgets and invocation deadlines.
- Locally observed the saved GPT pilot display “Needs review”, two emails and
  8:45 elapsed time. Its first email renders in the sandboxed HTML preview.
- Downloaded the two-email text file through the browser. The 2,151-byte file
  contains both expected subjects and the intended login destination.
- The copy button acknowledged success. Browser clipboard inspection returned
  an empty value, so clipboard contents were not independently verified.
- A second local backend on port 8012 confirmed the saved GPT pilot has
  `last_run_status=completed` and `last_run_needs_review=true`; the saved Claude
  pilot has no warning. The existing backend on port 8000 was left running.
- No new real campaign, external research or provider request was used for this
  work. No claim that the new prompt reliably fixes every model output follows
  from scripted-provider tests.

Local browser checks use the current working UI, which also contains pre-existing
visual edits. Only this task's functional changes are staged for deployment.
Build and deployment results are recorded in the accompanying verification JSON.
