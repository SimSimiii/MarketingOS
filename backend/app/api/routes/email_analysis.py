from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select

from app.api.deps import AIProviderDep, SessionDep
from app.api.routes.market import _guard_brand
from app.core.config import get_settings
from app.models.email_analysis import EmailAnalysis
from app.schemas.email_analysis import (
    EmailAnalysisCapabilities,
    EmailAnalysisRead,
    EmailAnalysisRequest,
)
from app.services.email_analysis_service import EmailAnalysisError, checks, launch

router = APIRouter(prefix="/market/{brand_id}/email-analyses", tags=["email-analysis"],
                   dependencies=[Depends(_guard_brand)])


@router.get("", response_model=list[EmailAnalysisRead])
def history(brand_id: UUID, session: SessionDep) -> list[EmailAnalysis]:
    return list(session.exec(select(EmailAnalysis).where(EmailAnalysis.brand_id == brand_id)
                             .order_by(col(EmailAnalysis.created_at).desc()).limit(30)))


@router.get("/capabilities", response_model=EmailAnalysisCapabilities)
def capabilities(brand_id: UUID) -> EmailAnalysisCapabilities:
    available = not get_settings().credit_billing_enabled
    return EmailAnalysisCapabilities(cold_read_available=available,
                                     reason="" if available else "Cold reads are unavailable in credit billing mode. Immediate checks remain available.")


@router.get("/{analysis_id}", response_model=EmailAnalysisRead)
def read(brand_id: UUID, analysis_id: UUID, session: SessionDep) -> EmailAnalysis:
    row = session.get(EmailAnalysis, analysis_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(404, "Email analysis not found")
    return row


@router.post("", response_model=EmailAnalysisRead, status_code=202)
async def start(brand_id: UUID, data: EmailAnalysisRequest, session: SessionDep,
                provider: AIProviderDep) -> EmailAnalysis:
    try:
        return launch(session, brand_id, provider, data) if data.cold_read else checks(session, brand_id, data)
    except EmailAnalysisError as exc:
        raise HTTPException(409, str(exc)) from exc
