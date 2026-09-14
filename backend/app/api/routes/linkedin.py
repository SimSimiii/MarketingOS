from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select

from app.api.deps import AIProviderDep, PrincipalDep, SessionDep
from app.api.routes.market import _guard_brand
from app.auth.scope import owned
from app.models.brand import Brand
from app.models.linkedin import LinkedInRun
from app.schemas.linkedin import CriteriaRequest, LinkedInRunRead, MessageRequest, SearchRequest
from app.services.linkedin_service import LinkedInError, launch

router = APIRouter(tags=["linkedin"],
                   dependencies=[Depends(_guard_brand)])


@router.get("/market/{brand_id}/linkedin/runs", response_model=list[LinkedInRunRead])
def list_runs(brand_id: UUID, session: SessionDep) -> list[LinkedInRun]:
    return list(session.exec(select(LinkedInRun).where(LinkedInRun.brand_id == brand_id)
                             .order_by(col(LinkedInRun.created_at).desc()).limit(50)))


@router.post("/market/{brand_id}/linkedin/criteria", response_model=LinkedInRunRead, status_code=202)
async def start_criteria(brand_id: UUID, data: CriteriaRequest, session: SessionDep,
                         provider: AIProviderDep) -> LinkedInRun:
    """Who to look for, proposed from what this brand already knows. Its own
    job rather than a step inside the search, so the proposal can be corrected
    before it is paid for on the open web."""
    try:
        return launch(session, brand_id, provider, data)
    except LinkedInError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/market/{brand_id}/linkedin/search", response_model=LinkedInRunRead, status_code=202)
async def start_search(brand_id: UUID, data: SearchRequest, session: SessionDep,
                       provider: AIProviderDep) -> LinkedInRun:
    try:
        return launch(session, brand_id, provider, data)
    except LinkedInError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/market/{brand_id}/linkedin/messages", response_model=LinkedInRunRead, status_code=202)
async def start_message(brand_id: UUID, data: MessageRequest, session: SessionDep,
                        provider: AIProviderDep) -> LinkedInRun:
    try:
        return launch(session, brand_id, provider, data)
    except LinkedInError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/linkedin/runs", response_model=list[LinkedInRunRead])
def recent_runs(session: SessionDep, principal: PrincipalDep) -> list[LinkedInRun]:
    statement = select(LinkedInRun).join(Brand, Brand.id == LinkedInRun.brand_id)
    statement = owned(statement, Brand, principal)
    return list(session.exec(statement.order_by(col(LinkedInRun.created_at).desc()).limit(20)))
