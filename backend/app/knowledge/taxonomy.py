"""Where a fact belongs, and what it is worth to a sale.

The compiler produces one flat inventory. That is the right shape for the
evidence gate - it only ever asks "is this licensed" - and the wrong shape for
everything else. A hundred and twenty entries in one list is not knowledge a
person can read, and it is not knowledge a strategist can plan against either:
"you have 121 facts" says nothing, while "you have six commercial facts, three
proof points and nothing at all about security" is a campaign decision.

So every fact gets two coordinates, both computed here, both computed in code.

**Category** is the shelf: the department of the business a fact belongs to,
and therefore the buyer question it answers. A price answers "what does this
cost me"; a SOC 2 report answers "can I put our data in it". Those are
different conversations and a reader browsing their own knowledge base is
almost always in one of them.

**Commercial value** is how much the fact can move somebody. It is a score,
not a vibe: a named customer with a percentage beats a paragraph about a
powerful, intuitive dashboard, and the scorer says so with reasons attached,
because a number a user cannot interrogate is a number they will not trust.

Neither costs a model call. Classification runs off the kind the compiler
already assigned plus a lexicon; scoring runs off the strength it already
assigned plus what the text actually contains. Both are therefore available
for artifacts compiled months ago, with no recompile and no migration.

This module deliberately imports nothing from the rest of the application. It
is depended on by the ledger, which is depended on by everything.
"""

import re
from dataclasses import dataclass, field
from enum import StrEnum


class FactCategory(StrEnum):
    """The shelves. Ordered as a buyer meets them, not alphabetically."""

    PROOF = "proof"
    COMMERCIAL = "commercial"
    PRODUCT = "product"
    TECHNICAL = "technical"
    TRUST = "trust"
    MARKET = "market"
    OPERATIONS = "operations"
    COMPANY = "company"
    BRAND = "brand"


class ValueBand(StrEnum):
    """What a fact is for, in a campaign.

    A band is a coarser thing than a score and the one a human should read:
    the difference between 71 and 68 is noise, the difference between "lead
    an email with this" and "use it as a supporting line" is a decision.
    """

    HEADLINE = "headline"
    SUPPORTING = "supporting"
    BACKGROUND = "background"


@dataclass(frozen=True)
class Shelf:
    """What one category is, phrased for the two audiences that read it.

    `buyer_question` is the user-facing one - it is what somebody browsing
    their own knowledge base is actually looking for. `sells_by` is the
    agent-facing one: how copy is allowed to spend this kind of fact.
    """

    category: FactCategory
    label: str
    blurb: str
    buyer_question: str
    sells_by: str
    #: Where a fact of this category starts before anything else is known
    #: about it. The whole ordering of the knowledge base rests on this line,
    #: so it is stated once, here, rather than implied by sort order in three
    #: different places.
    base_value: int
    #: What it costs a campaign when this shelf is empty. Rendered to the user
    #: and to the strategist, because an empty shelf is a decision, not a bug.
    when_empty: str


