"""Market intelligence, per brand.

Everything is scoped to a brand rather than to a campaign, and that is a
product decision rather than a routing one: a market belongs to the business,
outlives any one campaign, and is the reason a second campaign starts from
more than the first one did.
"""

import csv
import io
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import AIProviderDep, SessionDep
from app.core.database import engine
from app.market.demand import ContactKind, ProspectStatus, contacts_of
from app.market.proof import ProofStatus
from app.market.store import prospect_contacts, unseen_alerts
from app.marketing.preflight import PROOF_KINDS
from app.models.brand import Brand
from app.models.market import ProofCandidateRow, ProspectRow, Rival
from app.repositories.brand_repository import BrandRepository
from app.schemas.market import (
    AudienceRead,
    DemandMapRead,
    JobStatusRead,
    MapAudienceRequest,
    MarketRead,
    ProofCandidateRead,
    ProofDecision,
    ProspectDecision,
    ProspectRead,
    ProspectSearchRequest,
    RadarEventRead,
    RivalCreate,
    RivalMuteUpdate,
    RivalRead,
    ScanRequest,
    proof_reads,
    prospect_reads,
    radar_reads,
)
from app.services.market_service import MarketError, MarketService, all_jobs, job_for

router = APIRouter(prefix="/market", tags=["market"])


#: Every route below that launches a job is `async def`, and it has to be.
#:
#: FastAPI runs a *sync* handler in an anyio worker thread, where there is no
#: running event loop - so `asyncio.create_task` inside one raises
#: `RuntimeError: no running event loop` and the job never starts. An `async
#: def` handler runs on the loop itself, which is where the task belongs and
#: which is what `campaigns.start_campaign` has always done.
#:
#: The handlers stay otherwise synchronous: they do a handful of small SQLite
#: reads before handing off, exactly as the campaign start route does, and the
#: work that takes minutes is in the task rather than in the request.


def _brand(session: SessionDep, brand_id: UUID) -> Brand:
    brand = BrandRepository(session).get(brand_id)
    if brand is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found")
    return brand


