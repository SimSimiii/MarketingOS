from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.core.database import get_session
from app.services.campaign_service import CampaignService
from app.services.knowledge_service import KnowledgeService
from app.services.settings_service import SettingsService

SessionDep = Annotated[Session, Depends(get_session)]
AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]


def get_campaign_service(session: SessionDep, ai_provider: AIProviderDep) -> CampaignService:
    return CampaignService(session, ai_provider)


def get_knowledge_service(session: SessionDep) -> KnowledgeService:
    return KnowledgeService(session)


def get_settings_service(session: SessionDep) -> SettingsService:
    return SettingsService(session)


CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]
KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
