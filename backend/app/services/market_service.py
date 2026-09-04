"""Running and reading a brand's market intelligence.

Six background jobs, one shape: scan the competitors, hunt for proof, map the
demand, research one audience, build its relevance dossier, find prospects. Each is a
background task for exactly the reason a
campaign is: it makes model calls and crawls half a dozen sites, so it takes
minutes, and a request that blocks on it is a request that times out behind a
proxy. All six are much smaller than a campaign, though - a few bounded calls
one extraction per site - so they get a small in-process status record and
polling rather than the whole execution/event/SSE apparatus. A job lost to a
restart costs the user a button press, and there is nothing half-written to
reconcile.

They share one slot per brand, which is a product decision rather than a
technical one. Two of these jobs write versioned rows and would race each
other to version n+1; the rest would simply be four progress lines competing
for one banner. A brand does one piece of market work at a time.

What is *not* here is any decision about what any of it means. The scanner
computes the snapshot, the radar computes the diff, the cartographer decides
who buys, and this module's whole job is sessions, background tasks and rows.
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Engine
from sqlmodel import Session

from app.ai.base import AIProvider, ResearchTool
from app.ai.model_router import ModelRouter
from app.ai.roles import ROLE_CATALOG
from app.core.config import PROMPTS_DIR
from app.knowledge.artifacts import KnowledgeArtifacts
from app.knowledge.store import ArtifactScope, ArtifactStore
from app.market.audience_research import (
    AudienceResearch,
    AudienceResearcher,
    AudienceResearchError,
)
from app.market.capabilities import (
    CapabilityProfileDraft,
    ProductCapabilityProfile,
    capability_ledger_fingerprint,
    derive_capability_profile,
    normalize_capability_profile,
)
from app.market.demand import (
    AudienceCartographer,
    DemandMap,
    ProspectFinder,
    ProspectLead,
    ProspectStatus,
)
from app.market.proof import ProofHunter, ProofStatus
from app.market.qualification import (
    COMPANY_QUALIFIER_VERSION,
    COMPANY_REQUIREMENT_EXTRACTOR_VERSION,
    COMPANY_REQUIREMENT_NORMALIZER_VERSION,
    AudienceDefinition,
    CompanyQualification,
    EvidenceCompleteness,
    QualificationClass,
    QualificationDimension,
    Reachability,
    qualify_company,
    stale_company_qualification,
)
from app.market.radar import MarketSnapshot
from app.market.relevance import (
    DossierState,
    MissingPrerequisite,
    QualifiedCompanySnapshot,
    RelevanceAnalyst,
    RelevanceDossier,
    RelevanceStatus,
    RelevanceValidationError,
)
from app.market.scanner import MarketScanner
from app.market.store import (
    MarketStore,
    merge_proof,
    prospect_contacts,
    prospect_qualification,
)
from app.models.brand import Brand
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.market import (
    AudienceResearchRow,
    MarketScan,
    ProductCapabilityProfileRow,
    ProofCandidateRow,
    ProspectRow,
    Rival,
)
from app.repositories.knowledge_artifact_repository import KnowledgeArtifactRepository
from app.runtime.events import EventBus
from app.runtime.exceptions import CapabilityUnavailableError, ModelRuntimeError
from app.runtime.model_session import ModelSession, RoleCall
from app.runtime.prompt_engine import get_prompt_engine

logger = logging.getLogger("marketingos.market")


class MarketError(Exception):
    """Raised when a market job cannot be started at all."""


@dataclass
class JobStatus:
    """Where one background market job has got to, and what it has cost.

    Held in memory only. A restart loses it, and that is the right trade for a
    job whose recovery is "press the button again" - persisting it would buy a
    reconciliation problem to protect a two-minute operation.

    The spend is here rather than only on the `ModelSession` because the
    session is created inside the background task and dies with it. A market
    job spends real quota - the cartographer runs on the deep tier and the
    prospect reader runs once per company - and a user watching a job they
    started has exactly one question the progress line does not answer, which
    is what it is costing them.
    """

    kind: str
    brand_id: UUID
    #: Whose market this is. Carried so a board listing every running job can
    #: name it without one brand lookup per row.
    brand_name: str = ""
    state: str = "running"
    #: The most recent progress line, in the user's language.
    message: str = ""
    #: Every line so far, so a page that opens late is not blank.
    log: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
    error: str = ""
    #: What the finished job produced, for the page that was polling it.
    summary: str = ""
    found: int = 0

    #: Model calls made so far, and what they cost. Cached input is counted
    #: into `input_tokens` for the same reason the campaign runs count it: it
    #: is what the quota actually paid for, and reporting only the uncached
    #: remainder makes every job look several times cheaper than it was.
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0

    def say(self, message: str) -> None:
        self.message = message
        self.log.append(message)

    def record(self, call: RoleCall) -> None:
        """One finished model call, counted and written into the trace.

        The line is appended to the log rather than replacing `message`: the
        progress line is the *stage* the job is at, in the user's language,
        and overwriting it with "Audience cartographer finished" replaces
        something meaningful with bookkeeping.
        """
        self.calls += 1
        self.input_tokens += call.billable_input_tokens
        self.output_tokens += call.output_tokens
        self.cache_read_tokens += call.cache_read_input_tokens
        self.cost_usd += call.cost_usd
        label = spec.label if (spec := ROLE_CATALOG.get(call.role)) else call.role
        self.log.append(
            f"{label} · {call.model} · {call.duration_ms / 1000:.1f}s · "
            f"{call.billable_input_tokens:,} in / {call.output_tokens:,} out"
            + (f" · ${call.cost_usd:.4f}" if call.cost_usd else "")
        )


#: One job per brand at a time, keyed by brand. Two concurrent scans of the
#: same market would race each other to write version n+1 and one of them
#: would lose its findings; two scans of *different* brands are independent
#: and both allowed.
_jobs: dict[UUID, JobStatus] = {}

#: The tasks those jobs are running in. Held here because the event loop holds
#: only a *weak* reference to a task, so one that nothing else references may
#: be garbage collected at any point before it finishes - which is what
#: `asyncio.create_task`'s own documentation warns about.
#:
#: `_jobs` was not that reference. It holds the `JobStatus` the polling route
#: reads, and a status is not a task: a scan could vanish between two polls and
#: leave a status that says "running" for the life of the process, at which
#: point `_require_idle` refuses every further job for that brand and the only
#: fix is a restart. The campaign path never had this hole - `ExecutionRegistry`
#: holds its task and drops it on completion - and this is the same guarantee
#: for market work, in the same shape.
_running: set[asyncio.Task] = set()


@dataclass(frozen=True)
class _RelevanceInputs:
    knowledge_row: KnowledgeArtifactSet
    artifacts: KnowledgeArtifacts
    research_row: AudienceResearchRow
    research: AudienceResearch
    market_scan_row: MarketScan
    snapshot: MarketSnapshot
    capability_profile_row: ProductCapabilityProfileRow
    capability_profile: ProductCapabilityProfile
    company_qualifications: list[QualifiedCompanySnapshot]
    qualification_fingerprint: str


def _spawn(coro: Coroutine[Any, Any, None]) -> None:
    """Start one background market job and keep hold of it until it ends.

    The only place in this module allowed to call `create_task`, so that no
    future launcher can reintroduce the unheld task by copying its neighbour.
    """
    task = asyncio.create_task(coro)
    _running.add(task)
    task.add_done_callback(_running.discard)


def job_for(brand_id: UUID) -> JobStatus | None:
    return _jobs.get(brand_id)


def all_jobs() -> list[JobStatus]:
    """Every market job this process knows about, running ones first.

    For the board that answers "what is happening right now". A finished job
    is kept and listed after the running ones because the answer to that
    question, five minutes after a scan lands, is "that scan, and here is what
    it cost" - not an empty page.
    """
    return sorted(
        _jobs.values(),
        key=lambda job: (job.state != "running", -job.started_at.timestamp()),
    )


class MarketService:
    """A brand's competitors, scans, proof, audience, relevance and prospects."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._store = MarketStore(session)
        self._artifacts = ArtifactStore(session)

    # ---------------------------------------------------------------- reads

    @property
    def store(self) -> MarketStore:
        return self._store

    def rivals(self, brand_id: UUID, include_muted: bool = True) -> list[Rival]:
        return self._store.rivals(brand_id, include_muted=include_muted)

    def snapshot(self, brand_id: UUID) -> MarketSnapshot | None:
        return self._store.latest_scan(brand_id)

    def proof_queue(
        self, brand_id: UUID, status: ProofStatus | None = None
    ) -> list[ProofCandidateRow]:
        return self._store.proof_candidates(brand_id, status)

    def demand(self, brand_id: UUID) -> DemandMap | None:
        return self._store.latest_map(brand_id)

    def prospects(
        self,
        brand_id: UUID,
        segment: str | None = None,
        status: ProspectStatus | None = None,
    ) -> list[ProspectRow]:
        return self._store.prospects(brand_id, segment, status)

    def artifacts_for(self, brand_id: UUID) -> KnowledgeArtifacts | None:
        """The brand's compiled knowledge, with approved proof folded in.

        The same view the campaign pipeline gets, so what the market pages say
        this business can prove and what a run says it can prove are the same
        statement.
        """
        stored = self._artifacts.load(ArtifactScope(brand_id=brand_id))
        if stored is None:
            return None
        return merge_proof(stored.artifacts, self._store.approved_evidence(brand_id))

    def capability_profile(
        self, brand_id: UUID
    ) -> tuple[ProductCapabilityProfileRow, ProductCapabilityProfile] | None:
        """Return the latest readable profile without silently deriving support."""
        return self._store.latest_capability_profile(brand_id)

    def current_company_qualification(
        self, brand_id: UUID, audience: str, row: ProspectRow
    ) -> CompanyQualification:
        """Re-evaluate stored company evidence against current V2 inputs.

        The classification can be replayed for the same capability catalogue.
        A profile or extractor change can alter semantic requirement mapping,
        so that extraction is explicitly stale until the company is read
        again instead of being silently interpreted under a different input.
        """
        stored = prospect_qualification(row)
        if stored is None:
            return _unverified_company_qualification(
                "legacy_prospect_has_no_qualification"
            )
        profile = self.capability_profile(brand_id)
        if profile is None:
            return _unverified_company_qualification("capability_profile_missing")
        if stored.stale_reasons(profile[1]):
            return stale_company_qualification(stored, profile[1])
        research = self._store.latest_research(brand_id, audience)
        mapped_segment = self._store.segment_named(brand_id, audience)
        definition = (
            research[1].definition
            if research is not None
            else mapped_segment.definition
            if mapped_segment is not None
            else None
        )
        if definition is None:
            return stored
        return qualify_company(
            definition=definition,
            profile=profile[1],
            evidence=stored.evidence,
            requirements=stored.requirements,
            unmapped_requirements=stored.unmapped_requirements,
            site_verified=row.verified,
            pages_read=row.pages_read,
            reachable=bool(prospect_contacts(row)),
        )

    def save_capability_profile(
        self, brand_id: UUID, draft: CapabilityProfileDraft
    ) -> ProductCapabilityProfileRow:
        knowledge = KnowledgeArtifactRepository(self._session).latest_for_brand(brand_id)
        artifacts = self.artifacts_for(brand_id)
        if knowledge is None or artifacts is None:
            raise MarketError("Compile Product Knowledge before editing product capabilities.")
        previous = self._store.latest_capability_profile_row(brand_id)
        profile = normalize_capability_profile(
            draft,
            ledger=artifacts.evidence,
            knowledge_id=knowledge.id,
            knowledge_version=knowledge.version,
            version=(previous.version + 1) if previous else 1,
        )
        return self._store.save_capability_profile(brand_id, profile)

    def ensure_capability_profile(
        self, brand_id: UUID
    ) -> tuple[ProductCapabilityProfileRow, ProductCapabilityProfile]:
        knowledge = KnowledgeArtifactRepository(self._session).latest_for_brand(brand_id)
        artifacts = self.artifacts_for(brand_id)
        if knowledge is None or artifacts is None:
            raise MarketError("Compile Product Knowledge before qualifying an audience.")
        current_fingerprint = capability_ledger_fingerprint(artifacts.evidence)
        existing = self._store.capability_profile_for_knowledge(
            brand_id,
            knowledge_id=knowledge.id,
            knowledge_version=knowledge.version,
        )
        if existing is not None and existing[1].ledger_fingerprint == current_fingerprint:
            return existing
        previous = self._store.latest_capability_profile(brand_id)
        profile = derive_capability_profile(
            artifacts.evidence,
            knowledge_id=knowledge.id,
            knowledge_version=knowledge.version,
            previous=previous[1] if previous is not None else None,
        )
        row = self._store.save_capability_profile(brand_id, profile)
        return row, profile.model_copy(update={"version": row.version})

    def relevance_status(self, brand_id: UUID, audience: str) -> RelevanceStatus:
        """Current/stale/missing derived only from persisted version pointers."""
        knowledge = KnowledgeArtifactRepository(self._session).latest_for_brand(brand_id)
        research = self._store.latest_research_row(brand_id, audience)
        scan = self._store.latest_scan_row(brand_id)
        missing = _missing_relevance_prerequisites(knowledge, research, scan)
        latest = self._store.latest_dossier(brand_id, audience)
        if latest is None:
            return RelevanceStatus(
                audience_name=audience,
                status=DossierState.MISSING,
                missing_prerequisites=missing,
            )

        row, dossier = latest
        stale: list[str] = []
        if (
            knowledge is None
            or row.knowledge_id != knowledge.id
            or row.knowledge_version != knowledge.version
        ):
            stale.append("knowledge_changed")
        if (
            research is None
            or row.audience_research_id != research.id
            or row.audience_research_version != research.version
        ):
            stale.append("audience_research_changed")
        if (
            scan is None
            or row.market_scan_id != scan.id
            or row.market_scan_version != scan.version
        ):
            stale.append("market_scan_changed")
        if row.schema_version >= 2 and row.capability_profile_id is not None:
            profile = self._store.latest_capability_profile_row(brand_id)
            if (
                profile is None
                or profile.id != row.capability_profile_id
                or profile.version != row.capability_profile_version
            ):
                stale.append("capability_profile_changed")
            profile_read = self._store.latest_capability_profile(brand_id)
            research_read = self._store.latest_research(brand_id, row.audience_name)
            fingerprint = _qualification_fingerprint(
                _qualification_snapshots(
                    self._store.prospects(brand_id, row.audience_name),
                    definition=(research_read[1].definition if research_read else None),
                    profile=(profile_read[1] if profile_read else None),
                ),
                profile=(profile_read[1] if profile_read else None),
            )
            if fingerprint != row.qualification_fingerprint:
                stale.append("company_qualification_changed")
        return RelevanceStatus(
            audience_name=row.audience_name,
            status=DossierState.STALE if stale else DossierState.CURRENT,
            stale_reasons=stale,
            missing_prerequisites=missing,
            dossier_id=row.id,
            generation_version=row.generation_version,
            created_at=row.created_at,
            dossier=dossier,
        )

    def relevance_statuses(self, brand_id: UUID) -> list[RelevanceStatus]:
        return [
            self.relevance_status(brand_id, row.audience_name)
            for row in self._store.latest_researches(brand_id)
        ]

    # --------------------------------------------------------------- edits

    def add_rival(
        self, brand_id: UUID, name: str, url: str = "", kind: str = "alternative", why: str = ""
    ) -> Rival:
        return self._store.add_rival(
            brand_id, name=name, url=url, kind=kind, why=why, added_by="user"
        )

    def set_muted(self, rival: Rival, muted: bool) -> Rival:
        return self._store.set_muted(rival, muted)

    def delete_rival(self, rival: Rival) -> None:
        self._store.delete_rival(rival)

    def decide_proof(self, row: ProofCandidateRow, approved: bool) -> ProofCandidateRow:
        return self._store.decide(row, approved)

    def decide_prospect(self, row: ProspectRow, status: ProspectStatus) -> ProspectRow:
        return self._store.decide_prospect(row, status)

    def delete_prospect(self, row: ProspectRow) -> None:
        self._store.delete_prospect(row)

    def mark_radar_seen(self, brand_id: UUID) -> int:
        return self._store.mark_radar_seen(brand_id)

    # ------------------------------------------------------------ launching

    def launch_scan(
        self,
        brand: Brand,
        provider: AIProvider,
        engine: Engine,
        discover: bool = True,
    ) -> JobStatus:
        self._require_idle(brand.id)
        self._require_knowledge(brand.id)
        if discover:
            _require_web(provider)
        status = JobStatus(kind="scan", brand_id=brand.id, brand_name=brand.name)
        status.say("Starting")
        _jobs[brand.id] = status
        _spawn(_run_scan(brand.id, provider, engine, discover, status))
        return status

    def launch_proof_hunt(
        self, brand: Brand, provider: AIProvider, engine: Engine
    ) -> JobStatus:
        self._require_idle(brand.id)
        self._require_knowledge(brand.id)
        _require_web(provider)
        status = JobStatus(kind="proof", brand_id=brand.id, brand_name=brand.name)
        status.say("Searching for anyone who has vouched for this company")
        _jobs[brand.id] = status
        _spawn(_run_hunt(brand.id, provider, engine, status))
        return status

    def launch_audience_map(
        self, brand: Brand, provider: AIProvider, engine: Engine
    ) -> JobStatus:
        self._require_idle(brand.id)
        self._require_knowledge(brand.id)
        _require_web(provider)
        status = JobStatus(kind="audience", brand_id=brand.id, brand_name=brand.name)
        status.say("Working out who would actually buy this")
        _jobs[brand.id] = status
        _spawn(_run_audience_map(brand.id, provider, engine, status))
        return status

    def launch_prospect_search(
        self,
        brand: Brand,
        provider: AIProvider,
        engine: Engine,
        *,
        segment: str,
        limit: int = 10,
        with_contacts: bool = True,
    ) -> JobStatus:
        """Find named organisations for one mapped segment.

        The segment is resolved here rather than in the background task on
        purpose: "you asked for a segment that is not on your map" is a
        mistake in the request, and a 409 the user can act on beats a job that
        starts, spends a search call and reports the same thing two minutes
        later.
        """
        self._require_idle(brand.id)
        self._require_knowledge(brand.id)
        # The segment is resolved before the provider is checked, because it
        # is about what the user just asked for and the capability check is
        # about how the server is configured. Telling somebody who mistyped a
        # segment that their provider cannot read the web sends them to fix
        # the wrong thing.
        demand = self._store.latest_map(brand.id)
        found = demand.named(segment) if demand is not None else None
        if found is None:
            raise MarketError(
                f"No segment called '{segment}' is on this brand's audience map. Map the "
                "audience first, then pick one of the segments it found."
            )
        admission = demand.admission_for(found)
        if not admission.researchable:
            raise MarketError(
                f"'{found.name}' is not researchable, so no prospect search was started. "
                + " ".join(admission.reasons)
            )
        _require_web(provider)
        status = JobStatus(kind="prospects", brand_id=brand.id, brand_name=brand.name)
        status.say(f"Looking for organisations that match {found.name}")
        _jobs[brand.id] = status
        _spawn(
            _run_prospects(
                brand.id,
                provider,
                engine,
                status,
                segment=found.name,
                limit=limit,
                with_contacts=with_contacts,
            )
        )
        return status

    def launch_audience_research(
        self,
        brand: Brand,
        provider: AIProvider,
        engine: Engine,
        *,
        segment: str,
    ) -> JobStatus:
        """Research one current, admitted audience without product context."""
        self._require_idle(brand.id)
        demand = self._store.latest_map(brand.id)
        found = demand.named(segment) if demand is not None else None
        if found is None:
            raise MarketError(
                f"No segment called '{segment}' is on this brand's current audience map. "
                "Map the audience first, then pick one of the segments it found."
            )
        admission = demand.admission_for(found)
        if not admission.researchable:
            raise MarketError(
                f"'{found.name}' did not pass audience research admission. "
                + " ".join(admission.reasons)
            )
        _require_search(provider)
        status = JobStatus(
            kind="audience_research", brand_id=brand.id, brand_name=brand.name
        )
        status.say(f"Starting deep research for {found.name}")
        _jobs[brand.id] = status
        _spawn(
            _run_audience_research(
                brand.id,
                provider,
                engine,
                status,
                segment=found.name,
            )
        )
        return status

    def launch_relevance_dossier(
        self,
        brand: Brand,
        provider: AIProvider,
        engine: Engine,
        *,
        segment: str,
        force: bool = False,
    ) -> JobStatus:
        """Build or reuse one dossier for the latest persisted input triple."""
        self._require_idle(brand.id)
        inputs = self._relevance_inputs(brand.id, segment)
        exact = self._store.dossier_for_v2_inputs(
            brand.id,
            inputs.research.audience_name,
            knowledge_id=inputs.knowledge_row.id,
            knowledge_version=inputs.knowledge_row.version,
            research_id=inputs.research_row.id,
            research_version=inputs.research_row.version,
            market_scan_id=inputs.market_scan_row.id,
            market_scan_version=inputs.market_scan_row.version,
            capability_profile_id=inputs.capability_profile_row.id,
            capability_profile_version=inputs.capability_profile_row.version,
            qualification_fingerprint=inputs.qualification_fingerprint,
        )
        # A stored V1 exact-triple receipt remains reusable and inspectable.
        # Campaign preflight treats its missing recommendation as discovery-only,
        # so compatibility never silently becomes permission to assert fit.
        if exact is None:
            legacy = self._store.dossier_for_triple(
                brand.id,
                inputs.research.audience_name,
                knowledge_id=inputs.knowledge_row.id,
                knowledge_version=inputs.knowledge_row.version,
                research_id=inputs.research_row.id,
                research_version=inputs.research_row.version,
                market_scan_id=inputs.market_scan_row.id,
                market_scan_version=inputs.market_scan_row.version,
            )
            exact = legacy if legacy is not None and legacy.schema_version == 1 else None
        if exact is not None and exact.payload and not force:
            # An unreadable row is not a reusable success receipt.
            try:
                RelevanceDossier.model_validate(exact.payload)
            except ValueError:
                exact = None
        if exact is not None and not force:
            status = JobStatus(
                kind="relevance_dossier",
                brand_id=brand.id,
                brand_name=brand.name,
                state="done",
            )
            status.summary = (
                f"Reused relevance dossier v{exact.generation_version}; the knowledge, "
                "audience research and market scan are unchanged"
            )
            status.say(status.summary)
            status.finished_at = datetime.now(UTC)
            _jobs[brand.id] = status
            return status

        status = JobStatus(
            kind="relevance_dossier", brand_id=brand.id, brand_name=brand.name
        )
        status.say(f"Connecting verified product evidence to {inputs.research.audience_name}")
        _jobs[brand.id] = status
        _spawn(
            _run_relevance_dossier(
                brand.id,
                provider,
                engine,
                status,
                segment=inputs.research.audience_name,
            )
        )
        return status

    def _require_idle(self, brand_id: UUID) -> None:
        running = _jobs.get(brand_id)
        if running is not None and running.state == "running":
            raise MarketError(
                f"A {running.kind} is already running for this brand. Wait for it to finish."
            )

    def _require_knowledge(self, brand_id: UUID) -> None:
        if self.artifacts_for(brand_id) is None:
            raise MarketError(
                "This brand's knowledge has not been compiled yet. Add its website or a "
                "document and run a campaign once, so there is something to position."
            )

    def _relevance_inputs(self, brand_id: UUID, audience: str) -> _RelevanceInputs:
        knowledge = KnowledgeArtifactRepository(self._session).latest_for_brand(brand_id)
        found = self._store.latest_research(brand_id, audience)
        scan = self._store.latest_scan_row(brand_id)
        missing = _missing_relevance_prerequisites(
            knowledge, found[0] if found is not None else None, scan
        )
        if missing:
            raise MarketError(
                "A relevance dossier needs three current persisted inputs. "
                + " ".join(item.message for item in missing)
            )
        artifacts = self.artifacts_for(brand_id)
        assert knowledge is not None and found is not None and scan is not None
        if artifacts is None or not scan.payload:
            raise MarketError(
                "The current Product Knowledge or Market Scan payload cannot be read. "
                "Recompile knowledge or run the market scan again."
            )
        profile_row, profile = self.ensure_capability_profile(brand_id)
        companies = _qualification_snapshots(
            self._store.prospects(brand_id, found[1].audience_name),
            definition=found[1].definition,
            profile=profile,
        )
        return _RelevanceInputs(
            knowledge_row=knowledge,
            artifacts=artifacts,
            research_row=found[0],
            research=found[1],
            market_scan_row=scan,
            snapshot=MarketSnapshot.model_validate(scan.payload),
            capability_profile_row=profile_row,
            capability_profile=profile,
            company_qualifications=companies,
            qualification_fingerprint=_qualification_fingerprint(companies, profile=profile),
        )


