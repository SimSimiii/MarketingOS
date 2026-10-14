"""Recover accepted emails after a process failure, without calling a model."""

import logging
from uuid import UUID

from sqlmodel import Session, select

from app.marketing.email_copy import Email
from app.marketing.render_html import BrandStyle, text_alternative
from app.models.agent_execution import AgentExecution
from app.models.campaign import Campaign
from app.models.campaign_execution import CampaignExecution
from app.models.enums import AssetType
from app.models.generated_asset import GeneratedAsset

logger = logging.getLogger("marketingos.checkpoints")


def recover_accepted_emails(session: Session, execution: CampaignExecution) -> int:
    """Flush recovered rows; the caller commits them with the terminal status.

    Only the acceptance hook writes these checkpoints. They passed individual
    gates, but may not have reached the sequence review. Keep that distinction
    visible instead of presenting them as the finished campaign.
    """
    assets = session.exec(select(GeneratedAsset).where(
        GeneratedAsset.campaign_execution_id == execution.id
    )).all()
    existing_positions = {asset.position for asset in assets}
    campaign = session.get(Campaign, execution.campaign_id)
    # A recovered checkpoint has no final brief. Preserve only the user's
    # explicit destination rather than guessing the strategy's selected URL.
    style = BrandStyle(cta_url=(campaign.cta_url or "") if campaign else "")
    recovered = 0
    checkpoints = (execution.result or {}).get("accepted_checkpoints", {})
    if not isinstance(checkpoints, dict):
        logger.warning("Invalid checkpoint collection for execution %s", execution.id)
        return len(assets)
    for checkpoint in checkpoints.values():
        try:
            email = Email.model_validate(checkpoint["email"])
            agent = session.get(AgentExecution, UUID(checkpoint["agent_execution_id"]))
            if agent is None or agent.campaign_execution_id != execution.id:
                continue
            if email.position in existing_positions:
                continue
            session.add(GeneratedAsset(
                campaign_execution_id=execution.id,
                agent_execution_id=agent.id,
                asset_type=AssetType.EMAIL,
                title=email.subject,
                content=text_alternative(email, style),
                position=email.position,
                asset_metadata={
                    **email.model_dump(mode="json"),
                    "checkpoint": True,
                    "sequence_review_pending": True,
                    "pull": checkpoint.get("pull"),
                },
            ))
            existing_positions.add(email.position)
            recovered += 1
        except (KeyError, ValueError, TypeError):
            logger.warning("Invalid checkpoint for execution %s", execution.id, exc_info=True)
    session.flush()
    return len(assets) + recovered
