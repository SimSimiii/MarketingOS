"""Read-only replay of saved Tally inputs; no providers, network or database writes.

Run from backend with .venv/Scripts/python.exe ../docs/reviews/tally-retest-2026-10-16/audience-chain-probe.py
Synthetic mutations are labelled; current normalization is not a regenerated campaign.
"""
import json
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
import tests.conftest  # noqa: E402,F401 -- establish safe test settings before app imports

from app.knowledge.artifacts import KnowledgeArtifacts  # noqa: E402
from app.knowledge.ledger import EvidenceIndex  # noqa: E402
from app.market.audience_discovery import rank_assessment  # noqa: E402
from app.market.audience_research import (  # noqa: E402
    FetchedSource,
    SourceTier,
    _ResearchDraft,
    verify_research,
)
from app.market.demand import AudienceSegment, DemandMap  # noqa: E402
from app.market.relevance import (  # noqa: E402
    INTERPRETATION_VERSION, DossierState, RelevanceDossier, RelevanceStatus,
)
from app.marketing.briefs import CampaignBrief  # noqa: E402
from app.marketing.contract import parse_contract  # noqa: E402
from app.marketing.email_copy import Email  # noqa: E402
from app.marketing.gates import copy_review_gate, evidence_gate  # noqa: E402
from app.marketing.intelligence import (  # noqa: E402
    AudienceResolution,
    CampaignIntelligenceTrace,
    adapt_researched_audience,
    build_campaign_intelligence,
    resolve_audience_research,
)
from app.marketing.pipeline import CampaignRunResult, EmailCampaignPipeline  # noqa: E402
from app.marketing.policy import PRESETS  # noqa: E402
from app.marketing.reader import personas_for  # noqa: E402
from app.marketing.request import CampaignRequest  # noqa: E402
from app.marketing.strategist import Strategist  # noqa: E402
from app.models.market import AudienceResearchRow  # noqa: E402


HERE = Path(__file__).resolve().parent
INPUT = HERE / "inputs"


def rows(name):
    return json.loads((INPUT / f"{name}.json").read_text(encoding="utf-8"))


def fields(brief):
    email = brief.emails[0]
    return {key: getattr(email, key) for key in (
        "single_idea", "felt_need", "status_quo", "why_it_fails", "mechanism",
        "evidence_ids", "must_not_say", "call_to_action", "next_step_value", "next_step_limit",
    )}


campaign = rows("campaign")[0]
execution = rows("executions")[0]
original = execution["result"]
knowledge = KnowledgeArtifacts.model_validate(rows("knowledgeartifactset")[0]["payload"])
research_row = AudienceResearchRow.model_validate(rows("audienceresearchrow")[0])
dossier_row = rows("relevancedossierrow")[0]
dossier = RelevanceDossier.model_validate(dossier_row["payload"])
brief = CampaignBrief.model_validate(original["brief"])
request = CampaignRequest(
    name=campaign["name"], request=campaign["request"],
    product_description=campaign["product_description"], target_market=campaign["target_market"],
)
contract = parse_contract(request.request)
selected = campaign["audience_segment"]
match = resolve_audience_research(selected, [research_row])
stale = dossier.interpretation_version != INTERPRETATION_VERSION
status = RelevanceStatus(
    audience_name=selected,
    status=DossierState.STALE if stale else DossierState.CURRENT,
    stale_reasons=["interpretation_changed"] if stale else [],
    dossier_id=dossier_row["id"], generation_version=dossier_row["generation_version"],
    dossier=dossier,
)
context = build_campaign_intelligence(
    selected_audience=selected, match=match, dossier_status=status, ledger=knowledge.evidence,
)
adapted = adapt_researched_audience(knowledge, match.research, context)
normalized = Strategist(None)._normalize(
    brief.model_copy(deep=True), contract, adapted, context, request.render_context(),
)