def _missing_relevance_prerequisites(
    knowledge: KnowledgeArtifactSet | None,
    research: AudienceResearchRow | None,
    scan: MarketScan | None,
) -> list[MissingPrerequisite]:
    missing: list[MissingPrerequisite] = []
    if knowledge is None or not knowledge.payload:
        missing.append(
            MissingPrerequisite(
                code="knowledge",
                message=(
                    "Compile Product Knowledge from this brand's website or documents first."
                ),
            )
        )
    if research is None or not research.payload:
        missing.append(
            MissingPrerequisite(
                code="audience_research",
                message="Run Deep Audience Research for this audience first.",
            )
        )
    if scan is None or not scan.payload:
        missing.append(
            MissingPrerequisite(
                code="market_scan",
                message="Run a Market Scan so a current Positioning Map exists first.",
            )
        )
    return missing


def _require_web(provider: AIProvider) -> None:
    """Refuse before spending anything, rather than after answering wrongly.

    See `CapabilityUnavailableError`: a scan without web access does not fail,
    it returns competitors the model remembered, and nothing downstream can
    tell that from a real scan.
    """
    missing = [
        tool
        for tool in (ResearchTool.WEB_SEARCH, ResearchTool.WEB_FETCH)
        if tool not in provider.available_tools()
    ]
    if missing:
        raise MarketError(
            "The configured AI provider cannot read the web, so there is nothing to "
            "discover. Competitors you add by hand can still be profiled."
        )


