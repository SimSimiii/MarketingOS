from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Brand(SQLModel, table=True):
    """One business the system knows about, and the scope its knowledge lives in.

    Knowledge belongs here rather than on a campaign because a company does not
    change between two of its own campaigns. Compiling their site, their prices
    and their voice once and reusing it is the difference between a second
    campaign starting from everything the first one learned and starting from
    an empty page.

    Campaigns may still run without a brand - a one-off keeps its knowledge to
    itself, scoped to the campaign. See app.knowledge.store.ArtifactScope.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    website_url: str | None = None
    #: How this brand's email looks when it is rendered as HTML. Kept to the
    #: few things a reader would actually notice, all optional: an email with
    #: none of them set still renders, in the typographic tier that is the
    #: right answer for cold mail anyway. See app.marketing.render_html.
    logo_url: str | None = None
    #: Hex, used for the link and the button.
    primary_color: str | None = None
    #: Who is sending this, and any postal address the user's jurisdiction
    #: requires, one line per entry.
    footer_lines: list[str] | None = Field(default=None, sa_column=Column(JSON))
    #: Where the footer's "Unsubscribe" points. Marketing mail is required to
    #: carry one almost everywhere this will be sent, and the line is rendered
    #: only when there is somewhere for it to go - a dead unsubscribe link is
    #: what turns an unsubscribe into a spam report.
    unsubscribe_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
