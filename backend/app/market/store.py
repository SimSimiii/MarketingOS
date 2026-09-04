"""Reading and writing a brand's market intelligence.

Two things here are worth more than the CRUD around them.

**Approved proof is merged into knowledge, never written into it.** The
obvious implementation is to append an approved candidate to the evidence
ledger in the stored artifact set. It is also wrong: artifacts are recompiled
whenever the user's material changes, and the recompile would silently drop
every proof the user had approved - the one class of fact in the system that
cost a human a decision. So approvals live in their own table and are merged
onto the ledger at read time. A recompile can no longer lose them, and nothing
downstream can tell the difference: an approved proof arrives as an `Evidence`
entry with a verbatim quote and a source, which is exactly what the compiler
produces, and it is checked by the same gate.

**A chosen audience is merged the same way, and for a stronger reason.**
`merge_audience` puts a segment the user picked off the demand map at the head
of the compiled audience model, so the strategist, the cold reader panel and
the critic are all aimed at that buyer without any of them knowing the market
package exists. Writing it into the stored artifacts instead would mean one
campaign's targeting silently retargeting every other campaign attached to the
same brand.

**Merging re-derives the gaps.** `find_gaps` is a pure function of the
artifacts, so approving the first customer quotation does not just add a fact -
it closes `G-proof`, changes what `preflight.assess` says the campaign may
argue from, and stops the run being blocked for having nothing anybody has
vouched for. That chain is the whole point of the proof hunter, and it works
because nothing along it caches a conclusion.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlmodel import Session, col, select

from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.compiler import find_gaps
from app.knowledge.ledger import Evidence
from app.market.audience_research import AudienceResearch
from app.market.capabilities import ProductCapabilityProfile
from app.market.demand import (
    AudienceSegment,
    Contact,
    DemandMap,
    Prospect,
    ProspectStatus,
)
from app.market.proof import ProofCandidate, ProofKind, ProofStatus, next_evidence_id
from app.market.qualification import CompanyQualification
from app.market.radar import MarketSnapshot, RadarEvent, RadarSeverity
from app.market.relevance import RelevanceDossier
from app.market.rivals import RivalLead
from app.models.market import (
    AudienceMapRow,
    AudienceResearchRow,
    MarketScan,
    ProductCapabilityProfileRow,
    ProofCandidateRow,
    ProspectRow,
    RadarEventRow,
    RelevanceDossierRow,
    Rival,
)

logger = logging.getLogger("marketingos.market")


class MarketStore:
    """Everything one brand knows about its market, read and written."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --------------------------------------------------------------- rivals

    def rivals(self, brand_id: UUID, include_muted: bool = False) -> list[Rival]:
        statement = select(Rival).where(col(Rival.brand_id) == brand_id)
        if not include_muted:
            statement = statement.where(col(Rival.muted).is_(False))
        return list(self._session.exec(statement.order_by(col(Rival.created_at))))

    def add_rival(
        self,
        brand_id: UUID,
        name: str,
        url: str = "",
        kind: str = "alternative",
        why: str = "",
        added_by: str = "user",
    ) -> Rival:
        """Add one competitor, or return the one already there.

        Matched on name rather than on URL: the scout and the user regularly
        arrive at the same company through different addresses (a marketing
        site and an app subdomain), and a list with the same competitor twice
        makes every share-of-field number in the positioning map wrong.
        """
        if existing := self._rival_named(brand_id, name):
            if url and not existing.url:
                existing.url = url
                self._session.add(existing)
                self._session.commit()
                self._session.refresh(existing)
            return existing
        rival = Rival(
            brand_id=brand_id, name=name.strip(), url=url, kind=kind, why=why, added_by=added_by
        )
        self._session.add(rival)
        self._session.commit()
        self._session.refresh(rival)
        return rival

    def set_muted(self, rival: Rival, muted: bool) -> Rival:
        rival.muted = muted
        self._session.add(rival)
        self._session.commit()
        self._session.refresh(rival)
        return rival

    def delete_rival(self, rival: Rival) -> None:
        self._session.delete(rival)
        self._session.commit()

    def leads(self, brand_id: UUID) -> list[RivalLead]:
        """The competitor list as the scanner consumes it."""
        return [
            RivalLead(name=rival.name, url=rival.url, kind=rival.kind, why=rival.why)
            for rival in self.rivals(brand_id)
        ]

    def _rival_named(self, brand_id: UUID, name: str) -> Rival | None:
        wanted = " ".join(name.lower().split())
        return next(
            (
                rival
                for rival in self.rivals(brand_id, include_muted=True)
                if " ".join(rival.name.lower().split()) == wanted
            ),
            None,
        )

    # ---------------------------------------------------------------- scans

    def latest_scan(self, brand_id: UUID) -> MarketSnapshot | None:
        row = self._latest_scan_row(brand_id)
        return MarketSnapshot.model_validate(row.payload) if row and row.payload else None

    def latest_scan_row(self, brand_id: UUID) -> MarketScan | None:
        """The persisted identity/version behind :meth:`latest_scan`."""
        return self._latest_scan_row(brand_id)

    def scan_history(self, brand_id: UUID, limit: int = 20) -> list[MarketScan]:
        statement = (
            select(MarketScan)
            .where(col(MarketScan.brand_id) == brand_id)
            .order_by(col(MarketScan.version).desc())
            .limit(limit)
        )
        return list(self._session.exec(statement))

    def save_scan(self, brand_id: UUID, snapshot: MarketSnapshot) -> MarketScan:
        previous = self._latest_scan_row(brand_id)
        scan = MarketScan(
            brand_id=brand_id,
            version=(previous.version + 1) if previous else 1,
            payload=snapshot.model_dump(mode="json"),
            rivals_profiled=sum(1 for rival in snapshot.rivals if rival.verified),
            claims_verified=sum(len(rival.claims.claims) for rival in snapshot.rivals),
        )
        self._session.add(scan)
        self._session.commit()
        self._session.refresh(scan)
        return scan

    def _latest_scan_row(self, brand_id: UUID) -> MarketScan | None:
        statement = (
            select(MarketScan)
            .where(col(MarketScan.brand_id) == brand_id)
            .order_by(col(MarketScan.version).desc())
        )
        return self._session.exec(statement).first()

    # ---------------------------------------------------------------- proof

    def proof_candidates(
        self, brand_id: UUID, status: ProofStatus | None = None
    ) -> list[ProofCandidateRow]:
        statement = select(ProofCandidateRow).where(
            col(ProofCandidateRow.brand_id) == brand_id
        )
        if status is not None:
            statement = statement.where(col(ProofCandidateRow.status) == str(status))
        return list(
            self._session.exec(statement.order_by(col(ProofCandidateRow.found_at).desc()))
        )

    def record_candidates(
        self, brand_id: UUID, candidates: list[ProofCandidate]
    ) -> list[ProofCandidateRow]:
        """Store a hunt's findings, skipping ones already decided.

        Deduplicated on the URL and the quotation together, because the same
        review page legitimately yields two different quotations and the same
        quotation legitimately appears on two aggregators. Re-offering a
        candidate the user already rejected is the fastest way to teach them
        to stop reading the queue.
        """
        seen = {
            (row.url, row.verbatim.strip()) for row in self.proof_candidates(brand_id)
        }
        stored: list[ProofCandidateRow] = []
        for candidate in candidates:
            key = (candidate.url, candidate.verbatim.strip())
            if key in seen:
                continue
            seen.add(key)
            row = ProofCandidateRow(
                brand_id=brand_id,
                kind=str(candidate.kind),
                claim=candidate.claim,
                verbatim=candidate.verbatim,
                url=candidate.url,
                attributed_to=candidate.attributed_to,
                venue=candidate.venue,
                confidence=candidate.confidence,
                caveat=candidate.caveat,
                found_at=candidate.found_at,
            )
            self._session.add(row)
            stored.append(row)
        if stored:
            self._session.commit()
            for row in stored:
                self._session.refresh(row)
        return stored

    def decide(self, row: ProofCandidateRow, approved: bool) -> ProofCandidateRow:
        row.status = str(ProofStatus.APPROVED if approved else ProofStatus.REJECTED)
        row.decided_at = datetime.now(UTC)
        if approved and not row.evidence_id:
            taken = {
                other.evidence_id
                for other in self.proof_candidates(row.brand_id)
                if other.evidence_id
            }
            row.evidence_id = next_evidence_id(taken)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def approved_evidence(self, brand_id: UUID) -> list[Evidence]:
        """Every proof the user has said yes to, as ledger entries."""
        return [
            ProofCandidate(
                kind=ProofKind(row.kind),
                claim=row.claim,
                verbatim=row.verbatim,
                url=row.url,
                attributed_to=row.attributed_to,
                venue=row.venue,
                confidence=row.confidence,
            ).as_evidence(row.evidence_id)
            for row in self.proof_candidates(brand_id, ProofStatus.APPROVED)
            if row.evidence_id
        ]

    # ------------------------------------------------------------- audience

    def latest_map(self, brand_id: UUID) -> DemandMap | None:
        row = self._latest_map_row(brand_id)
        return DemandMap.model_validate(row.payload) if row and row.payload else None

    def latest_map_row(self, brand_id: UUID) -> AudienceMapRow | None:
        """The current map row when a derived artifact needs its exact version."""
        return self._latest_map_row(brand_id)

    def save_map(self, brand_id: UUID, demand: DemandMap) -> AudienceMapRow:
        previous = self._latest_map_row(brand_id)
        row = AudienceMapRow(
            brand_id=brand_id,
            version=(previous.version + 1) if previous else 1,
            payload=demand.model_dump(mode="json"),
            segments=len(demand.segments),
            unobvious_segments=sum(1 for item in demand.segments if item.unobvious),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def _latest_map_row(self, brand_id: UUID) -> AudienceMapRow | None:
        statement = (
            select(AudienceMapRow)
            .where(col(AudienceMapRow.brand_id) == brand_id)
            .order_by(col(AudienceMapRow.version).desc())
        )
        return self._session.exec(statement).first()

    def segment_named(self, brand_id: UUID, name: str) -> AudienceSegment | None:
        """One segment off this brand's current map, by the name a campaign stored."""
        if not name.strip():
            return None
        demand = self.latest_map(brand_id)
        return demand.named(name) if demand is not None else None

    # ----------------------------------------------------- audience research

    def latest_research_row(
        self, brand_id: UUID, audience: str
    ) -> AudienceResearchRow | None:
        key = _audience_key(audience)
        if not key:
            return None
        statement = (
            select(AudienceResearchRow)
            .where(col(AudienceResearchRow.brand_id) == brand_id)
            .where(col(AudienceResearchRow.audience_key) == key)
            .order_by(col(AudienceResearchRow.version).desc())
        )
        return self._session.exec(statement).first()

    def latest_research(
        self, brand_id: UUID, audience: str
    ) -> tuple[AudienceResearchRow, AudienceResearch] | None:
        row = self.latest_research_row(brand_id, audience)
        if row is None or not row.payload:
            return None
        try:
            return row, AudienceResearch.model_validate(row.payload)
        except ValidationError:
            logger.info("market: unreadable audience research payload on row %s", row.id)
            return None

    def latest_researches(self, brand_id: UUID) -> list[AudienceResearchRow]:
        """The newest readable row for each audience, preserving older versions."""
        statement = (
            select(AudienceResearchRow)
            .where(col(AudienceResearchRow.brand_id) == brand_id)
            .order_by(
                col(AudienceResearchRow.audience_key),
                col(AudienceResearchRow.version).desc(),
            )
        )
        latest: dict[str, AudienceResearchRow] = {}
        for row in self._session.exec(statement):
            if row.audience_key not in latest and row.payload:
                try:
                    AudienceResearch.model_validate(row.payload)
                except ValidationError:
                    logger.info("market: unreadable audience research payload on row %s", row.id)
                    continue
                latest[row.audience_key] = row
        return list(latest.values())

    def research_history(
        self, brand_id: UUID, audience: str, limit: int = 20
    ) -> list[AudienceResearchRow]:
        statement = (
            select(AudienceResearchRow)
            .where(col(AudienceResearchRow.brand_id) == brand_id)
            .where(col(AudienceResearchRow.audience_key) == _audience_key(audience))
            .order_by(col(AudienceResearchRow.version).desc())
            .limit(limit)
        )
        return list(self._session.exec(statement))

    def save_research(
        self,
        brand_id: UUID,
        research: AudienceResearch,
        source_map: AudienceMapRow | None,
    ) -> AudienceResearchRow:
        previous = self.latest_research_row(brand_id, research.audience_name)
        row = AudienceResearchRow(
            brand_id=brand_id,
            audience_key=_audience_key(research.audience_name),
            audience_name=research.audience_name,
            source_map_id=source_map.id if source_map else None,
            source_map_version=source_map.version if source_map else None,
            version=(previous.version + 1) if previous else 1,
            payload=research.model_dump(mode="json"),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    # --------------------------------------------------- product truth V2

    def latest_capability_profile_row(
        self, brand_id: UUID
    ) -> ProductCapabilityProfileRow | None:
        statement = (
            select(ProductCapabilityProfileRow)
            .where(col(ProductCapabilityProfileRow.brand_id) == brand_id)
            .order_by(col(ProductCapabilityProfileRow.version).desc())
        )
        return self._session.exec(statement).first()

    def latest_capability_profile(
        self, brand_id: UUID
    ) -> tuple[ProductCapabilityProfileRow, ProductCapabilityProfile] | None:
        row = self.latest_capability_profile_row(brand_id)
        if row is None or not row.payload:
            return None
        try:
            return row, ProductCapabilityProfile.model_validate(row.payload)
        except ValidationError:
            logger.info("market: unreadable capability profile payload on row %s", row.id)
            return None

    def capability_profile_for_knowledge(
        self,
        brand_id: UUID,
        *,
        knowledge_id: UUID,
        knowledge_version: int,
    ) -> tuple[ProductCapabilityProfileRow, ProductCapabilityProfile] | None:
        statement = (
            select(ProductCapabilityProfileRow)
            .where(col(ProductCapabilityProfileRow.brand_id) == brand_id)
            .where(col(ProductCapabilityProfileRow.knowledge_id) == knowledge_id)
            .where(col(ProductCapabilityProfileRow.knowledge_version) == knowledge_version)
            .order_by(col(ProductCapabilityProfileRow.version).desc())
        )
        for row in self._session.exec(statement):
            if not row.payload:
                continue
            try:
                return row, ProductCapabilityProfile.model_validate(row.payload)
            except ValidationError:
                logger.info("market: unreadable capability profile payload on row %s", row.id)
        return None

    def save_capability_profile(
        self, brand_id: UUID, profile: ProductCapabilityProfile
    ) -> ProductCapabilityProfileRow:
        previous = self.latest_capability_profile_row(brand_id)
        version = (previous.version + 1) if previous else 1
        normalized = profile.model_copy(update={"version": version})
        row = ProductCapabilityProfileRow(
            brand_id=brand_id,
            knowledge_id=normalized.knowledge_id,
            knowledge_version=normalized.knowledge_version,
            version=version,
            schema_version=normalized.schema_version,
            payload=normalized.model_dump(mode="json"),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    # --------------------------------------------------- relevance dossiers

    def latest_dossier_row(
        self, brand_id: UUID, audience: str
    ) -> RelevanceDossierRow | None:
        statement = (
            select(RelevanceDossierRow)
            .where(col(RelevanceDossierRow.brand_id) == brand_id)
            .where(col(RelevanceDossierRow.audience_key) == _audience_key(audience))
            .order_by(col(RelevanceDossierRow.generation_version).desc())
        )
        return self._session.exec(statement).first()

    def latest_dossier(
        self, brand_id: UUID, audience: str
    ) -> tuple[RelevanceDossierRow, RelevanceDossier] | None:
        row = self.latest_dossier_row(brand_id, audience)
        if row is None or not row.payload:
            return None
        try:
            return row, RelevanceDossier.model_validate(row.payload)
        except ValidationError:
            logger.info("market: unreadable relevance dossier payload on row %s", row.id)
            return None

    def dossier_for_triple(
        self,
        brand_id: UUID,
        audience: str,
        *,
        knowledge_id: UUID,
        knowledge_version: int,
        research_id: UUID,
        research_version: int,
        market_scan_id: UUID,
        market_scan_version: int,
    ) -> RelevanceDossierRow | None:
        statement = (
            select(RelevanceDossierRow)
            .where(col(RelevanceDossierRow.brand_id) == brand_id)
            .where(col(RelevanceDossierRow.audience_key) == _audience_key(audience))
            .where(col(RelevanceDossierRow.knowledge_id) == knowledge_id)
            .where(col(RelevanceDossierRow.knowledge_version) == knowledge_version)
            .where(col(RelevanceDossierRow.audience_research_id) == research_id)
            .where(
                col(RelevanceDossierRow.audience_research_version) == research_version
            )
            .where(col(RelevanceDossierRow.market_scan_id) == market_scan_id)
            .where(col(RelevanceDossierRow.market_scan_version) == market_scan_version)
            .order_by(col(RelevanceDossierRow.generation_version).desc())
        )
        return self._session.exec(statement).first()

    def dossier_for_v2_inputs(
        self,
        brand_id: UUID,
        audience: str,
        *,
        knowledge_id: UUID,
        knowledge_version: int,
        research_id: UUID,
        research_version: int,
        market_scan_id: UUID,
        market_scan_version: int,
        capability_profile_id: UUID,
        capability_profile_version: int,
        qualification_fingerprint: str,
    ) -> RelevanceDossierRow | None:
        statement = (
            select(RelevanceDossierRow)
            .where(col(RelevanceDossierRow.brand_id) == brand_id)
            .where(col(RelevanceDossierRow.audience_key) == _audience_key(audience))
            .where(col(RelevanceDossierRow.knowledge_id) == knowledge_id)
            .where(col(RelevanceDossierRow.knowledge_version) == knowledge_version)
            .where(col(RelevanceDossierRow.audience_research_id) == research_id)
            .where(col(RelevanceDossierRow.audience_research_version) == research_version)
            .where(col(RelevanceDossierRow.market_scan_id) == market_scan_id)
            .where(col(RelevanceDossierRow.market_scan_version) == market_scan_version)
            .where(col(RelevanceDossierRow.capability_profile_id) == capability_profile_id)
            .where(
                col(RelevanceDossierRow.capability_profile_version)
                == capability_profile_version
            )
            .where(
                col(RelevanceDossierRow.qualification_fingerprint)
                == qualification_fingerprint
            )
            .where(col(RelevanceDossierRow.schema_version) == 2)
            .order_by(col(RelevanceDossierRow.generation_version).desc())
        )
        return self._session.exec(statement).first()

    def dossier_history(
        self, brand_id: UUID, audience: str
    ) -> list[RelevanceDossierRow]:
        statement = (
            select(RelevanceDossierRow)
            .where(col(RelevanceDossierRow.brand_id) == brand_id)
            .where(col(RelevanceDossierRow.audience_key) == _audience_key(audience))
            .order_by(col(RelevanceDossierRow.generation_version).desc())
        )
        return list(self._session.exec(statement))

    def save_dossier(
        self, brand_id: UUID, dossier: RelevanceDossier
    ) -> RelevanceDossierRow:
        previous = self.latest_dossier_row(brand_id, dossier.audience_name)
        row = RelevanceDossierRow(
            brand_id=brand_id,
            audience_key=_audience_key(dossier.audience_name),
            audience_name=dossier.audience_name,
            audience_research_id=dossier.audience_research_id,
            audience_research_version=dossier.audience_research_version,
            knowledge_id=dossier.knowledge_id,
            knowledge_version=dossier.knowledge_version,
            market_scan_id=dossier.market_scan_id,
            market_scan_version=dossier.market_scan_version,
            capability_profile_id=dossier.capability_profile_id,
            capability_profile_version=dossier.capability_profile_version,
            qualification_fingerprint=dossier.qualification_fingerprint,
            schema_version=dossier.schema_version,
            generation_version=(previous.generation_version + 1) if previous else 1,
            payload=dossier.model_dump(mode="json"),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    # ------------------------------------------------------------ prospects

    def prospects(
        self,
        brand_id: UUID,
        segment: str | None = None,
        status: ProspectStatus | None = None,
    ) -> list[ProspectRow]:
        statement = select(ProspectRow).where(col(ProspectRow.brand_id) == brand_id)
        if segment is not None:
            statement = statement.where(col(ProspectRow.segment) == segment)
        if status is not None:
            statement = statement.where(col(ProspectRow.status) == str(status))
        return list(
            self._session.exec(
                statement.order_by(col(ProspectRow.fit).desc(), col(ProspectRow.found_at))
            )
        )

    def record_prospects(
        self, brand_id: UUID, prospects: list[Prospect]
    ) -> list[ProspectRow]:
        """Store new findings and refresh explicitly re-read organisations.

        Deduplicated on the host rather than the full URL, because the same
        company is reached at `acme.com`, `www.acme.com` and `acme.com/en` by
        three different searches, and re-offering a company the user already
        dismissed is the fastest way to teach them the list is not curated.
        A current read may replace the extracted fields on that row while its
        keep/dismiss decision survives. Falls back to the name where there is
        no URL to compare.
        """
        existing = {
            _prospect_key(row.url, row.name): row for row in self.prospects(brand_id)
        }
        stored: list[ProspectRow] = []
        for prospect in prospects:
            key = _prospect_key(prospect.url, prospect.name)
            row = existing.get(key)
            payload = {
                "segment": prospect.segment,
                "name": prospect.name,
                "url": prospect.url,
                "what_they_do": prospect.what_they_do,
                "why_them": prospect.why_them,
                "verbatim": prospect.verbatim,
                "fit": prospect.fit,
                "contacts": [
                    contact.model_dump(mode="json") for contact in prospect.contacts
                ],
                "caveat": prospect.caveat,
                "verified": prospect.verified,
                "pages_read": prospect.pages_read,
                "invented_contacts": prospect.invented_contacts,
                "qualification": (
                    prospect.qualification.model_dump(mode="json")
                    if prospect.qualification is not None
                    else None
                ),
                "note": prospect.note,
                "found_at": prospect.found_at,
            }
            if row is None:
                row = ProspectRow(brand_id=brand_id, **payload)
                existing[key] = row
            else:
                for field, value in payload.items():
                    setattr(row, field, value)
            self._session.add(row)
            stored.append(row)
        if stored:
            self._session.commit()
            for row in stored:
                self._session.refresh(row)
        return stored

    def decide_prospect(self, row: ProspectRow, status: ProspectStatus) -> ProspectRow:
        row.status = str(status)
        row.decided_at = datetime.now(UTC)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def delete_prospect(self, row: ProspectRow) -> None:
        self._session.delete(row)
        self._session.commit()

    # ---------------------------------------------------------------- radar

    def radar(self, brand_id: UUID, limit: int = 50) -> list[RadarEventRow]:
        statement = (
            select(RadarEventRow)
            .where(col(RadarEventRow.brand_id) == brand_id)
            .order_by(col(RadarEventRow.created_at).desc())
            .limit(limit)
        )
        return list(self._session.exec(statement))

    def record_events(self, brand_id: UUID, events: list[RadarEvent]) -> list[RadarEventRow]:
        rows = [
            RadarEventRow(
                brand_id=brand_id,
                headline=event.headline,
                detail=event.detail,
                severity=str(event.severity),
                rival=event.rival,
                axis=str(event.axis) if event.axis else "",
                what_to_do=event.what_to_do,
                created_at=event.at,
            )
            for event in events
        ]
        for row in rows:
            self._session.add(row)
        if rows:
            self._session.commit()
        return rows

    def mark_radar_seen(self, brand_id: UUID) -> int:
        now = datetime.now(UTC)
        unseen = [row for row in self.radar(brand_id, limit=200) if row.seen_at is None]
        for row in unseen:
            row.seen_at = now
            self._session.add(row)
        if unseen:
            self._session.commit()
        return len(unseen)


def merge_proof(artifacts: KnowledgeArtifacts, approved: list[Evidence]) -> KnowledgeArtifacts:
    """Fold approved third-party proof into a compiled knowledge set.

    Returns a copy. The stored artifacts are the compiler's output and stay
    that way: a run that reused them would otherwise find them changed under
    it by a decision made in the UI, and the fingerprint that decides whether
    to recompile covers the *material*, not this.

    The gap report is re-derived rather than patched, because it is a pure
    function of the ledger and patching it by hand would be the one place the
    two could disagree. Approving a customer quotation therefore closes
    `G-proof` on its own, which is what turns the approval into a different
    campaign rather than one extra line in a prompt.
    """
    if not approved:
        return artifacts
    merged = artifacts.model_copy(deep=True)
    known = merged.evidence.ids
    added = [entry for entry in approved if entry.id not in known]
    if not added:
        return artifacts
    merged.evidence.entries.extend(added)
    merged.gaps = find_gaps(merged)
    logger.info("market: merged %d approved proof point(s) into knowledge", len(added))
    return merged


def merge_audience(
    artifacts: KnowledgeArtifacts, segment: AudienceSegment | None
) -> KnowledgeArtifacts:
    """Aim a compiled knowledge set at one buyer off the demand map.

    Returns a copy, for exactly the reason `merge_proof` does: the stored
    artifacts are the compiler's output and belong to the business, while this
    is one campaign's decision about who it is for. Writing it in would mean
    the campaign that targeted resellers on Tuesday quietly retargeted every
    other campaign attached to the same brand.

    The segment goes to the *front* rather than being appended, because
    `AudienceModel.primary()` is what a good deal of the pipeline falls back
    to and "the audience this campaign is for" is precisely what primary means.
    Anything already there is kept behind it: a strategist that can see the
    company's own idea of its buyer beside the one the market suggested is
    making a choice, and one that can only see the second is being told the
    first does not exist.

    An identically-named segment already in the model is replaced rather than
    duplicated - the market's version carries the trigger and the pains that
    made it worth choosing, and two segments with one name is how the cold
    reader ends up decided by a coin flip.
    """
    if segment is None:
        return artifacts
    merged = artifacts.model_copy(deep=True)
    wanted = " ".join(segment.name.lower().split())
    merged.audience.segments = [
        item
        for item in merged.audience.segments
        if " ".join(item.name.lower().split()) != wanted
    ]
    merged.audience.segments.insert(0, segment.as_segment())
    if (objection := segment.as_objection()) is not None and not any(
        existing.objection.strip().lower() == objection.objection.strip().lower()
        for existing in merged.audience.objections
    ):
        # Ahead of the compiler's objections for the same reason the segment
        # is: the strategist assigns one objection per email off the top of
        # this list, and this is the doubt the chosen reader actually holds.
        merged.audience.objections.insert(0, objection)
    logger.info("market: campaign aimed at mapped segment %r", segment.name)
    return merged


def prospect_contacts(row: ProspectRow) -> list[Contact]:
    """One stored prospect's contacts, back as models.

    Tolerant of a payload that no longer parses: contacts are stored as JSON,
    and a row written by an older shape has to degrade to "no way in found"
    rather than take down a list of two hundred prospects.
    """
    contacts: list[Contact] = []
    for item in row.contacts or []:
        try:
            contacts.append(Contact.model_validate(item))
        except ValidationError:
            logger.info("market: unreadable contact payload on prospect %s", row.id)
    return contacts


def prospect_qualification(row: ProspectRow) -> CompanyQualification | None:
    if not row.qualification:
        return None
    try:
        return CompanyQualification.model_validate(row.qualification)
    except ValidationError:
        logger.info("market: unreadable company qualification payload on row %s", row.id)
        return None


def _prospect_key(url: str, name: str) -> str:
    host = url.strip().lower()
    for prefix in ("https://", "http://"):
        host = host.removeprefix(prefix)
    host = host.removeprefix("www.").split("/")[0].strip()
    return host or " ".join(name.lower().split())


def _audience_key(name: str) -> str:
    return " ".join(name.casefold().split())


def unseen_alerts(rows: list[RadarEventRow]) -> int:
    """How many changes worth interrupting somebody about are still unread.

    Only `acts_on_copy`. A badge that counts every routine row is a badge that
    is always lit, and a badge that is always lit is furniture.
    """
    return sum(
        1
        for row in rows
        if row.seen_at is None and row.severity == str(RadarSeverity.ACTS_ON_COPY)
    )
