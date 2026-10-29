"""Bounded evidence views for a decision; the complete ledger remains authoritative."""

import math
import re
from collections import Counter
from dataclasses import dataclass

from app.knowledge.corpus import fold
from app.knowledge.ledger import Evidence, EvidenceLedger, category_of, context_of

_STOP = frozenset({"this", "that", "with", "from", "your", "their", "have", "will", "email", "write", "exactly", "product", "people", "which", "about"})
_RELATED = (
    (r"\b(?:cost\w*|pric\w*|afford\w*|expensive|budget\w*)\b",
     "annual yearly billing discount renewal cancellation free tier"),
    (r"\b(?:trust\w*|accura\w*|counting|counts|numbers)\b",
     "bots bot filtering nonhuman verification accuracy"),
    (r"\b(?:list|lists|liste|listes)\b",
     "signup capture list automation funnel"),
)

# Retrieval hints only. These groups never license a quotation, a capability,
# a price or an outcome. Keep the original words as well as the shared concept
# so a French source can compete with English summaries under the same cap.
_CONCEPTS = (
    frozenset(["list", "lists", "liste", "listes"]),
    frozenset(["capture", "capturing", "collect", "collecting", "collecte", "collecter", "inscription", "inscriptions", "inscrit", "inscrite", "signup", "subscribe", "subscribed", "subscribes"]),
    frozenset(["funnel", "funnels", "tunnel", "tunnels"]),
    frozenset(["sell", "sells", "selling", "sale", "sales", "vente", "vendre", "vendant"]),
    frozenset(["book", "books", "livre", "livres"]),
    frozenset(["physical", "physique", "physiques"]),
    frozenset(["shipping", "shipment", "dispatch", "livraison", "expedition", "expedier"]),
    frozenset(["payment", "payments", "paiement", "paiements"]),
    frozenset(["automation", "automated", "automate", "automatically", "automatisation", "automatise", "automatisee", "automatiser", "automatique", "automatiquement"]),
    frozenset(["download", "downloads", "telechargement", "telechargements"]),
    frozenset(["price", "prices", "pricing", "prix", "tarif", "tarifs"]),
    frozenset(["monthly", "month", "months", "mois", "mensuel", "mensuelle"]),
    frozenset(["annual", "annually", "yearly", "year", "years", "an", "annuel", "annuelle"]),
)


def _terms(text: str) -> set[str]:
    words = {word for word in re.findall(r"[^\W_]{3,}", fold(text)) if word not in _STOP}
    return words | {f"concept{index}" for index, group in enumerate(_CONCEPTS) if words & group}


@dataclass(frozen=True)
class DecisionEvidence:
    ledger: EvidenceLedger
    omitted_ids: tuple[str, ...]

    def render_manifest(self) -> str:
        return (
            f"Selected {len(self.ledger.entries)} evidence entries; {len(self.omitted_ids)} others remain in the complete inventory. "
            "Omission is retrieval, not absence, invalidity or a competitor advantage. "
            "The full ledger remains authoritative for factual checks."
        )


