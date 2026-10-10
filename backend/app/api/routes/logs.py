from fastapi import APIRouter, Query

from app.api.deps import PrincipalDep, SessionDep
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.schemas.execution_log import ExecutionLogRead

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[ExecutionLogRead])
def list_recent_logs(
    session: SessionDep, principal: PrincipalDep, limit: int = Query(200, ge=1, le=500)
) -> list[ExecutionLogRead]:
    repository = ExecutionLogRepository(session)
    return [
        ExecutionLogRead.model_validate(log)
        for log in repository.list_recent(limit, principal)
    ]
