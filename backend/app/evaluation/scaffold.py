"""The disposable database one benchmark case runs against.

Split out of `runner.py` for one reason: the audience experiment needs to be
able to build exactly the same rows a billed run builds and then assert things
about them without spending anything. A test that constructs its own
approximation of the benchmark's database proves the approximation works.

Nothing here touches the application database. Every caller hands in a session
opened on a temporary SQLite file that is deleted afterwards.

## Scoping, and why the arms all get a brand

`positioning()` and `demand()` on `_DbKnowledgeGateway` are brand-scoped: a
campaign with no `brand_id` gets `None` from both, and `_with_market` returns
the compiled artifacts untouched. Every benchmark round to date created its
campaign without a brand, so the market package has never been inside a
measured run - which is the finding this experiment was built to check and then
to fix.

The fix is not "give the audience arms a brand". It is to give *every* arm of
the experiment a brand, including the arm with no audience intelligence, so the
only difference between them is the demand map and the chosen segment. Brand
scoping moves where documents and artifacts are stored, what `prior_learnings`
looks at, and whether approved proof is merged; in a fresh temporary database
all three answer the same on both sides, but they answer the same *because they
were held constant*, not because nobody looked.

`condition=None` keeps the original campaign-scoped path exactly as it was, so
`runner.py --out` with no experiment behaves as it always has.
"""

from sqlmodel import Session

from app.evaluation.audience import AudienceArm, AudienceCondition, arm_for
from app.evaluation.golden import GoldenCase
from app.market.store import MarketStore
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.knowledge_document import KnowledgeDocument

#: The roles whose prompts the audience experiment reads. Four of the five
#: reasoning roles: the compiler is left out because it runs before any of this
#: exists and reads only the user's own material, so a marker turning up there
#: would mean the fixture had leaked into the corpus.
PROBED_ROLES: tuple[str, ...] = (
    "strategist",
    "email_writer",
    "blind_reader",
    "conversion_critic",
)


class UnknownArm(Exception):
    """Asked for an audience condition this golden case has no fixture for."""


def prepare_case(
    session: Session,
    case: GoldenCase,
    preset: str,
    condition: AudienceCondition | None = None,
) -> Campaign:
    """Write one case's rows and return the campaign a run is built from.

    `condition=None` is the original benchmark: a campaign that owns its own
    documents and belongs to no brand. Any condition at all brand-scopes the
    case - see the module docstring for why that includes `none`.
    """
    if condition is None:
        campaign = Campaign(
            name=f"[eval] {case.name}",
            request=case.request,
            product_description=case.product_description,
            target_market=case.target_market,
            goals=case.goals,
            policy={"preset": preset},
        )
        session.add(campaign)
        session.commit()
        session.refresh(campaign)
        _add_documents(session, case, campaign_id=campaign.id)
        return campaign

    arm = arm_for(case.name, condition)
    if arm is None:
        raise UnknownArm(
            f"golden case {case.name!r} has no hand-written {condition} audience record"
        )

    brand = Brand(name=f"[eval] {case.name}")
    session.add(brand)
    session.commit()
    session.refresh(brand)

    _add_documents(session, case, brand_id=brand.id)
    if arm.demand is not None:
        # Through the store the market pages write to, so the run reads it back
        # through `MarketStore.latest_map` exactly as a real brand campaign
        # does. Nothing here injects text into a prompt.
        MarketStore(session).save_map(brand.id, arm.demand)

    campaign = Campaign(
        name=f"[eval] {case.name} [{condition}]",
        brand_id=brand.id,
        request=case.request,
        product_description=case.product_description,
        target_market=case.target_market,
        goals=case.goals,
        audience_segment=arm.chosen or None,
        policy={"preset": preset},
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    return campaign


def _add_documents(
    session: Session, case: GoldenCase, *, brand_id=None, campaign_id=None
) -> None:
    for title, content in case.documents:
        session.add(
            KnowledgeDocument(
                brand_id=brand_id,
                campaign_id=campaign_id,
                title=title,
                source_type="markdown",
                content=content,
            )
        )
    session.commit()


def describe(arm: AudienceArm | None) -> str:
    """One line naming what a run was pointed at, for a progress log."""
    if arm is None or arm.demand is None:
        return "no audience map - the run works from the company's own material"
    segment = arm.segment
    if segment is None:
        return f"a map of {len(arm.demand.segments)} segment(s), none chosen"
    return (
        f"{len(arm.demand.segments)} segment(s) mapped, written to {segment.name!r} "
        f"({round(segment.fit * 100)}% estimated to bite)"
    )
