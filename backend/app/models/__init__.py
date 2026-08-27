"""SQLModel table models.

Importing every model module here ensures they are registered on
SQLModel.metadata before `init_db()` / Alembic autogenerate run.
"""

from app.models.agent_execution import AgentExecution
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import (
    AssetType,
    ExecutionStatus,
    LogLevel,
)
from app.models.execution_log import ExecutionLog
from app.models.generated_asset import GeneratedAsset
from app.models.knowledge_artifacts import KnowledgeArtifactSet
from app.models.knowledge_document import KnowledgeDocument
from app.models.market import (
    AudienceMapRow,
    MarketScan,
    ProofCandidateRow,
    ProspectRow,
    RadarEventRow,
    Rival,
)
from app.models.user_settings import UserSettings

__all__ = [
    "AgentExecution",
    "AssetType",
    "AudienceMapRow",
    "Brand",
    "Campaign",
    "CampaignExecution",
    "ExecutionLog",
    "ExecutionStatus",
    "GeneratedAsset",
    "KnowledgeArtifactSet",
    "KnowledgeDocument",
    "LogLevel",
    "MarketScan",
    "ProofCandidateRow",
    "ProspectRow",
    "RadarEventRow",
    "Rival",
    "UserSettings",
]