def _require_search(provider: AIProvider) -> None:
    if ResearchTool.WEB_SEARCH not in provider.available_tools():
        raise MarketError(
            "The configured AI provider cannot search the web, so audience research "
            "cannot locate sources."
        )


# ------------------------------------------------------------- background

async def _run_scan(
    brand_id: UUID,
    provider: AIProvider,
    engine: Engine,
    discover: bool,
    status: JobStatus,
) -> None:
    with Session(engine) as session:
        service = MarketService(session)
        store = service.store
        try:
            artifacts = service.artifacts_for(brand_id)
            if artifacts is None:
                raise MarketError("This brand has no compiled knowledge to position.")

            previous = store.latest_scan(brand_id)
            scanner = MarketScanner(_session_for(provider, brand_id, status))
            result = await scanner.scan(
                artifacts=artifacts,
                known=store.leads(brand_id),
                previous=previous,
                discover=discover,
                on_progress=lambda _stage, message: status.say(message),
            )

            for lead in result.discovered:
                store.add_rival(
                    brand_id,
                    name=lead.name,
                    url=lead.url,
                    kind=lead.kind,
                    why=lead.why,
                    added_by="scout",
                )
            store.save_scan(brand_id, result.snapshot)
            store.record_events(brand_id, result.events)

            status.state = "done"
            status.summary = result.snapshot.positioning.summary()
            status.found = len(result.discovered)
            for note in result.notes:
                status.say(note)
            status.say(status.summary)
        except (MarketError, ModelRuntimeError) as exc:
            logger.info("market: scan failed - %s", exc)
            status.state = "failed"
            status.error = str(exc)
            status.say(f"Stopped: {exc}")
        except Exception:  # a background task must not vanish silently
            logger.exception("market: scan crashed")
            status.state = "failed"
            status.error = "The scan crashed unexpectedly. Check server logs."
            status.say(status.error)
        finally:
            status.finished_at = datetime.now(UTC)


