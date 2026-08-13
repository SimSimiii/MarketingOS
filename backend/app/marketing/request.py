from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignRequest:
    """What the user asked for, in their own words, plus the context around it.

    `request` is the contract and is rendered verbatim at the top of every
    prompt in the run. That one habit is what makes "3 emails" produce three
    emails instead of a generic campaign, and it survives the redesign
    unchanged - it was the best idea in the original system.

    Everything else here is context the knowledge artifacts usually know
    better. It is kept because a user typing "we're targeting agencies, not
    freelancers" in the campaign form is stating something no crawl can
    discover, and that must outrank what the compiler inferred.
    """

    name: str
    request: str
    product_description: str = ""
    product_url: str | None = None
    target_market: str | None = None
    goals: str | None = None

    def render_context(self) -> str:
        lines = [f"Campaign: {self.name}"]
        if self.product_description:
            lines.append(f"What the user says the product is: {self.product_description}")
        if self.target_market:
            lines.append(f"Who the user says they are targeting: {self.target_market}")
        if self.goals:
            lines.append(f"What the user wants out of it: {self.goals}")
        return "\n".join(lines)