def _rival(session: SessionDep, brand_id: UUID, rival_id: UUID) -> Rival:
    row = session.get(Rival, rival_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Competitor not found")
    return row


def _candidate(session: SessionDep, brand_id: UUID, proof_id: UUID) -> ProofCandidateRow:
    row = session.get(ProofCandidateRow, proof_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proof candidate not found")
    return row


def _prospect(session: SessionDep, brand_id: UUID, prospect_id: UUID) -> ProspectRow:
    row = session.get(ProspectRow, prospect_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prospect not found")
    return row


@router.get("/jobs", response_model=list[JobStatusRead])
def read_jobs() -> list[JobStatusRead]:
    """Every market job this process knows about, running ones first.

    Declared before `/{brand_id}/...` because "jobs" would otherwise be read
    as a brand id and fail UUID parsing. Not brand-scoped, and deliberately:
    this is what the live board asks, and the question there is "what is
    happening anywhere", not "what is happening to this business".
    """
    return [JobStatusRead(**vars(job)) for job in all_jobs()]


@router.get("/{brand_id}", response_model=MarketRead)
def read_market(brand_id: UUID, session: SessionDep) -> MarketRead:
    """Everything the market page shows, in one request."""
    _brand(session, brand_id)
    service = MarketService(session)
    snapshot = service.snapshot(brand_id)
    note = ""
    if snapshot is None:
        note = (
            "Nothing has been scanned yet. A scan finds who this buyer is really deciding "
            "between, reads their pages, and works out which of your claims are yours alone."
        )
    elif (artifacts := service.artifacts_for(brand_id)) is not None:
        # Whether *we* can name a customer is the one thing on this map that
        # is about us rather than about the field, and it is the thing the
        # user is most likely to have just changed - by approving a
        # testimonial in the tab next to this one. Read from current knowledge
        # rather than from the snapshot, or the banner keeps saying "you name
        # none" to somebody who fixed it a minute ago and has to run a whole
        # scan to be told so.
        snapshot.positioning.we_have_proof = bool(
            artifacts.evidence.of_kind(*PROOF_KINDS)
        )
    demand = service.demand(brand_id)
    return MarketRead.of(
        brand_id=brand_id,
        snapshot=snapshot,
        rivals=service.rivals(brand_id),
        pending_proof=len(service.proof_queue(brand_id, ProofStatus.PENDING)),
        unseen_alerts=unseen_alerts(service.store.radar(brand_id, limit=200)),
        audience_segments=len(demand.segments) if demand else 0,
        prospects=len(service.prospects(brand_id)),
        note=note,
    )


# ---------------------------------------------------------------- competitors


@router.get("/{brand_id}/rivals", response_model=list[RivalRead])
def list_rivals(brand_id: UUID, session: SessionDep) -> list[RivalRead]:
    _brand(session, brand_id)
    return [
        RivalRead.model_validate(rival) for rival in MarketService(session).rivals(brand_id)
    ]


@router.post(
    "/{brand_id}/rivals", response_model=RivalRead, status_code=status.HTTP_201_CREATED
)
def add_rival(brand_id: UUID, data: RivalCreate, session: SessionDep) -> RivalRead:
    """Add a competitor by hand.

    The user's own list is the authority. A scan proposes; this is where
    somebody who knows the market says who is really in it.
    """
    _brand(session, brand_id)
    if not data.name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A competitor needs a name")
    rival = MarketService(session).add_rival(
        brand_id, name=data.name, url=data.url, kind=data.kind, why=data.why
    )
    return RivalRead.model_validate(rival)


@router.patch("/{brand_id}/rivals/{rival_id}", response_model=RivalRead)
def mute_rival(
    brand_id: UUID, rival_id: UUID, data: RivalMuteUpdate, session: SessionDep
) -> RivalRead:
    """Take a competitor out of the map without forgetting the decision -
    otherwise the next scan proposes it again."""
    rival = _rival(session, brand_id, rival_id)
    return RivalRead.model_validate(MarketService(session).set_muted(rival, data.muted))


@router.delete("/{brand_id}/rivals/{rival_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rival(brand_id: UUID, rival_id: UUID, session: SessionDep) -> None:
    MarketService(session).delete_rival(_rival(session, brand_id, rival_id))


# ----------------------------------------------------------------- scanning


@router.post("/{brand_id}/scan", response_model=JobStatusRead, status_code=status.HTTP_202_ACCEPTED)
async def start_scan(
    brand_id: UUID, data: ScanRequest, session: SessionDep, provider: AIProviderDep
) -> JobStatusRead:
    brand = _brand(session, brand_id)
    try:
        job = MarketService(session).launch_scan(
            brand, provider, engine, discover=data.discover
        )
    except MarketError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return JobStatusRead(**vars(job))


@router.post(
    "/{brand_id}/proof/hunt",
    response_model=JobStatusRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_proof_hunt(
    brand_id: UUID, session: SessionDep, provider: AIProviderDep
) -> JobStatusRead:
    brand = _brand(session, brand_id)
    try:
        job = MarketService(session).launch_proof_hunt(brand, provider, engine)
    except MarketError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return JobStatusRead(**vars(job))


@router.get("/{brand_id}/job", response_model=JobStatusRead | None)
def read_job(brand_id: UUID, session: SessionDep) -> JobStatusRead | None:
    """Where the running (or last finished) scan or hunt got to.

    Polled rather than streamed: a scan is a handful of calls, and the whole
    SSE apparatus exists for runs that produce a timeline somebody watches.
    """
    _brand(session, brand_id)
    job = job_for(brand_id)
    return JobStatusRead(**vars(job)) if job is not None else None



# ----------------------------------------------------------------- audience


@router.get("/{brand_id}/audience", response_model=AudienceRead)
def read_audience(
    brand_id: UUID, session: SessionDep, segment: str | None = None
) -> AudienceRead:
    """The demand map and every organisation found for it, in one request.

    `segment` narrows the prospect list without touching the map, which is
    what the page does when the user clicks into one buyer: the map is the
    context for reading the list, so hiding it would make the numbers beside
    each name mean nothing.
    """
    _brand(session, brand_id)
    service = MarketService(session)
    demand = service.demand(brand_id)
    note = ""
    if demand is None:
        note = (
            "Nobody has mapped this brand's demand yet. Until somebody does, every campaign "
            "is written to the audience this company describes on its own website - which is "
            "the audience it set out to have, not necessarily the one most likely to answer."
        )
    return AudienceRead(
        brand_id=brand_id,
        map=DemandMapRead.of(demand) if demand is not None else None,
        prospects=prospect_reads(service.prospects(brand_id, segment)),
        note=note,
    )


@router.post(
    "/{brand_id}/audience/map",
    response_model=JobStatusRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_audience_map(
    brand_id: UUID,
    data: MapAudienceRequest,
    session: SessionDep,
    provider: AIProviderDep,
) -> JobStatusRead:
    """Work out who would actually buy this.

    Deliberately a market job and not part of the knowledge compile. The
    compiler reads what this company published and is right to stay inside it;
    this reads the open web to find the buyers that material could not contain,
    and folding the two together would mean every recompile re-billed a search
    of the whole market.
    """
    brand = _brand(session, brand_id)
    try:
        job = MarketService(session).launch_audience_map(brand, provider, engine)
    except MarketError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return JobStatusRead(**vars(job))


@router.post(
    "/{brand_id}/audience/prospects",
    response_model=JobStatusRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_prospect_search(
    brand_id: UUID,
    data: ProspectSearchRequest,
    session: SessionDep,
    provider: AIProviderDep,
) -> JobStatusRead:
    """Name real organisations that match one mapped segment.

    Every contact detail this produces was read off a page the server fetched
    and checked back against it, so the list is short and it is real - see
    `app.market.demand`. Nothing here writes to anybody; it finds published
    addresses and hands them to the person whose campaign it is.
    """
    brand = _brand(session, brand_id)
    try:
        job = MarketService(session).launch_prospect_search(
            brand,
            provider,
            engine,
            segment=data.segment,
            limit=data.limit,
            with_contacts=data.with_contacts,
        )
    except MarketError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return JobStatusRead(**vars(job))


@router.get("/{brand_id}/prospects", response_model=list[ProspectRead])
def list_prospects(
    brand_id: UUID,
    session: SessionDep,
    segment: str | None = None,
    status_filter: str | None = None,
) -> list[ProspectRead]:
    _brand(session, brand_id)
    wanted = ProspectStatus(status_filter) if status_filter else None
    return prospect_reads(MarketService(session).prospects(brand_id, segment, wanted))


@router.post("/{brand_id}/prospects/{prospect_id}", response_model=ProspectRead)
def decide_prospect(
    brand_id: UUID, prospect_id: UUID, data: ProspectDecision, session: SessionDep
) -> ProspectRead:
    """Keep or dismiss one organisation.

    A dismissal is kept rather than deleted, for the same reason a muted
    competitor is: the next search would only find them again, and a list that
    re-offers a company the user already rejected is a list they stop reading.
    """
    row = _prospect(session, brand_id, prospect_id)
    try:
        wanted = ProspectStatus(data.status)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"'{data.status}' is not a prospect status. Use 'kept' or 'dismissed'.",
        ) from exc
    return ProspectRead.of(MarketService(session).decide_prospect(row, wanted))


@router.delete(
    "/{brand_id}/prospects/{prospect_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_prospect(brand_id: UUID, prospect_id: UUID, session: SessionDep) -> None:
    MarketService(session).delete_prospect(_prospect(session, brand_id, prospect_id))


@router.get("/{brand_id}/prospects.csv")
def export_prospects(
    brand_id: UUID, session: SessionDep, segment: str | None = None
) -> Response:
    """The kept list, as a file.

    Here because a prospect list that cannot leave the product is a demo. The
    people who use this already have somewhere they send mail from, and the
    honest thing is to hand them the rows rather than to build a worse mail
    client to keep them here.

    Only `kept` rows are exported. `new` means nobody has looked at it yet,
    and a file that quietly includes unreviewed rows defeats the entire point
    of the review - the user believes they exported the eleven they checked.
    """
    _brand(session, brand_id)
    rows = MarketService(session).prospects(brand_id, segment, ProspectStatus.KEPT)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "name",
            "website",
            "segment",
            "what_they_do",
            "why_them",
            "fit",
            "emails",
            "phones",
            "contact_form",
            "source_of_contacts",
            "caveat",
        ]
    )
    for row in rows:
        contacts = prospect_contacts(row)
        writer.writerow(
            [
                row.name,
                row.url,
                row.segment,
                row.what_they_do,
                row.why_them,
                f"{row.fit:.2f}",
                contacts_of(contacts, ContactKind.EMAIL),
                contacts_of(contacts, ContactKind.PHONE),
                contacts_of(contacts, ContactKind.FORM),
                # The page every address was read on travels with it. A
                # contact whose provenance was dropped at the door is one
                # nobody downstream can check, and this list is going to be
                # mailed.
                "; ".join(
                    sorted({contact.source for contact in contacts if contact.source})
                ),
                row.caveat,
            ]
        )

    return Response(
        # utf-8-sig, i.e. with a BOM: Excel opens a plain UTF-8 CSV as the
        # local codepage, and a European prospect list is mostly accented
        # company names.
        content=buffer.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="prospects-{brand_id}.csv"'
        },
    )


# -------------------------------------------------------------------- proof


@router.get("/{brand_id}/proof", response_model=list[ProofCandidateRead])
def list_proof(
    brand_id: UUID, session: SessionDep, status_filter: str | None = None
) -> list[ProofCandidateRead]:
    _brand(session, brand_id)
    wanted = ProofStatus(status_filter) if status_filter else None
    return proof_reads(MarketService(session).proof_queue(brand_id, wanted))


@router.post("/{brand_id}/proof/{proof_id}", response_model=ProofCandidateRead)
def decide_proof(
    brand_id: UUID, proof_id: UUID, data: ProofDecision, session: SessionDep
) -> ProofCandidateRead:
    """Approve or reject one found proof.

    Approving it is what turns it into a fact the copy may spend: it enters
    the evidence ledger on the next run, the writer may cite it, and the
    evidence gate licenses the words in it. That is why a human decides and
    not a confidence score.
    """
    row = _candidate(session, brand_id, proof_id)
    return ProofCandidateRead.model_validate(
        MarketService(session).decide_proof(row, data.approved)
    )


# -------------------------------------------------------------------- radar


@router.get("/{brand_id}/radar", response_model=list[RadarEventRead])
def read_radar(brand_id: UUID, session: SessionDep, limit: int = 50) -> list[RadarEventRead]:
    _brand(session, brand_id)
    return radar_reads(MarketService(session).store.radar(brand_id, limit=limit))


@router.post("/{brand_id}/radar/seen", response_model=dict[str, int])
def mark_seen(brand_id: UUID, session: SessionDep) -> dict[str, int]:
    _brand(session, brand_id)
    return {"marked": MarketService(session).mark_radar_seen(brand_id)}
