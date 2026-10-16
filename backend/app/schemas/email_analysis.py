from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmailAnalysisRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    preview_text: str = Field(default="", max_length=1000)
    body: str = Field(min_length=1, max_length=30_000)
    audience: str = Field(default="", max_length=2000)
    objective: str = Field(default="", max_length=2000)
    merge_fields: list[str] = Field(default_factory=list, max_length=30)
    cold_read: bool = False


class AnalysisFinding(BaseModel):
    category: Literal["verification", "editorial", "context"]
    check: str
    detail: str
    action: str


class AnalysisReader(BaseModel):
    reported: bool
    understood: bool | None = None
    what_it_sells: str = ""
    biggest_doubt: str = ""
    stopped_at: str = ""
    would_act: bool | None = None
    situation_matches: bool | None = None
    relevance_feedback: str = ""
    fixes: list[str] = Field(default_factory=list)
    assessment: int | None = None


class EmailAnalysisResult(BaseModel):
    findings: list[AnalysisFinding] = Field(default_factory=list)
    reader: AnalysisReader | None = None
    knowledge_version: int | None = None
    coverage: list[str] = Field(default_factory=list)
    objective: str = ""
    forecast_calls: int = 0


class EmailAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    brand_id: UUID
    state: str
    request: EmailAnalysisRequest
    result: EmailAnalysisResult
    error: str
    calls: int
    input_tokens: int
    output_tokens: int
    created_at: datetime
    completed_at: datetime | None
