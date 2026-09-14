from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

#: One line of a targeting criterion - a role, an industry, a signal. Bounded
#: because every one of them is pasted into a search prompt.
Criterion = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def linkedin_url(value: str) -> str:
    parts = urlsplit(value.strip())
    host = (parts.hostname or "").lower()
    path = parts.path.rstrip("/")
    segments = path.split("/")
    if (parts.scheme != "https" or parts.username or parts.password or parts.port
        or not (host == "linkedin.com" or host.endswith(".linkedin.com"))
        or len(segments) != 3 or segments[1] not in {"in", "company"} or not segments[2]):
        raise ValueError("Use an HTTPS LinkedIn /in/profile or /company/account URL")
    return urlunsplit(("https", "www.linkedin.com", path, "", ""))


class TargetingCriteria(BaseModel):
    """Who is worth looking for, decided before anybody has been found.

    The user is not expected to know how to describe their own buyer in search
    terms - the business's own material and its audience map already contain
    that, which is why this can be proposed rather than typed. It is a
    proposal and not a decision: it comes back to the form, where it can be
    corrected before it costs a search.
    """

    model_config = ConfigDict(str_strip_whitespace=True, populate_by_name=True)

    roles: list[Criterion] = Field(default_factory=list, max_length=12)
    industries: list[Criterion] = Field(default_factory=list, max_length=12)
    company_sizes: list[Criterion] = Field(default_factory=list, max_length=6)
    geographies: list[Criterion] = Field(default_factory=list, max_length=8)
    #: What a LinkedIn profile or its company page would actually say for
    #: somebody to count: a job title, a company descriptor, a product the
    #: company's own page names. This is the bar a candidate is held to.
    #:
    #: Reads `signals` from a proposal saved before the split, so a job the
    #: user already paid for still renders and can still drive a search.
    profile_signals: list[Criterion] = Field(
        default_factory=list, max_length=10,
        validation_alias=AliasChoices("profile_signals", "signals"),
    )
    #: Evidence that would strengthen a lead and cannot be read off a profile:
    #: a repository, a changelog, a postmortem, a forum post.
    #:
    #: Its own field because an audience map's `signals` are written for the
    #: prospect finder, which qualifies *companies* against fetched evidence.
    #: Handed to a profile search as though they were entry conditions, they
    #: ask it to prove per person something no profile carries - and it
    #: correctly answers with nobody. Here they are optional by construction:
    #: found, they belong in the candidate's reason; absent, they change
    #: nothing.
    corroboration: list[Criterion] = Field(default_factory=list, max_length=10)
    #: Who looks like a match on paper and is not, e.g. "job seekers", "students".
    exclusions: list[Criterion] = Field(default_factory=list, max_length=10)
    #: Why these criteria and not others, in the model's own words.
    rationale: str = Field(default="", max_length=2000)
    #: What they were derived from, written by code rather than the model:
    #: "the audience map" or "the compiled knowledge base".
    basis: str = Field(default="", max_length=400)

    @property
    def is_empty(self) -> bool:
        """Nothing here can drive a search. Corroboration and exclusions do
        not count: neither of them can find anybody on their own."""
        return not (self.roles or self.industries or self.geographies
                    or self.profile_signals or self.company_sizes)

    def render(self) -> str:
        """The criteria as prompt text. Empty sections are left out rather
        than sent as "none", which a model reads as a constraint."""
        sections = (
            ("Roles or job titles", self.roles),
            ("Industries", self.industries),
            ("Organisation size", self.company_sizes),
            ("Geographies", self.geographies),
            ("Visible on the profile", self.profile_signals),
            (
                "Corroboration - optional, never a condition for returning somebody",
                self.corroboration,
            ),
            ("Do not return", self.exclusions),
        )
        lines = [f"{label}: {', '.join(values)}" for label, values in sections if values]
        return "\n".join(lines)


