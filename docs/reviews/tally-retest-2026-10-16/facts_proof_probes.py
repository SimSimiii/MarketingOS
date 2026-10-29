"""Read-only replay of the exported Tally artifacts; no network or model calls.

Run from the repository with backend/.venv/Scripts/python.exe. Acceptance
observations deliberately live outside the normal regression suite: a missing
guard is reported as missing, without changing product code or old assertions.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
import tests.conftest  # noqa: E402,F401 - set test settings before app imports

from app.knowledge.artifacts import KnowledgeArtifacts  # noqa: E402
from app.knowledge.compiler import find_gaps  # noqa: E402
from app.knowledge.corpus import Document, SourceCorpus  # noqa: E402
from app.knowledge.ledger import EvidenceContext, EvidenceIndex, EvidenceLedger  # noqa: E402
from app.market.proof import ProofCandidate  # noqa: E402
from app.market.store import merge_proof  # noqa: E402
from app.marketing.gates import evidence_gate  # noqa: E402
from app.marketing.preflight import assess  # noqa: E402
from app.marketing.reader import BlindRead  # noqa: E402
from app.marketing.report import CampaignReport  # noqa: E402
from app.schemas.market import ProofCandidateRead  # noqa: E402

FOLDER = Path(__file__).resolve().parent


def read(name):
    return json.loads((FOLDER / "inputs" / f"{name}.json").read_text(encoding="utf-8"))


def gate_output(text, index):
    report = evidence_gate(text, index)
    return {
        "text": text,
        "blocking": [item.detail for item in report.blocking],
        "advisory": [item.detail for item in report.advisory],
    }


def main():
    stored = read("knowledgeartifactset")[-1]
    artifacts = KnowledgeArtifacts.model_validate(stored["payload"])
    unique = {row["content"]: row for row in reversed(read("knowledgedocument"))}
    corpus = SourceCorpus.from_documents([
        Document(id=row["id"], title=row["title"], content=row["content"],
                 source=row.get("source_url") or row["title"], source_type=row["source_type"])
        for row in reversed(list(unique.values()))
    ])
    index = EvidenceIndex(artifacts.evidence, corpus.text)
    asset = next(row for row in read("assets") if row["title"] == "Put Tally before your automation")
    opening = "Tally is now available as the form front end for your next automation."
    probes = []

    def check(name, text, expectation, criterion):
        observed = gate_output(text, index)
        probes.append({"id": name, "expectation": expectation,
                       "result": "corrected" if criterion(observed) else "missing",
                       "observed": observed})

    check("exact_now_available", opening, "Caution about unsubstantiated novelty",
          lambda value: bool(value["advisory"]))
    check("monthly_amount_reused_as_yearly", "Tally Pro costs $29/year.",
          "Reject the incompatible billing period", lambda value: bool(value["blocking"]))
    check("feature_price_vs_subscription", "Custom domains cost $29/month.",
          "Flag treating the plan amount as an independent feature price",
          lambda value: bool(value["blocking"] or value["advisory"]))
    check("vendor_comparison_without_attribution", "Typeform costs $39/month.",
          "Flag an unqualified rival price licensed by Tally's comparison pages",
          lambda value: bool(value["blocking"] or value["advisory"]))
    check("customer_result_transferred_to_integrations",
          "Tally gets you 30%+ response rates with Make, Zapier or n8n.",
          "Flag transferring Flylighter's feedback result into a general automation result",
          lambda value: bool(value["blocking"] or value["advisory"]))
    check("customer_result_generic_you_will", "You will increase your response rate to 30%.",
          "Flag generalizing the saved customer result even when legacy context is absent",
          lambda value: bool(value["blocking"] or value["advisory"]))

    functional = artifacts.model_copy(deep=True)
    functional.evidence = EvidenceLedger(entries=[artifacts.evidence.get("E32")])
    functional.gaps = find_gaps(functional)
    posture = assess(functional)
    probes.append({
        "id": "documented_function_without_testimonial",
        "expectation": "Allow the documented webhook function without requiring a testimonial",
        "result": "corrected" if not posture.nothing_to_argue_from else "missing",
        "observed": {"has_proof": posture.has_proof, "has_checkable": posture.has_checkable,
                     "nothing_to_argue_from": posture.nothing_to_argue_from},
    })
    missing_context = sum(entry.context is None for entry in artifacts.evidence.entries)
    context_unknown_visible = "context not recorded" in artifacts.evidence.render()
    probes.append({
        "id": "legacy_context_explicitly_unknown",
        "expectation": "Keep legacy context unknown and visible instead of silently certifying it",
        "result": "corrected" if context_unknown_visible else "missing",
        "observed": {"missing_context": missing_context, "total_entries": len(artifacts.evidence.entries),
                     "unknown_context_visible": context_unknown_visible},
    })

    customer = artifacts.evidence.get("E265").model_copy(deep=True)
    customer.context = EvidenceContext(subject="Thomas Frank / Flylighter",
                                       claim_scope="customer_outcome",
                                       conditions="feedback collection for Flylighter")
    enriched_index = EvidenceIndex(EvidenceLedger(entries=[customer]))
    controls = {
        "synthetic_novelty_wording_control": gate_output(
            "We just launched our new feature: webhooks.", index),
        "synthetic_metadata_added_to_real_customer_quote": {
            "metadata_is_synthetic_not_a_recompile": True,
            "covered_wording": gate_output("You will increase your response rate to 30%.", enriched_index),
            "uncovered_wording": gate_output(
                "Tally gets you 30%+ response rates with Make, Zapier or n8n.", enriched_index),
        },
    }
    proof_rows = read("proofcandidaterow")
    proof_reads = [ProofCandidateRead.model_validate(row) for row in proof_rows]
    synthetic_added = ProofCandidate.model_validate(proof_rows[0]).as_evidence("P_RETEST_SYNTHETIC")
    merged_in_memory = merge_proof(artifacts, [synthetic_added])
    saved_result = read("executions")[0]["result"]
    rendered_report = CampaignReport.model_validate(saved_result["report"]).render()
    simulated = BlindRead(opens_in_100=20, clicks_in_100=6)
    approved = [item for item in proof_reads if item.status == "approved"]
    output = {
        "scope": "Saved Tally campaign, exact 380-entry ledger and all 11 exported source documents; no current web claims",
        "model_calls": 0, "network_calls": 0, "source_database_writes": 0,
        "source_documents": len(corpus.documents), "source_corpus_chars": len(corpus.text),
        "knowledge_version": stored["version"], "asset_id": asset["id"],
        "exact_asset_evidence_check": gate_output(asset["content"], index),
        "acceptance_counts": {"corrected": sum(item["result"] == "corrected" for item in probes),
                              "missing": sum(item["result"] == "missing" for item in probes)},
        "acceptance_probes": probes, "controls": controls,
        "source_passages": [{"id": entry.id, "claim": entry.claim, "quote": entry.verbatim,
                             "source": entry.source, "context": None if entry.context is None else entry.context.model_dump()}
                            for entry in [artifacts.evidence.get(key) for key in ("E21", "E32", "E33", "E68", "E102", "E241", "E265")]],
        "proof_view": {
            "saved_candidates": len(proof_reads), "approved_candidates": len(approved),
            "legacy_candidates_not_checked": sum(item.verification_status == "not_checked" for item in proof_reads),
            "known_customer_result_in_corpus": artifacts.evidence.get("E265").claim,
            "transport_confidence_still_exists": all(hasattr(item, "confidence") for item in proof_reads),
            "synthetic_in_memory_approval_probe": {
                "scenario": "First saved pending candidate approved only in a temporary object; no real approval or database write",
                "before": len(artifacts.evidence.entries),
                "after": len(merged_in_memory.evidence.entries),
                "known_E265_retained": merged_in_memory.evidence.get("E265") is not None,
                "added_proof_appended": merged_in_memory.evidence.entries[-1].id == "P_RETEST_SYNTHETIC",
                "unverified_legacy_strength": synthetic_added.strength,
                "automatic_verification": synthetic_added.context.verification,
            },
            "code_findings": [
                "ProofHunter.hunt receives business, website, limit; no campaign argument or audience.",
                "MarketService.artifacts_for merges known and human-approved new evidence; merge_proof appends without relevance ranking.",
                "Relevance dossier inputs consume the merged ledger and its UI shows ranked_relevance; rebuilding can rank approved proof for an audience.",
                "ProofInbox receives candidate rows only, showing pending cards and approved count; corpus E265 is not part of that view.",
                "Proof badges show explicit quote-check status; identity and use-for-this-argument are not independent validated status fields.",
                "The empty-hunt fallback in _run_hunt still asserts nobody outside the site mentions the brand if no note is returned.",
            ],
        },
        "simulated_metrics": {
            "saved_report_opening_rendered_now": rendered_report.splitlines()[:2],
            "current_render_says_uncalibrated": "uncalibrated" in rendered_report,
            "internal_six_clicks_still_maps_to": simulated.pull,
            "current_reader_render": simulated.render(),
            "interpretation": "Presentation corrected; internal frequency estimates and six-to-seven mapping remain. No empirical click calibration was demonstrated.",
        },
    }
    target = FOLDER / "facts-proof-retest.json"
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"result_file": str(target), "acceptance_counts": output["acceptance_counts"],
                      "exact_asset_issues": len(output["exact_asset_evidence_check"]["blocking"])
                      + len(output["exact_asset_evidence_check"]["advisory"]),
                      "source_documents": len(corpus.documents), "source_corpus_chars": len(corpus.text)}))


if __name__ == "__main__":
    main()
