from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CampaignServiceDep
from app.schemas.campaign import (
    CampaignCreateRequest,
    CampaignExecutionRead,
    CampaignPolicyUpdate,
    CampaignRead,
)
from app.services.campaign_service import (
    CampaignAlreadyRunningError,
    NoExecutionToRestartError,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(data: CampaignCreateRequest, service: CampaignServiceDep) -> CampaignRead:
    campaign = service.create_campaign(data)
    return CampaignRead.model_validate(campaign)


@router.get("", response_model=list[CampaignRead])
def list_campaigns(
    service: CampaignServiceDep, include_archived: bool = False
) -> list[CampaignRead]:
    latest = service.latest_run_by_campaign()
    campaigns = []
    for campaign in service.list_campaigns(include_archived):
        read = CampaignRead.model_validate(campaign)
        run = latest.get(campaign.id)
        if run is not None:
            read.last_run_status, read.last_run_at = run
        campaigns.append(read)
    return campaigns


@router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: UUID, service: CampaignServiceDep) -> CampaignRead:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return CampaignRead.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: UUID, service: CampaignServiceDep) -> None:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    try:
        service.delete_campaign(campaign)
    except CampaignAlreadyRunningError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


@router.post("/{campaign_id}/archive", response_model=CampaignRead)
def archive_campaign(campaign_id: UUID, service: CampaignServiceDep) -> CampaignRead:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return CampaignRead.model_validate(service.archive_campaign(campaign))


@router.post("/{campaign_id}/unarchive", response_model=CampaignRead)
def unarchive_campaign(campaign_id: UUID, service: CampaignServiceDep) -> CampaignRead:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return CampaignRead.model_validate(service.unarchive_campaign(campaign))


@router.post("/{campaign_id}/duplicate", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def duplicate_campaign(campaign_id: UUID, service: CampaignServiceDep) -> CampaignRead:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return CampaignRead.model_validate(service.duplicate_campaign(campaign))


@router.put("/{campaign_id}/policy", response_model=CampaignRead)
def update_campaign_policy(
    campaign_id: UUID, data: CampaignPolicyUpdate, service: CampaignServiceDep
) -> CampaignRead:
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    return CampaignRead.model_validate(service.update_policy(campaign, data))


@router.post(
    "/{campaign_id}/start",
    response_model=CampaignExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_campaign(campaign_id: UUID, service: CampaignServiceDep) -> CampaignExecutionRead:
    """Hand the campaign to the pipeline. Returns immediately with
    the new execution in RUNNING state - the run itself continues in the
    background; poll GET /executions/{id}/status or open
    GET /executions/{id}/stream to watch it happen live."""
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    try:
        execution = await service.start_execution(campaign)
    except CampaignAlreadyRunningError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return CampaignExecutionRead.model_validate(execution)


@router.post(
    "/{campaign_id}/restart",
    response_model=CampaignExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def restart_campaign(campaign_id: UUID, service: CampaignServiceDep) -> CampaignExecutionRead:
    """Start a fresh run of a campaign that has run before (typically after
    a failed or cancelled execution) - same as /start, but 404s instead of
    silently behaving like a first run when there is nothing to restart."""
    campaign = service.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found")
    try:
        execution = await service.restart_execution(campaign)
    except NoExecutionToRestartError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except CampaignAlreadyRunningError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return CampaignExecutionRead.model_validate(execution)


@router.get("/{campaign_id}/executions", response_model=list[CampaignExecutionRead])
def list_campaign_executions(
    campaign_id: UUID, service: CampaignServiceDep
) -> list[CampaignExecutionRead]:
    return [CampaignExecutionRead.model_validate(e) for e in service.list_executions(campaign_id)]
