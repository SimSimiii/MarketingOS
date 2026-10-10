from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from app.api.deps import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(session: SessionDep) -> dict[str, str]:
    """Database readiness without spending model quota or exposing connection details."""
    try:
        session.exec(select(1)).one()
    except SQLAlchemyError as exc:
        raise HTTPException(503, "The workspace database is temporarily unavailable.") from exc
    return {"status": "ready"}