SHELVES: dict[FactCategory, Shelf] = {
    FactCategory.PROOF: Shelf(
        category=FactCategory.PROOF,
        label="Proof & results",
        blurb=(
            "Somebody other than the company vouching for it, or a measured outcome "
            "somebody actually got."
        ),
        buyer_question="Has this worked for anyone like me?",
        sells_by=(
            "The only facts a stranger has any reason to believe on first contact. Spend "
            "them where the email asks for trust."
        ),
        base_value=46,
        when_empty=(
            "Nothing here proves anyone uses this. Every email will be the company "
            "asserting things about itself - plan angles that do not need proof."
        ),
    ),
    FactCategory.COMMERCIAL: Shelf(
        category=FactCategory.COMMERCIAL,
        label="Commercial terms",
        blurb="Prices, plans, trials, credits, contracts and how money changes hands.",
        buyer_question="What does this cost me, and what happens if I stop?",
        sells_by=(
            "The most checkable facts a business has. A named price converts better than "
            "any adjective, and it removes the reason people stall."
        ),
        base_value=40,
        when_empty=(
            "No price, no trial and no terms were found. The copy cannot name a number, "
            "cannot offer a risk reversal, and has to end on a vague ask."
        ),
    ),
    FactCategory.PRODUCT: Shelf(
        category=FactCategory.PRODUCT,
        label="Product & capability",
        blurb="What the thing actually does, and the specific capabilities it has.",
        buyer_question="What does it do, exactly?",
        sells_by=(
            "The mechanism, stated plainly enough to be judged. It asks for no trust, so "
            "it works even when there is no proof at all."
        ),
        base_value=30,
        when_empty=(
            "The material never says concretely what the product does, so the copy has to "
            "describe it in general terms - which is how an email reads as generic."
        ),
    ),
    FactCategory.TECHNICAL: Shelf(
        category=FactCategory.TECHNICAL,
        label="Technical & integration",
        blurb=(
            "How it plugs into what the reader already runs: APIs, integrations, limits, "
            "performance, deployment."
        ),
        buyer_question="Will it fit what we already have?",
        sells_by=(
            "What kills a deal silently. A reader who cannot see their own stack in the "
            "list assumes the answer is no and never asks."
        ),
        base_value=26,
        when_empty=(
            "Nothing was found about how this connects to anything else, so an email cannot "
            "answer the first question a technical reader asks."
        ),
    ),
    FactCategory.TRUST: Shelf(
        category=FactCategory.TRUST,
        label="Trust & compliance",
        blurb="Certifications, security posture, guarantees, SLAs, awards, warranties.",
        buyer_question="Is it safe to put our data and our name on this?",
        sells_by=(
            "Rarely the reason somebody buys and often the reason they cannot. One line "
            "here removes an objection an entire email would otherwise be spent on."
        ),
        base_value=32,
        when_empty=(
            "No certification, guarantee or security commitment was found. Any reader who "
            "needs one has no answer, and the copy cannot invent one."
        ),
    ),
    FactCategory.MARKET: Shelf(
        category=FactCategory.MARKET,
        label="Market & audience",
        blurb="Who buys this, what they are trying to get done, and why they say no.",
        buyer_question="Is this for someone like me?",
        sells_by=(
            "Where the first sentence comes from. An email opens on the reader's situation "
            "or it opens on the product, and the second one is deleted."
        ),
        base_value=24,
        when_empty=(
            "Who buys this was never established, so every email is written to a guess "
            "about the reader."
        ),
    ),
    FactCategory.OPERATIONS: Shelf(
        category=FactCategory.OPERATIONS,
        label="Onboarding & support",
        blurb="Getting started, migration, implementation, support and what happens after.",
        buyer_question="How much work is this going to be for me?",
        sells_by=(
            "The answer to effort objections, which are the most common kind and the least "
            "often addressed. 'An afternoon, not a quarter' is a whole email."
        ),
        base_value=24,
        when_empty=(
            "Nothing was found about setup, migration or support, so the copy cannot answer "
            "'how much work is this' - the objection that stops the most deals."
        ),
    ),
    FactCategory.COMPANY: Shelf(
        category=FactCategory.COMPANY,
        label="Company & people",
        blurb="Who is behind it: team, founding, funding, mission, where they are.",
        buyer_question="Who am I actually dealing with?",
        sells_by=(
            "Almost never the argument, occasionally the reason a cold email reads as being "
            "from a person. Use it in the sign-off, not the pitch."
        ),
        base_value=14,
        when_empty="Nothing was found about who is behind this. Rarely a problem for cold copy.",
    ),
    FactCategory.BRAND: Shelf(
        category=FactCategory.BRAND,
        label="Brand & voice",
        blurb="How this company sounds and the words it uses about itself.",
        buyer_question="Does this sound like us?",
        sells_by=(
            "Not a claim and never cited as one. It is what stops the copy sounding like an "
            "agency that skimmed the site for ten minutes."
        ),
        base_value=18,
        when_empty=(
            "No existing copy was found to learn a voice from, so the emails will sound "
            "competent but not like this company."
        ),
    ),
}

#: Display order everywhere: the API, the UI, the strategist's map. Most
#: commercially useful first, so an empty top shelf is the first thing seen.
CATEGORY_ORDER: tuple[FactCategory, ...] = tuple(SHELVES)


def shelf(category: FactCategory) -> Shelf:
    return SHELVES[category]


# -------------------------------------------------------------- the lexicons

