# Campaign Quality Evaluation V1

Campaign Quality Evaluation answers two separate questions about generated email drafts:

1. Is the email factually and evidentially safe?
2. Is it commercially strong and readable for the intended buyer?

The first pass is deterministic, repeatable, and free of model calls. The second pass is an
explicitly opt-in, blind model review under fixed buyer personas. Evaluation only reads campaign
inputs and persisted generation snapshots; it never rewrites or publishes a campaign.

## Run the deterministic evaluation

Run commands from `backend`. `--campaign` accepts a bundled fixture name, a JSON fixture path, or
a campaign UUID in the configured application database. Repeat it to evaluate several cases.

```bash
python -m app.evaluation.campaign_quality_bench \
  --campaign strong-grounded \
  --campaign generic-safe \
  --out eval/campaign-quality
```

For an existing generated campaign:

```bash
python -m app.evaluation.campaign_quality_bench \
  --campaign <campaign-uuid> \
  --out eval/campaign-quality
```

Each case produces a JSON report for automation and a Markdown report for review. Both include
individual checks, offending text, applicable evidence or rule IDs, a verdict, and prioritized
revisions. The three verdicts are `SAFE_TO_REVIEW`, `NEEDS_REVISION`, and `UNSAFE`.

Database campaigns are evaluated against their persisted final email assets, the exact stored
knowledge version when available, and the V2 `recommendation_snapshot` used for generation. The
snapshot's allowed claims and evidence form the campaign-safe contract; its prohibited claims and
capabilities remain prohibited. Evidence the snapshot's claim contract merely *withheld* - true,
and not spent by this campaign - is not reported as prohibited; it is simply absent from the
campaign-safe contract, so `CQ-SAF-004` and `CQ-SAF-005` still catch a draft that spends it. The
loader does not substitute newer evidence when the exact historical version is missing.

## Deterministic rules

| ID | Check |
| --- | --- |
| `CQ-SAF-001` | Forbidden capabilities and campaign- or draft-specific forbidden claims |
| `CQ-SAF-002` | High-risk unsupported promises, including telephony, HIPAA, backend replacement, and architecture claims |
| `CQ-SAF-003` | Target-company claims without supplied company evidence |
| `CQ-SAF-004` | Product claims outside the explicit campaign-safe claim contract |
| `CQ-SAF-005` | Unsupported numerical, quoted, or linked claims |
| `CQ-COM-001` | Missing or weak CTA |
| `CQ-COM-002` | Contradictions across subject, preview, and body |
| `CQ-COM-003` | Excessive claim density |
| `CQ-COM-004` | Repeated product facts, numbers, or evidence references |
| `CQ-COM-005` | Structural, placeholder, stock-phrase, and spam-warning gates |

## Opt in to live commercial review

`--live` is the only CLI mode that constructs a model provider. It prints an estimated call count
before starting and **spends configured model quota**. The evaluator normally makes one structured
model call per buyer persona. Tests mock this provider and never require live calls.

```bash
python -m app.evaluation.campaign_quality_bench \
  --campaign blind-comparison \
  --out eval/campaign-quality \
  --live
```

An optional configured model slug can override the balanced-tier route:

```bash
python -m app.evaluation.campaign_quality_bench \
  --campaign <campaign-uuid> \
  --out eval/campaign-quality \
  --live \
  --model <configured-model-slug>
```

Configure the same provider used by the backend:

- Claude CLI: set `AI_PROVIDER=claude`, optionally set `ANTHROPIC_MODEL`, and authenticate the
  Claude CLI as described in `.env.example`.
- Codex CLI: set `AI_PROVIDER=openai`, optionally set `OPENAI_MODEL`, and authenticate with
  `codex login`.
- If a CLI is not on `PATH`, set `CLAUDE_CLI_PATH` or `CODEX_CLI_PATH`.

When multiple drafts are supplied, the live evaluator exposes only anonymous labels, rotates their
order between personas, and maps results back to draft IDs after scoring. Its 1–5 rubric covers
audience/company specificity, problem relevance, credibility, value clarity, differentiation,
readability, CTA quality, likely interest, and spammy or generic-AI tone.

## Regression fixtures and tests

Fixtures live in `eval/fixtures/campaign_quality`:

- `strong-grounded`
- `generic-safe`
- `false-voice`
- `false-backend-replacement`
- `invented-company-problem`
- `blind-comparison` (two drafts and two buyer personas)

Run the focused tests from `backend`:

```bash
python -m pytest -q tests/evaluation/test_campaign_quality.py
```
