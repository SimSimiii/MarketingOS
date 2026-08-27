"""Building a pipeline around a gateway a test has already constructed.

`test_pipeline.build` makes the gateway itself, which is right for the great
majority of tests - they care about what the pipeline does with knowledge, not
about where it came from. The audience tests care about the gateway: what a
run is told about the market, and which buyer it was pointed at, are both
answers the gateway gives, so they have to hand one in.
"""

from app.marketing.pipeline import EmailCampaignPipeline
from app.marketing.policy import ExecutionPolicy
from tests.marketing.conftest import (
    FakeKnowledgeGateway,
    RoleScriptedProvider,
    make_session,
)


def build_with_gateway(
    provider: RoleScriptedProvider,
    policy: ExecutionPolicy,
    gateway: FakeKnowledgeGateway,
    **kwargs,
) -> EmailCampaignPipeline:
    return EmailCampaignPipeline(
        session=make_session(provider),
        knowledge=gateway,
        policy=policy,
        **kwargs,
    )