#: Terms that place a fact on a shelf. Deliberately concrete nouns rather than
#: concepts: "webhook" is evidence of a technical fact in a way that
#: "flexible" is evidence of nothing. Multi-word entries are matched as
#: phrases, so "case study" does not fire on the word "case".
_LEXICON: dict[FactCategory, tuple[str, ...]] = {
    # No bare "customer" or "client". Those words appear in "customer data",
    # "customer support" and "client library" far more often than in anything
    # a stranger would find persuasive, and a proof shelf that fills up with
    # them stops answering the one question it exists for. Proof needs
    # somebody vouching, so the terms here are the shapes vouching takes.
    FactCategory.PROOF: (
        "our customers", "customers say", "customers use", "customers trust",
        "customers report", "customers, including", "clients include", "testimonial",
        "case study", "case studies", "review", "reviews", "rated", "rating",
        "trusted by", "used by", "teams use", "companies use", "saved", "savings",
        "reduced", "increased", "cut", "grew", "doubled", "tripled", "roi",
        "results", "outcome", "says", "said", "according to", "g2", "capterra",
        "trustpilot", "stars", "nps", "retention", "churn", "switched from",
        "before and after", "we use", "our team uses",
    ),
    FactCategory.COMMERCIAL: (
        "price", "prices", "pricing", "cost", "costs", "per month", "per year",
        "per seat", "per user", "monthly", "annual", "annually", "plan", "plans", "tier",
        "tiers", "subscription", "free tier", "free trial", "trial", "credits", "discount",
        "billing", "billed", "invoice", "contract", "seat", "seats", "license", "quote",
        "money back", "refund", "upgrade", "downgrade", "cancel anytime", "usd", "eur",
        "gbp", "pay as you go", "paid", "purchase", "buy", "quota", "included in",
        "starter", "pro plan", "enterprise", "usage", "overage", "add-on", "renewal",
    ),
    FactCategory.PRODUCT: (
        "feature", "features", "dashboard", "workflow", "workflows", "template",
        "templates", "editor", "automates", "automatically", "generates", "drafts",
        "tracks", "manages", "schedules", "reports", "alerts", "notifications",
        "collaborate", "you can", "supports", "built in", "built-in", "offline",
        "mobile app", "desktop app", "browser extension", "search", "filter",
    ),
    FactCategory.TECHNICAL: (
        "api", "apis", "sdk", "webhook", "webhooks", "integration", "integrations",
        "integrates", "connects", "connector", "oauth", "sso", "saml", "scim", "latency",
        "uptime", "throughput", "requests per", "rate limit", "self-host", "self hosted",
        "on-premise", "on premise", "cloud", "aws", "azure", "gcp", "kubernetes", "docker",
        "database", "postgres", "mysql", "python", "javascript", "typescript", "endpoint",
        "json", "csv", "encryption", "architecture", "deploy", "deployment", "ci/cd",
        "github", "gitlab", "slack", "zapier", "salesforce", "hubspot", "notion",
        "export", "import", "schema", "open source", "library", "runtime", "server",
        "serverless", "auto-scaling", "autoscaling", "scales", "availability", "region",
        "regions", "concurrency", "http", "rest", "graphql", "token", "tokens", "model",
        "models", "queue", "retry", "timeout", "logs", "backup", "version",
    ),
    FactCategory.TRUST: (
        "soc 2", "soc2", "iso 27001", "gdpr", "hipaa", "pci", "ccpa", "compliance",
        "compliant", "certified", "certification", "audit", "audited", "penetration test",
        "encrypted at rest", "security", "privacy", "sla", "guarantee", "guaranteed",
        "warranty", "insured", "award", "awarded", "patent", "patented", "accredited",
        "data residency", "no training on your data",
    ),
    FactCategory.MARKET: (
        "competitor", "competitors", "alternative", "alternatives", "unlike", "versus",
        " vs ", "compared to", "category", "positioning", "market", "industry",
        "segment", "ideal for", "built for", "designed for", "made for", "niche",
        "market leader", "buyers", "audience", "persona",
    ),
    FactCategory.OPERATIONS: (
        "onboarding", "onboard", "setup", "set up", "get started", "getting started",
        "migration", "migrate", "implementation", "rollout", "support", "training",
        "documentation", "docs", "help center", "response time", "account manager",
        "customer success", "ticket", "live chat", "office hours", "in minutes",
        "no code", "no-code", "installation", "install",
    ),
    FactCategory.COMPANY: (
        "founded", "founder", "founders", "headquarters", "headquartered", "based in",
        "team of", "employees", "hiring", "funding", "raised", "series a", "series b",
        "seed round", "investors", "backed by", "mission", "remote team", "offices",
        "our story", "since 19", "since 20",
    ),
}

#: A kind the compiler assigns that decides the shelf outright. These are not
#: ambiguous: a price is a commercial fact wherever the words around it point,
#: and letting a lexicon overrule them costs accuracy on the entries that
#: matter most.
_LOCKED_BY_KIND: dict[str, FactCategory] = {
    "price": FactCategory.COMMERCIAL,
    "testimonial": FactCategory.PROOF,
    "customer": FactCategory.PROOF,
    "award": FactCategory.TRUST,
    "certification": FactCategory.TRUST,
}