async def _run_hunt(
    brand_id: UUID, provider: AIProvider, engine: Engine, status: JobStatus
) -> None:
    with Session(engine) as session:
        service = MarketService(session)
        try:
            artifacts = service.artifacts_for(brand_id)
            if artifacts is None:
                raise MarketError("This brand has no compiled knowledge to search around.")
            brand = session.get(Brand, brand_id)
            hunt = await ProofHunter(_session_for(provider, brand_id, status)).hunt(
                artifacts.business, website=(brand.website_url if brand else "") or ""
            )
            stored = service.store.record_candidates(brand_id, hunt.candidates)
            status.state = "done"
            status.found = len(stored)
            status.summary = (
                f"{len(stored)} new proof point(s) waiting for your approval"
                if stored
                else (
                    hunt.note
                    or "Nothing outside this company's own site mentions it yet. That is "
                    "itself the finding: three customer names would change more than any "
                    "rewrite."
                )
            )
            status.say(status.summary)
        except (MarketError, ModelRuntimeError, CapabilityUnavailableError) as exc:
            logger.info("market: proof hunt failed - %s", exc)
            status.state = "failed"
            status.error = str(exc)
            status.say(f"Stopped: {exc}")
        except Exception:  # a background task must not vanish silently
            logger.exception("market: proof hunt crashed")
            status.state = "failed"
            status.error = "The hunt crashed unexpectedly. Check server logs."
            status.say(status.error)
        finally:
            status.finished_at = datetime.now(UTC)