class CriteriaRequest(BaseModel):
    """Ask for a targeting proposal. Every field is optional: the point of
    this step is that the brand already knows the answer."""

    model_config = ConfigDict(str_strip_whitespace=True)

    #: An audience from this brand's demand map. When set, its buyer role,
    #: signals and where-to-find-them drive the proposal instead of the
    #: knowledge base's own idea of who buys.
    segment_name: str = Field(default="", max_length=200)
    #: Anything the user knows that the material does not say.
    hint: str = Field(default="", max_length=2000)
    target: Literal["people", "companies"] = "people"


class SearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    #: Optional since the criteria step exists: a search can be driven by the
    #: proposal, by a typed query, or by both - but not by neither, which
    #: would be a paid call with nothing to look for.
    query: str = Field(default="", max_length=2000)
    criteria: TargetingCriteria | None = None
    target: Literal["people", "companies"] = "people"
    limit: int = Field(default=5, ge=1, le=10)

    @model_validator(mode="after")
    def something_to_search_for(self) -> "SearchRequest":
        if len(self.query) < 3 and (self.criteria is None or self.criteria.is_empty):
            raise ValueError("Describe who to look for, or propose criteria first")
        return self


class LinkedInCandidate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: str
    headline: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=1000)
    source_url: str
    excerpt: str = Field(min_length=1, max_length=2000)

    @field_validator("url")
    @classmethod
    def valid_profile(cls, value: str) -> str:
        return linkedin_url(value)

    @field_validator("source_url")
    @classmethod
    def safe_source(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
            raise ValueError("A public HTTP source URL is required")
        return value


class SearchAnswer(BaseModel):
    """What the searching model is asked for - and nothing else. The criteria
    are not in here on purpose: they were decided before the search and a
    model that could restate them would be reporting a search nobody ran."""

    candidates: list[LinkedInCandidate] = Field(default_factory=list, max_length=10)
    note: str = Field(default="", max_length=2000)


class SearchResult(SearchAnswer):
    #: The criteria this search was actually run against, echoed back so the
    #: saved job says who it was looking for and not only what it found.
    criteria: TargetingCriteria | None = None


class MessageRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    recipient_name: str = Field(min_length=1, max_length=200)
    recipient_url: str
    confirmed_context: str = Field(default="", max_length=6000)
    objective: str = Field(min_length=3, max_length=1500)
    language: str = Field(default="French", min_length=2, max_length=60)
    kind: Literal["connection", "message"] = "message"

    @field_validator("recipient_url")
    @classmethod
    def valid_profile(cls, value: str) -> str:
        return linkedin_url(value)


class MessageDraft(BaseModel):
    body: str = Field(min_length=1, max_length=1500)


class LinkedInChannel(BaseModel):
    """A campaign whose deliverable is a LinkedIn message rather than email.

    Stored on the campaign as its own column rather than folded into `policy`:
    the policy decides how a run is executed, and this decides what the run
    produces. A campaign with this set plans exactly as an email campaign does
    - same knowledge, same audience, same Strategist - and then writes one
    message instead of a sequence.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    recipient_name: str = Field(min_length=1, max_length=200)
    recipient_url: str
    #: Facts about this recipient the user has checked themselves. The only
    #: recipient-specific evidence the writer may argue from - a search
    #: result's own suggestion never lands here without somebody reading it.
    confirmed_context: str = Field(default="", max_length=6000)
    language: str = Field(default="French", min_length=2, max_length=60)
    kind: Literal["connection", "message"] = "message"

    @field_validator("recipient_url")
    @classmethod
    def valid_profile(cls, value: str) -> str:
        return linkedin_url(value)

    def message_request(self, objective: str) -> MessageRequest:
        """The writer's own request. The objective comes from the campaign -
        its goal if the user set one, its request otherwise - so the same
        sentence drives the brief and the draft."""
        return MessageRequest(
            recipient_name=self.recipient_name,
            recipient_url=self.recipient_url,
            confirmed_context=self.confirmed_context,
            objective=objective,
            language=self.language,
            kind=self.kind,
        )


class LinkedInRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    brand_id: UUID
    kind: str
    state: str
    request: dict
    result: dict
    error: str
    calls: int
    input_tokens: int
    output_tokens: int
    created_at: datetime
    completed_at: datetime | None