#: A kind that suggests a shelf without settling it, and how hard it leans.
#: `feature` leans barely at all - it is the compiler's catch-all, and roughly
#: two thirds of a real ledger arrives wearing it, which is exactly why a
#: kind-only classification would file two thirds of a business under
#: "product" and teach the user nothing.
_PRIOR_BY_KIND: dict[str, tuple[FactCategory, float]] = {
    "feature": (FactCategory.PRODUCT, 1.2),
    "integration": (FactCategory.TECHNICAL, 2.5),
    "guarantee": (FactCategory.TRUST, 2.0),
    # Under 1, so any single lexicon hit outvotes it. `metric` means "there is
    # a number in this", which is true of a customer outcome, a rate limit, a
    # plan quota and an uptime figure alike - four different shelves. Left at
    # 1.5 it filed "99.9% uptime" and "Pro plan includes 30 days of history"
    # under proof, which is the one shelf a user reads to answer "has this
    # worked for anyone", and neither of those answers it.
    "metric": (FactCategory.PROOF, 0.9),
}

#: Where a kind lands when the text gives no signal whatsoever. Distinct from
#: the prior, and the distinction matters most for `metric`: it leans proof
#: when the words back it up, but a bare number with nothing around it
#: ("default temperature setting is 0.7") is a product detail, and filing it
#: under proof puts a config default on the shelf a user opens to find out
#: whether anybody uses this.
_FALLBACK_BY_KIND: dict[str, FactCategory] = {
    "feature": FactCategory.PRODUCT,
    "integration": FactCategory.TECHNICAL,
    "guarantee": FactCategory.TRUST,
    "metric": FactCategory.PRODUCT,
}

#: A long verbatim quote mentioning "slack" four times is not four times as
#: technical as one mentioning it once.
_MAX_HITS_PER_CATEGORY = 4


def _compile(terms: tuple[str, ...]) -> re.Pattern[str]:
    # Terms containing a space are phrases and are matched literally; single
    # words get word boundaries so "api" does not fire inside "capital".
    parts = [
        re.escape(term) if " " in term or "/" in term else rf"\b{re.escape(term)}\b"
        for term in terms
    ]
    return re.compile("|".join(parts), re.IGNORECASE)


_PATTERNS: dict[FactCategory, re.Pattern[str]] = {
    category: _compile(terms) for category, terms in _LEXICON.items()
}


def classify(text: str, kind: str = "") -> FactCategory:
    """Which shelf this fact belongs on.

    `kind` is whatever the compiler already decided (an EvidenceKind value, or
    empty for facts that never had one). It is a prior, not an answer: the
    text gets a vote, and for the catch-all kinds the text usually wins.
    """
    locked = _LOCKED_BY_KIND.get(str(kind).lower())
    if locked is not None:
        return locked

    normalized = str(kind).lower()
    scores: dict[FactCategory, float] = {}
    haystack = text.lower()
    for category, pattern in _PATTERNS.items():
        hits = len({match.group(0).lower() for match in pattern.finditer(haystack)})
        if hits:
            scores[category] = min(hits, _MAX_HITS_PER_CATEGORY)

    if not scores:
        # The text said nothing either way, so the prior has nothing to weigh
        # against and must not decide by walkover - a prior below 1.0 exists
        # precisely because its shelf is wrong more often than not.
        return _FALLBACK_BY_KIND.get(normalized, FactCategory.PRODUCT)

    prior = _PRIOR_BY_KIND.get(normalized)
    if prior is not None:
        scores[prior[0]] = scores.get(prior[0], 0.0) + prior[1]
    # Ties break towards the shelf that is worth more commercially, which is
    # also the shelf a user is more likely to be looking for it on.
    return max(scores, key=lambda category: (scores[category], -CATEGORY_ORDER.index(category)))


# ----------------------------------------------------------------- the score

#: Score at or above which a fact can carry an email on its own.
HEADLINE_AT = 70
#: Score at or above which a fact is worth a sentence somewhere in the copy.
SUPPORTING_AT = 42

_MONEY_RE = re.compile(r"[$€£]\s?\d|\b\d[\d,.]*\s?(?:usd|eur|gbp|dollars?|euros?)\b", re.IGNORECASE)
_PROPORTION_RE = re.compile(r"\b\d[\d,.]*\s?%|\b\d[\d,.]*\s?[x×]\b|\b\d[\d,.]*\s?percent\b", re.IGNORECASE)
_DURATION_RE = re.compile(
    r"\b\d[\d,.]*[\s-]?(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\b\d{2,}\b")