async def _run_audience_map(
    brand_id: UUID, provider: AIProvider, engine: Engine, status: JobStatus
) -> None:
    with Session(engine) as session:
        service = MarketService(session)
        try:
            artifacts = service.artifacts_for(brand_id)
            if artifacts is None:
                raise MarketError("This brand has no compiled knowledge to map demand from.")

            # The competitive reading is passed in where one exists, because
            # who to sell to and who else is selling are the same question
            # asked twice: a segment every competitor already saturates is a
            # worse bet at the same rate than one none of them address.
            snapshot = service.store.latest_scan(brand_id)
            demand = await AudienceCartographer(_session_for(provider, brand_id, status)).map(
                artifacts,
                positioning=snapshot.positioning if snapshot is not None else None,
            )
            service.store.save_map(brand_id, demand)

            status.state = "done"
            status.found = len(demand.segments)
            status.summary = demand.summary()
            if demand.note:
                status.say(demand.note)
            status.say(status.summary)
        except (MarketError, ModelRuntimeError, CapabilityUnavailableError) as exc:
            logger.info("market: audience map failed - %s", exc)
            status.state = "failed"
            status.error = str(exc)
            status.say(f"Stopped: {exc}")
        except Exception:  # a background task must not vanish silently
            logger.exception("market: audience map crashed")
            status.state = "failed"
            status.error = "Mapping the audience crashed unexpectedly. Check server logs."
            status.say(status.error)
        finally:
            status.finished_at = datetime.now(UTC)