# Diagnostic only: how the same argument is handled after a fresh dossier supplies
# the same reference links. This does not pretend the saved old dossier is current.
fresh_equivalent = dossier.model_copy(update={"interpretation_version": INTERPRETATION_VERSION})
fresh_context = build_campaign_intelligence(
    selected_audience=selected, match=match,
    dossier_status=status.model_copy(update={"status": DossierState.CURRENT,
                                            "stale_reasons": [], "dossier": fresh_equivalent}),
    ledger=knowledge.evidence,
)
fresh_normalized = Strategist(None)._normalize(
    brief.model_copy(deep=True), contract, adapted, fresh_context, request.render_context(),
)

# Original quotation, wrapped in a SYNTHETIC fetched document containing exactly
# the captured quotation: tests interpretation acceptance, not a new live fetch.
inverted = match.research.incumbent_behaviour[0]
ref = inverted.evidence[0]
verified = verify_research(
    AudienceSegment(name=selected),
    _ResearchDraft(incumbent_behaviour=[inverted]),
    [FetchedSource(requested_url="https://synthetic.example/quote", final_url="https://synthetic.example/quote",
                   title="Synthetic wrapper around the original captured quotation",
                   tier=SourceTier.BUYER_VOICE, fetched_at=datetime.now(UTC),
                   content_hash=sha256(ref.quote.encode()).hexdigest(), content=ref.quote)],
)
# _corpus gives a single source S1; the original observation used S3.
if not verified.incumbent_behaviour:
    synthetic_observation = inverted.model_copy(update={"evidence": [ref.model_copy(update={"source_id": "S1"})]})
    verified = verify_research(
        AudienceSegment(name=selected), _ResearchDraft(incumbent_behaviour=[synthetic_observation]),
        [FetchedSource(requested_url="https://synthetic.example/quote", final_url="https://synthetic.example/quote",
                       title="Synthetic wrapper around the original captured quotation",
                       tier=SourceTier.BUYER_VOICE, fetched_at=datetime.now(UTC),
                       content_hash=sha256(ref.quote.encode()).hexdigest(), content=ref.quote)],
    )

mutation = brief.model_copy(deep=True)
mutation.emails[0].status_quo = "They export a CSV every morning to keep their workflow running."
mutation.emails[0].why_it_fails = "CSV imports leave the workflow without an owner or a maintained handover."
mutated = Strategist(None)._normalize(mutation, contract, adapted, context, request.render_context())

route_text = "Use Tally's native Make integration by configuring a custom HTTP endpoint."
route_email = Email(position=1, subject="Connect the form", preview_text="", body=route_text,
                    greeting="", call_to_action="", sign_off="")
route_checks = evidence_gate(route_text, EvidenceIndex(knowledge.evidence))
route_review = copy_review_gate(route_email, knowledge.evidence.entries)

# Final receipt fallback visibility, SYNTHETIC unknown brief identity with no
# explicit audience/target override; this is not the selected-audience Tally run.
unknown_brief = brief.model_copy(update={"reader_segment": "", "reader": "Selected audience: not established."})
fallback_trace = CampaignIntelligenceTrace(selected_audience="", audience_resolution_status=AudienceResolution.MISSING)
pipeline = EmailCampaignPipeline(session=None, knowledge=None, policy=PRESETS["fast"])
fallback_report = pipeline._build_report(request, contract, CampaignRunResult(
    artifacts=knowledge, brief=unknown_brief, intelligence=fallback_trace,
))
fallback_persona = personas_for(knowledge.audience, None, panel=False)[0]
effective_fallback = knowledge.audience.primary().name