def select_evidence(
    ledger: EvidenceLedger, query: str, *, preferred_ids: list[str] | None = None,
    excluded_ids: set[str] | frozenset[str] = frozenset(), cap: int = 36,
    problem_queries: list[str] | None = None,
) -> DecisionEvidence:
    """Keep explicit assignments, relevant boundary facts and a diverse overview.

    Stable id tie-breaking makes source order irrelevant. Mandatory references
    are never discarded to satisfy a display cap. Conditions on each entry are
    retained in full by the normal evidence renderer.
    """
    eligible = [entry for entry in ledger.entries if entry.id not in excluded_ids]
    by_id = {entry.id: entry for entry in eligible}
    terms = _terms(query)
    ranked = sorted(eligible, key=lambda entry: (
        -len(terms & _terms(f"{entry.claim} {entry.verbatim} {context_of(entry).render()}")),
        entry.id,
    ))
    chosen = {id_ for id_ in (preferred_ids or []) if id_ in by_id}
    # Contextual limits from the same sources as explicit assignments cannot
    # disappear behind high-scoring positive facts.
    sources = {by_id[id_].source for id_ in chosen if by_id[id_].source}
    subjects = {
        (by_id[id_].source, fold(context_of(by_id[id_]).subject)) for id_ in chosen
    }
    for entry in ranked:
        context = context_of(entry)
        # A page can document dozens of unrelated integrations. Its URL alone
        # cannot make every integration's exceptions mandatory for one choice.
        # Unscoped legacy facts retain the conservative same-source behaviour.
        same_subject = (entry.source, fold(context.subject)) in subjects
        if entry.source in sources and same_subject and (context.limitations or re.search(
            r"\b(?:not supported|not covered|exclud\w*|limited to|only available)\b", entry.verbatim, re.IGNORECASE
        )):
            chosen.add(entry.id)
    for kind in sorted({entry.kind for entry in eligible}):
        match = next((entry for entry in ranked if entry.kind == kind), None)
        if match:
            chosen.add(match.id)
    # A long common problem must not hide the one fact that answers a less
    # verbose problem. Rare terms identify the mechanism; this reserves context
    # for the judge, never an automatic fit or a stronger claim.
    tokens = {entry.id: _terms(f"{entry.claim} {entry.verbatim}") for entry in eligible}
    frequency = Counter(word for words in tokens.values() for word in words)
    mechanisms = [entry for entry in eligible
                  if context_of(entry).claim_scope in {"capability", "offer", "comparison"}
                  and context_of(entry).source_kind in {"official_documentation", "vendor_statement", "third_party"}]
    # Published findings can be the offering of a review publisher. Retrieval
    # keeps their third-party scope; it never turns the reviewed hardware into
    # the publisher's own capability. Like assigned references, these bounded
    # decision facts survive a budget already filled by mandatory conditions.
    for problem in (problem_queries or [])[:8]:
        words = _terms(problem)
        scores = {entry.id: sum(math.log((1 + len(eligible)) / (1 + frequency[word]))
                               for word in words & tokens[entry.id]) for entry in mechanisms}
        best = min((entry for entry in mechanisms if entry.id not in chosen),
                   key=lambda entry: (-scores[entry.id], entry.id), default=None)
        if best is not None and scores[best.id] > 0:
            chosen.add(best.id)
    # Related mechanisms are material to inspect, not proof of an outcome.
    # Reserve room within the existing cap instead of issuing another search.
    for trigger, related in _RELATED:
        if not re.search(trigger, query, re.IGNORECASE):
            continue
        related_terms = _terms(related)
        candidates = sorted(eligible, key=lambda entry: (
            -(3 * len(related_terms & _terms(entry.claim))
              + len(related_terms & _terms(entry.verbatim))), entry.id,
        ))
        added = 0
        for entry in candidates:
            if added >= 2:
                break
            if entry.id in chosen or not related_terms & _terms(f"{entry.claim} {entry.verbatim}"):
                continue
            if context_of(entry).claim_scope in {"customer_outcome", "comparison", "launch"}:
                continue
            chosen.add(entry.id)
            added += 1
    for entry in ranked:
        if len(chosen) >= cap:
            break
        chosen.add(entry.id)
    # Preserve semantic priority, not the input row order.
    selected = [entry for entry in ranked if entry.id in chosen]
    return DecisionEvidence(
        ledger=EvidenceLedger(entries=selected),
        omitted_ids=tuple(sorted(entry.id for entry in eligible if entry.id not in chosen)),
    )


def evidence_record(entry: Evidence) -> dict:
    """The shared source/claim boundary, never a paraphrase-only reference."""
    return {
        "id": entry.id, "kind": str(entry.kind), "category": str(category_of(entry)),
        "claim": entry.claim, "verbatim": entry.verbatim, "source": entry.source,
        "document_id": entry.document_id, "user_attested": entry.user_attested,
        "source_references": entry.source_references,
        "context": context_of(entry).model_dump(mode="json"),
    }