async def _run_prospects(
    brand_id: UUID,
    provider: AIProvider,
    engine: Engine,
    status: JobStatus,
    *,
    segment: str,
    limit: int,
    with_contacts: bool,
) -> None:
    with Session(engine) as session:
        service = MarketService(session)
        store = service.store
        try:
            artifacts = service.artifacts_for(brand_id)
            found = store.segment_named(brand_id, segment)
            if artifacts is None or found is None:
                raise MarketError(
                    "This brand's audience map or knowledge went away while the search was "
                    "starting. Map the audience again."
                )

            # Every organisation already on this brand's list, whatever
            # segment it came from, so a second search does not spend its
            # budget re-finding what the user has already decided about.
            existing_prospects = store.prospects(brand_id)
            known = [row.name for row in existing_prospects]
            _, capability_profile = service.ensure_capability_profile(brand_id)
            refresh = [
                ProspectLead(
                    name=row.name,
                    url=row.url,
                    why_them=row.why_them,
                    segment=row.segment,
                )
                for row in existing_prospects
                if row.segment == found.name
                and row.url.strip()
                and (
                    (qualification := prospect_qualification(row)) is None
                    or qualification.stale_reasons(capability_profile)
                )
            ]
            prospects = await ProspectFinder(_session_for(provider, brand_id, status)).find(
                artifacts=artifacts,
                segment=found,
                limit=limit,
                known=known,
                with_contacts=with_contacts,
                capability_profile=capability_profile,
                refresh=refresh,
            )
            stored = store.record_prospects(brand_id, prospects)

            reachable = sum(1 for row in stored if any(row.contacts or []))
            invented = sum(row.invented_contacts for row in stored)
            status.state = "done"
            status.found = len(stored)
            if invented:
                # Surfaced rather than logged. The user is about to act on
                # this list, and how much the extractor tried to invent is the
                # single most useful thing they can know about it.
                status.say(
                    f"{invented} contact detail(s) were reported that are nowhere on those "
                    "companies' sites. They were discarded, not shown."
                )
            status.summary = (
                f"{len(stored)} organisation(s) refreshed or added for {found.name}, "
                f"{reachable} with a published way in"
                if stored
                else (
                    f"Nothing new for {found.name}. Either this segment is not enumerable "
                    "the way the map thought, or you already have everyone it can find."
                )
            )
            status.say(status.summary)
        except (MarketError, ModelRuntimeError, CapabilityUnavailableError) as exc:
            logger.info("market: prospect search failed - %s", exc)
            status.state = "failed"
            status.error = str(exc)
            status.say(f"Stopped: {exc}")
        except Exception:  # a background task must not vanish silently
            logger.exception("market: prospect search crashed")
            status.state = "failed"
            status.error = "The prospect search crashed unexpectedly. Check server logs."
            status.say(status.error)
        finally:
            status.finished_at = datetime.now(UTC)