demand = DemandMap.model_validate(rows("audiencemaprow")[0]["payload"])
mapped = demand.named(selected)
rank_assessment(mapped)
source_code = (ROOT / "backend/app/marketing/pipeline.py").read_text(encoding="utf-8")
output = {
    "scope": "Read-only current-code normalization of original saved Tally artifacts; no regenerated text and no live models.",
    "model_calls": 0,
    "original_execution": {
        "execution_id": execution["id"], "run_status": original.get("run_status"),
        "report_emails": original["report"].get("emails"), "report_notes": original["report"].get("notes"),
    },
    "original_brief": fields(brief),
    "actual_current_replay": {
        "dossier_status": str(status.status), "stale_reasons": status.stale_reasons,
        "fields": fields(normalized), "warnings": context.trace.validation_warnings,
        "redirect_need_retained_with_free_webhook_argument": normalized.emails[0].felt_need == brief.emails[0].felt_need,
        "inverted_status_quo_retained": normalized.emails[0].status_quo == inverted.text,
    },
    "synthetic_fresh_dossier_same_links": {
        "fields": fields(fresh_normalized), "warnings": fresh_context.trace.validation_warnings,
        "unlinked_need_removed": not fresh_normalized.emails[0].felt_need,
        "main_argument_and_mechanism_still_retained": fresh_normalized.emails[0].single_idea == brief.emails[0].single_idea
            and fresh_normalized.emails[0].mechanism == brief.emails[0].mechanism,
        "eligible_slice_original": dossier.recommendation.eligible_subsegment,
        "eligible_slice_in_strategy_context": dossier.recommendation.eligible_subsegment in fresh_context.render_for_strategy(),
    },
    "source_interpretation": {
        "original_claim": inverted.text, "original_quote": ref.quote,
        "synthetic_quote_wrapper_accepts_opposite_interpretation": bool(verified.incumbent_behaviour),
        "original_observation_accepted_as_current_alternative": context.normalized_status_quo(inverted.text),
    },
    "synthetic_unobserved_csv_mutation": {
        "status_quo": mutated.emails[0].status_quo,
        "why_it_fails": mutated.emails[0].why_it_fails,
        "unknown_current_workflow_removed": not mutated.emails[0].status_quo,
        "unsupported_failure_story_remains": bool(mutated.emails[0].why_it_fails),
    },
    "synthetic_native_vs_custom_route": {
        "text": route_text, "evidence_gate_blocking": [issue.detail for issue in route_checks.blocking],
        "all_gate_issues": [issue.detail for issue in [*route_checks.issues, *route_review.issues]],
        "limitation": "No route-consistency signal here; existing subjective readers/critic could still catch it. This is not a claim that a full run would pass.",
    },
    "audience_cards_current_projection": {
        "name": mapped.name, "assessment": mapped.assessment.model_dump(mode="json"),
        "fit_legacy": mapped.fit,
        "pipeline_still_emits_estimated_bite_percentage": "% of them are estimated to bite" in source_code,
        "would_emit": f"Written to {mapped.name} - {round(mapped.fit * 100)}% of them are estimated to bite",
    },
    "synthetic_final_fallback_visibility": {
        "reported_notes": fallback_report.notes, "effective_reader": effective_fallback,
        "reader_persona": fallback_persona,
        "effective_name_in_final_notes": any(effective_fallback in note for note in fallback_report.notes),
        "limitation": "Current selected-audience Tally identity is preserved; this probes the no-explicit-audience fallback path only.",
    },
    "limits": [
        "This does not run strategy, writers, readers or critique with a real model.",
        "Version mismatch only is replayed; full DB readiness and capability-profile changes are outside this script.",
        "The original saved email is unchanged. New code labels/constraints cannot establish that a newly generated Tally email would be convincing.",
    ],
}
target = HERE / "audience-chain-results.json"
target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"output": str(target), "model_calls": 0,
                  "original_run_status": original.get("run_status"),
                  "current_dossier_status": str(status.status),
                  "original_need_retained_actual_stale_path": bool(normalized.emails[0].felt_need),
                  "inverted_source_interpretation_retained": bool(verified.incumbent_behaviour),
                  "native_custom_route_check_issues": len(route_checks.issues) + len(route_review.issues),
                  "csv_status_quo_removed": not mutated.emails[0].status_quo,
                  "csv_failure_story_retained": bool(mutated.emails[0].why_it_fails),
                  "legacy_bite_percentage_still_emitted": output["audience_cards_current_projection"]["pipeline_still_emits_estimated_bite_percentage"]},
                 ensure_ascii=False, indent=2))
