"""Free bookkeeping for the reviewed implementation; no model or API calls."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / "state.json"
state = json.loads(path.read_text(encoding="utf-8"))
entries = [
    dict(iteration=2, execution_id="round2/b2b-acquisition/proposed", track="b2b-planned",
         score=86, grid=[25, 18, 15, 12, 7, 9], comparable=False,
         strengths=["Read-only customer repair-stage view is specific and supported", "Sample board is a concrete next step"],
         remaining_defect="Procedural wording can be shortened during ordinary brand review."),
    dict(iteration=3, execution_id="production-direct/activation/direct", track="activation-direct",
         score=88, grid=[25, 18, 16, 13, 7, 9], comparable=False,
         strengths=["Customer relationship and first-folder indexing limit preserved", "Known connect-drive destination; two calls"],
         remaining_defect="Indexing explanation repeats; permissions and providers remain unknown rather than invented."),
    dict(iteration=4, execution_id="production-direct/consumer-offer/direct", track="consumer-direct",
         score=89, grid=[24, 19, 17, 13, 7, 9], comparable=False,
         strengths=["Clear beginner hand-building offer and scope limits", "Coherent programme CTA and verified rendering"],
         remaining_defect="Tighten weekend headline; session details remain unknown."),
]
for entry in entries:
    assert sum(entry["grid"]) == entry["score"]
    entry["evidence"] = "comparisons/" + entry["execution_id"] + "/email-1.txt"
    entry["next_action"] = "Accepted for observed scope after ordinary brand review; no further model calls."
state.update(status="implementation_validated", date="2026-10-18")
state["report"] = "docs/reviews/architecture-quality-implementation-2026-10-18.md"
state["next_action"] = "Implementation complete. Use Automatic for eligible single emails and Planned for sequences or ambiguous actions. Supply real announcement/service facts where material is insufficient."
state["quality_history"] = entries
state["quality_best"] = {"by_track": {
    e["track"]: {k: e[k] for k in ("score", "iteration", "execution_id")} for e in entries
}}
state["quality_verdict"] = "Usable after ordinary brand review in inspected B2B, activation and B2C cases; broader sellability and conversion unproven."
state["validation"] = dict(
    backend_full_passed=1709, backend_warnings=2,
    final_targeted_passed=[70, 75, 19], targeted_counts_overlap=True,
    frontend_passed=27, frontend_typecheck="passed", frontend_lint="passed",
    frontend_build="passed", api_schema="current", ruff="passed",
    migration="applied with verified backup; existing rows unchanged",
    ui="1280/390 px, no overflow; intent and mode payload intercepted; CTA destinations checked",
)
state["evaluation_usage"] = dict(
    provider_attempts=117, reported_tokens=2861510,
    includes=["common dossier", "excluded initial diagnostic", "three-arm comparison",
              "anonymous swapped-order judgments", "two production-direct runs"],
    billing="subscription quota; catalogue estimates are not API charges",
)
state["comparison_limitations"] = [
    "One stochastic output per arm/case; qualitative not statistical.",
    "Tally baseline blocked by subsequently fixed POST gate.",
    "Thin-service proposed contaminated by homonym; excluded, identity guard fixed.",
    "Thin-service judging stopped at 24-attempt ceiling; no retry.",
    "Cart reminder fixture count ambiguous; frozen original preserved.",
    "No full balanced-preset comparison; selected model and limited policies.",
    "Final deterministic corrections have regression coverage; frozen outputs are not all final-code outputs.",
]
path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
note = """
## Completed review — 18 October 2026 (Paris)

Iteration 2, B2B planned: 86/100, first score on its own track (no comparable delta).
Specific read-only customer view and sample-board action; remaining procedural wording
is an ordinary edit. Best on track 86, round2/b2b-acquisition/proposed.

Iteration 3, activation direct: 88/100, first score on separate track. Customer
relationship, first-folder threshold and action URL preserved; remove repeated
indexing explanation at ordinary brand review. Unknown permissions/providers stay
unknown. Best on track 88, production-direct/activation/direct.

Iteration 4, B2C direct: 89/100, first score on separate track. Clear beginner offer,
hand building without wheel, post-firing collection and programme link. Tighten the
weekend headline. Best on track 89, production-direct/consumer-offer/direct.

These are coordinator judgments using the unchanged 25/20/20/15/10/10 grid, not
customer measurements. HTML inspected at 1280/390 px and CTA URLs verified. Direct
reader scores remain 6/10 and statuses degraded; they are not overridden. Outputs
are usable after ordinary brand review in the observed scope. Historical Tally 76
is non-comparable. Universal sellability and conversion remain unproven.

Validation: full suite 1709 passed, 2 dependency warnings; final targeted suites
70,75,19 passed with overlap. Frontend 27 tests, lint, types and static build;
Ruff/API schema; temporary migration and verified local migration passed. No test
pass is counted as a quality gain. The same old Tally email has 0 attributions versus
its historical 8, without editing history.

Total recorded provider attempts 117 and reported tokens 2861510 includes common
dossier, excluded stale-context diagnostic, three-arm generations, anonymous
judgments and two production-direct checks. Thin-service hit its 24-attempt ceiling
during judging; remaining ballot not bought. All snapshots retained.

Implementation complete for the agreed architecture scope. Automatic requires a
single explicit job and unambiguous documented action destination. Planned remains
for sequences and ambiguous/unsupported jobs. Supplied domains anchor material
recovery, including redirect checks. Remaining source gaps require actual brand
facts. No emails sent, production deployment, branch switch or commit.
Final report: docs/reviews/architecture-quality-implementation-2026-10-18.md.
"""
journal = root / "journal.md"
current = journal.read_text(encoding="utf-8")
if "## Completed review — 18 October 2026 (Paris)" not in current:
    journal.write_text(current + note, encoding="utf-8")
print("Updated final case state and journal.")