async def _run_audience_research(
    brand_id: UUID,
    provider: AIProvider,
    engine: Engine,
    status: JobStatus,
    *,
    segment: str,
) -> None:
    with Session(engine) as session:
        store = MarketStore(session)
        try:
            demand = store.latest_map(brand_id)
            found = demand.named(segment) if demand is not None else None
            if found is None:
                raise MarketError(
                    "This brand's audience map changed while research was starting. "
                    "Choose the audience again."
                )
            admission = demand.admission_for(found)
            if not admission.researchable:
                raise MarketError(
                    f"'{found.name}' no longer passes audience research admission. "
                    + " ".join(admission.reasons)
                )
            research = await AudienceResearcher(
                _session_for(provider, brand_id, status)
            ).research(found, on_progress=status.say)
            row = store.save_research(brand_id, research, store.latest_map_row(brand_id))
            status.state = "done"
            status.found = len(research.problems) + len(research.buyer_phrases)
            status.summary = (
                f"Audience research v{row.version}: {len(research.sources)} source(s), "
                f"{len(research.problems)} verified problem(s), "
                f"{research.dropped_claims} unverifiable item(s) dropped"
            )
            status.say(status.summary)
        except (
            AudienceResearchError,
            MarketError,
            ModelRuntimeError,
            CapabilityUnavailableError,
        ) as exc:
            logger.info("market: audience research failed - %s", exc)
            status.state = "failed"
            status.error = str(exc)
            status.say(f"Stopped: {exc}")
        except Exception:
            logger.exception("market: audience research crashed")
            status.state = "failed"
            status.error = "Audience research crashed unexpectedly. Check server logs."
            status.say(status.error)
        finally:
            status.finished_at = datetime.now(UTC)