#: A capitalized word that is not the first word of the statement. Crude, and
#: it is meant to be: a proper noun anywhere in a claim usually means the
#: claim names somebody or something in particular, which is the property
#: being rewarded.
_PROPER_NOUN_RE = re.compile(r"(?<!^)(?<![.!?]\s)\b[A-Z][a-zA-Z]{2,}\b")

#: The words that appear when a sentence has nothing in it. Penalised only
#: when nothing checkable appears alongside them - "40% faster and genuinely
#: seamless" is still a fact with a number in it.
_FILLER_RE = _compile(
    (
        "powerful", "seamless", "seamlessly", "robust", "cutting edge", "cutting-edge",
        "world class", "world-class", "innovative", "intuitive", "easy to use",
        "best in class", "best-in-class", "leading", "revolutionary", "state of the art",
        "state-of-the-art", "next generation", "next-generation", "game changing",
        "game-changing", "unlock", "empower", "supercharge", "effortless", "streamline",
    )
)

_STRENGTH_POINTS: dict[str, tuple[int, str]] = {
    "strong": (18, "specific and attributed - it holds up if somebody checks"),
    "moderate": (6, "specific, but nobody is named behind it"),
    "weak": (-8, "real but vague, so it proves less than it seems to"),
}

#: Specificity is worth a lot and is easy to accumulate; without a cap a
#: sentence stuffed with numbers would outrank a named customer outcome.
_MAX_SPECIFICITY = 20


@dataclass(frozen=True)
class CommercialValue:
    """What a fact is worth to a sale, and why - the why is the point.

    A bare number invites the user to argue with the ranking and gives them no
    way to. The reasons are the same lines the strategist reads, so a user who
    disagrees with the score is disagreeing with something they can actually
    fix, usually by uploading the page that would make the fact attributable.
    """

    score: int
    band: ValueBand
    reasons: list[str] = field(default_factory=list)

    @property
    def is_headline(self) -> bool:
        return self.band is ValueBand.HEADLINE


def band_for(score: int) -> ValueBand:
    if score >= HEADLINE_AT:
        return ValueBand.HEADLINE
    if score >= SUPPORTING_AT:
        return ValueBand.SUPPORTING
    return ValueBand.BACKGROUND


def assess_value(
    *,
    category: FactCategory,
    statement: str,
    verbatim: str = "",
    strength: str = "",
    user_attested: bool = False,
) -> CommercialValue:
    """Score one fact out of a hundred, with the reasoning attached.

    Everything here is read off the fact itself. Nothing consults a model,
    which is what makes it safe to run over every entry of every artifact set
    on every page load, and what makes two identical facts score identically
    forever.
    """
    contributions: list[tuple[int, str]] = []
    known = SHELVES[category]
    contributions.append(
        (known.base_value, f"answers the question buyers ask here: {known.buyer_question}")
    )

    if strength:
        points, reason = _STRENGTH_POINTS.get(str(strength).lower(), (0, ""))
        if reason:
            contributions.append((points, reason))

    specificity = 0
    if _MONEY_RE.search(statement):
        specificity += 10
        contributions.append((10, "names a figure in money, which a reader can act on"))
    if _PROPORTION_RE.search(statement):
        specificity += 10
        contributions.append((10, "carries a proportion, which is the most quotable kind of number"))
    if _DURATION_RE.search(statement):
        specificity += 6
        contributions.append((6, "says how long something takes"))
    if _NUMBER_RE.search(statement):
        specificity += 5
        contributions.append((5, "carries a number a skeptical reader could check"))
    if specificity > _MAX_SPECIFICITY:
        contributions.append((_MAX_SPECIFICITY - specificity, "capped: one fact, however many numbers"))
        specificity = _MAX_SPECIFICITY

    if _PROPER_NOUN_RE.search(statement):
        contributions.append((5, "names somebody or something in particular"))
    if user_attested:
        contributions.append((5, "the user confirmed this themselves"))

    if not verbatim.strip():
        contributions.append((-6, "nothing in the material is quoted behind it"))
    elif len(verbatim.strip()) >= 60:
        contributions.append((4, "the source states it in full, not in passing"))

    checkable = bool(specificity)
    if _FILLER_RE.search(statement) and not checkable:
        contributions.append((-10, "marketing adjectives with nothing checkable behind them"))

    score = max(0, min(100, sum(points for points, _ in contributions)))
    # Reasons the user reads, biggest movers first. The base is always shown
    # because it explains the shelf; after that only what actually changed the
    # answer is worth their attention.
    ranked = [contributions[0]] + sorted(contributions[1:], key=lambda item: -abs(item[0]))
    reasons = [reason for _, reason in ranked if reason][:4]
    return CommercialValue(score=score, band=band_for(score), reasons=reasons)
