"""The first screen: how many accounts, on what plans, spending what."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from .. import service
from ..auth import CurrentAdminDep
from ..db import get_session
from ..schemas import OverviewResponse, TimeseriesResponse

router = APIRouter(prefix="/api", tags=["overview"])


@router.get("/overview", response_model=OverviewResponse)
def get_overview(
    session: Annotated[Session, Depends(get_session)], _: CurrentAdminDep
) -> OverviewResponse:
    return service.overview(session)


@router.get("/stats/timeseries", response_model=TimeseriesResponse)
def get_timeseries(
    session: Annotated[Session, Depends(get_session)],
    _: CurrentAdminDep,
    metric: str = Query(default="signups", description="signups | runs | campaigns"),
    days: int = Query(default=30, ge=1, le=365),
) -> TimeseriesResponse:
    return TimeseriesResponse(
        metric=metric, days=days, series=service.timeseries(session, metric, days)
    )
