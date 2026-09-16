# Launch retest: audience context and revision selection

The supplied email is asset `ca8fc176cc2945bd89c3c4c914963a38`, execution
`726b48031a2847bfb4096d96b956d289`, campaign `263108f8db044003b3bf2ce5c4089439`.
The saved result was `degraded`, with simulated pull 6/10, `landed=false` and
`rewrites_stopped_helping=true`. Inspection used SQLite in read-only mode.

## What failed

- The brief expanded a generalist considering a Slack assistant into someone who
  had scoped and postponed a build, with nobody owning internal tooling. That
  expansion reached the writer as the reader description. The argument also moved
  from manual document search to a hypothetical custom bot's maintenance burden.
- Two panel variants invented an installed alternative and a prior failed product.
  Those simulated histories encouraged objections about migration and previous
  failures even though they were not established audience facts.
- The critic found the invented team history and ambiguous product introduction.
  It also incorrectly said evidence E22 did not license automatic scaling: the
  saved quotation explicitly says it does. Credibility and source support are
  different questions.
- A rewrite was generated. Its isolated reader assessment reported an audience
  mismatch; the selection code returned before the existing preference comparison.
  The original body therefore survived without a side-by-side decision.
- The revision task instructed the writer to delete a line where the reader
  stopped, even though the critic prompt correctly treated that as a place to
  diagnose, not an automatic deletion instruction.

## Changes

- Reconstruct the downstream reader description from the selected audience and
  explicit user context. Discard the strategist's expanded biography. Preserve
  grounding labels, user-specified audience and confirmed LinkedIn context.
- Label the brief's status quo and limitation as proposed interpretations. Ask
  strategy to keep unsupported histories out of every brief field and to keep
  its limitation attached to the same approach it described.
- Vary reader scrutiny of effort and trust without inventing purchases or tools.
  Readers distinguish a small test from a production deployment or product limit.
- Use the existing blinded preference comparison when relevance assessments
  differ, in both revision selection and candidate runoff. Gates, comprehension
  and revision proof retention still take precedence. Without a usable comparison,
  relevance remains part of the conservative fallback. A comparison win does not
  erase the original warning or automatically make the delivery clean.
- Resolve rewrite feedback against source evidence; a stopping point is not an
  instruction to delete. Critics must distinguish an unsupported extension from
  a supported feature a reader finds unpersuasive.
- Ask writers to translate brief shorthand into natural headlines, advance the
  argument rather than repeat the benefit, and state a requested launch plainly
  without claiming every feature is newly released.

No schema, database or frontend changes. No additional production role, retry or
revision allowance. Disputed drafts can now consume the comparison and subsequent
revisions already covered by the forecast; this can spend more of that allowance
than the old early rejection. Forecast tests remain within their existing bounds.

## Regression material and verification

`backend/eval/fixtures/campaign_quality/slack-launch-retest.json` preserves the
delivered email, the historical revision and five relevant source excerpts. The
revision event did not retain its headline or eyebrow; those are not reconstructed.
Neither version is presented as a good-copy control.

Tests cover the actual pair reaching the comparison, either preference outcome,
the unresolved warning surviving selection, unchanged role counts, a candidate
runoff with disputed relevance, and invented biography staying out of the writer
while explicit user context survives. The critic source test checks that E22 and
the reader's doubt both reach the model; it does not simulate correct judgment.

The full backend suite passed with 1,242 tests before the final runoff test was
added; the affected suite then passed with 57 tests including that new regression.
The full suite reported two existing Starlette/AnyIO deprecation warnings.

The deterministic campaign-quality bench reads the historical pair and returns
`UNSAFE`. Its existing recipient-fact detector also flags the revision's question
about answer quality, and its CTA detector flags both valid action labels. These
lexical findings are not evidence that the revised selection is wrong or that the
historical revision is factually false. The fixture is a reproduction input, not
a passing quality benchmark.

The isolated probe script is `.scratch/email-quality/retest_probe.py`; its output
is `.scratch/email-quality/retest-probe.json`. It uses the historical brief and
reader reports, a bounded source excerpt, and the current critic and revision
prompts. It does not start a campaign or update stored assets. Its model judgments
are observations on one example, not measured conversion performance.
