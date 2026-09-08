from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.ai.base import AIProvider
from app.ai.factory import get_ai_provider
from app.auth.dependencies import CurrentUserDep, PrincipalDep
from app.auth.principal import Principal
from app.core.database import get_session
from app.services.campaign_service import CampaignService
from app.services.knowledge_service import KnowledgeService
from app.services.settings_service import SettingsService

SessionDep = Annotated[Session, Depends(get_session)]
AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]

#: Re-exported so routes have one import for "what a handler needs". The
#: definitions live in app.auth.dependencies, which knows nothing about
#: services and can therefore be imported by them.
__all__ = [
    "AIProviderDep",
    "CampaignServiceDep",
    "CurrentUserDep",
    "KnowledgeServiceDep",
    "Principal",
    "PrincipalDep",
    "SessionDep",
    "SettingsServiceDep",
]


def get_campaign_service(
    session: SessionDep, ai_provider: AIProviderDep, principal: PrincipalDep
) -> CampaignService:
    return CampaignService(session, ai_provider, principal)


def get_knowledge_service(session: SessionDep) -> KnowledgeService:
    return KnowledgeService(session)


def get_settings_service(session: SessionDep, principal: PrincipalDep) -> SettingsService:
    return SettingsService(session, principal)


CampaignServiceDep = Annotated[CampaignService, Depends(get_campaign_service)]
KnowledgeServiceDep = Annotated[KnowledgeService, Depends(get_knowledge_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