async def _run_relevance_dossier(
    brand_id: UUID,
    provider: AIProvider,
    engine: Engine,
    status: JobStatus,
    *,
    segment: str,
) -> None:
    with Session(engine) as session:
        service = MarketService(session)
        try:
            inputs = service._relevance_inputs(brand_id, segment)
            status.say("Reading the complete Evidence Ledger and current Positioning Map")
            dossier = await RelevanceAnalyst(
                _session_for(provider, brand_id, status)
            ).analyse(
                artifacts=inputs.artifacts,
                knowledge_id=inputs.knowledge_row.id,
                knowledge_version=inputs.knowledge_row.version,
                research=inputs.research,
                research_id=inputs.research_row.id,
                research_version=inputs.research_row.version,
                positioning=inputs.snapshot.positioning,
                market_scan_id=inputs.market_scan_row.id,
                market_scan_version=inputs.market_scan_row.version,
                capability_profile=inputs.capability_profile,
                capability_profile_id=inputs.capability_profile_row.id,
                capability_profile_version=inputs.capability_profile_row.version,
                company_qualifications=inputs.company_qualifications,
                qualification_fingerprint=inputs.qualification_fingerprint,
            )
            row = service.store.save_dossier(brand_id, dossier)
            status.state = "done"
            status.found = (
                len(dossier.ranked_relevance)
                + len(dossier.problem_fits)
                + len(dossier.silences)
            )
            counts = dossier.validation_counts
            status.summary = (
                f"Relevance dossier v{row.generation_version}: "
                f"{len(dossier.ranked_relevance)} ranked fact(s), "
                f"{len(dossier.problem_fits)} problem fit(s), "
                f"{len(dossier.silences)} silence(s); "
                f"{counts.dropped_items} dropped and "
                f"{counts.normalized_items} normalized"
            )
            status.say(status.summary)
        except (MarketError, ModelRuntimeError, RelevanceValidationError) as exc:
            logger.info("market: relevance dossier failed - %s", exc)
            status.state = "failed"
            status.error = str(exc)
            status.say(f"Stopped: {exc}")
        except Exception:
            logger.exception("market: relevance dossier crashed")
            status.state = "failed"
            status.error = "Building the relevance dossier crashed unexpectedly. Check server logs."
            status.say(status.error)
        finally:
            status.finished_at = datetime.now(UTC)


def _qualification_snapshots(
    rows: list[ProspectRow],
    *,
    definition: AudienceDefinition | None = None,
    profile: ProductCapabilityProfile | None = None,
) -> list[QualifiedCompanySnapshot]:
    """Current company-level inputs, with legacy rows explicitly unverified."""
    snapshots: list[QualifiedCompanySnapshot] = []
    for row in rows:
        qualification = prospect_qualification(row)
        if qualification is None:
            qualification = _unverified_company_qualification(
                "legacy_prospect_has_no_qualification"
            )
        elif definition is not None and profile is not None:
            if qualification.stale_reasons(profile):
                qualification = stale_company_qualification(qualification, profile)
            else:
                qualification = qualify_company(
                    definition=definition,
                    profile=profile,
                    evidence=qualification.evidence,
                    requirements=qualification.requirements,
                    unmapped_requirements=qualification.unmapped_requirements,
                    site_verified=row.verified,
                    pages_read=row.pages_read,
                    reachable=bool(prospect_contacts(row)),
                )
        snapshots.append(
            QualifiedCompanySnapshot(
                prospect_id=row.id,
                name=row.name,
                url=row.url,
                qualification=qualification,
            )
        )
    return snapshots


def _unverified_company_qualification(reason: str) -> CompanyQualification:
    return CompanyQualification(
        classification=QualificationClass.UNVERIFIED,
        audience_structure_fit=QualificationDimension.UNKNOWN,
        product_capability_fit=QualificationDimension.UNKNOWN,
        evidence_completeness=EvidenceCompleteness.MISSING,
        reachability=Reachability.UNKNOWN,
        reason_codes=[reason],
    )


def _qualification_fingerprint(
    items: list[QualifiedCompanySnapshot],
    *,
    profile: ProductCapabilityProfile | None = None,
) -> str:
    payload = {
        "capability_profile_version": profile.version if profile is not None else 0,
        "requirement_extractor_version": COMPANY_REQUIREMENT_EXTRACTOR_VERSION,
        "requirement_normalizer_version": COMPANY_REQUIREMENT_NORMALIZER_VERSION,
        "qualifier_version": COMPANY_QUALIFIER_VERSION,
        "companies": [
            item.model_dump(mode="json")
            for item in sorted(items, key=lambda item: str(item.prospect_id))
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _session_for(
    provider: AIProvider, brand_id: UUID, status: JobStatus | None = None
) -> ModelSession:
    """A model session for work that belongs to a brand rather than to a run.

    No observer and no per-call persistence: a market job is not a campaign,
    there is no execution row for its events to belong to, and a scan lost to
    a restart costs a button press. What it does get is `on_call`, which is
    the whole of the tracing story here - every finished call lands on the job
    status, so the page polling it sees which agent ran, on which model, for
    how long and at what cost, without any of that apparatus.
    """
    return ModelSession(
        provider=provider,
        prompt_engine=get_prompt_engine(PROMPTS_DIR),
        events=EventBus(),
        model_router=ModelRouter(),
        execution_id=f"market:{brand_id}",
        on_call=status.record if status is not None else None,
    )
