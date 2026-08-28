"""One pass over a brand's market, start to finish.

Same shape as the campaign pipeline and for the same reason: the order of work
is fixed by data dependencies, so nothing here spends a model call deciding
what happens next. Find who the competitors are, read their pages, compute
where we stand, compare it to last time. Four steps, in that order, always.

What it costs is arithmetic, and it is small: one search call, one extraction
call per competitor, and nothing else. Everything after the extractions -
territory, crowd vocabulary, the whole radar diff - is code, and free.
"""

import logging
from collections.abc import Callable

from pydantic import BaseModel, Field

from app.knowledge.artifacts import KnowledgeArtifacts
from app.market import positioning as positioning_module
from app.market.radar import MarketSnapshot, RadarEvent, diff
from app.market.rivals import RivalLead, RivalScout
from app.marketing.preflight import PROOF_KINDS
from app.runtime.model_session import ModelSession

logger = logging.getLogger("marketingos.market")

#: A progress line for the caller to show, so a scan that takes a minute is
#: not a spinner. Same contract as the knowledge compiler's `on_progress`.
type Progress = Callable[[str, str], None]


class ScanResult(BaseModel):
    snapshot: MarketSnapshot
    events: list[RadarEvent] = Field(default_factory=list)
    #: Competitors the scout proposed that were not already on the list. The
    #: caller persists these; the scanner does not touch the database.
    discovered: list[RivalLead] = Field(default_factory=list)
    #: Whether the open web was read at all this time round. A rescan of a
    #: known list never needs it, and saying so is what stops a user assuming
    #: every scan re-searched the market.
    searched_web: bool = False
    notes: list[str] = Field(default_factory=list)


class MarketScanner:
    def __init__(self, session: ModelSession, scout: RivalScout | None = None) -> None:
        self._session = session
        self._scout = scout or RivalScout(session)

    async def scan(
        self,
        *,
        artifacts: KnowledgeArtifacts,
        known: list[RivalLead],
        previous: MarketSnapshot | None = None,
        discover: bool = True,
        on_progress: Progress | None = None,
    ) -> ScanResult:
        """Read the market once.

        `discover` is separated from the rest because it is the only step that
        reads the open web, and it is the only one whose answer a user might
        reasonably not want re-derived: somebody who has curated their
        competitor list wants those five companies re-read, not a sixth
        proposed every Monday.
        """
        say = on_progress or (lambda stage, message: None)
        notes: list[str] = []

        leads = list(known)
        discovered: list[RivalLead] = []
        if discover:
            say("discover", "Searching for who this buyer is really deciding between")
            found = await self._scout.discover(
                artifacts.business, known=[lead.name for lead in leads]
            )
            existing = {lead.name.strip().lower() for lead in leads}
            discovered = [
                lead
                for lead in found.leads
                if lead.name.strip().lower() not in existing
            ]
            leads.extend(discovered)
            say(
                "discover",
                f"{len(discovered)} competitor(s) found that were not on the list"
                + (f" - searched: {'; '.join(found.searched[:3])}" if found.searched else ""),
            )

        if not leads:
            notes.append(
                "Nobody is on the competitor list and the search found no one, so there is "
                "no field to position against."
            )
            return ScanResult(
                snapshot=MarketSnapshot(),
                searched_web=discover,
                notes=notes,
            )

        say("profile", f"Reading {len(leads)} competitor site(s)")
        profiles = await self._scout.profile_all(leads)
        readable = [profile for profile in profiles if profile.verified]
        say(
            "profile",
            f"{len(readable)} of {len(profiles)} site(s) read, "
            f"{sum(len(profile.claims.claims) for profile in readable)} claim(s) verified",
        )
        if unread := [profile for profile in profiles if not profile.verified]:
            notes.append(
                f"{len(unread)} competitor site(s) could not be read: "
                + ", ".join(profile.name for profile in unread)
            )

        say("position", "Working out what only this company can say")
        ours = positioning_module.claims_from_knowledge(artifacts)
        snapshot = MarketSnapshot(
            rivals=profiles,
            positioning=positioning_module.build(
                ours, profiles, we_have_proof=_we_have_proof(artifacts)
            ),
        )
        say("position", snapshot.positioning.summary())

        events: list[RadarEvent] = []
        if previous is not None and previous.rivals:
            events = diff(previous, snapshot)
            say(
                "radar",
                f"{len(events)} change(s) since the last scan"
                if events
                else "nothing has moved since the last scan",
            )

        return ScanResult(
            snapshot=snapshot,
            events=events,
            discovered=discovered,
            searched_web=discover,
            notes=notes,
        )


def _we_have_proof(artifacts: KnowledgeArtifacts) -> bool:
    """Whether anybody outside this company has vouched for it.

    Deliberately the same definition the campaign preflight uses, imported
    rather than restated: two places deciding "do we have proof" by two
    slightly different rules is how a positioning map and a run report end up
    disagreeing about the same business on the same day.
    """
    return bool(artifacts.evidence.of_kind(*PROOF_KINDS))
